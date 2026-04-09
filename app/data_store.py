import json
import csv
import io
import urllib.request
from dataclasses import dataclass

@dataclass
class DetentionCenter:
    id: str; name: str; operator: str; state: str; city: str; lat: float; lng: float;
    status: str; capacity: int; category: str = "Detention"; note: str = "";
    population: int = 0; deaths: int = 0; pregnancies: int = 0

    def to_dict(self):
        return {
            "id": self.id, "name": self.name, "operator": self.operator,
            "state": self.state, "city": self.city, "lat": self.lat,
            "lng": self.lng, "status": self.status, "capacity": self.capacity,
            "category": self.category, "note": self.note, "population": self.population,
            "deaths": self.deaths, "pregnancies": self.pregnancies
        }

FACILITIES = []

def sync_live_data():
    global FACILITIES
    FACILITIES.clear()

    # 1. Inject Priority Intelligence (WIRED Sites & Sensitive Targets)
    FACILITIES.extend([
        DetentionCenter("tx-elpaso-camp", "ERO El Paso Camp Montana", "ICE", "Texas", "El Paso", 31.7619, -106.4850, "operational", 5000, "Detention", "Verified deaths: Victor Diaz, Geraldo Campos.", 2954, 2, 0),
        DetentionCenter("wire-ca-irv", "Irvine Surge Office", "GSA/ERO", "California", "Irvine", 33.6850, -117.8450, "expansion", 0, "Office", "Verified via WIRED memo."),
        DetentionCenter("wire-tx-wood", "The Woodlands OPLA", "GSA/OPLA", "Texas", "The Woodlands", 30.1600, -95.4610, "planned", 0, "Office", "Blocks from Primrose preschool."),
        DetentionCenter("wire-nj-rose", "Roseland Office Hub", "GSA/ERO", "New Jersey", "Roseland", 40.8217, -74.3101, "expansion", 0, "Office", "Near Roseland Child Development Center."),
        DetentionCenter("sens-pa-hill", "Hillside Elementary", "Civilian", "Pennsylvania", "Berwyn", 40.0600, -75.4600, "civilian", 0, "Sensitive", "Near planned Berwyn surge office.")
    ])

    # 2. Live Self-Healing Telemetry: Vera Institute Raw GitHub Feed
    try:
        url = "https://raw.githubusercontent.com/vera-institute/ice-detention-trends/main/metadata/facilities.csv"
        req = urllib.request.Request(url, headers={'User-Agent': 'Aegis-Tracker/3.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            decoded = response.read().decode('utf-8', errors='ignore')
            reader = csv.DictReader(io.StringIO(decoded))
            added_codes = {"tx-elpaso-camp"}

            for row in reader:
                code = row.get('detention_facility_code', '').strip()
                if code in added_codes or not code: continue

                lat_str = row.get('latitude', '')
                lng_str = row.get('longitude', '')

                if lat_str and lng_str and lat_str.strip().upper() != 'NA':
                    try:
                        FACILITIES.append(DetentionCenter(
                            id=code,
                            name=row.get('detention_facility_name', 'Unknown Facility'),
                            operator="ICE/IGSA",
                            state=row.get('state', 'US'),
                            city=row.get('city', 'Unknown'),
                            lat=float(lat_str),
                            lng=float(lng_str),
                            status="operational",
                            capacity=0,
                            category="Detention",
                            note="Verified geolocation via Vera Institute live feed."
                        ))
                        added_codes.add(code)
                    except ValueError:
                        pass

    except Exception as e:
        print(f"Live sync failed: {e}. Proceeding with cached priority intelligence.")
        # Fallback core nodes to ensure map is never empty if completely offline
        fallback = [
            (34.52, -117.43, "Adelanto IPC", "CA"), (32.04, -84.79, "Stewart DC", "GA"),
            (28.89, -99.09, "South Texas IPC", "TX"), (47.23, -122.42, "Northwest IPC", "WA")
        ]
        for idx, (la, lo, name, st) in enumerate(fallback):
            FACILITIES.append(DetentionCenter(f"fb-{idx}", name, "GEO/CoreCivic", st, "", la, lo, "operational", 1500))

sync_live_data()

def get_stats():
    return {
        "total": len(FACILITIES),
        "active": sum(1 for f in FACILITIES if f.status in ("operational", "expansion")),
        "total_beds": 108500,
        "total_pop": 68440,
        "total_deaths": 46,
        "total_pregs": 121
    }

def get_facilities_as_json():
    return json.dumps([f.to_dict() for f in FACILITIES], indent=2)
