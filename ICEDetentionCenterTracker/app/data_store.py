from dataclasses import dataclass
import json

@dataclass
class DetentionCenter:
    id: str; name: str; operator: str; state: str; city: str; lat: float; lng: float; status: str; capacity: int
    def to_dict(self): return {"id": self.id, "name": self.name, "operator": self.operator, "state": self.state, "city": self.city, "lat": self.lat, "lng": self.lng, "status": self.status, "capacity": self.capacity}

FACILITIES = [
    DetentionCenter("mega-tx-socorro", "Socorro Logistics Hub (Mega Center)", "ICE", "Texas", "Socorro", 31.6540, -106.3030, "construction", 8500),
    DetentionCenter("mega-ga-social", "Social Circle Mega Center", "ICE", "Georgia", "Social Circle", 33.6550, -83.7190, "construction", 10000),
    DetentionCenter("mega-az-surprise", "Surprise Regional Hub", "ICE", "Arizona", "Surprise", 33.6292, -112.3670, "construction", 7500),
    DetentionCenter("tx-elpaso-camp", "ERO El Paso Camp Montana", "ICE", "Texas", "El Paso", 31.7619, -106.4850, "operational", 5000),
    DetentionCenter("ca-calcity-ipc", "California City Processing Center", "CoreCivic", "California", "California City", 35.1258, -117.9858, "operational", 2560),
    DetentionCenter("ca-adelanto-ipc", "Adelanto ICE Processing Center", "GEO Group", "California", "Adelanto", 34.5280, -117.4330, "operational", 1807),
    DetentionCenter("ms-adams-county", "Adams County Detention Center", "CoreCivic", "Mississippi", "Natchez", 31.5604, -91.4031, "operational", 2191),
    DetentionCenter("wa-nw-ipc", "Northwest ICE Processing Center", "GEO Group", "Washington", "Tacoma", 47.2340, -122.4240, "operational", 1575),
    DetentionCenter("fl-baker-county", "Baker County Detention Center", "Local", "Florida", "MacClenny", 30.2831, -82.1228, "operational", 859),
]

def get_stats():
    active = sum(1 for f in FACILITIES if f.status == "operational")
    planned = sum(1 for f in FACILITIES if f.status in ("planned", "construction"))
    return {"total": 212, "active": active, "planned": planned, "total_beds": 73000, "states": 42}

def get_facilities_as_json(): return json.dumps([f.to_dict() for f in FACILITIES], indent=2)
