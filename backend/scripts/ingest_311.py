"""Pull NYC 311 complaints from the Socrata API and upsert them into Postgres.

Standalone script, not part of the Flask request path — run manually:

    cd backend && .venv/bin/python -m scripts.ingest_311

Pulls the last MONTHS_BACK months of "311 Service Requests" (dataset erm2-nwe9)
and upserts by unique_key, so re-running is always safe.

Uses keyset pagination (WHERE unique_key > last_seen), not offset pagination —
Socrata's own docs warn that OFFSET gets slow past tens of thousands of rows,
and even a 3-month pull is realistically a few hundred thousand rows.

unique_key is typed as Text in Socrata's schema, not Number, so the cursor is
compared and ordered as a string. That's only safe because unique_key values
within a recent, short (MONTHS_BACK) window share the same digit count, so
lexicographic and numeric ordering agree - it would not hold for a pull
spanning a digit-count boundary (e.g. many years back).
"""

import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import httpx
from sqlalchemy.dialects.postgresql import insert

from app import create_app
from app.config import settings
from app.extensions import db
from app.models import Borough, Complaint

DATASET_URL = "https://data.cityofnewyork.us/resource/erm2-nwe9.json"
PAGE_SIZE = 1000
MONTHS_BACK = 3
NYC_TZ = ZoneInfo("America/New_York")
CHECKPOINT_FILE = Path(__file__).parent / ".ingest_311_checkpoint.json"
MAX_RETRIES = 3
RETRY_BACKOFF_SECONDS = 2


def parse_socrata_datetime(value: str | None) -> datetime | None:
    """Socrata returns naive local (America/New_York) timestamps, e.g. '2024-03-01T14:22:07.000'."""
    if not value:
        return None
    naive = datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%f")
    return naive.replace(tzinfo=NYC_TZ)


def normalize_borough(value: str | None) -> Borough | None:
    if not value:
        return None
    try:
        return Borough(value.strip().upper())
    except ValueError:
        return None


def normalize_row(raw: dict) -> dict:
    return {
        "unique_key": int(raw["unique_key"]),
        "created_date": parse_socrata_datetime(raw.get("created_date")),
        "closed_date": parse_socrata_datetime(raw.get("closed_date")),
        "complaint_type": raw.get("complaint_type", ""),
        "descriptor": raw.get("descriptor"),
        "resolution_description": raw.get("resolution_description"),
        "borough": normalize_borough(raw.get("borough")),
        "incident_zip": (raw.get("incident_zip") or "").strip() or None,
        "agency": raw.get("agency"),
        "status": raw.get("status"),
        "latitude": float(raw["latitude"]) if raw.get("latitude") else None,
        "longitude": float(raw["longitude"]) if raw.get("longitude") else None,
    }


def fetch_page(client: httpx.Client, since: str, last_unique_key: int) -> list[dict]:
    params = {
        # unique_key is typed as Text in Socrata's schema, not Number — the
        # cursor value must be quoted or the API returns a type-mismatch 400.
        "$where": f"created_date >= '{since}' AND unique_key > '{last_unique_key}'",
        "$order": "unique_key ASC",
        "$limit": PAGE_SIZE,
    }
    headers = {"X-App-Token": settings.socrata_app_token} if settings.socrata_app_token else {}

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = client.get(DATASET_URL, params=params, headers=headers, timeout=60.0)
            response.raise_for_status()
            return response.json()
        except httpx.TransportError:
            if attempt == MAX_RETRIES:
                raise
            time.sleep(RETRY_BACKOFF_SECONDS * attempt)


def load_checkpoint() -> tuple[str, int] | None:
    if not CHECKPOINT_FILE.exists():
        return None
    data = json.loads(CHECKPOINT_FILE.read_text())
    return data["since"], data["last_unique_key"]


def save_checkpoint(since: str, last_unique_key: int) -> None:
    CHECKPOINT_FILE.write_text(json.dumps({"since": since, "last_unique_key": last_unique_key}))


def clear_checkpoint() -> None:
    CHECKPOINT_FILE.unlink(missing_ok=True)


def upsert_batch(rows: list[dict]) -> None:
    if not rows:
        return
    stmt = insert(Complaint).values(rows)
    update_columns = {column.name: column for column in stmt.excluded if column.name != "unique_key"}
    stmt = stmt.on_conflict_do_update(index_elements=["unique_key"], set_=update_columns)
    db.session.execute(stmt)
    db.session.commit()


def run() -> None:
    checkpoint = load_checkpoint()
    if checkpoint:
        since, last_unique_key = checkpoint
        print(f"Resuming from unique_key={last_unique_key}")
    else:
        since = (datetime.now(timezone.utc) - timedelta(days=30 * MONTHS_BACK)).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]
        last_unique_key = 0

    total = 0

    app = create_app()
    with app.app_context():
        with httpx.Client() as client:
            while True:
                raw_rows = fetch_page(client, since, last_unique_key)
                if not raw_rows:
                    break

                rows = [normalize_row(r) for r in raw_rows if r.get("unique_key") and r.get("created_date")]
                upsert_batch(rows)
                total += len(rows)
                last_unique_key = int(raw_rows[-1]["unique_key"])
                save_checkpoint(since, last_unique_key)
                print(f"Upserted {total} rows so far (last unique_key={last_unique_key})")

                if len(raw_rows) < PAGE_SIZE:
                    break

    clear_checkpoint()
    print(f"Done. {total} rows upserted.")


if __name__ == "__main__":
    run()
