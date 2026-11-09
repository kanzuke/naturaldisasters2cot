import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

from .models import CotEvent, ShapeStyle


def _fmt_time(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%S.") + f"{dt.microsecond // 1000:03d}Z"


def _centroid(vertices):
    """Centre simple (moyenne des sommets) : suffisant pour positionner le marqueur."""
    lat = sum(v[0] for v in vertices) / len(vertices)
    lon = sum(v[1] for v in vertices) / len(vertices)
    return lat, lon


def _add_shape_detail(detail: ET.Element, ev: CotEvent):
    style = ev.shape_style or ShapeStyle()
    vertices = list(ev.shape)

    # Un polygone CoT doit être fermé : premier sommet == dernier sommet
    if ev.shape_closed and vertices[0] != vertices[-1]:
        vertices.append(vertices[0])

    for lat, lon in vertices:
        ET.SubElement(detail, "link", {"point": f"{lat:.5f},{lon:.5f}"})

    ET.SubElement(detail, "strokeColor", {"value": str(style.stroke_argb)})
    ET.SubElement(detail, "strokeWeight", {"value": f"{style.stroke_weight}"})
    if ev.shape_closed:
        ET.SubElement(detail, "fillColor", {"value": str(style.fill_argb)})
    ET.SubElement(detail, "labels_on", {"value": "false"})


def event_to_xml(ev: CotEvent, default_stale_seconds: int) -> str:
    now_dt = datetime.now(timezone.utc)
    stale_s = ev.stale_seconds if ev.stale_seconds is not None else default_stale_seconds

    lat, lon = ev.lat, ev.lon
    if ev.shape:
        lat, lon = _centroid(ev.shape)

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
        "lat": f"{lat:.5f}", "lon": f"{lon:.5f}",
        "hae": f"{ev.hae}", "ce": f"{ev.ce}", "le": f"{ev.le}",
    })

    detail = ET.SubElement(root, "detail")
    if ev.callsign:
        ET.SubElement(detail, "contact", {"callsign": ev.callsign})
    if ev.course is not None and ev.speed is not None:
        ET.SubElement(detail, "track", {"course": f"{ev.course:.1f}", "speed": f"{ev.speed:.2f}"})
    if ev.shape:
        _add_shape_detail(detail, ev)
    for tag, attrs in ev.extra_detail.items():
        ET.SubElement(detail, tag, {k: str(v) for k, v in attrs.items()})
    if ev.remarks:
        ET.SubElement(detail, "remarks").text = ev.remarks

    return ET.tostring(root, encoding="unicode")