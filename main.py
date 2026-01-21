#!/usr/bin/env python3
"""StreamDeck state model and HID input report handling.

This module models the StreamDeck button state using a 16-bit unsigned
integer (bits 0..14 correspond to buttons 0..14). It parses HID input
reports (512 bytes, 15-byte payload starting at offsets 0x04) where each
payload byte is 0x00 for UP and 0x01 for DOWN.
"""
import time
from typing import List, Dict, Tuple

BUTTON_COUNT = 15

class Streamdeck:
    """
    Models the state of a StreamDeck device using a 16-bit unsigned int.

    Bit mapping:
    - Bit 0: button 0 (top-left)
    - Bit 14: button 14 (bottom-right)
    - Bit 15: unused (always 0)
    """

    def __init__(self) -> None:
        # start with all buttons released
        self._value = 0
        # start with all "switches" being off
        self._on = 0
        # per-button last event timestamps (unix ms). 0 == no events yet
        self._last_event: List[int] = [0] * 15

    def handle_hid_input_report(self, report: bytes) -> Dict:
        """Parse a 512-byte HID input `report` and return a summary of changes.

        The report is always 512 bytes. Layout:
        - header: bytes 0..3
          - [0] Report ID
          - [1] Command
          - [2:4] UINT16 little-endian: number of meaningful BYTES in payload
        - payload: bytes 4..511

        For this project the device sends one payload byte per button (15
        bytes). Each payload byte is 0x00 for UP or 0x01 for DOWN. We map the
        first 15 payload bytes to bits 0..14 and compute the changed buttons.

        Returns a dict with keys: previous, current, changed_mask, changed_count,
        changed_buttons (list of (index, is_down)).
        """
        if not isinstance(report, (bytes, bytearray)):
            raise TypeError("report must be bytes or bytearray")

        if len(report) != 512:
            raise ValueError("report must be exactly 512 bytes")

        header = report[0:4]
        size_bytes = int.from_bytes(header[2:4], "little")


        # Map first 15 payload bytes (one byte per button) into bits
        payload = report[4:4 + size_bytes]
        new_value = 0
        for i in range(len(payload)):
            bit = 0 if payload[i] == 0 else 1
            new_value |= (bit << i)

        previous = self._value
        changed_mask = previous ^ new_value
        changed_count = changed_mask.bit_count()

        now_ms = int(time.time() * 1000)
        changed_buttons: List[Dict[str, Optional[int]]] = []
        for i in range(BUTTON_COUNT):
            if (changed_mask >> i) & 1:
                is_down = bool((new_value >> i) & 1)
                last_ts = self._last_event[i]
                duration_ms: Optional[int]
                if last_ts > 0:
                    duration_ms = now_ms - last_ts
                else:
                    duration_ms = None

                # record the change with timing info, then update timestamp
                changed_buttons.append({
                    "index": i,
                    "is_down": is_down,
                    "last_ts": last_ts,
                    "duration_ms": duration_ms,
                })

                # update last event timestamp to now
                self._last_event[i] = now_ms

        # update internal state
        self._value = new_value

        result = {
            "timestamp": now_ms,
            "previous": previous,
            "current": new_value,
            "changed_mask": changed_mask,
            "changed_count": changed_count,
            "changed_buttons": changed_buttons,
        }

        print(result)
        return result

def run():
    sd = Streamdeck()

    # Build a 512-byte report: header (4 bytes) + 15-byte button payload + padding
    header = [0x01, 0x00, 0x0f, 0x00]
    payload = [0x00] * 508
    report = bytearray(header + payload)

    # Simulate: button 0 pressed
    report[4] = 0x01
    sd.handle_hid_input_report(bytes(report))

    time.sleep(1.5)  # wait 100ms

    # Simulate: button 0 released, button 3 pressed
    report[4] = 0x00
    report[7] = 0x01
    sd.handle_hid_input_report(bytes(report))

if __name__ == "__main__":
    run()