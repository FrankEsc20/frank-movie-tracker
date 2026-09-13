"""
Punto de entrada del bot de Telegram.
"""

from telegram.ext import ApplicationBuilder, CallbackQueryHandler, CommandHandler

from config import TELEGRAM_BOT_TOKEN
from handlers import (
    cancel_command,
    get_add_conversation_handler,
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

    # Registramos el flujo interactivo de /add (incluye entry_point para botón menu_add)
    app.add_handler(get_add_conversation_handler())

    # Registramos los comandos individuales
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("recent", recent_command))
    app.add_handler(CommandHandler("cancel", cancel_command))

    # Registramos el handler de botones del menú (recent, help, cancel)
    app.add_handler(
        CallbackQueryHandler(menu_button_handler, pattern=r"^menu_(recent|help|cancel)$")
    )

    print("Bot en ejecución. Presiona Ctrl + C para detenerlo.")

    # Escucha activa de mensajes
    app.run_polling()


if __name__ == "__main__":
    main()
