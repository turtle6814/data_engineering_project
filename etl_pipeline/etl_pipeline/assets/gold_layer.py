import pandas as pd
from dagster import (
    asset,
    Output,
    AssetIn,
    AssetExecutionContext,
)

@asset(
    name="gold_sales_values_by_category",
    key_prefix=["gold", "ecom"],
    ins={
        "silver_dim_products": AssetIn(key_prefix=["silver", "ecom"]),
        "silver_fact_sales": AssetIn(key_prefix=["silver", "ecom"]),
    },
    io_manager_key="minio_io_manager",
    compute_kind="Pandas",
)

def sales_values_by_category(context: AssetExecutionContext, silver_dim_products: pd.DataFrame, silver_fact_sales: pd.DataFrame) -> Output[pd.DataFrame]:
    """
    Create gold layer aggregation of sales values by product category and month.
    """
    
    delivered_sales = silver_fact_sales[silver_fact_sales['order_status'] == 'delivered'].copy()
    
    if not pd.api.types.is_datetime64_any_dtype(delivered_sales['order_purchase_timestamp']):
        delivered_sales['order_purchase_timestamp'] = pd.to_datetime(delivered_sales['order_purchase_timestamp'])
    
    delivered_sales['daily'] = delivered_sales['order_purchase_timestamp'].dt.date
    
    daily_sales_products = (
        delivered_sales
        .groupby(['daily', 'product_id'])
        .agg(
            sales=('payment_value', lambda x: round(sum(x.astype(float)), 2)),
            bills=('order_id', lambda x: len(set(x)))
        )
        .reset_index()
    )
    
    daily_sales_categories = daily_sales_products.merge(
        silver_dim_products,
        on='product_id',
        how='inner'
    )
    
    daily_sales_categories['monthly'] = daily_sales_categories['daily'].apply(
        lambda x: pd.to_datetime(x).strftime('%Y-%m')
    )
    
    daily_sales_categories.rename(columns={'product_category_name_english': 'category'}, inplace=True)
    
    daily_sales_categories['values_per_bills'] = daily_sales_categories['sales'] / daily_sales_categories['bills']
    
    sales_by_category = (
        daily_sales_categories
        .groupby(['monthly', 'category'])
        .agg(
            total_sales=('sales', 'sum'),
            total_bills=('bills', 'sum')
        )
        .reset_index()
    )
    
    sales_by_category['values_per_bills'] = sales_by_category['total_sales'] / sales_by_category['total_bills']    
    sales_by_category = sales_by_category.fillna(0)
    
    return Output(
        sales_by_category,
        metadata={
            "table": "sales_values_by_category",
            "records count": len(sales_by_category),
            "schema": "ecom",
            "storage": "MinIO",
            "path": "gold/ecom/sales_values_by_category",
        },
    )

@asset(
    name="sales_values_by_category",
    key_prefix=["warehouse", "gold"],
    ins={
        "gold_sales_values_by_category": AssetIn(key_prefix=["gold", "ecom"]),
    },
    io_manager_key="psql_io_manager",
    compute_kind="PostgreSQL",
)

def load_sales_values_to_postgresql(context: AssetExecutionContext, gold_sales_values_by_category: pd.DataFrame) -> Output[pd.DataFrame]:
    """
    Load gold layer data from MinIO into PostgreSQL as WareHouse Layer
    """

    df = gold_sales_values_by_category.copy()
    
    column_mapping = {
        'monthly': 'monthly',
        'category': 'category',
        'total_sales': 'sales',
        'total_bills': 'bills',
        'values_per_bills': 'values_per_bill'
    }
    
    df = df.rename(columns=column_mapping)
    
    required_columns = ['monthly', 'category', 'sales', 'bills', 'values_per_bill']
    df = df[required_columns]
    
    df['category'] = df['category'].str.strip()
    
    return Output(
        df,
        metadata={
            "table": "gold.sales_values_by_category",
            "records count": len(df),
            "schema": "gold",
            "storage": "PostgreSQL",
        },
    )