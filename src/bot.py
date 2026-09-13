"""
Punto de entrada del bot de Telegram.
"""

from telegram.ext import ApplicationBuilder, CommandHandler

from config import TELEGRAM_BOT_TOKEN
from handlers import help_command, recent_command, start_command


def main() -> None:
    """
    Inicia y ejecuta el bot de Telegram en modo polling.
    """
    print("Iniciando Frank's Movie Tracker Bot...")

    # Construimos la aplicación con el token
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    # Registramos los comandos disponibles
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("recent", recent_command))

    print("Bot en ejecución. Presiona Ctrl + C para detenerlo.")

    # Escucha activa de mensajes
    app.run_polling()


if __name__ == "__main__":
    main()
