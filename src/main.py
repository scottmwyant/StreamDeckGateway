import json
import logging
import logging.config
import paho.mqtt.client
import paho.mqtt.enums
import ssl
import subprocess
import time

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

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

@dataclass
class NetInfo:
    ifname: str
    operstate: str
    netAddress: str
    prefixlen: int
    phyAddress: Optional[str]

configFile = Path(__file__).resolve().parent / "config.json"
with open(configFile, "r", encoding="utf8") as cf:
    cfg = json.load(cf)
mqtt = MqttConfig(**cfg["mqtt"])
logging.config.dictConfig(cfg["logging"])
cfg = None

# ^ ^ ^ Logging setup ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^

log = logging.getLogger(__name__)
log_paho = logging.getLogger("paho")

from driver import Streamdeck

# =============================================================================
#   P R I V A T E
# =============================================================================

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

def _getInterfaceNames() -> List[str]:
    result: subprocess.CompletedProcess = subprocess.run(
        ["ls /sys/class/net"],
        capture_output=True,
        text=True,
        shell=True
    )
    if result.stdout:
        return (result.stdout.strip()).split("\n")
    return list()
        
def _getPhysicalAddress(ifName) -> Dict | None:
    result: subprocess.CompletedProcess = subprocess.run(
        ["ip", "-4", "-br", "-j", "link", "show", ifName],
        capture_output=True,
        text=True
    )
    if result.stdout:
        return (json.loads(result.stdout))[0]["address"]
    
def _getNetAddress(ifName) -> Dict | None:
    result: subprocess.CompletedProcess = subprocess.run(
        ["ip", "-4", "-br", "-j", "address", "show", ifName],
        capture_output=True,
        text=True
    )
    if result.stdout:
        return (json.loads(result.stdout))[0]

def getNetInfo() -> NetInfo | None:
    names = _getInterfaceNames()
    try:
        i = names.index("lo")
        names.pop(i)
    except ValueError:
        pass
    _if = names[0]
    
    netInfo = _getNetAddress(_if)
    if netInfo:
        netInfo["netAddress"] = netInfo["addr_info"][0]["local"]
        netInfo["prefixlen"] = netInfo["addr_info"][0]["prefixlen"]
        del netInfo["addr_info"]
        mac = _getPhysicalAddress(_if)
        if mac:
            netInfo["phyAddress"] = mac
        return NetInfo(**netInfo)

log.info("--- Stream Deck Gateway ---")

sd = Streamdeck()
mqtt.topic = mqtt.topic.replace("{{serial}}", sd.serial)

client = paho.mqtt.client.Client(
    callback_api_version=paho.mqtt.enums.CallbackAPIVersion.VERSION2,
    client_id=mqtt.clientId,
    protocol=paho.mqtt.client.MQTTv311
)
if mqtt.tls_client:
    client.tls_set(
        cert_reqs=ssl.CERT_REQUIRED,
        tls_version=ssl.PROTOCOL_TLS_CLIENT
    )
if mqtt.username is not None and mqtt.password is not None:
    client.username_pw_set(mqtt.username, mqtt.password)

client.on_connect = on_connect
client.on_connect_fail = on_connect_fail
client.on_disconnect = on_disconnect
client.on_log = on_log
client.on_publish = on_publish
client.connect(mqtt.host, mqtt.port)
client.loop_start()

def _publish(payload: Dict) -> bool:
    msgInfo = client.publish(mqtt.topic, json.dumps(payload))
    try:
        msgInfo.wait_for_publish(timeout=3.0)
        return True
    except Exception:
        return False


shutdown = False
while True:
    try:
        state = sd.listen(timeout_ms=60)
    except KeyboardInterrupt:
        break
    if state:
        if "exit" in state:
            shutdown = True
            break
        if _publish(state):
            sd.signalMessageSuccess()
        else:
            sd.signalMessageFailure()
        
log.info("Close connection to streamdeck")
sd.close()
client.disconnect()
time.sleep(0.5)
client.loop_stop()
log.info("Exit.")

if shutdown:
    subprocess.run(["systemctl", "poweroff"])
