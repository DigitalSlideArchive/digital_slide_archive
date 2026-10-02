#!/bin/bash
# Delete the local kind Kubernetes cluster.
#
# Usage:
#   ./cluster-down.sh
#
# Environment:
#   KIND_CLUSTER_NAME  cluster name (default: dsa-local)
#   K8S_TOOLS_DIR      directory holding kind (default: ~/.local/bin)
set -euo pipefail

KIND_CLUSTER_NAME=${KIND_CLUSTER_NAME:-dsa-local}
export PATH="${K8S_TOOLS_DIR:-$HOME/.local/bin}:$PATH"

if ! command -v kind >/dev/null 2>&1; then
  echo "ERROR: kind not found.  Run install-tools.sh first." >&2
  exit 1
fi

if kind get clusters 2>/dev/null | grep -qx "$KIND_CLUSTER_NAME"; then
  kind delete cluster --name "$KIND_CLUSTER_NAME"
else
  echo "No kind cluster named '$KIND_CLUSTER_NAME'."
fi

# Remove the helper image and container used when host port publishing is
# unavailable.
docker rm -f dsa-k8s-helper-run >/dev/null 2>&1 || true
docker rmi dsa-k8s-helper:local >/dev/null 2>&1 || true
