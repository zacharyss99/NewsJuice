# NewsJuice Deployment Guide

Deploy Loader, Scraper, Chatter and Frontend to Google Cloud Run and GKE (Kubernetes).

NewsJuice is fully deployed with HTTPS!

Final URLs:

Production: https://www.newsjuiceapp.com ✅
GKE Frontend: http://34.28.40.119
GKE Chatter: http://136.113.170.71

Features working:

✅ User registration/login (Firebase Auth)
✅ Preferences saving
✅ Daily Brief generation & playback
✅ Microphone/voice Q&A (now works with HTTPS!)
✅ SSL certificate (Google-managed, auto-renews)

Infrastructure:

✅ GKE cluster with Ingress
✅ Cloud Run (backup)
✅ Cloud SQL
✅ Cloud Scheduler (6 AM scraper, 7 AM loader)
✅ Pulumi IaC (fully repeatable)



## Prerequisites

- Docker installed locally
- GCP project with billing enabled (newsjuice-123456)
- Service account key (`deployment.json` in **secrets** folder in the parent folder of the app) with permissions:
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
sh docker-shell.sh
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


HTTPS

Check status (provisioning/active)
kubectl describe managedcertificate newsjuice-cert -n newsjuice | grep Status



EXPLORING KUBERNETES DEPLOYMENT

### Pods

```bash
root@e0d820fde2c9:/app# kubectl get pods -n newsjuice
NAME                                  READY   STATUS    RESTARTS   AGE
newsjuice-chatter-6fbcf5b8bd-d2v5f    2/2     Running   0          53m
newsjuice-chatter-6fbcf5b8bd-vrkhk    2/2     Running   0          53m
newsjuice-frontend-5bc9db886b-d6d77   2/2     Running   0          26m
newsjuice-frontend-5bc9db886b-dnkvj   2/2     Running   0          26m
newsjuice-loader-d57d94895-59579      2/2     Running   0          8h
newsjuice-loader-d57d94895-vdxv4      2/2     Running   0          8h
newsjuice-scraper-9f697bcf9-ljjdv     2/2     Running   0          26h
newsjuice-scraper-9f697bcf9-qkqg4     2/2     Running   0          26h
```
```bash
kubectl logs -n newsjuice <pod-name> -c <container-name>
```

### Deployment

```bash
root@e0d820fde2c9:/app# kubectl get deployments -n newsjuice
NAME                 READY   UP-TO-DATE   AVAILABLE   AGE
newsjuice-chatter    2/2     2            2           8h
newsjuice-frontend   2/2     2            2           6h17m
newsjuice-loader     2/2     2            2           26h
newsjuice-scraper    2/2     2            2           26h
```

### Services

```bash
kubectl get svc -n newsjuice
```

### Services
```bash
root@e0d820fde2c9:/app# kubectl get svc -n newsjuice
NAME               TYPE           CLUSTER-IP       EXTERNAL-IP      PORT(S)        AGE
chatter-service    LoadBalancer   34.118.238.5     136.113.170.71   80:32185/TCP   8h
frontend-service   LoadBalancer   34.118.227.57    34.28.40.119     80:30662/TCP   6h18m
loader-service     LoadBalancer   34.118.235.175   136.114.177.98   80:32501/TCP   26h
scraper-service    LoadBalancer   34.118.228.50    34.72.210.252    80:32313/TCP   26h
```

### Ingress
```bash
root@e0d820fde2c9:/app# kubectl get ingress -n newsjuice
NAME                CLASS    HOSTS                  ADDRESS           PORTS   AGE
newsjuice-ingress   <none>   www.newsjuiceapp.com   136.110.164.121   80      59m
```

### Certification
```bash
kubectl describe managedcertificate newsjuice-cert -n newsjuice
```
```
root@e0d820fde2c9:/app# kubectl describe managedcertificate newsjuice-cert -n newsjuice
Name:         newsjuice-cert
Namespace:    newsjuice
Labels:       <none>
Annotations:  <none>
API Version:  networking.gke.io/v1
Kind:         ManagedCertificate
Metadata:
  Creation Timestamp:  2025-12-05T22:43:21Z
  Generation:          3
  Resource Version:    1764975426564223020
  UID:                 90bf5e05-5a56-48c5-8287-48416e7b51a4
Spec:
  Domains:
    www.newsjuiceapp.com
Status:
  Certificate Name:    mcrt-a25004c9-72fc-4267-8b43-6796368f3946
  Certificate Status:  Active
  Domain Status:
    Domain:     www.newsjuiceapp.com
    Status:     Active
  Expire Time:  2026-03-05T14:43:26.000-08:00
Events:
  Type    Reason  Age   From                            Message
  ----    ------  ----  ----                            -------
  Normal  Create  60m   managed-certificate-controller  Create SslCertificate mcrt-a25004c9-72fc-4267-8b43-6796368f3946
```
### Watch pods in real time
```bash
 kubectl get pods -n newsjuice -w
 ```

