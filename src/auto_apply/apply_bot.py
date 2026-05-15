import asyncio
import random
from pathlib import Path

from loguru import logger

from .. import database
from ..config import Settings
from . import form_filler, session_manager

MAX_FORM_STEPS = 12


async def apply_job(job_id: str, settings: Settings) -> dict:
    if not settings.auto_apply.enabled:
        return {"success": False, "error": "Auto-apply desactivado"}

    daily = database.count_applied_today()
    cap = settings.auto_apply.linkedin.max_applications_per_day
    if daily >= cap:
        return {"success": False, "error": f"Límite diario alcanzado ({daily}/{cap})"}

    job = database.get_job_by_id(job_id)
    if not job:
        return {"success": False, "error": "Trabajo no encontrado en BD"}

    answers = dict(settings.auto_apply.cv.answers)
    answers["_cv_path"] = str(Path(settings.auto_apply.cv.pdf_path).resolve())

    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser, context, page = await session_manager.get_context(p, settings)
        try:
            logger.info(f"Aplicando a: {job['title']} en {job['company']}")
            await page.goto(job["job_url"], timeout=20000, wait_until="domcontentloaded")
            await asyncio.sleep(random.uniform(1.5, 3.0))

            easy_btn = await page.query_selector(".jobs-apply-button")
            if not easy_btn:
                return {"success": False, "error": "Botón Easy Apply no encontrado en la página"}

            await easy_btn.click()
            await asyncio.sleep(random.uniform(1.0, 2.0))

            for step_num in range(MAX_FORM_STEPS):
                result = await form_filler.handle_step(page, answers)
                logger.info(f"Paso {step_num + 1}: {result}")

                if result == "submit":
                    submit_btn = await page.query_selector("button[aria-label*='Submit']")
                    if submit_btn:
                        await submit_btn.click()
                        await asyncio.sleep(2.5)
                        content = await page.content()
                        if "application submitted" in content.lower() or "solicitud enviada" in content.lower():
                            logger.info(f"Aplicación enviada: {job['title']} en {job['company']}")
                            return {"success": True}
                        # Buscar confirmación visual alternativa
                        confirm = await page.query_selector(".artdeco-inline-feedback--success")
                        if confirm:
                            return {"success": True}
                        return {"success": False, "error": "Submit pulsado pero sin confirmación visible"}
                    break

                if result == "unknown":
                    logger.warning(f"Paso {step_num + 1} desconocido — abortando")
                    break

            return {"success": False, "error": "No se llegó al botón de envío"}

        except Exception as exc:
            logger.error(f"Error en flujo de apply: {exc}")
            return {"success": False, "error": str(exc)}

        finally:
            await session_manager.save_state(context)
            await browser.close()
