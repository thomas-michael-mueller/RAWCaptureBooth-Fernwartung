# RAWCaptureBooth-Fernwartung

Gebrandete Windows-Clients auf Basis von [RustDesk](https://github.com/rustdesk/rustdesk) (AGPL-3.0)
für den Support von RAWCaptureBooth. Server: `mueller.black` (eigener RustDesk-Server).

| Datei | Für | Verhalten |
| --- | --- | --- |
| `RAWCaptureBooth-Support.exe` | Kunde | nur eingehend, Quick Support ohne Installation, Einstellungen gesperrt, Annahme nur per Klick mit Kostenhinweis |
| `RAWCaptureBooth-Techniker.exe` | Support | nur ausgehend, keine Installation |
| `RAWCaptureBooth-Fotobox.exe` | eigene Fotoboxen | nur eingehend, installierbar (Dienst), Zugang nur über den dauerhaften PIN, ohne Annahme per Klick |

Zugang beim Kunden nur über Annahme per Klick (`approve-mode` = `click`), kein Einmalpasswort.
Über dem Knopf „Kostenpflichtig annehmen“ steht ein Hinweis auf Stundensatz, AGB und das Erlöschen
des Widerrufsrechts, mit Link auf die Fernwartungs-AGB. Gesteuert über `kunde.json`:
`rcb-kostenpflichtig` (`Y`), `rcb-stundensatz` (z. B. `70 €`), `rcb-agb-url`. Die Texte stehen als
`rcb_paid_*` / `rcb_terms_link` in `src/lang/de.rs` und `src/lang/en.rs` (übrige Sprachen fallen auf
Englisch zurück). „Annehmen und erhöhen“ ist im Annahmefenster ausgeblendet, damit jede Annahme über
den Knopf mit Kostenhinweis läuft; „Erhöhen“ bleibt nach der Annahme verfügbar.

Die Fotobox-Variante enthält keinen PIN. Nach der Installation wird an der Box unter
Einstellungen → Sicherheit ein dauerhaftes Passwort gesetzt (oder als Administrator
`"C:\Program Files\RAWCaptureBooth-Fotobox\RAWCaptureBooth-Fotobox.exe" --password <PIN>`). Solange keines gesetzt ist,
ist kein Zugriff möglich. Server-, Netzwerk- und Proxy-Einstellungen sind ausgeblendet.

`anwenden.py` kann über den Schlüssel `rcb-fester-pin` auch einen PIN aus einer Umgebungsvariable
einbetten (nur als Prüfsumme, mindestens 12 Zeichen); keine Variante nutzt das derzeit.

## Was gegenüber RustDesk geändert ist

- `branding/` – Varianten (`kunde.json`, `techniker.json`), Quellgrafiken, `anwenden.py`.
  `anwenden.py <variante>` kopiert die Variante nach `aktiv.json`, erzeugt Symbole und Logos,
  setzt die Akzentfarbe (RAWCaptureBooth-Gold) und die Dateieigenschaften.
- `src/common.rs` – `load_rcb_branding()` liest `branding/aktiv.json` (beim Bauen eingebettet) im
  Format der RustDesk-`custom.txt`, nur ohne Signatur.
- `src/core_main.rs`, `libs/portable/src/main.rs` – die Kunden-Variante ist immer Quick Support,
  ohne `-qs-` im Dateinamen.
- `flutter/lib/desktop/pages/server_page.dart` – Kostenhinweis und Knopf „Kostenpflichtig annehmen“
  im Annahmefenster der Kunden-Variante; `src/lang/de.rs`, `src/lang/en.rs` – Texte dazu.
- `.github/workflows/fernwartung.yml` – baut beide Varianten und signiert sie. Alle übrigen
  RustDesk-Workflows sind entfernt (außer `bridge.yml`, das gebraucht wird).

## Bauen

GitHub Actions → „Fernwartung bauen“ → *Run workflow*. Ein Tag `v*` legt zusätzlich ein Release an.
Dauer rund 45 Minuten je Variante (parallel).

Signiert wird über Azure Artifact Signing (Konto `rawcapturebooth`, Profil `RAWCaptureBooth`), sobald
die Repository-Variablen `AZURE_CLIENT_ID`, `AZURE_TENANT_ID` und `AZURE_SUBSCRIPTION_ID` gesetzt sind.
Die Anmeldung läuft über OIDC (föderierte Anmeldeinformation für die GitHub-Umgebung `signatur`
dieses Repositorys, App-Registrierung „RAWCaptureBooth-Fernwartung GitHub-Signatur“), es liegt kein
Geheimnis im Repository. Die Umgebung ist auf den Branch `rawcapturebooth` und Tags `v*` beschränkt. Die App-Registrierung braucht am Signaturkonto die Rolle
„Artifact Signing Certificate Profile Signer“.

## RustDesk-Update übernehmen

```
git fetch upstream tag <version> --no-tags
git merge <version>
```

Konflikte treten nur in den oben genannten Stellen auf. Danach `VERSION` in den Dateien prüfen
und einen neuen Tag setzen.

## Lizenz

AGPL-3.0 wie RustDesk (`LICENCE`). Der vollständige Quelltext dieser Fassung liegt in diesem
Repository.
