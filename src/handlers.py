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

from database import (
    delete_watch_by_id,
    get_recent_watches,
    get_watch_by_id,
    save_movie,
    save_watch_history,
    search_watches_by_title,
    update_watch_history,
)
from calendar_keyboard import create_calendar
from models import Movie, WatchHistory
from tmdb import get_movie_details, get_movie_director, search_movies


# Estados para la conversación /add
(
    WAITING_TITLE,
    WAITING_SELECTION,
    WAITING_DATE,
    WAITING_RATING,
    WAITING_REVIEW,
    WAITING_REWATCH,
    WAITING_CONFIRMATION,
) = range(7)

# Estados para la conversación /delete
(
    WAITING_DELETE_CHOICE,
    WAITING_DELETE_SEARCH,
    WAITING_DELETE_CONFIRM,
) = range(7, 10)

# Estados para la conversación /edit
(
    WAITING_EDIT_CHOICE,
    WAITING_EDIT_SEARCH,
    WAITING_EDIT_FIELD,
    WAITING_EDIT_VALUE,
) = range(10, 14)


def escape_markdown(text: str | None) -> str:
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


def format_watch_card(w: dict, index: int | None = None) -> str:
    """
    Formatea de manera completa y legible un registro de visualización con todos sus datos.
    """
    year = f" ({str(w['release_date'])[:4]})" if w.get("release_date") else ""
    rewatch_str = "Sí" if w.get("rewatch") == 1 else "No"
    rev = f'"{escape_markdown(w["review"])}"' if w.get("review") else "_Sin comentario_"
    idx_str = f"📌 *#{index} — *" if index is not None else "🎬 *"

    date_val = str(w.get("watched_at", ""))
    try:
        d = datetime.strptime(date_val, "%Y-%m-%d").date()
        date_display = d.strftime("%d/%m/%Y")
    except Exception:
        date_display = date_val

    title_escaped = escape_markdown(w.get("title", "Película"))
    close_bold = "*" if index is None else ""

    return (
        f"{idx_str}{title_escaped}{year}{close_bold}\n"
        f"👤 Director: {escape_markdown(w.get('director') or 'Desconocido')}\n"
        f"📅 Fecha: `{date_display}` | ⭐ Calificación: *{w.get('rating')}/10*\n"
        f"🔁 Rewatch: {rewatch_str}\n"
        f"💬 Comentario: {rev}\n"
    )


# --- Teclados reutilizables ---


def _main_menu_keyboard() -> InlineKeyboardMarkup:
    """Teclado con las opciones principales del bot."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎬 Registrar película", callback_data="menu_add")],
        [InlineKeyboardButton("🕐 Películas recientes", callback_data="menu_recent")],
        [InlineKeyboardButton("✏️ Editar un registro", callback_data="menu_edit")],
        [InlineKeyboardButton("🗑️ Eliminar un registro", callback_data="menu_delete")],
        [InlineKeyboardButton("❓ Ayuda", callback_data="menu_help")],
    ])


def _help_keyboard() -> InlineKeyboardMarkup:
    """Teclado para el menú de ayuda."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎬 Registrar película", callback_data="menu_add")],
        [InlineKeyboardButton("🕐 Películas recientes", callback_data="menu_recent")],
        [InlineKeyboardButton("✏️ Editar un registro", callback_data="menu_edit")],
        [InlineKeyboardButton("🗑️ Eliminar un registro", callback_data="menu_delete")],
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
    """Teclado Guardar/Cancelar para confirmación final de /add."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Guardar", callback_data="confirm_yes"),
            InlineKeyboardButton("❌ Cancelar", callback_data="confirm_no"),
        ]
    ])


def _format_recent_text(recent: list[dict]) -> str:
    """Construye el texto formateado de películas recientes ordenadas de la más reciente (#1) a la más antigua."""
    text = "🎬 *Películas vistas (de más reciente a más antigua):*\n\n"
    for i, item in enumerate(recent, start=1):
        text += format_watch_card(item, index=i)
        text += "────────────────────\n"
    return text


def _recent_action_keyboard() -> InlineKeyboardMarkup:
    """Teclado con acciones rápidas al consultar películas recientes."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎬 Registrar película", callback_data="menu_add")],
        [InlineKeyboardButton("✏️ Editar un registro", callback_data="menu_edit")],
        [InlineKeyboardButton("🗑️ Eliminar un registro", callback_data="menu_delete")],
        [InlineKeyboardButton("🏠 Menú principal", callback_data="menu_help")],
    ])


# --- Comandos y Menú Principal ---


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Responde al comando /start o a mensajes iniciales dando la bienvenida al usuario
    con las opciones en botones inline.
    """
    user = update.effective_user
    user_name = user.first_name if user else "cinéfilo"
    message = (
        f"¡Hola {user_name}! 👋🎬\n\n"
        "Bienvenido a *Frank's Movie Tracker*.\n\n"
        "¿Qué deseas hacer hoy?"
    )

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.message.reply_text(
            message, parse_mode="Markdown", reply_markup=_main_menu_keyboard()
        )
    elif update.message:
        await update.message.reply_text(
            message, parse_mode="Markdown", reply_markup=_main_menu_keyboard()
        )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Muestra la lista de opciones y comandos disponibles con botones.
    """
    text = (
        "📌 *Comandos y opciones disponibles:*\n\n"
        "• /add - Registrar una película que viste\n"
        "• /recent - Ver tus últimas películas registradas\n"
        "• /edit - Modificar los datos de un registro\n"
        "• /delete - Eliminar un registro de tu historial\n"
        "• /cancel - Cancelar cualquier operación en curso\n"
        "• /help - Mostrar esta ayuda"
    )
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.message.reply_text(
            text, parse_mode="Markdown", reply_markup=_help_keyboard()
        )
    elif update.message:
        await update.message.reply_text(
            text, parse_mode="Markdown", reply_markup=_help_keyboard()
        )


async def recent_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Muestra las últimas películas registradas en SQLite ordenadas por fecha de visualización
    (la más reciente vista como #1 y la más antigua al final).
    """
    recent = get_recent_watches(limit=10)
    if not recent:
        msg = "Aún no tienes películas registradas en tu historial."
        if update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.edit_message_text(msg)
        elif update.message:
            await update.message.reply_text(msg)
        return

    text = _format_recent_text(recent)
    markup = _recent_action_keyboard()
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.message.reply_text(text, parse_mode="Markdown", reply_markup=markup)
    elif update.message:
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=markup)


