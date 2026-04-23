import xml.etree.ElementTree as ET
import math, json

NS = {"g": "http://www.topografix.com/GPX/1/1"}
tree = ET.parse("KDF_Marathon.gpx")

pts = []
for trkpt in tree.iter("{http://www.topografix.com/GPX/1/1}trkpt"):
    lat = float(trkpt.get("lat"))
    lon = float(trkpt.get("lon"))
    ele_el = trkpt.find("g:ele", NS)
    ele = float(ele_el.text) if ele_el is not None else None
    pts.append((lat, lon, ele))

R = 6371000.0
def hav(a, b):
    lat1, lon1, _ = a
    lat2, lon2, _ = b
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = p2 - p1
    dl = math.radians(lon2 - lon1)
    h = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2*R*math.asin(math.sqrt(h))

cum = [0.0]
for i in range(1, len(pts)):
    cum.append(cum[-1] + hav(pts[i-1], pts[i]))

mi = 1609.344
total_mi = cum[-1] / mi
print(f"Total: {total_mi:.3f} mi, {len(pts)} pts")

# Downsample to ~600 points evenly along distance for the route polyline
target = 600
step = cum[-1] / (target - 1)
sampled = []  # [lat, lon, ele_ft, dist_mi]
j = 0
for k in range(target):
    target_d = k * step
    while j < len(cum)-1 and cum[j+1] < target_d:
        j += 1
    sampled.append({
        "lat": round(pts[j][0], 6),
        "lon": round(pts[j][1], 6),
        "ele": round(pts[j][2] * 3.28084, 1),
        "mi": round(cum[j] / mi, 4),
    })

# Mile markers - find the first point past each mile
miles = []
for m in range(1, int(total_mi)+1):
    target_d = m * mi
    j = 0
    while j < len(cum)-1 and cum[j] < target_d:
        j += 1
    miles.append({
        "mile": m,
        "lat": round(pts[j][0], 6),
        "lon": round(pts[j][1], 6),
        "ele": round(pts[j][2] * 3.28084, 1),
    })

# Per-mile elevation summary (5m sampled gain/loss)
def ele_at(d):
    lo, hi = 0, len(cum)-1
    while lo < hi:
        m = (lo+hi)//2
        if cum[m] < d: lo = m+1
        else: hi = m
    return pts[lo][2]

mile_summary = []
for m in range(1, int(total_mi)+2):
    s = (m-1) * mi
    e = min(m * mi, cum[-1])
    if s >= cum[-1]: break
    g = l = 0.0
    prev = ele_at(s)
    d = s + 5
    while d <= e:
        ee = ele_at(d)
        diff = ee - prev
        if diff > 0: g += diff
        else: l -= diff
        prev = ee
        d += 5
    mile_summary.append({
        "mile": m,
        "gain_ft": round(g * 3.28084, 1),
        "loss_ft": round(l * 3.28084, 1),
        "start_ft": round(ele_at(s) * 3.28084, 1),
        "end_ft": round(ele_at(e) * 3.28084, 1),
    })

# Bounding box
lats = [p[0] for p in pts]
lons = [p[1] for p in pts]
bbox = [min(lats), min(lons), max(lats), max(lons)]

start = {"lat": pts[0][0], "lon": pts[0][1]}
finish = {"lat": pts[-1][0], "lon": pts[-1][1]}

out = {
    "totalMi": round(total_mi, 3),
    "bbox": bbox,
    "start": start,
    "finish": finish,
    "route": sampled,
    "miles": miles,
    "mileSummary": mile_summary,
}

with open("route_data.json", "w") as f:
    json.dump(out, f)

print(f"Wrote route_data.json ({len(sampled)} route pts, {len(miles)} mile markers)")
