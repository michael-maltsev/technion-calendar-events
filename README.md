# Technion Schedule

Fetches the [Technion academic calendar](https://www.admin.technion.ac.il/dpcalendar/Student.ics) and extracts semester dates and days off into structured JSON.

## Output format

```json
{
  "202601": {
    "startDate": "2026-10-28",
    "endDate": "2027-02-02",
    "daysOff": ["2026-11-05"]
  }
}
```

Semester codes:

| Code | Semester |
|------|----------|
| `01` | Winter   |
| `02` | Spring   |
| `03` | Summer   |

The year portion is the academic year start - `202601` is winter 2026-2027, `202602` is spring 2027.

## Usage

```bash
pip install -r requirements.txt

# Print to stdout
python fetch_and_parse_ical.py -

# Write to directory (creates latest.json + per-semester files)
python fetch_and_parse_ical.py ./output
```

Output files when writing to a directory:
- `latest.json` — all semesters
- `<code>.json` — individual semester (e.g. `202601.json`)

## CI/CD

A GitHub Actions workflow (`.github/workflows/deploy.yml`) runs daily, fetches the calendar, and publishes the JSON files to the `gh-pages` branch.
