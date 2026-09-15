import requests
from datetime import date, timedelta, datetime
from icalendar import Calendar, Event

GROUP_ID = 45122

# Первый и последний день семестра
SEMESTER_START = date(2026, 9, 14)
SEMESTER_END = date(2026, 12, 31)

API_URL = f"https://ruz.spbstu.ru/api/v1/ruz/scheduler/{GROUP_ID}"


def get_week_schedule(day):
    """Получает расписание группы на неделю."""
    response = requests.get(
        API_URL,
        params={"date": day.isoformat()},
        timeout=30
    )
    response.raise_for_status()
    return response.json()


def parse_time(value):
    """Преобразует время HH:MM в объект time."""
    return datetime.strptime(value, "%H:%M").time()


def main():
    calendar = Calendar()

    calendar.add("prodid", "-//SPbPU RUZ Calendar//")
    calendar.add("version", "2.0")
    calendar.add("calscale", "GREGORIAN")
    calendar.add("X-WR-CALNAME", "СПбПУ — расписание")
    calendar.add("X-WR-TIMEZONE", "Europe/Moscow")

    current_week = SEMESTER_START
    processed_weeks = set()

    while current_week <= SEMESTER_END:

        # Защита от повторной обработки одной недели
        week_key = current_week.isoformat()

        if week_key in processed_weeks:
            current_week += timedelta(days=7)
            continue

        processed_weeks.add(week_key)

        print(f"Получаю расписание недели {current_week}")

        try:
            data = get_week_schedule(current_week)
        except Exception as e:
            print(f"Ошибка при получении {current_week}: {e}")
            current_week += timedelta(days=7)
            continue

        # Структура API может немного отличаться,
        # поэтому пытаемся найти список занятий.
        days = data.get("days", [])

        for day_data in days:

            day_date_string = day_data.get("date")

            if not day_date_string:
                continue

            try:
                lesson_date = date.fromisoformat(
                    day_date_string[:10]
                )
            except ValueError:
                continue

            if lesson_date < SEMESTER_START or lesson_date > SEMESTER_END:
                continue

            lessons = day_data.get("lessons", [])

            for lesson in lessons:

                title = (
                    lesson.get("subject")
                    or lesson.get("name")
                    or "Занятие"
                )

                start = lesson.get("startTime")
                end = lesson.get("endTime")

                if not start or not end:
                    continue

                try:
                    start_time = parse_time(start)
                    end_time = parse_time(end)
                except ValueError:
                    continue

                event = Event()

                event.add(
                    "uid",
                    f"spbpu-{GROUP_ID}-{lesson_date}-{start}-{title}"
                )

                event.add(
                    "summary",
                    title
                )

                event.add(
                    "dtstart",
                    datetime.combine(lesson_date, start_time)
                )

                event.add(
                    "dtend",
                    datetime.combine(lesson_date, end_time)
                )

                # Аудитория
                room = (
                    lesson.get("auditory")
                    or lesson.get("room")
                    or lesson.get("auditoryName")
                )

                if room:
                    event.add("location", room)

                # Преподаватель
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

        current_week += timedelta(days=7)

    with open("schedule.ics", "wb") as file:
        file.write(calendar.to_ical())

    print("Готово: schedule.ics")


if __name__ == "__main__":
    main()
