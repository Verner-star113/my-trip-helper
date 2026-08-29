import sqlite3
import requests
from datetime import datetime, timedelta
import math

# --- ГЛОБАЛЬНЫЙ ГЕО-СПРАВОЧНИК ГОРОДОВ И СТРАН МИРА (БАЗА ДАННЫХ НАВИГАТОРА) ---
GEO_REGISTRY = {
    "томск": (56.4977, 84.9744, "Россия", "Сибирь"),
    "новосибирск": (55.0084, 82.9357, "Россия", "Сибирь"),
    "кемерово": (55.3450, 86.0640, "Россия", "Сибирь"),
    "красноярск": (56.0153, 92.8932, "Россия", "Сибирь"),
    "омск": (54.9885, 73.3242, "Россия", "Сибирь"),
    "барнаул": (53.3548, 83.7698, "Россия", "Сибирь"),
    "иркутск": (52.2870, 104.3050, "Россия", "Сибирь"),
    "москва": (55.7558, 37.6173, "Россия", "Центр"),
    "санкт-петербург": (59.9343, 30.3351, "Россия", "Северо-Запад"),
    "екатеринбург": (56.8389, 60.6057, "Россия", "Урал"),
    "казань": (55.7887, 49.1221, "Россия", "Поволжье"),
    "нижний новгород": (56.2965, 43.9361, "Россия", "Центр"),
    "челябинск": (55.1644, 61.4368, "Россия", "Урал"),
    "самара": (53.2001, 50.1500, "Россия", "Поволжье"),
    "ростов-на-дону": (47.2357, 39.7015, "Россия", "Юг"),
    "уфа": (54.7431, 55.9678, "Россия", "Поволжье"),
    "волгоград": (48.7080, 44.5133, "Россия", "Юг"),
    "пермь": (58.0296, 56.2668, "Россия", "Урал"),
    "краснодар": (45.0355, 38.9753, "Россия", "Юг"),
    "сочи": (43.6028, 39.7342, "Россия", "Юг"),
    "владивосток": (43.1198, 131.8869, "Россия", "Дальний Восток"),
    "хабаровск": (48.4725, 135.0577, "Россия", "Дальний Восток"),
    "минск": (53.9006, 27.5590, "Беларусь", "Столица"),
    "брест": (52.0976, 23.7341, "Беларусь", "Граница"),
    "астана": (51.1605, 71.4704, "Казахстан", "Столица"),
    "алматы": (43.2389, 76.8897, "Казахстан", "Юг"),
    "пекин": (39.9042, 116.4074, "Китай", "Азия"),
    "берлин": (52.5200, 13.4050, "Германия", "Европа")
}


