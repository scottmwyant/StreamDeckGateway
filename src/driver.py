import logging
import threading
import time

from concurrent.futures import Future
from dataclasses import dataclass
from enum import Enum
from pyhidapi.hid import Device
from queue import Queue, Empty
from typing import List, Dict, Tuple, Optional, Any

log = logging.getLogger(__name__)

BUTTON_COUNT = 15

@dataclass
class Button:
    state: int = 0
    timestamp: int = 0
    position: int = 0

@dataclass
class DeviceInfoReport:
    future: Future

@dataclass
class SetFeatureReport:
    raw: bytes
    future: Future

@dataclass
class GetFeatureReport:
    reportId: int
    future: Future

@dataclass
class OutputReport:
    raw: bytes
    future: Future

@dataclass
class ChangeDetail:
    index: int
    position: int
    duration_ms: int | None

@dataclass
class HardwareEvent:
    timestamp: int
    eventType: int
    value: int
    changeMask: int
    changeCount: int
    detail: List[ChangeDetail]

class EventType(Enum):
    KEY_UP = 0
    KEY_DOWN = 1
    KEY_UP_DOWN = 2
    WAKE_UP = 3
    NO_CHANGE = 4
    UNKNOWN=5

class Driver():

    def __init__(self):
        """Start a background thread that will manage the hardware connection."""
        self._doGetHidInputReport = False
        #
        # Start the background thread now so the public API is ready.
        # We won't start polling the device for input reports until the main
        # thread calls .start(), but we're in position to apply a configuration
        #
        self._rx = Queue()
        self._tx = Queue()
        self._stop_event = threading.Event()
        self._thread = threading.Thread(
            target=self._worker_loop,
            args=(self._rx, self._tx),
            daemon=False,
            name="Driver"
        )
        self._thread.start()

        #
        # When the background thread starts, device info object is put into the
        # queue, it's immidiately pulled out and merged with the result from
        # 'getUnitInformation'.
        #
        device = self._rx.get(timeout=0.5)
        self.deviceInfo: Dict = self.getUnitInformation()
        keys = ("manufacturer", "product", "serial")
        self.deviceInfo.update({k: device[k] for k in keys})
        # BUTTON_COUNT = self.deviceInfo["keypadRows"] * self.deviceInfo["keypadColumns"]

    def start(self):
        self._doGetHidInputReport = True

    def stop(self):
        """Stop listening for HID input reports.  The HID handle remains open
        and the worker thread will still process commnads."""
        self._doGetHidInputReport = False

    def close(self):
        """Use for clean shutdown.  Signal the worker thread to stop and
        release resources."""
        self._stop_event.set()
        self._thread.join(timeout=2.0)
        if self._thread.is_alive():
            log.warning("HID thread did not exit cleanly!")

    def getEvent(self) -> Tuple[Any] | None:
        try:
            return self._rx.get(timeout=0.2)
        except Empty:
            return None

    def signalMessageSuccess(self):
        """Put a message into the queue that the HID worker thread watches"""
        btn = BUTTON_COUNT - 1
        self.fillKeyWithColor(btn, "#00ff00")
        time.sleep(0.5)
        self.fillKeyWithColor(btn, "#000000")

    def signalMessageFailure(self):
        """Put a message into the queue that the HID worker thread watches"""
        btn = BUTTON_COUNT - 1
        self.fillKeyWithColor(btn, "#ff0000")
        time.sleep(0.5)
        self.fillKeyWithColor(btn, "#000000")
        time.sleep(0.5)
        self.fillKeyWithColor(btn, "#ff0000")
        time.sleep(0.5)
        self.fillKeyWithColor(btn, "#000000")


    #
    # =========================================================================
    #   Feature Reports - Getters
    #   https://docs.elgato.com/streamdeck/hid/module-15_32#feature-report---getters
    # =========================================================================
    #

    def getUnitSerialNumber(self) -> str:
        """Request the unit's serial number string"""
        offset = 2
        res = self._getFeatureReport(0x06)
        return res[offset:offset+res[1]].decode("utf8")
        
    def getIdleSecondsBeforeSleep(self):
        """Request the duration, in seconds, of idle before the unit enters Sleep Mode."""
        offset = 2
        res = self._getFeatureReport(0x0a)
        return int.from_bytes(res[offset:offset + res[1]], "little")

    def getUnitInformation(self):
        """Request information about the unit, including keypad matrix layout, LCD geometry and more."""
        res = self._getFeatureReport(0x08)
        return {
            "keypadRows": res[1],
            "keypadColumns": res[2],
            "keyWidth": int.from_bytes(res[3:4]),
            "keyHeight": int.from_bytes(res[5:6]),
            "lcdWidth": int.from_bytes(res[7:8]),
            "lcdHeight": int.from_bytes(res[9:10]),
            "imageColorScheme": res[12],
            "numKeyImages": res[13],
            "numLcdImages": res[14],
            "numDemoFrames": res[15]
        }

    #
    # =========================================================================
    #   Feature Reports - Setters
    #   https://docs.elgato.com/streamdeck/hid/module-15_32#feature-report---setters
    # =========================================================================
    #

    def showLogo(self):
        """Forcibly trigger the display of the boot logo."""
        report = bytearray(32)
        report[0:2] = (0x03, 0x02)
        return self._sendFeatureReport(report)

    def fillLcdWithColor(self, rgb: Tuple[int] | str | bytes):
        """Fill the entire LCD with a given RGB color."""
        value = self._validateColor(rgb)
        report = bytearray(32)
        report[0:2] = (0x03, 0x05)
        report[2:5] = value
        return self._sendFeatureReport(report)

    def fillKeyWithColor(self, index: int, rgb: Tuple[int] | str | bytes):
        """Fill a single key with a given RGB color."""
        if not 0 <= index <= (BUTTON_COUNT-1):
            raise ValueError(f"Invalid button index: {index}")
        value = self._validateColor(rgb)
        report = bytearray(32)
        report[0:3] = (0x03, 0x06, index)
        report[3:6] = value
        return self._sendFeatureReport(report)

    def setBacklightBrightness(self, value: int):
        """Set the LCD backlight brightness."""
        value = value if 0 <= value <= 100 else 100
        report = bytearray(32)
        report[0:4] = (0x03, 0x08, value)
        return self._sendFeatureReport(report)
    
    def setIdleTimeBeforeSleep(self, value: int):
        """Set the duration, in seconds, of idle before the unit enters Sleep Mode."""
        report = bytearray(32)
        report[0:2] = (0x03, 0x0D)
        report[2:6] = value.to_bytes(length=4, byteorder="little", signed=False)
        return self._sendFeatureReport(report)
    
    def showBackgroundByIndex(self, index: int):
        """Show the background stored at the specified index."""
        if not 0 <= index <= 255:
            raise ValueError("index must be UINT8")
        report = bytearray(32)
        report[0:3] = (0x03, 0x13, index)
        return self._sendFeatureReport(report)
        
    # =========================================================================
    #   P R I V A T E
    # =========================================================================
    
    def _getFeatureReport(self, reportId) -> bytes:
        future: Future[bytes] = Future()
        report = GetFeatureReport(reportId, future)
        try:
            self._tx.put(report, block=False)
            return future.result(timeout=3)
        except Empty as e:
            log.info("Failed to add GetFeatureReport to queue")
            raise

    def _sendFeatureReport(self, report: bytearray | bytes) -> None:
        if isinstance(report, bytearray):
            report = bytes(report)

        future = Future()
        rpt = SetFeatureReport(report, future)
        self._tx.put(rpt, block=False)
        return rpt.future.result(timeout=5)
    
    def _validateColor(self, rgb: Tuple[int, int, int] | str | bytes) -> bytes:
        
        value = None
        if isinstance(rgb, tuple) and \
            len(rgb) == 3 and \
            isinstance(rgb[0], int) and (0 <= rgb[0] <= 255) and \
            isinstance(rgb[1], int) and (0 <= rgb[1] <= 255) and \
            isinstance(rgb[2], int) and (0 <= rgb[2] <= 255):
            value = bytes(rgb)
        
        if isinstance(rgb, str):
            if len(rgb) == 6:
                value = bytes.fromhex(rgb)
            elif len(rgb) == 7 and rgb.startswith("#"):
                value = bytes.fromhex(rgb[1:])

        if isinstance(rgb, bytes) and len(rgb) == 3:
            value = rgb

        if value is None:
            raise ValueError(f"Invalid value for argument 'rgb' {type(rgb)}")
        
        return value
    
    # =========================================================================
    #   H I D    T H R E A D
    # =========================================================================
        
    def _worker_loop(self, rx: Queue, tx: Queue) -> None:
        """This function runs on a background thread, watching for messages on rx,
        putting messages into tx."""
        
        VID, PID = (0x0fd9, 0x0080)

        #
        # These are intentionally flipped. The method signature is designed to
        # match the caller's perspective. The first argument passed by the
        # caller is the Queue that it will use to RECEIVE data, the second
        # argument is the Queue it will TRANSMIT data.
        #
        # For sanity, the assignments are flipped so in this method
        # we can use _tx.put() and _rx.get().
        #
        _rx = tx
        _tx = rx

        #
        # Don't need to bother enumerating hardware attached to the system
        # since this project is tailored to one specific model.  We will
        # hardcode the VENDOR and PRODUCT ids.
        #
        with Device(VID, PID) as dev: 
            
            # First message goes into the queue
            _tx.put({
                "manufacturer": dev.manufacturer,
                "product": dev.product,
                "serial": dev.serial
            })

            model = Streamdeck()

            #
            # Watch for events coming in from the main thread then watch HID.
            # Block on the HID read to maximize responsiveness on that end.
            #
            while not self._stop_event.is_set():

                # Check for commands coming in from the main thread
                try:
                    ms = 50 if self._doGetHidInputReport else 500
                    cmd = _rx.get(timeout=(ms/1000))
                except Empty:
                    pass

                # Forward the command to the hardware, use the runtime type
                # to know which method to call on the device instance. 
                if isinstance(cmd, GetFeatureReport):
                    res = dev.get_feature_report(cmd.reportId, 32)
                    cmd.future.set_result(res)
            
                elif isinstance(cmd, SetFeatureReport):
                    res = dev.set_feature_report(cmd.raw)
                    cmd.future.set_result(res)
                
                elif isinstance(cmd, OutputReport):
                    pass

                if self._doGetHidInputReport:
                    rawReport: bytes = dev.read(size=512, timeout=50)
                    if len(rawReport):
                        newState = model.handle_hid_input_report(rawReport)
                        if newState:
                            _tx.put(newState, block=False)
            
        # Exiting the 'with' block closes the HID handle
        log.debug("HID thread exiting, device closed")
        return # <= End the thread

