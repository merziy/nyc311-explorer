from datetime import datetime
from zoneinfo import ZoneInfo

from flask import Blueprint, jsonify, request
from sqlalchemy import func

from app.models import Borough, Complaint

api_bp = Blueprint("api", __name__, url_prefix="/api")

DEFAULT_LIMIT = 100
MAX_LIMIT = 500
DEFAULT_SUMMARY_LIMIT = 10
NYC_TZ = ZoneInfo("America/New_York")


def parse_date_param(value: str) -> datetime | None:
    try:
        naive = datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        return None
    return naive.replace(tzinfo=NYC_TZ)


def apply_borough_and_date_filters(query):
    """Applies borough/start/end filters shared by both endpoints. Returns
    (filtered_query, None) on success, or (None, (response, status)) if a
    param failed to parse."""
    borough_param = request.args.get("borough")
    if borough_param:
        try:
            borough = Borough(borough_param.strip().upper())
        except ValueError:
            return None, (jsonify({"error": f"invalid borough: {borough_param!r}"}), 400)
        query = query.filter(Complaint.borough == borough)

    start_param = request.args.get("start")
    if start_param:
        start = parse_date_param(start_param)
        if start is None:
            return None, (jsonify({"error": f"invalid start date: {start_param!r}"}), 400)
        query = query.filter(Complaint.created_date >= start)

    end_param = request.args.get("end")
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
