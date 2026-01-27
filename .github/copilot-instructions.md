# Copilot / AI Agent Instructions for this repository

This is a home automation / IoT project that involves a Raspberry Pi and a Stream Deck.

## Raspberry Pi

Details on the compute hardware we'll be using:

- [Raspberry Pi Zero 2 W](https://www.raspberrypi.com/products/raspberry-pi-zero-2-w/)
- 32GB micro SD card
- Raspberry Pi OS Lite (32-bit) -- A port of Debian Trixie.
- Python v3.13.5, this version of Python is included with the OS.


## Stream Deck

Details on the Stream Deck input device:

- [Stream Deck Mk.2](https://www.elgato.com/us/en/p/stream-deck)
- 3x5 button grid, top left = 0, bottom right = 14
- Vendor Id: `0x0fd9`
- Product Id: `0x0080`
- Functions as a human input device (HID), the custom protocol is well documented and available here: https://docs.elgato.com/streamdeck/hid/.

## Software stack

An overview of the software used at runtime.

### pyhidapi

This is a tiny python library that wraps the HIDAPI which is written in C.  Note the name of the GitHub project is `pyhidapi` and the package is listed on pypi.org under a different name, simply `hid`.

The OS we're using won't allow you to install python modules globally without a few extra hoops and suggests that you install global package using `sudo apt install -y python3-hid`.  Unfortunately, this is a valid command but it installs another library entirely (https://github.com/trezor/cython-hidapi).

- https://github.com/apmorton/pyhidapi

### hidapi

This is the library that `pyhidapi` wraps.  There are two different versions of this library on Linux systems, using different backends (`hidraw` or `libusb`).  We're using `libhidapi-hidraw.so.0`.  

- https://github.com/libusb/hidapi
- `/lib/arm-linux-gnueabihf/libhidapi-hidraw.so.0`

### hidraw

This gets down to the Linux kernel level.  Seems to be the preferred way to interact with HID.

## Application architecture

There are 3 core responsibilities:

1. Ingress - Interact with HID
2. Egress - Interact with the network side (assume MQTT).
3. Orchestration of the other two components, this will be the main thread of the app.

We will use the producer/consumer pattern extensively.  The main thread will instantiate two queues, one for messages sent to the HID thread, one for receiving messages from the HID thread.  We'll think of these objects from the perspective of the main thread:

- `rx` => HID thread puts messages in here, the main thread pulls them out.
- `tx` => main thread puts messages here, HID thread pulls them out

### HID Input Reports

The primary way python will interact with the StreamDeck is via HID Input reports.  These are binary blobs of data that are sent from the device to the host to report hardware state.

There is only 1 input report, it's always going to be 512-bytes long and the first 4 bytes are a header.

- 0x00: UINT8, Report ID (0x01)
- 0x01: UINT8, Command
- 0x02 and 0x03: UINT16 payload length in bytes

The message payload starts at 0x04 and is the remainder of the message.  Given the assumptions about the device we're using, we can focus on byets 0x04 through 0x12 (15 bytes), which reflect button state.

The device sends an output report when at least 1 button changes state KeyDown or KeyUp. The value of these 15 bytes corresponds to state of the button; value of 0x00 indicates the button is UP, value of 0x01 indicates the button is DOWN.

For now we assume when the device is powered on, all buttons are UP, that behavior will have to be tested.

## Code Style Guidelines

- Prefer `camelCase` over `snake_case`.