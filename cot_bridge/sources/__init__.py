from typing import Dict, Type

from .base import BaseSource

_REGISTRY: Dict[str, Type[BaseSource]] = {}


def register(type_name: str):
    """Décorateur d'enregistrement d'une source dans le registre."""
    def decorator(cls: Type[BaseSource]):
        if type_name in _REGISTRY:
            raise ValueError(f"Type de source déjà enregistré: {type_name}")
        _REGISTRY[type_name] = cls
        return cls
    return decorator


def create_source(cfg) -> BaseSource:
    try:
        cls = _REGISTRY[cfg.type]
    except KeyError:
        raise ValueError(
            f"Type de source inconnu '{cfg.type}' (disponibles: {', '.join(sorted(_REGISTRY))})"
        )
    return cls(cfg)


# Importer les modules déclenche l'enregistrement via @register.
# Pour ajouter une source : créer le fichier et l'importer ici.
from . import nhc, usgs_quakes  # noqa: E402,F401