from __future__ import annotations
import pandas as pd
import geopandas as gpd
import folium
from folium.features import GeoJsonTooltip
from .features import to_local

def make_folium_map(areas: gpd.GeoDataFrame, scored: pd.DataFrame, venues: pd.DataFrame, garages: pd.DataFrame,
                    score_col: str = "Opportunity", outfile: str = "maps/opportunities.html") -> None:
    g_areas = areas.merge(scored[["area_id", score_col]], on="area_id", how="left")
    g_areas = g_areas.to_crs(4326)

    center = [g_areas.geometry.centroid.y.mean(), g_areas.geometry.centroid.x.mean()]
    m = folium.Map(location=center, zoom_start=13, control_scale=True)

    # Choropleth by score
    gj = folium.GeoJson(
        g_areas,
        name="Opportunity",
        style_function=lambda f: {
            "fillColor": _color_scale(f["properties"].get(score_col, 0.0)),
            "color": "black",
            "weight": 1,
            "fillOpacity": 0.6,
        },
        tooltip=GeoJsonTooltip(
            fields=["area_id", score_col],
            aliases=["Area", "Opportunity"],
            localize=True
        )
    )
    gj.add_to(m)

    # Venues
    for _, r in venues.iterrows():
        folium.CircleMarker(
            location=[r["lat"], r["lon"]],
            radius=5,
            popup=f'{r["name"]} ({r["type"]})',
            fill=True
        ).add_to(m)

    # Garages
    for _, r in garages.iterrows():
        folium.Marker(
            location=[r["lat"], r["lon"]],
            tooltip=f'{r["name"]}: ${r["hourly_rate"]}/hr',
            icon=folium.Icon(color="blue", icon="parking", prefix="fa")
        ).add_to(m)

    folium.LayerControl().add_to(m)
    m.save(outfile)
    print(f"Saved map to {outfile}")

def _color_scale(x: float) -> str:
    # Simple green-red scale
    x = 0.0 if x is None else max(0.0, min(1.0, float(x)))
    r = int(255 * (1 - x))
    g = int(255 * x)
    return f"#{r:02x}{g:02x}55"

def build_map_cli():
    import pandas as pd
    import geopandas as gpd
    from .features import assemble_features
    from .scoring import compute_composites, compute_opportunity

    areas = gpd.read_file("data/boundaries.geojson")
    parcels = gpd.read_file("data/parcels_sample.geojson")
    venues = pd.read_csv("data/venues.csv")
    garages = pd.read_csv("data/parking_prices.csv")
    traffic = pd.read_csv("data/traffic.csv")

    feats = assemble_features(areas, venues, parcels, garages, traffic)
    comps = compute_composites(feats)
    scored = compute_opportunity(comps)
    make_folium_map(areas, scored.reset_index(), venues, garages, "Opportunity", "maps/opportunities.html")
