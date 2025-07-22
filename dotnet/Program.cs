﻿using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Hosting;
using System.Reflection;
using System;
using System.Threading.Tasks;

public static class Program
{
    // We keep the host so the background task can reach the DI container
    private static IHost? _appHost;

    public static async Task Main(string[] args)
    {
        // build the host first.
        var builder = Host.CreateDefaultBuilder(args)
            .ConfigureLogging(b =>
            {
                b.ClearProviders();
                b.AddSimpleConsole(o =>
                {
                    o.SingleLine = true;
                    o.TimestampFormat = "HH:mm:ss ";
                    o.IncludeScopes = false;
                });
                b.SetMinimumLevel(LogLevel.Warning);
            })
            .ConfigureServices(services =>
            {
                services.AddSingleton<IMessageHandler, PulseProcessor>();
                services.AddHostedService<SocketServer>();
                services.AddSingleton<DistanceState>();
                services.AddControllers().AddApplicationPart(Assembly.GetExecutingAssembly());
            })
            .ConfigureWebHost(web =>
            {
                web.UseWebRoot("wwwroot");
                web.UseUrls("http://*:5000");
                web.UseKestrel();
                web.Configure(app =>
                {
                    app.UseDefaultFiles();
                    app.UseStaticFiles();
                    app.UseRouting();
                    app.UseEndpoints(endpoint =>
                    {
                        endpoint.MapControllers();
                    });

                });
            });

        _appHost = builder.Build();

        // heartbeat + OFF-checker task.
        _ = Task.Run(async () =>
        {
            // Resolve the PulseProcessor singleton from DI.
            var pulse = (PulseProcessor)_appHost.Services
                                               .GetRequiredService<IMessageHandler>();

            int tick = 0;
            while (true)
            {
                await Task.Delay(1000);              // 1-second tick

                // every 3rd tick (≈3 s) send PING
                if (++tick % 3 == 0)
                {
                    Console.WriteLine("[Heartbeat] Sending PING");
                    string host = PicoEndpoint.CurrentIp ?? "192.168.10.223";
                    await SocketClient.Send("PING", host);   // errors swallowed
                }

                // let PulseProcessor decide whether to send OFF
                await pulse.TickAsync();
            }
        });

        // run the host (graceful Ctrl-C shutdown).
        await _appHost.RunAsync();
    }
}
