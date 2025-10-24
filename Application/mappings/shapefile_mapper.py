from Entities.shapefile_entity import ShapefileEntity

def to_entity(name: str, path: str, srid: int = 4674) -> ShapefileEntity:
    return ShapefileEntity(name=name, path=path, srid=srid)