class InputReport:
    """Represents a parsed HID input report."""

    def __init__(self, report: bytes | None = None):
        """Parse a 512-byte HID report into an InputReport instance."""
        self.timestamp = int(time.time() * 1000)
        
        if report is None:
            report = bytes([0x01, 0x00, 0x0f, 0x00] + ([0x00] * 508))
            
        if not (isinstance(report, (bytes, bytearray)) and len(report) == 512):
            raise ValueError("report must be exactly 512 bytes")
        
        self.id = report[0]
        self.command = report[1]
        length = int.from_bytes(report[2:4], "little")
        if length != BUTTON_COUNT:
            raise ValueError(f"unexpected payload length: {length}")
        self._report = report[0:4+length]
        # Build bit-packed integer where LSB = button 0
        payload = report[4:4 + length]
        self.value = 0
        for i, byteValue in enumerate(payload):
            self.value |= int(bool(byteValue)) << i
        self.countDown = self.value.bit_count()
        self.countUp = length - self.countDown

        # Attributes to be set externally after comparison to previous report
        self.changeMask: int | None = None
        self.changeCount: int | None = None
        self.eventType: int | None = None

    def hasButtonChanged(self, index: int) -> bool:
        """Check if a button has changed state since the previous report."""
        if self.changeMask is None:
            raise ValueError("changeMask is not set")
        if not 0 <= index < BUTTON_COUNT:
            raise IndexError(f"index must be in range 0..{BUTTON_COUNT-1}")
        return bool((self.changeMask >> index) & 1)

    def isButtonDown(self, index: int) -> bool:
        """Check if a button is currently down."""
        if not 0 <= index < BUTTON_COUNT:
            raise ValueError(f"index must be in range 0..{BUTTON_COUNT-1}")
        return bool((self.value >> index) & 1)

