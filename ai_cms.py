import os
import re
import base64
from pathlib import Path

from openai import OpenAI

# OpenAI-Client (API-Key kommt aus der Umgebungsvariable OPENAI_API_KEY)
client = OpenAI()

# Issue-Daten aus GitHub Actions
COMMAND = os.getenv("ISSUE_BODY", "") or ""
TITLE = os.getenv("ISSUE_TITLE", "") or ""


def read_file(path: Path) -> str:
    """Datei lesen, falls vorhanden, sonst leerer String."""
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""


def collect_site_files() -> dict:
    """
    Alle relevanten Website-Dateien einsammeln.
    Du kannst hier bei Bedarf weitere Dateien ergänzen.
    """
    root = Path(".")
    candidates = [
        Path("index.html"),
        Path("style.css"),
        Path("script.js"),
        Path("preview.html"),
    ]

    files = {}
    for p in candidates:
        files[p.name] = read_file(p)

    # Zusätzlich alle .html/.css/.js im Hauptordner einsammeln
    for p in root.iterdir():
        if p.is_file() and p.suffix in {".html", ".css", ".js"}:
            files.setdefault(p.name, read_file(p))

    return files


def call_gpt_for_site_update(command: str, title: str, files: dict) -> str:
    """
    Schickt den Befehl + aktuelle Dateien an GPT
    und erhält ein strukturiertes Ergebnis zurück.
    """
    # Kontext für GPT vorbereiten
    files_text_parts = []
    for name, content in files.items():
        files_text_parts.append(
            f"--- FILE: {name} ---\n{content}\n--- END FILE {name} ---"
        )
    files_text = "\n\n".join(files_text_parts) if files_text_parts else "Keine Dateien vorhanden."

    prompt = f"""
Du bist ein vollautomatisches AI-CMS für eine Streaming-/Talent-Agentur-Website
namens "RESPECT-AGENCY" mit Fokus auf BIGO Live, Hosts und Agentur-Branding.

Der Nutzer steuert dich über GitHub Issues.

Du bekommst:
- Einen Titel des Issues (oft der grobe Befehl)
- Den Inhalt des Issues (detaillierte Anweisungen)
- Die aktuellen Inhalte der Website-Dateien

Deine Aufgabe:
- Erstelle oder aktualisiere eine moderne, responsive Website.
- Verwende HTML5, saubere Struktur, klare Sections, gute Typografie.
- Nutze CSS für Layout, Farben, Buttons und Responsiveness.
- Nutze JavaScript nur, wenn sinnvoll (z.B. für kleinere Interaktionen).
- Inhaltlich: Es ist eine seriöse, aber moderne Agentur (RESPECT-AGENCY).

WICHTIG – AUSGABEFORMAT:
1. Gib NUR folgende Elemente zurück (kein zusätzlicher Text!):
   - Für jede geänderte Datei:
     <FILE name="DATEINAME">
     ...kompletter Inhalt der Datei...
     </FILE>

   - Für jedes zu erzeugende Bild (optional):
     IMAGE: relativer/pfad/zur_datei.png | präzise Bildbeschreibung auf Deutsch

2. Schreibe KEINE Erklärungen, KEINE Kommentare außerhalb dieser Struktur.
3. Wenn du Dateien nicht ändern willst, lasse sie einfach weg.

Aktuelle Dateien:
{files_text}

Issue-Titel:
{title}

Issue-Text / Befehl:
{command}
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": "Du bist ein AI-CMS, das Webseiten-Dateien strikt im vorgegebenen Format zurückgibt.",
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        temperature=0.4,
    )

    return response.choices[0].message.content


def parse_files_from_gpt_output(output: str) -> dict:
    """
    Liest Blöcke im Format
    <FILE name="index.html">
    ...
    </FILE>
    aus und gibt ein Dict {name: content} zurück.
    """
    pattern = re.compile(
        r'<FILE name="(?P<name>[^"]+)">\s*(?P<content>.*?)\s*</FILE>',
        re.DOTALL | re.IGNORECASE,
    )
    files = {}
    for match in pattern.finditer(output):
        name = match.group("name").strip()
        content = match.group("content").strip("\n\r")
        files[name] = content
    return files


def parse_image_tasks_from_output(output: str):
    """
    Sucht nach Zeilen wie:
    IMAGE: images/hero.png | Ein fettes Hero-Bild...

    Gibt Liste von (pfad, prompt)-Tupeln zurück.
    """
    tasks = []
    for line in output.splitlines():
        line = line.strip()
        if line.upper().startswith("IMAGE:"):
            try:
                _, rest = line.split(":", 1)
                path_part, prompt_part = rest.split("|", 1)
                img_path = path_part.strip()
                prompt = prompt_part.strip()
                if img_path and prompt:
                    tasks.append((img_path, prompt))
            except ValueError:
                # Zeile nicht korrekt formatiert -> ignorieren
                continue
    return tasks


def save_files(files: dict):
    """Schreibt die von GPT zurückgegebenen Dateien ins Repo."""
    for name, content in files.items():
        path = Path(name)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        print(f"[AI CMS] Datei aktualisiert: {name}")


def generate_image(prompt: str, file_path: str):
    """Erzeugt ein Bild mit GPT Image und speichert es als PNG."""
    print(f"[AI CMS] Generiere Bild: {file_path} | Prompt: {prompt}")

    response = client.images.generate(
        model="gpt-image-1",
        prompt=prompt,
        size="1024x1024",
    )

    image_base64 = response.data[0].b64_json
    image_bytes = base64.b64decode(image_base64)

    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        f.write(image_bytes)

    print(f"[AI CMS] Bild gespeichert unter: {file_path}")


def handle_image_tasks(tasks):
    """Verarbeitet alle IMAGE:-Aufgaben aus der GPT-Antwort."""
    for img_path, prompt in tasks:
        try:
            generate_image(prompt, img_path)
        except Exception as e:
            print(f"[AI CMS] Fehler beim Generieren von {img_path}: {e}")


def main():
    if not COMMAND and not TITLE:
        print("[AI CMS] Keine Issue-Daten gefunden – nichts zu tun.")
        return

    print("[AI CMS] Starte AI-CMS mit folgendem Befehl:")
    print(f"Titel: {TITLE}")
    print(f"Text: {COMMAND}")

    site_files = collect_site_files()
    gpt_output = call_gpt_for_site_update(COMMAND, TITLE, site_files)

    # Dateien aus der GPT-Antwort extrahieren und speichern
    new_files = parse_files_from_gpt_output(gpt_output)
    if new_files:
        save_files(new_files)
    else:
        print("[AI CMS] Keine <FILE>-Blöcke gefunden – keine Dateien aktualisiert.")

    # Bild-Aufgaben extrahieren und ausführen
    image_tasks = parse_image_tasks_from_output(gpt_output)
    if image_tasks:
        handle_image_tasks(image_tasks)
    else:
        print("[AI CMS] Keine IMAGE-Aufträge gefunden.")

    print("[AI CMS] Fertig.")


if __name__ == "__main__":
    main()
