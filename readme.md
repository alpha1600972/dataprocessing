# 🛒 E-Commerce Data Architecture

End-to-end data pipeline using PostgreSQL as a unified system for data lake and data warehouse.

> ⚠️ **This project currently runs on Linux only.**

---

# 🚀 Overview

This project implements a complete data architecture pipeline for an e-commerce dataset (Olist), including:

- 📥 **Data ingestion** (raw data)
- 🧱 **Data lake** (multi-layer zones)
- 🏗️ **Data warehouse** (star schema)
- 📊 **Analytical queries & visualization**

The goal is to simulate a real-world data engineering workflow using a single database system.

---

# 🧠 Architecture

```
Source Data → Data Lake → Data Warehouse → Analytics
```

## Layers

| Layer | Description |
|-------|-------------|
| `source_data` | Raw ingestion of Olist dataset |
| `raw_zone` | Immutable raw data |
| `processed_zone` | Cleaned & normalized data |
| `curated_zone` | Business-ready datasets |
| Data Warehouse | Star schema (fact + dimensions), optimized for analytics |

---

# 🛠️ Tech Stack

| Category | Tools |
|----------|-------|
| Database | PostgreSQL |
| Processing | Python (pandas, SQLAlchemy), SQL |
| Visualization | matplotlib |
| Orchestration | Python script |
| Containerization | Docker |

---

# 📂 Project Structure

```
dataprocessing/
│
├── Data_list/                  # Source data (CSV files)
├── charts/                     # Generated visualizations (Matplotlib)
│
├── main.py                     # Pipeline orchestrator
├── load_olist.py               # Data ingestion
├── create_data_lake.py         # Raw + initial lake setup
├── request_constraint.py       # Indexes & constraints
├── create_processed_zone.py    # Data cleaning
├── create_curated_zone.py      # Business transformations
├── create_data_warehouse.py    # Star schema creation
├── analytical_queries.py       # Analytics queries
│
├── docker-compose.yml          # PostgreSQL container
├── .env.example                # Environment variables template
└── requirements.txt            # Python dependencies
```

---

# ⚙️ Pipeline Workflow

The pipeline is executed sequentially:

1. Load raw data into PostgreSQL
2. Create data lake structure
3. Apply constraints and indexing
4. Clean and transform data
5. Build curated datasets
6. Create data warehouse (star schema)
7. Run analytical queries

---

# ▶️ Getting Started

## Prerequisites

Before running the project, make sure you have the following installed on your **Linux** system:

- [Docker](https://docs.docker.com/engine/install/) & [Docker Compose](https://docs.docker.com/compose/install/)
- Python 3.8+

To verify Docker is correctly installed:

```bash
docker --version
docker compose version
```

## 1. Clone the repository

```bash
git clone https://github.com/alpha1600972/dataprocessin.git
cd ecommerce-data-architecture
```

## 2. Configure environment variables

Copy the `.env.example` file and rename it to `.env`, then fill in the required values:

```bash
cp .env.example .env
```

Open `.env` and update the variables according to your setup:

```env
# Example — fill in with your actual values
POSTGRES_USER=your_user
POSTGRES_PASSWORD=your_password
POSTGRES_DB=your_database

SOURCE_DIR=
```

> ⚠️ Never commit your `.env` file. It is listed in `.gitignore` by default.

## 3. Run the pipeline

```bash
source start.sh
```

This will spin up the Docker containers and execute the full pipeline automatically.

---

# 📊 Data Warehouse Model

The warehouse is based on a star schema:

### ⭐ Fact Table
- `fact_orders`

### 📐 Dimension Tables
- `dim_customers`
- `dim_products`
- `dim_sellers`
- `dim_time`

---

# ✅ Features

- ✔ End-to-end data pipeline
- ✔ Data lake + warehouse in one system
- ✔ Modular Python pipeline
- ✔ SQL-based transformations
- ✔ Dockerized environment

---

# 🔧 Future Improvements

- Add Apache Airflow orchestration
- Implement incremental data loading
- Add data validation (Great Expectations)
- Integrate BI tools (Power BI / Tableau)

---

# 👤 Author

**Mamadou Alpha Diallo**  
🎓 Master of Engineering — SUPINFO  
💡 Interested in Data Engineering, Big Data & AI