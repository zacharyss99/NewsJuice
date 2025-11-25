# Explanation of the main files in the repository.

**/.github/**
Contains the workflow file for the CI/CD GitHub Actions workflow (ci_full.yaml)

**/docs/**  

- The **/services/** folder contains folders each of which is a self-contained containerized micro-service:

- **/scraper_deployed/**
scraper version - currently deployed on Cloud Run and running on Scheduler every 24 h

- **/loader_deployed/**
loader version - currently deployed on Cloud Run and running on Scheduler every 24 h

- **/loader_testing/**
A version of the loader service with a full test suit added (incl. CI/CD workflow)

- **/chatter_deployed/**
Contains the version of the chatter service 

- **/frontend/**
Contains the frontend

- **/finetuning/**
Contains the finetuning exercise for the LLM used for ppodcast generation.

- **/data_versioner/**
Contains the files for the Data Versioning module (hybrid SQL snapshot + DVC)

**/Finetuning/**
Contains the files for the LLM model finetuning

**/Archive/**
Older files and versions (not relevant for submission)
