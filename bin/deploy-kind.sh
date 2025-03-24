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

kubectl apply -f https://kind.sigs.k8s.io/examples/ingress/deploy-ingress-nginx.yaml
# Wait for the ingress-nginx namespace to be created
echo "Waiting for ingress-nginx pod to be created..."
# sleep 20
# kubectl wait --namespace ingress-nginx \
#   --for=condition=ready pod \
#   --selector=app.kubernetes.io/component=controller \
#   --timeout=90s

flux install --components="source-controller,kustomize-controller,helm-controller"

flux create source git flux-system \
  --url="https://github.com/forselli/akamai-sre-home-assignment" \
  --branch="main" \
  --username="forselli" \
  --password="${GITHUB_PAT}"

flux create kustomization flux-system \
  --source=flux-system \
  --path=./clusters/staging
# kubectl create ns demo
# helm install postgres -n demo deploy/helm/postgres --wait
# helm install redis -n demo deploy/helm/redis --wait
# helm install app -n demo deploy/helm/app --wait
