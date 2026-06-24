from pydantic import BaseModel


class Error(BaseModel):
    error: str
    message: str


class Health(BaseModel):
    status: str
    db: str
    version: str = "0.1.0"
