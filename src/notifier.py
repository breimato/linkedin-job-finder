import asyncio

from loguru import logger
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup

from .config import Settings
from .scraper import JobPosting


def _job_message(job: JobPosting, preview_chars: int) -> str:
    remote_tag = " | Remote" if job["is_remote"] else ""
    salary = f"\n💰 {job['salary_str']}" if job["salary_str"] else ""
    lines = [
        f"🆕 <b>{job['title']}</b>",
        f"🏢 {job['company']} — {job['location']}{remote_tag}",
        f"📅 {job['date_posted']}{salary}",
        f"🔗 <a href=\"{job['job_url']}\">Ver oferta</a>",
    ]
    if preview_chars > 0 and job["description"]:
        preview = job["description"][:preview_chars].strip()
        if len(job["description"]) > preview_chars:
            preview += "..."
        lines.append(f"\n<i>{preview}</i>")
    return "\n".join(lines)


async def _send(token: str, chat_id: str, text: str, reply_markup=None) -> None:
    async with Bot(token) as bot:
        await bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode="HTML",
            reply_markup=reply_markup,
            disable_web_page_preview=True,
        )


def send_jobs(jobs: list[JobPosting], settings: Settings) -> None:
    tg = settings.notification.telegram
    if not tg.enabled or not settings.telegram_bot_token:
        return

    for job in jobs:
        text = _job_message(
            job,
            tg.description_chars if tg.include_description_preview else 0,
        )
        try:
            asyncio.run(_send(settings.telegram_bot_token, settings.telegram_chat_id, text))
        except Exception as exc:
            logger.error(f"Error enviando notificación Telegram para {job['job_id']}: {exc}")


def send_approval_request(job: JobPosting, settings: Settings) -> None:
    if not settings.telegram_bot_token:
        return
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Aplicar", callback_data=f"approve:{job['job_id']}"),
        InlineKeyboardButton("❌ Saltar", callback_data=f"reject:{job['job_id']}"),
    ]])
    text = (
        f"Easy Apply disponible:\n"
        f"<b>{job['title']}</b> en {job['company']}\n"
        f"🔗 <a href=\"{job['job_url']}\">Ver oferta</a>"
    )
    try:
        asyncio.run(_send(settings.telegram_bot_token, settings.telegram_chat_id, text, keyboard))
    except Exception as exc:
        logger.error(f"Error enviando solicitud de aprobación: {exc}")
