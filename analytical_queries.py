"""
Analytical Queries and Dashboard Reports
Spanning Raw Zone → Curated Zone → Data Warehouse
Demonstrates query patterns across the data lake architecture
"""

import sqlalchemy as sa
from sqlalchemy import text
from datetime import datetime, timedelta
import logging
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os
from connect import get_db_engine

# Set style for better-looking plots
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (14, 8)
plt.rcParams['font.size'] = 10

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# SCHEMA COMPARISON ANALYSIS
# ============================================================================

def analyze_data_lineage():
    """
    Compare data across the three architectural layers
    Shows volume, quality, and transformations
    """
    engine = get_db_engine()
    
    print("\n" + "="*100)
    print("DATA LINEAGE ANALYSIS: Raw Zone → Curated Zone → Data Warehouse")
    print("="*100)
    
    # 1. RAW ZONE - Original data with lineage
    print("\n" + "-"*100)
    print("1. RAW ZONE (Source Data - JSONB)")
    print("-"*100)
    
    try:
        query = """
        SELECT 
            COUNT(*) as total_records,
            COUNT(DISTINCT source_file) as source_tables,
            MAX(loaded_at) as latest_load,
            COUNT(DISTINCT DATE(loaded_at)) as load_dates
        FROM raw_zone.data_metadata
        WHERE status = 'loaded'
        """
        
        with engine.connect() as conn:
            result = conn.execute(text(query)).fetchone()
            print(f"  Total Records Loaded:      {result[0]:>15,}")
            print(f"  Source Tables:             {result[1]:>15,}")
            print(f"  Latest Load Date:          {result[2]:>15}")
            print(f"  Load Dates:                {result[3]:>15,}")
    except Exception as e:
        print(f"  ℹ Raw zone metadata: {str(e)}")
    
    # 2. CURATED ZONE - Refined and validated data
    print("\n" + "-"*100)
    print("2. CURATED ZONE (Refined & Validated)")
    print("-"*100)
    
    queries = {
        'Orders Refined': "SELECT COUNT(*) FROM curated_zone.orders_refined WHERE is_valid = TRUE",
        'Customers Refined': "SELECT COUNT(*) FROM curated_zone.customers_refined WHERE is_valid = TRUE",
        'Order Items Refined': "SELECT COUNT(*) FROM curated_zone.order_items_refined",
        'Sellers Refined': "SELECT COUNT(*) FROM curated_zone.sellers_refined WHERE is_valid = TRUE"
    }
    
    with engine.connect() as conn:
        for label, query in queries.items():
            result = conn.execute(text(query)).scalar()
            print(f"  {label:<40} {result:>15,}")
    
    # 3. DATA WAREHOUSE - Star Schema Analytics
    print("\n" + "-"*100)
    print("3. DATA WAREHOUSE (Star Schema - Optimized for Analytics)")
    print("-"*100)
    
    queries = {
        'Fact Orders': "SELECT COUNT(*) FROM data_warehouse.fct_orders",
        'Dimension Customers': "SELECT COUNT(*) FROM data_warehouse.dim_customer",
        'Dimension Products': "SELECT COUNT(*) FROM data_warehouse.dim_product",
        'Dimension Sellers (Current)': "SELECT COUNT(*) FROM data_warehouse.dim_seller_scd WHERE is_current = TRUE",
        'Dimension Locations': "SELECT COUNT(*) FROM data_warehouse.dim_location"
    }
    
    with engine.connect() as conn:
        for label, query in queries.items():
            result = conn.execute(text(query)).scalar()
            print(f"  {label:<40} {result:>15,}")
    
    print("\n" + "="*100)


# ============================================================================
# QUERY 1: SALES BY REGION AND TIME (Spanning Warehouse)
# ============================================================================

def query_sales_by_region_time(engine=None):
    """
    Analytical Query 1: Sales Performance by Region over Time
    Uses: Data Warehouse (Star Schema)
    """
    if engine is None:
        engine = get_db_engine()
    
    print("\n" + "="*100)
    print("QUERY 1: SALES BY REGION AND TIME")
    print("="*100)
    print("Source: data_warehouse schema (Star Schema)")
    print("\nSQL Approach: Dimension joins with fact table aggregation")
    print("-"*100)
    
    query = """
    SELECT
        dl.state_code as region,
        dd.year,
        dd.month,
        COUNT(DISTINCT fo.order_id) as order_count,
        SUM(fo.total_order_value)::NUMERIC(15,2) as total_sales,
        AVG(fo.total_order_value)::NUMERIC(12,2) as avg_order_value,
        COUNT(DISTINCT fo.dim_customer_id) as unique_customers,
        SUM(CASE WHEN fo.is_on_time = TRUE THEN 1 ELSE 0 END) as on_time_deliveries,
        ROUND((100.0 * SUM(CASE WHEN fo.is_on_time = TRUE THEN 1 ELSE 0 END))::NUMERIC / 
              NULLIF(COUNT(DISTINCT fo.order_id), 0), 2) as on_time_percentage
    FROM data_warehouse.fct_orders fo
    LEFT JOIN data_warehouse.dim_location dl ON fo.dim_location_id = dl.dim_location_id
    LEFT JOIN data_warehouse.dim_date dd ON fo.dim_date_id = dd.date_id
    WHERE dd.year >= 2017
    GROUP BY dl.state_code, dd.year, dd.month
    ORDER BY dd.year DESC, dd.month DESC, total_sales DESC
    LIMIT 20
    """
    
    try:
        with engine.connect() as conn:
            result = conn.execute(text(query))
            rows = result.fetchall()
            
            print(f"\n{'Region':<10} {'Year':<6} {'Month':<6} {'Orders':<10} {'Sales':<15} "
                  f"{'Avg Order':<15} {'Customers':<12} {'On-Time %':<12}")
            print("-"*100)
            
            for row in rows:
                print(f"{row[0]:<10} {row[1]:<6} {row[2]:<6} {row[3]:<10} ${row[4]:<14,.0f} "
                      f"${row[5]:<14,.0f} {row[6]:<12,} {row[8]:<11.1f}%")
            
            print(f"\nTotal rows returned: {len(rows)}")
            
    except Exception as e:
        logger.error(f"Error in query 1: {str(e)}")


