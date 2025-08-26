from __future__ import annotations
import pandas as pd
import numpy as np
from typing import Dict, List

def normalize_series(s: pd.Series) -> pd.Series:
    """
    Min-max normalize to [0,1]. If constant, return 0.5.
    """
    s = s.astype(float)
    minv, maxv = s.min(), s.max()
    if np.isclose(maxv, minv):
        return pd.Series(0.5, index=s.index)
    return (s - minv) / (maxv - minv)

def weighted_sum(df: pd.DataFrame, cols: List[str], weights: Dict[str, float]) -> pd.Series:
    """
    Compute sum_i w_i * df[col_i]. Missing cols get weight 0.
    Assumes columns are already normalized as needed.
    """
    total = 0.0
    for c in cols:
        w = weights.get(c, 0.0)
        if c in df:
            total = total + w * df[c].astype(float)
    return pd.Series(total, index=df.index)

def compute_composites(features: pd.DataFrame) -> pd.DataFrame:
    """
    Build normalized component scores from raw feature columns.
    Expects the following raw columns to exist (some are placeholders):
      - traffic_index_mean, event_intensity, employment_density,
        public_supply, private_supply, poi_density_600m,
        avg_walk_distance_to_poi_m, garage_rate_median
    """
    f = features.copy()

    # DemandScore: high traffic, high events, high employment, low public supply
    f["traffic_n"] = normalize_series(f["traffic_index_mean"])
    f["events_n"] = normalize_series(f["event_intensity"])
    f["jobs_n"] = normalize_series(f["employment_density"])
    f["public_supply_n"] = normalize_series(f["public_supply"])  # good is low
    f["DemandScore"] = normalize_series(
        0.35 * f["traffic_n"] +
        0.35 * f["events_n"] +
        0.20 * f["jobs_n"] +
        0.10 * (1 - f["public_supply_n"])
    )

    # SupplyScore: private supply only
    f["private_supply_n"] = normalize_series(f["private_supply"])
    f["SupplyScore"] = f["private_supply_n"]

    # AccessScore: more POIs nearby and shorter walk distance
    f["poi_n"] = normalize_series(f["poi_density_600m"])
    f["walk_n"] = normalize_series(f["avg_walk_distance_to_poi_m"])
    f["AccessScore"] = normalize_series(0.6 * f["poi_n"] + 0.4 * (1 - f["walk_n"]))

    # EconomicScore: higher nearby garage rates → better price headroom
    f["garage_rate_n"] = normalize_series(f["garage_rate_median"])
    f["EconomicScore"] = f["garage_rate_n"]

    return f

def compute_opportunity(
    features: pd.DataFrame,
    weights: Dict[str, float] | None = None
) -> pd.DataFrame:
    """
    Combine component scores into an Opportunity score.
    Default weights:
      Demand 0.40, Supply 0.30, Access 0.20, Economic 0.10
    """
    if weights is None:
        weights = {"DemandScore": 0.40, "SupplyScore": 0.30, "AccessScore": 0.20, "EconomicScore": 0.10}

    f = features.copy()
    for key in ["DemandScore", "SupplyScore", "AccessScore", "EconomicScore"]:
        if key not in f:
            raise KeyError(f"Missing component score: {key}")

    f["Opportunity"] = (
        weights.get("DemandScore", 0) * f["DemandScore"] +
        weights.get("SupplyScore", 0) * f["SupplyScore"] +
        weights.get("AccessScore", 0) * f["AccessScore"] +
        weights.get("EconomicScore", 0) * f["EconomicScore"]
    )
    return f

def rank_areas(scored: pd.DataFrame, score_col: str = "Opportunity", n: int = 10) -> pd.DataFrame:
    """
    Return top-n areas sorted by score descending.
    """
    cols = [c for c in scored.columns if c not in []]
    out = scored.sort_values(score_col, ascending=False).head(n).copy()
    return out

def preset_weights(kind: str = "balanced") -> Dict[str, float]:
    """
    Presets:
      - "balanced": baseline weights
      - "office_commute": emphasize jobs and traffic, reduce events and price
    """
    if kind == "balanced":
        return {"DemandScore": 0.40, "SupplyScore": 0.30, "AccessScore": 0.20, "EconomicScore": 0.10}
    if kind == "office_commute":
        return {"DemandScore": 0.50, "SupplyScore": 0.25, "AccessScore": 0.20, "EconomicScore": 0.05}
    return {"DemandScore": 0.40, "SupplyScore": 0.30, "AccessScore": 0.20, "EconomicScore": 0.10}

def suggest_price_stub(
    base_rate: float,
    event_attendance: float | None,
    garage_price: float | None,
    alpha: float = 0.25,
    beta: float = 0.50
) -> float:
    """
    Placeholder for a pricing recommender.
    SuggestedPrice = base_rate + alpha*(event_attendance/1000) + beta*max(garage_price - base_rate, 0)
    """
    ea = 0.0 if event_attendance is None else event_attendance
    gp = base_rate if garage_price is None else garage_price
    return float(base_rate + alpha * (ea / 1000.0) + beta * max(gp - base_rate, 0))
