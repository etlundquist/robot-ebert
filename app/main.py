import os
import uvicorn
from fastapi import FastAPI

from app.api.users import router as users_router
from app.api.movies import router as movies_router
from app.api.recs import router as recs_router


app = FastAPI()
app.include_router(users_router, tags=["Users"])
app.include_router(movies_router, tags=["Movies"])
app.include_router(recs_router, tags=["Recs"])


@app.get("/", status_code=200)
def root():
    """hello world response for the application root"""

    response = "hello world!"
    return response


if __name__ == "__main__":
    host = str(os.environ.get("HOST", "0.0.0.0"))
    port = int(os.environ.get("PORT", "8080"))
    reload = bool(os.environ.get("RELOAD", "false"))
    uvicorn.run("app.main:app", host=host, port=port, reload=reload)
