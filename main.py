import sys
from pathlib import Path
from loguru import logger
from src.config import load_settings
from src import database, scraper, notifier


def setup_logging(settings) -> None:
    logger.remove()
    logger.add(sys.stderr, level=settings.logging.level)
    Path(settings.logging.file).parent.mkdir(exist_ok=True)
    logger.add(
        settings.logging.file,
        level=settings.logging.level,
        rotation=settings.logging.rotation,
        retention=settings.logging.retention,
    )


def main() -> None:
    settings = load_settings()
    setup_logging(settings)
    database.init_db()

    logger.info("Iniciando escaneo de LinkedIn...")
    jobs = scraper.fetch_jobs(settings)
    logger.info(f"Obtenidos {len(jobs)} trabajos de LinkedIn")

    new_jobs = database.filter_new(jobs)
    logger.info(f"{len(new_jobs)} trabajos nuevos encontrados")

    if not new_jobs:
        logger.info("Sin trabajos nuevos. Saliendo.")
        return

    database.mark_seen(new_jobs)
    notifier.send_jobs(new_jobs, settings)
    database.mark_notified([j["job_id"] for j in new_jobs])

    if settings.auto_apply.enabled:
        easy_apply_jobs = [j for j in new_jobs if j["easy_apply"]]
        for job in easy_apply_jobs:
            database.queue_for_review(job["job_id"])
            notifier.send_approval_request(job, settings)
        if easy_apply_jobs:
            logger.info(f"{len(easy_apply_jobs)} trabajos en cola para revisión de Easy Apply")

    logger.info("Escaneo completado.")


if __name__ == "__main__":
    main()
