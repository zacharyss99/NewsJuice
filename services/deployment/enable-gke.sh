#!/bin/bash
# Enable GKE and deploy

echo "=== Current Pulumi Stack ==="
pulumi stack ls

echo -e "\n=== Checking current configuration ==="
pulumi config

echo -e "\n=== Enabling GKE ==="
pulumi config set enable_gke true
pulumi config set enable_cloudrun true
pulumi config set gke_node_count 2
pulumi config set gke_machine_type e2-standard-2
pulumi config set db_instance_name newsdb-instance
pulumi config set db_name newsdb
pulumi config set db_user postgres

echo -e "\n=== Updated configuration ==="
pulumi config

echo -e "\n=== Ready to deploy ==="
echo "Run 'pulumi up' to create the GKE cluster and deploy your services"
