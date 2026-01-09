# Argentina Ideal - GCP Analytics Platform (GCS → BigQuery → Looker Studio)

End-to-end analytics platform on Google Cloud: **Cloud Storage landing → BigQuery (RAW → DWH → DM) → Looker Studio dashboards**.

## Links
- Dashboard: https://lookerstudio.google.com/reporting/d728688f-423a-4bc6-9f3d-d7757f9aba7c  
- Data Flow Diagram: https://drive.google.com/file/d/1-dLYjk9OU9Zshf4LEALqH2iBkizTTvw-/view?usp=sharing  
- DWH Architecture: https://drive.google.com/file/d/11QHJZwm-VQQRPOIGqwyJW54QlExWjciQ/view?usp=sharing  

---

## Context
5 distributors with fragmented systems (sales, stock, customers, debt). Objective: a **single source of truth** for **Executive, Finance, Marketing, and Logistics** teams.

---

## Architecture

### 1) Cloud Storage Data Lake (daily landing)
Daily structured files land in a bucket under a clear contract:
- `data/distribuidor_*/maestro/` → `Maestro_*.csv`
- `data/distribuidor_*/ventas/` → `Venta_Clientes_*.csv`
- `data/distribuidor_*/stock/` → `StockPeriodo_*.csv`

This layout is auditable (who/what/when) and scalable (add distributors or new file types without redesign).

---

### 2) BigQuery Medallion (RAW → DWH → DM)

#### RAW (Bronze) - staging “as received”
Script: `src/ingestion/load_raw_all.py`

- Reads all objects under `data/` in the bucket
- Filters by expected file patterns (maestro/ventas/stock)
- Loads into BigQuery tables (full refresh each run):
  - `raw.Maestro`
  - `raw.Ventas`
  - `raw.Stock`

Why: RAW is the base layer to rebuild everything reliably.

---

#### DWH (Silver) - dimensional star schema
Script: `src/modeling/build_dwh.py`

Creates/replaces a star schema optimized for analytics:

**Dimensions**
- `dwh.dim_sucursal` (from Maestro)
- `dwh.dim_cliente` (from Maestro)
- `dwh.dim_producto` (from Stock)
- `dwh.dim_distribuidor` (from sucursales/distributor attributes)
- `dwh.dim_fecha` (from distinct dates in ventas + stock)

**Facts**
- `dwh.fact_ventas` (measures: units, revenue; joins to dims)
- `dwh.fact_stock` (measure: stock; joins to dims)

Why: the star schema enforces consistent metrics and makes BI slicing fast and clean.

---

#### DM (Gold) - business-ready marts
Script: `src/modeling/build_dm.py`

Curated tables designed for dashboards (minimal BI logic):

- `dm.finanzas`: customer-level view (debt exposure + geo/contact + distributor filters)
- `dm.logistica`: stock view by date/SKU/sucursal/distributor with geo context
- `dm.marketing`: weekly aggregated sales performance by product + geography + distributor

Why: marts map directly to stakeholder questions and keep the BI layer thin.

---

### 3) Looker Studio dashboards (single source of truth)
Looker Studio connects to `dm.*` as the only source:
- Executive dashboard → `dm.marketing` + `dm.logistica` + `dm.finanzas`
- Finance dashboard → `dm.finanzas`
- Logistics dashboard → `dm.logistica`
- Marketing dashboard → `dm.marketing`

Why: keep business logic centralized in BigQuery, not duplicated across charts.

---

## Prerequisites
- Python 3.10+
- A GCP project with:
  - BigQuery enabled
  - A GCS bucket containing the data/... landing structure
- Authentication (one of):
  - gcloud auth application-default login
  - Service account with GCS + BigQuery permissions

---

## Installation (venv)
1) Create a virtual environment:
- `python -m venv .venv`

2) Activate it:
- macOS/Linux: `source .venv/bin/activate`
- Windows (PowerShell): `.venv\Scripts\Activate.ps1`

3) Install dependencies:
- `python -m pip install --upgrade pip`
- `pip install -r requirements.txt`

---

## Configuration
Environment variables:
- PROJECT_ID - BigQuery project id
- BUCKET - GCS bucket name

Example:
    export PROJECT_ID="argentina-ideal-478612"
    export BUCKET="distribuidores_argentina"

---

## How to run the pipeline (in order)

1) Load RAW:
- `python -m src.ingestion.load_raw_all`

2) Build DWH:
- `python -m src.modeling.build_dwh`

3) Build Data Marts:
- `python -m src.modeling.build_dm`

Optional single entrypoint:
- `python -m src.pipeline`

---

## Key design choices
- **Idempotent rebuilds**: rerun = same end state (RAW refresh + `CREATE OR REPLACE` downstream).
- **Clear contracts per layer**: RAW = ingestion, DWH = modeling, DM = consumption.
- **Stakeholder-first KPIs**: Executive/Finance/Marketing/Logistics questions drove the mart design.
