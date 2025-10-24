# canvas_energy_shapes.py
# -*- coding: utf-8 -*-
"""
Energy-Charts → verschiebbare Vektor-Flächen (Fabric.js via streamlit-drawable-canvas)
- Startdatum + Anzahl Tage (1–7), Enddatum intern
- Ein Button: 'Neu laden' (lädt & setzt Ursprung zurück)
- Zukunft/404/no data werden freundlich abgefangen
- Kein Lösch-Schutz (vereinfachtes, stabiles Verhalten)
- Reihenfolge steuerbar durch Entfernen & erneutes Hinzufügen (neue Einträge liegen oben)
- Download des aktuellen Canvas-Zustands als SVG (korrekte Positionen/Abstände)
- Optionale feste Labels (nicht verschiebbar)

Abhängigkeiten:
    pip install streamlit streamlit-drawable-canvas pandas numpy
"""
from __future__ import annotations

import datetime as dt
import streamlit as st
import pandas as pd
import numpy as np
from streamlit_drawable_canvas import st_canvas

from ec_fetch import fetch_public_power
from ec_transform import transform_df

# Optional: spezifische Fehlerklasse aus Submodul (falls vorhanden)
try:
    from app.api import APIRequestError  # type: ignore
except Exception:
    class APIRequestError(Exception):
        pass

st.set_page_config(page_title="🎨 Strommix in 🇩🇪", layout="wide")
st.title("🎨 Strommix in 🇩🇪")

# Farben (unten → oben gedacht)
COLOR = {
    "Biomasse": "#2ca02cCC",
    "Photovoltaik": "#ffd700CC",
    "Wasserkraft": "#003366CC",
    "Wind": "#87ceebCC",
    "Kohle und Öl": "#8b4513CC",
    "Gas": "#d2b48cCC",
    "Andere": "#7f7f7fCC",
}
DEFAULT_ORDER = [
    "Andere",
    "Wasserkraft",
    "Biomasse",
    "Wind",
    "Photovoltaik",
    "Kohle und Öl",
    "Gas",
]

# Canvas-Geometrie
CANVAS_WIDTH = 1200
CANVAS_HEIGHT = 600
PADDING_TOP = 20
PADDING_BOTTOM = 40
PADDING_LEFT = 40
PADDING_RIGHT = 20

# ---------------------------
# Session-State
# ---------------------------
ss = st.session_state
if "loaded" not in ss:
    ss.loaded = False
if "df_combined" not in ss:
    ss.df_combined: pd.DataFrame | None = None
if "start" not in ss:
    ss.start = dt.date.today() - dt.timedelta(days=7)
if "days" not in ss:
    ss.days = 7
if "selection" not in ss:
    ss.selection: list[str] = []
if "order" not in ss:
    ss.order = DEFAULT_ORDER.copy()
if "canvas_json" not in ss:
    ss.canvas_json: dict | None = None
if "prev_selection" not in ss:
    ss.prev_selection: list[str] = []
if "labels_on" not in ss:
    ss.labels_on = False  # Labels optional

# ---------------------------
# Sidebar: Start + Tage + Neu laden + Labels
# ---------------------------
with st.sidebar:
    st.header("⚙️ Einstellungen")
    ss.start = st.date_input("Startdatum (inkl.)", value=ss.start)
    ss.days = st.number_input("Anzahl Tage", min_value=1, max_value=7, value=int(ss.days), step=1)
    ss.labels_on = st.checkbox("Labels anzeigen (fix, nicht verschiebbar)", value=ss.labels_on)
    do_load = st.button("🔁 Neu laden", type="primary", use_container_width=True)

