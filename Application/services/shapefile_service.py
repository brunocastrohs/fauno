from typing import Optional

from Data.db_context import DbContext
from Data.repositories.shapefile_repository import ShapefileRepository
from Entities.shapefile_entity import ShapefileEntity
from Entities.geoserver_helper import build_basic_polygon_sld
from Application.services.geoserver_service import GeoServerService

class ShapefileService:
    def __init__(self, repo: ShapefileRepository, geoserver: GeoServerService, schema: str = "zcm"):
        self._repo = repo
        self._gs = geoserver
        self._schema = schema

    @classmethod
    def create_from_settings(cls, settings) -> "ShapefileService":
        db = DbContext(
            host=settings.DB_HOST,
            port=settings.DB_PORT,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD,
            db=settings.DB_NAME,
        )
        repo = ShapefileRepository(db)
        gs = GeoServerService(
            base_url=settings.GEOSERVER_BASEURL,
            user=settings.GEOSERVER_USER,
            password=settings.GEOSERVER_PASSWORD,
        )
        # schema padrão = workspace (mantém simetria)
        schema = settings.GEOSERVER_WORKSPACE or "public"
        return cls(repo=repo, geoserver=gs, schema=schema)

    def import_to_postgis(self, shp: ShapefileEntity) -> None:
        # idempotente: drop + import
        self._repo.drop_table_if_exists(table=shp.name, schema=self._schema)
        self._repo.import_with_ogr2ogr(shp, schema=self._schema)

    def publish_on_geoserver(
        self,
        shp: ShapefileEntity,
        workspace: str,
        datastore: str,
        sld_xml: Optional[str] = None,
        publish_on_inde: bool = False,                 
        inde_workspace: Optional[str] = None,          
        inde_datastore: Optional[str] = None,
    ) -> dict:
        """
        Fluxo:
        ::1 cria cadastro do style <layer>_style com filename <layer>.sld
        ::2 atualiza conteúdo do style com SLD (do zip, se houver; senão fallback)
        ::3 cria featureType (publica tabela como layer)
        ::4 vincula defaultStyle
        ::5 valida SLD (download e checa tamanho)
        ::6 checa status HTTP da layer
        """
        style_name = f"{shp.name}_style"
        style_filename = f"{shp.name}.sld"

        # Se não veio SLD no zip, gera um fallback básico
        final_sld = sld_xml or build_basic_polygon_sld(shp.name)

        # ::1 cria o registro do style
        self._gs.create_style_registration(name=style_name, workspace=workspace, filename=style_filename)

        # ::2 faz upload do conteúdo SLD para o style
        self._gs.upload_style_sld(name=style_name, workspace=workspace, sld_xml=final_sld)

        # ::3 cria featureType (publica a tabela como layer)
        self._gs.create_featuretype(workspace=workspace, datastore=datastore, layer=shp.name)

        # ::4 vincula defaultStyle
        self._gs.set_default_style(layer=shp.name, workspace=workspace, style=style_name)

        # ::5 valida SLD (baixa e vê se tem conteúdo suficiente)
        sld_len_main = self._gs.get_style_sld_length(workspace=workspace, name=style_name)
        sld_ok_main = sld_len_main is not None and sld_len_main >= 50  # mesmo critério do seu script

        # ::6 checa status da layer
        status_main = self._gs.check_layer_status(layer=shp.name, workspace=workspace)
        
        result = {
            "main": {
                "layer": f"{workspace}:{shp.name}",
                "style": style_name,
                "sld_filename": style_filename,
                "sld_ok": sld_ok_main,
                "sld_length": sld_len_main,
                "http_status": status_main,
            }
        }
        
        if publish_on_inde:
            if not inde_workspace or not inde_datastore:
                raise ValueError("INDE workspace/datastore não configurados.")

            # mesmo nome de tabela (datastore INDE deve apontar para o mesmo DB/schema)
            self._gs.create_style_registration(style_name, inde_workspace, style_filename)  # ::1
            self._gs.upload_style_sld(style_name, inde_workspace, final_sld)                # ::2
            self._gs.create_featuretype(inde_workspace, inde_datastore, shp.name)           # ::3
            self._gs.set_default_style(shp.name, inde_workspace, style_name)                # ::4
            sld_len_inde = self._gs.get_style_sld_length(inde_workspace, style_name)        # ::5
            sld_ok_inde = sld_len_inde is not None and sld_len_inde >= 50
            status_inde = self._gs.check_layer_status(shp.name, inde_workspace)             # ::6

            result["inde"] = {
                "layer": f"{inde_workspace}:{shp.name}",
                "style": style_name,
                "sld_filename": style_filename,
                "sld_ok": sld_ok_inde,
                "sld_length": sld_len_inde,
                "http_status": status_inde,
            }

        return result
