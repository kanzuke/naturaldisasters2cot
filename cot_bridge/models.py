from dataclasses import dataclass, field
from typing import Optional


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
    course: Optional[float] = None       # degrés
    speed: Optional[float] = None        # m/s
    stale_seconds: Optional[int] = None  # None -> défaut calculé par le scheduler
    how: str = "m-g"
    extra_detail: dict = field(default_factory=dict)  # {tag: {attrs}} pour balises <detail> custom