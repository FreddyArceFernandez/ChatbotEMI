from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any
from . import crud

app = FastAPI()

# Permitir conexión desde frontend local
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Cambia esto en producción
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MODELOS DE DATOS
class RowData(BaseModel):
    data: Dict[str, Any]

class UpdateData(BaseModel):
    id_column: str
    id_value: int
    data: Dict[str, Any]

class TableColumn(BaseModel):
    name: str
    type: str

class NewTable(BaseModel):
    table_name: str
    columns: List[TableColumn]

# ENDPOINTS

@app.get("/tables")
def list_tables():
    return crud.get_all_tables()

@app.get("/tables/{table_name}/columns")
def get_columns(table_name: str):
    return crud.get_table_columns(table_name)

@app.get("/tables/{table_name}/data")
def get_data(table_name: str):
    return crud.get_table_data(table_name)

@app.post("/tables/{table_name}/insert")
def insert_row(table_name: str, row: RowData):
    crud.insert_data(table_name, row.data)
    return {"message": "Insertado correctamente"}

@app.put("/tables/{table_name}/update")
def update_row(table_name: str, row: UpdateData):
    crud.update_data(table_name, row.id_column, row.id_value, row.data)
    return {"message": "Actualizado correctamente"}

@app.delete("/tables/{table_name}/delete")
def delete_row(table_name: str, id_column: str, id_value: int):
    crud.delete_data(table_name, id_column, id_value)
    return {"message": "Eliminado correctamente"}

@app.post("/tables/create")
def create_new_table(table: NewTable):
    crud.create_table(table.table_name, table.columns)
    return {"message": f"Tabla '{table.table_name}' creada correctamente"}