# ============================================================================
# QUERY 2: PRODUCT PERFORMANCE (Spanning Warehouse)
# ============================================================================

def query_product_performance(engine=None):
    """
    Analytical Query 2: Product Category Performance & Rankings
    Uses: Data Warehouse (Star Schema)
    """
    if engine is None:
        engine = get_db_engine()
    
    print("\n" + "="*100)
    print("QUERY 2: PRODUCT CATEGORY PERFORMANCE")
    print("="*100)
    print("Source: data_warehouse schema (Star Schema)")
    print("\nSQL Approach: Product dimension with SCD tracking + fact aggregation")
    print("-"*100)
    
    query = """
    SELECT
        dp.product_id,
        COUNT(DISTINCT fo.order_id) as orders,
        SUM(fo.quantity) as total_quantity,
        SUM(fo.total_order_value)::NUMERIC(15,2) as total_revenue,
        AVG(fo.total_order_value)::NUMERIC(12,2) as avg_order_value,
        AVG(dp.avg_price)::NUMERIC(10,2) as avg_product_price,
        COUNT(DISTINCT fo.dim_customer_id) as unique_customers,
        ROUND(100.0 * COUNT(DISTINCT fo.order_id)::NUMERIC / 
              (SELECT COUNT(DISTINCT order_id) FROM data_warehouse.fct_orders), 2) as pct_of_total_orders
    FROM data_warehouse.fct_orders fo
    LEFT JOIN data_warehouse.dim_product dp ON fo.dim_product_id = dp.dim_product_id
    WHERE dp.is_active = TRUE
    GROUP BY dp.product_id, dp.avg_price
    HAVING COUNT(DISTINCT fo.order_id) > 50
    ORDER BY total_revenue DESC
    LIMIT 15
    """
    
    try:
        with engine.connect() as conn:
            result = conn.execute(text(query))
            rows = result.fetchall()
            
            print(f"\n{'Product ID':<20} {'Orders':<10} {'Qty':<10} {'Revenue':<15} "
                  f"{'Avg Price':<12} {'Customers':<12} {'% of Orders':<12}")
            print("-"*100)
            
            for row in rows:
                print(f"{row[0]:<20} {row[1]:<10} {row[2]:<10} ${row[3]:<14,.0f} "
                      f"${row[5]:<11,.2f} {row[6]:<12,} {row[7]:<11.2f}%")
            
            print(f"\nTotal products analyzed: {len(rows)}")
            
    except Exception as e:
        logger.error(f"Error in query 2: {str(e)}")


# ============================================================================
# QUERY 3: CUSTOMER SEGMENTATION (Warehouse + Curated Zone Comparison)
# ============================================================================

