FROM python:3.9-slim
WORKDIR /app
EXPOSE 8080

RUN apt-get update \
    && apt-get install -y curl git gcc ca-certificates \
    && apt-get clean \
    && update-ca-certificates

COPY ./requirements.txt requirements.txt
RUN pip install -r requirements.txt

COPY app ./app/
ENTRYPOINT ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
