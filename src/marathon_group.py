#!/usr/bin/env python3
#
# marathon_group.py: generate a Marathon Group out of a list of containers
#
# Author: Fernando Sanchez [ fernando at mesosphere.com ]

import json
import sys
import argparse
import subprocess
import os
import socket

def create_group ( name, containers ):
	"""
	Creates a marathon group taking a list of containers as a parameter.
	If the list has a single member if returns the member.
	"""
	output = '{ 			\
	  "id": "'+name+'",		\
	  "apps": '+containers+'\
	  }'

	return str(output)

def create_artifact_from_volume( volume, app_name ):
	"""
	Compress and copy the application in "source_path". Upload it to "app_server_address" so that it can be downloaded as URI.
	"""

	#get firstPartOfHostPath, etc.
	host_path = volume['hostPath'] 					#./app , ./site.conf
	host_path_to_create = ""
	#first_part_of_host_path = host_path.split('/' , 1)[0]	#app
	#last_part_of_host_path = host_path.split('/' , 1)[1]		#NULL
	container_path = volume['containerPath']							#/src/app, "/etc/nginx/conf.d/site.conf",
	first_part_of_container_path = container_path[1:].split('/', 1)[0]	#src  etc
	if len(container_path[1:].split('/', 1)) > 1:
	  last_part_of_container_path = container_path[1:].split('/', 1)[1]	#app  
	else:
	  last_part_of_container_path = ""
	staging_mount_point = "/tmp/ctransform"

	#create an artifact 
	artifact_name = app_name.replace('/','_')+"_"+host_path[2:].replace('/','_')+".tgz"

	#create subdir for staging with containerpath
	#staging_dir = staging_mount_point+"/"+container_path[1:]+"/"
	if os.path.isdir(host_path):
		container_dir = container_path
		host_dir = host_path
		print("**DEBUG: source host path is dir: {0} and container dirname will be {1}".format(os.getcwd()+host_path[1:], container_dir) ) #remove leading slash
	else:
		container_dir = os.path.dirname(container_path)
		print("**DEBUG: source host path is file: {0} and container dirname will be {1}".format(host_path[1:], container_dir) ) #remove leading slash		

	staging_app_dir =staging_mount_point+"/"+app_name # /tmp/ctransform/nginx-php-group-web
	staging_container_path = staging_app_dir+container_dir #/tmp/ctransform/nginx-php-group-web/etc/nginx/conf.d
	#print("**DEBUG: Create staging container path {0}".format(staging_container_path) ) #remove leading slash
	#command = "sudo mkdir -p "+staging_container_path
	#proc = subprocess.Popen( command, stdout=subprocess.PIPE, shell=True)
	#(out, err) = proc.communicate()
	print("**DEBUG: Create staging app dir {0}".format(staging_app_dir) ) #remove leading slash
	command = "sudo mkdir -p "+staging_app_dir
	proc = subprocess.Popen( command, stdout=subprocess.PIPE, shell=True)
	(out, err) = proc.communicate()			

	input( "***DEBUG: Press ENTER to continue...")
	#copy contents to staging dir
	#if it's a directory, add "/." to copy contents not directory
	host_path_to_copy=host_path
	if os.path.isdir(host_path):
		host_path_to_copy+="/."
	#this copies /src/app
	#print("**DEBUG: Copy {0} into {1}".format(host_path_to_copy, staging_container_path))
	#command = "cp -r "+host_path_to_copy+" "+staging_container_path
	#proc = subprocess.Popen( command, stdout=subprocess.PIPE, shell=True)
	#(out, err) = proc.communicate()

	#this copies ./app
	#test for Node.JS -- suspect it doesn't go into staging_container_path and instead it executes from staging_app_dir. Copy there	
	print("**DEBUG: Copy {0} into {1}".format(host_path_to_copy, staging_app_dir))
	command = "cp -r "+host_path_to_copy+" "+staging_app_dir+"/"+last_part_of_container_path
	proc = subprocess.Popen( command, stdout=subprocess.PIPE, shell=True)
	(out, err) = proc.communicate()

	input( "***DEBUG: Press ENTER to continue...")

	#compress staging_dir to artifact
	#create an artifact name inside the staging dir
	#artifact_path = app_name+"/"+artifact_name
	#make artifact path dir
	#print("**DEBUG: mkdir artifact path {0} in staging app dir {1} ".format(artifact_path, staging_app_dir))
	#command = "mkdir -p "+staging_app_dir+"/"+artifact_path
	#proc = subprocess.Popen( command, stdout=subprocess.PIPE, shell=True)
	#(out, err) = proc.communicate()


	print("**DEBUG: cd to {0} ".format(staging_app_dir))
	command = "cd "+staging_app_dir
	proc = subprocess.Popen( command, stdout=subprocess.PIPE, shell=True)
	(out, err) = proc.communicate()

	input( "***DEBUG: Press ENTER to continue...")

	print("**DEBUG: Compress {0} into {1} with relative path {2}".format(staging_app_dir, artifact_name, staging_app_dir ))
	command = "tar -czvf "+staging_app_dir+"/"+artifact_name+" -C "+staging_app_dir+" ." #compress this directory
	proc = subprocess.Popen( command, stdout=subprocess.PIPE, shell=True)
	(out, err) = proc.communicate()

	input( "***DEBUG: Press ENTER to continue...")

	#TODO: put artifact in web server

	#move to web server
	web_server_location="/root/DCOS_install/genconf/serve"
	print("**DEBUG: mv {0} into {1}".format(staging_app_dir+"/"+artifact_name, web_server_location))
	command = "mv "+staging_app_dir+"/"+artifact_name+" "+web_server_location
	proc = subprocess.Popen( command, stdout=subprocess.PIPE, shell=True)
	(out, err) = proc.communicate()

	#remove staging_dir 
	print("**DEBUG: Remove {0}".format(staging_app_dir))
	command = "rm -Rf "+staging_app_dir 
	proc = subprocess.Popen( command, stdout=subprocess.PIPE, shell=True)
	(out, err) = proc.communicate()

	return artifact_name

