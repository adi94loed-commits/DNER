# Döner-Tracker als Android-App

Erstellt für: Adrian.Loederbusch@vermessung-frentzel.de
Hinweis: Code und Anleitung wurden maßgeblich mit KI (ATLAS / Claude) erstellt.

Es gibt zwei Wege zur APK. Bleib danach bei einem Weg, dann lassen sich
Updates einfach drüberinstallieren und deine Einträge bleiben erhalten.

## Weg A: GitHub baut die App (nichts installieren)

1. Kostenlosen Account auf github.com anlegen.
2. Neues Repository erstellen: oben rechts „+“ → „New repository“,
   Name z. B. `doener-tracker`, Sichtbarkeit **Private**, ohne README anlegen.
3. Auf der leeren Repository-Seite auf „uploading an existing file“ klicken
   und den **Inhalt** des entpackten Ordners hineinziehen (nicht den Ordner selbst),
   dann „Commit changes“.
4. Prüfen, ob der Ordner `.github` mit hochgeladen wurde. Unter macOS und
   Windows ist er oft versteckt. Falls er fehlt: im Repository
   „Add file“ → „Create new file“, als Namen `.github/workflows/apk-bauen.yml`
   eingeben und den Inhalt der gleichnamigen Datei hineinkopieren.
5. Reiter „Actions“ öffnen. Der Lauf „APK bauen“ startet automatisch
   und dauert etwa 5 Minuten.
6. Wenn er grün ist: Lauf anklicken, unten unter „Artifacts“
   `doener-tracker-apk` herunterladen. Das ist eine ZIP-Datei mit `app-debug.apk`.

## Weg B: Android Studio am eigenen PC

1. Node.js (Version 22 oder neuer) und Android Studio installieren.
2. Im entpackten Ordner ein Terminal öffnen und ausführen:
   ```
   npm install
   npm run android:init
   npm run android:sync
   npm run android:open
   ```
3. In Android Studio: Menü „Build“ → „Build App Bundle(s) / APK(s)“ → „Build APK(s)“.
   Die Datei liegt danach unter `android/app/build/outputs/apk/debug/app-debug.apk`.

## Installation auf dem Handy

1. Die `app-debug.apk` aufs Handy bringen (z. B. per Mail an dich selbst,
   Google Drive oder USB) und antippen.
2. Android fragt, ob du Apps aus dieser Quelle zulassen willst: erlauben.
3. Google Play Protect warnt eventuell, weil die App nicht aus dem Store kommt:
   „Trotzdem installieren“.
4. Beim ersten Tippen auf „Laden finden“ den Standort erlauben,
   am besten „Bei Nutzung der App“ und „Genau“.

## Änderungen später

Nur die Datei `www/index.html` ersetzen und neu bauen
(Weg A: Datei im Repository hochladen, der Bau startet von selbst).
Die neue APK einfach über die alte installieren.

Wichtig: Wird die App deinstalliert, sind die Einträge weg.

## Datenquellen

Ladendaten © OpenStreetMap-Mitwirkende (ODbL), abgefragt über die Overpass-API.
Schrift: Bricolage Grotesque (SIL Open Font License).


## Update einspielen (Einträge bleiben erhalten)

1. Den **Inhalt** des Update-Ordners in das bestehende Repository hochladen
   („Add file“ → „Upload files“) und vorhandene Dateien überschreiben lassen.
   Nichts löschen, vor allem nicht `www/data` (dort liegt die Döner-Basis).
2. „APK bauen“ startet von selbst. Wenn der Lauf grün ist, die APK unter „Artifacts“ laden.
3. Die neue APK auf dem Handy öffnen und **über die alte App installieren**,
   nicht vorher deinstallieren. Jede neue APK hat eine höhere Versionsnummer,
   Android akzeptiert sie deshalb als Update.
