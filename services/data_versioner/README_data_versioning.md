# Data versioning

Content:  
1. Chose method  
1.1. Description and workflow  
1.2. Justification    
2. Set-up instructions  
3. Usage  


### 1. Chosen method

#### 1.1. Description and workflow

The target for data versioning are the articles and chunks vector tables of the NewsJuice app PostgresSQL database.  

We apply here a hybrid approach - combining DVC + PostgreSQL exports for data versioning.  
The Workflow:  
- Export database → Create SQL dump of your tables (articles + chunks_vector)
- Track with DVC → DVC creates a small pointer file (.dvc)
- Commit to Git → Git tracks the pointer, not the actual data
- Push to GCS → DVC uploads the actual SQL file to Google Cloud Storage
- Link versions to code → Each data version is tied to a Git commit

It handles large data files and tores them efficiently in GCS. It links data versions to code versions
PostgreSQL Snapshots provide a Full database state capture and are easy to restore. It is in Human-readable SQL format.  

Role of Git:
- Tracks when versions were created
- Links data versions to code changes
- Lightweight (only stores pointers)


#### 1.2. Justification  

We use hybrid PostgreSQL plus DVC data-versioning because it provide complete and restorable snapshots of the database. DVC versions these (potentially large) database files and stores them in a bucket in GCS. Each data version directly to the corresponding Git commit. This provides reproducibility, traceability, and scalable storage. The approach avoids that Git has to store large binary files.



### 2. SET-UP INSTRUCTIONS

Get into a virtual environment in the loader_deployed directory
```bash
uv venv
source .venv/bin/activate
```

Create package structure
```bash
mkdir data_versioner
touch data_versioner/__init__.py
```
Create pyproject.toml
```bash
cat > pyproject.toml << 'EOF'
[project]
name = "data-versioner"
version = "0.1.0"
description = "Data versioning with DVC"
requires-python = ">=3.11"
dependencies = []

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/data_versioner"]
EOF
```

Install dvc and add to pyproject.toml
```bash
uv add dvc dvc-gs
uv sync
```

Goto into loader_deployed working directoty

Initialize dvc (in loader_deployed subdirectory)
```bash
dvc init --subdir
```

Create a GCS bucket for data versions (if not exists)
```bash
gsutil mb gs://newsjuice-data-versions-loader
```

Tell DVC to use this bucket
```bash
dvc remote add -d myremote gs://newsjuice-data-versions-loader/dvc-storage
```
Verify configuration
```bash
dvc remote list
```
Output:  
myremote gs://newsjuice-data-versions-loader/dvc-storage

Commit dvc setup to Git
```bash
git add .dvc/config .dvc/.gitignore
git commit -m "Initialize DVC with GCS remote"
git push
```

Create datastructure
(Inside loader_deployed folder)

Create directories
```bash
mkdir -p scripts/data_versioning
mkdir -p data/exports
```

Your structure should look like:
```
services/loader_deployed/
├── .dvc/                      ← DVC config
├── data/
│   └── exports/               ← Database exports go here
│       └── .gitignore         ← Auto-created by DVC
├── scripts/
│   └── version_data.py        ← Versioning script
├── logs/                      ← Your log files
├── loader.py
├── main.py
├── pyproject.toml
├── Dockerfile
└── docker-compose.local.yml
```

Create the Versioning Script  
Create file: **scripts/data_versioning/version_data.py**


Test the Script Locally  
First, make sure you have database access:  

Start Cloud SQL Proxy (in a separate terminal)
```bash
cloud-sql-proxy \
  --credentials-file="../../../secrets/sa-key.json" \
  --address 127.0.0.1 --port 5432 \
  newsjuice-123456:us-central1:newsdb-instance
```

Set environment variables
```bash
export DB_PASS="Newsjuice25+"
export GOOGLE_APPLICATION_CREDENTIALS="../../../secrets/sa-key.json"
```

Run the script:

Make script executable
```bash
chmod +x scripts/data_versioning/version_data.py
```

Then run it
```bash
export PGHOST=127.0.0.1
export PGPORT=5432
export PGUSER=postgres
export DB_PASS='Newsjuice25+'
export PGPASSWORD='Newsjuice25+'
python scripts/data_versioning/version_data.py
```

Check 1:
```bash
git log --oneline -n 3
```
Should show (example): Data version 20251112_143000  

Check 2:
```bash
ls -lh data/exports/
```
Should show: db_export_20251112_143000.sql.dvc (tiny, ~100 bytes)

Check 3:  
```bash
gsutil ls -lh gs://newsjuice-data-versions-loader/dvc-storage/files/md5/
```
Should show: Large SQL files


### 3. USAGE

### 3.1. Trigger dvc / snapshot

### 3.2. Restore a previous version

List all versions  
Make sure you are in directory **services/data-versioner**
```bash
git log --oneline -- data/exports/
```
Checkout a specific version
```bash
git checkout <commit-hash> -- data/exports/db_export_20251112_231041.sql.dvc
```

Pull the actual data from GCS
```bash
dvc pull data/exports/db_export_20251112_231041.sql.dvc
```

The SQL file appears in data/exports/  

Import to database  
```bash
psql -h ... -f data/exports/db_export_20251112_231041.sql
```



# Further checks

Check status (up to date?):
dvc status

See what's being tracked:
dvc list . --dvc-only


### 3.X Create new version:
# After your data has changed

Make sure right env and directory
```bash
uv venv
source .venv/bin/activate
```
```bash
dvc add data/
git add data.dvc .gitignore
git commit -m "Data version $(date +%Y%m%d_%H%M%S)"
dvc push
git push
```
# after generating new export(s) into data/
dvc add data/
git add data.dvc
git commit -m "Data version $(date +%Y%m%d_%H%M%S)"
dvc push
git push



## Pull specific version

Checkout a specific commit
```bash
git checkout <commit-hash>
```

See commit hashs (fingerprint of each snapshot)
```bash
git log --oneline
git rev-parse HEAD # recent commit
git rev-parse --short HEAD # short
git log --oneline --graph --all # graph form
```

Pull the corresponding data
```bash
dvc pull
```

## See version history
```bash
git log --oneline --all -- data.dvc
```





git rm -r --cached data
git commit -m "Stop tracking data/ in Git; managed by DVC instead"
dvc add data/
this creates data.dvc and data/.gitignore

git add data.dvc data/.gitignore
git commit -m "Version data/ with DVC"

dvc push     # uploads the actual data to your DVC remote (e.g. GCS)
git push     # pushes the .dvc pointer and .gitignore

What your setup looks like after this

Git:

Tracks data.dvc and data/.gitignore

No longer tracks raw dump files inside data/

DVC:

Owns data/ and its contents

Handles big files, deduplication, and remote storage

