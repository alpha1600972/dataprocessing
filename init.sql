-- Create schemas for the data pipeline
CREATE SCHEMA IF NOT EXISTS source_data;
CREATE SCHEMA IF NOT EXISTS data_warehouse;
CREATE SCHEMA IF NOT EXISTS data_lake;
CREATE SCHEMA IF NOT EXISTS raw_zone;
CREATE SCHEMA IF NOT EXISTS processed_zone;
CREATE SCHEMA IF NOT EXISTS curated_zone;

-- Set search path
ALTER DATABASE dataprocessing SET search_path TO source_data, public;

SELECT 'Schemas created successfully' AS message;

-- Verify schemas
SELECT schema_name
FROM information_schema.schemata
WHERE schema_name IN (
    'source_data',
    'data_warehouse',
    'data_lake',
    'raw_zone',
    'processed_zone',
    'curated_zone')
ORDER BY schema_name;