import logging
import ssl
import paho.mqtt.client
import paho.mqtt.enums

from dataclasses import dataclass
from typing import Any, Dict, Optional

log = logging.getLogger(__name__)
paholog = logging.getLogger(f"{__name__}.paho")

@dataclass
class MqttClientConfig:
    host: str = "localhost"
    port: int = 1883
    topic: str = "streamdeck/{{serial}}"
    tls_client: bool = False
    username: str | None = None
    password: str | None = None
    clientId: str | None = None
    qos: int = 0

class Gateway:

    def __init__(self, mqttConfig: MqttClientConfig):

        client = paho.mqtt.client.Client(
            callback_api_version=paho.mqtt.enums.CallbackAPIVersion.VERSION2,
            client_id=mqttConfig.clientId,
            protocol=paho.mqtt.client.MQTTv311
        )
        if mqttConfig.tls_client:
            client.tls_set(
                cert_reqs=ssl.CERT_REQUIRED,
                tls_version=ssl.PROTOCOL_TLS_CLIENT
            )
        if mqttConfig.username is not None and mqttConfig.password is not None:
            client.username_pw_set(mqttConfig.username, mqttConfig.password)
    
        client.on_connect = self._on_connect
        client.on_connect_fail = self._on_connect_fail
        client.on_disconnect = self._on_disconnect
        client.on_log = self._on_log
        client.on_publish = self._on_publish
        
        self._config = mqttConfig
        self._client = client

    def start(self) -> None:
        self._client.connect(self._config.host, self._config.port)
        self._client.loop_start()

    def stop(self) -> None:
        """Request thread shutdown and wait for it to exit."""
        self._client.disconnect()
        self._client.loop_stop()
         
    def publish(self, payload: str) -> bool:
        info = self._client.publish(
            topic=self._config.topic,
            payload=payload,
            qos=self._config.qos,
            retain=False
        )
        success = True
        try:
            info.wait_for_publish(timeout=1.2)
        except:
            success = False
        return success

    # =========================================================================
    #   P R I V A T E
    # =========================================================================

    def _on_connect(self, client, userdata, flags, rc, properties):
        log.info(f"on_connect: rc={rc}")

    def _on_connect_fail(self, client, userdata):
        log.info(f"on_connect_fail")

    def _on_publish(self, client, userdata, mid, rc, properties):
        log.info(f"on_publish: rc={rc}")

    def _on_disconnect(self, client, userdata, flags, rc, properties):
        log.info(f"on_disconnect: rc={rc}")

    def _on_log(self, client, userdata, level, buf):
        level_map = {
            0x01: logging.INFO,
            0x02: logging.INFO,
            0x04: logging.WARNING,
            0x08: logging.ERROR,
            0x10: logging.DEBUG
        }
        paholog.log(level_map[level], buf)

__all__ = ["Gateway", "MqttClientConfig"]
