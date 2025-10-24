import subprocess
from sqlalchemy import text
from Entities.shapefile_entity import ShapefileEntity
from Data.db_context import DbContext
from Data.interfaces.i_shapefile_repository import IShapefileRepository

class ShapefileRepository(IShapefileRepository):
    def __init__(self, db: DbContext):
        self._db = db

    def drop_table_if_exists(self, table: str, schema: str = "public") -> None:
        sql = text(f'DROP TABLE IF EXISTS "{schema}"."{table}" CASCADE;')
        with self._db.engine.begin() as conn:
            conn.execute(sql)

    def table_exists(self, table: str, schema: str = "public") -> bool:
        sql = text("""
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema = :schema AND table_name = :table
            LIMIT 1
        """)
        with self._db.engine.begin() as conn:
            row = conn.execute(sql, {"schema": schema, "table": table}).first()
            return row is not None

    def import_with_ogr2ogr(self, shp: ShapefileEntity, schema: str = "public") -> None:
        # Requer GDAL (ogr2ogr) instalado no sistema
        conn_str = self._db._url.replace("+psycopg2", "")
        # força SRID, cria geometria e índice espacial padrão
        cmd = [
            "ogr2ogr",
            "-f", "PostgreSQL",
            conn_str,
            shp.path,
            "-nln", f'{schema}.{shp.name}',
            "-lco", "GEOMETRY_NAME=geom",
            "-lco", "FID=fid",
            "-nlt", "PROMOTE_TO_MULTI",
            "-overwrite",
            "-t_srs", f"EPSG:{shp.srid}"
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            raise RuntimeError(f"ogr2ogr falhou: {proc.stderr}")

    def list_layers(self, schema: str) -> list[dict]:
        """
        Lista todas as camadas registradas em geometry_columns
        do schema especificado.
        """
        sql = text("""
            SELECT 
                f_table_schema,
                f_table_name,
                f_geometry_column,
                coord_dimension,
                srid,
                type
            FROM public.geometry_columns
            WHERE f_table_schema = :schema
            ORDER BY f_table_name
        """)
        with self._db.engine.begin() as conn:
            rows = conn.execute(sql, {"schema": schema}).mappings().all()
            return [dict(r) for r in rows]