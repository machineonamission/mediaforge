from processing.ffmpeg.ffprobe import get_resolution
from processing.run_command import run_command
from utils.tempfiles import TempFile, reserve_tempfile


async def heart_locket(media: TempFile):
    out = reserve_tempfile("mkv")
    w,h = await get_resolution(media)
    scalefactor = 4112
    pixelscalefactor = 257
    xmap = f"({w}*(r(X, Y)*{pixelscalefactor}/{scalefactor} + {scalefactor}*mod(b(X, Y)*{pixelscalefactor},{scalefactor}))  )/65536"
    ymap = f"({h}*(g(X, Y)*{pixelscalefactor}/{scalefactor} + {scalefactor}*floor(b(X, Y)*{pixelscalefactor}/{scalefactor})))/65536"

    # xmap = (
    #     f"( ( (r(X,Y)/257)/16 )"
    #     f" + 16*mod((b(X,Y)/257),16) )"  # 0..255
    #     f" * {w} / 127"                  # scale to 0..w
    # )
    # ymap = (
    #     f"( ( (g(X,Y)/257)/16 )"
    #     f" + 16*floor((b(X,Y)/257)/16) )"  # 0..255
    #     f" * {h} / 256"                    # scale to 0..h
    # )
    # xmap = "0.5"
    # ymap = "0.5"
    await run_command(
        "ffmpeg",
        "-i", media,  # Your main image/video
        "-i", "rendering/images/heartlocket/38/mapper.png",  # The color "every pixel" map
        "-filter_complex",
        (
            "[1:v]format=rgba64[1v];"
            # 1) Create the X map (16-bit grayscale) from R/B
            f"[1v]geq=r='{xmap}':g='{xmap}':b='{xmap}',format=gray16le[xmap];"
            # 2) Create the Y map (16-bit grayscale) from G/B
            f"[1v]geq=r='{ymap}':g='{ymap}':b='{ymap}',format=gray16le[ymap];"
            # 3) Remap the main input using absolute mode
            "[0:v][xmap][ymap]remap"
        ),
        "-c:v", "ffv1", "-fps_mode", "vfr",
        out)
    # await run_command("ffplay", out)
    return out
