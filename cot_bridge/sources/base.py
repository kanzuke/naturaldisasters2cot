import logging
from abc import ABC, abstractmethod
from typing import Any, List

import requests

from ..config import SourceConfig
from ..models import CotEvent

USER_AGENT = "storm-cot-bridge/2.0"


class BaseSource(ABC):
    """Contrat commun à toutes les sources.

    Pour créer une source :
      1. hériter de BaseSource
      2. décorer avec @register("nom_du_type")
      3. implémenter fetch() et to_events()
    """

    def __init__(self, cfg: SourceConfig):
        self.cfg = cfg
        self.name = cfg.name
        self.params = cfg.params
        self.log = logging.getLogger(f"source.{cfg.name}")

    # --- à implémenter ---
    @abstractmethod
    def fetch(self) -> Any:
        """Récupère les données brutes. Doit lever une exception en cas d'échec."""

    @abstractmethod
    def to_events(self, raw: Any) -> List[CotEvent]:
        """Convertit les données brutes en CotEvent."""

    # --- utilitaires partagés ---
    def http_get_json(self, url: str, **kwargs) -> Any:
        r = requests.get(url, timeout=kwargs.pop("timeout", 15),
                         headers={"User-Agent": USER_AGENT}, **kwargs)
        r.raise_for_status()
        return r.json()

    def require(self, key: str) -> str:
        if key not in self.params:
            raise ValueError(f"[Source:{self.name}] paramètre requis manquant: '{key}'")
        return self.params[key]

    # --- appelé par le scheduler ---
    def run(self) -> List[CotEvent]:
        raw = self.fetch()
        return self.to_events(raw)