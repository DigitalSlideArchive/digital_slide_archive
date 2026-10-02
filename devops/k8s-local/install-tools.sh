#!/bin/bash
# Install the local Kubernetes tooling (kubectl, helm, kind) into
# ~/.local/bin.  This does not require root.
#
# Usage:
#   ./install-tools.sh
#
# Set K8S_TOOLS_DIR to install somewhere other than ~/.local/bin.
set -euo pipefail

K8S_TOOLS_DIR=${K8S_TOOLS_DIR:-$HOME/.local/bin}

# Pin versions so local testing matches what the README documents.
KUBECTL_VERSION=${KUBECTL_VERSION:-v1.31.4}
HELM_VERSION=${HELM_VERSION:-v3.16.4}
KIND_VERSION=${KIND_VERSION:-v0.25.0}

mkdir -p "$K8S_TOOLS_DIR"

arch=amd64
case "$(uname -m)" in
  x86_64) arch=amd64 ;;
  aarch64|arm64) arch=arm64 ;;
  *)
    echo "Unsupported architecture: $(uname -m)" >&2
    exit 1
    ;;
esac

tmpdir=$(mktemp -d)
trap 'rm -rf "$tmpdir"' EXIT

echo "Installing kubectl $KUBECTL_VERSION"
curl -fsSL "https://dl.k8s.io/release/${KUBECTL_VERSION}/bin/linux/${arch}/kubectl" \
  -o "$K8S_TOOLS_DIR/kubectl"
chmod +x "$K8S_TOOLS_DIR/kubectl"

echo "Installing kind $KIND_VERSION"
curl -fsSL "https://kind.sigs.k8s.io/dl/${KIND_VERSION}/kind-linux-${arch}" \
  -o "$K8S_TOOLS_DIR/kind"
chmod +x "$K8S_TOOLS_DIR/kind"

echo "Installing helm $HELM_VERSION"
curl -fsSL "https://get.helm.sh/helm-${HELM_VERSION}-linux-${arch}.tar.gz" \
  -o "$tmpdir/helm.tgz"
tar -xzf "$tmpdir/helm.tgz" -C "$tmpdir"
cp "$tmpdir/linux-${arch}/helm" "$K8S_TOOLS_DIR/helm"
chmod +x "$K8S_TOOLS_DIR/helm"

echo
echo "Installed into $K8S_TOOLS_DIR:"
"$K8S_TOOLS_DIR/kubectl" version --client
"$K8S_TOOLS_DIR/kind" version
"$K8S_TOOLS_DIR/helm" version --short

case ":$PATH:" in
  *":$K8S_TOOLS_DIR:"*) ;;
  *)
    echo
    echo "NOTE: $K8S_TOOLS_DIR is not on your PATH.  Add it, for example:"
    echo "  export PATH=\"$K8S_TOOLS_DIR:\$PATH\""
    ;;
esac
