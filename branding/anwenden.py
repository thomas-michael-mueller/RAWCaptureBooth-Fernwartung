"""Branding der RAWCaptureBooth-Fernwartung auf den RustDesk-Quellstand anwenden.

Aufruf:  python branding/anwenden.py <kunde|techniker|fotobox>

Läuft im Build-Ablauf vor dem Bauen und lässt sich lokal beliebig oft wiederholen
(jede Ersetzung ist idempotent). Ändert:
  - branding/aktiv.json         Variante (Name, Server, nur ein- oder ausgehend)
  - Programmsymbole              res/icon.ico, res/tray-icon.ico, Flutter-Runner, Assets
  - Logo im Hauptfenster         flutter/assets/logo_light.png, logo_dark.png
  - Akzentfarben                 flutter/lib/common.dart
  - Dateieigenschaften           Runner.rc, libs/portable/Cargo.toml
"""

import base64
import hashlib
import io
import json
import os
import re
import secrets
import string
import sys
from pathlib import Path

from PIL import Image

WURZEL = Path(__file__).resolve().parent.parent
BRANDING = WURZEL / "branding"
QUELLE = BRANDING / "quelle"

FIRMA = "Thomas Michael Mueller"
COPYRIGHT = "Copyright © 2026 Thomas Michael Mueller. Based on RustDesk (AGPL-3.0)."

# RAWCaptureBooth-Gold, wie im Admin-Bereich (--accent: #d89904)
FARBEN = {
    "accent": "0xFFD89904",
    "accent50": "0x77D89904",
    "accent80": "0xAAD89904",
    "idColor": "0xFFE8A90F",
    "button": "0xFFD89904",
}

VARIANTEN = ("kunde", "techniker", "fotobox")

ICO_GROESSEN = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]


def lesen(pfad: Path) -> str:
    return io.open(pfad, encoding="utf-8", newline="").read()


def schreiben(pfad: Path, text: str) -> None:
    io.open(pfad, "w", encoding="utf-8", newline="").write(text)


def ersetzen(pfad: Path, muster: str, ersatz: str, anzahl: int = 1) -> None:
    text = lesen(pfad)
    neu, n = re.subn(muster, ersatz, text)
    if n != anzahl:
        sys.exit(f"{pfad}: Muster {muster!r} {n}-mal gefunden, erwartet {anzahl}")
    schreiben(pfad, neu)


def symbole() -> None:
    icon = Image.open(QUELLE / "icon.png").convert("RGBA")
    for ziel in (
        WURZEL / "res" / "icon.ico",
        WURZEL / "res" / "tray-icon.ico",
        WURZEL / "flutter" / "windows" / "runner" / "resources" / "app_icon.ico",
        WURZEL / "flutter" / "assets" / "icon.ico",
    ):
        icon.save(ziel, sizes=ICO_GROESSEN)
    icon.resize((256, 256), Image.LANCZOS).save(WURZEL / "flutter" / "assets" / "icon.png")
    icon.resize((256, 256), Image.LANCZOS).save(WURZEL / "res" / "icon.png")


def logos() -> None:
    logo = Image.open(QUELLE / "logo.png").convert("RGBA")
    # Höchstens 300 x 60, so zeigt RustDesk das Logo an
    breite = 300
    hoehe = round(logo.height * breite / logo.width)
    logo = logo.resize((breite * 2, hoehe * 2), Image.LANCZOS)
    logo.save(WURZEL / "flutter" / "assets" / "logo_dark.png")
    # Helles Design: weißer Schriftzug "RAW" wird dunkel, das Symbol links bleibt
    hell = logo.copy()
    pixel = hell.load()
    symbol_ende = hell.height  # das Symbol ist quadratisch und steht ganz links
    for x in range(symbol_ende, hell.width):
        for y in range(hell.height):
            r, g, b, a = pixel[x, y]
            if a and r > 200 and g > 200 and b > 200:
                pixel[x, y] = (34, 34, 34, a)
    hell.save(WURZEL / "flutter" / "assets" / "logo_light.png")


def farben() -> None:
    pfad = WURZEL / "flutter" / "lib" / "common.dart"
    for name, wert in FARBEN.items():
        ersetzen(pfad, rf"(static const Color {name} = Color\()0x[0-9A-Fa-f]{{8}}(\);)", rf"\g<1>{wert}\2")
    ersetzen(pfad, r"primary: (?:Colors\.blue|accent), secondary: accent, background: grayBg",
             "primary: accent, secondary: accent, background: grayBg")
    ersetzen(pfad, r"(ColorScheme\.dark\(\r?\n\s+primary: )(?:Colors\.blue|accent)", r"\1accent")


def dateieigenschaften(variante: dict) -> None:
    name = variante["app-name"]
    rc = WURZEL / "flutter" / "windows" / "runner" / "Runner.rc"
    ersetzen(rc, r'(VALUE "CompanyName", )"[^"]*"', rf'\1"{FIRMA}"')
    ersetzen(rc, r'(VALUE "FileDescription", )"[^"]*"', rf'\1"{name}"')
    ersetzen(rc, r'(VALUE "LegalCopyright", )"[^"]*"', rf'\1"{COPYRIGHT}"')
    ersetzen(rc, r'(VALUE "ProductName", )"[^"]*"', rf'\1"{name}"')
    cargo = WURZEL / "libs" / "portable" / "Cargo.toml"
    ersetzen(cargo, r'(?m)^(LegalCopyright = )"[^"]*"', rf'\1"{COPYRIGHT}"')
    ersetzen(cargo, r'(?m)^(ProductName = )"[^"]*"', rf'\1"{name}"')
    ersetzen(cargo, r'(?m)^(FileDescription = )"[^"]*"', rf'\1"{name}"')
    ersetzen(cargo, r'(?m)^(description = )"[^"]*"', rf'\1"{name}"')


MINDESTLAENGE_PIN = 12


def fester_pin(variante: dict) -> None:
    """Fester PIN aus einer Umgebungsvariable, nie aus dem Repository.

    Eingebettet wird nur die Prüfsumme mit Zufallswert, im Format der
    RustDesk-Voreinstellung (HARD_SETTINGS "password" = "00" + Base64(SHA-256(PIN + Salt))).
    Die Programmdatei ist öffentlich herunterladbar; ein kurzer PIN ließe sich aus der
    Prüfsumme durch Ausprobieren zurückrechnen, daher die Mindestlänge.
    """
    name = variante.pop("rcb-fester-pin", None)
    if not name:
        return
    pin = os.environ.get(name, "")
    if len(pin) < MINDESTLAENGE_PIN:
        sys.exit(f"{name} fehlt oder ist kürzer als {MINDESTLAENGE_PIN} Zeichen")
    salt = "".join(secrets.choice(string.ascii_letters + string.digits) for _ in range(32))
    pruefsumme = hashlib.sha256((pin + salt).encode("utf-8")).digest()
    variante["password"] = "00" + base64.b64encode(pruefsumme).decode("ascii")
    variante["salt"] = salt


def main() -> None:
    if len(sys.argv) != 2 or sys.argv[1] not in VARIANTEN:
        sys.exit(f"Aufruf: python branding/anwenden.py <{'|'.join(VARIANTEN)}>")
    quelle = BRANDING / f"{sys.argv[1]}.json"
    variante = json.loads(lesen(quelle))
    fester_pin(variante)
    schreiben(BRANDING / "aktiv.json", json.dumps(variante, indent=2, ensure_ascii=False) + "\n")
    symbole()
    logos()
    farben()
    dateieigenschaften(variante)
    print(f"Branding angewendet: {variante['app-name']}")


if __name__ == "__main__":
    main()
