# ec_transform.py
# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Tuple, Dict, List
import pandas as pd

COL_TIMESTAMP = "timestamp"

# --- Detaillierte Erzeuger (Original-Spalten aus df_raw) ---
ERZEUGER_COLS = [
    "Hydro Run-of-River",
    "Biomass",
    "Fossil brown coal / lignite",
    "Fossil hard coal",
    "Fossil oil",
    "Fossil coal-derived gas",
    "Fossil gas",
    "Geothermal",
    "Hydro water reservoir",
    "Hydro pumped storage",
    "Others",
    "Waste",
    "Wind offshore",
    "Wind onshore",
    "Solar",
]

# --- Zusammenfassungs-Mapping -> df_erzeuger_combined (deutsche Labels) ---
COMBINED_MAP: Dict[str, List[str]] = {
    "Wasserkraft": ["Hydro Run-of-River", "Hydro water reservoir"],
    "Biomasse": ["Biomass"],
    "Kohle und Öl": ["Fossil brown coal / lignite", "Fossil hard coal", "Fossil oil"],
    "Gas": ["Fossil coal-derived gas", "Fossil gas"],
    "Andere": ["Waste", "Others", "Geothermal"],
    "Wind": ["Wind onshore", "Wind offshore"],
    "Photovoltaik": ["Solar"],
}

# --- Ausgleich: Original->Deutsch ---
AUSGLEICH_COLS_ORIG = [
    "Hydro pumped storage",
    "Hydro pumped storage consumption",
    "Cross border electricity trading",
]
AUSGLEICH_RENAME = {
    "Hydro pumped storage": "Pumpspeicher (Stromerzeugung)",
    "Hydro pumped storage consumption": "Pumpspeicher (Stromverbrauch)",
    "Cross border electricity trading": "Grenzüberschreitender Stromhandel",
}

# --- Aggregierte Kennzahlen: nur "Load" und direkt umbenennen zu "Stromverbrauch" ---
AGGREGATED_COLS_ORIG = ["Load"]  # "Residual load" wird NICHT mehr berücksichtigt
AGGREGATED_RENAME = {"Load": "Stromverbrauch"}


def _ensure_subset(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    out = pd.DataFrame()
    out[COL_TIMESTAMP] = pd.to_datetime(df[COL_TIMESTAMP])
    for c in cols:
        out[c] = df[c] if c in df.columns else pd.NA
    return out


def _build_combined(df_erzeuger: pd.DataFrame) -> pd.DataFrame:
    out = pd.DataFrame()
    out[COL_TIMESTAMP] = pd.to_datetime(df_erzeuger[COL_TIMESTAMP])
    for target, sources in COMBINED_MAP.items():
        vals = None
        for src in sources:
            s = (pd.to_numeric(df_erzeuger.get(src), errors="coerce")
                 if src in df_erzeuger.columns else pd.Series(pd.NA, index=df_erzeuger.index))
            s = s.fillna(0.0)
            vals = s if vals is None else (vals + s)
        out[target] = vals if vals is not None else 0.0
    return out


def transform_df(df_raw: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    if COL_TIMESTAMP not in df_raw.columns:
        raise ValueError("Erwarte eine Spalte 'timestamp' in df_raw.")

    # Detaillierte Erzeuger
    df_erzeuger = _ensure_subset(df_raw, ERZEUGER_COLS)

    # Zusammengefasste Erzeuger
    df_erzeuger_combined = _build_combined(df_erzeuger)

    # Ausgleich (Original-Spalten) -> Umbenennen ins Deutsche
    df_ausgleich_orig = _ensure_subset(df_raw, AUSGLEICH_COLS_ORIG)
    df_ausgleich = df_ausgleich_orig.rename(columns=AUSGLEICH_RENAME)

    # Aggregiert: nur "Load" -> direkt umbenannt zu "Stromverbrauch"
    df_aggregated_orig = _ensure_subset(df_raw, AGGREGATED_COLS_ORIG)
    df_aggregated = df_aggregated_orig.rename(columns=AGGREGATED_RENAME)

    return df_erzeuger, df_erzeuger_combined, df_ausgleich, df_aggregated
