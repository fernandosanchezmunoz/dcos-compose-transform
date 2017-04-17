#!/usr/bin/env python3
#
# marathon_forwarder.py: generate a Marathon App for a dummy container that simply creates an entry in MLB
# Author: Fernando Sanchez [ fernando at mesosphere.com ]

import json
import sys
import argparse
import subprocess
import os

if __name__ == "__main__":

	#parse command line arguments
	parser = argparse.ArgumentParser(description='Create a Marathon app for a dummy container to create an entry in MLB.', \
		usage='marathon_pod.py -i [container_list_filename] -n [group_name] [-g]'
		)
	parser.add_argument('-i', '--input', help='full path of the Marathon JSON file for the Pod', required=True)
	parser.add_argument('-o', '--output', help='full path of the file to write output JSON to', required=False, default='forwarder.json')
	args = vars( parser.parse_args() )

	#get the Marathon JSON file
	try:
		with open( args['input'], "r") as input_file:
			marathon_pod = json.loads( input_file.read() )
	except (OSError, IOError):
		logger.error("File {0} not found or format not correct.".format( args['input'] ))
		sys.exit(1)

	vips = []

	#get the VIPs
	for container in marathon_pod.get( 'containers', [] ):
		for endpoint in container.get( 'endpoints', [] ):
			for label in endpoint.get( 'labels', {} ):
				if 'VIP_0' in label:
					vips.append( label['VIP_0'] )

	#list of VIPs is attached to the forwarders JSON definitino
	forwarder = {}
	forwarder['id'] = marathon_pod['id']+"-forwarder"
	forwarder['cpus'] = 0.1
	forwarder['mem'] = 64
	forwarder['container'] = {}
	forwarder['container']['type'] = "DOCKER"
	forwarder['container']['docker'] = {}
	forwarder['container']['docker']['image'] = "nginx"
	forwarder['container']['docker']['network'] = "BRIDGE"
	forwarder['container']['docker']['portMappings'] = [{ 
		"containerPort" = 80,
		"hostPort" = 0
		}]
	forwarder['healthChecks'] = [{
		"path" = "/",
		"protocol" = "MESOS_HTTP",
		"portIndex" = 0
	}]
	forwarder['labels'] = { "HAPROXY_GROUP": "external" }
	for vip, index in enumerate( vips ):
		forwarder['labels']['HAPROXY_'+str(index-1)+BACKEND_SERVER_OPTIONS]: vip

	print( json.dumps( forwarder ), file=open(args['output'], "w" ))

	sys.exit(0)