def query_customer_segments(engine=None):
    """
    Analytical Query 3: Customer Segmentation Analysis
    Demonstrates: Data Warehouse approach vs Curated Zone direct query
    """
    if engine is None:
        engine = get_db_engine()
    
    print("\n" + "="*100)
    print("QUERY 3: CUSTOMER SEGMENTATION ANALYSIS")
    print("="*100)
    
    # Approach 1: Data Warehouse (Pre-aggregated)
    print("\nApproach A: Using Data Warehouse (Pre-aggregated Star Schema)")
    print("-"*100)
    print("Performance: ✓ Fastest (pre-aggregated)")
    print("Data Freshness: Near real-time")
    print("\nSQL:")
    
    query_warehouse = """
    SELECT
        CASE 
            WHEN customer_lifetime_value < 1000 THEN 'Bronze'
            WHEN customer_lifetime_value < 5000 THEN 'Silver'
            WHEN customer_lifetime_value < 20000 THEN 'Gold'
            ELSE 'Platinum'
        END as customer_segment,
        COUNT(*) as segment_size,
        AVG(customer_lifetime_value)::NUMERIC(12,2) as avg_lifetime_value,
        SUM(customer_lifetime_value)::NUMERIC(15,2) as segment_total_value,
        AVG(order_frequency) as avg_orders_per_customer,
        AVG(avg_order_value) as segment_avg_order_value
    FROM (
        SELECT
            dc.dim_customer_id,
            COUNT(DISTINCT fo.order_id) as order_frequency,
            SUM(fo.total_order_value) as customer_lifetime_value,
            AVG(fo.total_order_value) as avg_order_value
        FROM data_warehouse.fct_orders fo
        LEFT JOIN data_warehouse.dim_customer dc ON fo.dim_customer_id = dc.dim_customer_id
        GROUP BY dc.dim_customer_id
    ) customer_metrics
    GROUP BY customer_segment
    ORDER BY avg_lifetime_value DESC
    """
    
    try:
        with engine.connect() as conn:
            result = conn.execute(text(query_warehouse))
            rows = result.fetchall()
            
            print(f"\n{'Segment':<12} {'Size':<10} {'Avg Lifetime':<15} {'Total Value':<15} "
                  f"{'Avg Orders':<12} {'Avg Order Value':<15}")
            print("-"*100)
            
            for row in rows:
                print(f"{row[0]:<12} {row[1]:<10,} ${row[2]:<14,.2f} ${row[3]:<14,.0f} "
                      f"{row[4]:<12.1f} ${row[5]:<14,.2f}")
            
    except Exception as e:
        logger.error(f"Error in warehouse approach: {str(e)}")
    
    # Approach 2: Direct Curated Zone Query (Ad-hoc)
    print("\n" + "-"*100)
    print("Approach B: Direct Query on Curated Zone (Ad-hoc)")
    print("-"*100)
    print("Performance: ⚠ Slower (real-time calculation)")
    print("Data Freshness: Most current (real-time)")
    print("\nSQL:")
    
    query_curated = """
    SELECT
        CASE 
            WHEN customer_lifetime_value < 1000 THEN 'Bronze'
            WHEN customer_lifetime_value < 5000 THEN 'Silver'
            WHEN customer_lifetime_value < 20000 THEN 'Gold'
            ELSE 'Platinum'
        END as customer_segment,
        COUNT(*) as segment_size,
        AVG(customer_lifetime_value)::NUMERIC(12,2) as avg_lifetime_value,
        SUM(customer_lifetime_value)::NUMERIC(15,2) as segment_total_value
    FROM (
        SELECT
            c.customer_id,
            COUNT(DISTINCT o.order_id) as order_frequency,
            SUM(oi.price + oi.freight_value) as customer_lifetime_value
        FROM curated_zone.customers_refined c
        LEFT JOIN curated_zone.orders_refined o ON c.customer_id = o.customer_id AND o.is_valid = TRUE
        LEFT JOIN curated_zone.order_items_refined oi ON o.order_id = oi.order_id
        WHERE c.is_valid = TRUE
        GROUP BY c.customer_id
    ) AS customer_metrics
    GROUP BY customer_segment
    ORDER BY avg_lifetime_value DESC
    """
    
    try:
        with engine.connect() as conn:
            result = conn.execute(text(query_curated))
            rows = result.fetchall()
            
            print(f"\n{'Segment':<12} {'Size':<10} {'Avg Lifetime':<15} {'Total Value':<15}")
            print("-"*100)
            
            for row in rows:
                print(f"{row[0]:<12} {row[1]:<10,} ${row[2]:<14,.2f} ${row[3]:<14,.0f}")
            
    except Exception as e:
        logger.error(f"Error in curated zone approach: {str(e)}")


# ============================================================================
# DASHBOARD 1: SALES BY REGION AND TIME
# ============================================================================

def dashboard_sales_regional(engine=None):
    """Dashboard: Sales Performance by Region and Time Period"""
    if engine is None:
        engine = get_db_engine()
    
    print("\n" + "="*100)
    print("DASHBOARD 1: REGIONAL SALES PERFORMANCE")
    print("="*100)
    
    query = """
    WITH regional_sales AS (
        SELECT
            dl.state_code as region,
            COUNT(DISTINCT fo.order_id) as total_orders,
            SUM(fo.total_order_value)::NUMERIC(15,2) as total_sales,
            AVG(fo.total_order_value)::NUMERIC(12,2) as avg_order_value,
            COUNT(DISTINCT fo.dim_customer_id) as unique_customers,
            (SUM(CASE WHEN fo.is_on_time = TRUE THEN 1 ELSE 0 END)::NUMERIC / 
            NULLIF(COUNT(DISTINCT fo.order_id), 0)) as on_time_rate
        FROM data_warehouse.fct_orders fo
        LEFT JOIN data_warehouse.dim_location dl ON fo.dim_location_id = dl.dim_location_id
        GROUP BY dl.state_code
    )
    SELECT
        region,
        total_orders,
        total_sales,
        avg_order_value,
        unique_customers,
        ROUND((100.0 * on_time_rate)::NUMERIC, 1) as on_time_pct,
        ROUND((total_sales / NULLIF(total_orders, 0))::NUMERIC, 2) as revenue_per_order,
        ROUND((total_orders::NUMERIC / NULLIF(unique_customers, 0))::NUMERIC, 2) as orders_per_customer
    FROM regional_sales
    ORDER BY total_sales DESC
    """
    
    try:
        with engine.connect() as conn:
            result = conn.execute(text(query))
            rows = result.fetchall()
            
            print(f"\n{'Region':<10} {'Orders':<10} {'Sales':<15} {'Avg Order':<12} "
                  f"{'Customers':<12} {'On-Time %':<12} {'Rev/Order':<12} {'Orders/Cust':<12}")
            print("-"*100)
            
            for row in rows:
                print(f"{row[0]:<10} {row[1]:<10,} ${row[2]:<14,.0f} ${row[3]:<11,.2f} "
                      f"{row[4]:<12,} {row[5]:<11.1f}% ${row[6]:<11,.2f} {row[7]:<11.2f}")
            
            # Summary statistics
            print("\n" + "-"*100)
            print("SUMMARY STATISTICS:")
            total_orders = sum(row[1] for row in rows if row[1])
            total_sales = sum(row[2] for row in rows if row[2])
            unique_customers = sum(row[4] for row in rows if row[4])
            print(f"  Total Orders:           {total_orders:>15,}")
            print(f"  Total Sales:            ${total_sales:>14,.0f}")
            print(f"  Total Unique Customers: {unique_customers:>15,}")
            print(f"  Average Order Value:    ${total_sales/total_orders:>14,.2f}")
            
    except Exception as e:
        logger.error(f"Error in regional dashboard: {str(e)}")


