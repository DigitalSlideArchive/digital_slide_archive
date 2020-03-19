#!/bin/bash

var="$@"

docker exec -it dsa_girder bash -lc "tox \"$var\""
