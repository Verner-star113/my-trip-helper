import sqlite3
import json
import urllib.request
import urllib.parse
import requests  # <-- ВОТ ЭТУ СТРОЧКУ НУЖНО ДОБАВИТЬ!
from datetime import datetime, timedelta


def init_db():
    conn = sqlite3.connect("trips.db", timeout=10)
    cursor = conn.cursor()
    # Таблица для планирования поездок
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS trips (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            origin TEXT NOT NULL,
            destination TEXT NOT NULL,
            arrival_time TEXT NOT NULL, -- К какому времени нужно успеть (YYYY-MM-DD HH:MM)
            transport_mode TEXT NOT NULL, -- driving, walking, bicycling, transit
            notes TEXT,
            status TEXT DEFAULT 'Запланирована' -- Запланирована, Завершена, Отменена
        )
    """)
    conn.commit()
    conn.close()

def add_trip(origin, destination, arrival_time, transport_mode, notes=""):
    conn = sqlite3.connect("trips.db", timeout=10)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO trips (origin, destination, arrival_time, transport_mode, notes)
        VALUES (?, ?, ?, ?, ?)
    """, (origin, destination, arrival_time, transport_mode, notes))
    conn.commit()
    conn.close()

def get_active_trips():
    conn = sqlite3.connect("trips.db", timeout=10)
    cursor = conn.cursor()
    cursor.execute("SELECT id, origin, destination, arrival_time, transport_mode, notes, status FROM trips WHERE status = 'Запланирована'")
    rows = cursor.fetchall()
    conn.close()
    return rows

def delete_trip(trip_id):
    conn = sqlite3.connect("trips.db", timeout=10)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM trips WHERE id = ?", (int(trip_id),))
    conn.commit()
    conn.close()


# --- ДВИЖОК УМНОГО РАСЧЕТА МАРШРУТА И ПРОБОК ---
def calculate_trip_timing(origin, destination, arrival_str, transport_mode):
    """
    Рассчитывает время в пути, коэффициент пробок и идеальное время выезда.
    """
    # 1. Симулируем расстояние (в км) на основе длины названий адресов
    # Для домашнего проекта это отличный способ получить уникальные цифры для каждого маршрута
    base_distance = max(5, (len(origin) + len(destination)) * 1.2)

    # 2. Определяем базовую скорость (км/ч) и запас времени на сборы (в минутах)
    if "автомобиле" in transport_mode:
        speed = 45
        buffer_min = 10
    elif "транспорт" in transport_mode:
        speed = 25
        buffer_min = 15
    elif "Пешком" in transport_mode:
        speed = 5
        buffer_min = 5
    else:  # Велосипед
        speed = 15
        buffer_min = 5

    # Чистое время в пути в минутах
    pure_time_min = int((base_distance / speed) * 60)

    # 3. Анализируем час пик для пробок
    try:
        arrival_dt = datetime.strptime(arrival_str, "%Y-%m-%d %H:%M")
    except ValueError:
        arrival_dt = datetime.now() + timedelta(hours=2)

    hour = arrival_dt.hour
    traffic_jam_coor = 1.0
    jam_description = "🟢 Дороги свободны"

    # Если прибытие выпадает на час пик, пробки увеличивают время
    if (8 <= hour <= 9) or (17 <= hour <= 19):
        traffic_jam_coor = 1.6
        jam_description = "🔴 Час пик (Тяжелые пробки)"
    elif (12 <= hour <= 14) or (20 <= hour <= 21):
        traffic_jam_coor = 1.2
        jam_description = "🟡 Плотное движение"

    # Итоговое время в пути с учетом ситуации на дороге
    final_travel_time = int(pure_time_min * traffic_jam_coor)

    # Полное время, которое нужно отнять от времени прибытия (в пути + запас на сборы)
    total_minutes_to_subtract = final_travel_time + buffer_min
    departure_dt = arrival_dt - timedelta(minutes=total_minutes_to_subtract)

    return {
        "distance": round(base_distance, 1),
        "pure_time": pure_time_min,
        "final_time": final_travel_time,
        "jam_status": jam_description,
        "departure_time": departure_dt.strftime("%H:%M"),
        "departure_datetime": departure_dt
    }


# --- СИСТЕМА TELEGRAM УВЕДОМЛЕНИЙ ---
def send_telegram_alert(token, chat_id, message):
    """Классический автоматический отправщик для работы в облаке."""
    if not token or not chat_id:
        return False
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {"chat_id": str(chat_id).strip(), "text": message}
        response = requests.post(url, json=payload, timeout=5)
        return response.status_code == 200
    except Exception:
        return False
