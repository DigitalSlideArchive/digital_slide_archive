#!/bin/bash

# @@Q quotes each parameter.  echo forms a single string that can be added to
# a command without further quoting.
var=$(echo "${@@Q}")

docker exec -it dsa_girder bash -lc "tox $var"