# ---------------------------
# Daten laden (und Ursprung zurücksetzen)
# ---------------------------
if do_load:
    end = ss.start + dt.timedelta(days=int(ss.days))
    if end <= ss.start:
        st.error("Ende muss nach Start liegen (exklusiv).")
        st.stop()

    try:
        with st.spinner("Lade Energy-Charts-Daten..."):
            df_raw = fetch_public_power(ss.start, end)
    except APIRequestError:
        st.warning("Für den gewählten Zeitraum sind keine Daten verfügbar.")
        st.stop()
    except Exception:
        st.warning("Für den gewählten Zeitraum sind keine Daten verfügbar.")
        st.stop()

    if df_raw is None or df_raw.empty:
        st.warning("Für den gewählten Zeitraum sind keine Daten verfügbar.")
        st.stop()

    try:
        _, df_combined, _, _ = transform_df(df_raw)
    except Exception:
        st.warning("Daten konnten nicht aufbereitet werden.")
        st.stop()

    if df_combined.empty:
        st.warning("Keine kombinierten Erzeugerdaten verfügbar.")
        st.stop()

    # Zustand setzen (kein rerun nötig)
    ss.df_combined = df_combined
    ss.loaded = True

    # Ursprung zurücksetzen
    ss.order = DEFAULT_ORDER.copy()  # <— Reset auf Default-Reihenfolge bei 'Neu laden'
    available_series = [c for c in df_combined.columns if c != "timestamp"]
    ss.selection = [s for s in ss.order if s in available_series]  # Standard-Auswahl
    ss.prev_selection = ss.selection.copy()
    ss.canvas_json = None  # frisches initial_drawing verwenden

# Ohne Daten: freundlich beenden
if not ss.loaded or ss.df_combined is None or ss.df_combined.empty:
    st.info("Bitte Startdatum und Anzahl Tage wählen und **Neu laden**.")
    st.stop()

# ---------------------------
# Auswahl der Energieträger (mit Reihenfolge-Hinweis)
# ---------------------------
available_series = [c for c in ss.df_combined.columns if c != "timestamp"]
if not ss.selection:
    ss.selection = [s for s in ss.order if s in available_series]

st.write("**Energieträger auswählen (werden als verschiebbare Flächen erzeugt).**  "
         "_Reihenfolge steuerst du durch Entfernen & erneutes Hinzufügen (neue Einträge liegen oben)_")

new_selection = st.multiselect(
    label="",
    options=available_series,
    default=ss.selection,
)

# Auswahl geändert → Layout verwerfen (neu aus Daten generieren)
if set(new_selection) != set(ss.selection):
    ss.selection = new_selection
    ss.prev_selection = new_selection.copy()
    ss.canvas_json = None

# Reihenfolge: bestehende behalten; neu ausgewählte kommen oben dazu
current_order = [s for s in ss.order if s in ss.selection] + [s for s in ss.selection if s not in ss.order]
ss.order = current_order + [s for s in ss.order if s not in ss.selection]
stack_order = [s for s in ss.order if s in ss.selection]

if not stack_order:
    st.info("Bitte mindestens einen Energieträger auswählen.")
    st.stop()

# ---------------------------
# Flächen (Polygonpfade) generieren – OBJ-LOKAL normalisiert
# ---------------------------
def _safe_numeric(s: pd.Series) -> np.ndarray:
    return pd.to_numeric(s, errors="coerce").fillna(0.0).to_numpy()

