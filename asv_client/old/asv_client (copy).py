#!/usr/bin/env python

# Title: UAV client
# Description: Randomly generates peoples poses and sends them to the RabbitMQ server
# Engineer: Jonathan Lwowski 
# Email: jonathan.lwowski@gmail.com
# Lab: Autonomous Controls Lab, The University of Texas at San Antonio


#########          Libraries         ###################
import sys
import math
import numpy as np
import random
import pika
import threading
import time

hostname = '129.114.111.193'
username = "yellow"
password = "test5243"
port="31111"
credentials = pika.PlainCredentials(username, password)

num_boats = 5
boat_info = []
clusters = []
clusters_threads = []
final_paths_threads = []
final_paths = []

class FinalPathsThread(threading.Thread):
	def __init__(self, host, topic, boat_id, *args, **kwargs):
		super(FinalPathsThread, self).__init__(*args, **kwargs)
		self.host = host
		self.topic = topic
		self.boat_id = boat_id
		self.start_time = time.time()
		self.end_time = 0.0
		self.final_paths_temp = []
	# Receive messages from Metaclustering and publish to Auctioning
	def callback_clustering(self, ch, method, properties, body):
		global final_paths
		if "START" in str(body):
			self.final_paths_temp = []
		elif "END" in str(body):
			if self.end_time == 0.0:
				self.end_time = time.time()
			if len(self.final_paths_temp) > 0:
				print("Time to get paths: ", self.end_time-self.start_time, " Boat ID: ", self.boat_id, "Final Path: ", len(self.final_paths_temp))
			final_paths[self.boat_id-1] = self.final_paths_temp
		else:
			poses_temp = body.decode("utf-8")
			for pose in poses_temp.split("\n")[0].split(">"):
				if len(pose.replace("(","").replace(")","").replace("'","").split(",")) == 2:
					x = pose.replace("(","").replace(")","").replace("'","").split(",")[0]
					y = pose.replace("(","").replace(")","").replace("'","").split(",")[1]
					self.final_paths_temp.append([float(x),float(y)])
		
	def run(self):
		connection = pika.BlockingConnection(pika.ConnectionParameters(host=self.host, credentials=credentials, port=port))
		channel = connection.channel()
		channel.exchange_declare(exchange='final_path'+'_'+str(self.boat_id), exchange_type='direct')
		result = channel.queue_declare(exclusive=True)
		queue = result.method.queue
		channel.queue_bind(exchange='final_path'+'_'+str(self.boat_id),queue=queue,routing_key='key_final_path'+'_'+str(self.boat_id))
		#Indicate queue readiness
		print(' [*] Waiting for messages. To exit, press CTRL+C')

		channel.basic_consume(self.callback_clustering,
							  queue=queue,
							  no_ack=False)

		channel.start_consuming()  
		
