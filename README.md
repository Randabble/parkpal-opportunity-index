# ParkPal Opportunity Index (Seattle MVP)

**Goal:** rank micro-areas in Seattle where a peer-to-peer driveway parking app will succeed first.

**Inputs (synthetic for MVP):**
- Demand: traffic index by area and hour, event venues with attendance, simple employment density proxy
- Supply: sample residential parcels with driveway area
- Access: distance to nearby points of interest, density within 600 m
- Economic: local garage price benchmarks

**Outputs:**
1) A ranked table of areas with an **Opportunity** score  
2) An interactive Folium map (`maps/opportunities.html`)  
3) A tiny time series demo that forecasts short-term demand and shows how to fold it into the score

---

## Why this fits transportation systems and ITS
This MVP mirrors how transportation analytics blends network demand, land use, and operational context. We build a multi-criteria index for **site selection** (like facility location in OR), add a **demand forecast** with SARIMA, and visualize results as usable decision support. This is aligned with work in urban traffic operations, mobile sensing, and intelligent transportation systems, in the spirit of research themes common to Dr. Xuegang "Jeff" Ban's group.

---

## Quickstart

### Option A: Conda (recommended for GeoPandas)
```bash
conda env create -f environment.yml
conda activate parkpal
python -m pip install -r requirements.txt  # pins light extras
pytest
jupyter lab
```

### Option B: pip only (works on many setups)
```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
python -m pip install -r requirements.txt
pytest
jupyter lab
```

Open and run notebooks in order:

1. `01_data_prep.ipynb` – load synthetic data, set CRS, spatial joins
2. `02_geospatial_metrics.ipynb` – build features per area
3. `03_time_series.ipynb` – build hourly demand, fit SARIMA, make a 1-week forecast
4. `04_opportunity_index.ipynb` – normalize, weight, score, rank, export CSV and map

**Artifacts:**
- `maps/opportunities.html`
- `outputs/top_areas.csv`

---

## Method overview

### Per-area features

**Demand**
- `traffic_index`: mean and peak from hourly series
- `event_intensity`: sum over venues with distance decay
- `employment_density`: simple proxy from boundaries attributes
- `violations_rate`: placeholder field for future Seattle Open Data

**Supply**
- `private_supply`: sum of parcel `driveway_area_m2` within area
- `public_supply`: garages within 600 m with capacity, for demand gap use

**Access**
- `poi_density_600m`: count of venues within 600 m
- `avg_walk_distance_to_poi_m`: centroid to nearest venue

**Economic**
- `garage_rate_median`: median hourly rate near the area

### Composites (min-max normalized to [0,1])

- **DemandScore** = f(traffic_index_mean, event_intensity, employment_density, -public_supply)
- **SupplyScore** = f(private_supply)
- **AccessScore** = f(poi_density_600m, -avg_walk_distance_to_poi_m)
- **EconomicScore** = f(garage_rate_median)

### Opportunity (baseline weights)
```
Opportunity = 0.40*DemandScore + 0.30*SupplyScore + 0.20*AccessScore + 0.10*EconomicScore
```

Weights are configurable in `src/scoring.py` through function args. A preset shifts weight toward office commute vs event demand.

---

## Time series

Small synthetic hourly demand series for a few areas with weekday peaks and event spikes
- SARIMA via statsmodels
- Optionally blend near-term forecast peak into DemandScore

---

## Design choices

- **CRS**: read in WGS84, project to a local projected CRS for distances (UTM zone 10N, EPSG:26910). Distances and buffers are in meters and rely on this projection.
- **Synthetic data**: tiny files so everything runs offline in minutes. Functions are structured to swap in real sources later (Seattle Open Data, LEHD, GTFS, events APIs).
- **Clean structure**: most logic in `src/`. Notebooks stay short and readable.

---

## How to swap in real data later

- **Boundaries**: neighborhood or custom grid from Seattle GIS → replace `data/boundaries.geojson`
- **Parcels**: King County Assessor parcels with driveway proxy features → replace `data/parcels_sample.geojson`
- **Events**: Ticketmaster/Eventbrite APIs or venue calendars → replace `data/venues.csv`
- **Traffic**: INRIX or TomTom or Google traffic aggregates → replace `data/traffic.csv`
- **Prices**: Parkopedia or SpotHero samples → replace `data/parking_prices.csv`

---

## Professor-ready description

We developed a small, reproducible MVP that scores Seattle micro-areas for a peer-to-peer driveway parking pilot. The index blends demand, supply, access, and economic signals using standard GIS methods: spatial joins, distance decay, and buffers in a projected CRS. A light SARIMA model produces a short-term demand forecast that can feed the score. Everything runs offline on synthetic data, but each step is designed to swap in real city datasets. The result is a transparent, reproducible site selection tool that reflects multi-criteria decision analysis and demand forecasting common in transportation systems and ITS.

---

## License

MIT. See [LICENSE](LICENSE).
