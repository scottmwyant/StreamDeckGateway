import json
import logging
import logging.config
import utils

from pathlib import Path
from dataclasses import asdict

def read_config_file():
    configFile = Path(__file__).resolve().parent / "config.json"
    with open(configFile, "r", encoding="utf8") as cf:
        cfg = json.load(cf)
    return cfg

def configure_logging(config):
    logging.config.dictConfig(config)

cfg = read_config_file()
configure_logging(cfg["logging"])

#
# ============================================================================
#

import sink.MqttClient as MqttClient
from driver import Streamdeck

log = logging.getLogger(__name__)
log.info("--- Streamdeck Gateway ---")

# Get information that identifies the host
log.debug("Collecting host info")
hostInfo = utils.getHostInfo()
log.debug(f"{asdict(hostInfo)}")

# Instantiate the producer
sd = Streamdeck()

# Instantiate the consumer and start it
sink = MqttClient.MqttClient(cfg["mqtt"], sd.manufacturer, sd.serial)
sink.start()

#
# =============================================================================
#  Main loop
# =============================================================================
#

shutdown_host = False
while True:
    try:
        state = sd.listen(timeout_ms=60)
    except KeyboardInterrupt:
        break
    if "exit" in state:
        shutdown_host = True
    if state.get("value") is not None:
        state["host"] = asdict(hostInfo)
        state["host"]["uptime"] = utils._getSystemUptime()
        state["serial"] = sd.serial
        if sink.publish(state):
            sd.signalMessageSuccess()
        else:
            sd.signalMessageFailure()

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
         
log.info("Close connection to streamdeck")
sd.close()
log.info("Stopping data flow to consumer")
sink.stop()
log.info("Exit.")

if shutdown_host:
    utils.shutdown()