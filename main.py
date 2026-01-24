#!/usr/bin/env python3
"""StreamDeck state model and HID input report handling.

This module models the StreamDeck button state using a 16-bit unsigned
integer (bits 0..14 correspond to buttons 0..14). It parses HID input
reports (512 bytes, 15-byte payload starting at offsets 0x04) where each
payload byte is 0x00 for UP and 0x01 for DOWN.
"""
import time
import json
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
# import paho.mqtt.client as mqtt

BUTTON_COUNT = 15

@dataclass
class Button:
    state: int = 0
    timestamp: int = 0
    position: int = 0

class EventType(Enum):
    KEY_UP = 0
    KEY_DOWN = 1
    KEY_UP_DOWN = 2
    WAKE_UP = 3
    NO_CHANGE = 4

@dataclass
class InputReport:
    """Represents a parsed HID input report."""
    
    reportId: int
    command: int
    length: int
    value: int
    timestamp: int = field(default_factory=lambda: int(time.time() * 1000))
    countKeysDown: int = field(init=False)
    countKeysUp: int = field(init=False)
    
    # Attributes to be set externally after comparison to previous report
    changedMask: int | None = None
    changedCount: int | None = None
    eventType: int | None = None

    def __post_init__(self):
        self.countKeysDown = self.value.bit_count()
        self.countKeysUp = BUTTON_COUNT - self.countKeysDown

    @classmethod
    def from_bytes(cls, report: bytes) -> "InputReport":
        """Parse a 512-byte HID report into an InputReport instance."""
        
        if len(report) != 512:
            raise ValueError("report must be exactly 512 bytes")

        report_id = report[0]
        command = report[1]
        length = int.from_bytes(report[2:4], "little")

        if length != BUTTON_COUNT:
            raise ValueError(f"unexpected payload length: {length}")

        payload = report[4:4 + length]

        # Build bit-packed integer where LSB = button 0
        value = 0
        for i, b in enumerate(payload):
            bit = int(bool(b))
            value |= bit << i

        return cls(
            reportId=reportId,
            command=command,
            length=length,
            value=value
        )

    def hasButtonChanged(self, index: int) -> bool:
        """Check if a button has changed state since the previous report."""
        if self.changedMask is None:
            raise ValueError("changedMask is not set")
        if not 0 <= index < BUTTON_COUNT:
            raise ValueError(f"index must be in range 0..{BUTTON_COUNT-1}")
        return bool((self.changedMask >> index) & 1)

    def isButtonDown(self, index: int) -> bool:
        """Check if a button is currently down."""
        if not 0 <= index < BUTTON_COUNT:
            raise ValueError(f"index must be in range 0..{BUTTON_COUNT-1}")
        return bool((self.value >> index) & 1)

