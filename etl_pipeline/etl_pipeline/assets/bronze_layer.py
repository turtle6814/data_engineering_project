import pandas as pd
from dagster import (
    asset,
    Output,
    AssetExecutionContext
)


ls_tables = [
    "olist_order_items_dataset",
    "olist_order_payments_dataset",
    "olist_orders_dataset",
    "olist_products_dataset",
    "product_category_name_translation",
]

# Dynamic asset generation for all tables in the list
def generate_bronze_assets():
    """Generate bronze layer assets for all tables in ls_tables."""
    assets_list = []
    
    for table_name in ls_tables:
        assets_list.append(create_bronze_asset(table_name))
    
    return assets_list


def create_bronze_asset(table_name):
    @asset(
        name=f"bronze_{table_name}",
        io_manager_key="minio_io_manager",
        required_resource_keys={"mysql_io_manager"},
        key_prefix=["bronze", "ecom"],
        compute_kind="MySQL",
    )
    def _bronze_table_asset(context: AssetExecutionContext) -> Output[pd.DataFrame]:
        
        sql_stm = f"SELECT * FROM {table_name}"
        pd_data = context.resources.mysql_io_manager.extract_data(sql_stm)
        
        return Output(
            pd_data,
            metadata={
                "table": table_name,
                "source_table": table_name,
                "records count": len(pd_data),
                "schema": "ecom",
            },
        )
    
    _bronze_table_asset.__name__ = f"bronze_{table_name}"
    return _bronze_table_asset

bronze_assets = generate_bronze_assets()
