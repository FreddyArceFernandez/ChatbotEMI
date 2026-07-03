from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from admin.backend.database import SessionLocal, engine
from admin.backend.models import PreguntaFrecuente, Base
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

# Crea tablas si no existen
Base.metadata.create_all(bind=engine)

app = FastAPI()

# Permitir acceso desde el frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # o ["http://localhost:3000"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Esquemas de Pydantic
class PreguntaSchema(BaseModel):
    pregunta: str
    respuesta: str

class PreguntaOut(PreguntaSchema):
    id_pregunta: int

    class Config:
        orm_mode = True

# Dependencia de DB
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Endpoints CRUD
@app.get("/preguntas", response_model=list[PreguntaOut])
def listar_preguntas(db: Session = Depends(get_db)):
    return db.query(PreguntaFrecuente).all()

@app.post("/preguntas", response_model=PreguntaOut)
def agregar_pregunta(pregunta: PreguntaSchema, db: Session = Depends(get_db)):
    nueva = PreguntaFrecuente(**pregunta.dict())
    db.add(nueva)
    db.commit()
    db.refresh(nueva)
    return nueva

@app.put("/preguntas/{id_pregunta}", response_model=PreguntaOut)
def actualizar_pregunta(id_pregunta: int, nueva_data: PreguntaSchema, db: Session = Depends(get_db)):
    pregunta = db.query(PreguntaFrecuente).filter_by(id_pregunta=id_pregunta).first()
    if not pregunta:
        raise HTTPException(status_code=404, detail="Pregunta no encontrada")
    pregunta.pregunta = nueva_data.pregunta
    pregunta.respuesta = nueva_data.respuesta
    db.commit()
    return pregunta

@app.delete("/preguntas/{id_pregunta}")
def eliminar_pregunta(id_pregunta: int, db: Session = Depends(get_db)):
    pregunta = db.query(PreguntaFrecuente).filter_by(id_pregunta=id_pregunta).first()
    if not pregunta:
        raise HTTPException(status_code=404, detail="Pregunta no encontrada")
    db.delete(pregunta)
    db.commit()
    return {"ok": True}
