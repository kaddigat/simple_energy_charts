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

import base64, pathlib
import datetime as dt
import streamlit as st
import pandas as pd
import numpy as np

def png_as_data_url(path: str) -> str | None:
    p = pathlib.Path(path)
    if not p.exists():
        return None
    return "data:image/png;base64," + base64.b64encode(p.read_bytes()).decode("ascii")

from streamlit_drawable_canvas import st_canvas

from ec_fetch import fetch_public_power
from ec_transform import transform_df

# Optional: spezifische Fehlerklasse aus Submodul (falls vorhanden)
try:
    from app.api import APIRequestError  # type: ignore
except Exception:
    class APIRequestError(Exception):
        pass

st.set_page_config(page_title="Strommix in 🇩🇪: Gestalte deine Postkarte 🎨", layout="wide")
st.title("Strommix in 🇩🇪: Gestalte deine Postkarte 🎨")

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
if 'show_symbol_labels' not in ss: ss.show_symbol_labels = False
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
if "show_consumption" not in ss:
    ss.show_consumption = True  # Stromverbrauch standardmäßig sichtbar
if "show_axes" not in ss:
    ss.show_axes = False  # Achsen standardmäßig aus

# ---------------------------
# Sidebar: Start + Tage + Neu laden + Labels
# ---------------------------
with st.sidebar:
    st.header("⚙️ Einstellungen")
    ss.start = st.date_input("Startdatum (inkl.)", value=ss.start)
    ss.days = st.number_input("Anzahl Tage", min_value=1, max_value=7, value=int(ss.days), step=1)
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
        _, df_combined, _, df_aggregated = transform_df(df_raw)
    except Exception:
        st.warning("Daten konnten nicht aufbereitet werden.")
        st.stop()

    if df_combined.empty:
        st.warning("Keine kombinierten Erzeugerdaten verfügbar.")
        st.stop()

    # Zustand setzen (kein rerun nötig)
    ss.df_combined = df_combined
    ss.df_aggregated = df_aggregated
    ss.loaded = True

    # Ursprung zurücksetzen
    ss.order = DEFAULT_ORDER.copy()  # <— Reset auf Default-Reihenfolge bei 'Neu laden'
    available_series = [c for c in df_combined.columns if c != "timestamp"]
    ss.selection = [s for s in ss.order if s in available_series]  # Standard-Auswahl
    ss.prev_selection = ss.selection.copy()
    ss.canvas_json = None  # frisches initial_drawing verwenden
    # Multiselect-Widget und Verbrauchs-Toggle auf Defaults setzen
    st.session_state['selection_widget'] = ss.selection
    ss.show_consumption = True

# Ohne Daten: freundlich beenden
if not ss.loaded or ss.df_combined is None or ss.df_combined.empty:
    st.info("Bitte Startdatum und Anzahl Tage wählen und **Neu laden**.")
    st.stop()

# ---------------------------
# Auswahl der Energieträger (mit Reihenfolge-Hinweis)
# ---------------------------
available_series = [c for c in ss.df_combined.columns if c != "timestamp"]
# Hinweis: Nach dem ersten Laden NICHT automatisch auffüllen.
# Der Benutzer kann bewusst alle entfernen und später einzelne wieder hinzufügen.
st.write("**Energieträger auswählen (werden als verschiebbare Flächen erzeugt).**  "
         "_Reihenfolge steuerst du durch Entfernen & erneutes Hinzufügen (neue Einträge liegen oben)_")

new_selection = st.multiselect(
    label="",
    options=available_series,
    default=ss.selection,
    key='selection_widget'
)

# Auswahl geändert → Layout verwerfen (neu aus Daten generieren)
selected_now = st.session_state.get('selection_widget', new_selection)
if set(selected_now) != set(ss.selection):
    ss.selection = list(selected_now)
    ss.prev_selection = list(selected_now)
    ss.canvas_json = None

# Anzeigeoption: Stromverbrauch (rote Linie)
col_consumption, col_axes, col_labels = st.columns(3)
with col_consumption:
    ss.show_consumption = st.toggle('Stromverbrauch anzeigen', value=ss.show_consumption)
with col_axes:
    ss.show_axes = st.toggle('Achsen anzeigen', value=ss.show_axes)


with col_labels:
    ss.show_symbol_labels = st.toggle('Labels anzeigen', value=ss.show_symbol_labels)
