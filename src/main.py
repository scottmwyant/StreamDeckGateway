import json
import logging
import logging.config
from pathlib import Path
from typing import Tuple, Dict, Any

configFile = Path(__file__).resolve().parent / "config.json"
with open(configFile, "r", encoding="utf8") as cf:
    config = json.load(cf)
logging.config.dictConfig(config["logging.config"])

# ^ ^ ^ Logging setup ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^

log = logging.getLogger(__name__)

from driver import Driver
from gateway import Gateway, MqttClientConfig

log.info("--- Stream Deck Gateway ---")

# Instantiate the driver
driver = Driver()
log.info(f"{driver.deviceInfo['manufacturer']} {driver.deviceInfo['product']} {driver.deviceInfo['serial']}")

# Expand topic path using hardware data 
mqttConfig = MqttClientConfig(**config["mqtt"])
deviceInfo = {"manufacturer": "Elgato", "product": "Stream Deck Mk.2", "serial": "8870"}
mqttConfig.topic = mqttConfig.topic.replace("{{serial}}", deviceInfo["serial"])

# Instantiate the gateway
gw = Gateway(mqttConfig)
gw.start()

# Listen for hardware events
driver.start()

# Stitch the driver and gateway together
# try:

#     while True:
#         event = driver.getEvent()
#         if event is not None:
#             log.info(f"event: {event}")
#             future: Future[Tuple[int, int]] = gw.publish({"keyState": event})
#             try:
#                 rc, mid = future.result(timeout=2.0)
#             except TimeoutError:
#                 rc = None
#             if rc == 0: # < Need to know the appropriate response code
#                 driver.signalMessageSuccess()
#             else:
#                 driver.signalMessageFailure()

# except KeyboardInterrupt:
#     log.info("Stopping...")
# finally:
#     try:
#         driver.stop()
#     except Exception:
#         pass