# ============================================================================
# DASHBOARD 2: PRODUCT CATEGORY PERFORMANCE
# ============================================================================

def dashboard_product_performance(engine=None):
    """Dashboard: Product Performance and Market Share"""
    if engine is None:
        engine = get_db_engine()
    
    print("\n" + "="*100)
    print("DASHBOARD 2: PRODUCT PERFORMANCE & MARKET SHARE")
    print("="*100)
    
    query = """
    SELECT
        dp.product_id,
        COUNT(DISTINCT fo.order_id) as order_count,
        SUM(fo.quantity) as units_sold,
        SUM(fo.total_order_value)::NUMERIC(15,2) as total_revenue,
        COUNT(DISTINCT fo.dim_customer_id) as unique_customers
    FROM data_warehouse.fct_orders fo
    LEFT JOIN data_warehouse.dim_product dp ON fo.dim_product_id = dp.dim_product_id
    WHERE dp.is_active = TRUE
    GROUP BY dp.product_id
    ORDER BY total_revenue DESC
    LIMIT 20
    """
    
    try:
        with engine.connect() as conn:
            result = conn.execute(text(query))
            rows = result.fetchall()
            
            print(f"\n{'Rank':<6} {'Product ID':<20} {'Revenue':<15} {'Orders':<10} "
                  f"{'Units':<10} {'% of Total':<12}")
            print("-"*100)
            
            total_revenue = sum(row[3] for row in rows)
            for i, row in enumerate(rows, 1):
                pct = (row[3] / total_revenue * 100) if total_revenue > 0 else 0
                print(f"{i:<6} {row[0]:<20} ${row[3]:<14,.0f} {row[1]:<10,} "
                      f"{row[2]:<10,} {pct:<11.2f}%")
            
    except Exception as e:
        logger.error(f"Error in product dashboard: {str(e)}")


# ============================================================================
# DASHBOARD 3: CUSTOMER SEGMENTS & BEHAVIOR
# ============================================================================

def dashboard_customer_insights(engine=None):
    """Dashboard: Customer Segments, Behavior, and Lifetime Value"""
    if engine is None:
        engine = get_db_engine()
    
    print("\n" + "="*100)
    print("DASHBOARD 3: CUSTOMER INSIGHTS & SEGMENTS")
    print("="*100)
    
    query = """
    WITH customer_profiles AS (
        SELECT
            CASE 
                WHEN customer_lifetime_value < 1000 THEN 'Bronze'
                WHEN customer_lifetime_value < 5000 THEN 'Silver'
                WHEN customer_lifetime_value < 20000 THEN 'Gold'
                ELSE 'Platinum'
            END as segment,
            COUNT(*) as customer_count,
            AVG(customer_lifetime_value) as avg_lifetime_value,
            SUM(customer_lifetime_value) as segment_total_value,
            AVG(order_frequency) as avg_orders,
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY customer_lifetime_value) as median_lifetime,
            MAX(customer_lifetime_value) as max_lifetime,
            MIN(customer_lifetime_value) as min_lifetime
        FROM (
            SELECT
                dc.dim_customer_id,
                COUNT(DISTINCT fo.order_id) as order_frequency,
                SUM(fo.total_order_value) as customer_lifetime_value
            FROM data_warehouse.fct_orders fo
            LEFT JOIN data_warehouse.dim_customer dc ON fo.dim_customer_id = dc.dim_customer_id
            GROUP BY dc.dim_customer_id
        ) customer_metrics
        GROUP BY segment
    )
    SELECT
        segment,
        customer_count,
        ROUND(avg_lifetime_value::NUMERIC, 2) as avg_ltv,
        ROUND(segment_total_value::NUMERIC, 2) as total_value,
        ROUND(avg_orders::NUMERIC, 2) as avg_orders,
        ROUND(median_lifetime::NUMERIC, 2) as median_ltv,
        ROUND(100.0 * customer_count::NUMERIC / SUM(customer_count) OVER (), 2) as pct_customers,
        ROUND(100.0 * segment_total_value::NUMERIC / SUM(segment_total_value) OVER (), 2) as pct_revenue
    FROM customer_profiles
    ORDER BY avg_lifetime_value DESC
    """
    
    try:
        with engine.connect() as conn:
            result = conn.execute(text(query))
            rows = result.fetchall()
            
            print(f"\n{'Segment':<12} {'Customers':<12} {'Avg LTV':<15} {'Total Value':<15} "
                  f"{'Avg Orders':<12} {'% Customers':<14} {'% Revenue':<12}")
            print("-"*100)
            
            for row in rows:
                print(f"{row[0]:<12} {row[1]:<12,} ${row[2]:<14,.2f} ${row[3]:<14,.0f} "
                      f"{row[4]:<12.1f} {row[6]:<13.1f}% {row[7]:<11.1f}%")
            
    except Exception as e:
        logger.error(f"Error in customer dashboard: {str(e)}")


