# Raw Zone with JSONB Storage - Implementation Guide

## Architecture Overview

```
source_data (normalized tables from CSV)
    ↓
raw_zone (JSONB storage - original format)
    ↓
processed_zone (normalized/flattened)
    ↓
curated_zone (business-ready views)
```

## Raw Zone Tables Structure

Each source table gets a corresponding raw zone table with this structure:

```sql
CREATE TABLE raw_zone.<table_name>_raw (
    raw_id BIGSERIAL PRIMARY KEY,
    data JSONB NOT NULL,                    -- Original data as JSON
    source_table VARCHAR(255),              -- Which source it came from
    loaded_at TIMESTAMP,                    -- When it was loaded
    file_hash VARCHAR(64),                  -- For deduplication
    created_by VARCHAR(100)                 -- Data lineage
);

CREATE INDEX idx_<table_name>_raw_data ON raw_zone.<table_name>_raw USING GIN (data);
```

## Key Advantages of JSONB Storage

| Advantage | Description |
|-----------|-------------|
| **Schema Flexibility** | No predefined schema needed; handles varying column structures |
| **Data Integrity** | Original data preserved without transformation |
| **Fast Queries** | GIN indexes enable efficient JSONB searches |
| **Data Lineage** | Track source and load timestamp for every record |
| **Easy Rollback** | Original data always available for reprocessing |

## How to Use

### 1. Initial Setup

```bash
# Initialize database with schemas
python3 load_olist.py      # Load CSV to source_data

# Create raw_zone with JSONB tables
python3 create_data_lake.py
```

### 2. Access Raw Data

#### Get all original data from a table
```sql
SELECT data 
FROM raw_zone.olist_customers_raw 
LIMIT 5;
```

#### Extract specific fields
```sql
SELECT 
    raw_id,
    data->>'customer_id' as customer_id,
    data->>'customer_city' as city,
    loaded_at
FROM raw_zone.olist_customers_raw
LIMIT 10;
```

#### Cast to appropriate type
```sql
SELECT 
    raw_id,
    (data->>'customer_id')::UUID as customer_id,
    (data->>'zip_code')::INTEGER as zip_code
FROM raw_zone.olist_customers_raw;
```

#### Filter by JSON field
```sql
SELECT COUNT(*) 
FROM raw_zone.olist_customers_raw 
WHERE data->>'state' = 'SP';
```

#### Use JSON containment operator
```sql
SELECT raw_id, data
FROM raw_zone.olist_customers_raw
WHERE data @> '{"state": "SP"}'::jsonb;
```

### 3. Common JSONB Operations

#### Get all keys in a JSON object
```sql
SELECT DISTINCT jsonb_object_keys(data) as fields
FROM raw_zone.olist_customers_raw
LIMIT 1;
```

#### Pretty print JSON data
```sql
SELECT 
    raw_id,
    jsonb_pretty(data) as formatted_data
FROM raw_zone.olist_customers_raw
LIMIT 1;
```

#### Extract nested JSON arrays
```sql
SELECT 
    raw_id,
    data->'attributes' as attributes
FROM raw_zone.<table_name>_raw
WHERE data ? 'attributes';
```

#### Check if key exists
```sql
SELECT COUNT(*) 
FROM raw_zone.olist_customers_raw
WHERE data ? 'optional_field';
```

#### Convert back to normalized table
```sql
SELECT 
    raw_id,
    (data->>'customer_id')::text as customer_id,
    (data->>'customer_unique_id')::text as customer_unique_id,
    data->>'customer_zip_code_prefix' as zip_code,
    data->>'customer_city' as city,
    data->>'customer_state' as state,
    loaded_at
FROM raw_zone.olist_customers_raw;
```

## JSONB Operators Reference

| Operator | Description | Example |
|----------|-------------|---------|
| `->` | Get JSON value as JSON | `data->'customer_id'` |
| `->>` | Get JSON value as text | `data->>'customer_id'` |
| `@>` | Contains (left contains right) | `data @> '{"state":"SP"}'` |
| `<@` | Is contained by | `'{"state":"SP"}' <@ data` |
| `?` | Key exists | `data ? 'zip_code'` |
| `\|\|` | Concatenate JSON | `data \|\| '{"new":"field"}'` |
| `@?` | JSON path exists | `data @? '$.customer_id'` |

## Performance Tips

1. **Use GIN Indexes**: Already created on `data` column for fast searches
2. **Use ->> for equality**: Text extraction is faster for simple comparisons
3. **Batch Operations**: Insert 1000+ records at a time
4. **Use LIMIT**: Always use LIMIT in exploratory queries on large tables
5. **Denormalize for Speed**: Create materialized views for frequently accessed data

## Monitoring Raw Zone

```sql
-- Check table sizes
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables
WHERE schemaname = 'raw_zone'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- Check metadata
SELECT * FROM raw_zone.data_metadata;

-- Count records per table
SELECT 
    source_table,
    COUNT(*) as total_records,
    MIN(loaded_at) as first_load,
    MAX(loaded_at) as last_load
FROM raw_zone.olist_customers_raw
GROUP BY source_table;
```

## SQL Examples: From Raw to Processed

```sql
-- Create a processed (normalized) view from raw JSONB
CREATE VIEW processed_zone.customers AS
SELECT 
    raw_id,
    (data->>'customer_id')::UUID as customer_id,
    (data->>'customer_unique_id')::UUID as customer_unique_id,
    data->>'customer_zip_code_prefix' as zip_code_prefix,
    data->>'customer_city' as city,
    data->>'customer_state' as state,
    loaded_at
FROM raw_zone.olist_customers_raw;

-- Query the normalized view
SELECT * FROM processed_zone.customers LIMIT 10;
```

## Migration Path

```
CSV Files
  ↓
load_olist.py (source_data schema - normalized)
  ↓
create_data_lake.py (raw_zone - JSONB format)
  ↓
Custom transformations (processed_zone - business rules)
  ↓
final outputs (curated_zone - analytics-ready)
```

## Troubleshooting

**Q: How do I modify JSONB data?**
```sql
UPDATE raw_zone.olist_customers_raw
SET data = jsonb_set(data, '{customer_state}', '"RJ"')
WHERE raw_id = 1;
```

**Q: How do I export back to CSV?**
```sql
COPY (
    SELECT 
        raw_id,
        jsonb_each(data)
    FROM raw_zone.olist_customers_raw
) TO '/tmp/export.csv' CSV HEADER;
```

**Q: Can I validate JSON structure?**
```sql
SELECT raw_id, data
FROM raw_zone.olist_customers_raw
WHERE NOT jsonb_typeof(data) = 'object';
```
