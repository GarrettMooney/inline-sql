from typing import Any

import duckdb
import pandas as pd
import sqlparse


def prepare_query(query: str) -> tuple[str, list[str], str, set[str]]:
    """Prepare a query and its table-discovery fallback."""
    statements = sqlparse.parse(query)
    if len(statements) != 1:
        raise ValueError("Only one SQL statement is allowed.")
    statement: sqlparse.sql.Statement = statements[0]
    first_token = statement.token_first(skip_ws=True, skip_cm=True)
    is_from_first = (
        first_token is not None
        and first_token.ttype in sqlparse.tokens.Keyword
        and first_token.normalized == "FROM"
    )
    if statement.get_type() != "SELECT" and not is_from_first:
        raise ValueError("Only SELECT statements are supported.")
    new_tokens: list[str] = []
    discovery_tokens: list[str] = []
    params_map: dict[str, int] = {}
    identifiers: set[str] = set()
    for token in statement.flatten():
        if token.ttype in sqlparse.tokens.Name.Placeholder:
            index = params_map.setdefault(token.value, len(params_map))
            new_tokens.append("?" + str(index + 1))
            discovery_tokens.append("NULL")
            continue

        token_value = str(token)
        new_tokens.append(token_value)
        discovery_tokens.append(token_value)
        if (
            token.ttype in sqlparse.tokens.Name
            or token.ttype in sqlparse.tokens.Keyword
        ):
            identifiers.add(token_value)
        elif token.ttype in sqlparse.tokens.Literal.String.Symbol:
            identifier = token_value[1:-1].replace('""', '"')
            identifiers.add(identifier)

    params_list = [k[1:] for _, k in sorted((v, k) for k, v in params_map.items())]
    return "".join(new_tokens), params_list, "".join(discovery_tokens), identifiers


def run_query(query: str, context: dict[str, Any]) -> pd.DataFrame:
    """Run a SQL query against an in-memory DuckDB database."""
    new_query, params_list, discovery_query, identifiers = prepare_query(query)
    for name in params_list:
        if name not in context:
            raise NameError(f"name {name!r} is not defined")
    con = duckdb.connect()
    dataframes = {
        name: value
        for name, value in context.items()
        if isinstance(value, pd.DataFrame)
    }
    table_names: set[str] = set()
    if dataframes:
        try:
            table_names = con.get_table_names(discovery_query)
        except duckdb.Error:
            table_names = identifiers

    registered_names: set[str] = set()
    for identifier in table_names:
        if identifier in dataframes:
            con.register(identifier, dataframes[identifier])
            registered_names.add(identifier)
            continue

        matches = [
            name
            for name in dataframes
            if name not in registered_names and name.casefold() == identifier.casefold()
        ]
        if len(matches) == 1:
            name = matches[0]
            con.register(name, dataframes[name])
            registered_names.add(name)
    con.execute(new_query, parameters=[context[k] for k in params_list])
    return con.fetchdf()
