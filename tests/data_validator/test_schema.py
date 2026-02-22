import awswrangler as wr
import pytest

from mlops.const import GLUE_DATABASE
from mlops.data_validator import IMPRESSION_LOG_SCHEMA, MST_ITEM_SCHEMA, VIEW_LOG_SCHEMA


@pytest.mark.integration # このテストを「統合テスト」としてマーキングしています。DB接続を伴う重いテストだけを切り分けて実行する際に役立ちます。
@pytest.mark.parametrize( #「パラメータ化テスト」**です。1つのテスト関数で、3種類のスキーマ（インプレッション、閲覧、商品マスタ）を順番に入れ替えて3回実行
    "schema", [IMPRESSION_LOG_SCHEMA, VIEW_LOG_SCHEMA, MST_ITEM_SCHEMA], ids=["impression_log", "view_log", "mst_item"]
)
def test_schema_validation(schema):
    sql = f"SELECT * FROM {schema.name} LIMIT 10"

    df = wr.athena.read_sql_query(sql, database=GLUE_DATABASE, ctas_approach=False)

    assert len(df) > 0, "No data retrieved"
    validated_df = schema.validate(df)
    assert len(validated_df) == len(df), "Row count changed after validation"
