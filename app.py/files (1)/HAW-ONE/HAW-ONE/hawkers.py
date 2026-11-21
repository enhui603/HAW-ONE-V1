"""Hawker centre data (cleaning dates, other works, location, nearest MRT)."""
import os
from datetime import timedelta

import pandas as pd
import streamlit as st

import store

HERE = os.path.dirname(os.path.abspath(__file__))
HAWKER_FILE = os.path.join(HERE, "hawker_centres_final.csv")
QUARTERS = ["q1", "q2", "q3", "q4"]


@st.cache_data
def load_hawkers():
    if not os.path.exists(HAWKER_FILE):
        return None
    df = pd.read_csv(HAWKER_FILE)
    for col in [c for c in df.columns if c.endswith("date")]:
        df[col] = pd.to_datetime(df[col], format="%d/%m/%y", errors="coerce")
    df["region"] = [store.region_of(a, b) for a, b in zip(df["latitude_hc"], df["longitude_hc"])]
    df["stalls"] = df["no_of_food_stalls"] + df["no_of_market_stalls"]
    df["letter"] = df["name"].str.strip().str[0].str.upper()
    return df


def centre_names():
    df = load_hawkers()
    return sorted(df["name"].tolist()) if df is not None else []


def window(row, q):
    """(start, end, days) for a quarter; start/end are None when still to be confirmed."""
    s, e = row[f"{q}_cleaningstartdate"], row[f"{q}_cleaningenddate"]
    if pd.isna(s) or pd.isna(e):
        return None, None, None
    d = row[f"{q}_days"]
    return s, e, (int(d) if not pd.isna(d) else None)


def status_of(start, end, today):
    if start is None or end is None:
        return "tbc"
    if end.date() < today:
        return "done"
    if start.date() <= today <= end.date():
        return "now"
    return "upcoming"


def upcoming_cleaning(df, today, days=30):
    """One row per cleaning window that is happening now or starts within `days` days."""
    rows = []
    limit = today + timedelta(days=days)
    for idx, r in df.iterrows():
        for q in QUARTERS:
            s, e, d = window(r, q)
            if s is None:
                continue
            if e.date() >= today and s.date() <= limit:
                rows.append({"idx": idx, "name": r["name"], "region": r["region"], "letter": r["letter"],
                             "start": s, "end": e, "days": d, "address": r["address_myenv"]})
    cols = ["idx", "name", "region", "letter", "start", "end", "days", "address"]
    out = pd.DataFrame(rows, columns=cols)
    return out.sort_values(["name", "start"]).reset_index(drop=True)


def next_cleaning(row, today):
    best = None
    for q in QUARTERS:
        s, e, _ = window(row, q)
        if s is not None and e.date() >= today and (best is None or s < best):
            best = s
    return best


def long_closures(df):
    rows = df[df["other_works_in_2026"] | df["closed_all_2026"]].copy()
    return rows.sort_values("other_works_startdate").reset_index(drop=True)
