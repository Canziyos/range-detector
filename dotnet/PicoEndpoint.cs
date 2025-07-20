/// <summary>
/// Holds the Pico’s latest IP address, learned when it connects
/// to our inbound port 4321.
/// </summary>
public static class PicoEndpoint
{
    public static volatile string? CurrentIp;
}
