#!/bin/bash
# Install one of the DSA Helm charts into the local kind cluster.
#
# Usage:
#   ./deploy-dsa.sh [dsa3|dsa5] [release-name]
#
# Defaults to dsa5 and the release name "dsa".
#
# Environment:
#   KIND_CLUSTER_NAME  cluster name (default: dsa-local)
#   K8S_TOOLS_DIR      directory holding kubectl/helm/kind (default: ~/.local/bin)
#   TIMEOUT            rollout timeout in seconds (default: 600)
set -euo pipefail

chart=${1:-dsa5}
release=${2:-dsa}
case "$chart" in
  dsa3|dsa5) ;;
  *) echo "Usage: $0 [dsa3|dsa5] [release-name]" >&2; exit 2 ;;
esac

script_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
KIND_CLUSTER_NAME=${KIND_CLUSTER_NAME:-dsa-local}
export KIND_CLUSTER_NAME
TIMEOUT=${TIMEOUT:-600}

# shellcheck source=k8s.sh
source "$script_dir/k8s.sh"

if ! kubectl get nodes >/dev/null 2>&1; then
  echo "ERROR: cannot reach the cluster.  Run ./cluster-up.sh first." >&2
  exit 1
fi

echo "Installing chart '$chart' as release '$release'..."
helm upgrade --install "$release" "$script_dir/charts/$chart" \
  --wait --timeout "${TIMEOUT}s"

echo
kubectl get pods
echo
kubectl get svc
echo
echo "Done.  See README.rst for how to reach the web interface."
