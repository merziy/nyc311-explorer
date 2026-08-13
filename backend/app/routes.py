import json
import re
from datetime import datetime
from zoneinfo import ZoneInfo

import anthropic
from flask import Blueprint, jsonify, request
from sqlalchemy import func, or_

from app.config import settings
from app.extensions import limiter
from app.models import Borough, Complaint

api_bp = Blueprint("api", __name__, url_prefix="/api")

DEFAULT_LIMIT = 100
MAX_LIMIT = 500
DEFAULT_SUMMARY_LIMIT = 10
DEFAULT_POINTS_LIMIT = 2000
MAX_POINTS_LIMIT = 5000
NYC_TZ = ZoneInfo("America/New_York")

ASK_MODEL = "claude-sonnet-5"
ASK_LIST_LIMIT = 20
ASK_SUMMARY_LIMIT = 10

anthropic_client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

EXTRACT_FILTER_TOOL = {
    "name": "extract_complaint_filter",
    "description": (
        "Extract a structured filter from a natural-language question about NYC 311 "
        "complaints, and decide whether the question wants aggregate counts by "
        "complaint type (mode='summary') or a list of individual complaints "
        "(mode='list'). Map any neighborhood name (e.g. Bushwick, Astoria) to its "
        "containing borough, since the underlying data only has borough-level "
        "granularity, not neighborhoods."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "borough": {
                "type": "string",
                "enum": [b.value for b in Borough],
                "description": "One of the five NYC boroughs, if the question mentions a place.",
            },
            "complaint_type": {
                "type": "string",
                "description": (
                    "A keyword or phrase describing the complaint category, if the "
                    "question names one (e.g. 'noise', 'party', 'parking', or the "
                    "exact category 'Noise - Residential' if you know it). Matched "
                    "as a case-insensitive partial match against both the complaint "
                    "type and descriptor, so an approximate term is fine — you don't "
                    "need the exact official category string. Only meaningful with "
                    "mode='list' — 'summary' mode groups by complaint type, so "
                    "filtering to one type first would be self-defeating."
                ),
            },
            "start": {
                "type": "string",
                "description": "Start date as YYYY-MM-DD, if the question implies a date range.",
            },
            "end": {
                "type": "string",
                "description": "End date (exclusive) as YYYY-MM-DD, if the question implies a date range.",
            },
            "mode": {
                "type": "string",
                "enum": ["summary", "list"],
                "description": (
                    "'summary' for questions about top/most-common complaint types "
                    "or counts (e.g. 'what are the top complaints in X'). 'list' for "
                    "questions asking to see individual complaints."
                ),
            },
        },
        "required": ["mode"],
    },
}


def parse_date_param(value: str) -> datetime | None:
    try:
        naive = datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        return None
    return naive.replace(tzinfo=NYC_TZ)


def apply_borough_and_date_filters(query, params=None):
    """Applies borough/start/end filters shared by all three endpoints. `params`
    defaults to the current request's query string but also accepts a plain
    dict, since /api/ask sources filter values from a Claude tool call rather
    than the query string. Returns (filtered_query, None) on success, or
    (None, (response, status)) if a param failed to parse."""
    if params is None:
        params = request.args

    borough_param = params.get("borough")
    if borough_param:
        try:
            borough = Borough(borough_param.strip().upper())
        except ValueError:
            return None, (jsonify({"error": f"invalid borough: {borough_param!r}"}), 400)
        query = query.filter(Complaint.borough == borough)

    start_param = params.get("start")
    if start_param:
        start = parse_date_param(start_param)
        if start is None:
            return None, (jsonify({"error": f"invalid start date: {start_param!r}"}), 400)
        query = query.filter(Complaint.created_date >= start)

    end_param = params.get("end")
    if end_param:
        end = parse_date_param(end_param)
        if end is None:
            return None, (jsonify({"error": f"invalid end date: {end_param!r}"}), 400)
        query = query.filter(Complaint.created_date < end)

    return query, None


def serialize_complaint(complaint: Complaint) -> dict:
    return {
        "unique_key": complaint.unique_key,
        "created_date": complaint.created_date.isoformat() if complaint.created_date else None,
        "closed_date": complaint.closed_date.isoformat() if complaint.closed_date else None,
        "complaint_type": complaint.complaint_type,
        "descriptor": complaint.descriptor,
        "resolution_description": complaint.resolution_description,
        "borough": complaint.borough.value if complaint.borough else None,
        "incident_zip": complaint.incident_zip,
        "agency": complaint.agency,
        "status": complaint.status,
        "latitude": complaint.latitude,
        "longitude": complaint.longitude,
    }


@api_bp.get("/complaints")
def list_complaints():
    query, error = apply_borough_and_date_filters(Complaint.query)
    if error:
        return error

    complaint_type = request.args.get("complaint_type")
    if complaint_type:
        query = query.filter(Complaint.complaint_type == complaint_type)

    limit = request.args.get("limit", DEFAULT_LIMIT, type=int)
    limit = max(1, min(limit, MAX_LIMIT))
    offset = max(0, request.args.get("offset", 0, type=int))

    total = query.count()
    rows = query.order_by(Complaint.created_date.desc()).offset(offset).limit(limit).all()

    return jsonify(
        {
            "results": [serialize_complaint(c) for c in rows],
            "limit": limit,
            "offset": offset,
            "total": total,
        }
    )


