import pandas as pd
from dagster import (
    asset,
    Output,
    AssetIn,
)

@asset(
    name="silver_dim_products",
    key_prefix=["silver", "ecom"],
    ins={
        "bronze_olist_products_dataset": AssetIn(key_prefix=["bronze", "ecom"]),
        "bronze_product_category_name_translation": AssetIn(key_prefix=["bronze", "ecom"]),
    },
    io_manager_key="minio_io_manager",
    compute_kind="Pandas",
)
def dim_products(
    bronze_olist_products_dataset: pd.DataFrame,
    bronze_product_category_name_translation: pd.DataFrame,
) -> Output[pd.DataFrame]:
    """Create dimension table for products with English category names."""
    
    dim_products_df = bronze_olist_products_dataset.merge(
        bronze_product_category_name_translation,
        on="product_category_name",
        how="inner"
    )
    
    dim_products_df = dim_products_df[[
        "product_id", 
        "product_category_name_english"
    ]]
    
    return Output(
        dim_products_df,
        metadata={
            "table": "dim_products",
            "records count": len(dim_products_df),
            "schema": "ecom",
        },
    )

@asset(
    name="silver_fact_sales",
    key_prefix=["silver", "ecom"],
    ins={
        "bronze_olist_orders_dataset": AssetIn(key_prefix=["bronze", "ecom"]),
        "bronze_olist_order_items_dataset": AssetIn(key_prefix=["bronze", "ecom"]),
        "bronze_olist_order_payments_dataset": AssetIn(key_prefix=["bronze", "ecom"]),
    },
    io_manager_key="minio_io_manager",
    compute_kind="Pandas",
)
def fact_sales(
    bronze_olist_orders_dataset: pd.DataFrame,
    bronze_olist_order_items_dataset: pd.DataFrame,
    bronze_olist_order_payments_dataset: pd.DataFrame,
) -> Output[pd.DataFrame]:
    """Create fact table for sales combining orders, items, and payments."""
    
    fact_sales_df = bronze_olist_orders_dataset.merge(
        bronze_olist_order_items_dataset,
        on="order_id",
        how="inner"
    )
    
    fact_sales_df = fact_sales_df.merge(
        bronze_olist_order_payments_dataset,
        on="order_id",
        how="inner"
    )
    
    fact_sales_df = fact_sales_df[[
        "order_id",
        "customer_id",
        "order_purchase_timestamp",
        "product_id",
        "payment_value",
        "order_status"
    ]]
    
    return Output(
        fact_sales_df,
        metadata={
            "table": "fact_sales",
            "records count": len(fact_sales_df),
            "schema": "ecom",
        },
    )