# ============================================================================
# VISUALIZATIONS WITH MATPLOTLIB
# ============================================================================

def visualize_sales_regional(engine=None, output_dir='./charts'):
    """Visualize: Sales Performance by Region"""
    if engine is None:
        engine = get_db_engine()
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    query = """
    WITH regional_sales AS (
        SELECT
            dl.state_code as region,
            COUNT(DISTINCT fo.order_id) as total_orders,
            SUM(fo.total_order_value)::NUMERIC(15,2) as total_sales,
            AVG(fo.total_order_value)::NUMERIC(12,2) as avg_order_value,
            COUNT(DISTINCT fo.dim_customer_id) as unique_customers
        FROM data_warehouse.fct_orders fo
        LEFT JOIN data_warehouse.dim_location dl ON fo.dim_location_id = dl.dim_location_id
        WHERE dl.state_code IS NOT NULL
        GROUP BY dl.state_code
    )
    SELECT *
    FROM regional_sales
    ORDER BY total_sales DESC
    """
    
    try:
        df = pd.read_sql_query(query, engine)
        
        # Create subplots
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        fig.suptitle('Regional Sales Performance Dashboard', fontsize=16, fontweight='bold')
        
        # 1. Sales by Region (Bar chart)
        ax1 = axes[0, 0]
        top_regions = df.nlargest(10, 'total_sales')
        ax1.barh(top_regions['region'], top_regions['total_sales'], color='steelblue')
        ax1.set_xlabel('Total Sales ($)', fontsize=11, fontweight='bold')
        ax1.set_title('Top 10 Regions by Revenue', fontsize=12, fontweight='bold')
        ax1.grid(axis='x', alpha=0.3)
        for i, v in enumerate(top_regions['total_sales']):
            ax1.text(v + 50000, i, f'${v:,.0f}', va='center', fontsize=9)
        
        # 2. Order Volume by Region (Bar chart)
        ax2 = axes[0, 1]
        top_regions_orders = df.nlargest(10, 'total_orders')
        ax2.barh(top_regions_orders['region'], top_regions_orders['total_orders'], color='coral')
        ax2.set_xlabel('Order Count', fontsize=11, fontweight='bold')
        ax2.set_title('Top 10 Regions by Order Volume', fontsize=12, fontweight='bold')
        ax2.grid(axis='x', alpha=0.3)
        for i, v in enumerate(top_regions_orders['total_orders']):
            ax2.text(v + 100, i, f'{int(v):,}', va='center', fontsize=9)
        
        # 3. Average Order Value by Region (Scatter plot)
        ax3 = axes[1, 0]
        scatter = ax3.scatter(df['unique_customers'], df['avg_order_value'], 
                             s=df['total_sales']/1000, alpha=0.6, c=df['total_sales'],
                             cmap='viridis', edgecolors='black', linewidth=0.5)
        ax3.set_xlabel('Unique Customers', fontsize=11, fontweight='bold')
        ax3.set_ylabel('Average Order Value ($)', fontsize=11, fontweight='bold')
        ax3.set_title('Customer Count vs Avg Order Value\n(bubble size = total sales)', 
                     fontsize=12, fontweight='bold')
        ax3.grid(alpha=0.3)
        cbar = plt.colorbar(scatter, ax=ax3)
        cbar.set_label('Total Sales ($)', fontsize=10)
        
        # 4. Regional Metrics Distribution (Box plot)
        ax4 = axes[1, 1]
        data_to_plot = [
            df['total_sales'] / 1000000,  # Convert to millions
            df['total_orders'] / 1000,     # Convert to thousands
            df['avg_order_value'] / 100    # Convert to hundreds
        ]
        bp = ax4.boxplot(data_to_plot, labels=['Sales ($M)', 'Orders (K)', 'Avg Order ($100)'],
                        patch_artist=True)
        for patch, color in zip(bp['boxes'], ['lightblue', 'lightcoral', 'lightgreen']):
            patch.set_facecolor(color)
        ax4.set_title('Distribution of Regional Metrics', fontsize=12, fontweight='bold')
        ax4.grid(axis='y', alpha=0.3)
        
        plt.tight_layout()
        output_path = os.path.join(output_dir, '01_regional_sales_dashboard.png')
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"✓ Saved: {output_path}")
        plt.close()
        
    except Exception as e:
        logger.error(f"Error visualizing regional sales: {str(e)}")


