from pydantic import BaseModel


class FeatureFlagsProxyParams(BaseModel):
    userId: str | None = None
