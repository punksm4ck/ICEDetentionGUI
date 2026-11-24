import csv
import io
import json
import math
import sqlite3
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

CACHE_DIR = Path.home() / ".local/share/ice-investigative-tracker"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = CACHE_DIR / "intel_cache.db"

HOME_COORDS = (34.2694, -118.7815)

@dataclass
class DetentionCenter:
    id: str
    name: str
    operator: str
    state: str
    city: str
    lat: float
    lng: float
    status: str
    capacity: int
    category: str = "Detention"
    source: str = "Vera/ICE"
    note: str = ""
    population: int = 0
    deaths: int = 0
    pregnancies: int = 0
    non_criminal_pct: float = 0.0

    def distance_miles(self, origin=HOME_COORDS):
        r = 3958.8
        phi1, phi2 = math.radians(origin[0]), math.radians(self.lat)
        dphi = math.radians(self.lat - origin[0])
        dlam = math.radians(self.lng - origin[1])
        a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
        return round(r * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)), 1)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "operator": self.operator,
            "state": self.state,
            "city": self.city,
            "lat": self.lat,
            "lng": self.lng,
            "status": self.status,
            "capacity": self.capacity,
            "category": self.category,
            "source": self.source,
            "note": self.note,
            "population": self.population,
            "deaths": self.deaths,
            "pregnancies": self.pregnancies,
            "non_criminal_pct": self.non_criminal_pct,
            "distance_mi": self.distance_miles()
        }

FACILITIES = []
LAST_SYNC_STATUS = "Initialized"

