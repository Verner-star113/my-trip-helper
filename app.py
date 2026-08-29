import streamlit as st
from datetime import datetime, timedelta
from database import *
from streamlit_folium import st_folium, folium_static
import folium


# Инициализируем БД
init_db()

st.set_page_config(page_title="Помощник поездок", page_icon="🚗", layout="wide")

st.title("🚗 Умный помощник управления расписанием поездок")
st.write("Планируйте маршруты, рассчитывайте время выезда с учетом пробок и получайте уведомления!")


# Боковая панель для добавления новой поездки (С разделением на Города и Улицы)
st.sidebar.header("🗺️ Запланировать поездку")
trip_form = st.sidebar.form("add_trip_form_v2", clear_on_submit=True)

with trip_form:
    st.markdown("### 🛫 Точка отправления")
    origin_city = st.text_input("Город:", placeholder="Например: Томск")
    origin_address = st.text_input("Улица, дом (необязательно):", placeholder="Например: ул. Ленина, 10")

    st.markdown("### 🛬 Точка прибытия")
    destination_city = st.text_input("Город назначения:", placeholder="Например: Кемерово")
    destination_address = st.text_input("Улица, дом (необязательно):", placeholder="Например: проспект Ленина, 5")

    st.divider()
    col_d, col_t = st.columns(2)
    with col_d:
        trip_date = st.date_input("Дата прибытия:")
    with col_t:
        trip_time = st.time_input("Время прибытия:")

    transport_mode = st.selectbox(
        "Способ передвижения:",
        ["На автомобиле (Driving)", "Общественный transport (Transit)", "Пешком / На велосипеде"]
    )
    notes = st.text_area("Дополнительные заметки:")

    submit = trip_form.form_submit_button("📅 Добавить в расписание", use_container_width=True)

    if submit:
        if origin_city.strip() == "" or destination_city.strip() == "":
            st.error("Пожалуйста, обязательно укажите Город отправления и Город прибытия!")
        else:
            full_arrival_datetime = f"{trip_date} {trip_time.strftime('%H:%M')}"
            add_trip(origin_city, origin_address, destination_city, destination_address, full_arrival_datetime,
                     transport_mode, notes)
            st.sidebar.success("Маршрут добавлен в навигатор!")
            st.rerun()

# Главный экран приложения
active_trips = get_active_trips()

st.divider()
# Блок настройки Telegram с понятной инструкцией пользователя
st.subheader("📲 Настройка мобильных уведомлений")

# Добавляем интерактивную шпаргалку, чтобы пользователь знал, какого бота подключать
with st.expander("ℹ️ Инструкция: Как подключить уведомления на телефон за 1 минуту?"):
    st.markdown("""
    1. Откройте Telegram и найдите официального бота-создателя: **[@BotFather](https://t.me)**.
    2. Напишите ему команду `/newbot`, укажите имя и получите длинный секретный **API Token**.
    3. Найдите в поиске бота **[@userinfobot](https://t.me)**, запустите его и скопируйте ваш личный цифровой **ID чата**.
    4. **ОБЯЗАТЕЛЬНО:** Найдите в поиске *вашего созданного бота*, откройте его и нажмите кнопку **Старт / Start** (иначе сервер не сможет написать вам первым!).
    5. Вставьте полученные данные в поля ниже.
    """)

tg_col1, tg_col2 = st.columns(2)
with tg_col1:
    tg_token = st.text_input(
        "Вставьте токен вашего Telegram-бота:",
        type="password",
        key="tg_token_saved",
        help="Длинный ключ, полученный от @BotFather"
    )
with tg_col2:
    tg_chat_id = st.text_input(
        "Вставьте ваш личный Telegram ID чата:",
        type="password",
        key="tg_id_saved",
        help="Цифровой ID, полученный от @userinfobot"
    )

if not active_trips:
    st.info("🛋️ У вас пока нет запланированных поездок. Отдыхайте или добавьте новый маршрут слева!")
