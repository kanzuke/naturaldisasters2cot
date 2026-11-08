from typing import Any, List

from ..models import CotEvent
from . import register
from .base import BaseSource


@register("usgs_quakes")
class UsgsQuakeSource(BaseSource):
    def fetch(self) -> Any:
        return self.http_get_json(self.require("url"))

    def to_events(self, raw: Any) -> List[CotEvent]:
        events = []
        for feat in raw.get("features", []):
            props = feat.get("properties", {})
            coords = feat.get("geometry", {}).get("coordinates", [])
            if len(coords) < 2:
                continue
            lon, lat = coords[0], coords[1]
            depth_km = coords[2] if len(coords) > 2 else 0.0
            mag = props.get("mag")

            events.append(CotEvent(
                uid=f"USGS-QUAKE-{feat.get('id', 'unknown')}",
                cot_type="a-u-G",
                lat=lat, lon=lon,
                hae=-float(depth_km) * 1000.0,
                callsign=f"M{mag} {props.get('place', '')}".strip(),
                remarks="\n".join([
                    f"Séisme M{mag}",
                    f"Lieu: {props.get('place', 'N/A')}",
                    f"Profondeur: {depth_km} km",
                    f"Détails: {props.get('url', 'N/A')}",
                    "Source: USGS",
                ]),
                stale_seconds=3600,
            ))
        return events