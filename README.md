# Robot Ebert

A Conversational Movie Recommendation App

![robot-ebert](./images/robot-ebert.png)

## Run the Application Locally

### Run the FastAPI Backend (Reload on Save)

```bash
cd src && PYTHONPATH=$PWD RELOAD=true python backend/app/main.py
```

### Run the Streamlit Frontend (Reload on Save)

```bash
cd src && streamlit run frontend/app/main.py
```

## Run the Application via Docker Desktop

### Run the FastAPI Backend

```bash
cd src && docker build -f backend/Dockerfile -t robot-ebert-fastapi . && cd -
docker run -p 8080:8080 --env-file .env robot-ebert-fastapi
```

### Run the Streamlit Frontend

```bash
cd src && docker build -f frontend/Dockerfile -t robot-ebert-streamlit . && cd -
docker run -p 8501:8501 --env-file .env robot-ebert-streamlit
```

## Deploy the Application to GCP Cloud Run

### Set Global Environment Variables

```bash
export PROJECT_ID="robot-ebert"
export LOCATION="us-west1"
export REPO_NAME="robot-ebert"
export REPO_DESCRIPTION="container images for the Robot Ebert movie recommender application"
```

### Create the Repo in GCP Artifact Registry

```bash
gcloud auth login
gcloud artifacts repositories create ${REPO_NAME} --repository-format=docker --location=${LOCATION} --description=${REPO_DESCRIPTION}
gcloud artifacts repositories list
gcloud auth configure-docker ${LOCATION}-docker.pkg.dev
```

### Update the FastAPI Backend Service

#### Set Environment Variables

```bash
export IMAGE_NAME="robot-ebert-fastapi"
export SERVICE_NAME="robot-ebert-fastapi"
```

#### Build and Push the FastAPI Image to Artifact Registry

```bash
cd src && docker build --platform linux/amd64 -f backend/Dockerfile -t ${IMAGE_NAME} . && cd -
docker tag ${IMAGE_NAME}:latest ${LOCATION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/${IMAGE_NAME}:latest
docker push ${LOCATION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/${IMAGE_NAME}:latest
```

#### Update the FastAPI Backend Cloud Run Service to Use the New Image

```bash
gcloud run deploy ${SERVICE_NAME} --image ${LOCATION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/${IMAGE_NAME}:latest --platform managed --region $LOCATION
```

### Update the Streamlit Frontend Service

#### Set Environment Variables

```bash
export IMAGE_NAME="robot-ebert-streamlit"
export SERVICE_NAME="robot-ebert-streamlit"
```

#### Build and Push the Streamlit Image to Artifact Registry

```bash
cd src && docker build --platform linux/amd64 -f frontend/Dockerfile -t ${IMAGE_NAME} . && cd -
docker tag ${IMAGE_NAME}:latest ${LOCATION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/${IMAGE_NAME}:latest
docker push ${LOCATION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/${IMAGE_NAME}:latest
```

#### Update the Frontend Cloud Run Service to Use the New Image

```bash
gcloud run deploy ${SERVICE_NAME} --image ${LOCATION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/${IMAGE_NAME}:latest --platform managed --region $LOCATION
```

## Connect to the Application Database in GCP CloudSQL

### Apply the SQLAlchemy DDL to the Database to Create the Tables

```bash
gcloud auth application-default login
cd app && python database.py && cd -
```

### Connect to the Database Locally using pgAdmin

* Whitelist Your Client IP: CloudSQL > Instances > `${INSTANCE_NAME}` > Networking > Add a Network > `${CLIENT_PUBLIC_IP}`
* Add a New Server in pgAdmin: Servers > Register > Server:
    * Host: `${SERVER_PUBLIC_IP}`
    * User: `postgres`
    * Pass: `POSTGRES_PASSWORD` (GCP Secrets Manager)
    * Port: 5432