def init_db():
    conn = sqlite3.connect("trips.db", timeout=10)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS trips (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            origin_city TEXT NOT NULL,
            origin_address TEXT,
            destination_city TEXT NOT NULL,
            destination_address TEXT,
            arrival_time TEXT NOT NULL,
            transport_mode TEXT NOT NULL,
            notes TEXT,
            status TEXT DEFAULT 'Запланирована'
        )
    """)
    conn.commit()
    conn.close()


def add_trip(origin_city, origin_address, destination_city, destination_address, arrival_time, transport_mode,
             notes=""):
    conn = sqlite3.connect("trips.db", timeout=10)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO trips (origin_city, origin_address, destination_city, destination_address, arrival_time, transport_mode, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (origin_city, origin_address, destination_city, destination_address, arrival_time, transport_mode, notes))
    conn.commit()
    conn.close()


def get_active_trips():
    conn = sqlite3.connect("trips.db", timeout=10)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, origin_city, origin_address, destination_city, destination_address, arrival_time, transport_mode, notes, status FROM trips WHERE status = 'Запланирована'")
    rows = cursor.fetchall()
    conn.close()
    return rows


def delete_trip(trip_id):
    conn = sqlite3.connect("trips.db", timeout=10)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM trips WHERE id = ?", (int(trip_id),))
    conn.commit()
    conn.close()


def get_location_data(location_name):
    name_clean = str(location_name).strip().lower()
    for key, data in GEO_REGISTRY.items():
        if key in name_clean:
            return data[0], data[1], data[2]
    fake_lat = 55.0 + (len(name_clean) % 5) * 0.5
    fake_lon = 75.0 + (len(name_clean) % 7) * 0.5
    return fake_lat, fake_lon, "Неизвестно"


def calculate_great_circle_distance(lat1, lon1, lat2, lon2):
    """Математический расчет реального расстояния между точками на сфере Земли (в км)."""
    R = 6371.0  # Радиус Земли
    p = math.pi / 180
    a = 0.5 - math.cos((lat2 - lat1) * p) / 2 + math.cos(lat1 * p) * math.cos(lat2 * p) * (
                1 - math.cos((lon2 - lon1) * p)) / 2
    return 2 * R * math.asin(math.sqrt(a))


def calculate_trip_timing(orig_city, orig_addr, dest_city, dest_addr, arrival_str, transport_mode):
    """Глобальный навигационный движок. Занимается ТОЛЬКО математикой времени и расстояний."""
    lat1, lon1, country1 = get_location_data(orig_city)
    lat2, lon2, country2 = get_location_data(dest_city)

    if orig_addr.strip():
        lat1 += (len(orig_addr) % 10) * 0.002
        lon1 += (len(orig_addr) % 7) * 0.002
    if dest_addr.strip():
        lat2 += (len(dest_addr) % 10) * 0.002
        lon2 += (len(dest_addr) % 7) * 0.002

    geo_distance = calculate_great_circle_distance(lat1, lon1, lat2, lon2)
    road_distance = geo_distance * 1.22

    if "автомобиле" in transport_mode:
        speed = 80
        buffer_min = 20
    elif "транспорт" in transport_mode:
        speed = 60
        buffer_min = 35
    else:
        speed = 12
        buffer_min = 10

    pure_time_min = int((road_distance / speed) * 60)
    border_delay = 0

    if country1 != country2 and country1 != "Неизвестно" and country2 != "Неизвестно":
        scale_status = f"🌍 Международный маршрут ({country1} ➔ {country2})"
        border_delay = 150
    else:
        scale_status = f"🇷🇺 Междугородний маршрут ({orig_city} ➔ {dest_city})"

    try:
        arrival_dt = datetime.strptime(arrival_str, "%Y-%m-%d %H:%M")
    except ValueError:
        arrival_dt = datetime.now() + timedelta(hours=3)

    hour = arrival_dt.hour
    traffic_jam_coor = 1.0
    jam_description = "🟢 Трасса свободна"

    if (8 <= hour <= 10) or (17 <= hour <= 19):
        traffic_jam_coor = 1.2
        jam_description = "🔴 Заторы на въезде/выезде (Час пик)"

    final_travel_time = int(pure_time_min * traffic_jam_coor) + border_delay
    total_minutes_to_subtract = final_travel_time + buffer_min
    departure_dt = arrival_dt - timedelta(minutes=total_minutes_to_subtract)

    return {
        "distance": round(road_distance, 1),
        "final_time": final_travel_time,
        "jam_status": jam_description,
        "scale_status": scale_status,
        "departure_time": departure_dt.strftime("%d.%m в %H:%M"),
        "coords": ((lat1, lon1), (lat2, lon2))
    }


def send_telegram_alert(token, chat_id, message):
    """Бронебойный прямой отправщик уведомлений в Telegram API."""
    if not token or not chat_id:
        return False
    try:
        url = f"https://telegram.org{str(token).strip()}/sendMessage"
        payload = {
            "chat_id": str(chat_id).strip(),
            "text": message
        }
        response = requests.post(url, json=payload, timeout=5)
        return response.status_code == 200
    except Exception:
        return False
