import streamlit as st
from datetime import datetime, timedelta
from database import *
from streamlit_folium import st_folium
import folium

# Инициализируем БД
init_db()

st.set_page_config(page_title="Помощник поездок", page_icon="🚗", layout="wide")

st.title("🚗 Умный помощник управления расписанием поездок")
st.write("Планируйте маршруты, рассчитывайте время выезда с учетом пробок и получайте уведомления!")


# Боковая панель для добавления новой поездки (Исправленный вариант)
st.sidebar.header("🗺️ Запланировать поездку")

# 1. Присваиваем форму переменной trip_form
trip_form = st.sidebar.form("add_trip_form", clear_on_submit=True)

with trip_form:
    origin = st.text_input("Откуда (А—Пункт):", placeholder="Например: ул. Ленина, 10")
    destination = st.text_input("Куда (Б—Пункт):", placeholder="Например: Аэропорт")

    col_d, col_t = st.columns(2)
    with col_d:
        trip_date = st.date_input("Дата прибытия:")
    with col_t:
        trip_time = st.time_input("Время, к которому нужно приехать:")

    transport_mode = st.selectbox(
        "Способ передвижения:",
        ["На автомобиле (Driving)", "Общественный транспорт (Transit)", "Пешком (Walking)", "На велосипеде (Bicycling)"]
    )
    notes = st.text_area("Дополнительные параметры / Заметки:")

    # 2. Вызываем кнопку отправки СТРОГО через объект формы trip_form (с 4 пробелами отступа!)
    submit = trip_form.form_submit_button("📅 Добавить в расписание", use_container_width=True)

    if submit:
        if origin.strip() == "" or destination.strip() == "":
            st.error("Заполните точки А и Б!")
        else:
            full_arrival_datetime = f"{trip_date} {trip_time.strftime('%H:%M')}"
            add_trip(origin, destination, full_arrival_datetime, transport_mode, notes)
            st.sidebar.success("Поездка успешно запланирована!")
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

    for t_id, t_orig, t_dest, t_arr, t_mode, t_notes, t_status in active_trips:
        # Считаем глобальные параметры поездки
        timing = calculate_trip_timing(t_orig, t_dest, t_arr, t_mode)
        (lat1, lon1), (lat2, lon2) = timing["coords"]

        with st.container(border=True):
            st.markdown(f"### 📍 Маршрут: Из **{t_orig}** в **{t_dest}**")
            st.caption(f"🗺️ Масштаб: {timing['scale_status']}")

            # Строим сетку метрик навигатора
            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric("📏 Расстояние по дорогам", f"{timing['distance']} км")
                st.write(f"🚲 **Транспорт:** {t_mode}")
            with c2:
                # Конвертируем минуты в читаемые Часы и Минуты
                h = timing['final_time'] // 60
                m = timing['final_time'] % 60
                time_str = f"{h} ч. {m} мин." if h > 0 else f"{m} мин."
                st.metric("⏰ Время в пути (с задержками)", time_str)
                st.write(f"📊 **Дорожная ситуация:** {timing['jam_status']}")
            with c3:
                st.metric("🚨 Рекомендуемое время выезда", timing['departure_time'])
                st.write(f"🎯 **Прибытие к:** {t_arr}")

            if t_notes:
                st.caption(f"📝 Детали поездки: {t_notes}")


            # НАСТОЯЩАЯ ИНТЕРАКТИВНАЯ КАРТА НАВИГАТОРА В СТИЛЕ 2ГИС (БЕЗОТКАЗНЫЙ ВАРИАНТ)
            st.write("🗺️ **Маршрут путешествия на интерактивной карте:**")

            # 1. Вычисляем центр карты между точкой А и точкой Б
            center_lat = (lat1 + lat2) / 2
            center_lon = (lon1 + lon2) / 2

            # 2. Создаем карту со стабильным шлюзом, который РАБОТАЕТ В РФ БЕЗ VPN
            # Используем красивый, детальный светлый стиль Positron
            m = folium.Map(
                location=[center_lat, center_lon],
                tiles='https://cartocdn.com',
                attr='CartoDB OpenStreetMap',
                control_scale=True
            )

            # 3. СТРОИМ РЕАЛЬНЫЙ МАРШРУТ ПО ТРАССАМ ОБЩЕГО ПОЛЬЗОВАНИЯ (Навигационный API OSRM)
            route_points = [[lat1, lon1], [lat2, lon2]]  # Запасной вариант (прямая линия)

            try:
                # Отправляем запрос на глобальный сервер маршрутизации автомобиля
                # OSRM принимает координаты в строгом формате: Долгота,Широта
                osrm_url = f"https://project-osrm.org{lon1},{lat1};{lon2},{lon2}?overview=full&geometries=geojson"
                osrm_response = requests.get(osrm_url, timeout=4)

                if osrm_response.status_code == 200:
                    data = osrm_response.json()
                    if "routes" in data and len(data["routes"]) > 0:
                        # Получаем гео-координаты сотен промежуточных поворотов реальной трассы
                        geojson_geometry = data["routes"][0]["geometry"]["coordinates"]
                        # Конвертируем обратно в формат Folium [Широта, Долгота]
                        route_points = [[coord[1], coord[0]] for coord in geojson_geometry]
            except Exception:
                pass  # Если шлюз навигации занят, нарисуется базовая линия

            # 4. Рисуем реальную извилистую автомобильную трассу со всеми поворотами
            folium.PolyLine(
                locations=route_points,
                color="#1e88e5",  # Красивый синий цвет навигатора 2ГИС
                weight=6,
                opacity=0.85
            ).add_to(m)

            # 5. Ставим маркер для точки отправления (А)
            folium.Marker(
                [lat1, lon1],
                tooltip=f"Старт: {t_orig}",
                icon=folium.Icon(color="green", icon="play", prefix="fa")
            ).add_to(m)

            # 6. Ставим маркер для пункта назначения (Б)
            folium.Marker(
                [lat2, lon2],
                tooltip=f"Финиш: {t_dest}",
                icon=folium.Icon(color="red", icon="flag", prefix="fa")
            ).add_to(m)

            # 7. АВТО-МАСШТАБ: Карта сама подгонит фокус, чтобы оба города были идеально видны на экране
            m.fit_bounds([[lat1, lon1], [lat2, lon2]], padding=[30, 30])

            # 8. Рендерим готовую карту на экран Streamlit
            st_folium(m, width="100%", height=420, key=f"map_folium_v5_{t_id}")


            # Кнопки управления (12 пробелов отступа внутри контейнера)
            btn_col1, btn_col2 = st.columns(2)
            with btn_col1:
                if st.button("🗑️ Отменить поездку", key=f"del_{t_id}", type="primary", use_container_width=True):
                    delete_trip(t_id)
                    st.success("Поездка отменена")
                    st.rerun()
            with btn_col2:
                if st.button("📲 Отправить сводку на телефон", key=f"tg_send_{t_id}", type="secondary",
                             use_container_width=True):
                    if not tg_token or not tg_chat_id:
                        st.error("Сначала заполните настройки Telegram-уведомлений выше!")
                    else:
                        alert_msg = (
                            f"🚗 ГЛОБАЛЬНЫЙ НАВИГАТОР ПОЕЗДОК\n\n"
                            f"📍 Маршрут: {t_orig} ➔ {t_dest}\n"
                            f"🌍 Статус: {timing['scale_status']}\n"
                            f"📏 Дистанция: {timing['distance']} км\n"
                            f"📊 Дороги: {timing['jam_status']}\n\n"
                            f"⏱️ Время в пути: {time_str}\n"
                            f"🎯 Прибытие к: {t_arr}\n"
                            f"🚨 ВЫЕЗЖАЙТЕ: {timing['departure_time']}"
                        )
                        success = send_telegram_alert(tg_token, tg_chat_id, alert_msg)
                        if success:
                            st.success("🚀 Сводка навигатора отправлена в Telegram!")
                        else:
                            st.error("❌ Ошибка отправки. Проверьте настройки бота.")
