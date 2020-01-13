import threading
import time
import paho.mqtt.client as mqtt

exitFlag = 0

MQTT_SERVER_PATH = "192.168.22.114"
MQTT_SERVER_PORT = 1884
MQTT_SUBSCRIBE_TOKEN = "/CSA/1/11111"
MQTT_SERVER_RESPONSE = "hahahahihihihohoho:)"

class myThread (threading.Thread):
    def __init__(self, threadID, name, counter):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.name = name
        self.counter = counter
    def run(self):
    	count = 1
        print "Starting " + self.name
        print_time(self.name, self.counter, count)
        print "Exiting " + self.name
    def exit():
		self.name.exit()

def print_time(threadName, delay, counter):

    while counter:
        if exitFlag:
            threadName.exit()
        time.sleep(delay)
        publish_message(threadName,counter)
        
       # counter -= 1
def publish_message(threadName, counter):
	mqttc = mqtt.Client("",True)
	mqttc.connect(MQTT_SERVER_PATH, MQTT_SERVER_PORT,100)
	print "sending.. token: %s: response text: %s" % (MQTT_SUBSCRIBE_TOKEN, MQTT_SERVER_RESPONSE)
	mqttc.publish(MQTT_SUBSCRIBE_TOKEN, MQTT_SERVER_RESPONSE+" "+str(counter))
	counter=0
	mqttc.disconnect()

def startSenderManager():
	try:
		thread=myThread(1, "Thread-1", 1)
		thread.daemon=True
		thread.start()
		while True: time.sleep(100)
	except (KeyboardInterrupt, SystemExit):
		print '\n! Received keyboard interrupt, quitting threads.\n'
		thread.exit()
# Start new Threads
#thread1.start()
#thread2.start()
	print "Exiting Main Thread"
