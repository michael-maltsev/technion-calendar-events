import json
import os
import re
import sys
from datetime import date, datetime, timedelta
from typing import Any

import requests
from icalendar import Calendar

ICS_URL = "https://www.admin.technion.ac.il/dpcalendar/Student.ics"


def to_date(dt: date | datetime) -> date:
    return dt.date() if isinstance(dt, datetime) else dt


def is_no_class_event(summary: str) -> bool:
    no_class_phrases = {
        "אין לימודים",
        "אין פעילות טכניונית",
        "אין פעילות טכניניות",
        "לא מתקיימת פעילות טכניונית",
    }

    chunks = re.split(r"[,.\-]", summary)
    if any(re.sub(r"\s+", " ", c).strip() in no_class_phrases for c in chunks):
        return True

    if "אין לימודים" in summary or "פעילות" in summary:
        print(f"Warning: Unrecognized no-class event summary: '{summary}'")

    return False


def parse_semester_event(summary: str) -> tuple[bool, str] | None:
    """Parse a semester boundary event. Returns (is_start, sem_code) or None."""
    semester_re = re.compile(
        r"(^|,\s*)"
        r"(?P<role>פתיחת|תחילת|סיום|יום אחרון ל)\s*"
        r"(?P<what>שנ[תה] הלימודים|סמסטר)"
        r"(\s+(?P<season>חורף|אביב|קיץ))?"
    )

    m = semester_re.search(summary)
    if not m:
        return None

    role = m.group("role")
    what = m.group("what")
    season = m.group("season")

    is_start = role in ("פתיחת", "תחילת")

    # "שנת/שנה הלימודים" is always winter semester opening
    if "הלימודים" in what:
        return is_start, "01"

    if season is None:
        print(f"Warning: semester event without season: '{summary}'")
        return None

    semester_type_map = {
        "חורף": "01",
        "אביב": "02",
        "קיץ": "03",
    }

    sem_type = semester_type_map.get(season)
    if sem_type is None:
        print(f"Warning: unknown semester season '{season}' in: '{summary}'")
        return None

    return is_start, sem_type


def academic_year(event_date: date, sem_type: str) -> int:
    if sem_type == "01":
        return event_date.year if event_date.month >= 8 else event_date.year - 1
    return event_date.year - 1


def fetch_ics() -> str:
    url = os.environ.get("ICS_URL_OVERRIDE", ICS_URL)
    resp = requests.get(url)
    resp.raise_for_status()
    return resp.text


def fetch_and_parse() -> dict[str, Any]:
    content = fetch_ics()
    cal = Calendar.from_ical(content)

    semesters = {}
    off_days = set()

    for ev in cal.walk("VEVENT"):
        summary = str(ev.get("SUMMARY", ""))
        dtstart = to_date(ev.get("DTSTART").dt)
        dtend = to_date(ev.get("DTEND").dt)

        # Collect days off
        if is_no_class_event(summary):
            d = dtstart
            while d < dtend:
                off_days.add(d)
                d += timedelta(days=1)

        # Collect semester boundaries
        parsed = parse_semester_event(summary)
        if parsed:
            is_start, st = parsed
            code = f"{academic_year(dtstart, st)}{st}"
            semesters.setdefault(code, {"startDate": None, "endDate": None})
            if is_start:
                semesters[code]["startDate"] = dtstart
            else:
                semesters[code]["endDate"] = dtstart

    # Assign days off to each semester
    sorted_codes = sorted(semesters)
    for i, code in enumerate(sorted_codes):
        sem = semesters[code]
        start = sem["startDate"]
        end = sem["endDate"]
        # If no end date, use day before next semester starts
        if end is None and i + 1 < len(sorted_codes):
            next_start = semesters[sorted_codes[i + 1]]["startDate"]
            if next_start:
                end = next_start - timedelta(days=1)
        sem["daysOff"] = sorted(
            d
            for d in off_days
            if (start is None or d >= start) and (end is None or d <= end)
        )

    # Format output
    result = {}
    for code in sorted_codes:
        sem = semesters[code]
        result[code] = {
            "startDate": sem["startDate"].isoformat() if sem["startDate"] else None,
            "endDate": sem["endDate"].isoformat() if sem["endDate"] else None,
            "daysOff": [d.isoformat() for d in sem["daysOff"]],
        }

    return result


def format_json(data: Any) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False)


def main() -> None:
    output_path = sys.argv[1] if len(sys.argv) > 1 else "-"
    result = fetch_and_parse()

    if output_path == "-":
        print(format_json(result))
        return

    os.makedirs(output_path, exist_ok=True)

    with open(os.path.join(output_path, "latest.json"), "w", encoding="utf-8") as f:
        f.write(format_json(result))

    for code, sem_data in result.items():
        with open(
            os.path.join(output_path, f"{code}.json"), "w", encoding="utf-8"
        ) as f:
            f.write(format_json(sem_data))


if __name__ == "__main__":
    main()
