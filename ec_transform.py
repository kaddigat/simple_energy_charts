# ec_transform.py
# -*- coding: utf-8 -*-
"""
Hard-coded Transformation:
Splittet df_raw in drei DataFrames mit Zeitstempel:
- df_erzeuger    (Generators, gestapelt im Plot)
- df_ausgleich   (Balancing/Consumption, gestapelt im Plot)
- df_aggregated  (Aggregierte Kennzahlen, als Linien auf zweiter Achse)
"""

from __future__ import annotations
from typing import Tuple
import pandas as pd

COL_TIMESTAMP = "timestamp"

# ---- Hard-coded Spaltenzuordnung (genau wie von dir gefordert) ----
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

AUSGLEICH_COLS = [
    "Hydro pumped storage consumption",
    "Cross border electricity trading",
]

AGGREGATED_COLS = [
    "Load",
    "Residual load",
]


def _ensure_subset(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    out = pd.DataFrame()
    out[COL_TIMESTAMP] = pd.to_datetime(df[COL_TIMESTAMP])
    for c in cols:
        out[c] = df[c] if c in df.columns else pd.NA
    return out


def transform_df(df_raw: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    if COL_TIMESTAMP not in df_raw.columns:
        raise ValueError("Erwarte eine Spalte 'timestamp' in df_raw.")

    df_erzeuger   = _ensure_subset(df_raw, ERZEUGER_COLS)
    df_ausgleich  = _ensure_subset(df_raw, AUSGLEICH_COLS)
    df_aggregated = _ensure_subset(df_raw, AGGREGATED_COLS)
    return df_erzeuger, df_ausgleich, df_aggregated
