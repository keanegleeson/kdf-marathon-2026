"""Build a self-contained interactive race plan HTML with mi/km toggle."""
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

MI = 1609.344
KM = 1000.0
total_m = cum[-1]
total_mi = total_m / MI
total_km = total_m / KM

def ele_at(d):
    lo, hi = 0, len(cum)-1
    while lo < hi:
        m = (lo+hi)//2
        if cum[m] < d: lo = m+1
        else: hi = m
    return pts[lo][2]

def find_index(d):
    lo, hi = 0, len(cum)-1
    while lo < hi:
        m = (lo+hi)//2
        if cum[m] < d: lo = m+1
        else: hi = m
    return lo

# Downsample to ~600 points
target = 600
step = total_m / (target - 1)
sampled = []
j = 0
for k in range(target):
    td = k * step
    while j < len(cum)-1 and cum[j+1] < td:
        j += 1
    sampled.append({
        "lat": round(pts[j][0], 6),
        "lon": round(pts[j][1], 6),
        "ele": round(pts[j][2] * 3.28084, 1),
        "mi": round(cum[j] / MI, 4),
        "km": round(cum[j] / KM, 4),
    })

def markers(unit_m, total_units):
    out = []
    for n in range(1, int(total_units)+1):
        td = n * unit_m
        j = find_index(td)
        out.append({
            "n": n,
            "lat": round(pts[j][0], 6),
            "lon": round(pts[j][1], 6),
            "ele": round(pts[j][2] * 3.28084, 1),
        })
    return out

def per_unit_summary(unit_m, total_units):
    out = []
    for n in range(1, int(total_units)+2):
        s = (n-1) * unit_m
        e = min(n * unit_m, total_m)
        if s >= total_m: break
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
        out.append({
            "n": n,
            "gain_ft": round(g * 3.28084, 1),
            "loss_ft": round(l * 3.28084, 1),
            "start_ft": round(ele_at(s) * 3.28084, 1),
            "end_ft": round(ele_at(e) * 3.28084, 1),
            "frac": round((e-s)/unit_m, 4),  # last unit may be partial
        })
    return out

mile_markers = markers(MI, total_mi)
km_markers = markers(KM, total_km)
mile_summary = per_unit_summary(MI, total_mi)
km_summary = per_unit_summary(KM, total_km)

# Aid stations - approximate, every ~1.5 mi (≈ 2.4 km) from the PDF count
AID_MILES = [1.5, 3.0, 4.5, 6.0, 7.5, 9.0, 10.5, 12.0, 13.5,
             15.0, 16.5, 18.0, 19.5, 21.0, 22.5, 24.0, 25.5]
POWERADE_MILES = {6.0, 12.0, 18.0, 24.0}
MEDICAL_MILES = {6.0, 13.5, 21.0}
FUEL_MILES = [4, 8, 11, 16, 20, 24]

aid_stations = []
for m in AID_MILES:
    j = find_index(m * MI)
    aid_stations.append({
        "mi": m, "km": round(m * MI / KM, 2),
        "lat": round(pts[j][0], 6), "lon": round(pts[j][1], 6),
        "powerade": m in POWERADE_MILES, "medical": m in MEDICAL_MILES,
    })
fuel_points = []
for m in FUEL_MILES:
    j = find_index(m * MI)
    fuel_points.append({"mi": m, "km": round(m * MI / KM, 2),
                        "lat": round(pts[j][0], 6), "lon": round(pts[j][1], 6)})

# Cues keyed by both mi and km
MILE_CUES = {
    1: "Bring it down. Crowd + adrenaline = the #1 KDF blowup. Cap +3 sec/mi (+2 sec/km) over goal.",
    3: "First 5K should be ~20:15 at goal B pace. If under 19:45, slow down NOW.",
    5: "Settle. Find a pack moving your pace and hide in it.",
    8: "Halfway to halfway. Quick form check: shoulders, hips, breathing.",
    10: "Mild +20 ft bump - last warning shot before the climb.",
    11: "Take a gel + full cup of fluid here. You climb in 1 mile - fuel BEFORE.",
    12: "THE CLIMB. +94 ft sustained. Hold EFFORT, not pace. Lose 20-30s, that's OK.",
    13: "Rolling inside Iroquois. Short stride up, open down. Stay smooth.",
    14: "Still in the park. Don't try to make up the time you lost on mile 12.",
    15: "Net -33 ft. Free pace coming - but DO NOT hammer. Quads matter at mile 23.",
    16: "Big descent (-64 ft net). High cadence, soft feet. 'Fall' downhill.",
    17: "Out of the park. Give it 0.5 mi to find your rhythm again.",
    20: "10K to go. Re-evaluate. On pace + HR sustainable = start nudging 2 sec/mi faster.",
    22: "5K to go. The race starts here.",
    23: "-25 ft mile. Free pace. Cash it in.",
    25: "Pick off one runner at a time. Don't look at the watch - look at backs.",
    26: "Small +20 ft bump near the finish. Empty the tank. You're home.",
}

