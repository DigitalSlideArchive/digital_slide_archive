========================================================
Digital Slide Archive on Kubernetes (local test harness)
========================================================

This directory contains a local Kubernetes test harness and sample Helm
charts for the Digital Slide Archive (DSA).  It is intended for local
development and chart validation, not for production use.

Two charts are provided:

- ``charts/dsa3`` matches the Girder 3 reference deployment in
  ``devops/dsa`` (MongoDB, Memcached, RabbitMQ).
- ``charts/dsa5`` matches the Girder 5 reference deployment in
  ``devops/ver5`` (MongoDB, Redis, RabbitMQ, plus a local worker in the
  Girder container).

These are sample charts meant to demonstrate a local deployment and to serve
as a starting point for a customer-facing chart.  See `Next steps for a real
EKS deployment`_ below for what is still missing.

Requirements
------------

- Docker (the daemon must be reachable).
- ``curl``.
- Roughly 10 GB of free disk for images and volumes.

No root access is required: the tools are installed into ``~/.local/bin``.

Quick start
-----------

From this directory::

    ./install-tools.sh            # kubectl, helm, kind into ~/.local/bin
    export PATH="$HOME/.local/bin:$PATH"
    ./cluster-up.sh               # create the kind cluster
    ./deploy-dsa.sh dsa5          # install the Girder 5 chart
    ./undeploy-dsa.sh dsa         # remove it
    ./cluster-down.sh             # delete the cluster

``deploy-dsa.sh`` also accepts ``dsa3``::

    ./deploy-dsa.sh dsa3

Both charts can be installed at the same time under different release names.
Note that the default ``NodePort`` values are 30080 (dsa3) and 30081 (dsa5),
matching the port mappings in ``kind-config.yaml``::

    ./deploy-dsa.sh dsa3 dsa3
    ./deploy-dsa.sh dsa5 dsa5

What is in this directory
-------------------------

``install-tools.sh``
    Downloads ``kubectl``, ``helm``, and ``kind`` into ``K8S_TOOLS_DIR``
    (default ``~/.local/bin``).  Versions are pinned at the top of the
    script.

    Note: the repository's pre-commit configuration runs ``helmlint`` on
    these charts, which requires ``helm`` to be on ``PATH``.  Install it with
    this script (and put ``~/.local/bin`` on ``PATH``) before running
    pre-commit, or the hook will fail with "helm: command not found".

``kind-config.yaml``
    A single-node kind cluster named ``dsa-local``.  It publishes NodePorts
    30080 and 30081 to the host so a normal workstation can reach the DSA
    web interface.  It also labels the node ``ingress-ready=true``.

``k8s.sh``
    A wrapper that defines ``kubectl`` and ``helm`` shell functions.  On a
    normal host they call the local binaries directly.  Some container
    sandboxes do not honor Docker's host port publishing or bind mounts; in
    that case the wrapper builds a small helper image containing the tools
    and a kubeconfig pointed at the kind node's bridge IP, and runs
    kubectl/helm inside a container on the kind network, copying the current
    directory in as needed.  Source it to use the functions interactively::

        source ./k8s.sh
        kubectl get pods
        helm list -A

``cluster-up.sh`` / ``cluster-down.sh``
    Create and delete the kind cluster.

``deploy-dsa.sh`` / ``undeploy-dsa.sh``
    Install and remove a chart from the cluster.  ``undeploy-dsa.sh`` also
    deletes the persistent volume claims, which Helm does not remove.

``charts/dsa3``, ``charts/dsa5``
    The sample Helm charts.

Backing services
----------------

Both charts deploy in-cluster MongoDB, RabbitMQ, and (for dsa5) Redis, plus
Memcached (for dsa3).  These are suitable for local testing only: they are
single-replica, use a ``ReadWriteOnce`` volume, and have no backup or
high-availability story.

The ``credentials`` values in ``values.yaml`` populate a Kubernetes
``Secret``.  For anything beyond local testing, create the Secret out of band
and point ``existingSecret`` at it.  The secret keys are:
``girder-admin-password``, ``mongodb-root-password``, ``rabbitmq-user``,
``rabbitmq-password``, ``celery-broker-url``, and ``celery-result-backend``.

Amazon DocumentDB is **not** MongoDB-compatible and must not be used as a
drop-in replacement.

Docker-in-Docker and slicer_cli_web
------------------------------------

``slicer_cli_web`` launches job containers with the Docker CLI.  The
reference docker-compose deployments bind-mount ``/var/run/docker.sock`` from
the host.  kind nodes run containerd and have no Docker socket, so the charts
default to a Docker-in-Docker sidecar instead:

