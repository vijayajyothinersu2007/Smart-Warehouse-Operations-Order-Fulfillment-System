# WarehouseIQ 🚀
### Smart Warehouse Operations & Autonomous Decision Engine (Phase 1 MVP)

WarehouseIQ is an intelligent warehouse operations and order fulfillment platform designed to replace passive transactional WMS systems with an **Explainable Autonomous Decision Engine**.

---

## 🌟 Key Features in Phase 1 MVP

1. **Autonomous Stock Contention Resolver**:
   - Intelligently evaluates trade-offs when stock demand exceeds on-hand units (e.g. Urgent VIP Order vs Normal Order).
   - Generates an **Explainable Decision Card** with mathematical factor weighting, confidence scores, and rejected alternatives.
2. **Dynamic Order Prioritization**:
   - Multi-factor algorithm scoring orders ($0-100$) based on SLA countdown timers, customer tiers, and value, with auto-escalation for deadlines under 2 hours.
3. **End-to-End Fulfillment Lifecycle**:
   - Smooth gate-by-gate pipeline: `Order Ingestion` $\rightarrow$ `Stock Allocation` $\rightarrow$ `Floor Picking` $\rightarrow$ `Packing` $\rightarrow$ `QC Scale Verification` $\rightarrow$ `Carrier Dispatch` (with automatic on-hand inventory depletion).
4. **Exception & Discrepancy Triage**:
   - Automated handling for damaged and missing stock: auto-quarantine, alternative bin discovery, real-time picker rerouting, and cycle-count auditing.
5. **Real-time Industrial SaaS Dashboard**:
   - High-contrast slate UI with responsive KPI metrics, live fulfillment kanban board, interactive Chart.js analytics, and explainable decision drawers.

---

## ⚡ Quick Start: How to Run Locally

### Prerequisites
- Python 3.10+ (Flask is included in requirements)

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run the Application
```bash
python run.py
```
Open your browser and navigate to: **`http://127.0.0.1:5000`**

*(The database will automatically initialize and seed with the mandatory stock contention scenario and realistic records on first run).*

---

## 🧪 Running Automated Tests

Run the full automated test suite covering priority calculations, stock contention resolution, exception triage, and the end-to-end fulfillment flow:

```bash
python tests/test_contention_scenario.py
python tests/test_decision_engine.py
python tests/test_order_workflow.py
```

Or run all tests with `pytest`:
```bash
pytest tests/ -v
```

---

## 🎯 Hackathon Demo Walkthrough (Stock Contention Scenario)

1. Open **Command Center** (`http://127.0.0.1:5000`).
2. Notice the top banner: **"Stock Contention Scenario (Order A vs Order B)"**.
   - **Order A (`ORD-URGENT-001`)**: VIP / Urgent Tier, requires **10 units** of `SKU-DRONE-4K` (SLA in 1.5 hrs).
   - **Order B (`ORD-NORM-002`)**: Normal Tier, requires **5 units** of `SKU-DRONE-4K` (SLA in 18 hrs).
   - **Available On-Hand Stock**: **7 units** in `BIN-A-01-01-1`.
3. Click **"🧪 Run Contention Demo"** or **"⚡ Auto-Allocate"**.
4. The system executes the Decision Engine:
   - **Order A** is allocated all **7 units** (`ALLOCATED_PARTIAL 7/10`) to safeguard the VIP SLA.
   - **Order B** is placed in `BACKORDERED (0/5)`.
   - The **Explainable Decision Card** modal automatically opens, displaying:
     - Mathematical Factor breakdown (Scores: 92.5 vs 45.0).
     - Recommended next steps (partial dispatch wave + emergency PO for 8 units).
     - Alternatives rejected (e.g. why an equal split of 4 vs 3 was rejected).
5. Switch to **Orders & Allocation** or **Fulfillment Pipeline** to advance Order A through `Picking` $\rightarrow$ `Packing` $\rightarrow$ `QC` $\rightarrow$ `Dispatch`.
6. Notice that upon Dispatch, physical stock in **Inventory & Bins** is automatically deducted.

---

## 📂 Project Architecture

```
smart-warehouse/
├── backend/
│   ├── app.py                      # Flask factory & blueprint registration
│   ├── config.py                   # Configuration & algorithm weights
│   ├── database/
│   │   ├── db.py                   # SQLite connection helpers
│   │   ├── schema.sql              # Clean relational DDL (10 tables)
│   │   └── seeder.py               # Contention scenario & realistic seeder
│   ├── services/
│   │   ├── decision_engine/
│   │   │   ├── priority_scorer.py  # SLA countdown & priority scoring
│   │   │   ├── allocation_engine.py# Contention resolver & explainability
│   │   │   └── exception_triage.py # Damaged/missing item auto-triage
│   │   ├── inventory_service.py    # Stock tracking & bin adjustments
│   │   ├── order_service.py        # Order creation & queue lifecycle
│   │   ├── fulfillment_service.py  # Picking, packing, QC, dispatch
│   │   └── analytics_service.py    # KPIs & Chart.js metric feeds
│   └── routes/                     # REST API blueprints
├── frontend/
│   ├── templates/
│   │   └── index.html              # Responsive SPA shell
│   └── static/
│       ├── css/                    # Industrial SaaS styling & components
│       └── js/                     # Modular view controllers & Chart.js
├── tests/                          # Complete automated test suite
├── data/
│   └── warehouse.db                # SQLite database
├── requirements.txt
└── run.py
```

---

## 🔮 Roadmap for Phase 2

- **Advanced 2D Warehouse Spatial Pick Routing**: Interactive Canvas rendering of S-Shape serpentine traversal and Manhattan distance calculations.
- **Predictive EOQ & Dynamic Safety Stock**: Automated Purchase Order generation based on lead times and demand variability.
- **Station Bottleneck Heatmap**: Real-time queue-to-throughput ratio tracking and automated picker load-balancing.