def modify_group ( group ):
	"""
	Modifies a marathon group received as a printable string to adapt the apps inside it 
	to the desired parameters.
	Adds AcceptedResourceRoles = "*"
	Deletes any hostPort values to have Marathon assign them automatically.
	Adds a label HAPROXY_GROUP=external for all hostPort values.
	If the apps mounts any volume that is local for compose (localhost), it mounts it as "external/rexray"
	Returns the group as a modified string.
	"""

	group_dict = json.loads( group )

	#find out my address
	s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	s.connect(("8.8.8.8", 53))
	my_address = print(s.getsockname()[0])
	s.close()

	for app in group_dict['apps']:
		app['acceptedResourceRoles']=["*"]
		for portMapping in app.get('container',{}).get('docker',{}).get('portMappings',{}):
			if portMapping.get('hostPort',{}): 	#delete ANY hostPort values, use them for VIP
				#create a VIP for every app, with a known pattern: group_dict['id']+'-'+app['id']:hostPort
				vip = "/"+group_dict['id']+'-'+app['id']+":"+str(portMapping['hostPort'])
				portMapping['labels'] = { "VIP_0": vip }
				#containerPort and hostPort are inverted??
				portMapping['containerPort'] = portMapping['hostPort']
				#portMapping['hostPort'] = 0  #BUG? Node issue? hostPort and containerPort need to be the same.
					## It works with any port but containerPort and hostPort need to be the same!?!?!?
				#make the app available in MarathonLB
				if 'labels' in app:
					app['labels'].update( {"HAPROXY_GROUP": "external"} )# if there was a hostPort add to MLB
				else:
					app['labels'] = { "HAPROXY_GROUP": "external" }

		#modify all volumes in the groups apps so that "this directory" volumes become external or downloaded from URI
		for volume in app.get('container', {}).get('volumes', {}):
			if volume['hostPath'][:2] == "./":			#if the volume is "this dir" for compose
				#FIRST CASE: using external persistent volumes, map ./DIR to a volume called DIR
				#volume = modify_volume_for_external( volume, group_dict['id']+'-'+app['id'] )	
						#modify it so that the local files are reachable via external volume
				#SECOND CASE: generate an artifact with the code in the local volume and add it as a URI
				artifact_name = create_artifact_from_volume( volume, group_dict['id']+'-'+app['id'] )
				uri = "http://"+my_address+"/"+artifact_name
				if 'uris' in app:
					app['uris'].append( uri )
				else:
					app['uris'] = [ uri ]
				#artifact will be downloaded to /mnt/mesos/sandbox
				#remove the volume
				del( volume )

		#correct dependencies:  "/db:redis" should be "redis" or "db"

	return json.dumps( group_dict )
