# Copilot / AI Agent Instructions for this repository

This project is going to explore using modern Python3 running on a Raspberry Pi Zero 2 W, running Raspberry Pi OS Lite (32-bit), to capture hardware events from a Streamdeck Mk.2 (via USB) and relay appropriate detail to an MQTT broker.

## Getting started

I have successfully setup a Proof-of-Concept (PoC) seperately.  I now want to focus on building out the python code that will model and manage state of the device.

I want to model button state as an 16-bit unsigned integer.  The most significant bit will always be 0 since there are only 15 buttons. The least significant bit will represent button 0, the next bit button 1, and so on up to bit 14 representing button 14.

When an HID input report is received, I want to compare the new button state to the previous button state, and to know how many buttons changed state, which buttons changed state, and the new state of the changed buttons.

### StreamDeck Mk.2 Overview

- 3x5 button grid, top left is button 0, bottom right is button 14
- Vendor Id: 0x0fd9
- Product ID: 0x0080

### HID Input Reports

The primary way python will interact with the StreamDeck is via HID Input reports.  These are binary blobs of data that are sent from the device to the host to report hardware state.

There is only 1 input reporty, it's always going to be 512-bytes long and the first 4 bytes are a header.

- 0x00: UINT8, Report ID (0x01)
- 0x01: UINT8, Command
- 0x02 and 0x03: UINT16 payload length in bytes

The message payload starts at 0x04 and is the remainder of the message.  Given the assumptions about the device we're using, we can focus on byets 0x04 through 0x12 (15 bytes), which reflect button state.

The device sends an output report when at least 1 button changes state KeyDown or KeyUp. The value of these 15 bytes corresponds to state of the button; value of 0x00 indicates the button is UP, value of 0x01 indicates the button is DOWN.

For now we assume when the device is powered on, all buttons are UP, that behavior will have to be tested.

## Resources

- The official documentation for the StreamDeck HID protocol is available at https://docs.elgato.com/streamdeck/hid/.

- The `pyhidapi` library will be used to interface with the StreamDeck device. This is a Python wrapper around the HIDAPI C library, which provides a way to communicate with USB and Bluetooth HID devices. The HIDAPI library has two possible backends on Linux: libusb and hidraw. This project will use the hidraw backend.

- The `paho-mqtt` library will be used to handle MQTT communication.