class Streamdeck:

    def __init__(self) -> None:
        # Initialize with a report indicating all buttons up
        header = [0x01, 0x00, 0x0f, 0x00]
        payload = [0x00] * 508
        self._buffer = [InputReport(bytes(header + payload))]
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
    
        return None
    
    def handle_hid_input_report(self, report) -> Dict:
        hwEvent = self._computeChanges(report)
        eventData = None
        if hwEvent["changeCount"] > 0:
            eventData = self._updateModel(hwEvent)

        # Construct a payload that contains
        #  - Manufacturer
        #  - Model
        #  - Serial number
        #  - Firmware version
        #  - Button states
        if eventData is not None:
            print(eventData)
            res = self._sendEventData(eventData)
            self._showResult(res)

    def _sendEventData(self, payload: Dict) -> Tuple[int, str]:
        """Stub for sending event data to another system.
        """
        return 200, "OK"
    
    def _sendEventData_MQTT(self, payload: Dict) -> Tuple[int, str]:
        """Send the event data to MQTT broker.
        
        Connects to the MQTT broker, publishes the event, and disconnects.
        Since events are infrequent, a new connection is created per event.
        
        Args:
            payload: Dictionary containing event data to publish
            
        Returns:
            Tuple of (status_code, message)
        """
        try:
            # MQTT configuration
            broker = "localhost"
            port = 1883
            topic = "streamdeck/events"
            
            # Create MQTT client and set up callbacks
            client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
            
            def on_connect(client, userdata, flags, rc):
                if rc != 0:
                    raise mqtt.MQTTException(f"Connection failed with code {rc}")
            
            def on_publish(client, userdata, mid):
                pass
            
            def on_disconnect(client, userdata, rc):
                pass
            
            client.on_connect = on_connect
            client.on_publish = on_publish
            client.on_disconnect = on_disconnect
            
            # Connect to broker
            client.connect(broker, port, keepalive=5)
            
            # Publish the event data as JSON
            message = json.dumps(payload)
            result = client.publish(topic, message, qos=1)
            
            # Wait for publish to complete
            client.loop(timeout=1.0)
            
            # Disconnect
            client.disconnect()
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                return 200, "Event published successfully"
            else:
                return 400, f"Failed to publish: {mqtt.error_string(result.rc)}"
                
        except Exception as e:
            return 500, f"MQTT error: {str(e)}"

    def _showResult(self, res: str) -> None:
        """Stub: show the result of sending event data.
        """
        print(f"Result: {res}")

    def _updateModel(self, hwEvent: Dict) -> Dict:
        """Update the internal model based on the changes detected
        in the input report.  Returns event data for further processing.
        """

        # This is where we translate hardware events to logical events
        # Button profile should be considered, e.g. momentary vs toggle vs double-toggle
        # Consider a long-press could communicate higher urgency.

        # The question is where do we set the threshold for long press?
        # Do we send the duration out to the higher level system?
        # Seems config file would be apporpriate, so different systems do not
        # have the opportunity to disagree on what a long-press is.
        # Keeping the logic local also enables immidiate feedback.
        #
        # Next question is what semantics do we send?
        # Maybe send an array of integer values (0,1,2).

        stateChange = False
        for btn in hwEvent["detail"]:
            index = btn["index"]
            position = btn["position"]
            duration_ms = btn.get("duration_ms") 
            self._model[index]["timestamp"] = hwEvent["timestamp"]
            self._model[index]["position"] = position

            if position == 0:
                stateChange = True
                level = 1 if duration_ms < 1000 else 2
                self._model[index]["state"] = level if self._model[index]["state"] == 0 else 0
                self._repaintButton(index, self._model[index]["state"])
        return [x["state"] for x in self._model] if stateChange else None

    def _computeChanges(self, report) -> Dict:
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

        rpt.changedMask = self._buffer[-1].value ^ rpt.value
        rpt.changedCount = rpt.changedMask.bit_count()
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

        changedButtons: List[Dict[str, Optional[int]]] = []

        # Iterate over the report payload (each button)
        # Get the profile for the button and call the appropriate handler.
        # 
        # 
        # , compare to previous reports.
        # May require cyclying back through multiple reports to find the last event
        # for the given button.
        for i in range(BUTTON_COUNT):
            if rpt.hasButtonChanged(i):
                obj = {"index": i, "position": int(rpt.isButtonDown(i))}                
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
                    obj["duration_ms"] = ms


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
                    if self._model[i]["timestamp"] > 0 and (self._model[i]["position"] != obj["position"]) :
                        ms = rpt.timestamp - self._model[i]["timestamp"]
                    obj["duration_ms"] = ms

                changedButtons.append(obj)


        # Summarize results
        result = {
            "timestamp": rpt.timestamp,
            "eventType": rpt.eventType,
            "value": rpt.value,
            "changeMask": rpt.changedMask,
            "changeCount": rpt.changedCount,
            "detail": changedButtons,
        }
        self._buffer.append(rpt)
        print(result)
        return result

    def _repaintButton(self, index: int, state: int) -> None:
        """Stub: repaint the button at the given index to reflect the given state.
        """
        pass

def run():
    sd = Streamdeck()

    # Build a 512-byte report: header (4 bytes) + 15-byte button payload + padding
    header = [0x01, 0x00, 0x0f, 0x00]
    payload = [0x00] * 508
    report = bytearray(header + payload)

    # Simulate: button 0 pressed
    report[4] = 0x01
    rpt = InputReport(bytes(report))
    sd.handle_hid_input_report(rpt)

    time.sleep(1.5)
    # Simulate: button 0 released, button 3 pressed
    report[4] = 0x00
    report[7] = 0x01
    rpt = InputReport(bytes(report))
    sd.handle_hid_input_report(rpt)

    time.sleep(0.5) 
    # Simulate button 3 released quickly
    report[7] = 0x00
    rpt = InputReport(bytes(report))
    sd.handle_hid_input_report(rpt)

if __name__ == "__main__":
    run()