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


def test_implicit_select_parsing():
    from inline_sql._src.runtime import prepare_query

    # FROM-first queries should be accepted by prepare_query
    query, params = prepare_query("FROM range(5)")
    assert query == "FROM range(5)"
    assert params == []

    # FROM-first with params
    query, params = prepare_query("FROM range(5) WHERE range > $n")
    assert "?1" in query
    assert params == ["n"]

    # Non-SELECT, non-FROM statements still rejected
    with pytest.raises(ValueError):
        prepare_query("INSERT INTO foo VALUES (1)")
    with pytest.raises(ValueError):
        prepare_query("DELETE FROM foo")


def test_implicit_select_execution():
    # FROM-first with subquery (no DataFrame dependency)
    result = sql^ "FROM (SELECT 1 AS x, 2 AS y UNION ALL SELECT 3, 4)"  # fmt: skip
    assert len(result) == 2
    assert list(result.columns) == ["x", "y"]

    # FROM-first with range function
    result = sql^ "FROM range(3)"  # fmt: skip
    assert len(result) == 3

    # FROM-first scalar
    assert sql_val^ "SELECT COUNT(*) FROM range(5)" == 5  # fmt: skip

    # FROM-first with params
    n = 3
    result = sql^ "FROM range(10) WHERE range < $n"  # fmt: skip
    assert len(result) == 3


def test_inline_df():
    df = pd.DataFrame({"x": [1, 2, 3], "y": [4, 2, 2]})
    assert len(sql^ "SELECT * FROM df") == 3  # fmt: skip
    assert len(sql^ "SELECT * FROM df a, df b WHERE a.x = b.y") == 2  # fmt: skip
    assert sql_val^ """
        SELECT COUNT() FROM (
            SELECT * FROM df a
            LEFT JOIN df b ON a.x = b.y
            LEFT JOIN df c ON b.x = c.y
        )
    """ == 5  # fmt: skip
