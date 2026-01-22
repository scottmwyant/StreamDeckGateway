# Streamdeck

This project captures events from a Streamdeck Mk.2 (VID = 0xfd9, PID = 0x0080) and relays events to an MQTT broker.

## Filtering logic
----------------------
| Hardware Events    |
----------------------
|  
|  The hardware reports the aggregate state of all buttons when ever the state of one or more buttons changes.
|  At this level "state" is referring to the position of the button, either UP or DOWN.
|
----------------------
| Ignore KeyDown     |
----------------------
|
|  We want to build in capability to detect short vs long press, so KeyDown is meaningless by itself,
|  it needs to be paired with a KeyUp to know the duration of the press.
|
|
----------------------
| Ignore Wake-Up     |
----------------------
|
|  When the hardware is in sleep, the first KeyDown event wakes it up, so the input report will be a KeyUp
|  although the previous state would be all keys up, you don't see the KeyDown event that triggers wake up.
|
----------------------
| Switch Position    |
----------------------
|
|  Need to track if each button is ON or OFF, to make it act like a SPST switch.
|
----------------------
| Remove duplicates   |
----------------------
|
|  There should not be a scenario where a button that's ON reports again that it's ON.  We should onl
|  report state changes of the switch.
|