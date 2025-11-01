from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.routers.pages import router as pages_router
from app.routers.rest import router as rest_router
from app.routers.websocket import router as ws_router


app = FastAPI()

# Static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Routers
app.include_router(pages_router)
app.include_router(rest_router)
app.include_router(ws_router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app)