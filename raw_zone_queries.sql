-- Raw Zone JSONB Queries - Practical Examples
-- =============================================
-- Run these queries in your PostgreSQL database to work with raw zone JSONB data

-- ========================================================================
-- 1. BASIC QUERIES - Get Data from Raw Zone
-- ========================================================================

-- View entire JSON record for a single row
SELECT 
    raw_id,
    jsonb_pretty(data) as original_record,
    loaded_at
FROM raw_zone.olist_customers_raw
LIMIT 1;

-- Extract specific fields as text
SELECT 
    raw_id,
    data->>'customer_id' as customer_id,
    data->>'customer_city' as city,
    data->>'customer_state' as state,
    loaded_at
FROM raw_zone.olist_customers_raw
LIMIT 10;

-- ========================================================================
-- 2. TYPE CASTING - Convert JSON strings to proper types
-- ========================================================================

-- Cast numeric values
SELECT 
    raw_id,
    (data->>'customer_id')::text as customer_id,
    (data->>'zip_code')::INTEGER as zip_code,
    (data->>'latitude')::NUMERIC as latitude,
    (data->>'longitude')::NUMERIC as longitude
FROM raw_zone.olist_geolocation_raw
LIMIT 5;

-- ========================================================================
-- 3. FILTERING - Query raw data by field values
-- ========================================================================

-- Simple equality filter
SELECT COUNT(*) as total_sp_customers
FROM raw_zone.olist_customers_raw
WHERE data->>'state' = 'SP';

-- Multiple conditions
SELECT COUNT(*) 
FROM raw_zone.olist_customers_raw
WHERE data->>'state' = 'SP'
  AND data->>'city' = 'São Paulo';

-- IN clause equivalent
SELECT raw_id, data->>'customer_id', data->>'state'
FROM raw_zone.olist_customers_raw
WHERE data->>'state' IN ('SP', 'RJ', 'MG', 'BA')
LIMIT 10;

-- ========================================================================
-- 4. JSON OPERATORS - Advanced JSONB operations
-- ========================================================================

-- Check if a key exists in JSON
SELECT COUNT(*) as records_with_optional_field
FROM raw_zone.olist_customers_raw
WHERE data ? 'phone_number';

-- Check if JSON contains a specific key-value pair
SELECT COUNT(*) 
FROM raw_zone.olist_customers_raw
WHERE data @> '{"state": "SP"}'::jsonb;

-- Check if value is contained (inverse of @>)
SELECT COUNT(*)
FROM raw_zone.olist_customers_raw
WHERE '{"state": "SP"}'::jsonb <@ data;

-- Get all unique keys in the JSON
SELECT DISTINCT jsonb_object_keys(data) as field_names
FROM raw_zone.olist_customers_raw
LIMIT 1;

-- ========================================================================
-- 5. TEXT SEARCH - Search within JSON values
-- ========================================================================

-- Search for substring in any field
SELECT raw_id, data
FROM raw_zone.olist_customers_raw
WHERE data::text ILIKE '%paulo%'
LIMIT 5;

-- Case-insensitive city search
SELECT raw_id, data->>'customer_id', data->>'customer_city'
FROM raw_zone.olist_customers_raw
WHERE LOWER(data->>'customer_city') LIKE '%paulo%'
LIMIT 10;

-- ========================================================================
-- 6. AGGREGATION - Analyze raw data
-- ========================================================================

-- Count records by state
SELECT 
    data->>'state' as state,
    COUNT(*) as total_customers
FROM raw_zone.olist_customers_raw
GROUP BY data->>'state'
ORDER BY total_customers DESC;

-- Count distinct values
SELECT COUNT(DISTINCT data->>'state') as number_of_states
FROM raw_zone.olist_customers_raw;

-- Min/Max values
SELECT 
    MIN((data->>'zip_code')::INTEGER) as min_zip,
    MAX((data->>'zip_code')::INTEGER) as max_zip,
    AVG((data->>'zip_code')::INTEGER) as avg_zip
FROM raw_zone.olist_geolocation_raw;

-- ========================================================================
-- 7. ORDERING & LIMITING - Sort raw data
-- ========================================================================

