"""Erstellt die deutschlandweite Döner-Basis aus Foursquare OS Places.

Läuft in GitHub Actions ("Döner-Basis erstellen"). Mit HF_TOKEN werden die
aktuellen Daten von Hugging Face geholt, ohne Token die letzte frei
verfügbare Ausgabe aus dem öffentlichen S3-Speicher von Foursquare.
Ergebnis: www/data/fsq-doener.json
"""
import json, os, re, subprocess, sys, urllib.request, datetime
import duckdb

NAME_RE = r"d[öo]ner|kebab|kebap|d[üu]r[üu]m|lahmacun|schawarma|shawarma"
CAT_RE = r"doner|döner|kebab"
OUT = os.path.join(os.path.dirname(__file__), "..", "www", "data", "fsq-doener.json")

con = duckdb.connect()
con.execute("INSTALL httpfs; LOAD httpfs;")
token = os.environ.get("HF_TOKEN", "").strip()

if token:
    con.execute(f"CREATE SECRET hf (TYPE HUGGINGFACE, TOKEN '{token}')")
    req = urllib.request.Request(
        "https://huggingface.co/api/datasets/foursquare/fsq-os-places/tree/main/release",
        headers={"Authorization": f"Bearer {token}"})
    items = json.load(urllib.request.urlopen(req))
    releases = sorted(re.search(r"dt=([\d-]+)", x["path"]).group(1) for x in items if "dt=" in x["path"])
    release = releases[-1]
    src = f"hf://datasets/foursquare/fsq-os-places/release/dt={release}/places/parquet/*.parquet"
    origin = "Hugging Face"
else:
    out = subprocess.run(["aws", "s3", "ls", "--no-sign-request", "s3://fsq-os-places-us-east-1/release/"],
                         capture_output=True, text=True).stdout
    releases = sorted(set(re.findall(r"dt=(\d{4}-\d{2}-\d{2})", out)))
    if not releases:
        sys.exit("Keine Foursquare-Ausgabe im öffentlichen Speicher gefunden.")
    release = releases[-1]
    con.execute("CREATE SECRET s3pub (TYPE S3, PROVIDER CONFIG, REGION 'us-east-1')")
    src = f"s3://fsq-os-places-us-east-1/release/dt={release}/places/parquet/*.parquet"
    origin = "öffentlicher S3-Speicher"

print(f"Quelle: {origin}, Ausgabe {release}")
rows = con.execute(f"""
    SELECT fsq_place_id, name, CAST(round(latitude, 5) AS DOUBLE), CAST(round(longitude, 5) AS DOUBLE),
           coalesce(locality, '?'), regexp_matches(lower(name), '{NAME_RE}')
    FROM read_parquet('{src}')
    WHERE country = 'DE'
      AND date_closed IS NULL
      AND latitude IS NOT NULL AND longitude IS NOT NULL AND name IS NOT NULL
      AND (regexp_matches(lower(name), '{NAME_RE}')
           OR regexp_matches(lower(coalesce(array_to_string(fsq_category_labels, '|'), '')), '{CAT_RE}'))
    ORDER BY fsq_place_id
""").fetchall()
print(f"{len(rows)} Döner-Läden in Deutschland gefunden")
if len(rows) < 100:
    sys.exit("Ungewöhnlich wenige Treffer – Datei wird nicht überschrieben.")

os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", encoding="utf-8") as f:
    json.dump({"source": "Foursquare OS Places (Apache 2.0)", "release": release,
               "created": datetime.date.today().isoformat(),
               "places": [[r[0], r[1], r[2], r[3]] for r in rows]},
              f, ensure_ascii=False, separators=(",", ":"))
size_kb = os.path.getsize(OUT) // 1024
print("Gespeichert:", size_kb, "KB")

# Übersicht für "Ergebnis prüfen" (erscheint im Lauf unter "Summary")
summary = os.environ.get("GITHUB_STEP_SUMMARY")
if summary:
    from collections import Counter
    orte = Counter(r[4] for r in rows).most_common(15)
    nur_kat = [r for r in rows if not r[5]]
    with open(summary, "a", encoding="utf-8") as f:
        f.write(f"## Döner-Basis\n\n| | |\n|---|---|\n")
        f.write(f"| Quelle | {origin} |\n| Ausgabe | {release} |\n")
        f.write(f"| Läden | {len(rows)} |\n| nur über Kategorie | {len(nur_kat)} |\n| Dateigröße | {size_kb} KB |\n\n")
        f.write("### Top-Orte\n\n| Ort | Läden |\n|---|---|\n")
        f.writelines(f"| {o} | {n} |\n" for o, n in orte)
        f.write("\n### Stichprobe nur über Kategorie (Name ohne Döner-Wort)\n\n")
        f.writelines(f"- {r[1]} ({r[4]})\n" for r in nur_kat[:15])
