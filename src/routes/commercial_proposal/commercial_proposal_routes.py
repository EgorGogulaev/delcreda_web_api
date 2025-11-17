import datetime
import traceback
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse

from connection_module import get_async_session
from lifespan import limiter
from security import check_app_auth


router = APIRouter(
    tags=["Commercial proposal"],
)

...  # TODO Реализовать (уточнить у Евгения Останина)
