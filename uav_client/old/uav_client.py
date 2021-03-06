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
import time

hostname = '129.114.111.193'
username = "yellow"
password = "test5243"
port="31111"
credentials = pika.PlainCredentials(username, password)

people = []

# Sends locations of people found to Rabbit
def publish_to_mq(data):
	channel.basic_publish(exchange='people_found',
		                    routing_key='key_people_found',
		                    body="START")
	for person in data:
		#print( person )
		# Publish message to outgoing exchange
		channel.basic_publish(exchange='people_found',
				            routing_key='key_people_found',
				            body=str(person)) 

	channel.basic_publish(exchange='people_found',
		                    routing_key='key_people_found',
		                    body="END") 
	time.sleep(0.01)
	# Indicate delivery of message
	#print(" [ >> ] Sent %r" % people)

### Randomly generate peoples poses
def gen_poses():
	global people
	min_x = -200
	while(min_x<200):
		num_people = int(random.uniform(100,200))
		while num_people > 0:
			x = random.uniform(min_x,min_x+10)
			y = random.uniform(-200,200)
			num_people -= 1
			people.append((x,y))
		publish_to_mq(people)
		min_x += 25
		time.sleep(1)
	while(1):
		print(len(people))
		publish_to_mq(people)
		time.sleep(1)

### Main Service Client for UAV
def uav_service():
        ### Randomly generate peoples poses
        people_locs = gen_poses()


if __name__ == '__main__':
	# Establish outgoing connection to RabbitMQ
	connection = pika.BlockingConnection(pika.ConnectionParameters(host=hostname,port=port, credentials=credentials))
	channel = connection.channel()
	channel.exchange_declare(exchange='people_found', exchange_type='direct')
	uav_service()


