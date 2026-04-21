# Project FIGMENT - Deployment Guide

This guide covers deploying Project FIGMENT locally (Docker) and to Google Cloud Run.

## Phase 3C: Docker Deployment Status

✅ **Completed:**
- [x] Multi-stage Docker build (optimized image size)
- [x] Docker Compose orchestration (backend + frontend)
- [x] Container networking and volume management
- [x] Health checks configured
- [x] Environment variable configuration
- [x] Graceful error handling in containers

✅ **Tested:**
- Backend container responding to API requests
- Spotify auth endpoint working in container
- Disney recommendations endpoint functional
- LLM agent orchestration with graceful fallback
- APScheduler background jobs running

✅ **Challenges Resolved:**
1. Fixed `uvicorn.run()` missing in main.py - added to entry point
2. Fixed None wait_time crashes - added null checks in calculations
3. Fixed LLM API errors - added graceful fallback to heuristic responses
4. Fixed Disney engine average calculation - filter None values properly
python -m venv venv

# Activate (Windows PowerShell)
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Copy environment variables
cp .env.example .env
# Edit .env with your credentials

# Run backend
python -c "import main; import uvicorn; uvicorn.run(main.app, host='0.0.0.0', port=8002)"

# In another terminal, run frontend
streamlit run frontend/app.py --server.port 8501 --server.address 0.0.0.0
```

## Docker Deployment

### Single Container (Backend Only)

```bash
# Build the image
docker build -t figment-backend .

# Run the container
docker run -p 8002:8002 \
  -e SPOTIFY_CLIENT_ID=your_id \
  -e SPOTIFY_CLIENT_SECRET=your_secret \
  -e GOOGLE_API_KEY=your_key \
  figment-backend
```

### Docker Compose (Recommended)

```bash
# Create .env file with your credentials
cp .env.example .env
# Edit .env with your actual credentials

# Build and start all services
docker-compose up --build

# Access the app
# Backend: http://localhost:8002
# Frontend: http://localhost:8501

# Stop services
docker-compose down

# View logs
docker-compose logs -f backend
docker-compose logs -f frontend
```

## Cloud Deployment

### Google Cloud Run

```bash
# Install Google Cloud CLI
# https://cloud.google.com/sdk/docs/install

# Configure gcloud
gcloud config set project YOUR_PROJECT_ID

# Build and push image
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/figment-backend

# Deploy to Cloud Run
gcloud run deploy figment-backend \
  --image gcr.io/YOUR_PROJECT_ID/figment-backend \
  --platform managed \
  --region us-central1 \
  --port 8002 \
  --set-env-vars \
    SPOTIFY_CLIENT_ID=your_id,\
    SPOTIFY_CLIENT_SECRET=your_secret,\
    GOOGLE_API_KEY=your_key
```

### Heroku

```bash
# Install Heroku CLI
# https://devcenter.heroku.com/articles/heroku-cli

# Login to Heroku
heroku login

# Create app
heroku create figment-backend

# Set environment variables
heroku config:set SPOTIFY_CLIENT_ID=your_id
heroku config:set SPOTIFY_CLIENT_SECRET=your_secret
heroku config:set GOOGLE_API_KEY=your_key

# Deploy
git push heroku main

# View logs
heroku logs --tail
```

### AWS

**Using ECR and ECS:**

```bash
# Create ECR repository
aws ecr create-repository --repository-name figment-backend

# Build and push image
docker build -t figment-backend .
docker tag figment-backend:latest \
  YOUR_AWS_ACCOUNT.dkr.ecr.us-east-1.amazonaws.com/figment-backend:latest
docker push YOUR_AWS_ACCOUNT.dkr.ecr.us-east-1.amazonaws.com/figment-backend:latest

# Create ECS task definition and service
# (See AWS console or use CloudFormation)
```

**Using Elastic Beanstalk:**

```bash
# Install EB CLI
pip install awsebcli

# Initialize
eb init -p docker figment

# Create environment
eb create figment-env

# Deploy
eb deploy

# Open app
eb open
```

### Azure Container Instances

```bash
# Build image
docker build -t figment-backend .

# Push to Azure Container Registry
az acr build --registry YOUR_REGISTRY \
  --image figment:latest .

# Deploy
az container create \
  --resource-group YOUR_RG \
  --name figment \
  --image YOUR_REGISTRY.azurecr.io/figment:latest \
  --ports 8002 \
  --environment-variables \
    SPOTIFY_CLIENT_ID=your_id \
    SPOTIFY_CLIENT_SECRET=your_secret \
    GOOGLE_API_KEY=your_key
```

## Environment Variable Management

### Using AWS Secrets Manager

```bash
# Store secret
aws secretsmanager create-secret \
  --name figment/dev \
  --secret-string '{"SPOTIFY_CLIENT_ID":"...","SPOTIFY_CLIENT_SECRET":"..."}'

# Retrieve in code
import json
import boto3
client = boto3.client('secretsmanager')
secret = client.get_secret_value(SecretId='figment/dev')
```

### Using Google Secret Manager

```bash
# Create secret
gcloud secrets create spotify-credentials \
  --replication-policy="automatic"

# Add secret version
echo -n "SPOTIFY_CLIENT_ID=..." | gcloud secrets versions add spotify-credentials --data-file=-

# Grant access
gcloud projects add-iam-policy-binding YOUR_PROJECT \
  --member=serviceAccount:YOUR_SERVICE_ACCOUNT \
  --role=roles/secretmanager.secretAccessor
```

## Monitoring & Logging

### Docker Logs

```bash
# View logs
docker logs -f figment-backend

# View Docker Compose logs
docker-compose logs -f
```

### Cloud Logging

**Google Cloud:**
```bash
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=figment-backend" --limit 50
```

**AWS CloudWatch:**
```bash
aws logs tail /ecs/figment-backend --follow
```

## Performance Optimization

1. **Use production ASGI server** (not uvicorn):
   ```bash
   pip install gunicorn
   gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app
   ```

2. **Enable caching**: Add Redis for token caching
   ```bash
   docker-compose -f docker-compose.redis.yml up
   ```

3. **Database optimization**: Use PostgreSQL instead of SQLite
   ```bash
   DATABASE_URL=postgresql://user:pass@host/dbname
   ```

## Scaling

### Horizontal Scaling with Load Balancer

```yaml
# docker-compose.yml with Nginx
services:
  nginx:
    image: nginx:latest
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
    depends_on:
      - backend

  backend:
    deploy:
      replicas: 3
```

## Security Considerations

1. ✅ Use environment variables for secrets (never hardcode)
2. ✅ Enable HTTPS in production
3. ✅ Use managed secrets services (AWS Secrets Manager, Google Secret Manager)
4. ✅ Implement API rate limiting
5. ✅ Regular security updates for dependencies
6. ✅ Run containers as non-root user
7. ✅ Use private container registries

## Troubleshooting

### Container won't start
```bash
docker logs container_id
# Check environment variables are set
docker inspect container_id | grep -A 20 Env
```

### Port already in use
```bash
# Kill process on port
lsof -i :8002
kill -9 PID
# Or use different port
docker run -p 8003:8002 figment-backend
```

### Database connection issues
```bash
# Check database file permissions
ls -la figment.db
# Reset database
rm figment.db
docker-compose restart
```

## Support

For issues, check:
- Docker logs: `docker-compose logs`
- Application logs in `/app/logs` (if enabled)
- GitHub issues: https://github.com/millyd03/project-figment

