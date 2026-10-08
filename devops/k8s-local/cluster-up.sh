#!/bin/bash
# Create (or reuse) the local kind Kubernetes cluster used for testing the
# Digital Slide Archive Helm charts.
#
# Usage:
#   ./cluster-up.sh
#
# Environment:
#   KIND_CLUSTER_NAME  cluster name (default: dsa-local)
#   K8S_TOOLS_DIR      directory holding kubectl/helm/kind (default: ~/.local/bin)
set -euo pipefail

script_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
KIND_CLUSTER_NAME=${KIND_CLUSTER_NAME:-dsa-local}
export KIND_CLUSTER_NAME

if ! command -v docker >/dev/null 2>&1; then
  echo "ERROR: docker is required." >&2
  exit 1
fi

if [[ ! -x "$script_dir/install-tools.sh" ]]; then
  echo "ERROR: install-tools.sh not found next to this script." >&2
  exit 1
fi

if [[ ! -x "${K8S_TOOLS_DIR:-$HOME/.local/bin}/kind" ]] \
   && ! command -v kind >/dev/null 2>&1; then
  echo "Local tools not found; running install-tools.sh"
  "$script_dir/install-tools.sh"
fi

export PATH="${K8S_TOOLS_DIR:-$HOME/.local/bin}:$PATH"

if kind get clusters 2>/dev/null | grep -qx "$KIND_CLUSTER_NAME"; then
  echo "Cluster '$KIND_CLUSTER_NAME' already exists; reusing it."
else
  echo "Creating kind cluster '$KIND_CLUSTER_NAME'..."
  kind create cluster --config "$script_dir/kind-config.yaml"
fi

echo
echo "Waiting for the control plane to be ready (may take a while)..."
# Source the wrapper so kubectl works even where host port publishing is broken.
# shellcheck source=k8s.sh
source "$script_dir/k8s.sh"

deadline=$((SECONDS + 300))
until kubectl get nodes 2>/dev/null | grep -q ' Ready'; do
  if (( SECONDS > deadline )); then
    echo "ERROR: cluster did not become ready in time." >&2
    exit 1
  fi
  sleep 5
done

echo
kubectl get nodes
echo
kubectl get storageclass
echo
echo "Cluster '$KIND_CLUSTER_NAME' is ready."
echo "Next: ./deploy-dsa.sh dsa3   (or dsa5)"
