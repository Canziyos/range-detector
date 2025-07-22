using System;
using System.Threading.Tasks;

public sealed class PulseProcessor : IMessageHandler
{
    private const int THRESHOLD_MM = 2000;     // >30 cm => far
    private const int GRACE_MS = 500;     // far for 0.5 s
    private const int RETRY_MS = 5000;    // after failed OFF

    private DateTime _lastSeenClose = DateTime.UtcNow;
    private DateTime _lastFarEnough = DateTime.MinValue;
    private DateTime _nextRetry = DateTime.MinValue;
    private bool _offSent = false;
    private readonly DistanceState _distState;
    public PulseProcessor(DistanceState dist)
    {
        _distState = dist;
    }

    public Task HandleLineAsync(string line)
    {
        if (!line.StartsWith("distance:", StringComparison.OrdinalIgnoreCase))
            return Task.CompletedTask;

        if (!int.TryParse(line.AsSpan(9).Trim(), out int mm))
            return Task.CompletedTask;

        Console.WriteLine($"distance = {mm} mm");
        _distState.lastDistMeasured = mm;
        _distState.LastUpdatedUtc = DateTime.UtcNow;

        var now = DateTime.UtcNow;
        if (mm <= THRESHOLD_MM) _lastSeenClose = now;
        else _lastFarEnough = now;

        return Task.CompletedTask;
    }

    // public async Task TickAsync()
    public Task TickAsync()
    {
        var now = DateTime.UtcNow;

        bool needOff = (now - _lastFarEnough).TotalMilliseconds >= GRACE_MS && !_offSent && now >= _nextRetry;

        if (needOff)
        {
            string host = PicoEndpoint.CurrentIp ?? "192.168.10.223";
            //     if (await SocketClient.Send("OFF", host))
            //     {
            //         Console.WriteLine("sent `OFF` (object out of range)");
            //         _offSent = true;
            //     }
            //     else
            //     {
            //         _nextRetry = now.AddMilliseconds(RETRY_MS);
            //     }
        }

        if (_offSent && (now - _lastSeenClose).TotalMilliseconds >= 1000)
        {
            // Console.WriteLine("object back in range – LED allowed ON");
            _offSent = false;
            _nextRetry = now.AddMilliseconds(RETRY_MS);
        }
        
        return Task.CompletedTask;
    }
}
