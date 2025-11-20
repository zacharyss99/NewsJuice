# Data versioning


# Get into a virtual environment in the loader_deployed directory
uv venv
source .venv/bin/activate

# INstall dvc and add to pyproject.toml
uv add dvc dvc-gs  
uv sync


Goto into loader_deployed working directoty

# Initialize dvc (in loader_deployed subdirectory)
dvc init --subdir

# Create a GCS bucket for data versions (if not exists)
gsutil mb gs://newsjuice-data-versions-loader

# Tell DVC to use this bucket
dvc remote add -d myremote gs://newsjuice-data-versions-loader/dvc-storage

# Verify configuration
dvc remote list
# Output: myremote gs://newsjuice-data-versions-loader/dvc-storage

# Commit dvc setup to Git
git add .dvc/config .dvc/.gitignore
git commit -m "Initialize DVC with GCS remote"
git push

# Create datastructure
(Inside loader_deployed folder)

# Create directories
mkdir -p scripts/data_versioning
mkdir -p data/exports

# Your structure should look like:
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

Step 5: Create the Versioning Script
Create file: scripts/data_versioning/version_data.py


Step 6: Test the Script Locally
First, make sure you have database access:

# Start Cloud SQL Proxy (in a separate terminal)
cloud-sql-proxy \
  --credentials-file="../../../secrets/sa-key.json" \
  --address 127.0.0.1 --port 5432 \
  newsjuice-123456:us-central1:newsdb-instance

# Set environment variables
export DB_PASS="Newsjuice25+"
export GOOGLE_APPLICATION_CREDENTIALS="../../../secrets/sa-key.json"

# Run the script

# Make script executable
chmod +x scripts/data_versioning/version_data.py

# Run it
export PGHOST=127.0.0.1
export PGPORT=5432
export PGUSER=postgres
export DB_PASS='Newsjuice25+'     
export PGPASSWORD='Newsjuice25+'  
python scripts/data_versioning/version_data.py


Check
git log --oneline -n 3
# Should show: Data version 20251112_143000

ls -lh data/exports/
# Should show: db_export_20251112_143000.sql.dvc (tiny, ~100 bytes)

gsutil ls -lh gs://newsjuice-data-versions-loader/dvc-storage/files/md5/
# Should show: Large SQL files


# RESTORE PREVIOUS VERSION

# List all versions
git log --oneline -- data/exports/

# Checkout a specific version
git checkout <commit-hash> -- data/exports/db_export_20251112_231041.sql.dvc

# Pull the actual data from GCS
dvc pull data/exports/db_export_20251112_231041.sql.dvc

# The SQL file appears in data/exports/
# Import to database
psql -h ... -f data/exports/db_export_20251112_231041.sql


# AUTOMATE WITH SCHEDULER




*******
Option 6 was the Hybrid Approach - combining DVC + PostgreSQL exports for data versioning.
Here's what it does:
The Workflow:

Export database → Create SQL dump of your tables (articles + chunks_vector)
Track with DVC → DVC creates a small pointer file (.dvc)
Commit to Git → Git tracks the pointer, not the actual data
Push to GCS → DVC uploads the actual SQL file to Google Cloud Storage
Link versions to code → Each data version is tied to a Git commit

Why it's "Hybrid":
DVC (Data Version Control):

Handles large data files
Stores them efficiently in GCS
Links data versions to code versions

PostgreSQL Snapshots:

Full database state capture
Easy to restore
Human-readable SQL format

Git:

Tracks when versions were created
Links data versions to code changes
Lightweight (only stores pointers)

What You Get:
