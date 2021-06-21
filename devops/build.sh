#!/bin/bash

# A commonm option is to watch a plugin.  Add
#   --watch-plugin histomicsui
# to the command line.

# @@Q quotes each parameter.  echo forms a single string that can be added to
# a command without further quoting.
var=$(echo "${@@Q}")

# We build in dev mode to get source maps on the client
docker exec -it dsa_girder bash -lc "girder build --dev $var"
