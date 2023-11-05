FROM python:3.9-slim
WORKDIR /src
EXPOSE 8501

RUN apt-get update && apt-get install -y curl git gcc

COPY ./frontend/requirements.txt requirements.txt
RUN pip install -r requirements.txt

COPY ./frontend/ frontend/
COPY ./shared/ shared/

ENTRYPOINT ["streamlit", "run", "frontend/app/main.py", "--server.address", "0.0.0.0", "--server.port", "8501"]
