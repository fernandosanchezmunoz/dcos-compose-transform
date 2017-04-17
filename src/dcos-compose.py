#!/usr/bin/env python3
#
# dcos_compose.py: translate from docker compose files to Marathon pods or groups JSON files
#
# Author: Fernando Sanchez [ fernando at mesosphere.com ]

import os
import sys
import subprocess
import marathon_group
import marathon_pod
import logging
import argparse
import json

if __name__ == "__main__":

	#parse command line arguments
	parser = argparse.ArgumentParser(description='Convert a list of containers to a Marathon Pod.', \
		usage='marathon_pod.py -i [container_list_filename] -n [group_name] [-g]'
		)
	parser.add_argument('-i', '--input', help='full path of the docker compose file', required=True)
	parser.add_argument('-n', '--name', help='name to be given to the Marathon Pod or Service Group', required=True)
	parser.add_argument('-s', '--server', help='address of the app server to be used for artifacts', required=False)
	parser.add_argument('-o', '--output', help='full path of the file to write output JSON to', required=False, default='output.json')
	args = vars( parser.parse_args() )

	#print('**DEBUG: input file is {0}'.format(args['input']))

	#get the docker compose file
	try:
		with open( args['input'], "r") as input_file:
			containers = input_file.read()
	except (OSError, IOError):
		logger.error("File {0} not found".format( args['input'] ))
		sys.exit(1)

	#translate it with container-transform and get the result
	#command = "container-transform -i compose -o marathon "+args['input']
	#proc = subprocess.Popen( [command], stdout=subprocess.PIPE, shell=True)
	#(out, err) = proc.communicate()	
	#containers = out.decode('utf-8')
	#print("**DEBUG: containers pre-rstrip is {0}".format( containers ))	

	#remove the trailing \n from file
	#convert to string
	containers_list = ""
	#for line in json.dumps(containers):
	#		containers_list += line.rstrip()
	#containers_list = json.loads(containers_list)
	#print("**DEBUG: containers is {0}".format( containers ))	
	#detect if it's just one app - if so, get in list
	if containers[0]=="{":
		containers_list="["+containers+"]"
	else:
		containers_list=containers
	#print("**DEBUG: container_list is {0}".format( containers_list ))
	containers_list = json.loads(containers_list)
	#print("**DEBUG: container_list is of type {0}".format( type(containers_list )))	
	#check if any of the containers does not have an IMAGE. FAIL if so
	for container in containers_list:
		#print('**DEBUG: container OOP is {0}'.format(container))
		if not 'image' in container.get('container',{}).get('docker',{}):
			print("**ERROR: Container {0} does not include an IMAGE. Please edit and re-run.".format(container['id']))
			exit(1)
	output_file=open( args['output'], "w")
	#move to the app's base directory to run create_pod
	current_dir = os.getcwd()
	app_dir = os.path.dirname( args['input'] )
	#print("**DEBUG: app_Dir is {0}".format( app_dir))	
	os.chdir( app_dir )
	pod = marathon_pod.create_pod( args['name'], json.dumps(containers_list), args['server'] )
	#print("**DEBUG: POD is of type {0}".format( type(pod )))	
	#print("**DEBUG: POD is {0}".format( pod ))
	#print("**DEBUG: output_file is {0}".format( args['output'] ))

	print( pod, file=open(args['output'], "w" ))

	#TODO: create MLB-forwarder
	"""
	"labels": {
    	"HAPROXY_0_BACKEND_SERVER_OPTIONS": "server composeapp.marathon.l4lb.thisdcos.directory:3000",
    	"HAPROXY_GROUP": "external"
  	}
	"""

	os.chdir( current_dir )
	#input( "***DEBUG: Press ENTER to continue...")
	sys.exit(0)