# Reihenfolge: bestehende behalten; neu ausgewählte kommen oben dazu
current_order = [s for s in ss.order if s in ss.selection] + [s for s in ss.selection if s not in ss.order]
ss.order = current_order + [s for s in ss.order if s not in ss.selection]
stack_order = [s for s in ss.order if s in ss.selection]
# Fallback: falls Reihenfolge-Intersection leer (z. B. nach komplettem Entfernen),
# verwende die aktuelle Auswahl direkt als Stack-Reihenfolge.
if not stack_order and ss.selection:
    stack_order = ss.selection.copy()

if not stack_order:
    if not (ss.show_consumption and hasattr(ss, 'df_aggregated') and ss.df_aggregated is not None and 'Stromverbrauch' in ss.df_aggregated.columns):
        st.info("Bitte mindestens einen Energieträger auswählen oder den Stromverbrauch anzeigen.")

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
# Wenn Stromverbrauch angezeigt wird, in die Skalierung einbeziehen
try:
    if ss.show_consumption and hasattr(ss, 'df_aggregated') and ss.df_aggregated is not None and 'Stromverbrauch' in ss.df_aggregated.columns:
        cons_arr = pd.to_numeric(ss.df_aggregated['Stromverbrauch'], errors='coerce').fillna(0.0).to_numpy()
        if cons_arr.size > 0:
            y_max = max(y_max, float(np.nanmax(cons_arr)))
except Exception:
    pass
usable_height = CANVAS_HEIGHT - PADDING_TOP - PADDING_BOTTOM
y_scale = usable_height / max(y_max, 1e-9)

polygons = []
offset = np.zeros(n)
for sname in stack_order:
    series = _safe_numeric(dfc[sname])
    top = offset + series
    bottom = offset
    color = COLOR.get(sname, "#999999CC")
    polygons.append(_build_normalized_path(sname, top, bottom, x_px, y_scale, color))
    offset = top

# Stromverbrauch als rote Linie (nicht verschiebbar)
consumption_objects = []
try:
    dfagg = ss.df_aggregated if hasattr(ss, 'df_aggregated') else None
    if ss.show_consumption and dfagg is not None and 'Stromverbrauch' in dfagg.columns:
        cons = pd.to_numeric(dfagg['Stromverbrauch'], errors='coerce').fillna(0.0).to_numpy()
        # Länge an x_px angleichen
        m = int(min(len(cons), len(x_px)))
        cons = cons[:m]
        x_line = x_px[:m]
        y_line = CANVAS_HEIGHT - PADDING_BOTTOM - cons * y_scale
        # Relative Pfadkoordinaten wie bei den Flächenobjekten
        min_x = float(x_line.min())
        min_y = float(y_line.min())
        parts = [f"M {float(x_line[0]-min_x):.1f} {float(y_line[0]-min_y):.1f}"]
        for i in range(1, m):
            parts.append(f"L {float(x_line[i]-min_x):.1f} {float(y_line[i]-min_y):.1f}")
        path_str = ' '.join(parts)
        consumption_objects.append({
            'type': 'path',
            'path': path_str,
            'left': min_x,
            'top': min_y,
            'fill': '',
            'stroke': '#ff0000',
            'strokeWidth': 4,
            'strokeUniform': True,
            'selectable': False,
            'evented': False,
            'hasControls': False,
            'hasBorders': False,
            'lockMovementX': True,
            'lockMovementY': True,
            'lockScalingX': True,
            'lockScalingY': True,
            'lockRotation': True,
            'hoverCursor': 'default',
            'name': 'Stromverbrauch',
        })
except Exception:
    pass
# Nullinie (immer sichtbar, sehr dünne schwarze Linie, nicht verschiebbar)
zero_line_objects = []
try:
    # Nutze x_px für Länge, baseline bei y=0
    if len(x_px) >= 2:
        min_x = float(x_px[0])
        max_x = float(x_px[-1])
        y0 = float(CANVAS_HEIGHT - PADDING_BOTTOM)
        path_str = f"M {0:.1f} {0:.1f} L {max_x - min_x:.1f} {0:.1f}"
        zero_line_objects.append({
            'type': 'path',
            'path': path_str,
            'left': min_x,
            'top': y0,
            'fill': '',
            'stroke': '#000000',
            'strokeWidth': 1,
            'strokeUniform': True,
            'selectable': False,
            'evented': False,
            'hasControls': False,
            'hasBorders': False,
            'lockMovementX': True,
            'lockMovementY': True,
            'lockScalingX': True,
            'lockScalingY': True,
            'lockRotation': True,
            'hoverCursor': 'default',
            'name': 'Nullinie',
        })
