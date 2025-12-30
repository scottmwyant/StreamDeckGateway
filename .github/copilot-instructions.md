---
applyTo: "**/src/App"
---

# StreamDeck Gateway - AI Development Guidelines

## Long-term Vision

Enable the Elgato Stream Deck MK.2 (model number 20GBA9901) to be used with a raspberry pi as a hardware controller for home automation.  Expose button press events to IoT platforms such as Home Assistant via MQTT.

## Short-term objectives (immidiate priority)

- Focus on building a robust framework for service lifetime, with basic error handling and logging capabilities.
- Establish reliable communication with the Stream Deck device using HidSharp.
- Gracefully handle device connection and disconnection events.
- Implement a background service that continuously monitors button presses.
- Ignore the egress side of the gateway for now (i.e., do not implement any MQTT capability yet, only listen for button presses).
- Images and labels on the buttons will be static and pre-configured; no need to implement dynamic image updates at this time; keep focus on listening for events.s

## Tech Stack & Constraints
- Implement the project using **.NET 10.0**.
- Use **HidSharp 2.6.4** for hardware communication.
- Use Generic Host pattern for service hosting, logging, and dependency injection.
- Assume the Stream Deck MK.2 device specifics: VID: `0x0fd9`, PID: `0x0080`.
- Assume the hardware running the application will only ever have either zero or one Stream Deck connected at a time.
- The Stream Deck may be connected or disconnected at any time; while the application is running.

## Architecture & Key Components
- There are two environments: Development (local machine) and Production (Raspberry Pi).


### Project Structure
- `src/App/Program.cs` - Application entry point; currently demonstrates device enumeration via HidSharp
- `src/App/Worker.cs` - BackgroundService implementation (template for long-running task)
- `src/App/appsettings.json` - Logging configuration (default: Information level)

3. Use dependency injection for logger: `Worker(ILogger<Worker> logger)`

### HidSharp Integration
- Enumerate devices: `DeviceList.Local.GetHidDevices()` returns all HID devices
- Filter by VID/PID: Check `device.VendorID` and `device.ProductID` before opening streams
- Device I/O: Use `device.Open()` for read/write access (blocking streams)
