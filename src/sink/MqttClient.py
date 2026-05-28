# import requests
import json
import logging
import paho.mqtt.client
import paho.mqtt.enums
import ssl
import time

from dataclasses import dataclass

@dataclass
class MqttConfig:
    host: str = "localhost"
    port: int = 1883
    topic: str = "streamdeck/{{serial}}"
    tls_client: bool = False
    username: str | None = None
    password: str | None = None
    clientId: str | None = None
    qos: int = 0

log = logging.getLogger(__name__)
log_paho = logging.getLogger("paho")

def on_connect(client, userdata, flags, rc, properties):
    log.info(f"on_connect: rc={rc}")

def on_connect_fail(client, userdata):
    log.info(f"on_connect_fail")

def on_publish(client, userdata, mid, rc, properties):
    log.info(f"on_publish: rc={rc}")

def on_disconnect(client, userdata, flags, rc, properties):
    log.info(f"on_disconnect: rc={rc}")

def on_log(client, userdata, level, buf):
    level_map = {
        0x01: logging.INFO,
        0x02: logging.INFO,
        0x04: logging.WARNING,
        0x08: logging.ERROR,
        0x10: logging.DEBUG
    }
    log_paho.log(level_map[level], buf)

class MqttClient:

    def __init__(self, config, mfg, sn, hostInfo):
        
        config = MqttConfig(**config)

        # The config for this consumer allows a placeholder in the topic for the
        # device serial number.  Replace the placeholder with the runtime value.
        config.topic = config.topic.replace("{{serial}}", sn)
        
        # Constuct a client Id from host info
        if config.clientId is None:
            mac = hostInfo["phyAddress"].replace(":", "")
            config.clientId = f"{hostInfo["hostname"]}_{mac[len(mac)-4:]}"

        # Instantiate MQTT client
        client = paho.mqtt.client.Client(
            callback_api_version=paho.mqtt.enums.CallbackAPIVersion.VERSION2,
            client_id=config.clientId,
            protocol=paho.mqtt.client.MQTTv311
        )

        # Config may require the client to use TLS
        if config.tls_client:
            client.tls_set(
                cert_reqs=ssl.CERT_REQUIRED,
                tls_version=ssl.PROTOCOL_TLS_CLIENT
            )

        # Config may include credentials
        if config.username is not None and config.password is not None:
            client.username_pw_set(config.username, config.password)

        # Attach event handlers
        client.on_connect = on_connect
        client.on_connect_fail = on_connect_fail
        client.on_disconnect = on_disconnect
        client.on_log = on_log
        client.on_publish = on_publish

        # Store client and config as instance variables
        self._client = client
        self._config = config

    def start(self) -> None:
        self._client.connect(self._config.host, self._config.port)
        self._client.loop_start()

    def publish(self, payload: dict) -> bool:
        msgInfo = self._client.publish(self._config.topic, json.dumps(payload))
        try:
            msgInfo.wait_for_publish(timeout=3.0)
            return True
        except Exception:
            return False

    def stop(self) -> None:
        self._client.disconnect()
        time.sleep(0.5)
        self._client.loop_stop()
