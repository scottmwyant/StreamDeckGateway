#!/usr/bin/env python3
"""StreamDeck state model and HID input report handling.

This module models the StreamDeck button state using a 16-bit unsigned
integer (bits 0-14 correspond to buttons 0..14). It parses HID input
reports (512 bytes, payload at offsets 0x04..0x12) where each payload
byte is 0x00 for UP and 0x01 for DOWN.
"""

from typing import List, Dict, Tuple


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
        self._value: int = 0


    def handle_hid_input_report(self, report: bytes) -> Dict:
        """Parse a 512-byte HID input `report` and return a summary of changes.

        The report is always 512 bytes. Layout:
        - header: bytes 0..3
          - [0] Report ID
          - [1] Command
          - [2:4] UINT16 little-endian: number of meaningful bits in payload
        - payload: bytes 4..511

        The payload can be provided either as one byte per button (0x00/0x01)
        or as a packed bit field. We use the header's meaningful-bit count to
        determine how many bits to consider and support both formats.

        Returns a dict with keys: previous, current, changed_mask, changed_count,
        changed_buttons (list of (index, is_down)).
        """
        print("Handling HID input report...")
        if not isinstance(report, (bytes, bytearray)):
            raise TypeError("report must be bytes or bytearray")

        if len(report) != 512:
            raise ValueError("report must be exactly 512 bytes")

        # number of meaningful bytes in the payload (little-endian uint16)
        header = report[0:4]
        size = int.from_bytes(header[2:4], "little")

        # We expect size to be tied to hardware, so it will always be 15. 

        print("Size: ", size)
        payload = report[4:(4+size)]

        newValue = 0
        i = 0
        for b in payload:
            bit = 1 if b > 0 else 0 
            newValue = newValue | (bit << i)
            i += 1
        print("New Value: ", newValue)

if __name__ == "__main__":
    sd = Streamdeck()

    # Build a 512-byte report: header (4 bytes) + 15-byte button payload + padding
    header = [0x01, 0x00, 0x0f, 0x00]
    payload = [0x00] * 508
    report = bytearray(header + payload)

    # Simulate: button 0 pressed
    report[4] = 0x01
    sd.handle_hid_input_report(bytes(report))

    # Simulate: button 0 released, button 3 pressed
    report[4] = 0x00
    report[7] = 0x01
    sd.handle_hid_input_report(bytes(report))
