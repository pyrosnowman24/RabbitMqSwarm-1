#!/usr/bin/env python

# Title: Auction service
# Description: Recieves metacluster locations and auctions them to the ASVs
# Engineer: Jonathan Lwowski 
# Email: jonathan.lwowski@gmail.com
# Lab: Autonomous Controls Lab, The University of Texas at San Antonio


#########          Libraries         ###################
import sys
import math
import numpy as np
import random
import time
import pika
import threading
import copy

hostname = '129.114.111.193'
username = "yellow"
password = "test5243"
port="31111"
credentials = pika.PlainCredentials(username, password)

number_boats = 5
poses = []
boat_info =[]
clusters = []
exhanges_out = []
connection = None

class AuctionThread(threading.Thread):
    def __init__(self, host, topic, *args, **kwargs):
        super(AuctionThread, self).__init__(*args, **kwargs)
        self.host = host
        self.topic = topic
        
    # Receive messages from Metaclustering and publish to Auctioning
    def callback_clustering(self, ch, method, properties, body):
        global poses
        if 'START' in str(body):
            poses = []
        elif 'END' in str(body):
            pass
        else:
            poses_temp = body.decode("utf-8")
            x = float(poses_temp.replace("(","").replace(")","").replace("'","").split(",")[0])
            y = float(poses_temp.replace("(","").replace(")","").replace("'","").split(",")[1])
            poses.append([x,y])
            
    def run(self):
        global credentials
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
        
class ClustersThread(threading.Thread):
    def __init__(self, host, topic, *args, **kwargs):
        super(ClustersThread, self).__init__(*args, **kwargs)
        self.host = host
        self.topic = topic
        
    # Receive messages from Metaclustering and publish to Auctioning
    def callback_clustering(self, ch, method, properties, body):
        global clusters
        if 'START' in str(body):
            clusters = []
        elif 'END' in str(body):
            pass
        else:
            poses_temp = body.decode("utf-8")
            x = float(poses_temp.replace("(","").replace(")","").replace("'","").split(",")[0])
            y = float(poses_temp.replace("(","").replace(")","").replace("'","").split(",")[1])
            clusters.append([x,y])
        
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
        
class BoatInfoThread(threading.Thread):
    def __init__(self, host, topic, *args, **kwargs):
        super(BoatInfoThread, self).__init__(*args, **kwargs)
        self.host = host
        self.topic = topic
        
    # Receive messages from Metaclustering and publish to Auctioning
    def callback_boatinfo(self, ch, method, properties, body):
        global boat_info
        if "START" in str(body):
            boat_info = []
        elif "END" in str(body):
            pass
        else:
            boat_info_temp = body.decode("utf-8")
            for boat in boat_info_temp.split("\n"):
                speed = boat.replace("(","").replace(")","").replace("'","").split(",")[0]
                capacity = boat.replace("(","").replace(")","").replace("'","").split(",")[1]
                x = boat.replace("(","").replace(")","").replace("'","").split(",")[2]
                y = boat.replace("(","").replace(")","").replace("'","").split(",")[3]
                boat_id = boat.replace("(","").replace(")","").replace("'","").split(",")[4]
                if boat_info == [] or boat_id not in np.array(boat_info)[:,4]:
                    boat_info.append([float(speed),float(capacity),float(x),float(y), int(boat_id)])
            
    def run(self):
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(host=self.host, credentials=credentials, port=port))
        self.channel = self.connection.channel()
        self.channel.exchange_declare(exchange=self.topic, exchange_type='direct')
        self.result = self.channel.queue_declare(exclusive=True)
        self.queue = self.result.method.queue
        self.channel.queue_bind(exchange=self.topic,queue=self.queue,routing_key="key_"+self.topic)
        
        #Indicate queue readiness
        print(' [*] Waiting for messages. To exit, press CTRL+C')

        self.channel.basic_consume(self.callback_boatinfo,
                              queue=self.queue,
                              no_ack=False)

        self.channel.start_consuming()  
        
### Euclidean Distance
def distance(p0, p1):
    return math.sqrt((p0[0] - p1[0])**2 + (p0[1] - p1[1])**2)