def _build_normalized_path(name: str, top: np.ndarray, bottom: np.ndarray,
                           x_px: np.ndarray, y_scale: float, color: str) -> dict:
    """Erzeugt ein Fabric-Path-Objekt mit PFADKOORDINATEN RELATIV zu (0,0),
    und setzt left/top = (minX, minY). Dadurch stimmen Positionen/Abstände nach Verschieben & im SVG-Export."""
    # Absolutpunkte (Canvas-Koordinaten)
    xs_upper = x_px
    ys_upper = CANVAS_HEIGHT - PADDING_BOTTOM - top * y_scale
    xs_lower = x_px[::-1]
    ys_lower = CANVAS_HEIGHT - PADDING_BOTTOM - bottom[::-1] * y_scale

    # Alle Punkte für Bounding-Box
    all_x = np.concatenate([xs_upper, xs_lower])
    all_y = np.concatenate([ys_upper, ys_lower])

    min_x = float(np.min(all_x))
    min_y = float(np.min(all_y))

    # In Objektkoordinaten verschieben (0,0) = (min_x, min_y)
    xu = xs_upper - min_x
    yu = ys_upper - min_y
    xl = xs_lower - min_x
    yl = ys_lower - min_y

    # Pfadstring relativ zu (0,0)
    parts = [f"M {xu[0]:.1f} {yu[0]:.1f}"]
    for i in range(1, len(xu)):
        parts.append(f"L {xu[i]:.1f} {yu[i]:.1f}")
    for i in range(len(xl)):
        parts.append(f"L {xl[i]:.1f} {yl[i]:.1f}")
    parts.append("Z")
    path_str = " ".join(parts)

    return {
        "type": "path",
        "path": path_str,
        "left": min_x,            # Position im Canvas
        "top": min_y,
        "fill": color,
        "stroke": "#333333",
        "strokeWidth": 1,
        "opacity": 0.9,
        "selectable": True,
        "hoverCursor": "move",
        "name": name,
        "scaleX": 1.0,
        "scaleY": 1.0,
        "angle": 0,
    }

dfc = ss.df_combined
t = pd.to_datetime(dfc["timestamp"])
n = len(t)
x_px = np.linspace(PADDING_LEFT, CANVAS_WIDTH - PADDING_RIGHT, n)

vals = np.column_stack([_safe_numeric(dfc[s]) for s in stack_order]) if stack_order else np.zeros((n, 0))
cum_max = np.max(np.cumsum(vals, axis=1), axis=1) if vals.shape[1] > 0 else np.zeros(n)
y_max = max(1.0, float(np.max(cum_max))) if cum_max.size > 0 else 1.0
usable_height = CANVAS_HEIGHT - PADDING_TOP - PADDING_BOTTOM
y_scale = usable_height / y_max

polygons = []
offset = np.zeros(n)
for sname in stack_order:
    series = _safe_numeric(dfc[sname])
    top = offset + series
    bottom = offset
    color = COLOR.get(sname, "#999999CC")
    polygons.append(_build_normalized_path(sname, top, bottom, x_px, y_scale, color))
    offset = top

# Optionale fixe Labels (nicht verschiebbar)
label_objects = []
if ss.labels_on:
    for obj in polygons:
        name = obj.get("name", "")
        lx = float(obj["left"]) + 10
        ly = float(obj["top"]) + 16  # 16 ~ baseline für fontSize 14
        label_objects.append({
            "type": "textbox",
            "text": name,
            "left": lx,
            "top": ly,
            "fontSize": 14,
            "fill": "#222222",
            "selectable": False,
            "evented": False,
            "hasControls": False,
            "lockMovementX": True,
            "lockMovementY": True,
            "name": f"label:{name}",
        })

initial_drawing = {"version": "5.2.4", "objects": polygons + label_objects}

# initial_for_canvas:
reuse_saved_layout = ss.canvas_json is not None and set(ss.selection) == set(ss.prev_selection)
initial_for_canvas = ss.canvas_json if reuse_saved_layout else initial_drawing

# ---------------------------
# Canvas anzeigen
# ---------------------------
st.subheader("🖼️ Verschiebbare Flächen")
canvas = st_canvas(
    fill_color="rgba(0,0,0,0)",
    stroke_width=1,
    stroke_color="#000000",
    background_color="#ffffff",
    height=CANVAS_HEIGHT,
    width=CANVAS_WIDTH,
    drawing_mode="transform",     # bewegen/skalieren/rotieren
    initial_drawing=initial_for_canvas,
    display_toolbar=True,
    key="canvas_poly_static_key",
)

