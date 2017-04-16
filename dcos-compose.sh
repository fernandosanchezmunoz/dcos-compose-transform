#!/bin/bash

# Reads a "docker-compose.yml" file passed as a parameter.
# Creates an output Marathon JSON file with a list of the containers included in the YML embedded 
# in a pod or group ready to be deployed to a DC/OS cluster.

#variables and environment
COMPOSE_FILE_NAME="$1"
APP_NAME=${COMPOSE_FILE_NAME##*/}  
BASE_DIR=$PWD
COMPOSE_DIR=$BASE_DIR"/compose"
MARATHON_DIR=$BASE_DIR"/marathon"
WORKING_DIR=$COMPOSE_DIR"/"$APP_NAME
SRC_DIR=$BASE_DIR"/src"
CONTAINER_TRANSFORM="container-transform"
DCOS_COMPOSE=$SRC_DIR"/dcos-compose.py"
OUTPUT_FILE=$MARATHON_DIR"/"$APP_NAME".json"
MARATHON_TEMP_FILE=$WORKING_DIR"/"$APP_NAME"-marathon-units.json" 
COMMAND_PIP_CHECK=$(pip3 -V)
COMMAND_PYTHON3_CHECK=$(python3 --version)
MY_IP=$(ip addr show eth0 | grep -Eo \
 '[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}' | head -1)
MARATHON_GROUP=$SRC_DIR"/marathon_group.py" 
MARATHON_POD=$SRC_DIR"/marathon_pod.py"


#argument validation
if [ -z "$1" ]; then
  echo "** ERROR: no input file received. Enter the full path of a Docker Compose YAML file to convert"
  echo "** INFO: syntax: dcos_compose.sh [full_path_of_YAML_file] [name]"
  find $COMPOSE_DIR|grep "yml" 
  #| grep ^d | awk '{print $9}'
  exit 1
fi

#pre-requisites: python3
if [[ $COMMAND_PYTHON3_CHECK == *"Python 3"* ]]; then
	echo "**INFO: python3 available."
else
	echo "**INFO: python3 unavailable. Please install. Exiting..."
	exit 1
fi

#pre-requisites: pip3
if [[ $COMMAND_PIP_CHECK == *"pip"* ]]; then
	echo "**INFO: pip3 available."
else
	echo "**INFO: pip3 unavailable. Please install. Exiting..."
	exit 1
fi

#install python requirements etc. (silently)
pip3 install -r $BASE_DIR/requirements.txt > /dev/null 2>&1

echo "DCOS COMPOSE: "$DCOS_COMPOSE
$CONTAINER_TRANSFORM -i compose -o marathon $1 > $MARATHON_TEMP_FILE
echo "***** MARATHON_TEMP.JSON *****"
cat $MARATHON_TEMP_FILE
$DCOS_COMPOSE -i $MARATHON_TEMP_FILE -n $APP_NAME -o $OUTPUT_FILE -s $MY_IP #produces group.json
echo "***** OUTPUT.JSON *****"
cat $OUTPUT_FILE

dcos auth login && \
dcos marathon pod add $OUTPUT_FILE

exit 0
