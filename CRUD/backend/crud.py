from sqlalchemy import text
from .database import engine, SessionLocal

def get_all_tables():
    query = "SHOW TABLES"
    with engine.connect() as conn:
        result = conn.execute(text(query))
        return [row[0] for row in result]

def get_table_columns(table_name: str):
    query = f"DESCRIBE {table_name}"
    with engine.connect() as conn:
        result = conn.execute(text(query))
        return [dict(row._mapping) for row in result]

def get_table_data(table_name: str):
    query = f"SELECT * FROM {table_name} LIMIT 100"
    with engine.connect() as conn:
        result = conn.execute(text(query))
        columns = result.keys()
        return [dict(zip(columns, row)) for row in result]

def insert_data(table_name: str, data: dict):
    keys = ", ".join(data.keys())
    values = ", ".join([f":{key}" for key in data.keys()])
    query = text(f"INSERT INTO {table_name} ({keys}) VALUES ({values})")
    with engine.begin() as conn:
        conn.execute(query, data)

def update_data(table_name: str, id_column: str, id_value: int, data: dict):
    set_clause = ", ".join([f"{k} = :{k}" for k in data.keys()])
    data["id_value"] = id_value
    query = text(f"UPDATE {table_name} SET {set_clause} WHERE {id_column} = :id_value")
    with engine.begin() as conn:
        conn.execute(query, data)

def delete_data(table_name: str, id_column: str, id_value: int):
    query = text(f"DELETE FROM {table_name} WHERE {id_column} = :id_value")
    with engine.begin() as conn:
        conn.execute(query, {"id_value": id_value})

def create_table(table_name: str, columns: list):
    """
    columns: [{"name": "nombre", "type": "VARCHAR(255)"}, ...]
    """
    columns_sql = ", ".join([f"{col['name']} {col['type']}" for col in columns])
    query = text(f"CREATE TABLE {table_name} (id INT AUTO_INCREMENT PRIMARY KEY, {columns_sql})")
    with engine.begin() as conn:
        conn.execute(query)
