import os
import requests
from datetime import datetime, timedelta

# Konfiguration
SCHOOL_NAME = "elgym"
ENTITY_ID = 15159
START_DATE_STR = "2026-09-14"

# Daten aus den GitHub Secrets laden
USERNAME = os.environ.get("UNTIS_USER")
PASSWORD = os.environ.get("UNTIS_PASSWORD")

def fetch_timetable():
    if not USERNAME or not PASSWORD:
        print("Fehler: Keine Zugangsdaten in den Secrets gefunden!")
        return

    ical_events = []
    start_date = datetime.strptime(START_DATE_STR, "%Y-%m-%d")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Content-Type": "application/json",
        "X-Requested-With": "XMLHttpRequest"
    }

    session = requests.Session()

    # 1. Schritt: Login
    login_url = f"https://webuntis.com"
    login_data = {"username": USERNAME, "password": PASSWORD, "school": SCHOOL_NAME}
    
    try:
        print("Melde bei WebUntis an...")
        login_res = session.post(login_url, json=login_data, headers=headers, timeout=12)
        if login_res.status_code != 200:
            print(f"Login fehlgeschlagen ({login_res.status_code})")
            return
        print("Login erfolgreich!")
    except Exception as e:
        print(f"Login-Fehler: {e}")
        return

    # 2. Schritt: Wir testen elementType=1 (Klasse) und elementType=5 (Schüler)
    # Da WebUntis-Links manchmal uneindeutig sind, probieren wir beide durch!
    for element_type in [1, 5]:
        print(f"Versuche Daten abzurufen für elementType={element_type}...")
        temporary_events = []
        
        for week_offset in range(0, 4):
            target_date = (start_date + timedelta(weeks=week_offset)).strftime("%Y-%m-%d")
            
            # Wir testen sowohl die interne als auch die öffentliche API-Route mit aktiver Session
            for api_route in ["timetable/weekly/data", "public/timetable/weekly/data"]:
                api_url = f"https://webuntis.com{api_route}?elementType={element_type}&elementId={ENTITY_ID}&date={target_date}&formatId=3&schoolName={SCHOOL_NAME}"
                
                try:
                    response = session.get(api_url, headers=headers, timeout=12)
                    if response.status_code != 200:
                        continue
                        
                    data = response.json()
                    result = data.get("data", {}).get("result", {})
                    periods = result.get("periods", [])
                    
                    if periods:
                        print(f"-> Erfolg! {len(periods)} Termine gefunden für Typ {element_type} via {api_route} (Woche {target_date})")
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
                                el_type = el_ref["type"]
                                if el_id in elements:
                                    name = elements[el_id].get("longName", elements[el_id].get("name", ""))
                                    if el_type == 3: subject = name
                                    elif el_type == 4: room = name
                            
                            uid = f"uid-{p['id']}-{p_date}@webuntis"
                            summary = subject if subject else "Unterricht"
                            
                            event = [
                                "BEGIN:VEVENT",
                                f"UID:{uid}",
                                f"DTSTART;TZID=Europe/Vienna:{p_date}T{sh}{sm}00",
                                f"DTEND;TZID=Europe/Vienna:{p_date}T{eh}{em}00",
                                f"SUMMARY:{summary}",
                                f"LOCATION:{room}",
                                "END:VEVENT"
                            ]
                            temporary_events.append("\n".join(event))
                        break # Wenn diese Route für die Woche klappte, nächste Woche ansehen
                        
                except Exception as e:
                    print(f"Fehler bei Typ {element_type}: {e}")
                    
        if temporary_events:
            ical_events.extend(temporary_events)
            print(f"Gesamt {len(temporary_events)} Termine für elementType={element_type} gesichert.")
            break # Wenn wir erfolgreich Termine extrahiert haben, brechen wir die Suche ab

    # 3. Schritt: Speichern
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
    print(f"Fertig! Datei wurde mit {len(ical_events)} Terminen geschrieben.")

if __name__ == "__main__":
    fetch_timetable()
