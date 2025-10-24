#Inicializar
#python3 -m venv .venv && source .venv/bin/activate
#pip install -r Presentation/API/requirements.txt
#export ENVIRONMENT=dev PYTHONPATH=$PWD
#uvicorn Presentation.API.main:app --host 0.0.0.0 --port 9090 --reload

#Startar
# source .venv/bin/activate && uvicorn Presentation.API.main:app --host 0.0.0.0 --port 9090 --reload

import os
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from Presentation.API.settings import settings
from Presentation.API.controllers.shapefile_controller import router as shapefile_router
from Presentation.API.controllers.auth_controller import router as auth_router


app = FastAPI(title=settings.API_TITLE, version=settings.API_VERSION)

# CORS a partir do settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ALLOW_ORIGINS,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=settings.CORS_ALLOW_METHODS,
    allow_headers=settings.CORS_ALLOW_HEADERS,
)

# Rotas com prefixo do settings
app.include_router(
    shapefile_router,
    prefix=f"{settings.API_PREFIX}/shapefiles",
    tags=["Shapefiles"],
)

app.include_router(auth_router, prefix=f"{settings.API_PREFIX}/auth", tags=["Auth"])


if __name__ == "__main__":
    env = os.getenv("ENVIRONMENT", "dev").lower()
    reload_flag = settings.API_RELOAD_ON_DEV and env != "docker"
    uvicorn.run(
        "Presentation.API.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=reload_flag,
    )
