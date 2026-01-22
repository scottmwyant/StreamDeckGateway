#!/usr/bin/env python3
"""StreamDeck state model and HID input report handling.

This module models the StreamDeck button state using a 16-bit unsigned
integer (bits 0..14 correspond to buttons 0..14). It parses HID input
reports (512 bytes, 15-byte payload starting at offsets 0x04) where each
payload byte is 0x00 for UP and 0x01 for DOWN.
"""
import time
from typing import List, Dict, Optional

BUTTON_COUNT = 15

class InputReport():
    """Represents a parsed HID input report.
    """

    def __init__(self, report: bytes) -> None:

        if not isinstance(report, (bytes, bytearray)):
            raise TypeError("report must be bytes or bytearray")

        if len(report) != 512:
            raise ValueError("report must be exactly 512 bytes")
        
        # filled in later, need to compare to previous report
        self.changedMask: int = None
        self.changedCount: int = 0
        self.eventType: int = None
        # timestamp in unix ms
        self.timestamp = int(time.time() * 1000)
        # header fields
        self.report_id = report[0]
        self.command = report[1]
        self.length = int.from_bytes(report[2:4], "little")
        # there should be exactly 1 byte in the payload per button
        if self.length != BUTTON_COUNT:
            raise ValueError(f"unexpected payload length: {self.length}")
        # extract the payload
        self.payload = report[4:4 + self.length]
        
        # Iterate over payload bytes to build a bit-packed
        # int value where LSB is button 0, MSB is button 14.
        self.value = 0
        for i in range(len(self.payload)):
            # coerce the byte to a bit 0x00 or 0x01
            bit = int(bool(self.payload[i]))
            # drop the bit into the correct position
            self.value |= (bit << i)
        
        #  number of buttons down == number of bits that are high
        self.countKeysDown = self.value.bit_count()
        self.countKeysUp = BUTTON_COUNT - self.countKeysDown

    def hasButtonChanged(self, index: int) -> bool:
        """Has the button at the given index has changed state
        since the previous report.
        """
        if self.changedMask is None:
            raise ValueError("changedMask is not set")
        
        if index < 0 or index >= BUTTON_COUNT:
            raise ValueError(f"index must be in range 0..{BUTTON_COUNT-1}")
        
        return bool((self.changedMask >> index) & 1)

    def isButtonDown(self, index: int) -> bool:
        """Is the button at the given index currently down.
        """
        if index < 0 or index >= BUTTON_COUNT:
            raise ValueError(f"index must be in range 0..{BUTTON_COUNT-1}")
        
        return bool((self.value >> index) & 1)

class InputReportBuffer():
    """
    Accumulates a collection of input reports so we can understand discrete state changes.
    Index 0 is the oldest report, index -1 is the most recent.
    """
    def __init__(self) -> None:
        self._buffer: List[InputReport] = []
        self._size = 20

    def add(self, report: InputReport) -> None:
        if len(self._buffer) >= self._size:
            self._buffer.pop(0)
        self._buffer.append(report)

    @property
    def size(self) -> int:
        return self._size
    
    def __len__(self) -> int:
        return len(self._buffer)
    
    def __getitem__(self, index: int) -> InputReport:
        """Access reports by index: 0 is oldest, -1 is newest."""
        return self._buffer[index]

class Streamdeck:

    def _seedInputReport(self) -> InputReport:
        header = [0x01, 0x00, 0x0f, 0x00]
        payload = [0x00] * 508
        return InputReport(bytearray(header + payload))

    def __init__(self) -> None:
        self._buffer = InputReportBuffer()
        # seed the buffer with an "all buttons up" report
        seedReport = self._seedInputReport()
        self._buffer.add(seedReport)
        # start with all buttons released
        self._value = 0

    def determineEventType(self, report: InputReport) -> int:
        """
        Compare the current report to the previous report to
        characterize the type of event.  Returns one of the following
        event type codes: 0=KeyUp, 1=KeyDown, 2=KeyUpDown,
        3=WakeUp, 4=NoChange.
        """

        # Compare to last report in buffer to determine event type
        if self._buffer[-1].value == report.value:
                return 3 if report.value == 0 else 4

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
            return 0  # KeyUp
        
        if isDown and not isUp:
            return 1  # KeyDown
        
        if isUp and isDown:
            return 2  # KeyUpDown
    
        return None
    
    def handle_hid_input_report(self, report) -> Dict:
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
        rpt.eventType = self.determineEventType(rpt)

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

        # Iterate over the report payload (each button), compare to previous reports.
        # May require cyclying back through multiple reports to find the last event
        # for the given button.
        for i in range(BUTTON_COUNT):
            btnProfile = self._getConfiguredProfile(i)
            if rpt.hasButtonChanged(i):
                
                if btnProfile == "default":
                    if rpt.isButtonDown(i):
                        self._fire(i)
                
                elif btnProfile == "double-action":
                    if not rpt.isButtonDown(i):
                        # Search the buffer for the most recent KeyUp event on this button
                        for x in range(len(self._buffer)):
                            e = self._buffer[-1 - x]
                            if e.isButtonDown(i):
                                    duration_ms = rpt.timestamp - e.timestamp
                                    if duration_ms < 1000:
                                        self._fire(i)
                                    else:
                                        self._fire(i, "long-press")
                                    break
                else:
                    pass


                


                # The _fire method is where we wire in action,
                # That could mean toggle internal state for switches then send a message over the network.
                # Will be interesting to see how that works out; do we pass in an action?
                

                
                # record the change with timing info, then update timestamp
                # toggle ON/OFF on key-up when duration < 1000ms
                if not is_down and duration_ms is not None and duration_ms < 1000:
                    # toggle bit
                    self._on ^= (1 << i)

                on_state = bool((self._on >> i) & 1)
                obj = {
                    "index": i,
                    "position": 1 if is_down else 0,
                    # "last_ts": last_ts,
                    "switch": 1 if on_state else 0,
                }
                if duration_ms is not None:
                    obj["duration_ms"] = duration_ms
                changedButtons.append(obj)

                # update last event timestamp to now
                self._lastEvent[i] = rpt.timestamp


        # Summarize results
        result = {
            "timestamp": rpt.timestamp,
            "eventType": rpt.eventType,
            "value_new": rpt.value,
            "changedMask": rpt.changedMask,
            "changedCount": rpt.changedCount,
            "changedButtons": changedButtons,
        }

        # update internal state
        self._lastReport = rpt

        print(result)
        return result

    def _getConfiguredProfile(self, index: int) -> str:
        """Stub: get the configured profile for the given button index.
        """
        return "double-action" if index == BUTTON_COUNT - 1 else "default"
    
    def _fire(self, index: int, modifier: Optional[str] = None) -> None:
        """Stub: fire the action for the given button index.
        """
        if modifier is None:
            print(f"Firing action for button {index}")
        elif modifier == "long-press":
            print(f"Firing action for button {index} with modifier {modifier}")
        else:
            raise ValueError(f"unknown action modifier: {modifier}")

def run():
    sd = Streamdeck()

    # Build a 512-byte report: header (4 bytes) + 15-byte button payload + padding
    header = [0x01, 0x00, 0x0f, 0x00]
    payload = [0x00] * 508
    report = bytearray(header + payload)

    # Simulate: button 0 pressed
    report[4] = 0x01
    rpt = InputReport(bytes(report))

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