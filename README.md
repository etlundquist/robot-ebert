# Robot Ebert

A conversational movie recommender

## Run the FastAPI App Locally (Re-Load on Save)

```bash
PYTHONPATH=$PWD RELOAD=true python app/main.py
```

## Run the FastAPI App via Docker Desktop

```bash
docker build -t robot-ebert-fastapi .
docker run -p 8080:8080 --env-file .env robot-ebert-fastapi
```

## Build and Deploy the FastAPI App via GCP Artifact Registry and GCP Cloud Run

### Set Environment Variables

```bash
export PROJECT_ID="robot-ebert"
export LOCATION="us-west1"
export REPO_NAME="robot-ebert"
export REPO_DESCRIPTION="container images for the Robot Ebert movie recommender application"
export IMAGE_NAME="robot-ebert-fastapi"
export SERVICE_NAME="robot-ebert"
```

### Create the Repo in GCP Artifact Registry

```bash
gcloud auth login
gcloud artifacts repositories create ${REPO_NAME} --repository-format=docker --location=${LOCATION} --description=${REPO_DESCRIPTION}
gcloud artifacts repositories list
```

### Configure Docker to use the Google Cloud CLI to authenticate requests to GCP Artifact Registry

```bash
gcloud auth configure-docker ${LOCATION}-docker.pkg.dev
```

### Build an Updated Image Targeting a 64 Bit Linux Runtime

```bash
docker build --platform linux/amd64 -t ${IMAGE_NAME} .
```

### Tag and Push the Image to GCP Artifact Registry

```bash
docker tag ${IMAGE_NAME}:latest ${LOCATION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/${IMAGE_NAME}:latest
docker push ${LOCATION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/${IMAGE_NAME}:latest
```

### Deploy the Updated Image to the Existing GCP Cloud Run Service

```bash
gcloud run deploy ${SERVICE_NAME} --image ${LOCATION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/${IMAGE_NAME}:latest --platform managed --region $LOCATION
```

## Create and Connect to the Application Database in GCP CloudSQL

### Apply the SQLAlchemy Tables DDL to the Database

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
