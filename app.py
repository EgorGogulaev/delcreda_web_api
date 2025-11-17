from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
# from fastapi.middleware.gzip import GZipMiddleware

from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from prometheus_fastapi_instrumentator import Instrumentator

from lifespan import lifespan, limiter
from security import check_app_auth, get_client_ip, is_ip_blocked
from src.routes.user_routes import router as user_router
from src.routes.file_store_routes import router as docs_router
from src.routes.reference_router import router as reference_router
from src.routes.chat_routes import router as chat_router
from src.routes.notification_routes import router as notification_router
from src.routes.comment_subject_routes import router as comment_subject_router

from src.routes.legal_entity.legal_entity_routes import router as legal_entity_router
from src.routes.legal_entity.bank_details_routes import router as bank_details_router

from src.routes.application.application_routes import router as application_router
from src.routes.application.mt_application_routes import router as mt_application_router

from src.routes.commercial_proposal.commercial_proposal_routes import router as commercial_proposal_router
# TODO тут будет конкретное КП



app = FastAPI(
    title="Delcreda WEB",
    lifespan=lifespan,
)

# Подключение prometheus
limiter.limit(("15/minute"), Instrumentator().instrument(app).expose(
    app,
    endpoint="/metrics",
    dependencies=[Depends(check_app_auth)],  # 🔒 Добавляем проверку авторизации
))

# Подключение лимитера к приложению
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# Middlewares
@app.middleware("http")
async def block_ip_middleware(request: Request, call_next):
    ip = get_client_ip(request)
    if await is_ip_blocked(ip):
        return JSONResponse(status_code=429, content={"msg": "Too many failed login attempts. Try again later."})
    response = await call_next(request)
    return response

# Подключение CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)

# Подключение GZipMiddleware
# app.add_middleware(
#     GZipMiddleware,
#     minimum_size=500,
#     compresslevel=6
# )

# ___________
app.include_router(user_router)
app.include_router(docs_router)
app.include_router(reference_router)
app.include_router(chat_router)
app.include_router(notification_router)
app.include_router(legal_entity_router)

app.include_router(application_router)
app.include_router(mt_application_router)

app.include_router(commercial_proposal_router)
# TODO тут будет конкретное КП

app.include_router(bank_details_router)
app.include_router(comment_subject_router)
# ___________
