# streamlit_app.py
# -*- coding: utf-8 -*-
"""
Interaktive Streamlit-Oberfläche (ersetzt die klassische Plot-Routine).
- Freie Datumswahl
- Feste Farben und deutsche Labels
- Aggregiert: nur "Stromverbrauch" (kein "Residual load")
- Rechte Achse exakt gleiche Skala wie linke (matches="y")
- Definierte Stack-Reihenfolge (unten → oben)
- Freundliche Meldung bei leeren/ zukünftigen Zeiträumen
- Quellenangabe unter dem Plot
- Button exakt auf Höhe der Datumsfelder (ohne fragile CSS-Hacks)
"""
from __future__ import annotations
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import datetime as dt

from ec_fetch import fetch_public_power, last_full_week
from ec_transform import transform_df

# ---- Seitentitel wie zuvor ----
st.set_page_config(page_title="Strommix in 🇩🇪: Energy-Charts", layout="wide")
st.title("🔌 Strommix in 🇩🇪: Energy-Charts")

# ---- Feste Farben (Hex) ----
COLOR = {
    # Aggregiert
    "Stromverbrauch": "#d62728",            # rot

    # Erzeuger (kombiniert)
    "Biomasse": "#2ca02c",                  # grün
    "Photovoltaik": "#ffd700",              # gelb
    "Wasserkraft": "#003366",               # dunkelblau
    "Wind": "#87ceeb",                      # hellblau
    "Kohle und Öl": "#8b4513",              # dunkelbraun
    "Gas": "#d2b48c",                       # hellbraun
    "Andere": "#7f7f7f",                    # grau

    # Ausgleich (deutsche Labels)
    "Pumpspeicher (Stromerzeugung)": "#555555",
    "Pumpspeicher (Stromverbrauch)": "#999999",
    "Grenzüberschreitender Stromhandel": "#444444",
}

# ---- Gewünschte Stack-Reihenfolge: unten → oben ----
STACK_ORDER = [
    "Pumpspeicher (Stromverbrauch)",
    "Grenzüberschreitender Stromhandel",
    "Andere",
    "Wasserkraft",
    "Biomasse",
    "Wind",
    "Photovoltaik",
    "Kohle und Öl",
    "Gas",
    "Pumpspeicher (Stromerzeugung)",
]

def _safe_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").fillna(0.0)

def _try_get_column(df: pd.DataFrame, col: str) -> pd.Series | None:
    if col in df.columns:
        return _safe_numeric(df[col])
    return None

def _build_stacked_traces_by_order(t: pd.Series, df_combined: pd.DataFrame, df_bal: pd.DataFrame) -> list[go.Scatter]:
    """Baut gestapelte Flächen-Traces in fester Reihenfolge (unten→oben)."""
    traces: list[go.Scatter] = []
    for name in STACK_ORDER:
        s = _try_get_column(df_bal, name)
        if s is None:
            s = _try_get_column(df_combined, name)
        if s is None:
            continue
        color = COLOR.get(name)
        traces.append(
            go.Scatter(
                x=t, y=s, name=name,
                mode="lines",
                stackgroup="power",
                line=dict(width=0.8, color=color) if color else dict(width=0.8),
                fillcolor=color if color else None,
            )
        )
    return traces

def _line_traces_from_df(df: pd.DataFrame, yaxis="y2", exclude=("timestamp",)):
    """Erzeugt Linien-Traces (Plotly) für rechte Achse ('Stromverbrauch')."""
    traces = []
    t = pd.to_datetime(df["timestamp"])
    for c in [c for c in df.columns if c not in exclude]:
        y = pd.to_numeric(df[c], errors="coerce")
        color = COLOR.get(c)
        traces.append(
            go.Scatter(
                x=t, y=y, name=c, mode="lines", yaxis=yaxis,
                line=dict(width=2, color=color) if color else dict(width=2)
            )
        )
    return traces

# ---- Zeitraum-UI: Button exakt auf Höhe der Inputs ----
default_s, default_e = last_full_week()
col1, col2, col3 = st.columns([1, 1, 0.7])

with col1:
    st.markdown("**Start (inkl.)**")  # eigenes Label, damit der Input höher sitzt
    start = st.date_input(label="", value=default_s, label_visibility="collapsed")

with col2:
    st.markdown("**Ende (exkl.)**")
    end = st.date_input(label="", value=default_e, label_visibility="collapsed")

with col3:
    # Spacer ersetzt Label-Höhe -> Button beginnt auf gleicher vertikaler Linie wie die Inputs
    st.markdown("&nbsp;", unsafe_allow_html=True)
    go_btn = st.button("📊 Plot aktualisieren", use_container_width=True)

# ---- Hauptlogik ----
if go_btn:
    if end <= start:
        st.error("Ende muss nach Start liegen (exklusiv).")
        st.stop()

    try:
        with st.spinner("Lade Daten..."):
            df_raw = fetch_public_power(start, end)

        if df_raw is None or df_raw.empty:
            st.warning("Für den gewählten Zeitraum sind keine Daten verfügbar.")
            st.stop()

        _, df_combined, df_bal, df_agg = transform_df(df_raw)

        if df_combined.empty and df_bal.empty and df_agg.empty:
            st.warning("Für den gewählten Zeitraum sind keine Daten verfügbar.")
            st.stop()

    except Exception:
        st.warning("Für den gewählten Zeitraum sind keine Daten verfügbar.")
        st.stop()

    # ---- Plot ----
    t = pd.to_datetime(df_combined["timestamp"] if "timestamp" in df_combined else df_bal["timestamp"])
    traces = []
    traces += _build_stacked_traces_by_order(t, df_combined, df_bal)
    traces += _line_traces_from_df(df_agg, yaxis="y2")

    layout = go.Layout(
        xaxis=dict(type="date"),
        yaxis=dict(title="Leistung [MW]"),
        yaxis2=dict(
            title="Stromverbrauch",
            overlaying="y",
            side="right",
            matches="y"       # identische Skala/Nullpunkt wie linke Achse
        ),
        hovermode="x unified",
        legend=dict(orientation="h", y=-0.2),
        title=f"{start:%d.%m.%Y} bis {(end - dt.timedelta(days=1)):%d.%m.%Y}",
        margin=dict(l=60, r=60, t=40, b=40)
    )

    fig = go.Figure(data=traces, layout=layout)
    st.plotly_chart(fig, use_container_width=True)

    # ---- Quellenangabe ----
    st.markdown(
        "<div style='text-align:center; font-size:0.8em; color:gray;'>"
        "Quelle: <a href='https://energy-charts.info' target='_blank' "
        "style='color:gray; text-decoration:none;'>energy-charts.info (Fraunhofer ISE)</a>"
        "</div>",
        unsafe_allow_html=True
    )
else:
    st.info("Bitte Zeitraum wählen und **Plot aktualisieren** klicken.")
