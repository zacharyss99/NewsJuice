# Loader testing notes

## Black (with container)

Run with mount so black changes code in origin
```bash
docker run --rm \
  -v $(pwd)/src/api-service/api:/app/api \
  loader-app-api:local \
  black api/
```


Rebuild after modifications by black
```bash
docker build -t loader-app-api:local -f Dockerfile .
```

Check with black - should now be clean
```bash
docker run --rm loader-app-api:local black --check api/
```

## Flake8

Check code quality with flake
```bash
flake8 src/api-service/api/
```

let black reformat
```bash
black src/api-service/api/
```

# PYTEST

## Unit tests

Execute the unit test
```bash
DATABASE_URL="postgresql://test:test@localhost:5432/testdb" \
GOOGLE_CLOUD_PROJECT="test-project" \
uv run pytest tests/unit/test_utils.py -v --cov=api --cov-report=html
```

Get the report:
```bash
open htmlcov/index.html
```

=====Appendix
Run this specific test file
```bash
uv run pytest tests/unit/test_chunking_simple.py -v
```
Run with details
```bash
uv run pytest tests/unit/test_chunking_simple.py -v -s
```
Run just one test
```bash
uv run pytest tests/unit/test_chunking_simple.py::test_character_chunking_creates_chunks -v
```
===========

## Integration tests

Integration test (no container)
```bash
DATABASE_URL="postgresql://dummy" GOOGLE_CLOUD_PROJECT="test-project" \
  uv run pytest tests/integration/ -v --cov-fail-under=50
```

Integration test (container)

Build the image first
```bash
docker build -t loader-app-api:local .
```
Run integration tests only
```bash
docker run --rm \
  -e DATABASE_URL="postgresql://dummy" \
  -e GOOGLE_CLOUD_PROJECT="test-project" \
  loader-app-api:local \
  pytest tests/integration/ -v
```



## System tests

Need to use a real DB now.

Use a docker-compose (docker-compose.test.yml) as we need to spin up DB for testing
and also initialize tables.
Initialization uses tests/setup/init_test_db.sql to create tables in temporary local DB
Will use real VertexAI calls for embeddings

Authenticate (if not already done)
```bash
gcloud auth application-default login
```

Verify credentials exist
```bash
ls -la ~/.config/gcloud/application_default_credentials.json
```
Clean up and start fresh
```bash
docker-compose -f docker-compose.test.yml down -v  # ← The -v removes volumes
docker-compose -f docker-compose.test.yml up --build --abort-on-container-exit
```

✅ Tests with real Google Cloud Vertex AI embeddings
✅ Validates the complete end-to-end pipeline
✅ Shows you the actual embedding values
✅ Runs in isolated Docker environment

(
issues encountered, stuff learned:
* local test PostgresSQL DB
* google cloud login and creation of credential file in ~/......... for VertexAI
* after FastAPI server starts, how to continue flow
* no coverage for system tests?
)


# GitHub Actions
With system test (needs credentials)

Use **.github/workflows/ci.yaml** file

then execute:
```bash
git add .github/workflows/ci.yml
git commit -m "Add simple CI for unit tests"
git push
```






Recommended Structure
```
.github/
└── workflows/
    ├── ci.yml              # Fast tests on every push
    ├── integration.yml     # Integration tests with DB
    └── system-tests.yml    # Manual/scheduled system tests (costs money)

tests/
├── unit/               # Fast, no external dependencies
├── integration/        # Database, mocked AI
└── system/            # Full stack, real AI (run locally or manually)
```

Set up SA and credentials

Create service account
```bash
gcloud iam service-accounts create github-actions-ci \
  --display-name="GitHub Actions CI" \
  --project=newsjuice-123456
```
Grant necessary permissions
```bash
gcloud projects add-iam-policy-binding newsjuice-123456 \
  --member="serviceAccount:github-actions-ci@newsjuice-123456.iam.gserviceaccount.com" \
  --role="roles/aiplatform.user"
```
Create and download key
```bash
gcloud iam service-accounts keys create github-actions-key.json \
  --iam-account=github-actions-ci@newsjuice-123456.iam.gserviceaccount.com
```

Paste the key to the Clipboard
```bash
cat github-actions-key.json | pbcopy
```

Add Secret to GitHub

Go to your GitHub repo → Settings → Secrets and variables → Actions
Click "New repository secret"
Name: GCP_SA_KEY
Value: Paste the entire contents of github-actions-key.json


# *****


Start the API server
docker run -d --name api-server -p 8080:8080 -e DEV=1 loader-app-api:local

Run system tests against the live server
docker run --rm --network host loader-app-api:local pytest tests/system/ -v

Clean up when done
docker stop api-server && docker rm api-server


DIRECTLY:
Run with pytest (standard way)

```bash
uv run pytest tests/integration/test_api_simple.py -v
```








Run as a Python script (educational mode with output)
```bash
uv run python tests/integration/test_api_simple.py
```

Run just one test
```bash
uv run pytest tests/integration/test_api_simple.py::TestBasicFunctionality::test_health_check -v
```
