"""
Handlers del bot de Telegram.
"""

from datetime import date, datetime

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    CallbackQueryHandler,
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


# --- Teclados reutilizables ---


def _main_menu_keyboard() -> InlineKeyboardMarkup:
    """Teclado con los comandos principales del bot."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎬 Registrar película", callback_data="menu_add")],
        [InlineKeyboardButton("🕐 Películas recientes", callback_data="menu_recent")],
        [InlineKeyboardButton("❓ Ayuda", callback_data="menu_help")],
    ])


def _date_keyboard() -> InlineKeyboardMarkup:
    """Teclado con la opción rápida 'Hoy' para la fecha."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📅 Hoy", callback_data="date_today")],
    ])


def _review_keyboard() -> InlineKeyboardMarkup:
    """Teclado con la opción de omitir el comentario."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⏭️ Omitir", callback_data="review_skip")],
    ])


def _rewatch_keyboard() -> InlineKeyboardMarkup:
    """Teclado Sí/No para rewatch."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Sí", callback_data="rewatch_yes"),
            InlineKeyboardButton("❌ No", callback_data="rewatch_no"),
        ]
    ])


def _confirmation_keyboard() -> InlineKeyboardMarkup:
    """Teclado Guardar/Cancelar para confirmación final."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Guardar", callback_data="confirm_yes"),
            InlineKeyboardButton("❌ Cancelar", callback_data="confirm_no"),
        ]
    ])


def _format_recent_text(recent: list[dict]) -> str:
    """Construye el texto formateado de películas recientes."""
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
    return text


# --- Comandos principales ---


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Responde al comando /start dando la bienvenida al usuario.
    """
    user_name = update.effective_user.first_name if update.effective_user else "cinéfilo"
    message = (
        f"¡Hola {user_name}! 👋🎬\n\n"
        "Bienvenido a *Frank's Movie Tracker*.\n\n"
        "¿Qué quieres hacer?"
    )
    await update.message.reply_text(
        message, parse_mode="Markdown", reply_markup=_main_menu_keyboard()
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Muestra la lista de comandos disponibles con botones.
    """
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎬 Registrar película", callback_data="menu_add")],
        [InlineKeyboardButton("🕐 Películas recientes", callback_data="menu_recent")],
        [InlineKeyboardButton("❌ Cancelar operación", callback_data="menu_cancel")],
        [InlineKeyboardButton("❓ Ayuda", callback_data="menu_help")],
    ])
    await update.message.reply_text(
        "📌 *Comandos disponibles:*",
        parse_mode="Markdown",
        reply_markup=keyboard,
    )


async def recent_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Muestra las últimas películas registradas en SQLite.
    """
    recent = get_recent_watches(limit=5)

    if not recent:
        await update.message.reply_text("Aún no tienes películas registradas en tu historial.")
        return

    await update.message.reply_text(_format_recent_text(recent), parse_mode="Markdown")


async def menu_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Maneja los botones del menú principal que NO inician la conversación de /add.
    """
    query = update.callback_query
    await query.answer()

    if query.data == "menu_recent":
        recent = get_recent_watches(limit=5)
        if not recent:
            await query.edit_message_text(
                "Aún no tienes películas registradas en tu historial."
            )
            return
        await query.edit_message_text(
            _format_recent_text(recent), parse_mode="Markdown"
        )

    elif query.data == "menu_help":
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🎬 Registrar película", callback_data="menu_add")],
            [InlineKeyboardButton("🕐 Películas recientes", callback_data="menu_recent")],
            [InlineKeyboardButton("❌ Cancelar operación", callback_data="menu_cancel")],
            [InlineKeyboardButton("❓ Ayuda", callback_data="menu_help")],
        ])
        await query.edit_message_text(
            "📌 *Comandos disponibles:*",
            parse_mode="Markdown",
            reply_markup=keyboard,
        )

    elif query.data == "menu_cancel":
        context.user_data.clear()
        await query.edit_message_text("❌ Operación cancelada.")


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


async def add_start_from_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Punto de entrada alternativo de /add desde un botón inline del menú.
    """
    query = update.callback_query
    await query.answer()
    context.user_data.clear()
    await query.edit_message_text(
        "🎬 *Registrar película*\n\n"
        "¿Qué película viste? Escribe su título para buscarla (o /cancel para salir):",
        parse_mode="Markdown",
    )
    return WAITING_TITLE


async def add_receive_title(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Busca la película en TMDB y presenta hasta 5 opciones como botones inline.
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

    # Construimos un botón por cada resultado
    keyboard = []
    for i, item in enumerate(top_results):
        year = item.get("release_date", "")[:4]
        year_str = f" ({year})" if year else ""
        label = f"{item.get('title', 'Sin título')}{year_str}"
        keyboard.append([InlineKeyboardButton(label, callback_data=str(i))])

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "🔍 *Encontré los siguientes resultados:*\n\n"
        "Selecciona la película que quieres registrar:",
        parse_mode="Markdown",
        reply_markup=reply_markup,
    )
    return WAITING_SELECTION


async def add_receive_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Procesa la selección del botón inline, descarga la información completa de TMDB y pide la fecha.
    """
    query = update.callback_query
    await query.answer()

    search_results = context.user_data.get("search_results", [])
    choice = int(query.data)
    selected_raw = search_results[choice]

    # Obtenemos metadata completa desde TMDB y la transformamos a nuestro modelo
    details = get_movie_details(selected_raw["id"])
    movie = Movie.from_tmdb(details)
    context.user_data["movie"] = movie

    year = f" ({movie.release_date.year})" if movie.release_date else ""

    # Editamos el mensaje original para mostrar la selección y eliminar los botones
    await query.edit_message_text(
        f"✅ Seleccionaste: *{escape_markdown(movie.title)}*{year}",
        parse_mode="Markdown",
    )

    # Enviamos la pregunta de la fecha con el botón "Hoy"
    await query.message.reply_text(
        "📅 ¿Cuándo la viste?\n"
        "Puedes escribir la fecha como `12/09/2026`, `2026-09-12` o usar el botón:",
        parse_mode="Markdown",
        reply_markup=_date_keyboard(),
    )
    return WAITING_DATE


async def add_receive_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Valida la fecha ingresada como texto y solicita la calificación.
    """
    text = update.message.text.strip()
    parsed_date = parse_date_input(text)

    if not parsed_date:
        await update.message.reply_text(
            "⚠️ Formato no reconocido. Escribe la fecha en formato `DD/MM/AAAA` (ej: 12/09/2026) o usa el botón:",
            parse_mode="Markdown",
            reply_markup=_date_keyboard(),
        )
        return WAITING_DATE

    context.user_data["watched_at"] = parsed_date
    await update.message.reply_text(
        "⭐ ¿Qué calificación le das del 0 al 10?\n"
        "(Puedes usar decimales, por ejemplo: `9.5` u `8`):",
        parse_mode="Markdown",
    )
    return WAITING_RATING


async def add_receive_date_today(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Maneja el botón 'Hoy' para la fecha.
    """
    query = update.callback_query
    await query.answer()

    today = date.today()
    context.user_data["watched_at"] = today

    await query.edit_message_text(
        f"📅 Fecha seleccionada: *{today.strftime('%d/%m/%Y')}*",
        parse_mode="Markdown",
    )

    await query.message.reply_text(
        "⭐ ¿Qué calificación le das del 0 al 10?\n"
        "(Puedes usar decimales, por ejemplo: `9.5` u `8`):",
        parse_mode="Markdown",
    )
    return WAITING_RATING


async def add_receive_rating(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Valida la calificación y pide el comentario/reseña con botón de omitir.
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
        "(Escribe tu comentario o usa el botón para omitir):",
        parse_mode="Markdown",
        reply_markup=_review_keyboard(),
    )
    return WAITING_REVIEW


async def add_receive_review(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Almacena el comentario escrito por el usuario y pregunta si fue un rewatch.
    """
    text = update.message.text.strip()

    if text.lower() in ("no", "ninguno", "ninguna", "-", "omitir"):
        context.user_data["review"] = None
    else:
        context.user_data["review"] = text

    await update.message.reply_text(
        "🔁 ¿Fue un rewatch? (¿Ya la habías visto antes?)",
        parse_mode="Markdown",
        reply_markup=_rewatch_keyboard(),
    )
    return WAITING_REWATCH


async def add_receive_review_skip(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Maneja el botón 'Omitir' para el comentario.
    """
    query = update.callback_query
    await query.answer()

    context.user_data["review"] = None

    await query.edit_message_text(
        "💬 Comentario: *Omitido*", parse_mode="Markdown"
    )

    await query.message.reply_text(
        "🔁 ¿Fue un rewatch? (¿Ya la habías visto antes?)",
        parse_mode="Markdown",
        reply_markup=_rewatch_keyboard(),
    )
    return WAITING_REWATCH


async def add_receive_rewatch(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Registra el rewatch desde botón inline y presenta la ficha resumen para confirmación.
    """
    query = update.callback_query
    await query.answer()

    rewatch = 1 if query.data == "rewatch_yes" else 0
    context.user_data["rewatch"] = rewatch

    movie: Movie = context.user_data["movie"]
    watched_at: date = context.user_data["watched_at"]
    rating: float = context.user_data["rating"]
    review: str | None = context.user_data["review"]

    rewatch_str = "Sí" if rewatch == 1 else "No"
    review_str = f'"{escape_markdown(review)}"' if review else "Sin comentario"

    await query.edit_message_text(
        f"🔁 Rewatch: *{rewatch_str}*", parse_mode="Markdown"
    )

    summary = (
        "📋 *Resumen del registro:*\n\n"
        f"🎬 *Película:* {escape_markdown(movie.title)}\n"
        f"👤 *Director:* {escape_markdown(movie.director or 'N/A')}\n"
        f"📅 *Fecha:* `{watched_at.strftime('%d/%m/%Y')}`\n"
        f"⭐ *Calificación:* {rating}/10\n"
        f"🔁 *Rewatch:* {rewatch_str}\n"
        f"💬 *Comentario:* {review_str}\n\n"
        "¿Deseas guardar este registro?"
    )

    await query.message.reply_text(
        summary, parse_mode="Markdown", reply_markup=_confirmation_keyboard()
    )
    return WAITING_CONFIRMATION


async def add_receive_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Persiste en SQLite si el usuario confirma mediante botón inline.
    """
    query = update.callback_query
    await query.answer()

    if query.data == "confirm_yes":
        movie: Movie = context.user_data["movie"]
        watched_at: date = context.user_data["watched_at"]
        rating: float = context.user_data["rating"]
        review: str | None = context.user_data["review"]
        rewatch: int = context.user_data["rewatch"]

        saved_movie = save_movie(movie)

        watch = WatchHistory(
            movie_id=saved_movie.id,
            watched_at=watched_at,
            rating=rating,
            review=review,
            rewatch=rewatch,
        )
        save_watch_history(watch)

        await query.edit_message_text(
            f"✅ *¡{escape_markdown(saved_movie.title)} guardada exitosamente!*\n\n"
            "Puedes consultarla en cualquier momento con /recent.",
            parse_mode="Markdown",
        )
    else:
        await query.edit_message_text("❌ Registro cancelado. No se guardaron cambios.")

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
        entry_points=[
            CommandHandler("add", add_start),
            CallbackQueryHandler(add_start_from_button, pattern=r"^menu_add$"),
        ],
        per_message=False,
        states={
            WAITING_TITLE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_receive_title)
            ],
            WAITING_SELECTION: [
                CallbackQueryHandler(add_receive_selection, pattern=r"^[0-4]$")
            ],
            WAITING_DATE: [
                CallbackQueryHandler(add_receive_date_today, pattern=r"^date_today$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_receive_date),
            ],
            WAITING_RATING: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_receive_rating)
            ],
            WAITING_REVIEW: [
                CallbackQueryHandler(add_receive_review_skip, pattern=r"^review_skip$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_receive_review),
            ],
            WAITING_REWATCH: [
                CallbackQueryHandler(add_receive_rewatch, pattern=r"^rewatch_(yes|no)$")
            ],
            WAITING_CONFIRMATION: [
                CallbackQueryHandler(add_receive_confirmation, pattern=r"^confirm_(yes|no)$")
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel_command)],
    )
