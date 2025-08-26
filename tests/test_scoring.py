import pandas as pd
from src.scoring import normalize_series, weighted_sum, compute_opportunity

def test_normalize_series_basic():
    s = pd.Series([0, 5, 10])
    n = normalize_series(s)
    assert float(n.min()) == 0.0
    assert float(n.max()) == 1.0
    assert float(n.iloc[1]) == 0.5

def test_normalize_series_constant():
    s = pd.Series([7, 7, 7])
    n = normalize_series(s)
    assert (n == 0.5).all()

def test_weighted_sum():
    df = pd.DataFrame({"a":[0.0, 1.0], "b":[1.0, 0.0]})
    w = {"a":0.7, "b":0.3}
    out = weighted_sum(df, ["a","b"], w)
    assert list(out.round(2)) == [0.3, 0.7]

def test_compute_opportunity():
    df = pd.DataFrame({
        "DemandScore":[0.2,0.8],
        "SupplyScore":[0.2,0.8],
        "AccessScore":[0.2,0.8],
        "EconomicScore":[0.2,0.8]
    })
    scored = compute_opportunity(df)
    assert list(scored["Opportunity"].round(2)) == [0.2, 0.8]
