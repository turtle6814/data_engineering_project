from contextlib import contextmanager
import pandas as pd
from dagster import IOManager, OutputContext, InputContext
from sqlalchemy import create_engine, text


@contextmanager
def connect_psql(config):
    conn_info = (
        f"postgresql+psycopg2://{config['user']}:{config['password']}"
        + f"@{config['host']}:{config['port']}"
        + f"/{config['database']}"
    )
    db_conn = create_engine(conn_info)
    try:
        yield db_conn
    except Exception:
        raise


class PostgreSQLIOManager(IOManager):
    def __init__(self, config):
        self._config = config

    def load_input(self, context: InputContext) -> pd.DataFrame:
        schema, table = context.asset_key.path[-2], context.asset_key.path[-1]
        with connect_psql(self._config) as conn:
            sql = f"SELECT * FROM {schema}.{table}"
            return pd.read_sql(sql, conn)

    def handle_output(self, context: OutputContext, obj: pd.DataFrame):
        schema, table = context.asset_key.path[-2], context.asset_key.path[-1]
        with connect_psql(self._config) as conn:
            # Create schema if it doesn't exist using proper connection
            with conn.connect() as connection:
                connection.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema}"))
                connection.commit()
            
            # Write DataFrame to PostgreSQL
            obj.to_sql(
                name=table,
                schema=schema,
                con=conn,
                if_exists="replace",
                index=False
            )