@api_bp.get("/complaints/summary")
def complaints_summary():
    query, error = apply_borough_and_date_filters(Complaint.query)
    if error:
        return error

    limit = request.args.get("limit", DEFAULT_SUMMARY_LIMIT, type=int)
    limit = max(1, min(limit, MAX_LIMIT))

    count = func.count(Complaint.unique_key)
    rows = (
        query.with_entities(Complaint.complaint_type, count.label("count"))
        .group_by(Complaint.complaint_type)
        .order_by(count.desc())
        .limit(limit)
        .all()
    )

    return jsonify({"complaint_types": [{"complaint_type": ct, "count": c} for ct, c in rows]})


@api_bp.get("/complaints/<int:unique_key>")
def get_complaint(unique_key):
    complaint = Complaint.query.get(unique_key)
    if complaint is None:
        return jsonify({"error": "not found"}), 404
    return jsonify(serialize_complaint(complaint))


@api_bp.get("/complaints/points")
def complaints_points():
    """Lat/long per complaint for map views (heatmap/clusters) - a lighter
    payload than /api/complaints since map rendering doesn't need the full
    serialized row, just enough to place and color a point."""
    query, error = apply_borough_and_date_filters(Complaint.query)
    if error:
        return error

    complaint_type = request.args.get("complaint_type")
    if complaint_type:
        query = query.filter(Complaint.complaint_type == complaint_type)

    limit = request.args.get("limit", DEFAULT_POINTS_LIMIT, type=int)
    limit = max(1, min(limit, MAX_POINTS_LIMIT))

    rows = (
        query.filter(Complaint.latitude.isnot(None), Complaint.longitude.isnot(None))
        .with_entities(Complaint.unique_key, Complaint.latitude, Complaint.longitude, Complaint.complaint_type)
        .order_by(Complaint.created_date.desc())
        .limit(limit)
        .all()
    )

    return jsonify(
        {
            "results": [
                {"unique_key": uk, "latitude": lat, "longitude": lon, "complaint_type": ct}
                for uk, lat, lon, ct in rows
            ],
            "limit": limit,
        }
    )


@api_bp.post("/ask")
@limiter.limit("10 per hour")
def ask():
    payload = request.get_json(silent=True) or {}
    question = (payload.get("question") or "").strip()
    if not question:
        return jsonify({"error": "missing question"}), 400

    today = datetime.now(NYC_TZ).strftime("%Y-%m-%d")
    system = (
        f"Today's date is {today}. You turn NL questions about NYC 311 complaints "
        "into a structured filter using the extract_complaint_filter tool, and "
        "then summarize the query results a backend returns to you. You never "
        "query the database directly."
    )

    extract_response = anthropic_client.messages.create(
        model=ASK_MODEL,
        max_tokens=1024,
        thinking={"type": "disabled"},
        system=system,
        tools=[EXTRACT_FILTER_TOOL],
        tool_choice={"type": "tool", "name": "extract_complaint_filter"},
        messages=[{"role": "user", "content": question}],
    )

    if extract_response.stop_reason != "tool_use":
        return jsonify({"error": "could not extract a filter from that question"}), 502

    tool_use = next(b for b in extract_response.content if b.type == "tool_use")
    filter_args = tool_use.input

    query, error = apply_borough_and_date_filters(Complaint.query, filter_args)
    if error:
        return error

    if filter_args.get("mode") == "list":
        complaint_type = filter_args.get("complaint_type")
        if complaint_type:
            # Claude's guess rarely matches the stored complaint_type verbatim
            # (e.g. "Noise - Party" vs the real "Noise - Residential" / descriptor
            # "Loud Music/Party") - require each word somewhere in either field,
            # rather than the whole phrase as one substring.
            for word in re.findall(r"\w+", complaint_type):
                if len(word) <= 2:
                    continue
                term = f"%{word}%"
                query = query.filter(
                    or_(Complaint.complaint_type.ilike(term), Complaint.descriptor.ilike(term))
                )
        rows = query.order_by(Complaint.created_date.desc()).limit(ASK_LIST_LIMIT).all()
        results = [serialize_complaint(c) for c in rows]
    else:
        count = func.count(Complaint.unique_key)
        rows = (
            query.with_entities(Complaint.complaint_type, count.label("count"))
            .group_by(Complaint.complaint_type)
            .order_by(count.desc())
            .limit(ASK_SUMMARY_LIMIT)
            .all()
        )
        results = [{"complaint_type": ct, "count": c} for ct, c in rows]

    summary_response = anthropic_client.messages.create(
        model=ASK_MODEL,
        max_tokens=1024,
        thinking={"type": "disabled"},
        system=system,
        messages=[
            {"role": "user", "content": question},
            {"role": "assistant", "content": extract_response.content},
            {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": tool_use.id,
                        "content": json.dumps(results),
                    }
                ],
            },
        ],
    )
    answer = next((b.text for b in summary_response.content if b.type == "text"), "")

    return jsonify({"answer": answer, "filter": filter_args, "results": results})
