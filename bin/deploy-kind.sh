#!/bin/bash
set -e

# Check if required environment variables are defined
: "${GITHUB_PAT:?Environment variable GITHUB_PAT is not set}"
: "${GITHUB_URL:?Environment variable GITHUB_URL is not set}"
: "${GITHUB_BRANCH:?Environment variable GITHUB_BRANCH is not set}"
: "${GITHUB_USERNAME:?Environment variable GITHUB_USERNAME is not set}"

echo "Creating kind cluster"
cat <<EOF | kind create cluster --config=-
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
nodes:
- role: control-plane
  extraPortMappings:
  - containerPort: 80
    hostPort: 80
    protocol: TCP
  - containerPort: 443
    hostPort: 443
    protocol: TCP
EOF
kind load docker-image my-registry:5001/app:forselli

# Install Flux
flux install --components="source-controller,kustomize-controller,helm-controller"

# Create Flux main source
flux create source git flux-system \
  --url="${GITHUB_URL}" \
  --branch="${GITHUB_BRANCH}" \
  --username="${GITHUB_USERNAME}" \
  --password="${GITHUB_PAT}"

# Create Flux main kustomization
flux create kustomization flux-system \
  --source=flux-system \
  --path=./clusters/staging

# Verify all resources are ready
kubectl -n flux-system wait kustomization/apps-prerequisites --for=condition=ready --timeout=5m
kubectl -n flux-system wait kustomization/apps --for=condition=ready --timeout=5m
kubectl -n demo wait helmrelease/postgres --for=condition=ready --timeout=5m
kubectl -n demo wait helmrelease/redis --for=condition=ready --timeout=5m
kubectl -n demo wait helmrelease/app --for=condition=ready --timeout=5m
