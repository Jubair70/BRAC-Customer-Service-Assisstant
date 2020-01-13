import paho.mqtt.client as mqtt
from microfinance.settings import MQTT_SERVER_PATH, MQTT_SERVER_PORT

def send_push_msg(topic = "/CSA/1/11111", payload = None, qos = 1, retained = False):
    # MQTT_SERVER_PATH = "192.168.22.114"
    # MQTT_SERVER_PORT = 1884
    # MQTT_SUBSCRIBE_TOKEN = "/CSA/1/11111"
    # MQTT_SERVER_RESPONSE = "response from view=> ayayayayya :)"
    
    mqttc = mqtt.Client("",True)
    mqttc.connect(MQTT_SERVER_PATH, MQTT_SERVER_PORT,100)
    print "sending.. token: %s: response text: %s" % (topic, payload)
    mqttc.publish(topic, payload, qos , retained)
    mqttc.disconnect()