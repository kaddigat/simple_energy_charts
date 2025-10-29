# Energy Shapes (Canvas) – mit Symbolen

Interaktive Streamlit-Anwendung zum Visualisieren von Stromerzeugung und -verbrauch als **verschiebbare Vektorflächen** – optimiert für Poster, Folien und Infografiken.  
Diese README konzentriert sich auf **`canvas_energy_shapes_withSymbols.py`** und die damit verbundenen Module.

---

## ✨ Kernfunktionen

- **Vektorflächen der Erzeugung** (z. B. Wind, PV, Wasser, Biomasse, Kohle/Öl, Gas, Andere) als frei **verschiebbare Shapes** auf einer Canvas.
- **Fixe Symbole & Labels** (nicht verschiebbar) für klare Zuordnung der Kategorien.
- **Zeitleiste** (Tagesstriche, Wochentagslabels) optional ein-/ausblendbar.
- **SVG‑Export** der gesamten Szene (sauber & verlustfrei statt Pixel-Screenshot).
- Datenbezug aus **Energy‑Charts** (öffentliche Stromerzeugung/Last) inkl. Aggregation in deutsche Kategorien.
- Alternativ: **JSON‑API** via FastAPI und **klassische Stacked‑Charts** via Plotly‑App.

---

## 🔧 Architektur & Datenfluss

```
Energy-Charts API  →  ec_fetch.py  →  ec_transform.py  →  canvas_energy_shapes_withSymbols.py
                                        └→ (Labels/Mapping DE)      └→ SVG/Canvas
                                                        └→ streamlit_app.py (Plotly)
                                                        └→ ec_server.py (FastAPI JSON)
```

1. **`api.py`**: Kleiner Requests‑Wrapper & Fehlerklassen für Energy‑Charts-Endpunkte.  
2. **`ec_fetch.py`**: Zeitraumlogik (z. B. *letzte volle Woche*) + Abruf der Rohreihen.  
3. **`ec_transform.py`**: Mapping/Umbenennung in **deutsche, kombinierte Kategorien** (Wind, Photovoltaik, Wasserkraft, Biomasse, Kohle und Öl, Gas, Andere) sowie **Ausgleich** (Pumpspeicher ±, Import/Export) und **Aggregiertes** (Stromverbrauch).  
4. **`canvas_energy_shapes_withSymbols.py`**: Streamlit‑Canvas, die aus den Zeitreihen **Vektorflächen** baut; ergänzt **fixe Symbole/Labels**; **SVG‑Export**.  
5. **`streamlit_app.py`**: Klassische Stacked‑Area‑Ansicht mit Plotly.  
6. **`ec_server.py`**: JSON‑API (FastAPI) mit `GET /health` und `GET /power?start=YYYY-MM-DD&end=YYYY-MM-DD`.

---

## 🗂️ Projektstruktur (relevant)

```
.
├─ api.py
├─ ec_fetch.py
├─ ec_transform.py
├─ canvas_energy_shapes.py
├─ canvas_energy_shapes_withSymbols.py   ← Fokus dieser README
├─ streamlit_app.py
├─ ec_server.py
├─ requirements.txt
└─ README.md
```

---

## 🚀 Installation

