using HidSharp;

namespace App;

public class Worker(ILogger<Worker> logger) : BackgroundService
{
    private const int StreamDeckVid = 0x0fd9;
    private const int StreamDeckPid = 0x0080;
    private const int MonitoringIntervalMs = 5000;

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
                    logger.LogWarning("Device not found (VID: {vid:X4}, PID: {pid:X4})", StreamDeckVid, StreamDeckPid);
                    await Task.Delay(MonitoringIntervalMs, stoppingToken);
                    continue;
                }
                else
                {
                    logger.LogInformation("Discovered: {model} {serial}", streamDeckDevice.GetProductName(), streamDeckDevice.GetSerialNumber());
                    await MonitorDeviceAsync(streamDeckDevice, stoppingToken);
                }
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
                logger.LogError("Failed to open a connection to StreamDeck device");
                return;
            }
            else
            {
                logger.LogInformation("StreamDeck device opened successfully");
            }

            while (!stoppingToken.IsCancellationRequested)
            {
                stream.ReadTimeout = 5000;
                byte[] buffer = new byte[1024];
                try
                {
                    int length = await stream.ReadAsync(buffer, stoppingToken);
                    logger.LogInformation("Count of bytes read:{n}", length);
                    await Task.Delay(100, stoppingToken);
                }
                catch (TimeoutException)
                {
                    logger.LogDebug("Read operation timed out.");
                }
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