except Exception:
    pass



# ---------- Achsen-Helfer (Fabric) ----------
def _fabric_text(text, left, top, *, angle=0, font_size=14, fill="#333333", name="label", locked=True):
    return {
        "type": "textbox",
        "text": str(text),
        "left": float(left),
        "top": float(top),
        "angle": float(angle),
        "fontSize": int(font_size),
        "fill": fill,
        "name": name,
        "selectable": not locked,
        "evented": not locked,
        "lockMovementX": locked,
        "lockMovementY": locked,
        "hasBorders": False,
        "hasControls": False,
        "editable": False,
        "fontFamily": "Inter, Roboto, Arial, sans-serif",
    }

def _fabric_line(x1, y1, x2, y2, *, stroke="#000000", width=1, name="axis", round_cap=True):
    obj = {
        "type": "line",
        "x1": float(x1), "y1": float(y1),
        "x2": float(x2), "y2": float(y2),
        "stroke": stroke,
        "strokeWidth": float(width),
        "name": name,
        "selectable": False,
        "evented": False,
    }
    if round_cap:
        obj["strokeLineCap"] = "round"
    return obj

WD_SHORT = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]

def _weekday_short_from_ts(ts) -> str:
    try:
        return WD_SHORT[int(pd.to_datetime(ts).weekday())]
    except Exception:
        return ""

def _day_boundary_indices(ts_series: "pd.Series") -> list[int]:
    # indices where day changes (including 0)
    idxs = [0]
    if ts_series is None or len(ts_series) == 0:
        return idxs
    ts = pd.to_datetime(ts_series)
    last = ts.iloc[0].date()
    for i in range(1, len(ts)):
        d = ts.iloc[i].date()
        if d != last:
            idxs.append(i)
            last = d
    return sorted(set(idxs))


