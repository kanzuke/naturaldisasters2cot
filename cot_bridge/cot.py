import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

from .models import CotEvent


def _fmt_time(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%S.") + f"{dt.microsecond // 1000:03d}Z"


def event_to_xml(ev: CotEvent, default_stale_seconds: int) -> str:
    now_dt = datetime.now(timezone.utc)
    stale_s = ev.stale_seconds if ev.stale_seconds is not None else default_stale_seconds

    root = ET.Element("event", {
        "version": "2.0",
        "uid": ev.uid,
        "type": ev.cot_type,
        "how": ev.how,
        "time": _fmt_time(now_dt),
        "start": _fmt_time(now_dt),
        "stale": _fmt_time(now_dt + timedelta(seconds=stale_s)),
    })
    ET.SubElement(root, "point", {
        "lat": f"{ev.lat:.5f}", "lon": f"{ev.lon:.5f}",
        "hae": f"{ev.hae}", "ce": f"{ev.ce}", "le": f"{ev.le}",
    })

    detail = ET.SubElement(root, "detail")
    if ev.callsign:
        ET.SubElement(detail, "contact", {"callsign": ev.callsign})
    if ev.course is not None and ev.speed is not None:
        ET.SubElement(detail, "track", {"course": f"{ev.course:.1f}", "speed": f"{ev.speed:.2f}"})
    for tag, attrs in ev.extra_detail.items():
        ET.SubElement(detail, tag, {k: str(v) for k, v in attrs.items()})
    if ev.remarks:
        ET.SubElement(detail, "remarks").text = ev.remarks

    return ET.tostring(root, encoding="unicode")