from pydantic import BaseModel

class FallbackIn(BaseModel):
    user_id: int
    pin: str

class FallbackOut(BaseModel):
    status: str
    user_id: int
    record_id: int | None = None
