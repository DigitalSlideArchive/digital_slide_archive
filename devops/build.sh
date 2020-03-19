#!/bin/bash

# A commonm option is to watch a plugin.  Add
#   --watch-plugin histomicsui
# to the command line.

var="$(echo $@)"

# We build in dev mode to get source maps on the client
docker exec -it dsa_girder bash -lc "girder build --dev $var"