def build_axes_objects_minimal(timestamps: "pd.Series", x_px: "np.ndarray", y_max_value: float) -> list[dict]:
    """
    Minimaler Achsen-Satz:
      - X: Tagesgrenzen (Ticks) + Wochentags-Labels an der Position 12:00 Uhr
      - Y: vertikale Achse links; "0" an der Nullinie; Einheiten-Titel; GW-Markierung
    """
    if not getattr(ss, "show_axes", False):
        return []
    objs: list[dict] = []
    # Basiskoordinaten
    x_left = float(PADDING_LEFT)
    y_bottom = float(CANVAS_HEIGHT - PADDING_BOTTOM)
    y_top = float(PADDING_TOP)

    # Y-Achse
    objs.append(_fabric_line(x_left, y_top, x_left, y_bottom, stroke="#000000", width=1, name="axis-y", round_cap=True))

    # X: Tagesgrenzen (Start jedes Tages) als Ticks (etwas längere Linie)
    try:
        ts = pd.to_datetime(timestamps)
        n = len(x_px)
        day_idxs = _day_boundary_indices(ts)
        for di in day_idxs:
            if n <= 0:
                continue
            xi = min(max(di, 0), n-1)
            x = float(x_px[xi])
            objs.append(_fabric_line(x, y_bottom, x, y_bottom + 8, stroke="#000000", width=1, name="tick-x-boundary", round_cap=True))

        # Wochentags-Labels bei 12:00 je Tag
        unique_days = sorted(set(ts.dt.date.tolist()))
        for d in unique_days:
            target = pd.Timestamp(year=d.year, month=d.month, day=d.day, hour=12, minute=0, second=0)
            idx = int((ts - target).abs().argmin())
            xi = min(max(idx, 0), n-1)
            x_mid = float(x_px[xi])
            wd = _weekday_short_from_ts(ts.iloc[xi])
            if wd:
                objs.append(_fabric_text(wd, x_mid - 10, y_bottom + 14, font_size=14, fill="#333333", name=f"ticklabel-x-mid-{wd}", locked=True))
    except Exception:
        pass

    # Y-"0" an Nullinie
    try:
        objs.append(_fabric_text("0", x_left - 12, y_bottom - 6, font_size=14, fill="#333333", name="ylabel-0", locked=True))
    except Exception:
        pass

    # Y: Einheiten-Titel (gedreht, mittig)
    try:
        y_mid = (y_top + y_bottom) / 2.0
        objs.append(_fabric_text("Elektrische Leistung", x_left - 54, y_mid, angle=-90, font_size=14, fill="#333333", name="ylabel-title", locked=True))
    except Exception:
        pass

    # Y: GW-Markierung (abgerundete Maximalleistung)
    try:
        y_max_val = float(y_max_value)
        gw_floor = int(y_max_val // 1000)  # volle GW
        if gw_floor >= 1:
            y_val = gw_floor * 1000.0
            usable_h = (CANVAS_HEIGHT - PADDING_TOP - PADDING_BOTTOM)
            y_pos = float(CANVAS_HEIGHT - PADDING_BOTTOM - (y_val * (usable_h / max(y_max_val, 1e-9))))
            # Tick an der Achse
            objs.append(_fabric_line(x_left - 6, y_pos, x_left, y_pos, stroke="#000000", width=1, name="tick-y-gw", round_cap=True))
            # Label "x GW"
            objs.append(_fabric_text(f"{gw_floor} GW", x_left - 44, y_pos - 6, font_size=14, fill="#333333", name="ylabel-gw", locked=True))
    except Exception:
        pass

    return objs

axes_objects = build_axes_objects_minimal(timestamps=t, x_px=x_px, y_max_value=y_max)
initial_drawing = {"version": "5.2.4", "objects": polygons + consumption_objects + zero_line_objects + axes_objects}

# initial_for_canvas:
reuse_saved_layout = ss.canvas_json is not None and set(ss.selection) == set(ss.prev_selection)
initial_for_canvas = ss.canvas_json if reuse_saved_layout else initial_drawing

# ---------------------------
# Canvas anzeigen
# ---------------------------

# --- PNG-Label-Icons (oben rechts, reagiert auf "Labels anzeigen") ---
try:
    symbol_objects = []
    if ss.get("show_symbol_labels", False):
        import pathlib as _pl

        # Liste aller anzuzeigenden Icons (Name, Pfad)
        icons = [
            ("wind", "icons/icon_wind.png"),
            ("solar", "icons/icon_solar.png"),
            ("wasserkraft", "icons/icon_wasserkraft.png"),
        ]

        # Canvas-Geometrie
        canvas_w = CANVAS_WIDTH if "CANVAS_WIDTH" in globals() else 980
        pad_right = globals().get("PADDING_RIGHT", 24)
        pad_top = globals().get("PADDING_TOP", 16)

        # Einheitliche Icon-Größe
        icon_px = 72
        scale = icon_px / 256.0

        # Icons rechts oben untereinander anordnen
        for i, (name, path) in enumerate(icons):
            icon_path = _pl.Path(path)
            src_icon = png_as_data_url(str(icon_path)) if icon_path.exists() else None

            left = canvas_w - pad_right - icon_px - 12
            top = pad_top + 12 + i * (icon_px + 12)  # vertikal untereinander

            if src_icon:
                # Weißer Hintergrund hinter dem Icon
                symbol_objects.append({
                    "type": "rect",
                    "left": left - 6,
                    "top": top - 6,
                    "width": icon_px + 12,
                    "height": icon_px + 12,
                    "fill": "#FFFFFF",
                    "name": f"icon-bg-{name}",
                    "selectable": False,
                    "evented": False,
                    "lockMovementX": True,
                    "lockMovementY": True,
                    "hasBorders": False,
                    "hasControls": False,
                })

                # Das eigentliche Icon
                symbol_objects.append({
                    "type": "image",
                    "src": src_icon,
                    "left": left,
                    "top": top,
                    "angle": 0,
                    "scaleX": scale,
                    "scaleY": scale,
                    "name": f"icon:{name}",
                    "selectable": True,
                    "evented": True,
                    "lockMovementX": False,
                    "lockMovementY": False,
                    "hasBorders": True,
                    "hasControls": True,
                })

        # Symbole an das Canvas-Objekt anhängen
        try:
            initial_for_canvas["objects"] += symbol_objects
        except Exception:
            try:
                initial_drawing["objects"] += symbol_objects
            except Exception:
                pass
except Exception:
    pass


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