# Km cues - tied to the same physical features, expressed in km
KM_CUES = {
    2:  "Bring it down. Crowd + adrenaline = the #1 KDF blowup. Cap +2 sec/km over goal.",
    5:  "5K split should be ~20:15 at goal B pace. If you're under 19:45, slow down NOW.",
    8:  "Settle. Find a pack moving your pace and hide in it.",
    13: "Quick form check: shoulders, hips, breathing.",
    16: "Mild +20 ft bump approaching - last warning before the big climb at km 19.",
    18: "Take a gel + full cup of fluid HERE. You climb in 1 km - fuel BEFORE.",
    19: "THE CLIMB STARTS. ~30 m of vertical over the next 1.5 km. EFFORT, not pace. Expect to lose 15-20 sec/km.",
    21: "Rolling inside Iroquois Park. Short stride up, open down. Stay smooth.",
    23: "Still in the park - punchy rollers. Don't try to make up the climb's lost time.",
    25: "Big descent now (~30 m down over 2 km). High cadence, soft feet. Do NOT hammer - quads at km 37 will pay.",
    27: "Out of the park. Give it 1 km to find your rhythm again.",
    32: "10 km to go. Re-evaluate. If on pace + HR sustainable = start nudging 1-2 sec/km faster.",
    35: "5 km to go (a parkrun). The race starts here.",
    37: "-7 m of free pace through here. Cash it in.",
    40: "Pick off one runner at a time. Don't look at the watch - look at backs.",
    42: "Small +6 m bump just before the finish. Empty the tank. You're home.",
}

lats = [p[0] for p in pts]; lons = [p[1] for p in pts]
bbox = [min(lats), min(lons), max(lats), max(lons)]

data = {
    "totalMi": round(total_mi, 3),
    "totalKm": round(total_km, 3),
    "bbox": bbox,
    "start": {"lat": pts[0][0], "lon": pts[0][1]},
    "finish": {"lat": pts[-1][0], "lon": pts[-1][1]},
    "route": sampled,
    "miMarkers": mile_markers,
    "kmMarkers": km_markers,
    "miSummary": mile_summary,
    "kmSummary": km_summary,
    "aidStations": aid_stations,
    "fuelPoints": fuel_points,
    "miCues": MILE_CUES,
    "kmCues": KM_CUES,
}

embedded = json.dumps(data, separators=(",", ":"))

HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<title>2026 KDF Marathon - Race Plan</title>
<meta name="viewport" content="width=device-width,initial-scale=1" />
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"
  integrity="sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY=" crossorigin="" />
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"
  integrity="sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo=" crossorigin=""></script>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<style>
  :root {
    --bg:#0f1419; --panel:#171e26; --panel2:#1f2832; --line:#2a3441;
    --ink:#e6edf3; --ink2:#9aa7b4; --accent:#ff7a45;
    --green:#3fb950; --yellow:#d29922; --red:#f85149; --blue:#58a6ff;
  }
  *{box-sizing:border-box}
  html,body{margin:0;padding:0;background:var(--bg);color:var(--ink);
    font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;font-size:14px}
  header{padding:18px 22px;border-bottom:1px solid var(--line);background:var(--panel);display:flex;justify-content:space-between;align-items:center;gap:14px;flex-wrap:wrap}
  header .title h1{margin:0 0 4px 0;font-size:20px;letter-spacing:.3px}
  .sub{color:var(--ink2);font-size:13px}
  .unit-toggle{display:inline-flex;background:var(--panel2);border:1px solid var(--line);border-radius:8px;overflow:hidden;flex-shrink:0}
  .unit-toggle button{background:transparent;color:var(--ink2);border:0;padding:8px 16px;font-size:13px;font-weight:700;cursor:pointer;letter-spacing:.5px}
  .unit-toggle button.active{background:var(--accent);color:#1a0f0a}
  .container{display:grid;grid-template-columns:1fr 380px;gap:14px;padding:14px;height:calc(100vh - 90px)}
  @media (max-width:1100px){.container{grid-template-columns:1fr;height:auto}}
  .left{display:grid;grid-template-rows:1fr 240px;gap:14px;min-height:0}
  #map{width:100%;height:100%;border-radius:10px;background:#222;min-height:380px}
  .elev{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:8px 12px;position:relative}
  .elev h3{margin:2px 0 4px 0;font-size:13px;color:var(--ink2);font-weight:600;letter-spacing:.5px;text-transform:uppercase}
  .right{background:var(--panel);border:1px solid var(--line);border-radius:10px;display:flex;flex-direction:column;overflow:hidden}
  .goalbar{padding:12px;border-bottom:1px solid var(--line)}
  .goalbar .label{font-size:11px;color:var(--ink2);letter-spacing:.6px;text-transform:uppercase;margin-bottom:8px}
  .goals{display:grid;grid-template-columns:repeat(3,1fr);gap:6px}
  .goal{background:var(--panel2);border:1px solid var(--line);border-radius:8px;padding:8px 6px;text-align:center;cursor:pointer;transition:.15s}
  .goal:hover{border-color:var(--accent)}
  .goal.active{background:var(--accent);border-color:var(--accent);color:#1a0f0a}
  .goal .t{font-size:11px;font-weight:700;letter-spacing:.5px}
  .goal .v{font-size:15px;font-weight:700;margin-top:2px}
  .goal .p{font-size:10px;opacity:.7;margin-top:1px}
  .tabs{display:flex;border-bottom:1px solid var(--line);background:var(--panel2)}
  .tab{flex:1;padding:10px 8px;text-align:center;cursor:pointer;font-size:12px;font-weight:600;color:var(--ink2);letter-spacing:.4px;text-transform:uppercase}
  .tab.active{color:var(--accent);border-bottom:2px solid var(--accent);background:var(--panel)}
  .tabpanel{flex:1;overflow:auto;padding:10px 12px;display:none}
  .tabpanel.active{display:block}
  table{width:100%;border-collapse:collapse;font-size:12px}
  th,td{padding:5px 6px;text-align:right;border-bottom:1px solid var(--line)}
  th{color:var(--ink2);font-weight:600;font-size:10px;letter-spacing:.5px;text-transform:uppercase;text-align:right}
  th:first-child,td:first-child{text-align:left}
  tbody tr:hover{background:var(--panel2)}
  .seg-flat{color:var(--green)}.seg-hill{color:var(--red)}.seg-grind{color:var(--blue)}
  .legend{display:flex;flex-wrap:wrap;gap:10px;font-size:11px;color:var(--ink2);padding:6px 12px;border-top:1px solid var(--line);background:var(--panel2)}
  .legend .dot{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:5px;vertical-align:middle}
  .cue{padding:8px 10px;border-left:3px solid var(--accent);background:var(--panel2);border-radius:0 6px 6px 0;margin-bottom:8px}
  .cue .m{font-weight:700;color:var(--accent);font-size:12px}
  .cue .t{font-size:12px;margin-top:2px;color:var(--ink)}
  .phase{margin-bottom:10px;padding:10px;background:var(--panel2);border-radius:8px;border-left:4px solid var(--green)}
  .phase.hill{border-left-color:var(--red)}
  .phase.grind{border-left-color:var(--blue)}
  .phase h4{margin:0 0 4px 0;font-size:13px}
  .phase p{margin:4px 0 0 0;font-size:12px;color:var(--ink2);line-height:1.45}
  .fuel-row{display:flex;align-items:center;gap:10px;padding:7px 8px;background:var(--panel2);border-radius:6px;margin-bottom:6px}
  .fuel-mile{background:var(--accent);color:#1a0f0a;font-weight:700;border-radius:5px;padding:3px 8px;font-size:12px;min-width:48px;text-align:center}
  .fuel-text{font-size:12px;color:var(--ink);flex:1}
  .mile-marker{background:#1f2832;color:#fff;border:2px solid var(--accent);border-radius:50%;width:22px;height:22px;display:flex;align-items:center;justify-content:center;font-size:10px;font-weight:700}
  .km-marker{background:#1f2832;color:#fff;border:2px solid var(--accent);border-radius:50%;width:20px;height:20px;display:flex;align-items:center;justify-content:center;font-size:9px;font-weight:700}
  .aid-marker{background:#1d4e89;color:#fff;border:2px solid #6cb6ff;border-radius:4px;width:14px;height:14px;display:flex;align-items:center;justify-content:center;font-size:9px;font-weight:700}
  .aid-marker.powerade{background:#7d4dad;border-color:#c8a4ff}
  .aid-marker.medical{background:#a52828;border-color:#ff8888}
  .fuel-marker{background:var(--accent);color:#1a0f0a;border:2px solid #ffd1ba;border-radius:50%;width:18px;height:18px;display:flex;align-items:center;justify-content:center;font-size:10px;font-weight:800}
  .startfin{background:#1f2832;border:3px solid;border-radius:50%;width:20px;height:20px;display:flex;align-items:center;justify-content:center;color:#fff;font-size:10px;font-weight:800}
  .startfin.start{border-color:var(--green)}
  .startfin.finish{border-color:var(--red)}
  .note{font-size:11px;color:var(--ink2);font-style:italic;padding:6px 10px;border-radius:6px;background:var(--panel2);margin-bottom:8px}
</style>
</head>
<body>
<header>
  <div class="title">
    <h1>2026 KDF Marathon - Interactive Race Plan</h1>
    <div class="sub">Course: <span id="totaldist"></span> (per GPX) - Click a goal to refresh splits - Hover the elevation chart to position the marker on the map</div>
  </div>
  <div class="unit-toggle" id="unitToggle">
    <button data-u="mi">Miles</button>
    <button data-u="km" class="active">Kilometers</button>
  </div>
</header>

<div class="container">
  <div class="left">
    <div id="map"></div>
    <div class="elev">
      <h3 id="elevHeader">Elevation profile (ft) - hover to track on map</h3>
      <canvas id="elevChart"></canvas>
    </div>
  </div>

  <div class="right">
    <div class="goalbar">
      <div class="label" id="goalLabel">Goal pace - watch predicts 4:03/km, 35K sim @ 4:08/km felt controlled, you're fresher now + race shoes</div>
      <div class="goals" id="goals"></div>
    </div>

    <div class="tabs" id="tabs">
      <div class="tab active" data-tab="splits">Splits</div>
      <div class="tab" data-tab="phases">Phases</div>
      <div class="tab" data-tab="fuel">Fuel</div>
      <div class="tab" data-tab="cues">Cues</div>
    </div>

    <div class="tabpanel active" data-tab="splits" id="panel-splits">
      <table>
        <thead><tr>
          <th id="hdrUnit">Km</th><th>Pace</th><th>Split</th><th>Cum</th><th>Elev</th>
        </tr></thead>
        <tbody id="splitsBody"></tbody>
      </table>
    </div>

    <div class="tabpanel" data-tab="phases" id="panel-phases">
      <div class="phase">
        <h4 style="color:var(--green)">Phase 1 - Free Miles (<span class="ph1"></span>)</h4>
        <p>Net mildly downhill, gentle rollers. Run goal pace +3 sec/mi (+2 sec/km) MAX. The crowds, downtown energy and slight downhills will tempt you. Resist. Lock onto a pack moving your pace and hide.</p>
      </div>
      <div class="phase hill">
        <h4 style="color:var(--red)">Phase 2 - Iroquois Park (<span class="ph2"></span>)</h4>
        <p>The climb = ~30 m / ~94 ft sustained over ~1.5 km / 1 mi. Hold <b>effort</b>, not pace - expect to lose 15-25 sec/km (or 20-30 sec/mi). Punchy rollers inside the park, then ~30 m / 100 ft of free downhill back out. DO NOT hammer descents - quads will write a check at km 37 / mi 23 you can't cash.</p>
      </div>
      <div class="phase grind">
        <h4 style="color:var(--blue)">Phase 3 - The Grind (<span class="ph3"></span>)</h4>
        <p>Almost dead-flat back via Eastern Pkwy. Out of the park feels weird - give it 1 km / 0.5 mi. Reset rhythm, then with 10K to go (km 32 / mi 20): if HR is sustainable, nudge 1-2 sec/km (2 sec/mi) faster. There's a small free-pace stretch at km 37 / mi 23, then a tiny bump just before the finish.</p>
      </div>
    </div>

    <div class="tabpanel" data-tab="fuel" id="panel-fuel">
      <div class="note">Replicate exactly what you used in the 4/6 race sim (35.22 km @ 4:08/km, 2,380 kcal). 6 gels total at the orange dots on the map.</div>
      <div id="fuelList"></div>
      <div class="note">Water at every aid station from km 5 / mile 3 onward (a couple sips). Use Powerade stops (purple on map) post-Iroquois for sodium.</div>
    </div>

    <div class="tabpanel" data-tab="cues" id="panel-cues">
      <div id="cuesList"></div>
    </div>

    <div class="legend">
      <span><span class="dot" style="background:var(--green)"></span><span class="leg-p1"></span></span>
      <span><span class="dot" style="background:var(--red)"></span><span class="leg-p2"></span></span>
      <span><span class="dot" style="background:var(--blue)"></span><span class="leg-p3"></span></span>
      <span><span class="dot" style="background:#6cb6ff"></span>Water</span>
      <span><span class="dot" style="background:#c8a4ff"></span>Powerade</span>
      <span><span class="dot" style="background:#ff8888"></span>Medical</span>
      <span><span class="dot" style="background:var(--accent)"></span>Fuel</span>
    </div>
  </div>
</div>

<script>
const DATA = __DATA__;

let unit = "km";   // "mi" or "km"

// Phase boundaries in MILES (canonical)
const PHASE_MI = {p1End:11, p2End:16.2};
function phaseColorMi(mi){ if(mi<PHASE_MI.p1End) return "#3fb950"; if(mi<PHASE_MI.p2End) return "#f85149"; return "#58a6ff"; }
function phaseColorKm(km){ return phaseColorMi(km/1.609344); }
function phaseColor(d){ return unit==="mi" ? phaseColorMi(d) : phaseColorKm(d); }
function phaseClass(mi){ if(mi<=11) return "flat"; if(mi<=16) return "hill"; return "grind"; }

// Pace conversions; goals stored in sec/mi
// Set by km pace then convert: 1 km = 1.609344 mi conversion factor for sec/mi
const GOALS = [
  {key:"A", label:"Stretch",   sec_km:240}, // 4:00/km -> 2:48:50 (cert) / 2:50:11 (GPX)
  {key:"B", label:"Watch pred",sec_km:243}, // 4:03/km -> 2:50:55 / 2:52:19
  {key:"C", label:"Sim pace",  sec_km:248}, // 4:08/km -> 2:54:24 / 2:55:51
];
GOALS.forEach(g=>{
  g.sec_mi = g.sec_km * 1.609344;
  g.total = Math.round(g.sec_mi * DATA.totalMi);
});
let activeGoal = "B";

function fmt(t){
  let total=Math.round(t);
  const h=Math.floor(total/3600);
  const m=Math.floor((total%3600)/60);
  const s=total%60;
  return (h?h+":":"")+(h?String(m).padStart(2,"0"):m)+":"+String(s).padStart(2,"0");
}
function paceStr(secPerUnit){
  let total=Math.round(secPerUnit);
  const m=Math.floor(total/60);
  const s=total%60;
  return m+":"+String(s).padStart(2,"0");
}
function unitLabel(){ return unit; }
function totalDist(){ return unit==="mi" ? DATA.totalMi : DATA.totalKm; }
function goalPaceSec(g){ return unit==="mi" ? g.sec_mi : g.sec_km; }
function summary(){ return unit==="mi" ? DATA.miSummary : DATA.kmSummary; }
function markers(){ return unit==="mi" ? DATA.miMarkers : DATA.kmMarkers; }
function cues(){ return unit==="mi" ? DATA.miCues : DATA.kmCues; }

// ===== Map =====
const map = L.map("map", {zoomControl:true}).fitBounds([[DATA.bbox[0],DATA.bbox[1]],[DATA.bbox[2],DATA.bbox[3]]]);
L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
  attribution:'&copy; OpenStreetMap &copy; CARTO', maxZoom:19, subdomains:"abcd"
}).addTo(map);

// Phase-colored route (segmented polylines so colors change at boundaries)
let segPts = []; let prevColor = phaseColorMi(DATA.route[0].mi);
DATA.route.forEach((p)=>{
  const c = phaseColorMi(p.mi);
  if(c!==prevColor && segPts.length){
    L.polyline(segPts,{color:prevColor,weight:5,opacity:.92}).addTo(map);
    segPts = [segPts[segPts.length-1]];
    prevColor = c;
  }
  segPts.push([p.lat,p.lon]);
});
if(segPts.length>1) L.polyline(segPts,{color:prevColor,weight:5,opacity:.92}).addTo(map);

// Layer groups so we can swap unit-dependent markers
const distMarkerLayer = L.layerGroup().addTo(map);
const aidLayer = L.layerGroup().addTo(map);
const fuelLayer = L.layerGroup().addTo(map);

function renderDistanceMarkers(){
  distMarkerLayer.clearLayers();
  const ms = markers();
  const cls = unit==="mi" ? "mile-marker" : "km-marker";
  const sz = unit==="mi" ? 22 : 20;
  ms.forEach(m=>{
    L.marker([m.lat,m.lon], {icon: L.divIcon({className:"",html:`<div class="${cls}">${m.n}</div>`,iconSize:[sz,sz],iconAnchor:[sz/2,sz/2]})})
      .bindTooltip(`${unit==="mi"?"Mile":"Km"} ${m.n} - ${m.ele.toFixed(0)} ft`,{direction:"top"})
      .addTo(distMarkerLayer);
  });
}

function renderAidStations(){
  aidLayer.clearLayers();
  DATA.aidStations.forEach(a=>{
    const cls = a.medical ? "aid-marker medical" : a.powerade ? "aid-marker powerade" : "aid-marker";
    const t = a.medical ? "Medical + Aid" : a.powerade ? "Water + Powerade" : "Water";
    const dist = unit==="mi" ? `Mi ${a.mi.toFixed(1)}` : `Km ${a.km.toFixed(1)}`;
    L.marker([a.lat,a.lon],{icon:L.divIcon({className:"",html:`<div class="${cls}"></div>`,iconSize:[14,14],iconAnchor:[7,7]})})
      .bindTooltip(`~${dist} - ${t}`,{direction:"top"})
      .addTo(aidLayer);
  });
}

function renderFuelMarkers(){
  fuelLayer.clearLayers();
  DATA.fuelPoints.forEach(f=>{
    const dist = unit==="mi" ? `Mi ${f.mi}` : `Km ${f.km.toFixed(1)}`;
    L.marker([f.lat,f.lon],{icon:L.divIcon({className:"",html:`<div class="fuel-marker">G</div>`,iconSize:[18,18],iconAnchor:[9,9]})})
      .bindTooltip(`${dist} - take a gel`,{direction:"top"})
      .addTo(fuelLayer);
  });
}

L.marker([DATA.start.lat,DATA.start.lon],{icon:L.divIcon({className:"",html:`<div class="startfin start">S</div>`,iconSize:[20,20],iconAnchor:[10,10]})})
  .bindTooltip("Start",{permanent:true,direction:"top",offset:[0,-6]}).addTo(map);
L.marker([DATA.finish.lat,DATA.finish.lon],{icon:L.divIcon({className:"",html:`<div class="startfin finish">F</div>`,iconSize:[20,20],iconAnchor:[10,10]})})
  .bindTooltip("Finish",{permanent:true,direction:"top",offset:[0,-6]}).addTo(map);

const posMarker = L.circleMarker([DATA.start.lat,DATA.start.lon],{radius:8,color:"#ff7a45",weight:3,fillColor:"#ff7a45",fillOpacity:1}).addTo(map);
posMarker.setStyle({opacity:0,fillOpacity:0});

// ===== Elevation chart =====
const ctx = document.getElementById("elevChart").getContext("2d");
let elevChart;

function buildChart(){
  if(elevChart) elevChart.destroy();
  const data = DATA.route.map(p=>({x: unit==="mi"?p.mi:p.km, y:p.ele}));
  const total = totalDist();
  // gradient transition fractions
  const f1 = unit==="mi" ? PHASE_MI.p1End/DATA.totalMi : (PHASE_MI.p1End*1.609344)/DATA.totalKm;
  const f2 = unit==="mi" ? PHASE_MI.p2End/DATA.totalMi : (PHASE_MI.p2End*1.609344)/DATA.totalKm;

  elevChart = new Chart(ctx, {
    type:"line",
    data:{ datasets:[{
      data, parsing:false, borderColor:"#ff7a45", borderWidth:1.5,
      pointRadius:0, fill:true,
      backgroundColor:(c)=>{
        const {chart}=c; const {ctx,chartArea}=chart; if(!chartArea) return null;
        const g = ctx.createLinearGradient(0,0, chartArea.right,0);
        g.addColorStop(0, "rgba(63,185,80,.25)");
        g.addColorStop(f1, "rgba(63,185,80,.25)");
        g.addColorStop(Math.min(1,f1+0.001), "rgba(248,81,73,.30)");
        g.addColorStop(f2, "rgba(248,81,73,.30)");
        g.addColorStop(Math.min(1,f2+0.001), "rgba(88,166,255,.25)");
        g.addColorStop(1, "rgba(88,166,255,.25)");
        return g;
      },
      segment:{
        borderColor:(c)=>{
          const d=(c.p0.parsed.x+c.p1.parsed.x)/2;
          return phaseColor(d);
        }
      }
    }]},
    options:{
      responsive:true, maintainAspectRatio:false,
      interaction:{intersect:false,mode:"index"}, animation:false,
      plugins:{
        legend:{display:false},
        tooltip:{
          callbacks:{
            title:(items)=>`${unit==="mi"?"Mile":"Km"} ${items[0].parsed.x.toFixed(2)}`,
            label:(c)=>`${c.parsed.y.toFixed(0)} ft`
          }
        }
      },
      scales:{
        x:{type:"linear",min:0,max:total,
           title:{display:true,text:unit==="mi"?"Mile":"Kilometer",color:"#9aa7b4"},
           ticks:{color:"#9aa7b4",stepSize: unit==="mi"?2:5},grid:{color:"#2a3441"}},
        y:{title:{display:true,text:"Elevation (ft)",color:"#9aa7b4"},
           ticks:{color:"#9aa7b4"},grid:{color:"#2a3441"}}
      },
      onHover:(evt,items)=>{
        if(items.length){
          const idx = items[0].index;
          const p = DATA.route[idx];
          posMarker.setLatLng([p.lat,p.lon]);
          posMarker.setStyle({opacity:1,fillOpacity:1});
        } else {
          posMarker.setStyle({opacity:0,fillOpacity:0});
        }
      }
    }
  });
}

// ===== Goals UI =====
const goalsEl = document.getElementById("goals");
function renderGoals(){
  goalsEl.innerHTML = "";
  GOALS.forEach(g=>{
    const d = document.createElement("div");
    d.className = "goal" + (g.key===activeGoal?" active":"");
    d.dataset.key = g.key;
    const paceTxt = paceStr(goalPaceSec(g)) + "/" + unitLabel();
    d.innerHTML = `<div class="t">${g.label}</div><div class="v">${fmt(g.total)}</div><div class="p">${paceTxt}</div>`;
    d.onclick = ()=>{ activeGoal=g.key; renderGoals(); renderSplits(); };
    goalsEl.appendChild(d);
  });
}

// ===== Splits =====
function renderSplits(){
  document.getElementById("hdrUnit").textContent = unit==="mi" ? "Mile" : "Km";
  const goal = GOALS.find(g=>g.key===activeGoal);
  const ms = summary();
  const baseSec = goalPaceSec(goal);
  // hill cost model: extra seconds per unit based on net gain
  // tuned per-mile values; scale for km (km is shorter so smaller multipliers)
  const scale = unit==="mi" ? 1.0 : 1/1.609344;
  const adjusted = ms.map(m=>{
    const net = m.end_ft - m.start_ft;
    const extra = (net>0 ? net*0.6 : Math.max(net*0.3, -10)) * scale;
    const rollCost = Math.max(0, (m.gain_ft - Math.abs(net)) * 0.15) * scale;
    let split = baseSec + extra + rollCost;
    if(m.frac < 1) split = split * m.frac; // partial last unit
    return split;
  });
  // normalize so total == goal.total
  const sum = adjusted.reduce((a,b)=>a+b,0);
  const factor = goal.total/sum;
  const finalSplits = adjusted.map(s=>s*factor);

  const tbody = document.getElementById("splitsBody");
  tbody.innerHTML = "";
  let cum = 0;
  finalSplits.forEach((s,i)=>{
    cum += s;
    const m = ms[i];
    // for phase coloring: convert this unit's mile back to mi
    const miEquiv = unit==="mi" ? m.n : m.n/1.609344;
    const phase = phaseClass(miEquiv);
    const isPartial = m.frac < 1;
    const dist = m.frac;
    const pace = s/dist;
    const label = isPartial ? `${(m.n-1)}-${totalDist().toFixed(2)}` : m.n;
    const tr = document.createElement("tr");
    tr.innerHTML = `<td class="seg-${phase}">${label}</td>
      <td>${paceStr(pace)}</td>
      <td>${fmt(s)}</td>
      <td>${fmt(cum)}</td>
      <td style="color:#9aa7b4">${m.end_ft.toFixed(0)}</td>`;
    tbody.appendChild(tr);
  });
  const tr = document.createElement("tr");
  tr.style.fontWeight = "700";
  tr.innerHTML = `<td>Total</td><td>${paceStr(goalPaceSec(goal))}</td><td></td><td>${fmt(cum)}</td><td></td>`;
  tbody.appendChild(tr);
}

// ===== Cues =====
function renderCues(){
  const list = document.getElementById("cuesList");
  list.innerHTML = "";
  const cs = cues();
  Object.entries(cs).forEach(([n,t])=>{
    const d = document.createElement("div");
    d.className = "cue";
    d.innerHTML = `<div class="m">${unit==="mi"?"Mile":"Km"} ${n}</div><div class="t">${t}</div>`;
    list.appendChild(d);
  });
}

// ===== Fuel =====
const FUEL_PLAN = [
  {miLabel:"Pre", kmLabel:"Pre", text:"1 gel + sip water 10-15 min before gun."},
  {mi:4,  km:6.4,  text:"Gel #2 - by now you've found rhythm."},
  {mi:8,  km:12.9, text:"Gel #3 - midway through the easy section."},
  {mi:11, km:17.7, text:"<b>Gel #4 + full cup fluid.</b> Fuel BEFORE the climb so you climb fed, not chewing."},
  {mi:16, km:25.7, text:"Gel #5 - bottom of the descent, before the long grind home."},
  {mi:20, km:32.2, text:"Gel #6 - the last one. Take it before you need it."},
  {mi:24, km:38.6, text:"Optional caffeine gel if you trained with one - last 5K push."},
];
function renderFuel(){
  const list = document.getElementById("fuelList");
  list.innerHTML = "";
  FUEL_PLAN.forEach(f=>{
    let label;
    if(f.miLabel) label = f.miLabel;
    else label = unit==="mi" ? `Mi ${f.mi}` : `Km ${f.km}`;
    const row = document.createElement("div");
    row.className = "fuel-row";
    row.innerHTML = `<div class="fuel-mile">${label}</div><div class="fuel-text">${f.text}</div>`;
    list.appendChild(row);
  });
}

// ===== Phase + legend labels =====
function renderPhaseLabels(){
  const k = (mi)=> (mi*1.609344).toFixed(1);
  if(unit==="mi"){
    document.querySelector(".ph1").textContent = "mi 1-11";
    document.querySelector(".ph2").textContent = "mi 12-16";
    document.querySelector(".ph3").textContent = "mi 17-26";
    document.querySelector(".leg-p1").textContent = "Mi 1-11 (free)";
    document.querySelector(".leg-p2").textContent = "Mi 12-16 (hill)";
    document.querySelector(".leg-p3").textContent = "Mi 17-26 (grind)";
  } else {
    document.querySelector(".ph1").textContent = "km 1-18";
    document.querySelector(".ph2").textContent = "km 19-26";
    document.querySelector(".ph3").textContent = "km 27-42";
    document.querySelector(".leg-p1").textContent = "Km 1-18 (free)";
    document.querySelector(".leg-p2").textContent = "Km 19-26 (hill)";
    document.querySelector(".leg-p3").textContent = "Km 27-42 (grind)";
  }
}

// ===== Header total =====
function renderTotalDist(){
  document.getElementById("totaldist").textContent =
    unit==="mi" ? `${DATA.totalMi.toFixed(2)} mi` : `${DATA.totalKm.toFixed(2)} km`;
}

// ===== Tabs =====
document.querySelectorAll(".tab").forEach(t=>{
  t.onclick = ()=>{
    document.querySelectorAll(".tab").forEach(x=>x.classList.toggle("active",x===t));
    document.querySelectorAll(".tabpanel").forEach(p=>p.classList.toggle("active",p.dataset.tab===t.dataset.tab));
  };
});

// ===== Unit toggle =====
function setUnit(u){
  unit = u;
  document.querySelectorAll("#unitToggle button").forEach(b=>b.classList.toggle("active",b.dataset.u===u));
  renderGoals();
  renderSplits();
  renderCues();
  renderFuel();
  renderPhaseLabels();
  renderTotalDist();
  renderDistanceMarkers();
  renderAidStations();
  renderFuelMarkers();
  buildChart();
}
document.querySelectorAll("#unitToggle button").forEach(b=>{ b.onclick = ()=>setUnit(b.dataset.u); });

// initial
setUnit("km");
</script>
</body>
</html>
"""

with open("race_plan.html", "w", encoding="utf-8") as f:
    f.write(HTML.replace("__DATA__", embedded))

print(f"Wrote race_plan.html ({len(embedded)} bytes embedded data)")
