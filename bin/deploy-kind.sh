#!/bin/bash

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

flux install --components="source-controller,kustomize-controller,helm-controller"

flux create source git flux-system \
  --url="https://github.com/forselli/akamai-sre-home-assignment" \
  --branch="main" \
  --username="forselli" \
  --password="${GITHUB_PAT}"

flux create kustomization flux-system \
  --source=flux-system \
  --path=./clusters/staging
