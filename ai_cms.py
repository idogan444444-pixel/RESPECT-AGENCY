import os
import re
import base64
from openai import OpenAI

# OpenAI Client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

 command = os.getenv("ISSUE_BODY") or ""
title = os.getenv("ISSUE_TITLE") or ""

def read(path: str) -> str:
    return open(path, "r", encoding="utf-8").read() if os.path.exists(path) else ""

# Bestehende Dateien einlesen (falls vorhanden)
files = {
    "index.html": read("index.html"),
    "style.css": read("style.css"),
    "script.js": read("script.js"),
}

def generate_image(prompt: str, file_path: str):
    print(f"Generating image: {file_path} | Prompt: {prompt}")
    response = client.images.generate(
        model="gpt-image-1",
        prompt=prompt,
        size="1024x1024")

    image_base64 = response.data[0].b64_json
    image_bytes = base64.b64decode(image_base64)

    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "wb") as f:
        f.write(image_bytes)PROMPT = f"""
Du bist ein vollautomatisches AI-CMS für eine Streaming-/Talent-Agentur namens "RESPECT AGENCY".
Du verwaltest HTML, CSS, JS **und** Bilder.

---BEFEHL (vom Benutzer)---
{command}
---TITLE---
{title}

Bestehende Dateien (falls vorhanden):
{files}

Ziele:
- Erstelle ein modernes, responsives Basis-Theme für die Website "RESPECT AGENCY".
- Fokus: BIGO Live, Hosts, Agentur-Branding.
- Mobile First, saubere Typografie, klare Sections.
- Seitenstruktur:
  - index.html (Landingpage)
  - hosts.html
  - faq.html
  - contact.html
- Navigation + Footer überall gleich.
- Nutze moderne HTML5-Struktur und Animationen.
- Bilder automatisch generieren.

Bildregeln:
- Für jedes Bild zwingend eine Zeile:
  IMAGE: <pfad> | PROMPT: <beschreibung>
- Binde die Bilder direkt ein.

Antwortformat:
---FILENAME: dateiname---
[vollständiger Code]
---END---
"""response = client.chat.completions.create(
    model="gpt-4.1-mini",
    messages=[{"role": "user", "content": PROMPT}]
)

content = response.choices[0].message.content

# 1) Bild-Tasks auslesen
image_tasks = re.findall(r"IMAGE:\s*(.*?)\s*\|\s*PROMPT:\s*(.*)", content)

for path, img_prompt in image_tasks:
    generate_image(img_prompt.strip(), path.strip())

# 2) Dateien aus KI-Antwort extrahieren
blocks = re.findall(r"---FILENAME: (.*?)---(.*?)---END---", content, re.DOTALL)

for filename, code in blocks:
    filename = filename.strip()
    code = code.strip()
    if not filename:
        continue
    print(f"Writing file: {filename}")
    with open(filename, "w", encoding="utf-8") as f:
        f.write(code)

print("AI CMS: Dateien & Bilder vollständig aktualisiert.")
