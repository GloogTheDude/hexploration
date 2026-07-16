from fastapi import FastAPI
from routes.map_routes import router as map_router
from fastapi.staticfiles import StaticFiles



app = FastAPI()

app.include_router(map_router)
app.mount("/", StaticFiles(directory="static", html=True), name="static")