import xml.etree.ElementTree as ET
import math

NS = {"g": "http://www.topografix.com/GPX/1/1"}
tree = ET.parse("KDF_Marathon.gpx")
root = tree.getroot()

pts = []
for trkpt in root.iter("{http://www.topografix.com/GPX/1/1}trkpt"):
    lat = float(trkpt.get("lat"))
    lon = float(trkpt.get("lon"))
    ele_el = trkpt.find("g:ele", NS)
    ele = float(ele_el.text) if ele_el is not None else None
    pts.append((lat, lon, ele))

print(f"Total points: {len(pts)}")

R = 6371000.0

def hav(a, b):
    lat1, lon1, _ = a
    lat2, lon2, _ = b
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = p2 - p1
    dl = math.radians(lon2 - lon1)
    h = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2*R*math.asin(math.sqrt(h))

# Build cumulative distance in meters
cum = [0.0]
for i in range(1, len(pts)):
    cum.append(cum[-1] + hav(pts[i-1], pts[i]))

total_m = cum[-1]
print(f"Total distance: {total_m/1000:.3f} km / {total_m/1609.344:.3f} mi")

eles_m = [p[2] for p in pts]
print(f"Min ele: {min(eles_m):.1f} m  Max ele: {max(eles_m):.1f} m")
print(f"Min ele: {min(eles_m)*3.281:.1f} ft  Max ele: {max(eles_m)*3.281:.1f} ft")

# Smoothed elevation profile by 0.1-mi buckets
mile_m = 1609.344
total_mi = total_m / mile_m

def ele_at(dist_m):
    # binary search-ish
    lo, hi = 0, len(cum)-1
    while lo < hi:
        mid = (lo+hi)//2
        if cum[mid] < dist_m:
            lo = mid+1
        else:
            hi = mid
    return eles_m[lo]

# Per-mile elevation summary
print()
print("Mile | Start ele (ft) | End ele (ft) | Gain (ft) | Loss (ft) | Net (ft)")
print("-----+----------------+--------------+-----------+-----------+---------")
total_gain_ft = 0.0
total_loss_ft = 0.0
for mi in range(1, int(total_mi)+2):
    start_m = (mi-1)*mile_m
    end_m = min(mi*mile_m, total_m)
    if start_m >= total_m:
        break
    # accumulate gain/loss between cumulative points within the mile
    # find indices
    def idx_for(d):
        lo, hi = 0, len(cum)-1
        while lo < hi:
            mid = (lo+hi)//2
            if cum[mid] < d:
                lo = mid+1
            else:
                hi = mid
        return lo
    si = idx_for(start_m)
    ei = idx_for(end_m)
    gain_m = 0.0
    loss_m = 0.0
    # smooth a tiny bit by sampling every ~5m
    sample_step = 5.0
    prev_ele = ele_at(start_m)
    d = start_m + sample_step
    while d <= end_m:
        e = ele_at(d)
        diff = e - prev_ele
        if diff > 0:
            gain_m += diff
        else:
            loss_m += -diff
        prev_ele = e
        d += sample_step
    gain_ft = gain_m * 3.281
    loss_ft = loss_m * 3.281
    total_gain_ft += gain_ft
    total_loss_ft += loss_ft
    se = ele_at(start_m) * 3.281
    ee = ele_at(end_m) * 3.281
    print(f" {mi:>3} | {se:>14.1f} | {ee:>12.1f} | {gain_ft:>9.1f} | {loss_ft:>9.1f} | {ee-se:>+8.1f}")

print()
print(f"Total elevation gain (raw, 5m-sampled): {total_gain_ft:.0f} ft")
print(f"Total elevation loss (raw, 5m-sampled): {total_loss_ft:.0f} ft")

# Also compute with a stronger smoothing (rolling 30m)
import statistics
window = 30  # number of points
sm = []
for i in range(len(eles_m)):
    a = max(0, i-window//2)
    b = min(len(eles_m), i+window//2+1)
    sm.append(sum(eles_m[a:b])/(b-a))

gain_m = loss_m = 0.0
for i in range(1, len(sm)):
    diff = sm[i] - sm[i-1]
    if diff > 0.5/3.281:  # ignore <0.5ft
        gain_m += diff
    elif diff < -0.5/3.281:
        loss_m += -diff
print(f"Smoothed gain: {gain_m*3.281:.0f} ft, loss: {loss_m*3.281:.0f} ft")
