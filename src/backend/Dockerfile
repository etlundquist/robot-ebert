FROM python:3.9-slim
WORKDIR /src
EXPOSE 8080

RUN apt-get update && apt-get install -y curl git gcc

COPY ./backend/requirements.txt requirements.txt
RUN pip install -r requirements.txt

COPY ./backend/ backend/
COPY ./shared/ shared/

ENTRYPOINT ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8080"]
