using App;

using HidSharp;



HidDevice[] deviceList = DeviceList.Local.GetHidDevices().ToArray();
Console.WriteLine($"Count of devices: {deviceList.Length}");
foreach (var device in deviceList)
{
    Console.WriteLine($"Device: VID: {device.VendorID:X4}, PID: {device.ProductID:X4}");
}

Console.WriteLine("Exit");


//var builder = Host.CreateApplicationBuilder(args);
//builder.Services.AddHostedService<Worker>();

//var host = builder.Build();
//host.Run();
