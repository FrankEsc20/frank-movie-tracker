"""
Handlers del bot de Telegram.
"""

from datetime import date, datetime

from telegram import Update
from telegram.ext import (
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from database import get_recent_watches, save_movie, save_watch_history
from models import Movie, WatchHistory
from tmdb import get_movie_details, search_movies


# Estados de la conversación para el comando /add
(
    WAITING_TITLE,
    WAITING_SELECTION,
    WAITING_DATE,
    WAITING_RATING,
    WAITING_REVIEW,
    WAITING_REWATCH,
    WAITING_CONFIRMATION,
) = range(7)


def escape_markdown(text: str) -> str:
    """
    Escapa caracteres especiales de Markdown v1 para evitar errores de parseo.
    """
    if not text:
        return ""
    for char in ("_", "*", "`", "["):
        text = text.replace(char, f"\\{char}")
    return text


def parse_date_input(text: str) -> date | None:
    """
    Parsea una fecha introducida por el usuario ('hoy', 'DD/MM/AAAA' o 'AAAA-MM-DD').
    """
    text = text.strip().lower()
    if text in ("hoy", "today"):
        return date.today()

    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue

    return None


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Responde al comando /start dando la bienvenida al usuario.
    """
    user_name = update.effective_user.first_name if update.effective_user else "cinéfilo"
    message = (
        f"¡Hola {user_name}! 👋🎬\n\n"
        "Bienvenido a *Frank's Movie Tracker*.\n\n"
        "Comandos disponibles:\n"
        "• /add - Registrar una película que viste\n"
        "• /recent - Ver tus últimas películas vistas\n"
        "• /help - Ver información de ayuda"
    )
    await update.message.reply_text(message, parse_mode="Markdown")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Muestra la lista de comandos disponibles.
    """
    message = (
        "📌 *Comandos disponibles:*\n\n"
        "/add - Registrar una nueva película vista\n"
        "/recent - Ver tus últimas películas vistas\n"
        "/cancel - Cancelar la operación en curso\n"
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

    text = "🎬 *Tus últimas películas vistas:*\n\n"
    for item in recent:
        year = f" ({item['release_date'][:4]})" if item.get("release_date") else ""
        rewatch_badge = " 🔁 *(Rewatch)*" if item.get("rewatch") == 1 else ""

        text += (
            f"⭐ *{item['title']}*{year}{rewatch_badge}\n"
            f"👤 Director: {item.get('director') or 'Desconocido'}\n"
            f"📅 Vista el: `{item['watched_at']}` | Calificación: *{item['rating']}/10*\n"
        )
        if item.get("review"):
            text += f"💬 *\"{item['review']}\"*\n"
        text += "────────────────────\n"

    await update.message.reply_text(text, parse_mode="Markdown")


# --- Flujo de conversación de /add ---

async def add_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Punto de entrada de /add: solicita el título de la película.
    """
    context.user_data.clear()
    await update.message.reply_text(
        "🎬 *Registrar película*\n\n"
        "¿Qué película viste? Escribe su título para buscarla (o /cancel para salir):",
        parse_mode="Markdown",
    )
    return WAITING_TITLE


async def add_receive_title(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Busca la película en TMDB y presenta hasta 5 opciones.
    """
    query = update.message.text.strip()
    results = search_movies(query)

    if not results:
        await update.message.reply_text(
            f"❌ No encontré películas con el título '{query}'.\n"
            "Intenta con otro nombre o escribe /cancel para salir:"
        )
        return WAITING_TITLE

    # Guardamos hasta 5 resultados en memoria temporal
    top_results = results[:5]
    context.user_data["search_results"] = top_results

    text = "🔍 *Encontré los siguientes resultados:*\n\n"
    for i, item in enumerate(top_results, start=1):
        year = item.get("release_date", "")[:4]
        year_str = f" ({year})" if year else ""
        text += f"*{i}.* {item.get('title', 'Sin título')}{year_str}\n"

    text += f"\n¿Cuál quieres registrar? Escribe el número del *1 al {len(top_results)}* (o /cancel):"
    await update.message.reply_text(text, parse_mode="Markdown")
    return WAITING_SELECTION


async def add_receive_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Procesa el número elegido, descarga la información completa de TMDB y pide la fecha.
    """
    text = update.message.text.strip()
    search_results = context.user_data.get("search_results", [])

    if not text.isdigit() or not (1 <= int(text) <= len(search_results)):
        await update.message.reply_text(
            f"⚠️ Por favor ingresa un número válido del 1 al {len(search_results)} (o /cancel):"
        )
        return WAITING_SELECTION

    choice = int(text) - 1
    selected_raw = search_results[choice]

    # Obtenemos metadata completa desde TMDB y la transformamos a nuestro modelo
    details = get_movie_details(selected_raw["id"])
    movie = Movie.from_tmdb(details)
    context.user_data["movie"] = movie

    year = f" ({movie.release_date.year})" if movie.release_date else ""
    await update.message.reply_text(
        f"Seleccionaste: *{movie.title}*{year}\n\n"
        "📅 ¿Cuándo la viste?\n"
        "Puedes escribir la fecha como `12/09/2026`, `2026-09-12` o simplemente escribir *hoy*:",
        parse_mode="Markdown",
    )
    return WAITING_DATE


async def add_receive_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Valida la fecha y solicita la calificación.
    """
    text = update.message.text.strip()
    parsed_date = parse_date_input(text)

    if not parsed_date:
        await update.message.reply_text(
            "⚠️ Formato no reconocido. Escribe la fecha en formato `DD/MM/AAAA` (ej: 12/09/2026) o escribe *hoy*:",
            parse_mode="Markdown",
        )
        return WAITING_DATE

    context.user_data["watched_at"] = parsed_date
    await update.message.reply_text(
        "⭐ ¿Qué calificación le das del 0 al 10?\n"
        "(Puedes usar decimales, por ejemplo: `9.5` u `8`):",
        parse_mode="Markdown",
    )
    return WAITING_RATING


async def add_receive_rating(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Valida la calificación y pide el comentario/reseña.
    """
    text = update.message.text.strip().replace(",", ".")

    try:
        rating = float(text)
        if not (0.0 <= rating <= 10.0):
            raise ValueError()
    except ValueError:
        await update.message.reply_text(
            "⚠️ Por favor ingresa una calificación válida entre 0 y 10 (ej: 8 o 9.5):"
        )
        return WAITING_RATING

    context.user_data["rating"] = round(rating, 1)
    await update.message.reply_text(
        "💬 ¿Quieres agregar un comentario o reseña?\n"
        "(Escribe tu comentario o responde *no* para omitir):",
        parse_mode="Markdown",
    )
    return WAITING_REVIEW


async def add_receive_review(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Almacena el comentario y pregunta si fue un rewatch.
    """
    text = update.message.text.strip()

    if text.lower() in ("no", "ninguno", "ninguna", "-", "omitir"):
        context.user_data["review"] = None
    else:
        context.user_data["review"] = text

    await update.message.reply_text(
        "🔁 ¿Fue un rewatch? (¿Ya la habías visto antes?)\n"
        "Responde *si* o *no*:",
        parse_mode="Markdown",
    )
    return WAITING_REWATCH


async def add_receive_rewatch(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Registra el rewatch y presenta la ficha resumen para confirmación.
    """
    text = update.message.text.strip().lower()
    rewatch = 1 if text in ("si", "sí", "s", "yes", "1") else 0
    context.user_data["rewatch"] = rewatch

    movie: Movie = context.user_data["movie"]
    watched_at: date = context.user_data["watched_at"]
    rating: float = context.user_data["rating"]
    review: str | None = context.user_data["review"]

    rewatch_str = "Sí" if rewatch == 1 else "No"
    review_str = f'"{escape_markdown(review)}"' if review else "Sin comentario"

    summary = (
        "📋 *Resumen del registro:*\n\n"
        f"🎬 *Película:* {escape_markdown(movie.title)}\n"
        f"👤 *Director:* {escape_markdown(movie.director or 'N/A')}\n"
        f"📅 *Fecha:* `{watched_at.strftime('%d/%m/%Y')}`\n"
        f"⭐ *Calificación:* {rating}/10\n"
        f"🔁 *Rewatch:* {rewatch_str}\n"
        f"💬 *Comentario:* {review_str}\n\n"
        "¿Deseas guardar este registro? (Responde *si* o *no*, o escribe /cancel):"
    )

    await update.message.reply_text(summary, parse_mode="Markdown")
    return WAITING_CONFIRMATION


async def add_receive_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Persiste en SQLite si el usuario confirma.
    """
    text = update.message.text.strip().lower()

    if text in ("si", "sí", "s", "yes", "guardar", "confirmar"):
        movie: Movie = context.user_data["movie"]
        watched_at: date = context.user_data["watched_at"]
        rating: float = context.user_data["rating"]
        review: str | None = context.user_data["review"]
        rewatch: int = context.user_data["rewatch"]

        # 1. Guarda la película (o recupera la existente si ya estaba registrada)
        saved_movie = save_movie(movie)

        # 2. Guarda el registro de visualización
        watch = WatchHistory(
            movie_id=saved_movie.id,
            watched_at=watched_at,
            rating=rating,
            review=review,
            rewatch=rewatch,
        )
        save_watch_history(watch)

        await update.message.reply_text(
            f"✅ *¡{escape_markdown(saved_movie.title)} guardada exitosamente!*\n\n"
            "Puedes consultarla en cualquier momento con /recent.",
            parse_mode="Markdown",
        )
    else:
        await update.message.reply_text("❌ Registro cancelado. No se guardaron cambios.")

    context.user_data.clear()
    return ConversationHandler.END


async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Cancela la conversación en curso.
    """
    context.user_data.clear()
    await update.message.reply_text("❌ Operación cancelada.", parse_mode="Markdown")
    return ConversationHandler.END


def get_add_conversation_handler() -> ConversationHandler:
    """
    Construye el ConversationHandler para el comando /add.
    """
    return ConversationHandler(
        entry_points=[CommandHandler("add", add_start)],
        states={
            WAITING_TITLE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_receive_title)
            ],
            WAITING_SELECTION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_receive_selection)
            ],
            WAITING_DATE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_receive_date)
            ],
            WAITING_RATING: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_receive_rating)
            ],
            WAITING_REVIEW: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_receive_review)
            ],
            WAITING_REWATCH: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_receive_rewatch)
            ],
            WAITING_CONFIRMATION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_receive_confirmation)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel_command)],
    )