Voraussetzung: Python ≥ 3.10

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scriptsctivate
pip install -r requirements.txt
```

> Hinweis: `fastapi` & `uvicorn` sind nur für die optionale JSON‑API nötig, `plotly` nur für die klassische Streamlit‑App. Für die Canvas‑App sind primär `streamlit`, `pandas`, `numpy` und `requests` relevant.

---

## ▶️ Start der Canvas‑App (mit Symbolen)

```bash
streamlit run canvas_energy_shapes_withSymbols.py
```

- In der **Sidebar** (oder im oberen Bereich) können Zeitraum, Anzeigeoptionen (Achsen, Wochentage, Raster), sowie Export‑Einstellungen (Padding, Maße) gesetzt werden.
- Die farbigen **Erzeugungs‑Shapes** lassen sich per Maus **verschieben/überlagern** (damit Layouts für Poster/Slides entstehen).
- **Symbole & Labels** sind **fix** (absichtlich nicht verschiebbar), damit Orientierung erhalten bleibt.

### Export als SVG
- Über den **„Export als SVG“**‑Button wird die aktuelle Canvas‑Szene als `*.svg` gespeichert.  
- Die Shapes behalten ihre **Vektorqualität** (geeignet für Illustrator, Inkscape, Figma, PowerPoint).

---

## 📊 Alternative Oberflächen

- **Klassische Visualisierung**:
  ```bash
  streamlit run streamlit_app.py
  ```
  Stacked‑Flächen + Linien (z. B. Stromverbrauch) mit deutschen Labels & fixer Reihenfolge.

- **JSON‑API**:
  ```bash
  uvicorn ec_server:app --reload
  # Beispiel:
  # GET http://127.0.0.1:8000/power?start=2025-10-01&end=2025-10-08
  ```
  Liefert `timestamps`, `erzeugerCombined`, `ausgleich`, `aggregated`, `start`, `end`.

---

## ⚙️ Wichtige Konzepte & Optionen

- **Zeitraum** ist i. d. R. **[Start, End)** (Ende exklusiv).  
- **Letzte volle Woche**: Komfortfunktion, um genau 7 volle Tage (Mo–So) abzurufen.  
- **Skalierung**: Y‑Achse der Canvas folgt der Datenrange; in Streamlit‑Plots werden linke/rechte Achse ggf. synchronisiert.  
- **Kategorien/Mapping (DE)**:  
  - *Wasserkraft*, *Biomasse*, *Kohle und Öl*, *Gas*, *Andere*, *Wind*, *Photovoltaik*  
  - *Ausgleich*: **Pumpspeicher** (pos/neg), **Import/Export** (grenzüberschreitend)  
  - *Aggregiertes*: **Stromverbrauch**

> Die Canvas‑Variante mit **Symbolen** fixiert Kategorie‑Labels/Icons, was das Layouten deutlich einfacher macht und Missverständnisse verhindert.

---

## ❗Häufige Fehler & Tipps

- **Leere Daten / zukünftiger Zeitraum**: Prüfen, ob `start < end` und die Tage realistisch sind.  
- **Fehler beim Abruf**: Netzwerk/Firewall prüfen. `api.py` liefert klare Fehlermeldungen (Validation/APIRequest).  
- **Falsche Zeitzone**: Energy‑Charts liefert in der Regel UTC‑nahe Zeitreihen; Anzeige erfolgt lokal. Bei Offsets großzügig denken.  
- **SVG sieht „flach“ aus**: In Vektor‑Tools ggf. Ebenenreihenfolge anpassen oder Deckkraft/Blenden neu setzen.

---

## 🧪 Schneller Funktionstest

```bash
# Canvas mit Symbolen
streamlit run canvas_energy_shapes_withSymbols.py

# Klassische Plot-App
streamlit run streamlit_app.py

# API
uvicorn ec_server:app --reload
curl "http://127.0.0.1:8000/health"
```

---

## 📜 Lizenz & Danksagung

- Daten: **Energy‑Charts** (Fraunhofer ISE) – bitte deren Nutzungsbedingungen beachten.  
- Code: Siehe Lizenzhinweis Ihrer Wahl (z. B. MIT).  
- Danke an die Community rund um **Streamlit**, **FastAPI** und **pandas**.

---

## 💡 FAQ

**Warum zwei Streamlit‑Apps?**  
Die Canvas‑Variante richtet sich an Designer:innen/Kommunikator:innen, die **frei positionierbare Vektorflächen** benötigen. Die klassische Plot‑App ist ideal, wenn es primär um **Zeitreihenanalyse** geht.

**Kann ich eigene Symbole verwenden?**  
Ja – die Datei `canvas_energy_shapes_withSymbols.py` ist dafür gedacht, Symbol‑Assets und Positionen zu pflegen. Ersetzen/ergänzen Sie die Assets und/oder Koordinaten nach Bedarf.

**Wie bekomme ich eine Woche X?**  
Über die Zeitraumsteuerung in der Sidebar (oder durch Anpassung der Default‑Logik in `ec_fetch.py` → `last_full_week()`).