class ClustersThread(threading.Thread):
	def __init__(self, host, topic, boat_id, *args, **kwargs):
		super(ClustersThread, self).__init__(*args, **kwargs)
		self.host = host
		self.topic = topic
		self.boat_id = boat_id
		self.connection = pika.BlockingConnection(pika.ConnectionParameters(host=self.host, credentials=credentials, port=port))
		self.channel = self.connection.channel()
		self.channel.exchange_declare(exchange='tsp_info'+'_'+str(self.boat_id), exchange_type='direct')
		
	# Receive messages from Metaclustering and publish to Auctioning
	def callback_clustering(self, ch, method, properties, body):
		global clusters
		if 'START' in str(body):
			clusters[self.boat_id-1] = []
			clusters[self.boat_id-1].append([boat_info[self.boat_id-1][2],boat_info[self.boat_id-1][3]])
		elif 'END' in str(body):
			self.publish_to_mq(clusters[self.boat_id-1])
		else:
			poses_temp = body.decode("utf-8")
			x = float(poses_temp.replace("(","").replace(")","").replace("'","").split(",")[0])
			y = float(poses_temp.replace("(","").replace(")","").replace("'","").split(",")[1])
			clusters[self.boat_id-1].append([x,y])
		
	# Sends locations of people found to Rabbit
	def publish_to_mq(self,datas):
		self.channel.basic_publish(exchange='tsp_info'+'_'+str(self.boat_id),
								routing_key='key_'+'tsp_info'+'_'+str(self.boat_id),
								body="START")
		entries = ""
		for data in datas:
			entry = str((str(data[0]),str(data[1])))
			self.channel.basic_publish(exchange='tsp_info'+'_'+str(self.boat_id),
								routing_key='key_'+'tsp_info'+'_'+str(self.boat_id),
								body=entry)
			time.sleep(0.01)
			#print(entry)
		#print( 'tsp_info'+'_'+str(self.boat_id) )
		# Publish message to outgoing exchange
		self.channel.basic_publish(exchange='tsp_info'+'_'+str(self.boat_id),
								routing_key='key_'+'tsp_info'+'_'+str(self.boat_id),
								body="END") 
		# Indicate delivery of message
		#print("Boat ID: ", self.boat_id, " Data: ", entry)
		
	def run(self):
		self.connection = pika.BlockingConnection(pika.ConnectionParameters(host=self.host, credentials=credentials, port=port))
		self.channel = self.connection.channel()
		self.channel.exchange_declare(exchange=self.topic, exchange_type='direct')
		self.result = self.channel.queue_declare(exclusive=True)
		self.queue = self.result.method.queue
		self.channel.queue_bind(exchange=self.topic,queue=self.queue,routing_key="key_"+self.topic)
		
		#Indicate queue readiness
		print(' [*] Waiting for messages. To exit, press CTRL+C')

		self.channel.basic_consume(self.callback_clustering,
							  queue=self.queue,
							  no_ack=False)

		self.channel.start_consuming()  
		
# Sends locations of people found to Rabbit
def publish_to_mq(data):
	channel.basic_publish(exchange='boat_info',
				            routing_key='key_boat_info',
				            body="START")
	for boat in data:
		entry = str(boat)
		#print( entry )
		# Publish message to outgoing exchange
		channel.basic_publish(exchange='boat_info',
				            routing_key='key_boat_info',
				            body=entry) 
		time.sleep(0.01)
	channel.basic_publish(exchange='boat_info',
				            routing_key='key_boat_info',
				            body="END")
	# Indicate delivery of message
	#print(" [ >> ] Sent %r" % entry)

### Randomly generate peoples poses
def gen_poses():
	global num_boats, clusters_threads
	num_people = num_boats
	boat_id = 1
	while num_people > 0:
		boat_speed = random.uniform(.2,1.0)
		boat_capacity = random.uniform(10,150)
		boat_location_x = random.uniform(-400,-300)
		boat_location_y = random.uniform(-200,200)
		num_people -= 1
		boat_info.append((boat_speed,boat_capacity,boat_location_x,boat_location_y, boat_id))
		#publish_to_mq((boat_speed,boat_capacity,boat_location_x,boat_location_y, boat_id))
		
		
		# Establish incoming connection from UAVs
		clusters.append([])
		final_paths.append([])
		clusters_threads.append(ClustersThread(hostname, 'auctioning'+"_"+str(boat_id), boat_id))
		clusters_threads[len(clusters_threads)-1].start()
		final_paths_threads.append(FinalPathsThread(hostname, 'final_path'+"_"+str(boat_id), boat_id))
		final_paths_threads[len(final_paths_threads)-1].start()
		boat_id += 1
	while(1):
		#print(boat_info)
		publish_to_mq(boat_info)
		time.sleep(1)

### Main Service Client for ASV
def asv_service():
        ### Randomly generate peoples poses
        people_locs = gen_poses()


if __name__ == '__main__':
	# Establish outgoing connection to RabbitMQ
	connection = pika.BlockingConnection(pika.ConnectionParameters(host=hostname, credentials=credentials, port=port))
	channel = connection.channel()
	channel.exchange_declare(exchange='boat_info', exchange_type='direct')
	asv_service()
	