### All resources
```bash
kubectl get all -n newsjuice
```
```
NAME                                      READY   STATUS    RESTARTS   AGE
pod/newsjuice-chatter-6fbcf5b8bd-d2v5f    2/2     Running   0          62m
pod/newsjuice-chatter-6fbcf5b8bd-vrkhk    2/2     Running   0          62m
pod/newsjuice-frontend-5bc9db886b-d6d77   2/2     Running   0          36m
pod/newsjuice-frontend-5bc9db886b-dnkvj   2/2     Running   0          36m
pod/newsjuice-loader-d57d94895-59579      2/2     Running   0          9h
pod/newsjuice-loader-d57d94895-vdxv4      2/2     Running   0          9h
pod/newsjuice-scraper-9f697bcf9-ljjdv     2/2     Running   0          26h
pod/newsjuice-scraper-9f697bcf9-qkqg4     2/2     Running   0          26h

NAME                       TYPE           CLUSTER-IP       EXTERNAL-IP      PORT(S)        AGE
service/chatter-service    LoadBalancer   34.118.238.5     136.113.170.71   80:32185/TCP   8h
service/frontend-service   LoadBalancer   34.118.227.57    34.28.40.119     80:30662/TCP   6h23m
service/loader-service     LoadBalancer   34.118.235.175   136.114.177.98   80:32501/TCP   26h
service/scraper-service    LoadBalancer   34.118.228.50    34.72.210.252    80:32313/TCP   26h

NAME                                 READY   UP-TO-DATE   AVAILABLE   AGE
deployment.apps/newsjuice-chatter    2/2     2            2           8h
deployment.apps/newsjuice-frontend   2/2     2            2           6h23m
deployment.apps/newsjuice-loader     2/2     2            2           26h
deployment.apps/newsjuice-scraper    2/2     2            2           26h

NAME                                            DESIRED   CURRENT   READY   AGE
replicaset.apps/newsjuice-chatter-58b6748d8b    0         0         0       4h32m
replicaset.apps/newsjuice-chatter-59d7985d5d    0         0         0       8h
replicaset.apps/newsjuice-chatter-64d4ddbc77    0         0         0       6h24m
replicaset.apps/newsjuice-chatter-67f9bf5c87    0         0         0       8h
replicaset.apps/newsjuice-chatter-6f956dfcf9    0         0         0       8h
replicaset.apps/newsjuice-chatter-6fbcf5b8bd    2         2         2       62m
replicaset.apps/newsjuice-chatter-7b447c8d5     0         0         0       8h
replicaset.apps/newsjuice-chatter-8569c69bd4    0         0         0       7h47m
replicaset.apps/newsjuice-chatter-bdcdcf4f5     0         0         0       4h31m
replicaset.apps/newsjuice-chatter-c458f76c7     0         0         0       5h34m
replicaset.apps/newsjuice-chatter-c854b888      0         0         0       5h1m
replicaset.apps/newsjuice-frontend-54f9b46c8b   0         0         0       5h14m
replicaset.apps/newsjuice-frontend-5bc9db886b   2         2         2       36m
replicaset.apps/newsjuice-frontend-5c646f8c98   0         0         0       5h41m
replicaset.apps/newsjuice-frontend-5db685777c   0         0         0       4h9m
replicaset.apps/newsjuice-frontend-5f44fbffb9   0         0         0       4h18m
replicaset.apps/newsjuice-frontend-6d86f99b8    0         0         0       6h4m
replicaset.apps/newsjuice-frontend-767d574c6d   0         0         0       5h43m
replicaset.apps/newsjuice-frontend-79bb8b7d86   0         0         0       4h17m
replicaset.apps/newsjuice-frontend-7db8696c4    0         0         0       6h11m
replicaset.apps/newsjuice-frontend-85c86b98b5   0         0         0       6h23m
replicaset.apps/newsjuice-frontend-85cd545c8    0         0         0       5h13m
replicaset.apps/newsjuice-loader-5847b79c4      0         0         0       26h
replicaset.apps/newsjuice-loader-d57d94895      2         2         2       9h
replicaset.apps/newsjuice-scraper-9f697bcf9     2         2         2       26h
```

