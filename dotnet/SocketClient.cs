using System;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using System.Threading.Tasks;

public static class SocketClient
{
    private static TcpClient? _client;
    private static NetworkStream? _stream;
    private static readonly SemaphoreSlim Gate = new(1, 1);

    public static async Task<bool> Send(string cmd,
                                        string host,
                                        int    port = 1234)
    {
        await Gate.WaitAsync().ConfigureAwait(false);
        try
        {
            if (_client is null || !_client.Connected || _stream is null)
            {
                _client?.Dispose();
                _client = new TcpClient { NoDelay = true };

                var connect = _client.ConnectAsync(host, port);
                if (await Task.WhenAny(connect, Task.Delay(1000)) != connect)
                    throw new SocketException((int)SocketError.TimedOut);
                await connect;                       // propagate late errors

                _stream = _client.GetStream();
            }

            byte[] buf = Encoding.ASCII.GetBytes(cmd + '\n');
            await _stream.WriteAsync(buf).ConfigureAwait(false);
            await _stream.FlushAsync().ConfigureAwait(false);

            Console.WriteLine($"[SocketClient] sent `{cmd}`");
            return true;
        }
        catch (Exception ex)
        {
            Console.WriteLine($"[SocketClient] send failed: {ex.Message}");
            try { _client?.Dispose(); } catch { }
            _client = null;
            _stream = null;
            return false;
        }
        finally
        {
            Gate.Release();
        }
    }
}
