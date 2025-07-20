using System;
using System.IO;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using Microsoft.Extensions.Hosting;

public interface IMessageHandler
{
    Task HandleLineAsync(string line);
}

/// <summary>
/// Line-oriented TCP server (ASCII + LF).  
/// Learns the Pico’s IP as soon as it connects.
/// </summary>
public sealed class SocketServer : BackgroundService
{
    private readonly IPAddress _listenAddr = IPAddress.Any;
    private const int Port = 4321;
    private readonly IMessageHandler _handler;

    public SocketServer(IMessageHandler handler) => _handler = handler;

    protected override async Task ExecuteAsync(CancellationToken stop)
    {
        var listener = new TcpListener(_listenAddr, Port);
        listener.Server.SetSocketOption(SocketOptionLevel.Socket,
                                        SocketOptionName.ReuseAddress, true);
        listener.Start();

        Console.WriteLine($"[SocketServer] Listening on 0.0.0.0:{Port}");

        try
        {
            while (!stop.IsCancellationRequested)
            {
#if NET7_0_OR_GREATER
                var tcpClient = await listener.AcceptTcpClientAsync(stop);
#else
                var acceptTask = listener.AcceptTcpClientAsync();
                var completed  = await Task.WhenAny(acceptTask,
                                                    Task.Delay(Timeout.Infinite, stop));
                if (completed != acceptTask) break;
                var tcpClient = acceptTask.Result;
#endif
                _ = HandleClientAsync(tcpClient, stop);   // fire-and-forget
            }
        }
        finally
        {
            listener.Stop();
            Console.WriteLine("[SocketServer] Listener stopped.");
        }
    }

    private async Task HandleClientAsync(TcpClient client, CancellationToken stop)
    {
        // ── learn & cache Pico’s IP ─────────────────────────────────
        var remoteIp = ((IPEndPoint)client.Client.RemoteEndPoint!).Address.ToString();
        PicoEndpoint.CurrentIp = remoteIp;
        Console.WriteLine($"[SocketServer] Pico at {remoteIp}");
        // ────────────────────────────────────────────────────────────

        Console.WriteLine("[SocketServer] Client connected.");

        client.Client.SetSocketOption(SocketOptionLevel.Socket,
                                      SocketOptionName.KeepAlive, true);
        client.Client.LingerState = new LingerOption(true, 0);

        await using var stream = client.GetStream();
        using var reader = new StreamReader(stream, Encoding.ASCII);

        try
        {
            while (!stop.IsCancellationRequested && !reader.EndOfStream)
            {
                string? line = await reader.ReadLineAsync();
                if (!string.IsNullOrWhiteSpace(line))
                    await _handler.HandleLineAsync(line);
            }
        }
        catch (IOException ex)
        {
            Console.WriteLine($"[SocketServer] I/O error: {ex.Message}");
        }
        finally
        {
            client.Close();
            Console.WriteLine("[SocketServer] Client closed.");
        }
    }
}
