#!/usr/bin/env python3
#
# marathon_group.py: generate a Marathon Service Pod or Group out of a list of containers
#
# Author: Fernando Sanchez [ fernando at mesosphere.com ]

import json
import sys
import argparse
import subprocess
import os

def create_pod( name, apps, app_server_address ):
	"""
	Creates a marathon pod taking a list of apps as a parameter.
	If the list has a single member if returns the member.
	"""

	#get relevant information of first container
	#first_container = json.loads( containers[0] )
	#get port mapping
	#TODO: get relevant info from first container
	pod_cpu=0.5
	pod_mem=512
	#pod_disk=50

	#adapt all containers to pod format
	pod_apps, hostPath = adapt_apps_to_pod( apps, name, app_server_address )

	output = '{ 									\
	  "id": "/'+name+'",							\
	  "containers": '+pod_apps+',					\
  	  "networks": [									\
        {											\
          "mode": "host"							\
        }											\
      ],											\
	  "executorResources": {						\
        "cpus": '+str(pod_cpu)+',					\
        "mem": '+str(pod_mem)+'						\
	  },											\
      "labels": {									\
        "HAPROXY_GROUP": "external"					\
      },											\
      "volumes": [ { 								\
      	"name": "sandbox",							\
      	"host": "'+hostPath+'"						\
      	}]											\
	  }'


	return str(output)

def adapt_apps_to_pod( apps, name, app_server_address ):
	"""
	Receives a list of apps in Marathon single container format.
	Returns a list of those containers adapted to the Marathon pod format.
	"""
	#COMMAND = "cp -r $MESOS_SANDBOX/* $(pwd); npm start"
	app_cpu = 0.3
	app_mem = 256
	hostPath = ""

	pod_apps=[]
	app_list = json.loads(apps)
	for app in app_list:
		temp_app = {}
		temp_app['name'] = app['id']
		#TODO: figure out resources
		temp_app['resources'] = {
		"cpus": app_cpu,
		"mem": app_mem
		}
		#adapt volumes
		print("**DEBUG: app is {0}".format(app))
		app_uris, hostPath = adapt_app_volumes_for_uri( app, app_server_address )
		print("**DEBUG: app with URIs is {0}".format(app_uris))
		temp_app['volumeMounts'] = app_uris.get('volumeMounts', [])
		temp_app['artifacts'] = []
		for uri in app_uris.get( 'uris', [] ):
			temp_app['artifacts'].append( { 
				"uri": uri
				} )
			#TODO: trick to download URI content to "/src" as NPM starts there
			#temp_app['exec'] = {}
			#temp_app['exec']['command'] = {}
			#temp_app['exec']['command']['shell'] = COMMAND
		#adapt port mappings
		temp_app['endpoints'] = []
		container = app_uris['container']  #container is embedded in app
		print("**DEBUG: container is {0}".format(container))
		for portMapping in container.get('docker', {}).get('portMappings', {}):
			endpoint = {}
			endpoint['name'] = name+str(portMapping['containerPort'])
			#endpoint['hostPort'] = portMapping['hostPort']
			#hostPort is now containerPort
			endpoint['hostPort'] = portMapping['containerPort']
			endpoint['protocol'] = [ portMapping['protocol'] ]
			endpoint['labels'] = { "VIP_0": "/"+temp_app['name']+":"str(endpoint['hostPort']) }
			temp_app['endpoints'].append(endpoint)
		temp_app['image'] = { } 
		temp_app['image']['kind'] = container['type']
		temp_app['image']['id'] = container['docker']['image']
		print("**DEBUG: temp_app is {0}".format(temp_app))
		pod_apps.append(temp_app)
		print("**DEBUG: pod_apps is {0}".format(pod_apps))


	print("**DEBUG: pod_apps is {0}".format(pod_apps))
	return ( json.dumps(pod_apps), hostPath )


def adapt_app_volumes_for_uri( app, app_server_address ):
	"""
	converts a marathon app with a list of container volumes with links to current directory in a
	marathon app wih a list of uris to be downloaded from a web server.
	"""
	print("**DEBUG: APP is {0}".format(app))

	new_app = app.copy()
	new_app['volumeMounts'] = []
	hostPath = ""

	#modify all volumes in the groups apps so that "this directory" volumes become external or downloaded from URI
	for volume in new_app.get('container',{}).get('volumes', {}):
			print("**DEBUG: VOLUME is {0}".format(volume))
			if volume['hostPath'][:2] == "./":			#if the volume is "this dir" for compose
				#FIRST CASE: using external persistent volumes, map ./DIR to a volume called DIR
				#volume = modify_volume_for_external( volume, group_dict['id']+'-'+app['id'] )	
						#modify it so that the local files are reachable via external volume
				#SECOND CASE: generate an artifact with the code in the local volume and add it as a URI
				#find path where this will be mounted in the host for the pod
				hostPath = volume['hostPath'][2:]
				print("**DEBUG: hostPath is {0}".format(hostPath))
				app_id=new_app.get('id', {})
				container_id=new_app.get('container', {}).get('docker',{}).get('image',"")
				volume_containerPath=volume.get('containerPath', {}).replace('/','_')
				print("**DEBUG: new_app is {0}".format(new_app))				
				print("**DEBUG: volume is {0}".format(volume))
				print("**DEBUG: app_id is {0}".format(app_id))
				print("**DEBUG: container_id is {0}".format(container_id))
				print("**DEBUG: volume_containerPath is {0}".format(volume_containerPath))
				print("**DEBUG: app_server_address is {0}".format(app_server_address))				
				artifact_name = create_artifact_from_volume( volume, app_id+'-'+container_id+'-'+volume_containerPath, app_server_address )
				print("**DEBUG: ARTIFACT NAME is {0}".format(artifact_name))
				uri = "http://"+app_server_address+"/"+artifact_name
				if 'uris' in new_app:
					new_app['uris'].append( uri )
				else:
					new_app['uris'] = [ uri ]
				#artifact will be downloaded to /mnt/mesos/sandbox
				#this is mounted in the pod as relative local volume with name "sandbox" above
				#now this container needs to mount it to /src in absolute path
				new_app['volumeMounts'].append( { 
					"name": "sandbox",
					"mountPath": volume['containerPath'] #"/src/app"
				} )

				#remove the volume
				del( volume )

	return( new_app, hostPath )

def create_artifact_from_volume( volume, app_name, app_server_address ):
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

