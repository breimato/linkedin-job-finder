import sys
from pathlib import Path

from loguru import logger
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src import database
from src.auto_apply.apply_bot import apply_job
from src.config import load_settings

settings = load_settings()


def _authorized(update: Update) -> bool:
    return str(update.effective_user.id) == str(settings.telegram_chat_id)


async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not _authorized(update):
        return
    await update.message.reply_text(
        "Job Hunter activo.\n\n"
        "/status — estadísticas\n"
        "/pending — ofertas pendientes de aprobación"
    )


async def cmd_status(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not _authorized(update):
        return
    stats = database.get_stats()
    await update.message.reply_text(
        f"Ofertas vistas (total): {stats['total_seen']}\n"
        f"Vistas hoy: {stats['seen_today']}\n"
        f"Aplicadas (total): {stats['applied_total']}\n"
        f"Pendientes de aprobación: {stats['pending_review']}"
    )


async def cmd_pending(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not _authorized(update):
        return
    pending = database.get_pending_reviews()
    if not pending:
        await update.message.reply_text("No hay ofertas pendientes.")
        return
    for job in pending[:10]:
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ Aplicar", callback_data=f"approve:{job['job_id']}"),
            InlineKeyboardButton("❌ Saltar", callback_data=f"reject:{job['job_id']}"),
        ]])
        await update.message.reply_text(
            f"<b>{job['title']}</b> en {job['company']}\n"
            f"📍 {job['location']}\n"
            f"🔗 <a href=\"{job['job_url']}\">Ver oferta</a>",
            parse_mode="HTML",
            reply_markup=keyboard,
            disable_web_page_preview=True,
        )


async def handle_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not _authorized(update):
        return
    query = update.callback_query
    await query.answer()

    action, job_id = query.data.split(":", 1)
    job = database.get_job_by_id(job_id)
    if not job:
        await query.edit_message_text("Oferta no encontrada en la BD.")
        return

    if action == "reject":
        database.update_apply_status(job_id, "rejected")
        await query.edit_message_text(f"Saltado: {job['title']} en {job['company']}")
        return

    if action == "approve":
        database.update_apply_status(job_id, "approved")
        await query.edit_message_text(
            f"Aprobado — aplicando a <b>{job['title']}</b> en {job['company']}...",
            parse_mode="HTML",
        )
        try:
            result = await apply_job(job_id, settings)
            if result["success"]:
                database.update_apply_status(job_id, "applied")
                await ctx.bot.send_message(
                    settings.telegram_chat_id,
                    f"Aplicado a <b>{job['title']}</b> en {job['company']}",
                    parse_mode="HTML",
                )
            else:
                database.update_apply_status(job_id, "failed", result.get("error"))
                await ctx.bot.send_message(
                    settings.telegram_chat_id,
                    f"Error al aplicar a {job['title']}: {result.get('error')}",
                )
        except Exception as exc:
            database.update_apply_status(job_id, "failed", str(exc))
            await ctx.bot.send_message(
                settings.telegram_chat_id,
                f"Error inesperado al aplicar a {job['title']}: {exc}",
            )


def main() -> None:
    database.init_db()
    app = Application.builder().token(settings.telegram_bot_token).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("pending", cmd_pending))
    app.add_handler(CallbackQueryHandler(handle_callback))
    logger.info("Bot de aprobación iniciado, escuchando...")
    app.run_polling()


if __name__ == "__main__":
    main()