-- Order by JSON field
SELECT 
    raw_id,
    data->>'customer_id',
    data->>'customer_city'
FROM raw_zone.olist_customers_raw
ORDER BY data->>'customer_state', data->>'customer_city'
LIMIT 20;

-- Order by numeric field (with casting)
SELECT 
    raw_id,
    data->>'customer_id',
    (data->>'zip_code')::INTEGER as zip_code
FROM raw_zone.olist_geolocation_raw
ORDER BY (data->>'zip_code')::INTEGER DESC
LIMIT 10;

-- ========================================================================
-- 8. JOINING - Combine raw zone tables
-- ========================================================================

-- Join raw zone tables
SELECT 
    c.raw_id,
    c.data->>'customer_id' as customer_id,
    c.data->>'customer_city' as city,
    o.data->>'order_id' as order_id,
    o.data->>'order_status' as status
FROM raw_zone.olist_customers_raw c
JOIN raw_zone.olist_orders_raw o 
    ON (c.data->>'customer_id')::text = (o.data->>'customer_id')::text
LIMIT 10;

-- ========================================================================
-- 9. CREATING VIEWS - Denormalize for easier access
-- ========================================================================

-- Create a normalized view from raw JSONB
CREATE OR REPLACE VIEW processed_zone.vw_customers_normalized AS
SELECT 
    raw_id,
    (data->>'customer_id')::text as customer_id,
    (data->>'customer_unique_id')::text as customer_unique_id,
    data->>'customer_zip_code_prefix' as zip_code_prefix,
    data->>'customer_city' as city,
    data->>'customer_state' as state,
    loaded_at as ingestion_timestamp
FROM raw_zone.olist_customers_raw;

-- Query the view
SELECT * FROM processed_zone.vw_customers_normalized LIMIT 10;

-- ========================================================================
-- 10. MONITORING & DIAGNOSTICS
-- ========================================================================

-- Check raw zone table sizes
SELECT 
    table_name,
    pg_size_pretty(pg_total_relation_size('raw_zone.'||table_name)) as table_size
FROM information_schema.tables
WHERE table_schema = 'raw_zone'
ORDER BY pg_total_relation_size('raw_zone.'||table_name) DESC;

-- Check loading timestamps
SELECT 
    source_table,
    COUNT(*) as record_count,
    MIN(loaded_at) as first_record,
    MAX(loaded_at) as last_record
FROM raw_zone.olist_customers_raw
GROUP BY source_table;

-- Data quality checks - find NULL or empty JSON
SELECT COUNT(*) as null_records
FROM raw_zone.olist_customers_raw
WHERE data IS NULL OR data = '{}'::jsonb;

-- Check for records with missing expected fields
SELECT raw_id, data
FROM raw_zone.olist_customers_raw
WHERE NOT data ? 'customer_id'
LIMIT 10;

-- ========================================================================
-- 11. DATA MODIFICATION - Update JSONB data
-- ========================================================================

-- Update a field in JSON (example - don't run on production)
-- UPDATE raw_zone.olist_customers_raw
-- SET data = jsonb_set(data, '{customer_state}', '"RJ"')
-- WHERE raw_id = 1;

-- Add a new field to JSON
-- UPDATE raw_zone.olist_customers_raw
-- SET data = data || '{"processed": true}'::jsonb
-- WHERE loaded_at > NOW() - INTERVAL '1 day';

-- ========================================================================
-- 12. EXPORT - Convert back to normalized format
-- ========================================================================

-- Export to see structure
SELECT 
    raw_id,
    jsonb_each_text(data) as key_value,
    loaded_at
FROM raw_zone.olist_customers_raw
WHERE raw_id <= 5;

-- Create a CSV export (requires psql or client access)
-- COPY (
--   SELECT 
--     (data->>'customer_id')::text as customer_id,
--     (data->>'customer_unique_id')::text as customer_unique_id,
--     data->>'customer_city' as city,
--     data->>'customer_state' as state
--   FROM raw_zone.olist_customers_raw
-- ) TO '/tmp/customers_export.csv' CSV HEADER;
