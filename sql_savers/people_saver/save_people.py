#!/usr/bin/env python

# Title: Viz People
# Description: Reads people from RabbbitMQ and visualizes it
# Engineer: Jonathan Lwowski 
# Email: jonathan.lwowski@gmail.com
# Lab: Autonomous Controls Lab, The University of Texas at San Antonio

#########          Libraries         ###################
import numpy as np
import random
import pika
import time
import yaml
import json
import mysql.connector


### Read config parameters for mysql
with open('config.yaml') as f:
	config = yaml.safe_load(f)
	host = config['mysql_hostname']
	username = config['mysql_username']
	password = config['mysql_password']
	database = config['mysql_database']
	port = config['mysql_port']

### Connect to mysql database and get cursor
mydb = mysql.connector.connect(
  host=host,
  user=username,
  passwd=password,
  database=database,
  port = port
)
mycursor = mydb.cursor()

### Clear table for restart
sql = "TRUNCATE TABLE people_found"
mycursor.execute(sql)
mydb.commit()


### Read config parameters for RabbitMQ
with open('config.yaml') as f:
	config = yaml.safe_load(f)
	hostname = config['hostname']
	username = config['username']
	password = config['password']
	port = config['port']
credentials = pika.PlainCredentials(username, password)


### Global variable to store people count
people_count = 0

# Receive messages from UAVs and plot
def callback(ch, method, properties, body):
	global people_count
	#Receive person found
	people_count += 1
	person = json.loads(body.decode('utf-8'))

	# Save person into mysql
	sql = "INSERT INTO people_found (x_position, y_position, UAV_id, time_stamp) VALUES (%s, %s, %s, %s)"
	val = (person['x_position'], person['y_position'],person['uav_id'],str(person['timestamp']))
	mycursor.execute(sql, val)
	mydb.commit()

if __name__ == '__main__':
	# Establish incoming connection from UAVs
	connection_in = pika.BlockingConnection(pika.ConnectionParameters(host=hostname, credentials=credentials, port=port))
	channel_in = connection_in.channel()
	channel_in.exchange_declare(exchange='people_found', exchange_type='direct')
	result_in = channel_in.queue_declare(queue="",exclusive=True)
	queue_in_name = result_in.method.queue
	channel_in.queue_bind(exchange='people_found',queue=queue_in_name,routing_key='key_people_found')

	# Indicate queue readiness
	print(' [*] Waiting for messages. To exit, press CTRL+C')

	# Consumption configuration
	channel_in.basic_consume(on_message_callback=callback,queue=queue_in_name)

	# Begin consuming from UAVs
	channel_in.start_consuming()
	