def visualize_product_performance(engine=None, output_dir='./charts'):
    """Visualize: Product Performance and Market Share"""
    if engine is None:
        engine = get_db_engine()
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    query = """
    SELECT
        dp.product_id,
        COUNT(DISTINCT fo.order_id) as order_count,
        SUM(fo.quantity) as units_sold,
        SUM(fo.total_order_value)::NUMERIC(15,2) as total_revenue,
        COUNT(DISTINCT fo.dim_customer_id) as unique_customers
    FROM data_warehouse.fct_orders fo
    LEFT JOIN data_warehouse.dim_product dp ON fo.dim_product_id = dp.dim_product_id
    WHERE dp.is_active = TRUE
    GROUP BY dp.product_id
    HAVING COUNT(DISTINCT fo.order_id) > 50
    ORDER BY total_revenue DESC
    LIMIT 20
    """
    
    try:
        df = pd.read_sql_query(query, engine)
        
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        fig.suptitle('Product Performance & Market Share Dashboard', fontsize=16, fontweight='bold')
        
        # 1. Top 15 Products by Revenue (Horizontal bar)
        ax1 = axes[0, 0]
        top_15 = df.head(15).copy()
        ax1.barh(range(len(top_15)), top_15['total_revenue'], color='steelblue')
        ax1.set_yticks(range(len(top_15)))
        ax1.set_yticklabels(top_15['product_id'], fontsize=9)
        ax1.set_xlabel('Revenue ($)', fontsize=11, fontweight='bold')
        ax1.set_title('Top 15 Products by Revenue', fontsize=12, fontweight='bold')
        ax1.grid(axis='x', alpha=0.3)
        for i, v in enumerate(top_15['total_revenue']):
            ax1.text(v + 5000, i, f'${v:,.0f}', va='center', fontsize=8)
        
        # 2. Market Share - Revenue Distribution (Pie chart)
        ax2 = axes[0, 1]
        top_5 = df.head(5)
        rest_revenue = df.iloc[5:]['total_revenue'].sum() if len(df) > 5 else 0
        pie_data = list(top_5['total_revenue']) + [rest_revenue]
        pie_labels = list(top_5['product_id']) + ['Rest of Portfolio']
        colors = plt.cm.Set3(range(len(pie_data)))
        wedges, texts, autotexts = ax2.pie(pie_data, labels=pie_labels, autopct='%1.1f%%',
                                           colors=colors, startangle=90)
        ax2.set_title('Revenue Distribution: Top 5 vs Rest', fontsize=12, fontweight='bold')
        for autotext in autotexts:
            autotext.set_color('black')
            autotext.set_fontweight('bold')
            autotext.set_fontsize(9)
        
        # 3. Orders vs Units Sold (Scatter)
        ax3 = axes[1, 0]
        scatter = ax3.scatter(df['order_count'], df['units_sold'],
                             s=df['total_revenue']/1000, alpha=0.6,
                             c=df['total_revenue'], cmap='plasma',
                             edgecolors='black', linewidth=0.5)
        ax3.set_xlabel('Order Count', fontsize=11, fontweight='bold')
        ax3.set_ylabel('Units Sold', fontsize=11, fontweight='bold')
        ax3.set_title('Order Volume vs Units Sold\n(bubble size = revenue)', 
                     fontsize=12, fontweight='bold')
        ax3.grid(alpha=0.3)
        cbar = plt.colorbar(scatter, ax=ax3)
        cbar.set_label('Revenue ($)', fontsize=10)
        
        # 4. Product Performance Metrics (Top 10)
        ax4 = axes[1, 1]
        top_10 = df.head(10).copy()
        x = range(len(top_10))
        width = 0.35
        
        # Normalize for comparison
        orders_norm = top_10['order_count'] / top_10['order_count'].max() * 100
        customers_norm = top_10['unique_customers'] / top_10['unique_customers'].max() * 100
        
        ax4.bar([i - width/2 for i in x], orders_norm, width, label='Orders (normalized)',
               color='skyblue', edgecolor='black', linewidth=0.5)
        ax4.bar([i + width/2 for i in x], customers_norm, width, label='Unique Customers (normalized)',
               color='orange', edgecolor='black', linewidth=0.5)
        ax4.set_xlabel('Product ID', fontsize=11, fontweight='bold')
        ax4.set_ylabel('Normalized Score (0-100)', fontsize=11, fontweight='bold')
        ax4.set_title('Top 10 Products: Orders vs Unique Customers', fontsize=12, fontweight='bold')
        ax4.set_xticks(x)
        ax4.set_xticklabels(top_10['product_id'], rotation=45, ha='right', fontsize=9)
        ax4.legend(fontsize=10)
        ax4.grid(axis='y', alpha=0.3)
        
        plt.tight_layout()
        output_path = os.path.join(output_dir, '02_product_performance_dashboard.png')
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"✓ Saved: {output_path}")
        plt.close()
        
    except Exception as e:
        logger.error(f"Error visualizing product performance: {str(e)}")


