from fastapi import FastAPI
from consultes import router as router_consultes
from fastapi.staticfiles import StaticFiles

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

# Incluir las rutas de consultes.py
app.include_router(router_consultes)

@app.get("/")
def home():
    return {"mensaje": "API de PetMatch funcionando correctamente"}
