import logging
import socket
import ssl

log = logging.getLogger(__name__)


def _tls_context(cot: dict) -> ssl.SSLContext:
    ctx = ssl.create_default_context(cafile=cot["cafile"])
    if cot["certfile"]:
        ctx.load_cert_chain(cot["certfile"], cot["keyfile"])
    if not cot["verify"]:
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    return ctx


def send(cot: dict, payloads: list) -> bool:
    """Envoie une liste de messages XML au serveur CoT. Retourne True si OK."""
    if not payloads:
        return True
    ip, port, proto = cot["ip"], cot["port"], cot["protocol"]
    try:
        if proto == "udp":
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                for p in payloads:
                    s.sendto(p.encode("utf-8"), (ip, port))
            log.info("%d message(s) CoT envoyé(s) en UDP.", len(payloads))
            return True

        if proto not in ("tcp", "raw"):
            log.error("Protocole non supporté: %s", proto)
            return False

        with socket.create_connection((ip, port), timeout=10) as raw:
            sock = _tls_context(cot).wrap_socket(raw, server_hostname=ip) if cot["tls"] else raw
            try:
                for p in payloads:
                    sock.sendall(p.encode("utf-8"))
            finally:
                if sock is not raw:
                    sock.close()
        log.info("%d message(s) CoT envoyé(s) en TCP%s.", len(payloads), "+TLS" if cot["tls"] else "")
        return True

    except ConnectionRefusedError:
        log.error("Connexion refusée par %s:%s (serveur TAK démarré ?)", ip, port)
    except socket.timeout:
        log.error("Délai de connexion dépassé vers %s:%s", ip, port)
    except ssl.SSLError as e:
        log.error("Erreur TLS: %s", e)
    except OSError as e:
        log.error("Erreur socket: %s", e)
    return False