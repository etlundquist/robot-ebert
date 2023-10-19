# Robot Ebert

A conversational movie recommender

## Run the FastAPI App Locally

```bash
cd app
python main.py
```

## Build and Run the FastAPI App via Docker

```bash
docker build -t robot-ebert .
docker run -p 8080:8080 --env-file .env robot-ebert
```
