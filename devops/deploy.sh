#!/bin/bash

# Optionally set
#
# $GIRDER_SOURCE_FOLDER to the girder source repository
# $HISTOMICS_SOURCE_FOLDER to the HistomicsUI source repository
# $SLICER_CLI_WEB to the slicer_cli_web source repository
# $HISTOMICS_TESTDATA_FOLDER to a location to store data files

# $DIR will be the folder of this script.  See 
# https://stackoverflow.com/questions/59895
SOURCE="${BASH_SOURCE[0]}"
while [ -h "$SOURCE" ]; do # resolve $SOURCE until the file is no longer a symlink
  DIR="$( cd -P "$( dirname "$SOURCE" )" >/dev/null 2>&1 && pwd )"
  SOURCE="$(readlink "$SOURCE")"
  [[ $SOURCE != /* ]] && SOURCE="$DIR/$SOURCE" # if $SOURCE was a relative symlink, we need to resolve it relative to the path where the symlink file was located
done
DIR="$( cd -P "$( dirname "$SOURCE" )" >/dev/null 2>&1 && pwd )"

declare -a OPTS

HISTOMICS_TESTDATA_FOLDER=${HISTOMICS_TESTDATA_FOLDER:-~/.histomics_data}
if [ -d "$HISTOMICS_TESTDATA_FOLDER" ]; then
  OPTS+=(--mount "$HISTOMICS_TESTDATA_FOLDER:/data/")
fi

GIRDER_SOURCE_FOLDER="${GIRDER_SOURCE_FOLDER:-${DIR}/../../girder}"
if [ -d "$GIRDER_SOURCE_FOLDER" ]; then
  OPTS+=(--mount "$GIRDER_SOURCE_FOLDER:/opt/girder/")
fi

HISTOMICS_SOURCE_FOLDER="${HISTOMICS_SOURCE_FOLDER:-${DIR}/../../HistomicsUI}"
if [ -d "$HISTOMICS_SOURCE_FOLDER" ]; then
  OPTS+=(--mount "$HISTOMICS_SOURCE_FOLDER:/opt/HistomicsUI/")
fi

SLICER_CLI_WEB_SOURCE_FOLDER="${SLICER_CLI_WEB_SOURCE_FOLDER:-${DIR}/../../slicer_cli_web}"
if [ -d "$SLICER_CLI_WEB_SOURCE_FOLDER" ]; then
  OPTS+=(--mount "$SLICER_CLI_WEB_SOURCE_FOLDER:/opt/slicer_cli_web/")
fi

$DIR/../ansible/deploy_docker.py "${OPTS[@]}" $@
