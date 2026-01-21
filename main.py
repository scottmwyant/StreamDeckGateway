
class Streamdeck(object):
"""
    Models the state of the Streamdeck device.
"""
    def __init__(self):
        
        # Initialize internal state
        # Use a 16-bit uint value to represents state of the buttons, it
        # starts at 0 (all buttons released).
        self._value = 0

    def handle_hidInputReport(report):
        """
        Handle HID input report.

        Args:
            report (bytes): The HID input report data, assumed 512 bytes in length.
        """
        # When input is received, map the 15 byte payload to bits, compare the to
        # the internal state (self._value), to know how many buttons changed state
        # between this report and the last one.


if __name__ == "__main__":
    # Simulated 512-byte HID input report that says button-0 is pressed.
    header = [0x01, 0x00, 0x0f, 0x00]
    payload = [0x01] + ([0x00] * 507)
    handle_hidInputReport(bytes(header + payload))