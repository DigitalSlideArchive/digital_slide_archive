#!/bin/bash

var="$(echo $@)"

docker exec -it histomicstk_histomicstk bash -lc "tox $var"
