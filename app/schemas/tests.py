from typing import Literal

from pydantic import BaseModel


class TestParams(BaseModel):
    test: int | None = None
    industry: int | None = None
    params: float | None = None
    result: float | None = None
    