## Testing CronJobs for scraper and loader

1. List CronJobs
```bash
kubectl get cronjobs -n newsjuice
```

2. List Jobs (created by CronJobs)
```bash
kubectl get jobs -n newsjuice
```
3. List Pods (created by Jobs)
```bash
kubectl get pods -n newsjuice
```
Manually trigger a test
```bash
kubectl create job --from=cronjob/newsjuice-scraper test-scraper3 -n newsjuice
```
5. Watch pods
```bash
kubectl get pods -n newsjuice -w
```
6. Check logs
```bash
kubectl logs -l job-name=test-scraper3 -n newsjuice -c scraper
```


```
Users
  │
  ▼
GKE Ingress (www.newsjuiceapp.com)
  │
  ├── /api/* ──→ Chatter (FastAPI + SQL Proxy) ──→ Cloud SQL
  ├── /ws/*  ──→ Chatter (WebSockets)          ──→ Cloud SQL
  └── /*     ──→ Frontend (Nginx + React)
  
CronJobs (scheduled, not always-on):
  ├── Scraper (6 AM UTC) ──→ Cloud SQL
  └── Loader  (7 AM UTC) ──→ Cloud SQL + Vertex AI
```

```  
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                              NEWSJUICE DEPLOYMENT ARCHITECTURE                          │
└─────────────────────────────────────────────────────────────────────────────────────────┘

                                    ┌──────────────┐
                                    │    USERS     │
                                    │   Browser    │
                                    └──────┬───────┘
                                           │
                                           │ HTTPS
                                           ▼
                              ┌────────────────────────┐
                              │  www.newsjuiceapp.com  │
                              │     (DNS → GKE IP)     │
                              │    136.110.164.121     │
                              └────────────┬───────────┘
                                           │
                                           ▼
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│                                    GOOGLE KUBERNETES ENGINE                              │
│                                    (newsjuice-cluster)                                   │
│  ┌────────────────────────────────────────────────────────────────────────────────────┐  │
│  │                              GKE INGRESS (GCE Load Balancer)                       │  │
│  │                         + Managed SSL Certificate (newsjuice-cert)                 │  │
│  │  ┌──────────────────┬────────────────────────┬──────────────────────────────────┐  │  │
│  │  │    /api/*        │        /ws/*           │            /*                    │  │  │
│  │  │                  │    (WebSockets)        │                                  │  │  │
│  │  └────────┬─────────┴───────────┬────────────┴─────────────────┬────────────────┘  │  │
│  └───────────┼─────────────────────┼──────────────────────────────┼───────────────────┘  │
│              │                     │                              │                      │
│              ▼                     ▼                              ▼                      │
│  ┌─────────────────────────────────────────────┐    ┌─────────────────────────────────┐  │
│  │           CHATTER SERVICE                   │    │      FRONTEND SERVICE           │  │
│  │           (LoadBalancer)                    │    │      (LoadBalancer)             │  │
│  │           Port 80 → 8080                    │    │      Port 80 → 8080             │  │
│  │           + WebSocket BackendConfig         │    │                                 │  │
│  └─────────────────┬───────────────────────────┘    └───────────────┬─────────────────┘  │
│                    │                                                │                    │
│                    ▼                                                ▼                    │
│  ┌─────────────────────────────────────────────┐    ┌─────────────────────────────────┐  │
│  │         CHATTER DEPLOYMENT                  │    │     FRONTEND DEPLOYMENT         │  │
│  │         (2 replicas)                        │    │     (2 replicas)                │  │
│  │  ┌───────────────────────────────────────┐  │    │  ┌───────────────────────────┐  │  │
│  │  │ Pod                                   │  │    │  │ Pod                       │  │  │
│  │  │ ┌─────────────┐  ┌─────────────────┐  │  │    │  │ ┌─────────────────────┐   │  │  │
│  │  │ │  FastAPI    │  │ Cloud SQL Proxy │  │  │    │  │ │   Nginx (8080)      │   │  │  │
│  │  │ │  Uvicorn    │  │   (sidecar)     │  │  │    │  │ │   Static files      │   │  │  │
│  │  │ │  (8080)     │  │   (5432)        │  │  │    │  │ │   React SPA         │   │  │  │
│  │  │ └──────┬──────┘  └────────┬────────┘  │  │    │  │ └─────────────────────┘   │  │  │
│  │  └────────┼──────────────────┼───────────┘  │    │  └───────────────────────────┘  │  │
│  └───────────┼──────────────────┼──────────────┘    └─────────────────────────────────┘  │
│              │                  │                                                        │
│              │                  │ ┌─────────────────────────────────────────────────────┐│
│              │                  │ │              CRONJOBS (Scheduled)                   ││
│              │                  │ │                                                     ││
│              │                  │ │  ┌─────────────────────┐ ┌─────────────────────┐    ││
│              │                  │ │  │  SCRAPER CRONJOB    │ │  LOADER CRONJOB     │    ││
│              │                  │ │  │  Schedule: 6AM UTC  │ │  Schedule: 7AM UTC  │    ││
│              │                  │ │  │                     │ │                     │    ││
│              │                  │ │  │  ┌───────────────┐  │ │  ┌───────────────┐  │    ││
│              │                  │ │  │  │ Scraper Pod   │  │ │  │ Loader Pod    │  │    ││
│              │                  │ │  │  │ + SQL Proxy   │──┼─┼──│ + SQL Proxy   │  │    ││
│              │                  │ │  │  └───────────────┘  │ │  └───────────────┘  │    ││
│              │                  │ │  └─────────────────────┘ └─────────────────────┘    ││
│              │                  │ └──────────────────────────────────┬──────────────────┘│
│              │                  │                                    │                   │
└──────────────┼──────────────────┼────────────────────────────────────┼───────────────────┘
               │                  │                                    │
               │                  └────────────────┬───────────────────┘
               │                                   │
               │                                   ▼
               │                  ┌─────────────────────────────────────┐
               │                  │         CLOUD SQL (PostgreSQL)      │
               │                  │         newsdb-instance             │
               │                  │         + pgvector extension        │
               └──────────────────│                                     │
                                  │  ┌─────────────┐  ┌──────────────┐  │
                                  │  │  articles   │  │chunks_vector │  │
                                  │  │   table     │  │   table      │  │
                                  │  └─────────────┘  └──────────────┘  │
                                  └─────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                                   OTHER GCP SERVICES                                    │
│                                                                                         │
│  ┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────────────────┐  │
│  │  Artifact Registry  │  │   Cloud Storage     │  │       Vertex AI                 │  │
│  │  (Docker images)    │  │   (Audio bucket)    │  │   (Embeddings API)              │  │
│  │                     │  │   Podcast files     │  │   text-embedding-004            │  │
│  │  - loader:latest    │  │                     │  │                                 │  │
│  │  - scraper:latest   │  │                     │  │                                 │  │
│  │  - chatter:latest   │  │                     │  │                                 │  │
│  │  - frontend:latest  │  │                     │  │                                 │  │
│  └─────────────────────┘  └─────────────────────┘  └─────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                                    DATA FLOW                                            │
│                                                                                         │
│  1. SCRAPER (6 AM UTC)                                                                  │
│     └─→ Fetches articles from Harvard news sources                                      │
│     └─→ Stores raw articles in PostgreSQL (articles table)                              │
│                                                                                         │
│  2. LOADER (7 AM UTC)                                                                   │
│     └─→ Reads new articles from PostgreSQL                                              │
│     └─→ Chunks text + generates embeddings via Vertex AI                                │
│     └─→ Stores vectors in PostgreSQL (chunks_vector table with pgvector)                │
│                                                                                         │
│  3. CHATTER (On-demand)                                                                 │
│     └─→ User sends voice/text via WebSocket                                             │
│     └─→ Semantic search on chunks_vector (pgvector similarity)                          │
│     └─→ RAG: Retrieved context + LLM generates response                                 │
│     └─→ TTS generates audio → stored in Cloud Storage                                   │
│     └─→ Audio URL returned to user                                                      │
│                                                                                         │
│  4. FRONTEND (Always-on)                                                                │
│     └─→ React SPA served by Nginx                                                       │
│     └─→ WebSocket connection to Chatter for real-time chat                              │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```
````
─────────────────────────────────────────--------
| Component      | External Port | Internal Port |
|----------------|---------------|---------------|
| Ingress        | :443 (HTTPS)  | -             |
| Services       | :80           | :8080         |
| All containers | -             | :8080         |
| SQL Proxy      | -             | :5432         |
| Cloud SQL      | -             | :5432         |
─────────────────────────────────────────--------
```

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                              NEWSJUICE PORTS DIAGRAM                                    │
└─────────────────────────────────────────────────────────────────────────────────────────┘


                                    ┌──────────────┐
                                    │    USERS     │
                                    └──────┬───────┘
                                           │
                                           │ :443 (HTTPS)
                                           │ :443 (WSS)
                                           ▼
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│                                GKE INGRESS                                               │
│                          (Google Cloud Load Balancer)                                    │
│                                                                                          │
│   External IP: 136.110.164.121                                                           │
│   Listening:   :443 (HTTPS/WSS) with managed SSL cert                                    │
│                :80  (HTTP → redirects to HTTPS)                                          │
└────────────────────────────────────┬─────────────────────────────────────────────────────┘
                                     │
          ┌──────────────────────────┼──────────────────────────┐
          │                          │                          │
          │ /api/*                   │ /ws/*                    │ /*
          │                          │                          │
          ▼                          ▼                          ▼
┌──────────────────────────────────────────────┐    ┌─────────────────────────────────────┐
│         CHATTER-SERVICE (K8s Service)        │    │   FRONTEND-SERVICE (K8s Service)   │
│         Type: LoadBalancer                   │    │   Type: LoadBalancer                │
│                                              │    │                                     │
│   External: :80  ───────┐                    │    │   External: :80  ───────┐           │
│                         │                    │    │                         │           │
│   targetPort: 8080 ◄────┘                    │    │   targetPort: 8080 ◄────┘           │
└──────────────────────────┬───────────────────┘    └───────────────────────┬─────────────┘
                           │                                                │
                           ▼                                                ▼
┌──────────────────────────────────────────────┐    ┌─────────────────────────────────────┐
│              CHATTER POD                     │    │          FRONTEND POD               │
│  ┌─────────────────────────────────────────┐ │    │  ┌───────────────────────────────┐  │
│  │          CHATTER CONTAINER              │ │    │  │      FRONTEND CONTAINER       │  │
│  │                                         │ │    │  │                               │  │
│  │   FastAPI + Uvicorn                     │ │    │  │   Nginx                       │  │
│  │   Listening: :8080                      │ │    │  │   Listening: :8080            │  │
│  │                                         │ │    │  │   (configured in nginx.conf)  │  │
│  │   Endpoints:                            │ │    │  │                               │  │
│  │   - POST /api/chat                      │ │    │  │   Serves:                     │  │
│  │   - WS   /ws/chat                       │ │    │  │   - Static React files        │  │
│  │   - POST /process                       │ │    │  │   - SPA routing (/* → index)  │  │
│  │   - GET  /health                        │ │    │  │                               │  │
│  └────────────────────┬────────────────────┘ │    │  └───────────────────────────────┘  │
│                       │                      │    │                                     │
│                       │ localhost:5432       │    │  (No database connection)           │
│                       ▼                      │    │                                     │
│  ┌─────────────────────────────────────────┐ │    └─────────────────────────────────────┘
│  │       CLOUD-SQL-PROXY CONTAINER         │ │
│  │       (sidecar)                         │ │
│  │                                         │ │
│  │   Listening: :5432                      │ │
│  │   Connects to Cloud SQL via IAM         │ │
│  └────────────────────┬────────────────────┘ │
└───────────────────────┼──────────────────────┘
                        │
                        │ :5432 (PostgreSQL protocol)
                        │ (via private Google network)
                        ▼
┌──────────────────────────────────────────────┐
│              CLOUD SQL                       │
│              (PostgreSQL)                    │
│                                              │
│   Instance: newsdb-instance                  │
│   Listening: :5432                           │
│   Database: newsjuice                        │
└──────────────────────────────────────────────┘


┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                              CRONJOB PODS (Scheduled)                                   │
└─────────────────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────┐    ┌─────────────────────────────────────┐
│              SCRAPER POD                     │    │            LOADER POD               │
│              (Created at 6 AM UTC)           │    │            (Created at 7 AM UTC)    │
│  ┌─────────────────────────────────────────┐ │    │  ┌───────────────────────────────┐  │
│  │          SCRAPER CONTAINER              │ │    │  │       LOADER CONTAINER        │  │
│  │                                         │ │    │  │                               │  │
│  │   FastAPI + Uvicorn                     │ │    │  │   FastAPI + Uvicorn           │  │
│  │   Listening: :8080                      │ │    │  │   Listening: :8080            │  │
│  │                                         │ │    │  │                               │  │
│  │   Triggered by:                         │ │    │  │   Triggered by:               │  │
│  │   curl POST localhost:8080/process      │ │    │  │   curl POST localhost:8080/   │  │
│  │                                         │ │    │  │        process                │  │
│  └────────────────────┬────────────────────┘ │    │  └──────────────┬────────────────┘  │
│                       │                      │    │                 │                   │
│                       │ localhost:5432       │    │                 │ localhost:5432    │
│                       ▼                      │    │                 ▼                   │
│  ┌─────────────────────────────────────────┐ │    │  ┌───────────────────────────────┐  │
│  │       CLOUD-SQL-PROXY CONTAINER         │ │    │  │   CLOUD-SQL-PROXY CONTAINER   │  │
│  │       (sidecar)                         │ │    │  │   (sidecar)                   │  │
│  │       Listening: :5432                  │ │    │  │   Listening: :5432            │  │
│  └────────────────────┬────────────────────┘ │    │  └──────────────┬────────────────┘  │
└───────────────────────┼──────────────────────┘    └─────────────────┼───────────────────┘
                        │                                             │
                        └──────────────────┬──────────────────────────┘
                                           │
                                           │ :5432
                                           ▼
                              ┌────────────────────────┐
                              │       CLOUD SQL        │
                              │       :5432            │
                              └────────────────────────┘


┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                              PORTS SUMMARY TABLE                                        │
└─────────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────┬────────────┬────────────┬─────────────────────────────────────────┐
│ Component           │ External   │ Internal   │ Notes                                   │
├─────────────────────┼────────────┼────────────┼─────────────────────────────────────────┤
│ GKE Ingress         │ :443/:80   │ -          │ SSL termination, routes to services     │
├─────────────────────┼────────────┼────────────┼─────────────────────────────────────────┤
│ chatter-service     │ :80        │ :8080      │ LoadBalancer → Pod                      │
├─────────────────────┼────────────┼────────────┼─────────────────────────────────────────┤
│ frontend-service    │ :80        │ :8080      │ LoadBalancer → Pod                      │
├─────────────────────┼────────────┼────────────┼─────────────────────────────────────────┤
│ Chatter container   │ -          │ :8080      │ FastAPI/Uvicorn                         │
├─────────────────────┼────────────┼────────────┼─────────────────────────────────────────┤
│ Frontend container  │ -          │ :8080      │ Nginx (nginx.conf: listen 8080)         │
├─────────────────────┼────────────┼────────────┼─────────────────────────────────────────┤
│ Scraper container   │ -          │ :8080      │ FastAPI/Uvicorn (CronJob)               │
├─────────────────────┼────────────┼────────────┼─────────────────────────────────────────┤
│ Loader container    │ -          │ :8080      │ FastAPI/Uvicorn (CronJob)               │
├─────────────────────┼────────────┼────────────┼─────────────────────────────────────────┤
│ Cloud SQL Proxy     │ -          │ :5432      │ Sidecar in each pod                     │
├─────────────────────┼────────────┼────────────┼─────────────────────────────────────────┤
│ Cloud SQL           │ -          │ :5432      │ PostgreSQL (private network)            │
└─────────────────────┴────────────┴────────────┴─────────────────────────────────────────┘


┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                              REQUEST FLOW WITH PORTS                                    │
└─────────────────────────────────────────────────────────────────────────────────────────┘

HTTPS Request (API):
  User :443 → Ingress :443 → chatter-service :80 → chatter-pod :8080 → SQL-proxy :5432 → CloudSQL :5432

WebSocket Connection:
  User :443 (wss) → Ingress :443 → chatter-service :80 → chatter-pod :8080 (upgrade to WS)

Static Files:
  User :443 → Ingress :443 → frontend-service :80 → frontend-pod :8080 (nginx)

CronJob (internal):
  Scheduler → Create Pod → uvicorn :8080 & curl localhost:8080/process → SQL-proxy :5432 → CloudSQL :5432
```
