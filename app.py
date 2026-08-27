import streamlit as st
from datetime import datetime, timedelta
from database import *

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
    st.subheader("📋 Ваше расписание и умные напоминания")

    for t_id, t_orig, t_dest, t_arr, t_mode, t_notes, t_status in active_trips:
        # Запускаем наш умный математический движок расчета пробок
        timing = calculate_trip_timing(t_orig, t_dest, t_arr, t_mode)

        with st.container(border=True):
            st.markdown(f"### 📍 Маршрут: Из **{t_orig}** в **{t_dest}**")

            # Строим сетку параметров
            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric("📏 Длина маршрута", f"{timing['distance']} км")
                st.write(f"🚲 **Транспорт:** {t_mode}")
            with c2:
                st.metric("⏰ Время в пути (с пробками)", f"{timing['final_time']} мин")
                st.write(f"📊 **Ситуация:** {timing['jam_status']}")
            with c3:
                # САМАЯ ГЛАВНАЯ ФИЧА: Время, когда нужно выйти из дома!
                st.metric("🚨 Время выезда (ПОРА В ПУТЬ)", timing['departure_time'])
                st.write(f"🎯 **Прибытие к:** {t_arr}")

            if t_notes:
                st.caption(f"📝 Дополнительные параметры: {t_notes}")

            # Рендеринг карты для визуализации логистики
            st.write("🗺️ **Интерактивная карта поездки:**")

            # Кнопки управления внутри контейнера (12 пробелов отступа)
            btn_col1, btn_col2 = st.columns([1, 4])
            with btn_col1:
                if st.button("🗑️ Отменить", key=f"del_{t_id}", type="primary", use_container_width=True):
                    delete_trip(t_id)
                    st.success("Поездка отменена")
                    st.rerun()
            with btn_col2:
                if st.button("📲 Прислать напоминание в Telegram", key=f"tg_send_{t_id}", type="secondary",
                             use_container_width=True):
                    if not tg_token or not tg_chat_id:
                        st.error("Сначала заполните настройки Telegram-уведомлений выше!")
                    else:
                        alert_msg = (
                            f"🔔 НАПОМИНАНИЕ О ПОЕЗДКЕ!\n\n"
                            f"📍 Маршрут: {t_orig} ➔ {t_dest}\n"
                            f"🚲 Транспорт: {t_mode}\n"
                            f"🚨 Ситуация: {timing['jam_status']}\n\n"
                            f"⏱️ Итоговое время в пути: {timing['final_time']} мин.\n"
                            f"⚠️ ВАМ НУЖНО ВЫЕХАТЬ В: {timing['departure_time']}"
                        )
                        success = send_telegram_alert(tg_token, tg_chat_id, alert_msg)
                        if success:
                            st.success("🚀 Напоминание отправлено!")
                        else:
                            st.error("❌ Ошибка сети. Проверьте VPN или правильность токена/ID!")
