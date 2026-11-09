import io
import re
import zipfile
import xml.etree.ElementTree as ET
from typing import List, Tuple

import requests

from .base import USER_AGENT

Ring = List[Tuple[float, float]]  # liste de (lat, lon)
_KML_NS = re.compile(r"^\{[^}]+\}")


def _local(tag: str) -> str:
    """Nom de balise sans namespace."""
    return _KML_NS.sub("", tag)


def download_kmz_kml(url: str, timeout: int = 20) -> bytes:
    """Télécharge un KMZ (ou KML brut) et retourne le contenu KML en octets."""
    r = requests.get(url, timeout=timeout, headers={"User-Agent": USER_AGENT})
    r.raise_for_status()
    data = r.content
    if data[:2] == b"PK":  # signature ZIP -> KMZ
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            kml_names = [n for n in zf.namelist() if n.lower().endswith(".kml")]
            if not kml_names:
                raise ValueError("Aucun fichier .kml dans l'archive KMZ")
            return zf.read(kml_names[0])
    return data


def _parse_coordinates(text: str) -> Ring:
    """Parse 'lon,lat[,alt] lon,lat[,alt] ...' -> [(lat, lon), ...]"""
    ring = []
    for token in text.split():
        parts = token.split(",")
        if len(parts) < 2:
            continue
        try:
            lon, lat = float(parts[0]), float(parts[1])
        except ValueError:
            continue
        ring.append((lat, lon))
    return ring


def extract_polygons(kml_bytes: bytes) -> List[Ring]:
    """Retourne les anneaux extérieurs de tous les <Polygon> du KML."""
    root = ET.fromstring(kml_bytes)
    rings = []
    for poly in root.iter():
        if _local(poly.tag) != "Polygon":
            continue
        for outer in poly.iter():
            if _local(outer.tag) == "outerBoundaryIs":
                for coords in outer.iter():
                    if _local(coords.tag) == "coordinates" and coords.text:
                        ring = _parse_coordinates(coords.text)
                        if len(ring) >= 3:
                            rings.append(ring)
    return rings


def extract_linestrings(kml_bytes: bytes) -> List[Ring]:
    """Retourne les coordonnées de tous les <LineString> du KML (lat, lon)."""
    root = ET.fromstring(kml_bytes)
    lines = []
    for elem in root.iter():
        if _local(elem.tag) != "LineString":
            continue
        for coords in elem.iter():
            if _local(coords.tag) == "coordinates" and coords.text:
                line = _parse_coordinates(coords.text)
                if len(line) >= 2:
                    lines.append(line)
    return lines



def simplify_ring(ring: Ring, max_points: int) -> Ring:
    """Décimation uniforme pour limiter la taille du message CoT."""
    if len(ring) <= max_points:
        return ring
    step = len(ring) / max_points
    simplified = [ring[int(i * step)] for i in range(max_points)]
    if simplified[-1] != ring[-1]:
        simplified.append(ring[-1])
    return simplified