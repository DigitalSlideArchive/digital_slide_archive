#!/bin/bash

var="$(echo $@)"

docker exec -it dsa_girder bash -lc "tox $var"
