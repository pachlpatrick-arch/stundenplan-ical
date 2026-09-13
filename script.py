import requests
from datetime import datetime, timedelta
import os

# Konfiguration
SCHOOL_NAME = "elgym"
ENTITY_ID = 15159  # Deine ID aus dem Link
BASE_URL = f"https://webuntis.com"

def fetch_timetable():
    # Wir holen die aktuelle Woche und die nächsten 4 Wochen ab
    today = datetime.now()
    ical_events = []
    
    # Header simulieren einen echten Browser
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Content-Type": "application/json"
    }

    # Schleife über die nächsten Wochen, um ausreichend Daten zu puffern
    for week_offset in range(0, 6):
        target_date = (today + timedelta(weeks=week_offset)).strftime("%Y-%m-%d")
        
        # API-URL für den öffentlichen Stundenplan
        api_url = f"https://webuntis.com?elementType=1&elementId={ENTITY_ID}&date={target_date}&formatId=3&schoolName={SCHOOL_NAME}"
        
        try:
            response = requests.get(api_url, headers=headers)
            if response.status_code != 200:
                print(f"Fehler bei Datum {target_date}: Status {response.status_code}")
                continue
                
            data = response.json()
            result = data.get("data", {}).get("result", {})
            
            # WebUntis liefert getrennte Listen für Elemente (Fächer, Lehrer) und die eigentlichen Perioden
            elements = {el["id"]: el for el in result.get("elements", [])}
            periods = result.get("periods", [])
            
            for p in periods:
                # Datum parsen (Format: YYYYMMDD)
                p_date = str(p["date"])
                
                # Start- und Endzeit parsen (WebUntis speichert z.B. 800 für 08:00 oder 1035 für 10:35)
                def parse_time(t_num):
                    t_str = str(t_num).zfill(4)
                    return t_str[:2], t_str[2:]
                
                sh, sm = parse_time(p["startTime"])
                eh, em = parse_time(p["endTime"])
                
                dt_start = f"{p_date}T{sh}{sm}00"
                dt_end = f"{p_date}T{eh}{em}00"
                
                # Fächer und Details zuordnen
                subject = ""
                teacher = ""
                room = ""
                
                for el_ref in p.get("elements", []):
                    el_id = el_ref["id"]
                    el_type = el_ref["type"]
                    if el_id in elements:
                        name = elements[el_id].get("longName", elements[el_id].get("name", ""))
                        if el_type == 3: # Fach
                            subject = name
                        elif el_type == 2: # Lehrer
                            teacher = name
                        elif el_type == 4: # Raum
                            room = name
                
                # iCal Event Block generieren
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
            print(f"Fehler beim Verarbeiten der Woche {target_date}: {e}")

    # Komplettes iCal-Format zusammenbauen
    ical_content = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//WebUntis Extractor//DE",
        "X-WR-CALNAME:Stundenplan",
        "X-WR-TIMEZONE:Europe/Vienna",
        "\n".join(ical_events),
        "END:VCALENDAR"
    ]
    
    # Datei abspeichern
    with open("stundenplan.ics", "w", encoding="utf-8") as f:
        f.write("\n".join(ical_content))
    print("Stundenplan erfolgreich als stundenplan.ics gespeichert!")

if __name__ == "__main__":
    fetch_timetable()
