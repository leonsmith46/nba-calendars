import os
import requests
from datetime import datetime, timedelta, timezone

TEAMS = {"knicks": "ny", "jazz": "utah"}  # ESPN team codes
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
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", f"PRODID:-//{name}//NBA//EN",
             f"X-WR-CALNAME:{name.title()} Games",
             "REFRESH-INTERVAL;VALUE=DURATION:PT3H"]
    now = datetime.now(timezone.utc).strftime(FMT)
    for e in fetch_events(code):
        comp = e["competitions"][0]
        home = next(c for c in comp["competitors"] if c["homeAway"] == "home")
        away = next(c for c in comp["competitors"] if c["homeAway"] == "away")
        start = datetime.fromisoformat(e["date"].replace("Z", "+00:00"))
        end = start + timedelta(hours=2, minutes=30)
        away_name = away["team"]["displayName"]
        home_name = home["team"]["displayName"]
        title = f"{away_name} @ {home_name}"
        if comp["status"]["type"].get("completed"):
            mine = home if home["team"].get("abbreviation", "").lower() == code else away
            result = "W" if mine.get("winner") else "L"
            title = f"{result} | {away_name} {score_of(away)} @ {home_name} {score_of(home)}"
        lines += ["BEGIN:VEVENT",
                  f"UID:espn-{e['id']}@nba-cal",
                  f"DTSTAMP:{now}",
                  f"DTSTART:{start.strftime(FMT)}",
                  f"DTEND:{end.strftime(FMT)}",
                  f"SUMMARY:{title}",
                  "END:VEVENT"]
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines)

if __name__ == "__main__":
    os.makedirs("docs", exist_ok=True)
    for name, code in TEAMS.items():
        with open(f"docs/{name}.ics", "w", encoding="utf-8") as f:
            f.write(build(name, code))
