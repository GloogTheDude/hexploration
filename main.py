from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from routes.map_routes import router as map_router
from routes.health_routes import router as health_router
from routes.user_routes import router as user_router
from routes.campaign_routes import router as campaign_router
from routes.character_routes import router as character_router
from routes.character_sheet_routes import router as character_sheet_router
from routes.expedition_routes import router as expedition_router
from routes.movement_routes import router as movement_router
from routes.movement_modifier_routes import router as movement_modifier_router
from routes.world_event_routes import router as world_event_router
from routes.map_edge_routes import router as map_edge_router
from routes.poi_routes import router as poi_router


app = FastAPI(
    title="Hexploration",
    version="0.6.0-temporal-poi",
)

app.include_router(map_router)
app.include_router(health_router)
app.include_router(user_router)
app.include_router(campaign_router)
app.include_router(character_router)
app.include_router(character_sheet_router)
app.include_router(expedition_router)
app.include_router(movement_router)
app.include_router(movement_modifier_router)
app.include_router(world_event_router)
app.include_router(map_edge_router)
app.include_router(poi_router)

# Keep this last: mounting "/" first would swallow /api routes.
app.mount("/", StaticFiles(directory="static", html=True), name="static")
