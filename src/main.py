import json
import logging
import logging.config

from concurrent.futures import Future
from pathlib import Path
from typing import Tuple

#
# Logging configuration needs to be done early so other
# modules will pick up the config.
#
configFile = Path(__file__).resolve().parent / "config.json"
with open(configFile, "r", encoding="utf8") as cf:
    config = json.load(cf)
logging.config.dictConfig(config["logging.config"])

from driver import Driver
from gateway import Gateway

log = logging.getLogger(__name__)
log.info("--- Stream Deck Gateway ---")

#  Instantiate the driver
driver = Driver()
log.info(f"{driver.deviceInfo['manufacturer']} {driver.deviceInfo['product']} {driver.deviceInfo['serial']}")

# Instantiate the Gateway
gw = Gateway(topic=f"streamdeck/{driver.deviceInfo['serial']}")

# Begin listening for  hardware events
driver.start()

try:

    while True:
        event = driver.getEvent()
        if event is not None:
            log.info(f"event: {event}")
            future: Future[Tuple[int, str]] = gw.publish({"keyState": event})
            rc, mid = future.result(timeout=2.0)

except KeyboardInterrupt:
    log.info("Stopping...")
finally:
    try:
        driver.stop()
    except Exception:
        pass