class Streamdeck:

    def __init__(self) -> None:
        # Initialize with a report indicating all buttons up
        self._buffer = [InputReport()]
        self._value = 0
        # Initialize a logical model, all switches off
        self._model = [Button() for _ in range(BUTTON_COUNT)]

    def _determineEventType(self, report: InputReport) -> int:
        """
        Compare the current report to the previous report to
        characterize the type of event.  Returns one of the following
        event type codes: 0=KeyUp, 1=KeyDown, 2=KeyUpDown,
        3=WakeUp, 4=NoChange.
        """

        # Compare to last report in buffer to determine event type
        if self._buffer[-1].value == report.value:
                return EventType.WAKE_UP.value if report.value == 0 else EventType.NO_CHANGE.value

        isUp = False
        isDown = False
        for i in range(BUTTON_COUNT):
            # check if button state has changed
            if report.hasButtonChanged(i):
                if report.isButtonDown(i):
                    isDown = True
                else:
                    isUp = True
        
        if isUp and not isDown:
            return EventType.KEY_UP.value
        
        if isDown and not isUp:
            return EventType.KEY_DOWN.value
        
        if isUp and isDown:
            return EventType.KEY_UP_DOWN.value
    
        return EventType.UNKNOWN.value
    
    def handle_hid_input_report(self, report: bytes) -> List[int] | None:
        hwEvent = self._computeChanges(report)
        log.debug(hwEvent)
        if hwEvent.changeCount > 0:
            newState = self._updateModel(hwEvent)
            # log.debug(newState)
            return newState


    
    # def _sendEventData_MQTT(self, payload: Dict) -> Tuple[int, str]:
    #     """Send the event data to MQTT broker.
        
    #     Connects to the MQTT broker, publishes the event, and disconnects.
    #     Since events are infrequent, a new connection is created per event.
        
    #     Args:
    #         payload: Dictionary containing event data to publish
            
    #     Returns:
    #         Tuple of (status_code, message)
    #     """
    #     try:
    #         # MQTT configuration
    #         broker = "localhost"
    #         port = 1883
    #         topic = "streamdeck/events"
            
    #         # Create MQTT client and set up callbacks
    #         client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
            
    #         def on_connect(client, userdata, flags, rc):
    #             if rc != 0:
    #                 raise mqtt.MQTTException(f"Connection failed with code {rc}")
            
    #         def on_publish(client, userdata, mid):
    #             pass
            
    #         def on_disconnect(client, userdata, rc):
    #             pass
            
    #         client.on_connect = on_connect
    #         client.on_publish = on_publish
    #         client.on_disconnect = on_disconnect
            
    #         # Connect to broker
    #         client.connect(broker, port, keepalive=5)
            
    #         # Publish the event data as JSON
    #         message = json.dumps(payload)
    #         result = client.publish(topic, message, qos=1)
            
    #         # Wait for publish to complete
    #         client.loop(timeout=1.0)
            
    #         # Disconnect
    #         client.disconnect()
            
    #         if result.rc == mqtt.MQTT_ERR_SUCCESS:
    #             return 200, "Event published successfully"
    #         else:
    #             return 400, f"Failed to publish: {mqtt.error_string(result.rc)}"
                
    #     except Exception as e:
    #         return 500, f"MQTT error: {str(e)}"

    def _showResult(self, res: str) -> None:
        """Stub: show the result of sending event data.
        """
        pass
        # log.info(f"Result: {res}")

    def _updateModel(self, hwEvent: HardwareEvent) -> List[int] | None:
        """Update the internal model based on the changes detected
        in the input report.  Returns event data for further processing.
        """

        # This is where we translate hardware events to logical events
        # Button profile should be considered, e.g. momentary vs toggle vs double-toggle
        # Consider a long-press could communicate higher urgency.

        # The question is where do we set the threshold for long press?
        # Do we send the duration out to the higher level system?
        # Seems config file would be apporate, so different systems do not
        # have the opportunity to disagree on what a long-press is.
        # Keeping the logic local also enables immidiate feedback.
        #
        # Next question is what semantics do we send?
        # Maybe send an array of integer values (0,1,2).

        stateChange = False
        for btn in hwEvent.detail:
            index = btn.index
            position = btn.position
            self._model[index].timestamp = hwEvent.timestamp
            self._model[index].position = position

            if position == 0:
                stateChange = True
                level = 1 if (btn.duration_ms if btn.duration_ms is not None else 0) < 1000 else 2
                self._model[index].state = level if self._model[index].state == 0 else 0
                self._repaintButton(index, self._model[index].state)
        return [x.state for x in self._model] if stateChange else None

    def _computeChanges(self, report: InputReport | bytearray | bytes) -> HardwareEvent:
        # Accept either raw bytes or an InputReport instance
        if isinstance(report, InputReport):
            rpt = report
        elif isinstance(report, (bytes, bytearray)):
            rpt = InputReport(report)
        else:
            raise TypeError("report must be bytes or InputReport instance")
        
        # Now that we are sure we have an InputReport, we can set
        # values for attributes that depend on the previous report
        # i.e. the last one in the buffer.

        rpt.changeMask = self._buffer[-1].value ^ rpt.value
        rpt.changeCount = rpt.changeMask.bit_count()
        rpt.eventType = self._determineEventType(rpt)

        # What's thhe logic for a "switch" or for a "long-press"?
        
        # 1 - Momentary button that toggles a software switch.
        #     
        #     > When there is a KeyDown, check the profile for that button.
        #     > If it's single-action (momentary) fire the event immediately.
        #     > If it's a double-action, you have to wait for KeyUp to get duration.
        #
        #     > Can't fire an action on KeyDown becuase that may
        #     > turn into a long-press which would require a different action.
        #     > So we wait for KeyUp, and check the duration.
        #     > KeyDown events just go into the buffer
        #     > KeyUp events trigger logic to cycle through the buffer to find
        #     > the corresponding KeyDown and measure duration.
        #     > Once we have duration, we have the action defined.


        # The steps above calculate attributes for the event by looking at
        # deltas from the previous report.  Now we look at each button.

        changedButtons: List[ChangeDetail] = []

        # Iterate over the report payload (each button)
        # Get the profile for the button and call the appropriate handler.
        # 
        # 
        # , compare to previous reports.
        # May require cyclying back through multiple reports to find the last event
        # for the given button.
        for i in range(BUTTON_COUNT):
            if rpt.hasButtonChanged(i):
                obj = ChangeDetail(i, int(rpt.isButtonDown(i)), None)
                if not rpt.isButtonDown(i):
                    # Search the buffer for the most recent KeyDown event on this button
                    # to calculate duration.  If not found, duration is 0.
                    # Could also consider a secondary data structure, keeping the details
                    # for each most recent button event in a dictionary.  This assumes
                    # button state always toggles, the only exception should be wakeup.
                    ms = 0
                    for x in range(len(self._buffer)):
                        e = self._buffer[-1 - x]
                        if e.isButtonDown(i):
                                ms = rpt.timestamp - e.timestamp
                    obj.duration_ms = ms


                    # Get the timestamp for the inverse state from the model...
                    # Want to assume that the last event is always the opposite state
                    # but that's not really safe.  When you wake up the device, the
                    # timestamp of the KeyDown will be missed, so you'll get a KeyUp
                    # without a prior KeyDown.
                    #
                    # That said, we should never be hitting this code path on
                    # a wake up because we're assuming a wake up will look like
                    # no buttons have changed state.
                    ms =0
                    if self._model[i].timestamp > 0 and (self._model[i].position != obj.position) :
                        ms = rpt.timestamp - self._model[i].timestamp
                    obj.duration_ms = ms

                changedButtons.append(obj)


        # Summarize results
        hwEvent = HardwareEvent(rpt.timestamp, rpt.eventType, rpt.value,
                                    rpt.changeMask, rpt.changeCount, changedButtons)
    
        self._buffer.append(rpt)
        return hwEvent

    def _repaintButton(self, index: int, state: int) -> None:
        """Stub: repaint the button at the given index to reflect the given state.
        """
        pass

__all__ = ["Driver"]
