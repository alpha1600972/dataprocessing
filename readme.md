# 🛒 E-Commerce Data Architecture

End-to-end data pipeline using PostgreSQL as a unified system for data lake and data warehouse.

# 🚀 Overview

This project implements a complete data architecture pipeline for an e-commerce dataset (Olist), including:

## 📥 Data ingestion (raw data)
## 🧱 Data lake (multi-layer zones)
## 🏗️ Data warehouse (star schema)
## 📊 Analytical queries & visualization

The goal is to simulate a real-world data engineering workflow using a single database system.

# 🧠 Architecture

Source Data → Data Lake → Data Warehouse → Analytics

## Layers:
    source_data
        Raw ingestion of Olist dataset
    Data Lake
        raw_zone: immutable raw data
        processed_zone: cleaned & normalized data
        curated_zone: business-ready datasets
    Data Warehouse
        Star schema (fact + dimensions)
        Optimized for analytics

# 🛠️ Tech Stack

| Category         | Tools                            |
| ---------------- | -------------------------------- |
| Database         | PostgreSQL                       |
| Processing       | Python (pandas, SQLAlchemy), SQL |
| Visualization    | matplotlib                       |
| Orchestration    | Python script                    |
| Containerization | Docker                           |

# 📂 Project Structure

dataprocessing/
│
├── Data_list/                  # source data (csv files)
├── charts/                     # image generated for Visualizations with Matplotlib
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
└── requirements.txt            # Python dependencies

# ⚙️ Pipeline Workflow

## The pipeline is executed sequentially:

    Load raw data into PostgreSQL
    Create data lake structure
    Apply constraints and indexing
    Clean and transform data
    Build curated datasets
    Create data warehouse (star schema)
    Run analytical queries

# ▶️ Getting Started

## 1. Clone the repository
    ```Bash
    git clone https://github.com/alpha1600972/dataprocessin.git
    cd ecommerce-data-architecture
    ```

## 2. Run pipeline
    ```Bash
    source start.sh
    ```

# 📊 Data Warehouse Model

The warehouse is based on a star schema:

## ⭐ Fact Table
    fact_orders
## 📐 Dimension Tables
    dim_customers
    dim_products
    dim_sellers
    dim_time

# ✅ Features

    ✔ End-to-end data pipeline
    ✔ Data lake + warehouse in one system
    ✔ Modular Python pipeline
    ✔ SQL-based transformations
    ✔ Dockerized environment

# 🔧 Future Improvements
    Add Apache Airflow orchestration
    Implement incremental data loading
    Add data validation (Great Expectations)
    Integrate BI tools (Power BI / Tableau)

# 👤 Author
    Mamadou Alpha Diallo
    🎓 Master of Engeneering (SUPINFO)
    💡 Interested in Data Engineering, Big Data & AI