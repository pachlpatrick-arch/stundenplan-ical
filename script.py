import os
import requests
from datetime import datetime, timedelta

SCHOOL_NAME = "elgym"
START_DATE_STR = "2026-09-14"

USERNAME = os.environ.get("UNTIS_USER")
PASSWORD = os.environ.get("UNTIS_PASSWORD")

def fetch_timetable():
    logs = []
    ical_events = []
    
    logs.append(f"Starte Skript um {datetime.now().isoformat()}")
    
    if not USERNAME or not PASSWORD:
        logs.append("FEHLER: UNTIS_USER oder UNTIS_PASSWORD fehlt in den Secrets!")
        write_debug_ical(ical_events, logs)
        return

    start_date = datetime.strptime(START_DATE_STR, "%Y-%m-%d")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Content-Type": "application/json",
        "X-Requested-With": "XMLHttpRequest"
    }

    session = requests.Session()

    # 1. Schritt: Login
    login_url = f"https://webuntis.com"
    login_data = {"username": USERNAME, "password": PASSWORD, "school": SCHOOL_NAME}
    
    try:
        logs.append("Sende Login-Anfrage an WebUntis...")
        login_res = session.post(login_url, json=login_data, headers=headers, timeout=12)
        logs.append(f"Login-Antwort Statuscode: {login_res.status_code}")
        
        if login_res.status_code != 200:
            logs.append(f"FEHLER: Login fehlgeschlagen. Text: {login_res.text[:200]}")
            write_debug_ical(ical_events, logs)
            return
            
        login_json = login_res.json()
        person_id = login_json.get("data", {}).get("personId")
        logs.append(f"Login erfolgreich! Erkannte personId: {person_id}")
    except Exception as e:
        logs.append(f"FEHLER beim Login-Prozess: {str(e)}")
        write_debug_ical(ical_events, logs)
        return

    # 2. Schritt: Daten abrufen (Wir testen die automatische Route OHNE IDs und MIT IDs)
    for week_offset in range(0, 3):
        target_date = (start_date + timedelta(weeks=week_offset)).strftime("%Y-%m-%d")
        logs.append(f"--- Prüfe Woche ab {target_date} ---")
        
        # Test 1: Die Standard-Route für den aktuell angemeldeten Benutzer
        urls_to_test = [
            f"https://webuntis.com{target_date}",
            f"https://webuntis.com{person_id}&date={target_date}&formatId=3"
        ]
        
        for url in urls_to_test:
            try:
                logs.append(f"Rufe URL auf: {url[:80]}...")
                response = session.get(url, headers=headers, timeout=12)
                logs.append(f"Statuscode: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    result = data.get("data", {}).get("result", {})
                    periods = result.get("periods", [])
                    logs.append(f"Gefundene Unterrichtsblöcke: {len(periods)}")
                    
                    if periods:
                        elements = {el["id"]: el for el in result.get("elements", [])}
                        for p in periods:
                            if p.get("is", {}).get("cancelled", False):
                                continue
                            
                            p_date = str(p["date"])
                            sh, sm = str(p["startTime"]).zfill(4)[:2], str(p["startTime"]).zfill(4)[2:]
                            eh, em = str(p["endTime"]).zfill(4)[:2], str(p["endTime"]).zfill(4)[2:]
                            
                            subject = ""
                            room = ""
                            
                            for el_ref in p.get("elements", []):
                                el_id = el_ref["id"]
                                if el_id in elements:
                                    name = elements[el_id].get("longName", elements[el_id].get("name", ""))
                                    if el_ref["type"] == 3: subject = name
                                    elif el_ref["type"] == 4: room = name
                            
                            event = [
                                "BEGIN:VEVENT",
                                f"UID:uid-{p['id']}-{p_date}@webuntis",
                                f"DTSTART;TZID=Europe/Vienna:{p_date}T{sh}{sm}00",
                                f"DTEND;TZID=Europe/Vienna:{p_date}T{eh}{em}00",
                                f"SUMMARY:{subject if subject else 'Unterricht'}",
                                f"LOCATION:{room}",
                                "END:VEVENT"
                            ]
                            ical_events.append("\n".join(event))
                        break # Wenn Termine gefunden wurden, reicht das für diese Woche
            except Exception as e:
                logs.append(f"FEHLER bei Abfrage: {str(e)}")

    write_debug_ical(ical_events, logs)

def write_debug_ical(events, logs):
    # Wir packen die Logs sauber als Beschreibung in den Kalender-Header
    clean_logs = "\\n".join([l.replace(":", "\\:") for l in logs])
    ical_content = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//WebUntis Extractor//DE",
        "X-WR-CALNAME:Stundenplan ELGYM",
        "X-WR-TIMEZONE:Europe/Vienna",
        f"X-WR-CALDESC:{clean_logs}", # Die Logs sind jetzt die offizielle Kalenderbeschreibung!
        "\n".join(events) if events else "",
        "END:VCALENDAR"
    ]
    with open("stundenplan.ics", "w", encoding="utf-8") as f:
        f.write("\n".join(ical_content))
    print("Datei mit Diagnose-Protokoll gespeichert.")

if __name__ == "__main__":
    fetch_timetable()