PRIORITY_INTEL = [
    DetentionCenter("tx-elpaso-camp", "ERO El Paso Camp East Montana", "ICE / Amentum", "TX", "El Paso", 31.7619, -106.4850, "operational", 5000, "Detention", "TRAC / Vera 2026", "Top national ADP leader (2,026-2,954). Verified deaths: Victor Diaz, Geraldo Campos.", 2954, 2, 0, 72.1),
    DetentionCenter("ga-stewart", "Stewart Detention Center", "CoreCivic", "GA", "Lumpkin", 32.0435, -84.7891, "operational", 2040, "Detention", "TRAC 2026", "Major Southeast hub; sustained near-capacity ADP.", 2010, 4, 3, 69.8),
    DetentionCenter("ms-adams", "Adams County Correctional Center", "CoreCivic", "MS", "Natchez", 31.5604, -91.3210, "operational", 2200, "Detention", "TRAC 2026", "High-volume Gulf Coast transfer hub.", 1878, 1, 2, 71.4),
    DetentionCenter("tx-southtexas", "South Texas ICE Processing Center", "GEO Group", "TX", "Pearsall", 28.8914, -99.0950, "operational", 1904, "Detention", "TRAC 2026", "Primary San Antonio AOR intake center.", 1703, 2, 4, 70.2),
    DetentionCenter("ca-adelanto", "Adelanto ICE Processing Center", "GEO Group", "CA", "Adelanto", 34.5586, -117.4419, "operational", 1940, "Detention", "TRAC / Vera 2026", "Largest active Southern California detention facility.", 1686, 3, 2, 68.5),
        DetentionCenter("wa-nwipc-buyout", "Northwest ICE Processing Center", "DHS Federal Buyout (ex-GEO)", "WA", "Tacoma", 47.2529, -122.4111, "buyout", 1575, "Warehouse", "Senate / DHS Nov 2026", "DHS $453M direct federal acquisition under Inspector General scrutiny (Nov 2026).", 1350, 0, 0, 0.0),
    DetentionCenter("ca-calcity-buyout", "California City Immigration Processing Center", "DHS Federal Buyout (ex-CoreCivic)", "CA", "California City", 35.1464, -117.8556, "buyout", 2560, "Warehouse", "TIME / Marshall Project 2026", "Part of $1.5B DHS direct federal acquisition of CoreCivic private prisons.", 1654, 0, 1, 70.9),
    DetentionCenter("fl-alligator", "Florida Soft-Sided Facility-South", "FDEM / DHS", "FL", "Ochopee", 25.9018, -81.3034, "expansion", 2000, "Warehouse", "News / Investigative 2026", "Rapid-deployment soft-sided site ('Alligator Alcatraz'); 1,300-1,800 ADP.", 1550, 0, 0, 74.0),
    DetentionCenter("il-broadview", "Broadview Service Staging Facility", "ICE / ERO", "IL", "Broadview", 41.8639, -87.8534, "staging", 450, "Staging", "Vera / News 2026", "Midwest hold and rapid-transfer staging site omitted from routine public counts.", 310, 0, 0, 73.2),
    DetentionCenter("ca-gilroy-site", "7240 Holsclaw Rd Rural Holding Site", "DHS / Contractor", "CA", "Gilroy", 36.9891, -121.5290, "planned", 600, "Staging", "Investigative 2026", "Contested rural holding and staging site in Santa Clara County.", 0, 0, 0, 70.6),
    DetentionCenter("wire-ca-irv", "Irvine Surge Office (2020 Main St)", "GSA / ERO", "CA", "Irvine", 33.6850, -117.8450, "expansion", 0, "Office", "WIRED Leak Feb 2026", "Secret lease bypassing CICA via compelling urgency loophole.", 0, 0, 0, 70.6),
    DetentionCenter("wire-ca-vannuys", "James C. Corman Federal Building Hub", "GSA / ERO", "CA", "Van Nuys", 34.1856, -118.4487, "expansion", 0, "Office", "WIRED Leak Feb 2026", "Confirmed San Fernando Valley ERO expansion hub.", 0, 0, 0, 70.6),
    DetentionCenter("wire-ca-santaana", "Santa Ana Federal Building Hub", "GSA / ERO", "CA", "Santa Ana", 33.7486, -117.8703, "expansion", 0, "Office", "WIRED Leak Feb 2026", "Orange County federal expansion and processing office.", 0, 0, 0, 70.6),
    DetentionCenter("wire-ca-sandiego", "Edward J. Schwartz Courthouse Hub", "GSA / ERO", "CA", "San Diego", 32.7157, -117.1638, "expansion", 0, "Office", "WIRED Leak Feb 2026", "Confirmed Southern border federal expansion hub.", 0, 0, 0, 70.6),
    DetentionCenter("wire-ca-sac", "John E. Moss Federal Building Hub", "GSA / ERO", "CA", "Sacramento", 38.5805, -121.4997, "expansion", 0, "Office", "WIRED Leak Feb 2026", "Northern California interior enforcement expansion hub.", 0, 0, 0, 70.6),
    DetentionCenter("wire-ca-la", "Los Angeles Federal Expansion Hub", "GSA / ERO", "CA", "Los Angeles", 34.0558, -118.2414, "expansion", 0, "Office", "WIRED Leak Feb 2026", "DTLA federal office surge expansion.", 0, 0, 0, 70.6),
    DetentionCenter("wire-tx-wood", "The Woodlands OPLA Surge Office", "GSA / OPLA", "TX", "The Woodlands", 30.1600, -95.4610, "planned", 0, "Office", "WIRED Leak Feb 2026", "Secret lease blocks from Primrose preschool.", 0, 0, 0, 70.6),
    DetentionCenter("wire-nj-rose", "Roseland Office Hub", "GSA / ERO", "NJ", "Roseland", 40.8217, -74.3101, "expansion", 0, "Office", "WIRED Leak Feb 2026", "Near Roseland Child Development Center.", 0, 0, 0, 70.6),
    DetentionCenter("wire-pa-berwyn", "Berwyn Surge Office", "GSA / ERO", "PA", "Berwyn", 40.0459, -75.4424, "planned", 0, "Office", "WIRED Leak Feb 2026", "Planned suburban surge hub near Hillside Elementary.", 0, 0, 0, 70.6),
    DetentionCenter("wh-tx-dallas", "North Texas Mega-Warehouse Conversion", "DHS / Turnkey", "TX", "Hutchins", 32.6487, -96.7128, "planned", 7500, "Warehouse", "Freedom for Immigrants 2026", "Part of 7+ confirmed warehouse acquisitions targeting 30,000+ beds.", 0, 0, 0, 70.6),
    DetentionCenter("wh-az-phoenix", "West Valley Industrial Holding Warehouse", "DHS / Turnkey", "AZ", "Goodyear", 33.4353, -112.3577, "planned", 5000, "Warehouse", "Freedom for Immigrants 2026", "Planned large-scale industrial conversion facility.", 0, 0, 0, 70.6),
        DetentionCenter("preg-la-basile", "South Louisiana ICE Processing Center (Maternal)", "GEO Group / ICE", "LA", "Basile", 30.4860, -92.6001, "operational", 1000, "Pregnancy", "Guardian / DHS FOIA 2026", "Highest documented miscarriage cluster in 2025 DHS FOIA records (18 national miscarriages Jan-Oct 3, 2025; tracking halted Oct 3, 2025).", 920, 0, 14, 0.0),
    DetentionCenter("preg-nm-otero", "Otero County Processing Center (Maternal)", "MTC / ICE", "NM", "Chaparral", 32.0365, -106.3822, "operational", 1089, "Pregnancy", "Guardian / DHS FOIA 2026", "Documented in-custody miscarriage in 2025 DHS FOIA medical billing records.", 850, 0, 6, 0.0),
    DetentionCenter("preg-ky-campbell", "Campbell County Detention Center (Maternal)", "County / ICE IGSA", "KY", "Newport", 39.0914, -84.4958, "operational", 600, "Pregnancy", "Guardian Sept 2026", "Documented pregnant asylum seeker hospitalized in ER after delayed prenatal/emergency care.", 240, 0, 3, 0.0),
    DetentionCenter("preg-tx-pearsall", "South Texas IPC (Maternal Oversight)", "GEO Group / ICE", "TX", "Pearsall", 28.8935, -99.0920, "operational", 1904, "Pregnancy", "Guardian / DHS FOIA 2026", "Documented miscarriage and pregnant detainee custody reports in 2025-2026.", 1703, 2, 8, 0.0),
    DetentionCenter("preg-ga-stewart", "Stewart Detention Center (Maternal Oversight)", "CoreCivic / ICE", "GA", "Lumpkin", 32.0455, -84.7860, "operational", 2040, "Pregnancy", "ACLU / Senate 2026", "Documented pregnant and postpartum detainees held under medical neglect complaints.", 2010, 4, 5, 0.0),
    DetentionCenter("preg-ca-adelanto", "Adelanto IPC (Maternal Oversight)", "GEO Group / ICE", "CA", "Adelanto", 34.5610, -117.4390, "operational", 1940, "Pregnancy", "LA Times / ACLU 2026", "Southern California hub with reported pregnant detainees held despite 2021 directive.", 1686, 3, 4, 0.0),
    DetentionCenter("sens-pa-hill", "Hillside Elementary", "Civilian", "PA", "Berwyn", 40.0600, -75.4600, "civilian", 0, "Sensitive", "Proximity Watch", "Sensitive school zone near planned Berwyn surge office.", 0, 0, 0, 0.0),
    DetentionCenter("sens-tx-primrose", "Primrose Preschool", "Civilian", "TX", "The Woodlands", 30.1620, -95.4630, "civilian", 0, "Sensitive", "Proximity Watch", "Sensitive childcare zone near The Woodlands OPLA hub.", 0, 0, 0, 0.0),
    DetentionCenter("sens-nj-roseland", "Roseland Child Development Center", "Civilian", "NJ", "Roseland", 40.8225, -74.3115, "civilian", 0, "Sensitive", "Proximity Watch", "Sensitive childcare zone near Roseland ERO hub.", 0, 0, 0, 0.0),
]

