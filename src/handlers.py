"""
Handlers del bot de Telegram.
"""

from telegram import Update
from telegram.ext import ContextTypes


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Responde al comando /start dando la bienvenida al usuario.
    """
    user_name = update.effective_user.first_name if update.effective_user else "cinéfilo"
    message = (
        f"¡Hola {user_name}! 👋🎬\n\n"
        "Bienvenido a **Frank's Movie Tracker**.\n\n"
        "Próximamente podrás registrar las películas que ves y consultar tu biblioteca.\n\n"
        "Usa /help para ver los comandos disponibles."
    )
    await update.message.reply_text(message, parse_mode="Markdown")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Muestra la lista de comandos disponibles.
    """
    message = (
        "📌 **Comandos disponibles:**\n\n"
        "/start - Iniciar el bot y ver bienvenida\n"
        "/help - Mostrar este mensaje de ayuda\n\n"
        "*(Los comandos interactivos /add y /recent los integraremos a continuación)*"
    )
    await update.message.reply_text(message, parse_mode="Markdown")
