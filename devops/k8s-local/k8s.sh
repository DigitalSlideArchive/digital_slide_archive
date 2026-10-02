#!/bin/bash
# kubectl/helm wrapper that works both on a normal workstation and in
# sandboxes where Docker's host port publishing and bind mounts do not
# function.
#
# Background: kind publishes the Kubernetes API server to a random port on
# 127.0.0.1.  On a normal host, `kubectl` can use the generated kubeconfig
# directly.  In some container sandboxes the port mapping never gets a
# listener and bind mounts do not propagate files, so this script builds a
# small helper image containing the tools plus a kubeconfig adjusted to the
# node's bridge IP.  Files that must be visible to kubectl/helm (charts,
# manifests) are copied in with `docker cp`.
#
# Usage:
#   source ./k8s.sh          # defines kubectl() and helm()
#   ./k8s.sh kubectl get nodes
#   ./k8s.sh helm list -A
#
# Environment:
#   KIND_CLUSTER_NAME  kind cluster name (default: dsa-local)
#   K8S_TOOLS_DIR      directory holding kubectl/helm/kind (default: ~/.local/bin)
#   FORCE_IN_NETWORK   set to 1 to always use the in-network helper container
#                      even if the host can reach the API server.

KIND_CLUSTER_NAME=${KIND_CLUSTER_NAME:-dsa-local}
K8S_TOOLS_DIR=${K8S_TOOLS_DIR:-$HOME/.local/bin}
FORCE_IN_NETWORK=${FORCE_IN_NETWORK:-0}

_K8S_SH_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
_K8S_HELPER_IMAGE="dsa-k8s-helper:local"
_K8S_HELPER_CONTAINER="dsa-k8s-helper-run"

_k8s_tool() {
  local name=$1
  if [[ -x "$K8S_TOOLS_DIR/$name" ]]; then
    echo "$K8S_TOOLS_DIR/$name"
  elif command -v "$name" >/dev/null 2>&1; then
    command -v "$name"
  else
    echo "ERROR: $name not found.  Run $(_K8S_SH_DIR)/install-tools.sh first." >&2
    return 1
  fi
}

_k8s_node_container() {
  docker ps --filter "label=io.x-k8s.kind.cluster=${KIND_CLUSTER_NAME}" \
    --filter "label=io.x-k8s.kind.role=control-plane" \
    --format '{{.Names}}' | head -1
}

# Return 0 if the host can reach the API server from the kubeconfig.
_k8s_host_can_reach_api() {
  [[ "$FORCE_IN_NETWORK" == "1" ]] && return 1
  local kubectl
  kubectl=$(_k8s_tool kubectl) || return 1
  local server
  server=$("$kubectl" config view --minify -o jsonpath='{.clusters[0].cluster.server}' 2>/dev/null) || return 1
  [[ -z "$server" ]] && return 1
  local hostport=${server#https://}
  hostport=${hostport#http://}
  hostport=${hostport%%/*}
  local host=${hostport%%:*}
  local port=${hostport##*:}
  timeout 15 bash -c "exec 3<>/dev/tcp/${host}/${port}" 2>/dev/null
}

# Build the helper image with tools + adjusted kubeconfig.
_k8s_build_helper() {
  local node_container node_ip
  node_container=$(_k8s_node_container)
  if [[ -z "$node_container" ]]; then
    echo "ERROR: no kind control-plane container for cluster '$KIND_CLUSTER_NAME'." >&2
    echo "       Start it with: ./cluster-up.sh" >&2
    return 1
  fi
  node_ip=$(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' "$node_container")
  if [[ -z "$node_ip" ]]; then
    echo "ERROR: could not determine IP of $node_container" >&2
    return 1
  fi

  local kubectl helm ctx
  kubectl=$(_k8s_tool kubectl) || return 1
  helm=$(_k8s_tool helm) || return 1

  local build_dir
  build_dir=$(mktemp -d)
  trap 'rm -rf "$build_dir"' RETURN
  cp "$kubectl" "$build_dir/kubectl"
  cp "$helm" "$build_dir/helm"
  sed -e "s#https://127.0.0.1:[0-9]*#https://${node_ip}:6443#g" \
    -e "s#https://localhost:[0-9]*#https://${node_ip}:6443#g" \
    "$HOME/.kube/config" > "$build_dir/kubeconfig"

  cat > "$build_dir/Dockerfile" <<'EOF'
FROM alpine:latest
RUN apk add --no-cache ca-certificates bash
COPY kubectl /usr/local/bin/kubectl
COPY helm /usr/local/bin/helm
RUN mkdir -p /root/.kube
COPY kubeconfig /root/.kube/config
RUN chmod 600 /root/.kube/config
ENV HOME=/root
ENTRYPOINT []
CMD ["sleep", "infinity"]
EOF

  if ! docker build -q -t "$_K8S_HELPER_IMAGE" "$build_dir" >/dev/null; then
    echo "ERROR: failed to build helper image." >&2
    return 1
  fi
  echo "$node_ip"
}

# Ensure a long-running helper container exists on the kind network.
_k8s_ensure_helper_container() {
  if docker ps --format '{{.Names}}' | grep -qx "$_K8S_HELPER_CONTAINER"; then
    return 0
  fi
  docker rm -f "$_K8S_HELPER_CONTAINER" >/dev/null 2>&1 || true
  _k8s_build_helper >/dev/null || return 1
  docker run -d --rm --name "$_K8S_HELPER_CONTAINER" \
    --network kind "$_K8S_HELPER_IMAGE" sleep infinity >/dev/null
}

# Copy a file or directory into the helper container, preserving absolute
# paths under /work so relative references work.
_k8s_copy_in() {
  local src=$1 dest=$2
  docker exec "$_K8S_HELPER_CONTAINER" mkdir -p "$(dirname "$dest")"
  docker cp "$src" "$_K8S_HELPER_CONTAINER:$dest"
}

# Run kubectl/helm inside the helper container.
#
# Files referenced by absolute path in the arguments are copied in first.
# Anything under the current directory is copied so relative paths resolve
# under /work.
_k8s_run_in_network() {
  _k8s_ensure_helper_container || return 1

  local cwd
  cwd=$(pwd)
  # Copy the current directory into /work once per invocation.  This is cheap
  # for the small charts/manifests we use here.
  if [[ -d "$cwd" ]]; then
    docker exec "$_K8S_HELPER_CONTAINER" mkdir -p /work 2>/dev/null || true
    docker cp "$cwd/." "$_K8S_HELPER_CONTAINER:/work/" >/dev/null 2>&1 || true
  fi

  docker exec -w /work -e HOME=/root "$_K8S_HELPER_CONTAINER" "$@"
}

kubectl() {
  if _k8s_host_can_reach_api; then
    "$(_k8s_tool kubectl)" "$@"
  else
    _k8s_run_in_network kubectl "$@"
  fi
}

helm() {
  if _k8s_host_can_reach_api; then
    "$(_k8s_tool helm)" "$@"
  else
    _k8s_run_in_network helm "$@"
  fi
}

kind() {
  "$(_k8s_tool kind)" "$@"
}

# Stop the helper container (called by cluster-down.sh).
_k8s_stop_helper() {
  docker rm -f "$_K8S_HELPER_CONTAINER" >/dev/null 2>&1 || true
}

# Allow direct invocation: ./k8s.sh kubectl ... / ./k8s.sh helm ...
if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  cmd=${1:-}
  shift || true
  case "$cmd" in
    kubectl|helm|kind) "$cmd" "$@" ;;
    *)
      echo "Usage: $0 {kubectl|helm|kind} [args...]" >&2
      exit 2
      ;;
  esac
fi
