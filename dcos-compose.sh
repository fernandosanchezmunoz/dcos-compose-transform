#!/bin/bash

#   Reads a "docker-compose.yml" file located in a directory with the application name:
# (e.g. ./data/redis/docker-compose.yml).
#  Creates a marathon.json out of it with a list of the containers included in the YML. 
#  Finally processes that list and builds a Marathon group out of it, modifying some parameters
# to adapt it to a DC/OS cluster (e.g. using Marathon's dynamic port assignment and Marathon-LB). 

APP_NAME="$1"
BASE_DIR=$PWD
COMPOSE_DIR=$BASE_DIR"/compose"
WORKING_DIR=$COMPOSE_DIR"/"$APP_NAME
SRC_DIR=$BASE_DIR"/src"

COMMAND_PIP_CHECK=$(pip list --format columns|grep container-transform)
MY_IP=$(ip addr show eth0 | grep -Eo \
 '[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}' | head -1)

MARATHON_GROUP=$SRC_DIR"/marathon_group.py" 
MARATHON_POD=$SRC_DIR"/marathon_pod.py"

#pre-requisites: container-transform
if [[ $COMMAND_PIP_CHECK == *"container-transform"* ]]; then
	echo "**INFO: container-transform available."
else
	echo "**INFO: container-transform unavailable. Installing..."
	pip install container-transform
fi

#read example name from first argument
if [ -z "$1" ]; then
  echo "** ERROR: no parameter received. Enter the name of the subdirectory on "$COMPOSE_DIR" to convert"
  ls -A1l $COMPOSE_DIR | grep ^d | awk '{print $9}'
  exit 1
fi

#change to subdirectory
cd $WORKING_DIR

container-transform -i compose -o marathon docker-compose.yml > marathon.json 
echo "***** MARATHON.JSON *****"
cat marathon.json
../../src/marathon_pod.py -i marathon.json -n ${PWD##*/} -s $MY_IP #produces group.json
echo "***** OUTPUT.JSON *****"
cat output.json

dcos auth login && \
dcos marathon pod add ./output.json

cd $CURRENT_DIR

exit 0