async def menu_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Maneja botones del menú principal que no forman parte de un ConversationHandler activo.
    """
    query = update.callback_query
    await query.answer()

    if query.data == "menu_recent":
        recent = get_recent_watches(limit=10)
        if not recent:
            await query.edit_message_text("Aún no tienes películas registradas en tu historial.")
            return
        await query.message.reply_text(
            _format_recent_text(recent),
            parse_mode="Markdown",
            reply_markup=_recent_action_keyboard(),
        )

    elif query.data == "menu_help":
        await help_command(update, context)

    elif query.data == "menu_cancel":
        context.user_data.clear()
        await query.edit_message_text("❌ Operación cancelada.")


# =========================================================
# FLUJO DE CONVERSACIÓN: /add (Registrar película)
# =========================================================


async def add_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Punto de entrada de /add desde comando."""
    context.user_data.clear()
    await update.message.reply_text(
        "🎬 *Registrar película*\n\n"
        "¿Qué película viste? Escribe su título para buscarla (o /cancel para salir):",
        parse_mode="Markdown",
    )
    return WAITING_TITLE


async def add_start_from_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Punto de entrada de /add desde botón inline del menú."""
    query = update.callback_query
    await query.answer()
    context.user_data.clear()
    await query.message.reply_text(
        "🎬 *Registrar película*\n\n"
        "¿Qué película viste? Escribe su título para buscarla (o /cancel para salir):",
        parse_mode="Markdown",
    )
    return WAITING_TITLE


async def add_receive_title(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Busca la película en TMDB e incluye el DIRECTOR junto al título y año
    para diferenciar claramente versiones con el mismo nombre.
    """
    query = update.message.text.strip()
    results = search_movies(query)

    if not results:
        await update.message.reply_text(
            f"❌ No encontré películas con el título '{query}'.\n"
            "Intenta con otro nombre o escribe /cancel para salir:"
        )
        return WAITING_TITLE

    top_results = results[:5]
    context.user_data["search_results"] = top_results

    text = "🔍 *Encontré los siguientes resultados:*\n\n"
    keyboard = []

    for i, item in enumerate(top_results, start=1):
        year = item.get("release_date", "")[:4]
        year_str = f" ({year})" if year else ""
        title = item.get("title", "Sin título")

        # Obtenemos el director de la película desde créditos de TMDB
        director = get_movie_director(item["id"])
        item["director_name"] = director
        director_str = director if director else "Desconocido"

        text += (
            f"*{i}.* *{escape_markdown(title)}*{year_str}\n"
            f"   👤 Director: {escape_markdown(director_str)}\n\n"
        )

        btn_dir = f" — {director}" if director else ""
        btn_label = f"{i}. {title}{year_str}{btn_dir}"
        if len(btn_label) > 60:
            btn_label = btn_label[:57] + "..."
        keyboard.append([InlineKeyboardButton(btn_label, callback_data=str(i - 1))])

    keyboard.append([InlineKeyboardButton("❌ Cancelar", callback_data="menu_cancel")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    text += "Selecciona la película que quieres registrar:"
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=reply_markup)
    return WAITING_SELECTION


async def add_receive_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Procesa la selección de película mediante botón inline."""
    query = update.callback_query
    await query.answer()

    if query.data == "menu_cancel":
        context.user_data.clear()
        await query.edit_message_text("❌ Operación cancelada.")
        return ConversationHandler.END

    search_results = context.user_data.get("search_results", [])
    choice = int(query.data)
    selected_raw = search_results[choice]

    details = get_movie_details(selected_raw["id"])
    movie = Movie.from_tmdb(details)
    context.user_data["movie"] = movie

    year = f" ({movie.release_date.year})" if movie.release_date else ""
    director_line = f"\n👤 Director: *{escape_markdown(movie.director or 'Desconocido')}*"

    await query.edit_message_text(
        f"✅ Seleccionaste: *{escape_markdown(movie.title)}*{year}{director_line}",
        parse_mode="Markdown",
    )

    await query.message.reply_text(
        "📅 *¿Cuándo viste la película?*\n"
        "Selecciona el día en el calendario (o escribe la fecha en formato `DD/MM/AAAA`):",
        parse_mode="Markdown",
        reply_markup=create_calendar(prefix="cal"),
    )
    return WAITING_DATE


async def calendar_nav_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Navega entre meses en el calendario inline sin enviar mensajes nuevos."""
    query = update.callback_query
    await query.answer()

    parts = query.data.split("_")
    year = int(parts[2])
    month = int(parts[3])

    await query.edit_message_reply_markup(
        reply_markup=create_calendar(year=year, month=month, prefix="cal")
    )
    return WAITING_DATE


async def calendar_ignore_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Ignora clics en celdas vacías o cabeceras informativas del calendario."""
    if update.callback_query:
        await update.callback_query.answer()


async def calendar_day_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Procesa la selección de un día específico en el calendario.
    Recibe la fecha en formato YYYY-MM-DD y continúa el flujo pidiendo la calificación.
    """
    query = update.callback_query
    await query.answer()

    date_str = query.data.replace("cal_day_", "")
    selected_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    context.user_data["watched_at"] = selected_date

    await query.edit_message_text(
        f"📅 Fecha seleccionada: *{selected_date.strftime('%d/%m/%Y')}*",
        parse_mode="Markdown",
    )

    await query.message.reply_text(
        "⭐ ¿Qué calificación le das del 0 al 10?\n"
        "(Puedes usar decimales, por ejemplo: `9.5` u `8`):",
        parse_mode="Markdown",
    )
    return WAITING_RATING


async def calendar_today_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Maneja el botón 'Hoy' del calendario para seleccionar la fecha actual."""
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


async def add_receive_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Valida la fecha escrita manualmente por el usuario."""
    text = update.message.text.strip()
    parsed_date = parse_date_input(text)

    if not parsed_date:
        await update.message.reply_text(
            "⚠️ Formato no reconocido. Escribe la fecha en formato `DD/MM/AAAA` (ej: 12/09/2026) o usa el calendario:",
            parse_mode="Markdown",
            reply_markup=create_calendar(prefix="cal"),
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
    """Valida la calificación y pide comentario con botón de omitir."""
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
    """Almacena el comentario escrito y pregunta si fue rewatch."""
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
    """Maneja el botón de omitir comentario."""
    query = update.callback_query
    await query.answer()

    context.user_data["review"] = None
    await query.edit_message_text("💬 Comentario: *Omitido*", parse_mode="Markdown")
    await query.message.reply_text(
        "🔁 ¿Fue un rewatch? (¿Ya la habías visto antes?)",
        parse_mode="Markdown",
        reply_markup=_rewatch_keyboard(),
    )
    return WAITING_REWATCH


async def add_receive_rewatch(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Registra si fue rewatch y presenta la confirmación con todos los datos."""
    query = update.callback_query
    await query.answer()

    rewatch = 1 if query.data == "rewatch_yes" else 0
    context.user_data["rewatch"] = rewatch

    movie: Movie = context.user_data["movie"]
    watched_at: date = context.user_data["watched_at"]
    rating: float = context.user_data["rating"]
    review: str | None = context.user_data["review"]

    rewatch_str = "Sí" if rewatch == 1 else "No"
    review_str = f'"{escape_markdown(review)}"' if review else "_Sin comentario_"

    await query.edit_message_text(f"🔁 Rewatch: *{rewatch_str}*", parse_mode="Markdown")

    summary = (
        "📋 *Resumen del registro:*\n\n"
        f"🎬 *Película:* {escape_markdown(movie.title)}\n"
        f"👤 *Director:* {escape_markdown(movie.director or 'Desconocido')}\n"
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
    """Persiste en SQLite si el usuario confirma."""
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

        success_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🕐 Ver películas recientes", callback_data="menu_recent")],
            [InlineKeyboardButton("🎬 Registrar otra película", callback_data="menu_add")],
            [InlineKeyboardButton("🏠 Menú principal", callback_data="menu_help")],
        ])

        await query.edit_message_text(
            f"✅ *¡{escape_markdown(saved_movie.title)} guardada exitosamente!*\n\n"
            "Selecciona una opción a continuación:",
            parse_mode="Markdown",
            reply_markup=success_keyboard,
        )
    else:
        await query.edit_message_text("❌ Registro cancelado. No se guardaron cambios.")

    context.user_data.clear()
    return ConversationHandler.END


# =========================================================
# FLUJO DE CONVERSACIÓN: /delete (Eliminar registro)
# =========================================================


def _render_records_for_action(records: list[dict], action_prefix: str) -> tuple[str, InlineKeyboardMarkup]:
    """Genera el texto detallado de los registros y sus botones de selección."""
    text = ""
    keyboard = []

    for i, w in enumerate(records, start=1):
        text += format_watch_card(w, index=i)
        text += "────────────────────\n"

        date_val = str(w.get("watched_at", ""))
        try:
            d = datetime.strptime(date_val, "%Y-%m-%d").date()
            date_display = d.strftime("%d/%m")
        except Exception:
            date_display = date_val

        btn_title = w.get("title", "Película")
        if len(btn_title) > 24:
            btn_title = btn_title[:21] + "..."
        btn_label = f"#{i} {btn_title} ({date_display})"

        keyboard.append([
            InlineKeyboardButton(f"👉 {btn_label}", callback_data=f"{action_prefix}_pick_{w['watch_id']}")
        ])

    keyboard.append([InlineKeyboardButton("🔍 Buscar por título", callback_data=f"{action_prefix}_search")])
    keyboard.append([InlineKeyboardButton("❌ Cancelar", callback_data=f"{action_prefix}_cancel")])

    return text, InlineKeyboardMarkup(keyboard)


async def delete_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Punto de entrada de /delete desde comando."""
    context.user_data.clear()
    recent = get_recent_watches(limit=6)

    if not recent:
        await update.message.reply_text("No tienes películas registradas en tu historial.")
        return ConversationHandler.END

    records_text, markup = _render_records_for_action(recent, "del")
    await update.message.reply_text(
        "🗑️ *Eliminar un registro*\n\n"
        "Revisa todos los datos de tus registros y pulsa el botón del que deseas eliminar:\n\n"
        + records_text,
        parse_mode="Markdown",
        reply_markup=markup,
    )
    return WAITING_DELETE_CHOICE


async def delete_start_from_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Punto de entrada de /delete desde botón inline del menú."""
    query = update.callback_query
    await query.answer()
    context.user_data.clear()
    recent = get_recent_watches(limit=6)

    if not recent:
        await query.message.reply_text("No tienes películas registradas en tu historial.")
        return ConversationHandler.END

    records_text, markup = _render_records_for_action(recent, "del")
    await query.message.reply_text(
        "🗑️ *Eliminar un registro*\n\n"
        "Revisa todos los datos de tus registros y pulsa el botón del que deseas eliminar:\n\n"
        + records_text,
        parse_mode="Markdown",
        reply_markup=markup,
    )
    return WAITING_DELETE_CHOICE


async def delete_start_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Solicita el nombre de la película a buscar para eliminar."""
    query = update.callback_query
    await query.answer()
    await query.message.reply_text(
        "🔍 Escribe el nombre (o parte del título) de la película que deseas buscar para eliminar (o /cancel):"
    )
    return WAITING_DELETE_SEARCH


async def delete_receive_search_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Busca registros por título y los presenta para eliminación."""
    search_text = update.message.text.strip()
    matches = search_watches_by_title(search_text, limit=6)

    if not matches:
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔍 Intentar otra búsqueda", callback_data="del_search")],
            [InlineKeyboardButton("❌ Cancelar", callback_data="del_cancel")],
        ])
        await update.message.reply_text(
            f"❌ No encontré registros que coincidan con '{search_text}'.",
            reply_markup=keyboard,
        )
        return WAITING_DELETE_CHOICE

    records_text, markup = _render_records_for_action(matches, "del")
    await update.message.reply_text(
        f"🔍 *Resultados para '{search_text}':*\n\n"
        "Selecciona el registro que deseas eliminar:\n\n"
        + records_text,
        parse_mode="Markdown",
        reply_markup=markup,
    )
    return WAITING_DELETE_CHOICE


async def delete_receive_pick(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Muestra la confirmación detallada del registro a eliminar."""
    query = update.callback_query
    await query.answer()

    watch_id = int(query.data.split("_")[-1])
    record = get_watch_by_id(watch_id)

    if not record:
        await query.edit_message_text("⚠️ El registro ya no existe o fue eliminado.")
        return ConversationHandler.END

    context.user_data["delete_watch_id"] = watch_id
    card = format_watch_card(record)

    confirm_keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🗑️ Sí, eliminar registro", callback_data=f"del_confirm_{watch_id}")],
        [InlineKeyboardButton("❌ No, cancelar", callback_data="del_cancel")],
    ])

    await query.message.reply_text(
        "⚠️ *¿Estás seguro de que deseas ELIMINAR este registro?*\n\n"
        f"{card}\n"
        "_Esta acción no se puede deshacer._",
        parse_mode="Markdown",
        reply_markup=confirm_keyboard,
    )
    return WAITING_DELETE_CONFIRM


async def delete_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Ejecuta la eliminación del registro en SQLite."""
    query = update.callback_query
    await query.answer()

    watch_id = int(query.data.split("_")[-1])
    record = get_watch_by_id(watch_id)
    title = record.get("title", "Película") if record else "Película"

    success = delete_watch_by_id(watch_id)
    context.user_data.clear()

    if success:
        await query.edit_message_text(
            f"✅ Registro de *{escape_markdown(title)}* eliminado correctamente.",
            parse_mode="Markdown",
        )
    else:
        await query.edit_message_text("⚠️ No se pudo eliminar el registro (posiblemente ya no existe).")

    return ConversationHandler.END


async def delete_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancela la eliminación."""
    query = update.callback_query
    await query.answer()
    context.user_data.clear()
    await query.edit_message_text("❌ Operación cancelada. No se eliminó ningún registro.")
    return ConversationHandler.END


# =========================================================
# FLUJO DE CONVERSACIÓN: /edit (Editar registro)
# =========================================================


def _edit_fields_keyboard() -> InlineKeyboardMarkup:
    """Teclado para seleccionar qué campo del registro editar."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📅 Fecha", callback_data="edit_field_date")],
        [InlineKeyboardButton("⭐ Calificación", callback_data="edit_field_rating")],
        [InlineKeyboardButton("💬 Comentario", callback_data="edit_field_review")],
        [InlineKeyboardButton("🔁 Rewatch", callback_data="edit_field_rewatch")],
        [InlineKeyboardButton("❌ Cancelar", callback_data="edit_cancel")],
    ])


async def edit_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Punto de entrada de /edit desde comando."""
    context.user_data.clear()
    recent = get_recent_watches(limit=6)

    if not recent:
        await update.message.reply_text("No tienes películas registradas en tu historial.")
        return ConversationHandler.END

    records_text, markup = _render_records_for_action(recent, "edit")
    await update.message.reply_text(
        "✏️ *Editar un registro*\n\n"
        "Revisa todos los datos de tus registros y pulsa el botón del que deseas modificar:\n\n"
        + records_text,
        parse_mode="Markdown",
        reply_markup=markup,
    )
    return WAITING_EDIT_CHOICE


async def edit_start_from_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Punto de entrada de /edit desde botón inline del menú."""
    query = update.callback_query
    await query.answer()
    context.user_data.clear()
    recent = get_recent_watches(limit=6)

    if not recent:
        await query.message.reply_text("No tienes películas registradas en tu historial.")
        return ConversationHandler.END

    records_text, markup = _render_records_for_action(recent, "edit")
    await query.message.reply_text(
        "✏️ *Editar un registro*\n\n"
        "Revisa todos los datos de tus registros y pulsa el botón del que deseas modificar:\n\n"
        + records_text,
        parse_mode="Markdown",
        reply_markup=markup,
    )
    return WAITING_EDIT_CHOICE


async def edit_start_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Solicita el nombre de la película a buscar para editar."""
    query = update.callback_query
    await query.answer()
    await query.message.reply_text(
        "🔍 Escribe el nombre (o parte del título) de la película que deseas buscar para editar (o /cancel):"
    )
    return WAITING_EDIT_SEARCH


async def edit_receive_search_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Busca registros por título y los presenta para edición."""
    search_text = update.message.text.strip()
    matches = search_watches_by_title(search_text, limit=6)

    if not matches:
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔍 Intentar otra búsqueda", callback_data="edit_search")],
            [InlineKeyboardButton("❌ Cancelar", callback_data="edit_cancel")],
        ])
        await update.message.reply_text(
            f"❌ No encontré registros que coincidan con '{search_text}'.",
            reply_markup=keyboard,
        )
        return WAITING_EDIT_CHOICE

    records_text, markup = _render_records_for_action(matches, "edit")
    await update.message.reply_text(
        f"🔍 *Resultados para '{search_text}':*\n\n"
        "Selecciona el registro que deseas editar:\n\n"
        + records_text,
        parse_mode="Markdown",
        reply_markup=markup,
    )
    return WAITING_EDIT_CHOICE


async def edit_receive_pick(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Muestra la ficha completa del registro seleccionado y los botones de campos editables."""
    query = update.callback_query
    await query.answer()

    watch_id = int(query.data.split("_")[-1])
    record = get_watch_by_id(watch_id)

    if not record:
        await query.edit_message_text("⚠️ El registro ya no existe.")
        return ConversationHandler.END

    context.user_data["edit_watch_id"] = watch_id
    card = format_watch_card(record)

    await query.message.reply_text(
        "📋 *Registro seleccionado:*\n\n"
        f"{card}\n"
        "¿Qué dato deseas modificar?",
        parse_mode="Markdown",
        reply_markup=_edit_fields_keyboard(),
    )
    return WAITING_EDIT_FIELD


async def edit_receive_field(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Prepara la solicitud del nuevo valor para el campo elegido."""
    query = update.callback_query
    await query.answer()

    field = query.data.replace("edit_field_", "")
    context.user_data["edit_field"] = field

    if field == "date":
        await query.message.reply_text(
            "📅 *Selecciona la nueva fecha:*\n"
            "Elige el día en el calendario interactivo o escribe la fecha (`DD/MM/AAAA`):",
            parse_mode="Markdown",
            reply_markup=create_calendar(prefix="editcal"),
        )
        return WAITING_EDIT_VALUE

    elif field == "rating":
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("❌ Cancelar", callback_data="edit_cancel")],
        ])
        await query.message.reply_text(
            "⭐ Ingresa la nueva calificación del 0 al 10 (ej: `8.5`):",
            parse_mode="Markdown",
            reply_markup=keyboard,
        )
        return WAITING_EDIT_VALUE

    elif field == "review":
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🗑️ Borrar comentario", callback_data="edit_val_review_clear")],
            [InlineKeyboardButton("❌ Cancelar", callback_data="edit_cancel")],
        ])
        await query.message.reply_text(
            "💬 Escribe el nuevo comentario (o pulsa *Borrar comentario* para quitarlo):",
            parse_mode="Markdown",
            reply_markup=keyboard,
        )
        return WAITING_EDIT_VALUE

    elif field == "rewatch":
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Sí", callback_data="edit_val_rewatch_yes"),
                InlineKeyboardButton("❌ No", callback_data="edit_val_rewatch_no"),
            ],
            [InlineKeyboardButton("❌ Cancelar", callback_data="edit_cancel")],
        ])
        await query.message.reply_text(
            "🔁 ¿Fue un rewatch? (¿Ya la habías visto antes?)",
            parse_mode="Markdown",
            reply_markup=keyboard,
        )
        return WAITING_EDIT_VALUE

    return WAITING_EDIT_FIELD


async def _finish_edit_and_respond(update: Update, context: ContextTypes.DEFAULT_TYPE, watch_id: int) -> int:
    """Envía la ficha actualizada del registro con opciones para seguir o finalizar."""
    updated = get_watch_by_id(watch_id)
    card = format_watch_card(updated)

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✏️ Modificar otro dato de este registro", callback_data=f"edit_pick_{watch_id}")],
        [InlineKeyboardButton("🏁 Finalizar", callback_data="edit_finish")],
    ])

    msg = (
        "✅ *¡Registro actualizado con éxito!*\n\n"
        f"{card}\n"
        "¿Deseas hacer otro cambio en este registro?"
    )

    if update.callback_query:
        await update.callback_query.message.reply_text(msg, parse_mode="Markdown", reply_markup=keyboard)
    elif update.message:
        await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=keyboard)

    return WAITING_EDIT_VALUE


async def edit_calendar_nav_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Navega entre meses en el calendario inline al editar un registro."""
    query = update.callback_query
    await query.answer()

    parts = query.data.split("_")
    year = int(parts[2])
    month = int(parts[3])

    await query.edit_message_reply_markup(
        reply_markup=create_calendar(year=year, month=month, prefix="editcal")
    )
    return WAITING_EDIT_VALUE


async def edit_calendar_day_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Aplica la fecha seleccionada en el calendario al editar un registro."""
    query = update.callback_query
    await query.answer()

    date_str = query.data.replace("editcal_day_", "")
    selected_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    watch_id = context.user_data.get("edit_watch_id")

    update_watch_history(watch_id, watched_at=selected_date)
    return await _finish_edit_and_respond(update, context, watch_id)


async def edit_calendar_today_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Aplica la fecha de hoy al editar un registro."""
    query = update.callback_query
    await query.answer()

    watch_id = context.user_data.get("edit_watch_id")
    update_watch_history(watch_id, watched_at=date.today())
    return await _finish_edit_and_respond(update, context, watch_id)


async def edit_receive_text_value(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Procesa el nuevo valor de fecha, calificación o comentario ingresado por texto."""
    field = context.user_data.get("edit_field")
    watch_id = context.user_data.get("edit_watch_id")
    text = update.message.text.strip()

    if field == "date":
        parsed = parse_date_input(text)
        if not parsed:
            await update.message.reply_text(
                "⚠️ Fecha no válida. Usa el formato `DD/MM/AAAA` (ej: 12/09/2026) o selecciona en el calendario:",
                parse_mode="Markdown",
                reply_markup=create_calendar(prefix="editcal"),
            )
            return WAITING_EDIT_VALUE
        update_watch_history(watch_id, watched_at=parsed)

    elif field == "rating":
        try:
            rating = float(text.replace(",", "."))
            if not (0.0 <= rating <= 10.0):
                raise ValueError()
        except ValueError:
            await update.message.reply_text(
                "⚠️ Calificación inválida. Ingresa un número del 0 al 10 (ej: `8.5`):",
                parse_mode="Markdown",
            )
            return WAITING_EDIT_VALUE
        update_watch_history(watch_id, rating=round(rating, 1))

    elif field == "review":
        if text.lower() in ("no", "ninguno", "ninguna", "-", "borrar", "eliminar"):
            update_watch_history(watch_id, clear_review=True)
        else:
            update_watch_history(watch_id, review=text)

    return await _finish_edit_and_respond(update, context, watch_id)


async def edit_receive_date_today(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Maneja el botón 'Hoy' en la edición de fecha."""
    query = update.callback_query
    await query.answer()

    watch_id = context.user_data.get("edit_watch_id")
    update_watch_history(watch_id, watched_at=date.today())
    return await _finish_edit_and_respond(update, context, watch_id)


async def edit_receive_review_clear(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Maneja el botón 'Borrar comentario'."""
    query = update.callback_query
    await query.answer()

    watch_id = context.user_data.get("edit_watch_id")
    update_watch_history(watch_id, clear_review=True)
    return await _finish_edit_and_respond(update, context, watch_id)


async def edit_receive_rewatch(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Maneja los botones Sí/No para la edición de rewatch."""
    query = update.callback_query
    await query.answer()

    rewatch_val = 1 if query.data == "edit_val_rewatch_yes" else 0
    watch_id = context.user_data.get("edit_watch_id")
    update_watch_history(watch_id, rewatch=rewatch_val)
    return await _finish_edit_and_respond(update, context, watch_id)


async def edit_finish(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Finaliza el proceso de edición."""
    query = update.callback_query
    await query.answer()
    context.user_data.clear()
    await query.edit_message_text(
        "🏁 *Edición completada con éxito.*\n\nPuedes consultar tus registros con /recent.",
        parse_mode="Markdown",
    )
    return ConversationHandler.END


async def edit_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancela la edición sin más cambios."""
    query = update.callback_query
    await query.answer()
    context.user_data.clear()
    await query.edit_message_text("❌ Edición cancelada.")
    return ConversationHandler.END


# =========================================================
# COMANDO /cancel Y BUILDERS DE CONVERSATIONHANDLERS
# =========================================================


async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancela cualquier conversación activa."""
    context.user_data.clear()
    await update.message.reply_text("❌ Operación cancelada.", parse_mode="Markdown")
    return ConversationHandler.END


def get_add_conversation_handler() -> ConversationHandler:
    """Construye el ConversationHandler para registrar películas (/add)."""
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
                CallbackQueryHandler(add_receive_selection, pattern=r"^[0-4]$"),
                CallbackQueryHandler(menu_button_handler, pattern=r"^menu_cancel$"),
            ],
            WAITING_DATE: [
                CallbackQueryHandler(calendar_nav_handler, pattern=r"^cal_nav_\d+_\d+$"),
                CallbackQueryHandler(calendar_ignore_handler, pattern=r"^cal_ignore$"),
                CallbackQueryHandler(calendar_day_handler, pattern=r"^cal_day_\d{4}-\d{2}-\d{2}$"),
                CallbackQueryHandler(calendar_today_handler, pattern=r"^cal_today$"),
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


def get_delete_conversation_handler() -> ConversationHandler:
    """Construye el ConversationHandler para eliminar registros (/delete)."""
    return ConversationHandler(
        entry_points=[
            CommandHandler("delete", delete_start),
            CallbackQueryHandler(delete_start_from_button, pattern=r"^menu_delete$"),
        ],
        per_message=False,
        states={
            WAITING_DELETE_CHOICE: [
                CallbackQueryHandler(delete_receive_pick, pattern=r"^del_pick_\d+$"),
                CallbackQueryHandler(delete_start_search, pattern=r"^del_search$"),
                CallbackQueryHandler(delete_cancel, pattern=r"^del_cancel$"),
            ],
            WAITING_DELETE_SEARCH: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, delete_receive_search_query),
            ],
            WAITING_DELETE_CONFIRM: [
                CallbackQueryHandler(delete_confirm, pattern=r"^del_confirm_\d+$"),
                CallbackQueryHandler(delete_cancel, pattern=r"^del_cancel$"),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel_command),
            CallbackQueryHandler(delete_cancel, pattern=r"^del_cancel$"),
        ],
    )


def get_edit_conversation_handler() -> ConversationHandler:
    """Construye el ConversationHandler para editar registros (/edit)."""
    return ConversationHandler(
        entry_points=[
            CommandHandler("edit", edit_start),
            CallbackQueryHandler(edit_start_from_button, pattern=r"^menu_edit$"),
        ],
        per_message=False,
        states={
            WAITING_EDIT_CHOICE: [
                CallbackQueryHandler(edit_receive_pick, pattern=r"^edit_pick_\d+$"),
                CallbackQueryHandler(edit_start_search, pattern=r"^edit_search$"),
                CallbackQueryHandler(edit_cancel, pattern=r"^edit_cancel$"),
            ],
            WAITING_EDIT_SEARCH: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, edit_receive_search_query),
            ],
            WAITING_EDIT_FIELD: [
                CallbackQueryHandler(edit_receive_field, pattern=r"^edit_field_(date|rating|review|rewatch)$"),
                CallbackQueryHandler(edit_cancel, pattern=r"^edit_cancel$"),
            ],
            WAITING_EDIT_VALUE: [
                CallbackQueryHandler(edit_calendar_nav_handler, pattern=r"^editcal_nav_\d+_\d+$"),
                CallbackQueryHandler(calendar_ignore_handler, pattern=r"^editcal_ignore$"),
                CallbackQueryHandler(edit_calendar_day_handler, pattern=r"^editcal_day_\d{4}-\d{2}-\d{2}$"),
                CallbackQueryHandler(edit_calendar_today_handler, pattern=r"^editcal_today$"),
                CallbackQueryHandler(edit_receive_review_clear, pattern=r"^edit_val_review_clear$"),
                CallbackQueryHandler(edit_receive_rewatch, pattern=r"^edit_val_rewatch_(yes|no)$"),
                CallbackQueryHandler(edit_receive_pick, pattern=r"^edit_pick_\d+$"),
                CallbackQueryHandler(edit_finish, pattern=r"^edit_finish$"),
                CallbackQueryHandler(edit_cancel, pattern=r"^edit_cancel$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, edit_receive_text_value),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel_command),
            CallbackQueryHandler(edit_cancel, pattern=r"^edit_cancel$"),
        ],
    )
