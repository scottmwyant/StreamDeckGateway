---
applyTo: "**/src/App"
---

# StreamDeck Service - AI Development Guidelines

## Project Objective
Build a .NET 10 service that communicates with a StreamDeck device to receive and log button presses.

## Tech Stack & Constraints
- **.NET 10.0** (Microsoft.NET.Sdk.Worker)
- **HidSharp 2.6.4** for hardware communication
- **Microsoft.Extensions.Hosting** for service hosting
- StreamDeck VID: `0x0fd9`, PID: `0x0080`
- Nullable reference types enabled (`<Nullable>enable</Nullable>`)
- Implicit usings enabled

## Architecture & Key Components

### Project Structure
- `src/App/Program.cs` - Application entry point; currently demonstrates device enumeration via HidSharp
- `src/App/Worker.cs` - BackgroundService implementation (template for long-running task)
- `src/App/appsettings.json` - Logging configuration (default: Information level)

### Development Pattern
The project uses a **Worker Service pattern** (IHostedService/BackgroundService). When activating the Worker:
1. Uncomment the builder code in Program.cs
2. Implement `ExecuteAsync()` in Worker.cs for continuous device monitoring
3. Use dependency injection for logger: `Worker(ILogger<Worker> logger)`

### HidSharp Integration
- Enumerate devices: `DeviceList.Local.GetHidDevices()` returns all HID devices
- Filter by VID/PID: Check `device.VendorID` and `device.ProductID` before opening streams
- Device I/O: Use `device.Open()` for read/write access (blocking streams)

## Build & Run Commands
- **Build**: `dotnet build src/App/App.csproj`
- **Run with watch**: `dotnet watch run --project src/App/App.csproj`
- **Debug**: Press F5 (preLaunchTask runs build automatically)
- **Publish**: `dotnet publish src/App/App.csproj`

## Key Implementation Patterns
1. **Logging**: Use injected `ILogger<T>` with `logger.IsEnabled(LogLevel.Information)` guards before logging
2. **Cancellation**: Honor `CancellationToken` in async loops to enable graceful shutdown
3. **Console Output**: Current Program.cs demonstrates simple Console.WriteLine for device discovery
4. **Configuration**: Leverage appsettings.json + IConfiguration for logging levels (avoid hardcoding)

## Common Workflows
- **Discover devices**: Use Program.cs pattern to enumerate and display VID/PID
- **Monitor button presses**: Implement read loop in Worker.ExecuteAsync with HidSharp streams
- **Handle disconnection**: Wrap device operations in try-catch; re-enumerate on device removal