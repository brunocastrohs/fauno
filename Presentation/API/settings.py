import json
import os
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional

class _Settings(BaseModel):
    # DB
    DB_HOST: str
    DB_PORT: int
    DB_USER: str
    DB_PASSWORD: str
    DB_NAME: str

    # GeoServer
    GEOSERVER_BASEURL: str
    GEOSERVER_WORKSPACE: str
    GEOSERVER_DATASTORE: str
    GEOSERVER_USER: str
    GEOSERVER_PASSWORD: str
    INDE_ENABLED: bool = True
    INDE_WORKSPACE: str | None = "inde"
    INDE_DATASTORE: str | None = "inde_ds"

    # Upload
    UPLOAD_TEMP_PATH: Optional[str] = None

    # API
    API_TITLE: str = Field(default="Fauno API")
    API_VERSION: str = Field(default="1.0.0")
    API_HOST: str = Field(default="0.0.0.0")
    API_PORT: int = Field(default=9090)
    API_PREFIX: str = Field(default="/fauno-api/v1")
    API_RELOAD_ON_DEV: bool = Field(default=True)

    # CORS
    CORS_ALLOW_ORIGINS: List[str] = Field(default_factory=lambda: ["*"])
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: List[str] = Field(default_factory=lambda: ["*"])
    CORS_ALLOW_HEADERS: List[str] = Field(default_factory=lambda: ["*"])

def _load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

def _resolve_config_file() -> Path:
    env = os.getenv("ENVIRONMENT", "dev").lower()
    base = Path(__file__).parent
    return base / ("appsettings.docker.json" if env == "docker" else "appsettings.dev.json")

_cfg = _load_json(_resolve_config_file())

def _get(path, default=None):
    cur = _cfg
    for key in path.split("."):
        cur = cur.get(key, {})
    return cur if cur else (default if default is not None else cur)

settings = _Settings(
    # DB
    DB_HOST=_cfg["Database"]["Host"],
    DB_PORT=int(_cfg["Database"]["Port"]),
    DB_USER=_cfg["Database"]["User"],
    DB_PASSWORD=_cfg["Database"]["Password"],
    DB_NAME=_cfg["Database"]["Name"],

    # GeoServer
    GEOSERVER_BASEURL=_cfg["GeoServer"]["BaseUrl"].rstrip("/"),
    GEOSERVER_WORKSPACE=_cfg["GeoServer"]["Workspace"],
    GEOSERVER_DATASTORE=_cfg["GeoServer"]["Datastore"],
    GEOSERVER_USER=_cfg["GeoServer"]["User"],
    GEOSERVER_PASSWORD=_cfg["GeoServer"]["Password"],
    INDE_ENABLED=bool(_get("INDE.Enabled", True)),
    INDE_WORKSPACE=_get("INDE.Workspace", "inde"),
    INDE_DATASTORE=_get("INDE.Datastore", "inde_ds"),

    # Upload
    UPLOAD_TEMP_PATH=_get("Upload.TempPath"),

    # API
    API_TITLE=_get("Api.Title", "Fauno API"),
    API_VERSION=_get("Api.Version", "1.0.0"),
    API_HOST=_get("Api.Host", "0.0.0.0"),
    API_PORT=int(_get("Api.Port", 9090)),
    API_PREFIX=_get("Api.Prefix", "/fauno-api/v1"),
    API_RELOAD_ON_DEV=bool(_get("Api.ReloadOnDev", True)),

    # CORS
    CORS_ALLOW_ORIGINS=_get("Cors.AllowOrigins", ["*"]),
    CORS_ALLOW_CREDENTIALS=bool(_get("Cors.AllowCredentials", True)),
    CORS_ALLOW_METHODS=_get("Cors.AllowMethods", ["*"]),
    CORS_ALLOW_HEADERS=_get("Cors.AllowHeaders", ["*"]),
)
