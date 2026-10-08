#!/bin/bash
# Uninstall a DSA Helm release and remove its persistent volume claims.
#
# Usage:
#   ./undeploy-dsa.sh [release-name]
#
# Defaults to the release name "dsa".
#
# Environment:
#   KIND_CLUSTER_NAME  cluster name (default: dsa-local)
#   K8S_TOOLS_DIR      directory holding kubectl/helm/kind (default: ~/.local/bin)
set -euo pipefail

release=${1:-dsa}
script_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
KIND_CLUSTER_NAME=${KIND_CLUSTER_NAME:-dsa-local}
export KIND_CLUSTER_NAME

# shellcheck source=k8s.sh
source "$script_dir/k8s.sh"

if helm status "$release" >/dev/null 2>&1; then
  echo "Uninstalling release '$release'..."
  helm uninstall "$release"
else
  echo "No Helm release named '$release'."
fi

# Helm does not remove PVCs created by the chart.  Delete the ones we manage so
# a subsequent install starts clean.
echo "Removing PersistentVolumeClaims for '$release'..."
kubectl delete pvc -l "app.kubernetes.io/instance=$release" --ignore-not-found

echo "Done."