else:
    st.subheader("📋 Ваше расписание и умные напоминания (Движок Навигатора)")

    for t_id, t_cit1, t_adr1, t_cit2, t_adr2, t_arr, t_mode, t_notes, t_status in active_trips:
        # Рассчитываем точные междугородние параметры
        timing = calculate_trip_timing(t_cit1, t_adr1, t_cit2, t_adr2, t_arr, t_mode)
        (lat1, lon1), (lat2, lon2) = timing["coords"]

        # Красиво собираем полные адреса для отображения на экране
        full_from = f"{t_cit1}, {t_adr1}" if t_adr1.strip() else t_cit1
        full_to = f"{t_cit2}, {t_adr2}" if t_adr2.strip() else t_cit2

        with st.container(border=True):
            st.markdown(f"### 📍 Из **{full_from}** в **{full_to}**")
            st.caption(f"🗺️ Статус маршрута: {timing['scale_status']}")

            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric("📏 Расстояние по дорогам", f"{timing['distance']} км")
                st.write(f"🚲 **Транспорт:** {t_mode}")
            with c2:
                h = timing['final_time'] // 60
                m = timing['final_time'] % 60
                time_str = f"{h} ч. {m} мин." if h > 0 else f"{m} мин."
                st.metric("⏰ Время в пути", time_str)
                st.write(f"📊 **Ситуация:** {timing['jam_status']}")
            with c3:
                st.metric("🚨 Рекомендуемое время выезда", timing['departure_time'])
                st.write(f"🎯 **Прибытие к:** {t_arr}")

            if t_notes:
                st.caption(f"📝 Заметки: {t_notes}")

            # НАСТОЯЩАЯ ИНТЕРАКТИВНАЯ КАРТА НАВИГАТОРА ОБЩЕГО ПОЛЬЗОВАНИЯ
            route_points = [[lat1, lon1], [lat2, lon2]]
            try:
                # Отправляем исправленный [lon, lat] запрос к OSRM навигатору автомобильных дорог
                osrm_url = f"https://project-osrm.org{lon1},{lat1};{lon2},{lon2}?overview=full&geometries=geojson"
                osrm_response = requests.get(osrm_url, timeout=5)
                if osrm_response.status_code == 200:
                    data = osrm_response.json()
                    if "routes" in data and len(data["routes"]) > 0:
                        geojson_geometry = data["routes"][0]["geometry"]["coordinates"]
                        route_points = [[coord[1], coord[0]] for coord in geojson_geometry]
            except Exception:
                pass

            m = folium.Map(
                location=[(lat1 + lat2) / 2, (lon1 + lon2) / 2],
                tiles='https://{s}.tile.openstreetmap.fr/osmfr/{z}/{x}/{y}.png',
                attr='OpenStreetMap France',
                control_scale=True
            )

            folium.PolyLine(locations=route_points, color="#007aff", weight=6, opacity=0.85).add_to(m)
            folium.Marker([lat1, lon1], tooltip=f"Старт: {full_from}",
                          icon=folium.Icon(color="green", icon="play", prefix="fa")).add_to(m)
            folium.Marker([lat2, lon2], tooltip=f"Финиш: {full_to}",
                          icon=folium.Icon(color="red", icon="flag", prefix="fa")).add_to(m)

            m.fit_bounds([[lat1, lon1], [lat2, lon2]], padding=10)
            folium_static(m, width=700, height=400)

            # Кнопки управления (Разделены ровно на 2 колонки по фиксу ТЗ)
            btn_col1, btn_col2 = st.columns(2)
            with btn_col1:
                if st.button("🗑️ Отменить поездку", key=f"del_{t_id}", type="primary", use_container_width=True):
                    delete_trip(t_id)
                    st.success("Маршрут удален")
                    st.rerun()
            with btn_col2:
                if st.button("📲 Отправить сводку на телефон", key=f"tg_send_{t_id}", type="secondary",
                             use_container_width=True):
                    alert_msg = (
                        f"🚗 УМНЫЙ НАВИГАТОР ПОЕЗДОК\n\n"
                        f"🛫 Из: {full_from}\n"
                        f"🛬 В: {full_to}\n"
                        f"📏 Дистанция: {timing['distance']} км\n"
                        f"⏱️ Время в пути: {time_str}\n\n"
                        f"⚠️ ВЫЕЗЖАЙТЕ В: {timing['departure_time']}"
                    )
                    send_telegram_alert(tg_token, tg_chat_id, alert_msg)
                    st.success("🚀 Сводка отправлена!")
