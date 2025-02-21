from processing.ffmpeg.ffprobe import get_resolution
from processing.run_command import run_command
from utils.tempfiles import TempFile, reserve_tempfile


async def heart_locket(media: TempFile):
    out = reserve_tempfile("mkv")
    w,h = await get_resolution(media)
    xmap = f"(r(X, Y)/16 + 16*mod(b(X, Y),16))"
    ymap = f"(g(X, Y)/16 + 16*floor(b(X, Y)/16))"
    await run_command(
        "ffmpeg",
        "-i", media,  # Your main image/video
        "-i", "rendering/images/heartlocket/38/mapper.png",  # The color "every pixel" map
        "-filter_complex",
        (
            # "[1:v]format=rgba64[1v];"
            # 1) Create the X map (16-bit grayscale) from R/B
            f"[1:v]geq=r='{xmap}':g='{xmap}':b='{xmap}'[xmap];"
            # 2) Create the Y map (16-bit grayscale) from G/B
            f"[1:v]geq=r='{ymap}':g='{ymap}':b='{ymap}'[ymap];"
            # 3) Remap the main input using absolute mode
            "[0:v][xmap][ymap]remap"
        ),
        out)
    # await run_command("ffplay", out)
    return out
