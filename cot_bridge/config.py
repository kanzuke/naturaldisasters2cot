import configparser
import logging
from dataclasses import dataclass, field

log = logging.getLogger(__name__)


@dataclass
class SourceConfig:
    name: str
    type: str
    enabled: bool
    interval: int
    params: dict = field(default_factory=dict)  # tout le reste (url, clés API, bbox...)


@dataclass
class AppConfig:
    cot: dict
    default_interval: int
    sources: list


def load_config(path: str = "config.ini") -> AppConfig:
    parser = configparser.ConfigParser()
    if not parser.read(path):
        raise FileNotFoundError(f"Fichier de configuration introuvable: {path}")

    try:
        cot = {
            "ip": parser.get("COT", "COT_IP"),
            "port": parser.getint("COT", "COT_PORT"),
            "protocol": parser.get("COT", "COT_PROTOCOL").lower(),
            "tls": parser.getboolean("COT", "COT_TLS", fallback=False),
            "certfile": parser.get("COT", "COT_CERTFILE", fallback="") or None,
            "keyfile": parser.get("COT", "COT_KEYFILE", fallback="") or None,
            "cafile": parser.get("COT", "COT_CAFILE", fallback="") or None,
            "verify": parser.getboolean("COT", "COT_VERIFY", fallback=True),
        }
        default_interval = parser.getint("Scheduler", "POLLING_INTERVAL")
    except (configparser.Error, ValueError) as e:
        raise ValueError(f"Configuration invalide: {e}")

    sources = []
    for section in parser.sections():
        if not section.startswith("Source:"):
            continue
        name = section.split(":", 1)[1]
        s = parser[section]
        if "type" not in s:
            raise ValueError(f"[{section}] : clé 'type' manquante")
        reserved = {"type", "enabled", "interval"}
        sources.append(SourceConfig(
            name=name,
            type=s["type"],
            enabled=s.getboolean("enabled", fallback=True),
            interval=s.getint("interval", fallback=default_interval),
            params={k: v for k, v in s.items() if k not in reserved},
        ))
    return AppConfig(cot=cot, default_interval=default_interval, sources=sources)