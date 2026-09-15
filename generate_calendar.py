import requests
from datetime import date, timedelta, datetime
from icalendar import Calendar, Event

GROUP_ID = 45122

SEMESTER_START = date(2026, 9, 14)
SEMESTER_END = date(2026, 12, 31)

API_URL = f"https://ruz.spbstu.ru/api/v1/ruz/scheduler/{GROUP_ID}"


def get_week_schedule(day):
    response = requests.get(
        API_URL,
        params={"date": day.isoformat()},
        timeout=30,
        headers={
            "User-Agent": "Mozilla/5.0"
        }
    )

    print("API status:", response.status_code)
    print("API URL:", response.url)

    response.raise_for_status()

    data = response.json()

    print("Ответ API:")
    print(data)

    return data


def parse_time(value):
    return datetime.strptime(value, "%H:%M").time()


def main():

    # Проверяем API на первой неделе
    test_data = get_week_schedule(SEMESTER_START)

    # Пока НЕ создаём пустой календарь молча.
    # Если API не содержит ожидаемые данные,
    # workflow должен остановиться с понятной ошибкой.

    if not test_data:
        raise RuntimeError("API СПбПУ вернул пустой ответ.")

    print("Тип ответа:", type(test_data))

    if isinstance(test_data, dict):
        print("Ключи ответа:", list(test_data.keys()))

    calendar = Calendar()

    calendar.add("prodid", "-//SPbPU RUZ Calendar//")
    calendar.add("version", "2.0")
    calendar.add("calscale", "GREGORIAN")
    calendar.add("X-WR-CALNAME", "СПбПУ — расписание")
    calendar.add("X-WR-TIMEZONE", "Europe/Moscow")

    current_week = SEMESTER_START
    total_events = 0

    while current_week <= SEMESTER_END:

        print()
        print("=" * 50)
        print("Неделя:", current_week)
        print("=" * 50)

        data = get_week_schedule(current_week)

        # Ищем возможные варианты названия списка дней
        days = None

        if isinstance(data, dict):
            for key in ["days", "week", "schedule", "items"]:
                if isinstance(data.get(key), list):
                    days = data[key]
                    print("Найден список:", key)
                    break

        if days is None:
            print("Не удалось найти список дней.")
            current_week += timedelta(days=7)
            continue

        for day_data in days:

            if not isinstance(day_data, dict):
                continue

            day_date_string = (
                day_data.get("date")
                or day_data.get("day")
                or day_data.get("dateStart")
            )

            if not day_date_string:
                continue

            try:
                lesson_date = date.fromisoformat(
                    str(day_date_string)[:10]
                )
            except ValueError:
                continue

            if not (
                SEMESTER_START
                <= lesson_date
                <= SEMESTER_END
            ):
                continue

            lessons = (
                day_data.get("lessons")
                or day_data.get("pairs")
                or day_data.get("schedule")
                or []
            )

            for lesson in lessons:

                if not isinstance(lesson, dict):
                    continue

                title = (
                    lesson.get("subject")
                    or lesson.get("name")
                    or lesson.get("discipline")
                    or "Занятие"
                )

                start = (
                    lesson.get("startTime")
                    or lesson.get("start")
                    or lesson.get("start_time")
                )

                end = (
                    lesson.get("endTime")
                    or lesson.get("end")
                    or lesson.get("end_time")
                )

                if not start or not end:
                    continue

                try:
                    start_time = parse_time(str(start)[:5])
                    end_time = parse_time(str(end)[:5])
                except ValueError:
                    continue

                event = Event()

                event.add(
                    "uid",
                    f"spbpu-{GROUP_ID}-"
                    f"{lesson_date}-{start}-{title}"
                )

                event.add("summary", str(title))

                event.add(
                    "dtstart",
                    datetime.combine(
                        lesson_date,
                        start_time
                    )
                )

                event.add(
                    "dtend",
                    datetime.combine(
                        lesson_date,
                        end_time
                    )
                )

                room = (
                    lesson.get("auditory")
                    or lesson.get("auditoryName")
                    or lesson.get("room")
                    or lesson.get("classroom")
                )

                if room:
                    event.add("location", str(room))

                teacher = (
                    lesson.get("teacher")
                    or lesson.get("teacherName")
                )

                if teacher:
                    event.add(
                        "description",
                        f"Преподаватель: {teacher}"
                    )

                calendar.add_component(event)

                total_events += 1

        current_week += timedelta(days=7)

    print()
    print("=" * 50)
    print("Всего найдено занятий:", total_events)
    print("=" * 50)

    if total_events == 0:
        raise RuntimeError(
            "Не найдено ни одного занятия. "
            "Скрипт остановлен, чтобы не создать пустой schedule.ics."
        )

    with open("schedule.ics", "wb") as file:
        file.write(calendar.to_ical())

    print("schedule.ics успешно создан.")


if __name__ == "__main__":
    main()
