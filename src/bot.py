"""
Punto de entrada del bot de Telegram.
"""

from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

from config import TELEGRAM_BOT_TOKEN
from handlers import (
    cancel_command,
    get_add_conversation_handler,
    get_delete_conversation_handler,
    get_edit_conversation_handler,
    help_command,
    menu_button_handler,
    recent_command,
    start_command,
)


def main() -> None:
    """
    Inicia y ejecuta el bot de Telegram en modo polling.
    """
    print("Iniciando Frank's Movie Tracker Bot...")

    # Construimos la aplicación con el token
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    # Registramos los flujos interactivos (ConversationHandlers tienen prioridad)
    app.add_handler(get_add_conversation_handler())
    app.add_handler(get_edit_conversation_handler())
    app.add_handler(get_delete_conversation_handler())

    # Registramos los comandos individuales
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("recent", recent_command))
    app.add_handler(CommandHandler("cancel", cancel_command))

    # Registramos el handler de botones auxiliares del menú (recent, help, cancel)
    app.add_handler(
        CallbackQueryHandler(menu_button_handler, pattern=r"^menu_(recent|help|cancel)$")
    )

    # Mensajes de texto libres (ej: "hola", "buenas") fuera de conversación responden como /start
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, start_command)
    )

    print("Bot en ejecución. Presiona Ctrl + C para detenerlo.")

    # Escucha activa de mensajes
    app.run_polling()


if __name__ == "__main__":
    main()