- ``girder.dockerSocket.mode`` and ``worker.dockerSocket.mode`` select the
  behavior.

  - ``dind`` (default): a ``docker:dind`` sidecar in the same pod provides a
    socket over a shared ``emptyDir``; the DSA containers use
    ``DOCKER_HOST=unix:///var/run/docker.sock``.
  - ``hostPath``: mount the node's Docker socket, as docker-compose does.
    Use this on a host that actually has a Docker daemon (for example a
    self-managed node with Docker).

- The worker and the DinD sidecar share a ``tmp`` volume so staged job files
  are visible to the launched containers.
- Because Kubernetes starts sidecars only after init containers finish, the
  Girder and worker containers wait for the DinD socket in their main
  process rather than in an init container.

The sidecars run privileged.  This mirrors the privileged mode the
docker-compose files already require.

Provisioning
------------

Provisioning follows the reference deployments: ``provision.py`` runs at
container start and applies ``provision.yaml``.  The Girder container runs
the pre/main/post phases and then serves the application.

- dsa3 uses the Girder 3 provision script that ships in the image.
- dsa5 mounts the ver5 ``provision.py`` over the ``devops/dsa/provision.py``
  path, exactly as ``devops/ver5/docker-compose.yml`` does, so the in-image
  ver5 start script finds the Girder 5 script.

The admin user defaults to ``admin`` / ``password``.  Change it via the
``credentials.girderAdminPassword`` value or an ``existingSecret``.

Known limitations of the local setup
------------------------------------

- Pulling the ``dsarchive/histomicstk`` slicer CLI image into the DinD daemon
  during post-provisioning can be slow. Set ``slicerCli.pullImages=false`` to
  skip it; core DSA functionality is unaffected.
- Provisions must run with a single Girder replica.  The default
  ``girder.replicaCount`` is 1 and should stay 1 with this provisioning
  model.
- The in-cluster databases are not durable beyond their volume and have no
  failover.

Verifying a deployment
----------------------

::

    source ./k8s.sh
    kubectl get pods
    kubectl get pvc
    kubectl run curl-test --rm -i --restart=Never --image=curlimages/curl:latest \
      --command -- curl -s http://dsa-dsa5:8080/api/v1/system/version

A healthy deployment shows all pods ``Running``, all claims ``Bound``, and a
JSON version string from the API.

Reaching the web interface
--------------------------

On a normal workstation, open ``http://localhost:30080`` (dsa3) or
``http://localhost:30081`` (dsa5) after installing the chart; the kind port
mappings forward the NodePorts.

If host port publishing is not available (some sandboxes), the wrapper cannot
forward ports to the host.  Two options:

1. Run a temporary proxy container on the kind network::

       docker run --rm -it --network kind -p 8080:8080 \
         alpine/socat tcp-listen:8080,fork,reuseaddr tcp:dsa-dsa5:8080

   (the published port may itself be unavailable in that sandbox), or

2. Query the API from inside the cluster, as shown above.

Next steps for a real EKS deployment
------------------------------------

These charts are a local demonstration.  A customer-facing chart would need
additional work:

- **Managed backing services.** Decide between managed MongoDB (for example
  MongoDB Atlas; never DocumentDB), ElastiCache Redis, Amazon MQ/RabbitMQ,
  and S3/EFS for the assetstore, versus self-hosted pods.  The charts already
  expose ``mongodb.externalUri``, ``redis.externalHost``, and
  ``rabbitmq.externalHost`` hooks for external endpoints; the S3 assetstore
  is configured through ``provision.yaml``.
- **Ingress and TLS.** Enable the bundled ``ingress`` values and use the AWS
  Load Balancer Controller (an ALB is an Application Load Balancer, a
  managed layer-7 load balancer) with an ACM certificate, or cert-manager.
  An ALB is the usual way to expose HTTP services on EKS.
- **Storage classes.** Replace the default storage class with an EBS-backed
  class (``gp3``) and use ``ReadWriteMany``/EFS where multiple replicas must
  share the assetstore.
- **Secrets.** Move credentials to AWS Secrets Manager or External Secrets
  rather than chart values.
- **Scheduler / registry access.** Ensure nodes can reach the image registry,
  grant the worker nodes the permissions it needs, and decide how slicer CLI
  images are distributed.
- **Resource tuning.** Set realistic requests/limits and remove the
  single-replica constraints once provisioning is made idempotent or run as a
  one-shot Job.
- **Images.** Build and publish versioned DSA images; do not rely on
  ``latest``.
- **DinD vs. external workers.** For production, decide whether to run
  privileged DinD pods, use dedicated Docker hosts, or use the external
  worker pattern in ``devops/external-worker``.
