import requests
from datetime import datetime, timedelta

# Konfiguration
SCHOOL_NAME = "elgym"
ENTITY_ID = 15159
# Wir starten die Abfrage fest beim 14. September 2026
START_DATE_STR = "2026-09-14"

def fetch_timetable():
    start_date = datetime.strptime(START_DATE_STR, "%Y-%m-%d")
    ical_events = []
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Content-Type": "application/json"
    }

    # Wir holen die Woche vom 14.09. und die darauffolgenden 5 Wochen ab
    for week_offset in range(0, 6):
        target_date = (start_date + timedelta(weeks=week_offset)).strftime("%Y-%m-%d")
        
        api_url = f"https://webuntis.com{ENTITY_ID}&date={target_date}&formatId=3&schoolName={SCHOOL_NAME}"
        
        try:
            print(f"Lade Daten für Woche ab: {target_date}...")
            response = requests.get(api_url, headers=headers)
            if response.status_code != 200:
                continue
                
            data = response.json()
            result = data.get("data", {}).get("result", {})
            
            elements = {el["id"]: el for el in result.get("elements", [])}
            periods = result.get("periods", [])
            
            for p in periods:
                p_date = str(p["date"])
                
                def parse_time(t_num):
                    t_str = str(t_num).zfill(4)
                    return t_str[:2], t_str[2:]
                
                sh, sm = parse_time(p["startTime"])
                eh, em = parse_time(p["endTime"])
                
                dt_start = f"{p_date}T{sh}{sm}00"
                dt_end = f"{p_date}T{eh}{em}00"
                
                subject = ""
                teacher = ""
                room = ""
                
                for el_ref in p.get("elements", []):
                    el_id = el_ref["id"]
                    el_type = el_ref["type"]
                    if el_id in elements:
                        name = elements[el_id].get("longName", elements[el_id].get("name", ""))
                        if el_type == 3:
                            subject = name
                        elif el_type == 2:
                            teacher = name
                        elif el_type == 4:
                            room = name
                
                uid = f"uid-{p['id']}-{p_date}@webuntis"
                summary = subject if subject else "Unterricht"
                description = f"Lehrer: {teacher}" if teacher else ""
                
                event = [
                    "BEGIN:VEVENT",
                    f"UID:{uid}",
                    f"DTSTART;TZID=Europe/Vienna:{dt_start}",
                    f"DTEND;TZID=Europe/Vienna:{dt_end}",
                    f"SUMMARY:{summary}",
                    f"LOCATION:{room}",
                    f"DESCRIPTION:{description}",
                    "END:VEVENT"
                ]
                ical_events.append("\n".join(event))
                
        except Exception as e:
            print(f"Fehler in Woche {target_date}: {e}")

    ical_content = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//WebUntis Extractor//DE",
        "X-WR-CALNAME:Stundenplan ELGYM",
        "X-WR-TIMEZONE:Europe/Vienna",
        "\n".join(ical_events),
        "END:VCALENDAR"
    ]
    
    with open("stundenplan.ics", "w", encoding="utf-8") as f:
        f.write("\n".join(ical_content))
    print(f"Fertig! {len(ical_events)} Termine wurden gespeichert.")

if __name__ == "__main__":
    fetch_timetable()
