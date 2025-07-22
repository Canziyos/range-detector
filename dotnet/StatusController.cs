

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
        if (string.IsNullOrEmpty(PicoEndpoint.CurrentIp))
        {
            return BadRequest("Current IP is not set.");
        }

        bool result = await SocketClient.Send(cmd, PicoEndpoint.CurrentIp);
        if (result)
        {
            return Ok(new { success = true });
        }
        else
        {
            return StatusCode(500, new { success = false, message = "Failed to send command." });
        }
    }
}