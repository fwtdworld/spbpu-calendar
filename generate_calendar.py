```python
import requests
from datetime import date, timedelta, datetime, timezone
from icalendar import Calendar, Event

GROUP_ID = 45122

# Осенний семестр 2026
SEMESTER_START = date(2026, 9, 14)
SEMESTER_END = date(2026, 12, 31)

API_URL = f"https://ruz.spbstu.ru/api/v1/ruz/scheduler/{GROUP_ID}"


def get_week_schedule(day):
    response = requests.get(
        API_URL,
        params={"date": day.isoformat()},
        timeout=30,
        headers={"User-Agent": "Mozilla/5.0"}
    )

    response.raise_for_status()
    return response.json()


def parse_date(value):
    return date.fromisoformat(str(value)[:10])


def parse_time(value):
    return datetime.strptime(str(value)[:5], "%H:%M").time()


def main():

    calendar = Calendar()

    calendar.add("prodid", "-//SPbPU RUZ Calendar//Sofia//")
    calendar.add("version", "2.0")
    calendar.add("calscale", "GREGORIAN")
    calendar.add("X-WR-CALNAME", "СПбПУ — 3332705/60001")
    calendar.add("X-WR-TIMEZONE", "Europe/Moscow")
    calendar.add("X-WR-CALDESC", "Расписание СПбПУ, группа 3332705/60001")

    current_week = SEMESTER_START

    total_events = 0
    processed_weeks = 0

    while current_week <= SEMESTER_END:

        print(f"Получаю неделю: {current_week}")

        try:
            data = get_week_schedule(current_week)
        except Exception as error:
            print(f"Ошибка API: {error}")
            current_week += timedelta(days=7)
            continue

        days = data.get("days", [])

        for day_data in days:

            lesson_date = parse_date(day_data["date"])

            if not (
                SEMESTER_START
                <= lesson_date
                <= SEMESTER_END
            ):
                continue

            for lesson in day_data.get("lessons", []):

                subject = lesson.get(
                    "subject",
                    "Занятие"
                )

                start = lesson.get("time_start")
                end = lesson.get("time_end")

                if not start or not end:
                    continue

                start_time = parse_time(start)
                end_time = parse_time(end)

                # Тип занятия
                lesson_type = (
                    lesson.get("typeObj", {})
                    .get("name", "")
                )

                summary = subject

                if lesson_type:
                    summary += f" ({lesson_type})"

                # Аудитория
                auditories = lesson.get("auditories") or []

                location = ""

                if auditories:

                    auditorium = auditories[0]

                    room = auditorium.get("name", "")

                    building = auditorium.get(
                        "building",
                        {}
                    )

                    building_name = building.get(
                        "name",
                        ""
                    )

                    if building_name and room:
                        location = (
                            f"{building_name}, "
                            f"ауд. {room}"
                        )
                    elif room:
                        location = f"ауд. {room}"

                # Преподаватель
                teachers = lesson.get("teachers") or []

                teacher_names = []

                for teacher in teachers:

                    name = teacher.get("full_name")

                    if name:
                        teacher_names.append(name)

                description_parts = []

                if teacher_names:
                    description_parts.append(
                        "Преподаватель: "
                        + ", ".join(teacher_names)
                    )

                additional_info = lesson.get(
                    "additional_info"
                )

                if additional_info:
                    description_parts.append(
                        f"Дополнительно: {additional_info}"
                    )

                description = "\n".join(
                    description_parts
                )

                # --------------------------------
                # Создаём событие
                # --------------------------------

                event = Event()

                uid = (
                    f"spbpu-{GROUP_ID}-"
                    f"{lesson_date.isoformat()}-"
                    f"{start}-{end}-"
                    f"{subject}-"
                    f"{lesson.get('type', 0)}-"
                    f"{lesson.get('additional_info', '')}"
                )

                event.add("uid", uid)

                # Время в Москве → UTC
                start_local = datetime.combine(
                    lesson_date,
                    start_time
                )

                end_local = datetime.combine(
                    lesson_date,
                    end_time
                )

                moscow_offset = timedelta(hours=3)

                start_utc = (
                    start_local - moscow_offset
                ).replace(tzinfo=timezone.utc)

                end_utc = (
                    end_local - moscow_offset
                ).replace(tzinfo=timezone.utc)

                event.add("dtstart", start_utc)
                event.add("dtend", end_utc)

                # Обязательная отметка времени создания
                event.add(
                    "dtstamp",
                    datetime.now(timezone.utc)
                )

                event.add(
                    "summary",
                    summary
                )

                event.add(
                    "status",
                    "CONFIRMED"
                )

                event.add(
                    "sequence",
                    0
                )

                if location:
                    event.add(
                        "location",
                        location
                    )

                if description:
                    event.add(
                        "description",
                        description
                    )

                calendar.add_component(event)

                total_events += 1

        processed_weeks += 1
        current_week += timedelta(days=7)

    print()
    print("=" * 50)
    print(f"Обработано недель: {processed_weeks}")
    print(f"Найдено занятий: {total_events}")
    print("=" * 50)

    if total_events == 0:
        raise RuntimeError(
            "API не вернул ни одного занятия."
        )

    with open(
        "schedule.ics",
        "wb"
    ) as file:

        file.write(
            calendar.to_ical()
        )

    print("schedule.ics успешно создан!")


if __name__ == "__main__":
    main()
```
