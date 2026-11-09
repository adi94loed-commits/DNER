"""Erstellt die deutschlandweite Döner-Basis für die App (offline nutzbar).

Läuft in GitHub Actions ("Döner-Basis erstellen"), monatlich oder per Hand.
Quellen:
  1. OpenStreetMap über Overpass (ganz Deutschland, ein Abruf)
  2. Foursquare OS Places (mit HF_TOKEN aktuell von Hugging Face, sonst
     letzte freie Ausgabe aus dem öffentlichen S3-Speicher)
Fällt eine Quelle aus, wird mit der anderen weitergemacht.

Ergebnis: www/data/doener-basis.json
  places: [id, name, lat, lon, stufe]   stufe 2 = Döner sicher, 1 = vielleicht Döner
"""
import datetime, json, math, os, re, subprocess, sys, time, unicodedata, urllib.parse, urllib.request
from collections import Counter, defaultdict

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "www", "data", "doener-basis.json")

# eindeutig Döner (Name oder Küche)
SURE = r"d[öo]ner|d[öo]nner|kebab|kebap|d[üu]r[üu]m|lahmacun|schawarma|shawarma|iskender"
# typisch türkisch/orientalisch, aber nicht eindeutig
MAYBE_CUISINE = r"turkish|middle_eastern|arab|lebanese|syrian|kurdish|falafel|pide|persian|afghan|iraqi"
MAYBE_NAME = (r"istanbul|stanbul|ankara|antalya|izmir|anatolia|anadolu|bosporus|bosphorus|bodrum|alanya|"
              r"kapadokya|sultan|efes|mangal|kervan|osmanl|ottoman|marmara|bursa|adana|urfa|gaziantep|"
              r"mersin|trabzon|karadeniz|aksaray|konya|kayseri|sofra|lokanta|grill|imbiss|falafel|shawerma")
TURK_NAME = re.sub(r"\|grill|\|imbiss|\|falafel|\|shawerma", "", MAYBE_NAME)
# nicht als "vielleicht" werten (deutsche/andere Imbisse)
NOT_MAYBE = (r"wurst|curry|burger|gyros|griech|hellas|akropolis|olymp|souvlaki|steak|sushi|asia|china|thai|vietnam|"
             r"fisch|backfisch|hähnchen|broiler|pommes|mcdonald|burger king|kfc|subway|nordsee|pizza hut|domino|"
             r"dunkin|starbucks|vapiano|wienerwald|kamps|backwerk|ditsch|five guys|popeyes|dean ?& ?david|"
             r"coffee|bäck|baeck|backstube|eiscaf|eisdiele|gelato|bubble|poke|crepe|crêpe|waffel|frittenwerk|"
             r"kiosk|tankstelle|bakery|donut|bagel|sandwich|nudel|noodle|ramen|taco|burrito|mexi")
# Fast Food mit diesen Küchen ist sicher kein Döner
NOT_CUISINE = (r"burger|chicken|asian|chinese|thai|vietnam|japanese|sushi|korean|indian|sandwich|ice_cream|coffee|"
               r"bakery|donut|fish|seafood|german|sausage|bratwurst|currywurst|greek|gyros|crepe|waffle|bubble_tea|"
               r"poke|bagel|hot_dog|salad|juice|cake|fries|friture|mexican|burrito|taco|noodle|ramen|dessert")

def level(name, cuisine, fast):
    n, c = (name or "").lower(), (cuisine or "").lower()
    if re.search(SURE, n) or re.search(r"kebab|doner|döner|shawarma|lahmacun|durum|dürüm", c):
        return 2
    if re.search(NOT_MAYBE, n):
        return 0
    if re.search(MAYBE_CUISINE, c):
        return 1
    if re.search(TURK_NAME, n):
        return 1
    # Fast Food, das nicht klar etwas anderes ist: vielleicht Döner
    if fast and not (c and re.search(NOT_CUISINE, c)):
        return 1
    return 0

def norm(s):
    s = unicodedata.normalize("NFD", (s or "").lower())
    return re.sub(r"[^a-z0-9]", "", "".join(ch for ch in s if unicodedata.category(ch) != "Mn"))

FILL = r"doener|doner|dner|kebab|kebap|kebabhaus|durum|imbiss|grill|haus|house|pizza|pizzeria|restaurant|bistro|und|the"

def core(s):
    n = norm(s).replace("oe", "o").replace("ue", "u").replace("ae", "a")
    return re.sub(FILL, "", n) or n

def dist(a, b):
    r = math.radians
    h = math.sin(r(b[0] - a[0]) / 2) ** 2 + math.cos(r(a[0])) * math.cos(r(b[0])) * math.sin(r(b[1] - a[1]) / 2) ** 2
    return 2 * 6371e3 * math.asin(math.sqrt(h))

