import re
from typing import Any, Callable
from pydantic.types import T
from sqlalchemy import text


def _resolve_table_name(table: Any) -> str:
    """Extract a string table name from various descriptor types."""

    if isinstance(table, str):
        return table

    for attr in ("table_name", "__tablename__", "name"):
        if hasattr(table, attr):
            value = getattr(table, attr)
            if isinstance(value, str):
                return value
            if callable(value):
                resolved = value()
                if isinstance(resolved, str):
                    return resolved

    raise TypeError("table must be a string or expose a table_name/name attribute")


class sql:
    """
    A class to handle SQL queries using a connection and query string.
    It can be used to execute SQL commands with parameters.
    """

    def __init__(self, connection, query=None, params=None):
        self.connection = connection
        self.query = query
        self.params = params or {}

    def run(self):
        return self.connection.execute(text(self.query), self.params)

    def dicts(self):
        result = self.connection.execute(text(self.query), self.params).mappings().all()
        return result

    def dict(self):
        """
        Returns the first row of the result as a dictionary.
        """
        result = (
            self.connection.execute(text(self.query), self.params).mappings().first()
        )
        return dict(result) if result else None

    def insert_one(self, table, data):
        """
        Inserts a single record into the specified table.
        :param table: The name of the table to insert into or a table descriptor.
        :param data: A dictionary of column names and values to insert.
        """
        table_name = _resolve_table_name(table)
        columns = ", ".join(data.keys())
        placeholders = ", ".join(f":{key}" for key in data.keys())
        query = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"
        self.connection.execute(text(query), data)
    
    def insert_many(self, table, data_list: list[dict]):
        """
        Inserts multiple records into the specified table.
        :param table: Table name
        :param data_list: List of dictionaries
        """

        table_name = _resolve_table_name(table)

        columns = ", ".join(data_list[0].keys())
        placeholders = ", ".join(f":{key}" for key in data_list[0].keys())

        query = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"

        self.connection.execute(text(query), data_list)
    
    def _build_set_clause(self, data: dict) -> str:
        if not data:
            raise ValueError("No fields provided for update")
        return ", ".join([f"{key} = :{key}" for key in data.keys()])

    def _build_where_clause(self, filters: dict) -> str:
        if not filters:
            raise ValueError("WHERE condition required for update")

        return " AND ".join(
            [f"{key} = :filter_{key}" for key in filters.keys()]
        )

    def update_one(self, table: str, data: dict, filters: dict, updated_by: str = None):
        table_name = _resolve_table_name(table)

        data = data.model_dump(exclude_none=True) if hasattr(data, "model_dump") else data

        if updated_by:
            data["updated_by"] = updated_by

        set_clause = self._build_set_clause(data)
        where_clause = self._build_where_clause(filters)

        query = f"""
            UPDATE {table_name}
            SET {set_clause}
            WHERE {where_clause}
        """
        params = {
            **data,
            **{f"filter_{k}": v for k, v in filters.items()}
        }
        self.connection.execute(text(query), params)
    

    def update_many(self, table, data_list: list[dict], filters_keys: list[str], updated_by: str = None):
        if not data_list:
            return

        table_name = _resolve_table_name(table)

        # add updated_by if needed
        if updated_by:
            for d in data_list:
                d["updated_by"] = updated_by

        # columns to update (exclude filter keys)
        update_keys = [
            key for key in data_list[0].keys()
            if key not in filters_keys
        ]

        set_clause = ", ".join(f"{k}=:{k}" for k in update_keys)
        where_clause = " AND ".join(f"{k}=:{k}" for k in filters_keys)

        query = f"""
            UPDATE {table_name}
            SET {set_clause}
            WHERE {where_clause}
        """

        self.connection.execute(text(query), data_list)
    
    def update_where_in(self, table: str, data: dict, filter_key: str, subquery: str, subquery_params: dict = {}, updated_by: str = None):
        table_name = _resolve_table_name(table)

        if updated_by:
            data["updated_by"] = updated_by

        set_clause = self._build_set_clause(data)

        query = f"""
            UPDATE {table_name}
            SET {set_clause}
            WHERE {filter_key} IN ({subquery})
        """

        params = {**data, **subquery_params}
        self.connection.execute(text(query), params)