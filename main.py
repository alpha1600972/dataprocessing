from load_olist import main as load_olist_data
from create_data_lake import main as create_data_lake
from request_constraint import main as request_constraints
from create_processed_zone import main as create_processed_zone
from create_curated_zone import main as create_curated_zone
from create_data_warehouse import main as create_data_warehouse
from analytical_queries import main as run_analytical_queries

def main():
    # Step 1: Load Olist data into source_data schema
    load_olist_data()
    
    # Step 2: Create data lake (raw_zone and row_zone)
    create_data_lake()
    
    # Step 3: Add indexes and constraints to source_data tables
    request_constraints()
    
    # Step 4: Create processed_zone with cleaned/normalized data
    create_processed_zone()
    
    # Step 5: Create curated_zone with business-friendly tables
    create_curated_zone()
    
    # Step 6: Create data warehouse with star schema
    create_data_warehouse()
    
    # Step 7: Run analytical queries on the data warehouse
    run_analytical_queries()
    print("\n✓ All steps completed successfully!")

if __name__ == "__main__":
    main()
