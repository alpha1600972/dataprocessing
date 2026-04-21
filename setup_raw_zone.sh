#!/bin/bash

# Quick Start: Data Lake Creation with JSONB Raw Zone
# ===================================================

echo "=========================================="
echo "Data Lake Setup - Raw Zone with JSONB"
echo "=========================================="
echo ""

# Step 1: Load source data from CSV
echo "[Step 1] Loading data from CSV to source_data schema..."
python3 load_olist.py

if [ $? -ne 0 ]; then
    echo "❌ Failed to load source data"
    exit 1
fi

echo ""

# Step 2: Create raw_zone with JSONB tables
echo "[Step 2] Creating raw zone with JSONB storage..."
python3 create_data_lake.py

if [ $? -ne 0 ]; then
    echo "❌ Failed to create raw zone"
    exit 1
fi

echo ""

# Step 3: Show database info
echo "[Step 3] Verifying database structure..."
python3 -c "
from connect import get_db_engine
import sqlalchemy as sa

engine = get_db_engine()

print('\n📊 Schemas created:')
with engine.connect() as conn:
    result = conn.execute(sa.text('''
        SELECT schema_name FROM information_schema.schemata 
        WHERE schema_name IN ('source_data', 'raw_zone', 'processed_zone', 'curated_zone')
        ORDER BY schema_name
    '''))
    for row in result:
        print(f'  ✓ {row[0]}')

print('\n📋 Tables in raw_zone:')
with engine.connect() as conn:
    result = conn.execute(sa.text('''
        SELECT table_name FROM information_schema.tables 
        WHERE table_schema = 'raw_zone'
        ORDER BY table_name
    '''))
    for row in result:
        print(f'  ✓ {row[0]}')

print('\n✅ Data lake created successfully!')
print('\n📖 See RAW_ZONE_JSONB_GUIDE.md for usage examples')
"

echo ""
echo "=========================================="
echo "✅ Setup Complete!"
echo "=========================================="
