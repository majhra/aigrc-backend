import json
from os.path import join
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse

from app.api import deps
from app.modules.tlogger import TLogger
from app.schemas import TestParams, User

router = APIRouter()


MODELS_DIR: str = join("app", "assets", "ai_models")


@router.post("/tests")
async def run_tests(
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
    params: TestParams = Depends(),
    logger: TLogger = Depends(deps.get_logger),
):
    """
    Execute the test.
    """
    logger.info(
        f"params: {params.dict()}"
    )
    
    return JSONResponse(
        content={"owner": json.loads(current_user.model_dump_json()), "result": params.dict()},
    )
