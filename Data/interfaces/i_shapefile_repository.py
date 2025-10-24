from abc import ABC, abstractmethod
from Entities.shapefile_entity import ShapefileEntity

class IShapefileRepository(ABC):
    @abstractmethod
    def drop_table_if_exists(self, table: str) -> None: ...

    @abstractmethod
    def import_with_ogr2ogr(self, shp: ShapefileEntity, schema: str = "public") -> None: ...

    @abstractmethod
    def table_exists(self, table: str, schema: str = "public") -> bool: ...
