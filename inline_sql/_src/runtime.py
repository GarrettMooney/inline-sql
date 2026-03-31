from typing import Any

import duckdb
import pandas as pd
import sqlparse


def prepare_query(query: str) -> tuple[str, list[str]]:
    """Prepare a query, replacing all placeholders with numbered parameters."""
    statements = sqlparse.parse(query)
    if len(statements) != 1:
        raise ValueError("Only one SQL statement is allowed.")
    statement: sqlparse.sql.Statement = statements[0]
    if statement.get_type() != "SELECT":
        raise ValueError("Only SELECT statements are supported.")
    new_tokens: list[str] = []
    params_map: dict[str, int] = {}
    for token in statement.flatten():
        if token.ttype in sqlparse.tokens.Name.Placeholder:
            index = params_map.setdefault(token.value, len(params_map))
            new_tokens.append("?" + str(index + 1))
        else:
            new_tokens.append(str(token))
    params_list = [k[1:] for _, k in sorted((v, k) for k, v in params_map.items())]
    return "".join(new_tokens), params_list


def run_query(query: str, context: dict[str, Any]) -> pd.DataFrame:
    """Run a SQL query against an in-memory DuckDB database."""
    new_query, params_list = prepare_query(query)
    for name in params_list:
        if name not in context:
            raise NameError(f"name {name!r} is not defined")
    con = duckdb.connect()
    for name, value in context.items():
        if isinstance(value, pd.DataFrame):
            con.register(name, value)
    con.execute(new_query, parameters=[context[k] for k in params_list])
    return con.fetchdf()
