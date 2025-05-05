from dagster import Definitions, load_assets_from_modules

from etl_pipeline.assets import bronze_layer, silver_layer, gold_layer
from etl_pipeline.resources.mysql_io_manager import MySQLIOManager
from etl_pipeline.resources.minio_io_manager import MinIOIOManager
from etl_pipeline.resources.psql_io_manager import PostgreSQLIOManager

all_assets = load_assets_from_modules([bronze_layer, silver_layer, gold_layer])

MYSQL_CONFIG = {
    "host": "de_mysql",
    "port": 3306,
    "database": "brazillian_ecommerce",
    "user": "admin",
    "password": "admin123",
}

MINIO_CONFIG = {
    "endpoint_url": "minio:9000",
    "bucket": "warehouse",
    "aws_access_key_id": "minio",
    "aws_secret_access_key": "minio123",
}

PSQL_CONFIG = {
    "host": "de_psql",
    "port": 5432,
    "database": "postgres",
    "user": "admin",
    "password": "admin123",
}

defs = Definitions(
    assets=all_assets,
    resources={
        "mysql_io_manager": MySQLIOManager(MYSQL_CONFIG),
        "minio_io_manager": MinIOIOManager(MINIO_CONFIG),
        "psql_io_manager": PostgreSQLIOManager(PSQL_CONFIG),
    },
)