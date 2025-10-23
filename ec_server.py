# ec_server.py
# -*- coding: utf-8 -*-
"""
Unsere eigene FastAPI-Schnittstelle für Power-Daten.
Ersetzt alte Plot-Funktion durch eine JSON-API mit flexiblem Zeitraum.
"""
from __future__ import annotations
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import datetime as dt

from ec_fetch import fetch_public_power, last_full_week
from ec_transform import transform_df

app = FastAPI(title="Energy Charts Project API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # für lokale Tests ok; in Produktion einschränken!
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/power")
def get_power(
    start: str = Query(default=None, description="YYYY-MM-DD (inklusive)"),
    end: str = Query(default=None, description="YYYY-MM-DD (exklusive)"),
):
    """
    Liefert Zeitreihen als JSON:
    - timestamps
    - erzeugerCombined
    - ausgleich
    - aggregated
    Zeitraum [start, end). Fehlt einer, wird letzte volle Woche verwendet.
    """
    try:
        if not start or not end:
            s, e = last_full_week()
        else:
            s, e = dt.date.fromisoformat(start), dt.date.fromisoformat(end)
        if e <= s:
            raise ValueError("end muss nach start liegen (exklusiv).")
    except Exception as ex:
        raise HTTPException(status_code=400, detail=f"Ungültiger Zeitraum: {ex}")

    try:
        df_raw = fetch_public_power(s, e)
        _, df_combined, df_bal, df_agg = transform_df(df_raw)
    except Exception as ex:
        raise HTTPException(status_code=500, detail=f"Datenabruf/Transformation fehlgeschlagen: {ex}")

    return {
        "timestamps": df_combined["timestamp"].astype(str).tolist(),
        "erzeugerCombined": {c: df_combined[c].fillna(0).astype(float).tolist() for c in df_combined.columns if c != "timestamp"},
        "ausgleich": {c: df_bal[c].fillna(0).astype(float).tolist() for c in df_bal.columns if c != "timestamp"},
        "aggregated": {c: df_agg[c].fillna(0).astype(float).tolist() for c in df_agg.columns if c != "timestamp"},
        "start": str(s),
        "end": str(e),
    }