def visualize_customer_segments(engine=None, output_dir='./charts'):
    """Visualize: Customer Segmentation Analysis"""
    if engine is None:
        engine = get_db_engine()
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    query = """
    WITH customer_profiles AS (
        SELECT
            CASE 
                WHEN customer_lifetime_value < 1000 THEN 'Bronze'
                WHEN customer_lifetime_value < 5000 THEN 'Silver'
                WHEN customer_lifetime_value < 20000 THEN 'Gold'
                ELSE 'Platinum'
            END as segment,
            COUNT(*) as customer_count,
            AVG(customer_lifetime_value) as avg_lifetime_value,
            SUM(customer_lifetime_value) as segment_total_value,
            AVG(order_frequency) as avg_orders
        FROM (
            SELECT
                dc.dim_customer_id,
                COUNT(DISTINCT fo.order_id) as order_frequency,
                SUM(fo.total_order_value) as customer_lifetime_value
            FROM data_warehouse.fct_orders fo
            LEFT JOIN data_warehouse.dim_customer dc ON fo.dim_customer_id = dc.dim_customer_id
            GROUP BY dc.dim_customer_id
        ) customer_metrics
        GROUP BY segment
    )
    SELECT *
    FROM customer_profiles
    ORDER BY avg_lifetime_value DESC
    """
    
    try:
        df = pd.read_sql_query(query, engine)
        
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        fig.suptitle('Customer Segmentation & Insights Dashboard', fontsize=16, fontweight='bold')
        
        # Define segment colors
        segment_colors = {'Bronze': '#CD7F32', 'Silver': '#C0C0C0', 
                         'Gold': '#FFD700', 'Platinum': '#E5E4E2'}
        colors = [segment_colors.get(seg, 'gray') for seg in df['segment']]
        
        # 1. Customer Count by Segment (Bar chart)
        ax1 = axes[0, 0]
        ax1.bar(df['segment'], df['customer_count'], color=colors, edgecolor='black', linewidth=1.5)
        ax1.set_ylabel('Number of Customers', fontsize=11, fontweight='bold')
        ax1.set_title('Customer Distribution by Segment', fontsize=12, fontweight='bold')
        ax1.grid(axis='y', alpha=0.3)
        for i, (seg, count) in enumerate(zip(df['segment'], df['customer_count'])):
            ax1.text(i, count + max(df['customer_count'])*0.01, f'{int(count):,}', 
                    ha='center', fontweight='bold', fontsize=10)
        
        # 2. Revenue Contribution by Segment (Pie chart)
        ax2 = axes[0, 1]
        explode_values = (0.05, 0.05, 0.05, 0.1) if len(df) == 4 else tuple([0.05] * len(df))
        wedges, texts, autotexts = ax2.pie(df['segment_total_value'], labels=df['segment'],
                                           autopct='%1.1f%%', colors=colors,
                                           startangle=90, explode=explode_values[:len(df)])
        ax2.set_title('Revenue Contribution by Segment', fontsize=12, fontweight='bold')
        for autotext in autotexts:
            autotext.set_color('black')
            autotext.set_fontweight('bold')
            autotext.set_fontsize(10)
        
        # 3. Average Lifetime Value by Segment (Bar chart with value labels)
        ax3 = axes[1, 0]
        bars = ax3.bar(df['segment'], df['avg_lifetime_value'], color=colors, 
                      edgecolor='black', linewidth=1.5)
        ax3.set_ylabel('Average Lifetime Value ($)', fontsize=11, fontweight='bold')
        ax3.set_title('Average Customer Lifetime Value by Segment', fontsize=12, fontweight='bold')
        ax3.grid(axis='y', alpha=0.3)
        for i, (seg, val) in enumerate(zip(df['segment'], df['avg_lifetime_value'])):
            ax3.text(i, val + max(df['avg_lifetime_value'])*0.02, f'${val:,.0f}',
                    ha='center', fontweight='bold', fontsize=10)
        
        # 4. Segment Analysis Matrix
        ax4 = axes[1, 1]
        ax4.axis('off')
        
        # Create a summary table
        summary_data = []
        for _, row in df.iterrows():
            pct_customers = (row['customer_count'] / df['customer_count'].sum()) * 100
            pct_revenue = (row['segment_total_value'] / df['segment_total_value'].sum()) * 100
            summary_data.append([
                row['segment'],
                f"{int(row['customer_count']):,}",
                f"${row['avg_lifetime_value']:,.0f}",
                f"${row['segment_total_value']:,.0f}",
                f"{pct_customers:.1f}%",
                f"{pct_revenue:.1f}%"
            ])
        
        table = ax4.table(cellText=summary_data,
                         colLabels=['Segment', 'Customers', 'Avg LTV', 'Total Value', 
                                   '% Customers', '% Revenue'],
                         cellLoc='center', loc='center',
                         colWidths=[0.15, 0.15, 0.15, 0.15, 0.15, 0.15])
        table.auto_set_font_size(False)
        table.set_fontsize(10)
        table.scale(1, 2.5)
        
        # Color the header row
        for i in range(6):
            table[(0, i)].set_facecolor('#40466e')
            table[(0, i)].set_text_props(weight='bold', color='white')
        
        # Color data rows by segment
        for i, row_data in enumerate(summary_data, 1):
            seg_color = segment_colors.get(row_data[0], 'white')
            for j in range(6):
                table[(i, j)].set_facecolor(seg_color)
                table[(i, j)].set_alpha(0.3)
        
        ax4.set_title('Customer Segment Summary', fontsize=12, fontweight='bold', pad=20)
        
        plt.tight_layout()
        output_path = os.path.join(output_dir, '03_customer_segments_dashboard.png')
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"✓ Saved: {output_path}")
        plt.close()
        
    except Exception as e:
        logger.error(f"Error visualizing customer segments: {str(e)}")


