#!/usr/bin/env python3
#
# dcos_compose.py: translate from docker compose files to Marathon pods or groups JSON files
#
# Author: Fernando Sanchez [ fernando at mesosphere.com ]

import os
import marathon_group
import marathon_pod
import logging

if __name__ == "__main__":

	logging.basicConfig(level=logging.INFO)
	logger = logging.getLogger(__name__)

	#parse command line arguments
	parser = argparse.ArgumentParser(description='Convert a list of containers to a Marathon Pod.', \
		usage='marathon_pod.py -i [container_list_filename] -n [group_name] [-g]'
		)
	parser.add_argument('-i', '--input', help='full path of the docker compose file', required=True)
	parser.add_argument('-n', '--name', help='name to be given to the Marathon Pod or Service Group', required=True)
	parser.add_argument('-s', '--server', help='address of the app server to be used for artifacts', required=False)
	parser.add_argument('-o', '--output', help='full path of the file to write output JSON to', required=False, default='output.json')
	args = vars( parser.parse_args() )

	#get the docker compose file
	try:
		compose_file = open( args['input'], "r")
	except (OSError, IOError):
		logger.error("File {0} not found".format( args['input'] ))
		exit(1)

	#translate it with container-transform and get the result
	command = "container-transform -i compose -o marathon "args['input']
	proc = subprocess.Popen( [command], stdout=subprocess.PIPE, shell=True)
	(containers, err) = proc.communicate()	
	logger.debug("Output of CONTAINER-TRANSFORM is {0}".format( containers ))

	#remove the trailing \n from file
	for line in containers:
		containers += line.rstrip()
	#detect if it's just one app - if so, get in list
	if containers[0]=="{":
		containers="["+containers+"]"
	#check if any of the containers does not have an IMAGE. FAIL if so
	for container in json.loads(containers):
		print('**DEBUG: container is {0}'.format(container))
		if not 'image' in container.get('container',{}).get('docker',{}):
			print("**ERROR: Container {0} does not include an IMAGE. Please edit and re-run.".format(container['id']))
			exit(1)
	output_file=open( args['output'], "w")
	pod = create_pod( args['name'], containers, args['server'] )

	print( pod, file=output_file )

	input( "***DEBUG: Press ENTER to continue...")
	sys.exit(0)