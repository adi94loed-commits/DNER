// Ergänzt Standort- und Kamera-Berechtigungen (Döner-Foto) und eine feste Signatur,
// damit Updates sich über die alte App installieren lassen (Daten bleiben erhalten).
const fs = require("fs");
const path = require("path");

const manifest = path.join("android", "app", "src", "main", "AndroidManifest.xml");
let m = fs.readFileSync(manifest, "utf8");
const perms = [
  '<uses-permission android:name="android.permission.ACCESS_COARSE_LOCATION" />',
  '<uses-permission android:name="android.permission.ACCESS_FINE_LOCATION" />',
  '<uses-feature android:name="android.hardware.location.gps" android:required="false" />',
  '<uses-permission android:name="android.permission.CAMERA" />',
  '<uses-feature android:name="android.hardware.camera" android:required="false" />'
];
const missing = perms.filter(p => !m.includes(p.match(/name="([^"]+)"/)[1]));
if (missing.length) {
  m = m.replace(/<\/manifest>\s*$/, "    " + missing.join("\n    ") + "\n</manifest>\n");
  fs.writeFileSync(manifest, m);
}
console.log("Berechtigungen: ok");

const ks = path.resolve("keystore", "debug.keystore").replace(/\\/g, "/");
const groovy = path.join("android", "app", "build.gradle");
const kts = path.join("android", "app", "build.gradle.kts");
const marker = "// doener-tracker-signing";
if (fs.existsSync(groovy)) {
  let g = fs.readFileSync(groovy, "utf8");
  if (!g.includes(marker)) {
    g += `\n${marker}\nandroid {\n    signingConfigs {\n        debug {\n            storeFile file("${ks}")\n            storePassword "android"\n            keyAlias "androiddebugkey"\n            keyPassword "android"\n        }\n    }\n}\n`;
    fs.writeFileSync(groovy, g);
  }
} else if (fs.existsSync(kts)) {
  let g = fs.readFileSync(kts, "utf8");
  if (!g.includes(marker)) {
    g += `\n${marker}\nandroid {\n    signingConfigs {\n        getByName("debug") {\n            storeFile = file("${ks}")\n            storePassword = "android"\n            keyAlias = "androiddebugkey"\n            keyPassword = "android"\n        }\n    }\n}\n`;
    fs.writeFileSync(kts, g);
  }
}
console.log("Signatur: ok");

// App-Icon und Startbild übernehmen
function copyDir(src, dst) {
  for (const e of fs.readdirSync(src, { withFileTypes: true })) {
    const s = path.join(src, e.name), d = path.join(dst, e.name);
    if (e.isDirectory()) { fs.mkdirSync(d, { recursive: true }); copyDir(s, d); }
    else fs.copyFileSync(s, d);
  }
}
copyDir(path.join("assets", "android-res"), path.join("android", "app", "src", "main", "res"));
console.log("Icon: ok");
