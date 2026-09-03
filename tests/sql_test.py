import duckdb
import pandas as pd
import pytest

from inline_sql import sql, sql_val


def test_basic_math():
    assert sql_val^ "SELECT 1 + 2" == 3  # fmt: skip
    assert sql_val^ "SELECT 1234567 * 2" == 2469134  # fmt: skip
    assert sql_val^ "SELECT POW(x, 2) FROM (SELECT 5 AS x)" == 25  # fmt: skip


def test_val_cardinality():
    assert sql_val^ "SELECT 1 WHERE 1 = 0" is None  # fmt: skip

    with pytest.raises(RuntimeError) as exc:
        sql_val^ "SELECT 1 UNION SELECT 2"  # fmt: skip
    assert "more than one row" in str(exc.value)

    with pytest.raises(RuntimeError) as exc:
        sql_val^ "SELECT 1 AS x, 2 AS y"  # fmt: skip
    assert "more than one column" in str(exc.value)


def test_invalid_query():
    with pytest.raises(ValueError):
        sql^ "INSERT INTO foo VALUES (1, 2)"  # fmt: skip
    with pytest.raises(ValueError):
        sql^ "SELECT 1; SELECT 2"  # fmt: skip
    with pytest.raises(NameError):
        sql^ "SELECT $x"  # fmt: skip
    with pytest.raises(duckdb.ParserException):
        sql^ "SELECT SELECT"  # fmt: skip


def test_query_df():
    df = sql^ "SELECT 1 AS x, 2 AS y"  # fmt: skip
    assert df.shape == (1, 2)
    assert df.iloc[0, 0] == 1
    assert df.iloc[0, 1] == 2
    assert list(df.columns) == ["x", "y"]


def test_params():
    x, y = 5, 6
    assert sql_val^ "SELECT $x + $y" == 11  # fmt: skip
    assert sql_val^ "SELECT $y + $x" == 11  # fmt: skip
    assert sql_val^ "SELECT $x + $x" == 10  # fmt: skip
    assert sql_val^ "SELECT $x + $x + $x" == 15  # fmt: skip
    assert sql_val^ "SELECT $x + $x + $x + $x" == 20  # fmt: skip


def test_inline_df():
    df = pd.DataFrame({"x": [1, 2, 3], "y": [4, 2, 2]})
    assert len(sql^ "SELECT * FROM df") == 3  # fmt: skip
    assert len(sql^ "SELECT * FROM df a, df b WHERE a.x = b.y") == 2  # fmt: skip
    limit = 2
    assert sql_val^ "SELECT COUNT() FROM df WHERE x <= $limit" == 2  # fmt: skip
    assert sql_val^ """
        SELECT COUNT() FROM (
            SELECT * FROM df a
            LEFT JOIN df b ON a.x = b.y
            LEFT JOIN df c ON b.x = c.y
        )
    """ == 5  # fmt: skip


def test_inline_df_with_string_dtype():
    df = pd.DataFrame({"label": pd.Series(["alpha", "beta"], dtype="string")})
    assert sql_val^ "SELECT COUNT() FROM df WHERE label = 'alpha'" == 1  # fmt: skip


def test_unreferenced_dataframe_is_not_registered():
    unused = pd.DataFrame({"value": [1 + 2j]})
    assert sql_val^ "SELECT 1" == 1  # fmt: skip


@pytest.mark.parametrize(
    "query",
    [
        "SELECT COUNT() FROM df",
        "SELECT COUNT() FROM DF",
        'SELECT COUNT() FROM "df"',
    ],
)
def test_inline_df_name_matching(query):
    df = pd.DataFrame({"x": [1, 2, 3]})
    assert sql_val^ query == 3  # fmt: skip


def test_registers_each_joined_dataframe():
    left_df = pd.DataFrame({"x": [1, 2]})
    right_df = pd.DataFrame({"x": [2, 3]})
    assert sql_val^ """
        SELECT COUNT()
        FROM left_df
        JOIN right_df USING (x)
    """ == 1  # fmt: skip


def test_dataframe_name_matching_prefers_exact_case():
    df = pd.DataFrame({"x": [1]})
    DF = pd.DataFrame({"x": [1, 2]})
    assert sql_val^ "SELECT COUNT() FROM df" == 1  # fmt: skip
    assert sql_val^ "SELECT COUNT() FROM DF" == 2  # fmt: skip


def test_column_name_does_not_register_dataframe():
    price = pd.DataFrame({"unsupported": [1 + 2j]})
    purchases = pd.DataFrame({"price": [10, 20]})
    assert sql_val^ "SELECT SUM(price) FROM purchases" == 30  # fmt: skip


def test_cte_name_does_not_register_dataframe():
    df = pd.DataFrame({"unsupported": [1 + 2j]})
    assert sql_val^ "WITH df AS (SELECT 1 AS x) SELECT x FROM df" == 1  # fmt: skip


def test_registration_fallback_for_parameterized_table_function():
    df = pd.DataFrame({"x": [1]})
    path = "tests/data/weather.csv"
    assert sql_val^ "SELECT COUNT() FROM df, read_csv_auto($path)" == 1461  # fmt: skip


def test_implicit_select_all():
    result = sql^ "FROM range(3)"  # fmt: skip
    assert result["range"].tolist() == [0, 1, 2]


def test_implicit_select_from_dataframe_with_parameter():
    df = pd.DataFrame({"x": [1, 2, 3]})
    minimum = 1
    result = sql^ "FROM df WHERE x > $minimum"  # fmt: skip
    assert result["x"].tolist() == [2, 3]


def test_from_first_with_explicit_select():
    df = pd.DataFrame({"x": [1, 2, 3]})
    result = sql^ "FROM df SELECT x * 2 AS doubled"  # fmt: skip
    assert result["doubled"].tolist() == [2, 4, 6]


def test_from_first_scalar_query():
    assert sql_val^ "FROM range(5) SELECT COUNT(*)" == 5  # fmt: skip


def test_implicit_select_with_leading_comment():
    result = sql^ """
        -- Return every generated row.
        FROM range(2)
    """  # fmt: skip
    assert result["range"].tolist() == [0, 1]


@pytest.mark.parametrize(
    "query",
    [
        "UPDATE items SET value = 1",
        "DELETE FROM items",
    ],
)
def test_implicit_select_does_not_allow_mutations(query):
    with pytest.raises(ValueError, match="Only SELECT statements are supported"):
        sql^ query  # fmt: skip


def test_implicit_select_does_not_allow_multiple_statements():
    with pytest.raises(ValueError, match="Only one SQL statement is allowed"):
        sql^ "FROM range(1); DELETE FROM items"  # fmt: skip
