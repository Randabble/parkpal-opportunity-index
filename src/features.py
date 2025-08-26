from __future__ import annotations
import pandas as pd
import geopandas as gpd
import numpy as np
from shapely.geometry import Point
from shapely.ops import nearest_points

EPSG_LOCAL = 26910  # UTM zone 10N, meters for Seattle region

def to_local(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    if gdf.crs is None:
        gdf = gdf.set_crs(4326)
    return gdf.to_crs(EPSG_LOCAL)

def event_intensity_by_area(areas: gpd.GeoDataFrame, venues: pd.DataFrame, decay_m: float = 300.0) -> pd.Series:
    """
    Sum attendance-weighted distance decay from all venues to each area centroid.
    intensity = sum(attendance * exp(-distance/decay_m))
    """
    vg = gpd.GeoDataFrame(venues.copy(), geometry=gpd.points_from_xy(venues["lon"], venues["lat"]), crs=4326)
    areas_l = to_local(areas)
    vg_l = to_local(vg)
    centroids = areas_l.centroid

    intensities = []
    for c in centroids:
        dists = vg_l.distance(c)  # meters in local CRS
        att = vg_l.get("attendance", pd.Series(np.ones(len(vg_l))))
        val = np.sum(att.values * np.exp(-dists.values / decay_m))
        intensities.append(val)
    return pd.Series(intensities, index=areas.index, name="event_intensity")

def private_supply_by_area(areas: gpd.GeoDataFrame, parcels: gpd.GeoDataFrame) -> pd.Series:
    """
    Sum driveway_area_m2 of parcels within each area polygon.
    """
    areas_l = to_local(areas)
    parcels_l = to_local(parcels)
    joined = gpd.sjoin(parcels_l, areas_l, how="inner", predicate="intersects")
    grp = joined.groupby(areas_l.index.name or "index_right")["driveway_area_m2"].sum()
    # Ensure full index
    supply = pd.Series(0.0, index=areas.index)
    supply.loc[grp.index] = grp.values
    supply.name = "private_supply"
    return supply

def public_supply_by_area(areas: gpd.GeoDataFrame, garages_df: pd.DataFrame, radius_m: float = 600.0) -> pd.Series:
    """
    Sum garage capacity within radius of the area centroid.
    """
    garages = gpd.GeoDataFrame(garages_df.copy(), geometry=gpd.points_from_xy(garages_df["lon"], garages_df["lat"]), crs=4326)
    garages_l = to_local(garages)
    areas_l = to_local(areas)
    centroids = areas_l.centroid

    caps = []
    for c in centroids:
        mask = garages_l.distance(c) <= radius_m
        cap_sum = garages_l.loc[mask, "capacity"].sum() if "capacity" in garages_l else 0.0
        caps.append(float(cap_sum))
    return pd.Series(caps, index=areas.index, name="public_supply")

def access_metrics(areas: gpd.GeoDataFrame, venues_df: pd.DataFrame, radius_m: float = 600.0) -> pd.DataFrame:
    """
    Compute:
      - poi_density_600m: venues within 600 m of area centroid
      - avg_walk_distance_to_poi_m: distance to nearest venue
    """
    venues = gpd.GeoDataFrame(venues_df.copy(), geometry=gpd.points_from_xy(venues_df["lon"], venues_df["lat"]), crs=4326)
    venues_l = to_local(venues)
    areas_l = to_local(areas)
    centroids = areas_l.centroid

    counts, nearest_dist = [], []
    for c in centroids:
        d = venues_l.distance(c)
        counts.append(int((d <= radius_m).sum()))
        nearest_dist.append(float(d.min()) if len(d) else 0.0)

    return pd.DataFrame({
        "poi_density_600m": counts,
        "avg_walk_distance_to_poi_m": nearest_dist
    }, index=areas.index)

def traffic_aggregate(traffic_df: pd.DataFrame) -> pd.DataFrame:
    """
    traffic_df: columns [area_id, hour, traffic_index]
    Returns area-level mean and peak.
    """
    agg = (traffic_df
           .groupby("area_id")["traffic_index"]
           .agg(traffic_index_mean="mean", traffic_index_peak="max"))
    return agg.reset_index()

def assemble_features(
    areas: gpd.GeoDataFrame,
    venues_df: pd.DataFrame,
    parcels: gpd.GeoDataFrame,
    garages_df: pd.DataFrame,
    traffic_df: pd.DataFrame
) -> pd.DataFrame:
    """
    Build a feature table keyed by area_id. Requires 'area_id' in areas.
    Also expects 'employment_density' already present in areas (synthetic proxy for MVP).
    """
    if "area_id" not in areas.columns:
        raise KeyError("areas must include 'area_id' column")

    # Base frame
    base = pd.DataFrame({"area_id": areas["area_id"].values}).set_index(areas.index)

    # Demand pieces
    base["event_intensity"] = event_intensity_by_area(areas, venues_df)
    traf = traffic_aggregate(traffic_df)
    base = base.merge(traf.set_index(areas["area_id"].values), left_on="area_id", right_index=True, how="left")
    # employment density from areas attributes
    base["employment_density"] = areas["employment_density"].values

    # Supply
    base["private_supply"] = private_supply_by_area(areas, parcels)
    base["public_supply"] = public_supply_by_area(areas, garages_df)

    # Access
    acc = access_metrics(areas, venues_df)
    base = pd.concat([base, acc], axis=1)

    # Economic
    # median garage rate within 600 m of centroid
    garages = gpd.GeoDataFrame(garages_df.copy(), geometry=gpd.points_from_xy(garages_df["lon"], garages_df["lat"]), crs=4326)
    garages_l = to_local(garages)
    centroids = to_local(areas).centroid
    rates = []
    for c in centroids:
        d = garages_l.distance(c)
        within = garages_l.loc[d <= 600.0, "hourly_rate"]
        rates.append(float(within.median()) if len(within) else float(garages_df["hourly_rate"].median()))
    base["garage_rate_median"] = rates

    # Final index on area_id for easy join
    base = base.set_index("area_id", drop=False)
    return base
