from pydantic import BaseModel

class ShapefileUploadResultDTO(BaseModel):
    layer: str
    workspace: str
    datastore: str
    database_table: str
    status: str
    geoserver: dict