# ---------------------------
# Serverseitiger SVG-Export aus Fabric-JSON
# ---------------------------
def _fabric_json_to_svg(j: dict | None, width: int, height: int) -> str | None:
    """Konvertiert Fabric-JSON (st_canvas) in SVG mit korrekten Positionen/Abständen.
       Erwartet path-Objekte mit objektlokalen Koordinaten und left/top/scale/angle."""
    if not j or "objects" not in j:
        return None

    def _path_to_d(path_val):
        # kann String (unser Format) oder Array (Fabric-Format) sein
        if isinstance(path_val, str):
            return path_val
        if isinstance(path_val, list):
            parts = []
            for seg in path_val:
                if isinstance(seg, list) and seg:
                    cmd = seg[0]
                    nums = seg[1:]
                    nums_fmt = " ".join(f"{float(v):.3f}" if isinstance(v, (int, float)) else str(v) for v in nums)
                    parts.append(f"{cmd} {nums_fmt}".strip())
                elif isinstance(seg, str):
                    parts.append(seg)
            return " ".join(parts)
        return ""

    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
           f'viewBox="0 0 {width} {height}">']

    for obj in j["objects"]:
        otype = obj.get("type")
        if otype == "path":
            d = _path_to_d(obj.get("path"))
            if not d:
                continue
            fill = obj.get("fill", "none")
            stroke = obj.get("stroke", "none")
            stroke_w = obj.get("strokeWidth", 1)
            opacity = obj.get("opacity", 1)

            # Transform aus left/top/angle/scale – da Pfad nun objektlokal ist
            tx = float(obj.get("left", 0) or 0)
            ty = float(obj.get("top", 0) or 0)
            angle = float(obj.get("angle", 0) or 0)
            sx = float(obj.get("scaleX", 1) or 1)
            sy = float(obj.get("scaleY", 1) or 1)
            transforms = []
            if tx or ty:
                transforms.append(f"translate({tx:.3f},{ty:.3f})")
            if angle:
                transforms.append(f"rotate({angle:.3f})")
            if sx != 1 or sy != 1:
                transforms.append(f"scale({sx:.6f},{sy:.6f})")
            t_attr = f' transform="{" ".join(transforms)}"' if transforms else ""

            svg.append(
                f'<path d="{d}" fill="{fill}" stroke="{stroke}" stroke-width="{stroke_w}" '
                f'opacity="{opacity}"{t_attr}/>'
            )

        elif otype in ("textbox", "text"):
            text = (obj.get("text") or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            font_size = int(obj.get("fontSize", 14))
            fill = obj.get("fill", "#000000")
            # Fabric top ist obere Kante; SVG y ist baseline → ~ +0.8*font_size
            x = float(obj.get("left", 0) or 0)
            y = float(obj.get("top", 0) or 0) + 0.8 * font_size
            svg.append(
                f'<text x="{x:.1f}" y="{y:.1f}" font-size="{font_size}" fill="{fill}">{text}</text>'
            )

    svg.append("</svg>")
    return "".join(svg)

# Download-Button für aktuelle Szene als SVG
svg_str = _fabric_json_to_svg(canvas.json_data, CANVAS_WIDTH, CANVAS_HEIGHT)
if svg_str:
    st.download_button(
        label="⬇️ Aktuelle Grafik als SVG herunterladen",
        data=svg_str.encode("utf-8"),
        file_name="energy_canvas.svg",
        mime="image/svg+xml",
        use_container_width=True,
    )

# Quellenangabe unter der Grafik (klein)
st.markdown(
    "<div style='text-align:center; font-size:0.85em; color:gray;'>"
    "Quelle: <a href='https://energy-charts.info' target='_blank' "
    "style='color:gray; text-decoration:none;'>energy-charts.info (Fraunhofer ISE)</a>"
    "</div>",
    unsafe_allow_html=True
)
