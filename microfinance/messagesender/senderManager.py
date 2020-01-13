import threading 
import time
import paho.mqtt.client as mqtt
import psycopg2
import logging

#-------------------Logging settings------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

#-------Databse settings-----------
schema = ""
username = ""
userpassword = ""
hostaddress = ""
hostport = ""
#-------mqttt settings--------------
MQTT_SERVER_PATH = "localhost"
MQTT_SERVER_PORT = 1883

#-------Message STATUS -------
NEW = 0
PROCESSING = 1
SUCCESS = 2
FAIL = 3
#-----MSG TYPES--------
TYPE_MSG = 0
TYPE_SMS = 1
TYPE_EMAIL = 2

class processThreadMain(threading.Thread):
    def __init__(self, threadID, name, counter, conn):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.name = name
        self.counter = counter
        self.conn = conn
    def run(self):
    	
    	while True:
    		count = 1
    		rows = fetchData(self.conn)
    		thread2 = threading.Thread(target = msg_sender, args = (rows,True,self.conn ))
    		thread2.daemon=True
    		thread2.start()
    		time.sleep(1)

    def exit():
		self.name.exit()
		if self.conn:
			self.conn.close()


def startApp(host,port,dbschema,dbhost,dbport,dbusr,dbpass):
	
	global MQTT_SERVER_PATH 
	MQTT_SERVER_PATH = host
	global MQTT_SERVER_PORT
	MQTT_SERVER_PORT = port
	try:
		conn = initializeDatabase(dbschema, dbusr, dbpass, dbhost, dbport)
		if conn is not None:
			logger.info('database connection done successfully with schema=%s, dbhost=%s, dbport=%s, dbusr=%s, dbpass=%s',dbschema,dbhost,dbport,dbusr,dbpass)
  		thread=processThreadMain(1, "Main thread", 1, conn)
  		thread.daemon=True
  		logger.info('Starting Main thread for message Sender')
  		thread.start()
  		while True: time.sleep(100)
	except (KeyboardInterrupt, SystemExit):
		logger.error('\n! Received keyboard interrupt, quitting threads.\n Exiting main thread')
  		#print '\n! Received keyboard interrupt, quitting threads.\n'
  		thread.exit()

def msg_sender(data,isrun,connection):
	response = "No Response"
	for row in data:
		if row[2]==NEW:
			publish_message(row,connection,row[4])
			time.sleep(1000)



def on_connect(client, userdata, rc):
	pass
	#print "Connection returned result: "+str(rc) + "client: "+str(client)
def on_publish(mosq, obj, mid):
	pass
    #print("mid: " + str(mid))

def publish_message(response,dbconnection,sending_type):
	#print response

	msg_payload = '_id = '+str(response[0])+' subscribid = '+str(response[1]) + ' msg= '+str(response[3])+' status= '+str(response[2]) 
	if sending_type==TYPE_MSG:
		logger.info('sending type : TYPE_MSG')
		mqttc = mqtt.Client()
		mqttc.on_connect = on_connect
		mqttc.on_publish = on_publish
		try:
			mqttc.connect(MQTT_SERVER_PATH, MQTT_SERVER_PORT,100)
			logger.warn('sending.. token: %s: response text: %s' ,response[1], msg_payload)
			mqttc.publish(str(response[1]), msg_payload,1)
			updateSuccessStatus(response[0],dbconnection,2)
			counter=0
			mqttc.loop(2)
			#mqttc.disconnect()
		except Exception,e:
			logger.error('Error %s',e)
			SystemExit(1)
	elif sending_type==TYPE_SMS:
		logger.info('sending type : TYPE_SMS')
		updateSuccessStatus(response[0],dbconnection,1)
		logger.info('SMS type sending is not implemented yet...discarding')
	elif sending_type==TYPE_EMAIL:
		logger.info('sending type : TYPE_EMAIL')
		updateSuccessStatus(response[0],dbconnection,1)
		logger.info('EMAIL type sending is not implemented yet...discarding')
	
def initializeDatabase(schema, userid, userpass, hostaddr, hostport):
	logger.info('initializing database postgres....')
	# initialize postgres database connection with kobotoolbox. 
	try:
		conn = psycopg2.connect(database=schema, user=userid, password=userpass, host=hostaddr, port=hostport)
		logger.debug('Opened database successfully')		
	except psycopg2.DatabseError,e:
		logger.error('Error %s',e)	
		
	return conn

def fetchData(conn):
	cur = conn.cursor()
	rawquery = "SELECT id,subscribeid,status,response,msg_type FROM public.main_message_queue where status="+str(NEW)+" OR status="+str(FAIL)+" LIMIT 5"
	
	logger.debug('raw qeury: %s',rawquery)
	try:
		cur.execute(rawquery)
	except psycopg2.DatabseError,e:	
		logger.error('Error %s',e)	
	#cur.execute("SELECT main_message_queue.subscribeid,main_message_queue.status,main_message_queue.response FROM public.main_message_queue")
	return cur.fetchall()

def updateSuccessStatus( msgid,dbconnection,status_type):
		cur = dbconnection.cursor()
		updateQuery = "UPDATE public.main_message_queue SET status="+ str(status_type) +" WHERE id="+str(msgid)+""
		logger.debug('update Query: %s',updateQuery)
		try:
			cur.execute(updateQuery)
			dbconnection.commit()
			logger.warn('successfully updated status')	
		except psycopg2.DatabseError,e:	
			logger.error('Error %s',e)	
	
   
 

