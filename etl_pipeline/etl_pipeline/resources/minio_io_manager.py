import os
from contextlib import contextmanager
from datetime import datetime
from typing import Union
import tempfile # Using Windows compatibility

import pandas as pd
from dagster import IOManager, OutputContext, InputContext
from minio import Minio


@contextmanager
def connect_minio(config):
    client = Minio(
        endpoint=config.get("endpoint_url"),
        access_key=config.get("aws_access_key_id"),
        secret_key=config.get("aws_secret_access_key"),
        secure=False,
    )
    try:
        yield client
    except Exception:
        raise


class MinIOIOManager(IOManager):
    def __init__(self, config):
        self._config = config

    def _get_path(self, context: Union[InputContext, OutputContext]):
        layer, schema, table = context.asset_key.path
        key = "/".join([layer, schema, table.replace(f"{layer}_", "")])

        # Use tempfile to get a proper temporary file path (Windows compatibility)
        tmp_dir = tempfile.gettempdir()
        tmp_file_name = "file-{}-{}.parquet".format(
            datetime.today().strftime("%Y%m%d%H%M%S"),
            "-".join(context.asset_key.path)
        )
        tmp_file_path = os.path.join(tmp_dir, tmp_file_name)
        
        return f"{key}.pq", tmp_file_path

    def handle_output(self, context: OutputContext, obj: pd.DataFrame):
        key_name, tmp_file_path = self._get_path(context)
        try:
            # Convert DataFrame to parquet format
            obj.to_parquet(tmp_file_path)

            # Upload to MinIO
            with connect_minio(self._config) as client:
                client.fput_object(
                    bucket_name="warehouse",
                    object_name=key_name,
                    file_path=tmp_file_path
                )

            # Clean up tmp file
            os.remove(tmp_file_path)
        except Exception:
            if os.path.exists(tmp_file_path):
                os.remove(tmp_file_path)
            raise

    def load_input(self, context: InputContext) -> pd.DataFrame:
        key_name, tmp_file_path = self._get_path(context)
        try:
            with connect_minio(self._config) as client:
                # Download file from MinIO
                client.fget_object(
                    bucket_name="warehouse",
                    object_name=key_name,
                    file_path=tmp_file_path
                )
                # Read parquet file into DataFrame
                df = pd.read_parquet(tmp_file_path)
                return df
        except Exception:
            if os.path.exists(tmp_file_path):
                os.remove(tmp_file_path)
            raise
        finally:
            if os.path.exists(tmp_file_path):
                os.remove(tmp_file_path)