# ---------- 1. OpenStreetMap ----------
OVERPASS = ["https://overpass-api.de/api/interpreter",
            "https://overpass.private.coffee/api/interpreter",
            "https://maps.mail.ru/osm/tools/overpass/api/interpreter"]

def fetch_osm():
    names = f"{SURE}|{MAYBE_NAME}"
    q = (f'[out:json][timeout:900][maxsize:1073741824];'
         f'area["ISO3166-1"="DE"][admin_level=2]->.de;'
         f'nwr(area.de)["amenity"~"^(fast_food|restaurant|food_court|cafe)$"]->.f;'
         f'(nwr.f["amenity"="fast_food"];nwr.f["cuisine"~"kebab|doner|döner|shawarma|lahmacun|durum|dürüm|{MAYBE_CUISINE}",i];'
         f'nwr.f["name"~"{names}",i];);out tags center qt;')
    data = urllib.parse.urlencode({"data": q}).encode()
    last = None
    for attempt in range(2):
        for url in OVERPASS:
            try:
                print(f"OSM: frage {url} …", flush=True)
                req = urllib.request.Request(url, data=data, headers={"User-Agent": "DoenerTracker-Basis/2.0 (GitHub Actions)"})
                j = json.load(urllib.request.urlopen(req, timeout=1000))
                els = j.get("elements") or []
                if len(els) < 2000:
                    raise RuntimeError(f"nur {len(els)} Treffer")
                return els
            except Exception as e:
                last = e
                print(f"   fehlgeschlagen: {e}", flush=True)
        time.sleep(60)
    raise RuntimeError(f"Overpass nicht erreichbar ({last})")

osm, osm_err = [], None
try:
    for e in fetch_osm():
        t = e.get("tags") or {}
        lat = e.get("lat", (e.get("center") or {}).get("lat"))
        lon = e.get("lon", (e.get("center") or {}).get("lon"))
        if not t.get("name") or lat is None:
            continue
        if t.get("disused:amenity") or t.get("opening_hours") == "closed":
            continue
        lv = level(t["name"], t.get("cuisine"), t.get("amenity") == "fast_food")
        if lv:
            osm.append([f'{e["type"]}/{e["id"]}', t["name"].strip(), round(lat, 5), round(lon, 5), lv, t.get("addr:city") or ""])
    print(f"OSM: {len(osm)} Läden", flush=True)
except Exception as e:
    osm_err = str(e)
    print("OSM übersprungen:", e, flush=True)

# ---------- 2. Foursquare ----------
fsq, fsq_err, release, origin = [], None, None, None
try:
    import duckdb
    con = duckdb.connect()
    con.execute("INSTALL httpfs; LOAD httpfs;")
    token = os.environ.get("HF_TOKEN", "").strip()
    if token:
        con.execute(f"CREATE SECRET hf (TYPE HUGGINGFACE, TOKEN '{token}')")
        req = urllib.request.Request(
            "https://huggingface.co/api/datasets/foursquare/fsq-os-places/tree/main/release",
            headers={"Authorization": f"Bearer {token}"})
        items = json.load(urllib.request.urlopen(req))
        release = sorted(re.search(r"dt=([\d-]+)", x["path"]).group(1) for x in items if "dt=" in x["path"])[-1]
        src = f"hf://datasets/foursquare/fsq-os-places/release/dt={release}/places/parquet/*.parquet"
        origin = "Hugging Face"
    else:
        out = subprocess.run(["aws", "s3", "ls", "--no-sign-request", "s3://fsq-os-places-us-east-1/release/"],
                             capture_output=True, text=True).stdout
        rel = sorted(set(re.findall(r"dt=(\d{4}-\d{2}-\d{2})", out)))
        if not rel:
            raise RuntimeError("keine Ausgabe im öffentlichen Speicher gefunden")
        release = rel[-1]
        con.execute("CREATE SECRET s3pub (TYPE S3, PROVIDER CONFIG, REGION 'us-east-1')")
        src = f"s3://fsq-os-places-us-east-1/release/dt={release}/places/parquet/*.parquet"
        origin = "öffentlicher S3-Speicher"
    print(f"Foursquare: {origin}, Ausgabe {release} …", flush=True)
    rows = con.execute(f"""
        SELECT fsq_place_id, name, latitude, longitude,
               lower(coalesce(array_to_string(fsq_category_labels, '|'), '')) AS cat,
               coalesce(locality, '')
        FROM read_parquet('{src}')
        WHERE country = 'DE'
          AND date_closed IS NULL
          AND latitude IS NOT NULL AND longitude IS NOT NULL AND name IS NOT NULL
          AND (TRY_CAST(date_refreshed AS DATE) IS NULL
               OR TRY_CAST(date_refreshed AS DATE) >= current_date - INTERVAL 3 YEAR)
          AND (regexp_matches(lower(name), '{SURE}|{MAYBE_NAME}')
               OR regexp_matches(lower(coalesce(array_to_string(fsq_category_labels, '|'), '')),
                                 'doner|döner|kebab|turkish|middle eastern|falafel|shawarma|fast food|snack'))
    """).fetchall()
    for pid, name, lat, lon, cat, city in rows:
        fc = ("turkish" if re.search(r"turkish|middle eastern|falafel", cat) else
              "burger" if re.search(r"burger|chicken|sandwich|bakery|coffee|ice cream|dessert|asian|chinese|thai|"
                                    r"vietnam|japanese|sushi|indian|fish|seafood|german|hot dog|bagel|donut|salad|"
                                    r"juice|mexican|taco|noodle|bistro|cafe|café", cat) else "")
        lv = 2 if re.search(r"doner|döner|kebab|shawarma", cat) else level(
            name, fc, "fast food" in cat or "snack" in cat)
        if lv:
            fsq.append([f"fsq:{pid}", name.strip(), round(lat, 5), round(lon, 5), lv, city])
    print(f"Foursquare: {len(fsq)} Läden", flush=True)
