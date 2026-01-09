# app.py
# -----------------------------------------------------
# SMART WASTE COLLECTION ROUTING SYSTEM – WEB (CSV UPLOAD)
# -----------------------------------------------------
# Run:
#   pip install flask pandas folium requests
#   python app.py
# Open:
#   http://127.0.0.1:5000

from flask import Flask, render_template_string, request
import math, heapq, folium, pandas as pd, requests
from folium.plugins import AntPath

app = Flask(__name__)

# ------------------ CORE LOGIC (UNCHANGED) ------------------

def haversine(a, b):
    R = 6371
    lat1, lon1 = a
    lat2, lon2 = b
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    h = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * \
        math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return 2 * R * math.asin(math.sqrt(h))

TRAFFIC = {
    "1": {"peak": 1.4, "off": 1.0},
    "2": {"peak": 2.0, "off": 1.2},
    "3": {"peak": 2.8, "off": 1.6}
}

def traffic_factor(minute, cfg):
    hour = minute // 60
    if 7 <= hour <= 10 or 17 <= hour <= 20:
        return cfg["peak"]
    return cfg["off"]


def travel_time(a, b, start, cfg):
    speed = 30
    base = (haversine(a, b) / speed) * 60
    return base * traffic_factor(start, cfg)


def road_path(a, b):
    url = f"http://router.project-osrm.org/route/v1/driving/{a[1]},{a[0]};{b[1]},{b[0]}?overview=full&geometries=geojson"
    try:
        r = requests.get(url, timeout=5)
        coords = r.json()["routes"][0]["geometry"]["coordinates"]
        return [(lat, lon) for lon, lat in coords]
    except:
        return [a, b]


def dijkstra(start, end, nodes, start_time, cfg):
    pq = [(0, start, [start])]
    visited = set()
    while pq:
        cost, u, path = heapq.heappop(pq)
        if u == end:
            return path, cost
        if u in visited:
            continue
        visited.add(u)
        for v in nodes:
            if v != u and v not in visited:
                t = travel_time(u, v, start_time + cost, cfg)
                heapq.heappush(pq, (cost + t, v, path + [v]))
    return [], float("inf")


def build_routes(sctps, gvps, vehicles, capacity, traffic_cfg):
    for g in gvps:
        g["sctp"] = min(range(len(sctps)), key=lambda i: haversine(g["coord"], sctps[i]["coord"]))

    m = folium.Map(location=sctps[0]["coord"], zoom_start=12)

    for s in sctps:
        folium.Marker(s["coord"], popup=s["name"], icon=folium.Icon(color="blue")).add_to(m)
    for g in gvps:
        folium.CircleMarker(g["coord"], radius=4, color="red", fill=True).add_to(m)

    colors = ["green", "purple", "orange", "black", "darkred"]

    for i, sctp in enumerate(sctps):
        depot = sctp["coord"]
        points = [g for g in gvps if g["sctp"] == i]
        nodes = [depot] + [g["coord"] for g in points]
        routes = [{"path": [depot], "pos": depot, "time": 480, "load": 0} for _ in range(vehicles)]

        for g in points:
            for r in routes:
                if r["load"] + g["waste"] <= capacity:
                    path, cost = dijkstra(r["pos"], g["coord"], nodes, r["time"], traffic_cfg)
                    r["path"].extend(path[1:])
                    r["pos"] = g["coord"]
                    r["time"] += cost
                    r["load"] += g["waste"]
                    break

        for idx, r in enumerate(routes):
            r["path"].append(depot)
            road = []
            for j in range(len(r["path"]) - 1):
                road.extend(road_path(r["path"][j], r["path"][j + 1]))
            AntPath(road, color=colors[idx % len(colors)], weight=4, tooltip=f"Vehicle {idx+1}").add_to(m)

    return m

# ------------------ WEB UI ------------------

HTML = """
<!doctype html>
<html>
<head>
<title>Smart Waste Routing (CSV Upload)</title>
<style>
body{font-family:Arial;background:#f4f6f8;padding:40px}
.box{background:white;padding:25px;border-radius:8px;max-width:600px}
input,select{width:100%;padding:8px;margin:8px 0}
button{padding:10px 20px;background:#0b5ed7;color:white;border:none}
</style>
</head>
<body>
<h2>Smart Waste Collection Routing System</h2>
<div class="box">
<form method="post" enctype="multipart/form-data">

<label>Traffic Scenario</label>
<select name="traffic">
<option value="1">Normal</option>
<option value="2">Peak</option>
<option value="3">Festival</option>
</select>

<label>SCTP CSV (name,lat,lon)</label>
<input type="file" name="sctp" required>

<label>GVP CSV (lat,lon,waste,tw_start,tw_end)</label>
<input type="file" name="gvp" required>

<label>Config CSV (vehicles,capacity)</label>
<input type="file" name="config" required>

<button type="submit">Generate Routes</button>
</form>
</div>
</body>
</html>
"""

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        traffic_cfg = TRAFFIC[request.form['traffic']]

        sctp_df = pd.read_csv(request.files['sctp'])
        gvp_df = pd.read_csv(request.files['gvp'])
        cfg = pd.read_csv(request.files['config']).iloc[0]

        sctps = [{"name": r.name, "coord": (r.lat, r.lon)} for _, r in sctp_df.iterrows()]
        gvps = [{
            "coord": (r.lat, r.lon),
            "waste": r.waste,
            "tw": (r.tw_start * 60, r.tw_end * 60)
        } for _, r in gvp_df.iterrows()]

        fmap = build_routes(sctps, gvps, int(cfg.vehicles), int(cfg.capacity), traffic_cfg)
        return fmap._repr_html_()

    return render_template_string(HTML)

if __name__ == '__main__':
    app.run(debug=True)
