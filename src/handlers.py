"""
Handlers del bot de Telegram.
"""

from telegram import Update
from telegram.ext import ContextTypes

from database import get_recent_watches


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Responde al comando /start dando la bienvenida al usuario.
    """
    user_name = update.effective_user.first_name if update.effective_user else "cinéfilo"
    message = (
        f"¡Hola {user_name}! 👋🎬\n\n"
        "Bienvenido a **Frank's Movie Tracker**.\n\n"
        "Comandos disponibles:\n"
        "• /recent - Ver tus últimas películas vistas\n"
        "• /help - Ver información de ayuda\n\n"
        "*(El comando interactivo /add para registrar películas lo activaremos a continuación)*"
    )
    await update.message.reply_text(message, parse_mode="Markdown")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Muestra la lista de comandos disponibles.
    """
    message = (
        "📌 **Comandos disponibles:**\n\n"
        "/start - Iniciar el bot y ver bienvenida\n"
        "/recent - Ver tus últimas películas vistas\n"
        "/help - Mostrar este mensaje de ayuda"
    )
    await update.message.reply_text(message, parse_mode="Markdown")


async def recent_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Muestra las últimas películas registradas en SQLite.
    """
    recent = get_recent_watches(limit=5)

    if not recent:
        await update.message.reply_text("Aún no tienes películas registradas en tu historial.")
        return

    text = "🎬 **Tus últimas películas vistas:**\n\n"
    for item in recent:
        year = f" ({item['release_date'][:4]})" if item.get("release_date") else ""
        rewatch_badge = " 🔁 *(Rewatch)*" if item.get("rewatch") == 1 else ""

        text += (
            f"⭐ **{item['title']}**{year}{rewatch_badge}\n"
            f"👤 Director: {item.get('director') or 'Desconocido'}\n"
            f"📅 Vista el: `{item['watched_at']}` | Calificación: **{item['rating']}/10**\n"
        )
        if item.get("review"):
            text += f"💬 *\"{item['review']}\"*\n"
        text += "────────────────────\n"

    await update.message.reply_text(text, parse_mode="Markdown")
