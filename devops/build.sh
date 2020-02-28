#!/bin/bash

# A commonm option is to watch a plugin.  Add
#   --watch-plugin histomicsui
# to the command line.

var="$(echo $@)"

docker exec -it dsa_girder bash -lc "girder build --dev $var"
