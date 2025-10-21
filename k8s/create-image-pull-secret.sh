#!/bin/bash
# Script to create GHCR image pull secret in Kubernetes

set -e

# Get GitHub username
GH_USERNAME=$(gh api user -q .login)

# Get GitHub token
GH_TOKEN=$(gh auth token)

# Create namespace if it doesn't exist
kubectl create namespace mealie-mcp --dry-run=client -o yaml | kubectl apply -f -

# Create docker-registry secret
kubectl create secret docker-registry ghcr-secret \
  --namespace=mealie-mcp \
  --docker-server=ghcr.io \
  --docker-username="${GH_USERNAME}" \
  --docker-password="${GH_TOKEN}" \
  --docker-email="${GH_USERNAME}@users.noreply.github.com" \
  --dry-run=client -o yaml | kubectl apply -f -

echo "✓ Image pull secret 'ghcr-secret' created in namespace 'mealie-mcp'"
echo "✓ Using GitHub user: ${GH_USERNAME}"
