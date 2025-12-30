namespace App
{
    using HidSharp;

    public class Worker(ILogger<Worker> logger) : BackgroundService
    {
        private const int StreamDeckVid = 0x0fd9;
        private const int StreamDeckPid = 0x0080;
        private const int MonitoringIntervalMs = 1000;

        protected override async Task ExecuteAsync(CancellationToken stoppingToken)
        {
            logger.LogInformation("StreamDeck service starting...");

            HidDevice? streamDeckDevice = null;

            try
            {
                while (!stoppingToken.IsCancellationRequested)
                {
                    // Discover StreamDeck device
                    streamDeckDevice = DiscoverStreamDeckDevice();

                    if (streamDeckDevice == null)
                    {
                        if (logger.IsEnabled(LogLevel.Warning))
                        {
                            logger.LogWarning("StreamDeck device not found (VID: {vid:X4}, PID: {pid:X4})", StreamDeckVid, StreamDeckPid);
                        }
                        await Task.Delay(MonitoringIntervalMs, stoppingToken);
                        continue;
                    }

                    if (logger.IsEnabled(LogLevel.Information))
                    {
                        logger.LogInformation("StreamDeck device discovered: {path}", streamDeckDevice.DevicePath);
                    }

                    // Open device and read button presses
                    await MonitorDeviceAsync(streamDeckDevice, stoppingToken);
                }
            }
            catch (OperationCanceledException)
            {
                logger.LogInformation("StreamDeck service cancellation requested.");
            }
            catch (Exception ex)
            {
                logger.LogError(ex, "Unexpected error in StreamDeck service");
            }
            finally
            {
                logger.LogInformation("StreamDeck service stopping...");
            }
        }

        private HidDevice? DiscoverStreamDeckDevice()
        {
            try
            {
                return DeviceList.Local
                    .GetHidDevices()
                    .FirstOrDefault(d => d.VendorID == StreamDeckVid && d.ProductID == StreamDeckPid);
            }
            catch (Exception ex)
            {
                logger.LogError(ex, "Error discovering devices");
                return null;
            }
        }

        private async Task MonitorDeviceAsync(HidDevice device, CancellationToken stoppingToken)
        {
            HidStream? stream = null;

            try
            {
                if (!device.TryOpen(out stream))
                {
                    logger.LogError("Failed to open StreamDeck device");
                    return;
                }

                logger.LogInformation("StreamDeck device opened successfully");

                while (!stoppingToken.IsCancellationRequested)
                {
                    byte[] buffer = new byte[16];

                    // ReadTimeout of 0 means non-blocking; positive values block until data arrives
                    int bytesRead = stream.Read(buffer);

                    if (bytesRead > 0)
                    {
                        if (logger.IsEnabled(LogLevel.Information))
                        {
                            logger.LogInformation("Button press detected: {bytes} bytes", bytesRead);
                        }
                    }

                    await Task.Delay(100, stoppingToken);
                }
            }
            catch (Exception ex)
            {
                logger.LogError(ex, "Error monitoring device");
            }
            finally
            {
                stream?.Dispose();
            }
        }
    }
}
