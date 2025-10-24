import os
import shutil
import tempfile
from pathlib import Path
from typing import Dict

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse

from Application.services.shapefile_service import ShapefileService
from Application.dto.shapefile_dto import ShapefileUploadResultDTO
from Application.mappings.shapefile_mapper import to_entity
from Entities.geoserver_helper import sanitize_layer_name
from Presentation.API.settings import settings

router = APIRouter()

@router.post("/upload", response_model=ShapefileUploadResultDTO)
async def upload_and_publish(
    file: UploadFile = File(..., description="ZIP contendo .shp, .dbf, .shx, .prj"),
    workspace: str = Form(default=None),
    datastore: str = Form(default=None),
    srid: int = Form(default=4674),
    publishOnINDE: str | None = Form(default=None),
) -> ShapefileUploadResultDTO:
    if not file.filename.lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="Envie um arquivo .zip com o shapefile.")

    ws = workspace or settings.GEOSERVER_WORKSPACE
    ds = datastore or settings.GEOSERVER_DATASTORE

    # salvar zip em diretório temporário
    tmp_root = Path(settings.UPLOAD_TEMP_PATH or tempfile.gettempdir()) / "fauno"
    tmp_root.mkdir(parents=True, exist_ok=True)
    tmp_dir = Path(tempfile.mkdtemp(prefix="fauno_", dir=tmp_root))

    zip_path = tmp_dir / file.filename
    with zip_path.open("wb") as f:
        f.write(await file.read())

    # extrair
    shutil.unpack_archive(str(zip_path), str(tmp_dir))

    # converter todos os nomes de arquivos para minúsculo
    for item in tmp_dir.iterdir():
        lower_name = item.name.lower()
        if item.name != lower_name:
            item.rename(tmp_dir / lower_name)

    # localizar .shp
    shp_files = list(tmp_dir.glob("*.shp"))
    if not shp_files:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise HTTPException(status_code=400, detail="ZIP não contém .shp")

    shp_path = shp_files[0]
    layer_name = sanitize_layer_name(shp_path.stem)

    # tentar carregar SLD do zip (mesmo basename do .shp)
    sld_path = tmp_dir / f"{shp_path.stem}.sld"
    sld_xml: str | None = None
    if sld_path.exists():
        sld_xml = sld_path.read_text(encoding="utf-8", errors="ignore")

    # montar entidade + service
    shapefile_entity = to_entity(name=layer_name, path=str(shp_path), srid=srid)
    service = ShapefileService.create_from_settings(settings)

    # importar para PostGIS e publicar no GeoServer
    try:
        service.import_to_postgis(shapefile_entity)
        
        publish_on_inde = False
        if publishOnINDE is not None:
            publish_on_inde = str(publishOnINDE).strip().lower() in ("1", "true", "yes", "on")

        pub = service.publish_on_geoserver(
                shapefile_entity,
                workspace=ws,
                datastore=ds,
                sld_xml=sld_xml,
                publish_on_inde=publish_on_inde,
                inde_workspace=settings.INDE_WORKSPACE if publish_on_inde else None,
                inde_datastore=settings.INDE_DATASTORE if publish_on_inde else None,
        )

        return ShapefileUploadResultDTO(
            layer=layer_name,
            workspace=ws,
            datastore=ds,
            database_table=layer_name,
            status="Publicado com sucesso no GeoServer",
            geoserver=pub,
        )
    except Exception as ex:
        raise HTTPException(status_code=500, detail=f"Falha ao publicar: {ex}") from ex
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


@router.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}

@router.get("/layers")
def list_layers():
    """
    Lista todas as camadas do schema configurado no GeoServer Workspace.
    """
    try:
        service = ShapefileService.create_from_settings(settings)
        layers = service.list_layers()
        return JSONResponse(content=layers)
    except Exception as ex:
        raise HTTPException(status_code=500, detail=f"Erro ao listar layers: {ex}")