except Exception as e:
    fsq_err = str(e)
    print("Foursquare übersprungen:", e, flush=True)

if len(osm) + len(fsq) < 500:
    sys.exit("Zu wenige Treffer aus beiden Quellen – Datei wird nicht überschrieben.")

# ---------- 3. Zusammenführen (OSM hat Vorrang) ----------
grid = defaultdict(list)
cell = lambda la, lo: (int(la * 500), int(lo * 330))  # ca. 220 m
for p in osm:
    grid[cell(p[2], p[3])].append(p)

def twin(p):
    ci, cj = cell(p[2], p[3])
    for di in (-1, 0, 1):
        for dj in (-1, 0, 1):
            for o in grid.get((ci + di, cj + dj), []):
                d = dist((p[2], p[3]), (o[2], o[3]))
                if d < 20:
                    return o
                if d < 150:
                    a, b = core(p[1]), core(o[1])
                    if a and b and (a in b or b in a):
                        return o
    return None

dupes = 0
merged = list(osm)
for p in fsq:
    o = twin(p)
    if o:
        o[4] = max(o[4], p[4])
        dupes += 1
    else:
        merged.append(p)
        grid[cell(p[2], p[3])].append(p)

merged.sort(key=lambda p: p[0])
os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", encoding="utf-8") as f:
    json.dump({"version": 2, "created": datetime.date.today().isoformat(),
               "sources": {"osm": "OpenStreetMap-Mitwirkende (ODbL)" if osm else None,
                           "fsq": f"Foursquare OS Places (Apache 2.0), Ausgabe {release}" if fsq else None},
               "places": [p[:5] for p in merged]},
              f, ensure_ascii=False, separators=(",", ":"))
size_kb = os.path.getsize(OUT) // 1024
sure = sum(1 for p in merged if p[4] == 2)
print(f"Gespeichert: {len(merged)} Läden ({sure} sicher), {size_kb} KB")

# ---------- Übersicht im Lauf ("Summary") ----------
summary = os.environ.get("GITHUB_STEP_SUMMARY")
if summary:
    orte = Counter(p[5] or "?" for p in merged if p[4] == 2).most_common(15)
    with open(summary, "a", encoding="utf-8") as f:
        f.write("## Döner-Basis\n\n| | |\n|---|---|\n")
        f.write(f"| OpenStreetMap | {len(osm) if osm else 'fehlgeschlagen: ' + str(osm_err)} |\n")
        f.write(f"| Foursquare | {len(fsq) if fsq else 'fehlgeschlagen: ' + str(fsq_err)}" + (f" ({origin}, {release})" if fsq else "") + " |\n")
        f.write(f"| doppelt (zusammengeführt) | {dupes} |\n")
        f.write(f"| **Läden gesamt** | **{len(merged)}** |\n| davon Döner sicher | {sure} |\n")
        f.write(f"| davon vielleicht Döner | {len(merged) - sure} |\n| Dateigröße | {size_kb} KB |\n\n")
        f.write("### Top-Orte (Döner sicher)\n\n| Ort | Läden |\n|---|---|\n")
        f.writelines(f"| {o} | {n} |\n" for o, n in orte)
        f.write("\n### Stichprobe „vielleicht Döner“\n\n")
        f.writelines(f"- {p[1]} ({p[5] or '?'})\n" for p in [p for p in merged if p[4] == 1][::max(1, (len(merged) - sure) // 20)][:20])
