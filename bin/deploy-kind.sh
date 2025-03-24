#!/bin/bash
set -e
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
kind load docker-image app:forselli

# Install Flux
flux install --components="source-controller,kustomize-controller,helm-controller"

# Create Flux main source
flux create source git flux-system \
  --url="https://github.com/forselli/akamai-sre-home-assignment" \
  --branch="main" \
  --username="forselli" \
  --password="${GITHUB_PAT}"

# Create Flux main kustomization
flux create kustomization flux-system \
  --source=flux-system \
  --path=./clusters/staging

# Verify all resources are ready
kubectl -n ingress-nginx wait kustomization/ingress-nginx --for=condition=ready --timeout=5m
kubectl -n flux-system wait kustomization/apps --for=condition=ready --timeout=5m
kubectl -n demo wait helmrelease/postgres --for=condition=ready --timeout=5m
kubectl -n demo wait helmrelease/redis --for=condition=ready --timeout=5m
kubectl -n demo wait helmrelease/app --for=condition=ready --timeout=5m
