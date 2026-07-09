from fastapi import FastAPI
from tortoise.contrib.fastapi import register_tortoise

from app.config import TORTOISE_ORM

app = FastAPI(title="NYC 311 Explorer")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


register_tortoise(
    app,
    config=TORTOISE_ORM,
    generate_schemas=False,
    add_exception_handlers=True,
)
