from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

class DbContext:
    def __init__(self, host: str, port: int, user: str, password: str, db: str):
        self._url = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}"
        self._engine: Engine = create_engine(self._url, pool_pre_ping=True)

    @property
    def engine(self) -> Engine:
        return self._engine
