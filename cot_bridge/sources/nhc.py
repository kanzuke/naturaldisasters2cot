from typing import Any, List, Optional

from ..models import CotEvent, ShapeStyle, _argb
from . import register
from .base import BaseSource
from .geo import download_kmz_kml, extract_linestrings, extract_polygons, simplify_ring

CLASSIFICATIONS = {
    "TD": "Tropical Depression", "STD": "Subtropical Depression",
    "TS": "Tropical Storm", "STS": "Subtropical Storm",
    "HU": "Hurricane", "PTC": "Post-Tropical Cyclone",
    "PC": "Post-Tropical Cyclone", "TY": "Typhoon", "SS": "Subtropical Storm",
}

CONE_STYLE = ShapeStyle(
    stroke_argb=_argb(255, 255, 255, 255),
    fill_argb=_argb(70, 255, 255, 255),
    stroke_weight=2.0,
)

# Ligne centrale : orange vif, plus épaisse que le contour du cône
TRACK_STYLE = ShapeStyle(
    stroke_argb=_argb(255, 255, 140, 0),
    stroke_weight=4.0,
)


def _f(value, default=None):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _as_bool(value, default=True) -> bool:
    if value is None:
        return default
    return str(value).lower() in ("true", "1", "yes")


@register("nhc")
class NhcSource(BaseSource):
    def fetch(self) -> Any:
        return self.http_get_json(self.require("url"))

    # ---------- Point central ---------- (inchangé)
    def _storm_point(self, s, lat, lon, name, klass) -> CotEvent:
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
        return CotEvent(
            uid=f"NHC-STORM-{s.get('id', 'unknown').lower()}",
            cot_type="a-u-G",
            lat=lat, lon=lon,
            callsign=f"{klass} {name}",
            remarks=remarks,
            ce=50000.0,
            course=mdir,
            speed=mspd * 0.514444 if mspd is not None else None,
        )

    # ---------- Téléchargement KML mutualisé ----------
    def _load_kml(self, url: Optional[str], name: str, label: str) -> Optional[bytes]:
        """Télécharge un KMZ/KML ; retourne None (avec log) en cas d'échec."""
        if not url:
            return None
        try:
            return download_kmz_kml(url)
        except Exception as e:
            self.log.warning("%s indisponible pour %s (%s): %s", label, name, url, e)
            return None

    # ---------- Cône de trajectoire ----------
    def _cone_events(self, s, name, klass, cone_kml: Optional[bytes]) -> List[CotEvent]:
        if cone_kml is None:
            self.log.info("Pas de cône disponible pour %s.", name)
            return []
        try:
            rings = extract_polygons(cone_kml)
        except Exception as e:
            self.log.warning("KML du cône illisible pour %s: %s", name, e)
            return []

        max_pts = int(self.params.get("cone_max_points", 80))
        storm_id = s.get("id", "unknown").lower()
        events = []
        for i, ring in enumerate(rings):
            ring = simplify_ring(ring, max_pts)
            events.append(CotEvent(
                uid=f"NHC-CONE-{storm_id}-{i}",
                cot_type="u-d-f",
                lat=ring[0][0], lon=ring[0][1],
                callsign=f"Cône {name}",
                remarks=f"Cône de trajectoire probable - {klass} {name}\nSource: NOAA/NHC",
                shape=ring,
                shape_closed=True,
                shape_style=CONE_STYLE,
                how="h-e",
            ))
        self.log.info("%d polygone(s) de cône pour %s.", len(events), name)
        return events

    # ---------- Ligne centrale ----------
    def _track_events(self, s, name, klass, cone_kml: Optional[bytes]) -> List[CotEvent]:
        # 1) KMZ dédié à la trajectoire s'il existe dans le flux
        track_url = (s.get("track") or {}).get("kmzFile")
        track_kml = self._load_kml(track_url, name, "Trajectoire")

        # 2) Sinon, repli sur les LineString du KMZ du cône
        lines: List = []
        for source_kml in (track_kml, cone_kml):
            if source_kml is None:
                continue
            try:
                lines = extract_linestrings(source_kml)
            except Exception as e:
                self.log.warning("KML de trajectoire illisible pour %s: %s", name, e)
                continue
            if lines:
                break

        if not lines:
            self.log.info("Pas de ligne centrale disponible pour %s.", name)
            return []

        max_pts = int(self.params.get("track_max_points", 60))
        storm_id = s.get("id", "unknown").lower()
        events = []
        for i, line in enumerate(lines):
            line = simplify_ring(line, max_pts)
            events.append(CotEvent(
                uid=f"NHC-TRACK-{storm_id}-{i}",
                cot_type="u-d-f",
                lat=line[0][0], lon=line[0][1],
                callsign=f"Trajectoire {name}",
                remarks=f"Trajectoire prévue (ligne centrale) - {klass} {name}\nSource: NOAA/NHC",
                shape=line,
                shape_closed=False,        # polyligne ouverte : pas de fermeture, pas de remplissage
                shape_style=TRACK_STYLE,
                how="h-e",
            ))
        self.log.info("%d ligne(s) centrale(s) pour %s.", len(events), name)
        return events

    def to_events(self, raw: Any) -> List[CotEvent]:
        include_cone = _as_bool(self.params.get("include_cone"), True)
        include_track = _as_bool(self.params.get("include_track"), True)

        events = []
        for s in raw.get("activeStorms", []):
            lat, lon = _f(s.get("latitudeNumeric")), _f(s.get("longitudeNumeric"))
            if lat is None or lon is None:
                self.log.warning("Position manquante pour %s, ignoré.", s.get("name"))
                continue

            name = s.get("name", "UNNAMED").title()
            klass = CLASSIFICATIONS.get(s.get("classification", ""), s.get("classification", "Storm"))

            events.append(self._storm_point(s, lat, lon, name, klass))

            # Un seul téléchargement du KMZ du cône, partagé par cône ET ligne centrale
            cone_kml = None
            if include_cone or include_track:
                cone_url = (s.get("trackCone") or {}).get("kmzFile")
                cone_kml = self._load_kml(cone_url, name, "Cône")

            if include_cone:
                events.extend(self._cone_events(s, name, klass, cone_kml))
            if include_track:
                events.extend(self._track_events(s, name, klass, cone_kml))
        return events