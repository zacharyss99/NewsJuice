#!/bin/bash
# Quick deployment check script

echo "=== Pulumi Stack Outputs ==="
pulumi stack output

echo -e "\n=== Configuring kubectl ==="
gcloud container clusters get-credentials newsjuice-cluster --zone=us-central1-a --project=newsjuice-123456

echo -e "\n=== Checking Pods Status ==="
kubectl get pods -n newsjuice

echo -e "\n=== Checking Services ==="
kubectl get services -n newsjuice

echo -e "\n=== Checking Ingress ==="
kubectl get ingress -n newsjuice

echo -e "\n=== Checking Managed Certificate Status ==="
kubectl describe managedcertificate newsjuice-cert -n newsjuice

echo -e "\n=== Getting Ingress Details ==="
kubectl describe ingress newsjuice-ingress -n newsjuice
