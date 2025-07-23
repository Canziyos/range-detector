

using System.Threading.Tasks;
using Microsoft.AspNetCore.Mvc;
namespace RangeDetector;

[ApiController]
[Route("status/[action]")]
public class StatusController : ControllerBase
{
    private readonly DistanceState distanceState;

    public StatusController(DistanceState distanceState)
    {
        this.distanceState = distanceState;
    }

    [HttpGet]
    public IActionResult GetStatus()
    {
        return Ok(new
        {
            measured = distanceState.lastDistMeasured,
            updated = distanceState.LastUpdatedUtc
        });
    }

    [HttpPost]
    public async Task<IActionResult> SendCmd(string cmd)
    {
        string host = PicoEndpoint.CurrentIp ?? "192.168.10.223"; // fallback.
        bool ok = await SocketClient.Send(cmd, host);
        return ok
            ? Ok(new { success = true })
            : StatusCode(500, "Send failed.");
    }
}