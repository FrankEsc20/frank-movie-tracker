"""
Módulo para el selector interactivo de fechas en Telegram mediante botones inline.
"""

import calendar
from datetime import date
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

MONTHS_ES = [
    "",
    "Enero",
    "Febrero",
    "Marzo",
    "Abril",
    "Mayo",
    "Junio",
    "Julio",
    "Agosto",
    "Septiembre",
    "Octubre",
    "Noviembre",
    "Diciembre",
]

DAYS_ES = ["Lu", "Ma", "Mi", "Ju", "Vi", "Sá", "Do"]


def create_calendar(
    year: int | None = None,
    month: int | None = None,
    prefix: str = "cal",
) -> InlineKeyboardMarkup:
    """
    Construye un teclado inline de calendario interactivo para el mes y año dados.
    Si no se especifican año y mes, se utiliza el mes y año actual.

    Parameters
    ----------
    year : int | None
        Año a mostrar en el calendario.
    month : int | None
        Mes a mostrar en el calendario (1 a 12).
    prefix : str
        Prefijo único para los callback_data (por defecto 'cal').

    Returns
    -------
    InlineKeyboardMarkup
        Teclado con la cuadrícula del mes, botones de navegación y botón de Hoy.
    """
    today = date.today()
    if year is None:
        year = today.year
    if month is None:
        month = today.month

    keyboard = []

    # Fila 1: Navegación de mes y título
    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1
    next_month = month + 1 if month < 12 else 1
    next_year = year if month < 12 else year + 1

    header_row = [
        InlineKeyboardButton("◀️", callback_data=f"{prefix}_nav_{prev_year}_{prev_month}"),
        InlineKeyboardButton(f"{MONTHS_ES[month]} {year}", callback_data=f"{prefix}_ignore"),
        InlineKeyboardButton("▶️", callback_data=f"{prefix}_nav_{next_year}_{next_month}"),
    ]
    keyboard.append(header_row)

    # Fila 2: Nombres de los días de la semana
    week_header = [
        InlineKeyboardButton(day_name, callback_data=f"{prefix}_ignore")
        for day_name in DAYS_ES
    ]
    keyboard.append(week_header)

    # Filas de días del mes
    month_cal = calendar.monthcalendar(year, month)
    for week in month_cal:
        row = []
        for day in week:
            if day == 0:
                row.append(InlineKeyboardButton(" ", callback_data=f"{prefix}_ignore"))
            else:
                is_today = (year == today.year and month == today.month and day == today.day)
                label = f"•{day}•" if is_today else str(day)
                cal_data = f"{prefix}_day_{year:04d}-{month:02d}-{day:02d}"
                row.append(InlineKeyboardButton(label, callback_data=cal_data))
        keyboard.append(row)

    # Fila final: Botón rápido de "Hoy"
    footer_row = [
        InlineKeyboardButton("📅 Hoy", callback_data=f"{prefix}_today"),
    ]
    keyboard.append(footer_row)

    return InlineKeyboardMarkup(keyboard)
