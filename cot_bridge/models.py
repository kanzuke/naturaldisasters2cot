from dataclasses import dataclass, field
from typing import List, Optional, Tuple


def _argb(a: int, r: int, g: int, b: int) -> int:
    """Convertit ARGB en entier signé 32 bits attendu par ATAK."""
    v = (a << 24) | (r << 16) | (g << 8) | b
    return v - (1 << 32) if v & 0x80000000 else v


@dataclass
class ShapeStyle:
    stroke_argb: int = _argb(255, 255, 0, 0)    # rouge opaque
    fill_argb: int = _argb(64, 255, 0, 0)       # rouge ~25 %
    stroke_weight: float = 3.0



@dataclass
class CotEvent:
    """Représentation neutre d'un événement, indépendante de la source et du XML."""
    uid: str
    cot_type: str
    lat: float
    lon: float
    callsign: str = ""
    remarks: str = ""
    hae: float = 0.0
    ce: float = 9999999.0
    le: float = 9999999.0
    course: Optional[float] = None
    speed: Optional[float] = None
    stale_seconds: Optional[int] = None
    how: str = "m-g"
    extra_detail: dict = field(default_factory=dict)

    # --- Nouveau : forme géométrique optionnelle ---
    # Liste de sommets (lat, lon). Si renseignée, l'événement est une forme.
    shape: Optional[List[Tuple[float, float]]] = None
    shape_closed: bool = True            # True = polygone, False = polyligne ouverte
    shape_style: Optional[ShapeStyle] = None