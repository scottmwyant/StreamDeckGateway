import json
import logging
import requests
import ssl

log = logging.getLogger(__name__)

class HttpClient():
    
    def __init__(self, config, mfg, sn):
        self._config = config
        self._mfg = mfg
        self._sn = sn

    def start(self):
        pass

    def publish(self, state):
        url = self._config["url"]
        try:
            response = requests.post(url, json=state, timeout=5)
            response.raise_for_status()
            return True
        except requests.RequestException as e:
            log.error(f"HTTP request failed: {e}")
            return False
        
    def stop(self):
        pass