### Call Clustering Service
def auctioning(auction_info, boat_info, clusters_info):
        global number_boats, connection
        #print("Lens: ", len(auction_info), len(boat_info), len(clusters_info))
        clusters_auc_pub = []
        boats = range(len(boat_info))     
        assignments = [0]*number_boats
        boat_info_temp = copy.deepcopy(boat_info)

        ### Perform Auction Algorithm
        for metacluster in auction_info:
                if connection is not None:
                    connection.process_data_events()
                min_value = 999999
                min_index = 0
                for index in boats:
                        meta_pose = (metacluster[0], metacluster[1])
                        #print(boat_info,index)
                        boat_pose = (boat_info_temp[index][2],boat_info_temp[index][3])
                        if abs(distance(meta_pose,boat_pose)) < min_value:
                                min_value = abs(distance(meta_pose,boat_pose))
                                min_index = index
                assignments[min_index] = meta_pose
                boat_info_temp[min_index][2] = 9999999999
        #print("assignments :", assignments)

        ### Calculate which clusters are in the asv assigned metacluster
        for boat in boats:
                if connection is not None:
                    connection.process_data_events()
                clusters_auc = []
                metacluster = assignments[boat]
                for cluster in clusters_info:
                        if connection is not None:
                            connection.process_data_events()
                        min_dist = 999999
                        min_index = 0
                        for index,metacluster in enumerate(auction_info):
                                if connection is not None:
                                    connection.process_data_events()
                                meta_pose = (metacluster[0], metacluster[1])
                                cluster_pose = (cluster[0], cluster[1])
                                if abs(distance(meta_pose,cluster_pose)) < min_dist:
                                        min_dist = abs(distance(meta_pose,cluster_pose))
                                        min_index = index
                        if auction_info[min_index][0] == assignments[boat][0] and auction_info[min_index][1] == assignments[boat][1]:
                                clusters_auc.append(cluster)
                #print("Boat: ", boat, "Clusters: ", clusters_auc)
                colors = ['r','b','g','y','k']
                if len(clusters_auc) > 0:
                    clusters_auc_pub.append(clusters_auc)
        for i in range(len(clusters_auc_pub)):
            publish_to_mq(boat_info[i][4],clusters_auc_pub[i])
                    

        #print auction_info
        #print boat_info

def publish_to_mq(boat_id, datas):
    # Establish outgoing connection to auctioning
    connection = pika.BlockingConnection(pika.ConnectionParameters(host=hostname, credentials=credentials, port=port))
    channel = connection.channel()
    channel.exchange_declare(exchange='auctioning'+"_"+str(boat_id), exchange_type='direct')
    entries = ""
    channel.basic_publish(exchange='auctioning'+"_"+str(boat_id),
                            routing_key='key_' + 'auctioning' +"_"+str(boat_id),
                            body="START") 
    for data in datas:
        entry = str((str(data[0]),str(data[1])))
        channel.basic_publish(exchange='auctioning'+"_"+str(boat_id),
                            routing_key='key_' + 'auctioning' +"_"+str(boat_id),
                            body=entry) 
        time.sleep(0.01)
    #print(entries)
    # Publish message to outgoing exchange
    channel.basic_publish(exchange='auctioning'+"_"+str(boat_id),
                            routing_key='key_' + 'auctioning' +"_"+str(boat_id),
                            body="END") 
    # Indicate delivery of message
    #print(" [ >> ] Sent %r" % entry)


if __name__ == '__main__':
    # Establish incoming connection from UAVs
    auction_thread = AuctionThread(hostname, 'metaclusters_found')
    auction_thread.start()
    
    # Establish incoming connection from UAVs
    boat_thread = BoatInfoThread(hostname, 'boat_info')
    boat_thread.start()
    
    # Establish incoming connection from UAVs
    clusters_thread = ClustersThread(hostname, 'clusters_found')
    clusters_thread.start()
    
    while(1):
        poses_temp = copy.deepcopy(poses)
        boat_info_temp = copy.deepcopy(boat_info)
        clusters_temp = copy.deepcopy(clusters)
        if len(poses_temp) == number_boats and len(boat_info_temp)>0 and len(clusters_temp)>0:
            print("Auctioning with ", len(boat_info_temp), " boats, ", len(clusters_temp), " clusters, ", len(poses_temp), " metaclusters") 
            auctioning(poses_temp, boat_info_temp, clusters_temp)
    


