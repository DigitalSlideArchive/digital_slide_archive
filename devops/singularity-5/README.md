# Apptainer DSA (Girder 5)

Launches DSA containers using `apptainer`.

## Getting Started

```bash
# Build dsa_common with apptainer
./build.sh

# Pull DSA service images
./pull_images.sh

# Start DSA services
./dsa_compose.sh
```

## Notes

- This environment mounts a girder source checkout at `/src/girder` and
  installs the apptainer (singularity) support packages from it during
  provisioning, because the stock `dsa_common_5` image does not include them.
  The support now lives in the girder tree behind opt-in flags (the
  `slicer_cli_web.singularity_enabled` setting and the
  `GIRDER_WORKER_SINGULARITY_ENABLED` worker environment variable); the
  overlay installs can be dropped once the girder `apptainer-port` branch is
  merged and the base image is built from a ref that contains it.  See
  `../local-sim-5` for a verified docker-based simulation of the apptainer +
  slurm execution path.