def _init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS facilities (
            id TEXT PRIMARY KEY,
            payload TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

def _save_cache(items):
    _init_db()
    now = datetime.now().isoformat()
    conn = sqlite3.connect(DB_PATH)
    conn.execute("DELETE FROM facilities")
    conn.executemany(
        "INSERT OR REPLACE INTO facilities (id, payload, updated_at) VALUES (?, ?, ?)",
        [(f.id, json.dumps(f.to_dict()), now) for f in items]
    )
    conn.commit()
    conn.close()

def _load_cache():
    if not DB_PATH.exists():
        return []
    try:
        conn = sqlite3.connect(DB_PATH)
        rows = conn.execute("SELECT payload FROM facilities").fetchall()
        conn.close()
        loaded = []
        for (raw,) in rows:
            d = json.loads(raw)
            d.pop("distance_mi", None)
            loaded.append(DetentionCenter(**d))
        return loaded
    except Exception:
        return []

def load_initial_data():
    global FACILITIES, LAST_SYNC_STATUS
    cached = _load_cache()
    if cached:
        FACILITIES[:] = cached
        LAST_SYNC_STATUS = f"Loaded {len(FACILITIES)} nodes from local SQLite cache"
    else:
        FACILITIES[:] = PRIORITY_INTEL
        LAST_SYNC_STATUS = f"Loaded {len(FACILITIES)} priority 2026 intelligence nodes"

def sync_live_data():
    global FACILITIES, LAST_SYNC_STATUS
    merged = list(PRIORITY_INTEL)
    added_codes = {f.id for f in merged}
    added_names = {f.name.lower() for f in merged}

    try:
        url = "https://raw.githubusercontent.com/vera-institute/ice-detention-trends/main/metadata/facilities.csv"
        req = urllib.request.Request(url, headers={"User-Agent": "Punksm4ck-ICE-Tracker/4.0"})
        with urllib.request.urlopen(req, timeout=8) as response:
            decoded = response.read().decode("utf-8", errors="ignore")
            reader = csv.DictReader(io.StringIO(decoded))

            for row in reader:
                code = (row.get("detention_facility_code") or "").strip()
                name = (row.get("detention_facility_name") or "Unknown Facility").strip()
                if not code or code in added_codes or name.lower() in added_names:
                    continue

                lat_str = (row.get("latitude") or "").strip()
                lng_str = (row.get("longitude") or "").strip()
                if lat_str and lng_str and lat_str.upper() != "NA" and lng_str.upper() != "NA":
                    try:
                        fac_type = (row.get("type_grouped") or row.get("type_detailed") or "ICE/IGSA").strip()
                        is_staging = any(k in name.lower() or k in fac_type.lower() for k in ("hold", "staging", "processing"))
                        cat = "Staging" if is_staging else "Detention"
                        merged.append(DetentionCenter(
                            id=code,
                            name=name,
                            operator=fac_type or "ICE/IGSA",
                            state=(row.get("state") or "US").strip(),
                            city=(row.get("city") or "Unknown").strip(),
                            lat=float(lat_str),
                            lng=float(lng_str),
                            status="staging" if is_staging else "operational",
                            capacity=0,
                            category=cat,
                            source="Vera GitHub Live",
                            note=f"Synced from Vera Institute open dataset ({fac_type})."
                        ))
                        added_codes.add(code)
                        added_names.add(name.lower())
                    except ValueError:
                        pass

        FACILITIES[:] = merged
        _save_cache(FACILITIES)
        LAST_SYNC_STATUS = f"Live Sync OK: {len(FACILITIES)} nodes ({datetime.now().strftime('%H:%M:%S')})"
        return True, LAST_SYNC_STATUS
    except Exception as e:
        FACILITIES[:] = merged
        LAST_SYNC_STATUS = f"Offline/Cached Mode ({len(FACILITIES)} nodes): {e}"
        return False, LAST_SYNC_STATUS

def get_stats(items=None):
    data = items if items is not None else FACILITIES
    return {
        "total": len(data),
        "detention": sum(1 for f in data if f.category == "Detention"),
        "wired_offices": sum(1 for f in data if f.category == "Office"),
        "warehouses": sum(1 for f in data if f.category == "Warehouse"),
        "staging": sum(1 for f in data if f.category == "Staging"),
        "national_pop": 65765,
        "peak_pop": 73400,
        "non_criminal_pct": 70.6,
        "atd_monitored": 180701,
        "fy26_deaths": 37,
        "term_deaths": 60,
        "reported_pregnancies": 121,
        "miscarriages_2025": 18
    }

def get_facilities_as_json():
    return json.dumps([f.to_dict() for f in FACILITIES])

def export_csv(items, filepath):
    fields = ["id", "name", "category", "operator", "city", "state", "lat", "lng", "status", "capacity", "population", "deaths", "source", "distance_mi", "note"]
    with open(filepath, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for f in items:
            row = f.to_dict()
            writer.writerow({k: row.get(k, "") for k in fields})

def export_geojson(items, filepath):
    features = []
    for f in items:
        props = f.to_dict()
        features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [f.lng, f.lat]},
            "properties": props
        })
    payload = {"type": "FeatureCollection", "features": features}
    with open(filepath, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)

load_initial_data()