# ============================================================================
# ARCHITECTURE COMPARISON
# ============================================================================

def compare_query_approaches():
    """
    Compare and contrast querying approaches across the three architectural components
    """
    print("\n" + "="*100)
    print("ARCHITECTURE COMPARISON: QUERY APPROACHES")
    print("="*100)
    
    comparison = {
        'RAW ZONE': {
            'Purpose': 'Data Lineage & Source Tracking',
            'Data Format': 'JSONB (Schema-less)',
            'Query Pattern': 'Document queries with JSON operators',
            'Typical Use': 'Auditing, debugging data quality issues',
            'Performance': '⚠ Slower (unstructured)',
            'Freshness': 'Real-time (source data)',
            'Example': 'Find all JSON records where customer_id = X'
        },
        'CURATED ZONE': {
            'Purpose': 'Refined, Business-Ready Data',
            'Data Format': 'Structured Tables (Refined)',
            'Query Pattern': 'Direct SQL joins on business entities',
            'Typical Use': 'Ad-hoc analysis, data validation',
            'Performance': '⚠ Medium (real-time calc)',
            'Freshness': 'Near real-time (calculated)',
            'Example': 'Sum orders by customer with quality filters'
        },
        'DATA WAREHOUSE': {
            'Purpose': 'Analytics & Reporting',
            'Data Format': 'Star Schema (Pre-aggregated)',
            'Query Pattern': 'Dimension-fact table joins',
            'Typical Use': 'Dashboards, BI reports, analytics',
            'Performance': '✓ Fast (pre-aggregated)',
            'Freshness': 'Batch (periodic refresh)',
            'Example': 'Revenue by region using fact table'
        }
    }
    
    for layer, details in comparison.items():
        print(f"\n{layer}")
        print("-" * 100)
        for key, value in details.items():
            print(f"  {key:<20} {value}")
    
    print("\n" + "="*100)
    print("RECOMMENDATIONS FOR EACH USE CASE:")
    print("="*100)
    print("""
  1. REAL-TIME OPERATIONAL QUERIES
     → Use: CURATED ZONE
     → Reason: Most current data, good balance of structure and freshness
     → Example: "How many orders from this customer today?"
  
  2. HISTORICAL ANALYSIS & TRENDING
     → Use: DATA WAREHOUSE
     → Reason: Pre-aggregated for speed, designed for time-series
     → Example: "Sales trends by region over the past year"
  
  3. DATA QUALITY & DEBUGGING
     → Use: RAW ZONE + CURATED ZONE
     → Reason: Compare source vs refined to identify transformations
     → Example: "Why did this record fail validation?"
  
  4. EXECUTIVE DASHBOARDS
     → Use: DATA WAREHOUSE
     → Reason: Fast queries, pre-aggregated metrics
     → Example: "Regional sales dashboard for C-level"
  
  5. COMPLEX TRANSFORMATIONS
     → Use: CURATED ZONE
     → Reason: Full data available, more flexible joins
     → Example: "Custom segmentation with multiple criteria"
    """)


# ============================================================================
# MAIN EXECUTION
# ============================================================================

def run_all_reports():
    """Execute all analytical queries and dashboards"""
    
    print("\n" + "█"*100)
    print("█" + " "*98 + "█")
    print("█" + "ANALYTICAL QUERIES & DASHBOARDS - DATA LAKE ARCHITECTURE".center(98) + "█")
    print("█" + " "*98 + "█")
    print("█"*100)
    
    engine = get_db_engine()
    
    # 1. Schema Comparison
    analyze_data_lineage()
    
    # 2. Analytical Queries
    query_sales_by_region_time(engine)
    query_product_performance(engine)
    query_customer_segments(engine)
    
    # 3. Dashboards
    dashboard_sales_regional(engine)
    dashboard_product_performance(engine)
    dashboard_customer_insights(engine)
    
    # 4. Visualizations with Matplotlib
    print("\n" + "="*100)
    print("GENERATING VISUALIZATIONS")
    print("="*100)
    print("\nCreating matplotlib charts...")
    visualize_sales_regional(engine)
    visualize_product_performance(engine)
    visualize_customer_segments(engine)
    print("✓ All visualizations completed!")
    
    # 5. Architecture Comparison
    compare_query_approaches()
    
    print("\n" + "█"*100)
    print("█" + " "*98 + "█")
    print("█" + "✓ ALL REPORTS AND VISUALIZATIONS GENERATED SUCCESSFULLY".center(98) + "█")
    print("█" + " "*98 + "█")
    print("█"*100 + "\n")


def main():
    """Main entry point"""
    try:
        run_all_reports()
    except Exception as e:
        logger.error(f"❌ Error in main: {str(e)}")
        raise
