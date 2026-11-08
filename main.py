import logging
import time

from cot_bridge.config import load_config
from cot_bridge.cot import event_to_xml
from cot_bridge.sources import create_source
from cot_bridge.transport import send

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(name)s - %(message)s")
log = logging.getLogger("main")


def main():
    try:
        config = load_config()
    except (FileNotFoundError, ValueError) as e:
        log.critical("Échec de l'initialisation: %s", e)
        return

    # Instanciation des sources activées (une source mal configurée n'empêche pas les autres)
    sources = []
    for sc in config.sources:
        if not sc.enabled:
            log.info("Source '%s' désactivée.", sc.name)
            continue
        try:
            sources.append((create_source(sc), sc.interval))
            log.info("Source '%s' (type=%s, intervalle=%ds) chargée.", sc.name, sc.type, sc.interval)
        except ValueError as e:
            log.error("Source '%s' ignorée: %s", sc.name, e)

    if not sources:
        log.critical("Aucune source active. Arrêt.")
        return

    # Prochaine exécution planifiée pour chaque source
    next_run = {src.name: 0.0 for src, _ in sources}

    log.info("Démarrage de la boucle de scrutation.")
    while True:
        try:
            now = time.time()
            for src, interval in sources:
                if now < next_run[src.name]:
                    continue
                next_run[src.name] = now + interval
                try:
                    log.info("--- Cycle source '%s' ---", src.name)
                    events = src.run()
                    if not events:
                        log.info("[%s] Aucun événement actif.", src.name)
                        continue
                    payloads = [event_to_xml(e, default_stale_seconds=interval * 2) for e in events]
                    send(config.cot, payloads)
                except Exception:
                    # Isolation : l'échec d'une source ne bloque pas les autres
                    log.exception("[%s] Erreur durant le cycle", src.name)

            sleep_for = max(1.0, min(next_run.values()) - time.time())
            time.sleep(min(sleep_for, 30))

        except KeyboardInterrupt:
            log.info("Arrêt demandé par l'utilisateur.")
            break


if __name__ == "__main__":
    main()