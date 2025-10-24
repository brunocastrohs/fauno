from dataclasses import dataclass

@dataclass
class ShapefileEntity:
    name: str
    path: str
    srid: int = 4674
