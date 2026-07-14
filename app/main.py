from fastapi import FastAPI

from app.api.v1.router import api_router
from app.core.config import settings

app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "REST API для сервісу онлайн-кінотеатру: автентифікація, каталог фільмів, "
        "кошик, оплата, коментарі та обране. "
        "Документація Swagger доступна на `/docs`, ReDoc — на `/redoc`."
    ),
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.include_router(api_router)


@app.get("/health", tags=["System"], summary="Перевірка стану сервісу")
async def health_check() -> dict[str, str]:
    """Простий health-check ендпоінт для моніторингу/деплою (EC2, Docker healthcheck)."""
    return {"status": "ok"}
