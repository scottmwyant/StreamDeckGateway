import json
import logging
import threading
import time

from concurrent.futures import Future
from dataclasses import dataclass
from queue import Queue, Empty
from typing import Any, Dict, Optional

import paho.mqtt.client as paho
# import paho.mqtt

log = logging.getLogger(__name__)

@dataclass
class PublishRequest:
	payload: Dict[str, Any]
	topic: Optional[str]
	future: Future

class Gateway:

	def __init__(self, host: str = "localhost", port: int = 1883, topic: str = "streamdeck/events", qos: int = 0):
		self.host = host
		self.port = port
		self.defaultTopic = topic
		self.qos = qos

		self._tx: Queue[PublishRequest] = Queue()
		self._stop_event = threading.Event()
		self._thread = threading.Thread(target=self._worker_loop, name="Gateway", daemon=False)
		self._client: Optional[paho.Client] = None

		# Start thread immediately so API is ready (mirrors HID driver behavior)
		self._thread.start()

	def start(self) -> None:
		# kept for API symmetry with Driver; thread already started in ctor
		return None

	def stop(self) -> None:
		"""Request thread shutdown and wait for it to exit."""
		self._stop_event.set()
		
		#
		# Assume the other thread is blocking on the message queue, unblock it
		# to signal shutdown is coming.
		#
		try:
			self._tx.put(None, block=False)  # type: ignore[arg-type]
		except Exception:
			pass
		finally:
			time.sleep(0.05)

		try:
			self._thread.join(timeout=2.0)
			if self._thread.is_alive():
				log.warning("MQTT thread did not exit cleanly!")
		except Exception:
			log.warning("MQTT thread did not exit cleanly!")
			
	def publish(self, payload: Dict[str, Any], topic: Optional[str] = None) -> Future:
		"""Queue a payload to be published. Returns a Future for the publish result.
		The future resolves to a tuple `(rc, mid)` on success or raises an exception.
		"""
		future: Future = Future()
		req = PublishRequest(payload, topic, future)
		try:
			self._tx.put(req, block=False)
		except Exception as e:
			future.set_exception(e)
		return future

    # =========================================================================
    #   P R I V A T E
    # =========================================================================

	def _on_connect(self, client, userdata, flags, rc):
		if rc == 0:
			log.info("MQTT connected to %s:%d", self.host, self.port)
		else:
			log.warning("MQTT connect returned rc=%s", rc)

    # =========================================================================
    #   M Q T T    T H R E A D
    # =========================================================================

	def _worker_loop(self) -> None:
		"""Background loop: connect MQTT, then consume publish requests from queue."""
		client = paho.Client()
		client.on_connect = self._on_connect
		self._client = client

		try:
			client.connect(self.host, self.port, keepalive=60)
			client.loop_start()
		except Exception as e:
			log.exception("Failed to connect to MQTT broker: %s", e)

		while not self._stop_event.is_set():
			try:
				req = self._tx.get(timeout=0.2)
			except Empty:
				continue

			if req is None:
				break

			elif isinstance(req, PublishRequest):
				topic = req.topic if req.topic is not None else self.defaultTopic
				try:
					payload_str = json.dumps(req.payload)
				except Exception as e:
					req.future.set_exception(e)
					continue

				try:
					info = client.publish(topic, payload_str, qos=self.qos)
					# paho's publish returns an MQTTMessageInfo; wait briefly
					# to ensure it was queued
					# The rc is available as info.rc, mid as info.mid
					req.future.set_result((getattr(info, "rc", None), getattr(info, "mid", None)))
				except Exception as e:
					req.future.set_exception(e)


		# Drain any remaining requests and fail their futures
		while True:
			try:
				req = self._tx.get(block=False)
			except Empty:
				break
			if isinstance(req, PublishRequest):
				req.future.set_exception(RuntimeError("Gateway shutting down"))

		try:
			if self._client:
				self._client.loop_stop()
				self._client.disconnect()
		except Exception:
			pass

		log.debug("MQTT gateway loop exiting")

__all__ = ["Gateway"]
