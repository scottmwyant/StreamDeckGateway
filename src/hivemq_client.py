import ssl
import time
import paho.mqtt.client as mqtt
from paho.mqtt.enums import CallbackAPIVersion 

HIVEMQ_CLUSTER_URL = "5c35dccf09a24a34a0f4ec3674557135.s2.eu.hivemq.cloud"
HIVEMQ_USER = "testing"
HIVEMQ_PW = "testing123"

# =============================================================================
#   C A L L B A C K S
# =============================================================================

def on_connect(client, userdata, flags, rc, properties=None):
    print("CONNACK received with code %s." % rc)

def on_publish(client, userdata, mid, rc, properties=None):
    print("mid: " + str(mid))

def on_subscribe(client, userdata, mid, granted_qos, properties=None):
    print("Subscribed: " + str(mid) + " " + str(granted_qos))

def on_message(client, userdata, msg):
    print(msg.topic + " " + str(msg.qos) + " " + str(msg.payload))

def build_client():
    #
    # Configure the client
    #   > clientId
    #   > TLS
    #   > auth (username, password)
    #   > bind callbacks into client
    #
    client = mqtt.Client(callback_api_version=CallbackAPIVersion.VERSION2, client_id="sbx", protocol=mqtt.MQTTv311)
    client.tls_set(cert_reqs=ssl.CERT_REQUIRED, tls_version=ssl.PROTOCOL_TLS_CLIENT)
    client.username_pw_set(HIVEMQ_USER, HIVEMQ_PW)
    client.on_connect = on_connect
    client.on_subscribe = on_subscribe
    client.on_message = on_message
    client.on_publish = on_publish
    return client

def run():
    client = build_client()
    client.connect(HIVEMQ_CLUSTER_URL, 8883)
    client.subscribe("encyclopedia/#", qos=1)
    client.publish("encyclopedia/temperature", payload="hot", qos=1)

    try:
        client.loop_forever()
    except KeyboardInterrupt:
        print("Stopping...")

if __name__ == "__main__":
    run()