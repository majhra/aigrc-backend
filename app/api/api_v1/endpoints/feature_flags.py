from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from UnleashClient import UnleashClient

from app.api import deps
from app.api.utils import get_unleash_client
from app.modules.tlogger import TLogger
from app.schemas import FeatureFlagsProxyParams, User

router = APIRouter()


@router.get("/proxy")
async def get_feature_flag_toggles(
    current_user: Annotated[User, Depends(deps.get_current_user_safe)],
    params: FeatureFlagsProxyParams = Depends(),
    unleash_client: UnleashClient = Depends(get_unleash_client),
    logger: TLogger = Depends(deps.get_logger),
):
    """
    This endpoint is designed to mimic the functionality of the Unleash proxy
    so that we can use existing Unleash SDKs without having to modify them.
    See https://docs.getunleash.io/reference/unleash-proxy for more details.
    """
    if unleash_client == None:
        logger.warning("Unleash client not configured")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unleash client not configured",
        )

    feature_toggles = []
    feature_flags = unleash_client.features
    context = None

    # Set the context to the current user's email if they are logged in (prioritize current_user over params.userId)
    if current_user is not None:
        context = {
            "userId": current_user.email,
        }
    elif params.userId is not None:
        context = {
            "userId": params.userId,
        }

    for flag in feature_flags:
        variant = unleash_client.get_variant(flag, context)
        enabled = variant["feature_enabled"]
        variant.pop("feature_enabled")

        if enabled == False:
            continue

        feature_toggles.append(
            {
                "name": flag,
                "enabled": enabled,
                "variant": variant,
            }
        )

    return JSONResponse(content={"toggles": feature_toggles})
