from typing import Any, List

from ..models import CotEvent
from . import register
from .base import BaseSource

CLASSIFICATIONS = {
    "TD": "Tropical Depression", "STD": "Subtropical Depression",
    "TS": "Tropical Storm", "STS": "Subtropical Storm",
    "HU": "Hurricane", "PTC": "Post-Tropical Cyclone",
    "PC": "Post-Tropical Cyclone", "TY": "Typhoon", "SS": "Subtropical Storm",
}


def _f(value, default=None):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


@register("nhc")
class NhcSource(BaseSource):
    def fetch(self) -> Any:
        return self.http_get_json(self.require("url"))

    def to_events(self, raw: Any) -> List[CotEvent]:
        events = []
        for s in raw.get("activeStorms", []):
            lat, lon = _f(s.get("latitudeNumeric")), _f(s.get("longitudeNumeric"))
            if lat is None or lon is None:
                self.log.warning("Position manquante pour %s, ignoré.", s.get("name"))
                continue

            name = s.get("name", "UNNAMED").title()
            klass = CLASSIFICATIONS.get(s.get("classification", ""), s.get("classification", "Storm"))
            wind, pres = _f(s.get("intensity")), _f(s.get("pressure"))
            mdir, mspd = _f(s.get("movementDir")), _f(s.get("movementSpeed"))

            remarks = "\n".join([
                f"{klass} {name} ({s.get('id', 'N/A')})",
                f"Vents max: {wind:.0f} kt" if wind is not None else "Vents max: N/A",
                f"Pression: {pres:.0f} mb" if pres is not None else "Pression: N/A",
                f"Déplacement: {mdir:.0f}° à {mspd:.0f} kt" if mdir is not None and mspd is not None
                else "Déplacement: N/A",
                f"Dernière mise à jour NHC: {s.get('lastUpdate', 'N/A')}",
                "Source: NOAA/NHC",
            ])

            events.append(CotEvent(
                uid=f"NHC-STORM-{s.get('id', 'unknown').lower()}",
                cot_type="a-u-G",
                lat=lat, lon=lon,
                callsign=f"{klass} {name}",
                remarks=remarks,
                ce=50000.0,
                course=mdir,
                speed=mspd * 0.514444 if mspd is not None else None,
            ))
        return events