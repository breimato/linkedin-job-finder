import asyncio
import random

from loguru import logger


async def _delay() -> None:
    await asyncio.sleep(random.uniform(0.8, 2.5))


async def _get_label(page, element) -> str:
    try:
        el_id = await element.get_attribute("id")
        if el_id:
            label_el = await page.query_selector(f"label[for='{el_id}']")
            if label_el:
                return (await label_el.inner_text()).strip().lower()
        aria = await element.get_attribute("aria-label")
        if aria:
            return aria.strip().lower()
        placeholder = await element.get_attribute("placeholder")
        if placeholder:
            return placeholder.strip().lower()
    except Exception:
        pass
    return ""


def _match_answer(label: str, answers: dict) -> str | None:
    if not label:
        return None
    for key, value in answers.items():
        if key.startswith("_"):
            continue
        if key.lower() in label or label in key.lower():
            return str(value)
    return None


async def handle_step(page, answers: dict) -> str:
    """
    Procesa el paso actual del modal de Easy Apply.
    Devuelve: 'next' | 'submit' | 'unknown'
    """
    await _delay()

    # Subida de CV
    file_inputs = await page.query_selector_all("input[type='file']")
    cv_path = answers.get("_cv_path", "")
    for fi in file_inputs:
        if cv_path:
            try:
                await fi.set_input_files(cv_path)
                logger.info("CV subido")
            except Exception as exc:
                logger.warning(f"No se pudo subir el CV: {exc}")

    # Inputs de texto
    inputs = await page.query_selector_all(
        "input[type='text'], input[type='tel'], input[type='number'], textarea"
    )
    for inp in inputs:
        label = await _get_label(page, inp)
        value = _match_answer(label, answers)
        if value is not None:
            try:
                await inp.click()
                await inp.fill("")
                await inp.type(value, delay=random.randint(50, 150))
            except Exception as exc:
                logger.debug(f"No se pudo rellenar campo '{label}': {exc}")

    # Dropdowns
    selects = await page.query_selector_all("select")
    for sel in selects:
        label = await _get_label(page, sel)
        value = _match_answer(label, answers)
        if value is not None:
            try:
                await sel.select_option(label=value)
            except Exception:
                try:
                    await sel.select_option(value=value)
                except Exception as exc:
                    logger.debug(f"No se pudo seleccionar opción en '{label}': {exc}")

    # Botón de acción
    submit_btn = await page.query_selector("button[aria-label*='Submit']")
    if submit_btn:
        return "submit"

    next_btn = await page.query_selector(
        "button[aria-label*='Continue'], "
        "button[aria-label*='Next'], "
        "button[aria-label*='Review'], "
        "button[aria-label*='Siguiente'], "
        "button[aria-label*='Continuar']"
    )
    if next_btn:
        await next_btn.click()
        return "next"

    return "unknown"
