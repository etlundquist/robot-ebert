import os
import uvicorn
from fastapi import FastAPI

from backend.app.api.users import router as users_router
from backend.app.api.movies import router as movies_router
from backend.app.api.search import router as search_router
from backend.app.api.login import router as login_router


app = FastAPI()
app.include_router(users_router, tags=["Users"])
app.include_router(movies_router, tags=["Movies"])
app.include_router(search_router, tags=["Search"])
app.include_router(login_router, tags=["Login"])


@app.get("/")
def root():
    """hello world response for the application root"""

    response = "hello world!"
    return response


if __name__ == "__main__":
    host = str(os.environ.get("HOST", "0.0.0.0"))
    port = int(os.environ.get("PORT", "8080"))
    reload = bool(os.environ.get("RELOAD", ""))
    uvicorn.run("backend.app.main:app", host=host, port=port, reload=reload)
