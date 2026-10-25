import os
import requests
from datetime import datetime, timedelta, timezone

TEAMS = {"knicks": "ny", "jazz": "utah"}  # ESPN team codes

# Alerts (minutes). Set to None to turn an alert off.
ALERT_BEFORE_MINUTES = 60   # alert this long before the game starts
ALERT_AFTER_MINUTES = 30    # alert this long after the game's scheduled end

BASE = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/teams/{}/schedule"
FMT = "%Y%m%dT%H%M%SZ"


def score_of(c):
    s = c.get("score")
    if isinstance(s, dict):
        return s.get("displayValue", "0")
    return str(s) if s is not None else "0"


def fetch_events(code):
    events = {}
    for seasontype in (2, 3):  # 2 = regular season, 3 = playoffs
        r = requests.get(BASE.format(code), params={"seasontype": seasontype}, timeout=30)
        if r.ok:
            for e in r.json().get("events", []):
                events[e["id"]] = e
    return events.values()


def build(name, code):
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        f"PRODID:-//{name}//NBA//EN",
        f"X-WR-CALNAME:{name.title()} Games",
        "REFRESH-INTERVAL;VALUE=DURATION:PT3H",
    ]
    now = datetime.now(timezone.utc).strftime(FMT)

    for e in fetch_events(code):
        comp = e["competitions"][0]
        home = next(c for c in comp["competitors"] if c["homeAway"] == "home")
        away = next(c for c in comp["competitors"] if c["homeAway"] == "away")
        start = datetime.fromisoformat(e["date"].replace("Z", "+00:00"))
        end = start + timedelta(hours=2, minutes=30)
        away_name = away["team"]["displayName"]
        home_name = home["team"]["displayName"]
        completed = comp["status"]["type"].get("completed")

        title = f"{away_name} @ {home_name}"
        if completed:
            mine = home if home["team"].get("abbreviation", "").lower() == code else away
            result = "W" if mine.get("winner") else "L"
            title = f"{result} | {away_name} {score_of(away)} @ {home_name} {score_of(home)}"

        lines += [
            "BEGIN:VEVENT",
            f"UID:espn-{e['id']}@nba-cal",
            f"DTSTAMP:{now}",
            f"DTSTART:{start.strftime(FMT)}",
            f"DTEND:{end.strftime(FMT)}",
            f"SUMMARY:{title}",
        ]

        # Alerts only for games that haven't finished yet
        if not completed:
            if ALERT_BEFORE_MINUTES is not None:
                lines += [
                    "BEGIN:VALARM",
                    "ACTION:DISPLAY",
                    f"DESCRIPTION:Game starts in {ALERT_BEFORE_MINUTES} minutes",
                    f"TRIGGER:-PT{ALERT_BEFORE_MINUTES}M",
                    "END:VALARM",
                ]
            if ALERT_AFTER_MINUTES is not None:
                lines += [
                    "BEGIN:VALARM",
                    "ACTION:DISPLAY",
                    "DESCRIPTION:Game should be over - check the score",
                    f"TRIGGER;RELATED=END:PT{ALERT_AFTER_MINUTES}M",
                    "END:VALARM",
                ]

        lines.append("END:VEVENT")

    lines.append("END:VCALENDAR")
    return "\r\n".join(lines)


if __name__ == "__main__":
    os.makedirs("docs", exist_ok=True)
    for name, code in TEAMS.items():
        with open(f"docs/{name}.ics", "w", encoding="utf-8") as f:
            f.write(build(name, code))
