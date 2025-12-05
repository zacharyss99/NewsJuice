# NewsJuice Deployment Guide

Deploy Loader and Scraper services to Google Cloud Run and GKE (Kubernetes).

## Prerequisites

- Docker installed locally
- GCP project with billing enabled
- Service account key (`deployment.json`) with permissions:
  - Cloud Run Admin
  - Kubernetes Engine Admin
  - Cloud SQL Admin
  - Artifact Registry Admin
  - Service Account Admin
  - IAM Admin

## Directory Structure

```
services/
├── deployment/
│   ├── __main__.py           # Pulumi infrastructure code
│   ├── Pulumi.yaml           # Pulumi project config
│   ├── Pulumi.dev.yaml       # Environment config (secrets)
│   ├── Dockerfile            # Deployment container
│   ├── docker-shell.sh       # Start deployment container
│   └── docker-entrypoint.sh  # Container setup script
├── loader_deployed/          # Loader service code
└── scraper_deployed/         # Scraper service code
```

## Quick Start

### 1. Configure Secrets

Create `Pulumi.dev.yaml` in `services/deployment/`:

```yaml
config:
  gcp:project: YOUR-PROJECT-ID
  gcp:region: us-central1
  gcp:zone: us-central1-a
  newsjuice-loader:db_instance_name: newsdb-instance
  newsjuice-loader:db_name: newsdb
  newsjuice-loader:db_user: postgres
  newsjuice-loader:db_password:
    secure: YOUR-ENCRYPTED-PASSWORD
  newsjuice-loader:enable_cloudrun: true
  newsjuice-loader:enable_gke: true
  newsjuice-loader:gke_node_count: 2
  newsjuice-loader:gke_machine_type: e2-standard-2
```

To encrypt password:
```bash
pulumi config set --secret db_password YOUR_PASSWORD
```

### 2. Start Deployment Container

```bash
cd services/deployment
./docker-shell.sh
```

### 3. Deploy Infrastructure

Inside container:
```bash
cd /app
pulumi up
```

Type `yes` to confirm.

## Deployment Outputs

After successful deployment:

| Service | Platform | URL |
|---------|----------|-----|
| Loader | Cloud Run | https://newsjuice-loader-xxx.run.app |
| Scraper | Cloud Run | https://newsjuice-scraper-xxx.run.app |
| Loader | GKE | http://EXTERNAL-IP |
| Scraper | GKE | http://EXTERNAL-IP |

View all outputs:
```bash
pulumi stack output
```

## Common Commands

### Check Status
```bash
# Cloud Run services
gcloud run services list --region=us-central1

# GKE pods
kubectl get pods -n newsjuice

# GKE services (get external IPs)
kubectl get svc -n newsjuice
```

### View Logs
```bash
# Cloud Run
gcloud run services logs read newsjuice-loader --region=us-central1 --limit=50

# GKE
kubectl logs -n newsjuice -l app=newsjuice-loader -c loader --tail=50
```

### Update Deployment
```bash
# After code changes, redeploy
pulumi up
```

### Destroy Infrastructure
```bash
pulumi destroy
```

## Troubleshooting

### Kubernetes cluster unreachable
```bash
gcloud container clusters get-credentials newsjuice-cluster \
    --zone=us-central1-a \
    --project=YOUR-PROJECT-ID
```

### Pulumi state out of sync
```bash
pulumi refresh
pulumi up
```

### Pods stuck in Pending
Check node resources:
```bash
kubectl describe pod POD-NAME -n newsjuice | grep -A 10 Events
```

If "Insufficient cpu", upgrade to larger nodes (`e2-standard-2` or higher).

### Container crash loops
Check logs:
```bash
kubectl logs POD-NAME -n newsjuice -c loader --tail=50
```

Common fixes:
- Missing environment variables (DATABASE_URL)
- Database connection issues
- Missing dependencies

## Cost Estimates

| Component | Monthly Cost |
|-----------|-------------|
| Cloud Run (2 services) | ~$10 |
| GKE Cluster | ~$75 |
| GKE Nodes (2x e2-standard-2) | ~$100 |
| Cloud SQL | ~$10-50 |
| Load Balancers (2) | ~$40 |
| **Total (Cloud Run only)** | **~$20-60** |
| **Total (Cloud Run + GKE)** | **~$235-275** |

## Adding New Services

Edit `SERVICES` list in `__main__.py`:

```python
SERVICES = [
    {"name": "loader", "display_name": "NewsJuice Loader", "source_dir": "/loader_deployed"},
    {"name": "scraper", "display_name": "NewsJuice Scraper", "source_dir": "/scraper_deployed"},
    {"name": "newservice", "display_name": "New Service", "source_dir": "/newservice_deployed"},
]
```

Add volume mount in `docker-shell.sh`:
```bash
-v "$BASE_DIR/../newservice_deployed":/newservice_deployed \
```

Run `pulumi up` to deploy.


To get into the deplyment container:

```bash
docker exec -it newsjuice-app-deployment bash
```

# Winding down everthing:

Inside your deployment container:

1. Destroy all Pulumi-managed infrastructure
```bash
cd /app
pulumi destroy
```
Type yes to confirm. This deletes:

✅ Cloud Run services (loader + scraper)
✅ GKE cluster + nodes + pods
✅ Load balancers
✅ Service accounts + IAM bindings
✅ Artifact Registry images

What stays (not managed by Pulumi):

* Cloud SQL database (~$10-50/month)
* Pulumi state bucket

Start Fresh Deployment
After destroying:

# Exit container
```bash
exit
```

# Restart container
```bash
./docker-shell.sh
```

# Inside container
```bash
cd /app
pulumi up
```
# Test schduler manually

```bash
gcloud scheduler jobs run newsjuice-scraper-daily --location=us-central1
gcloud scheduler jobs run newsjuice-loader-daily --location=us-central1
```

Check logs
```bash
gcloud run services logs read newsjuice-scraper --region=us-central1 --limit=20
gcloud run services logs read newsjuice-loader --region=us-central1 --limit=20
```


