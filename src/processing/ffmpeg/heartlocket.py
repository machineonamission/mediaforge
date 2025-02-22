from processing.ffmpeg.ffprobe import get_resolution
from processing.ffmpeg.ffutils import resize
from processing.run_command import run_command
from utils.tempfiles import TempFile, reserve_tempfile


async def heart_locket(media: TempFile):
    out = reserve_tempfile("mkv")
    media = await resize(media, 256,256)
    w,h = await get_resolution(media)
    scalefactor = 16
    pixelscalefactor = 1
    # xmap = f"({w}*(r(X, Y)*{pixelscalefactor}/{scalefactor} + {scalefactor}*mod(b(X, Y)*{pixelscalefactor},{scalefactor}))  )/255"
    # ymap = f"({h}*(g(X, Y)*{pixelscalefactor}/{scalefactor} + {scalefactor}*floor(b(X, Y)*{pixelscalefactor}/{scalefactor})))/255"

    # xmap = "X"
    # ymap = "Y"
    xmap = (
        f"( ( ((r(X,Y)/255)) )"
        f" + 256*mod((b(X,Y)/255),16) )"  # 0..255
        f" * {w} / 4096"                  # scale to 0..w
    )
    ymap = (
        f"( ( ((g(X,Y)/255)) )"
        f" + 256*floor((b(X,Y)/255)/16) )"  # 0..255
        f" * {h} / 4096"                    # scale to 0..h
    )
    # xmap = "0.5"
    # ymap = "0.5"
    await run_command(
        "ffmpeg",
        "-i", media,  # Your main image/video
        "-i", "rendering/images/heartlocket/38/mapper.png",  # The color "every pixel" map
        "-filter_complex",
        (
            "[1:v]format=rgba64,split=2[1v1][1v2];"
            # 1) Create the X map (16-bit grayscale) from R/B
            f"[1v1]geq=r='{xmap}':g='{xmap}':b='{xmap}',format=gray16le[xmap];"
            # 2) Create the Y map (16-bit grayscale) from G/B
            f"[1v2]geq=r='{ymap}':g='{ymap}':b='{ymap}',format=gray16le[ymap];"
            # 3) Remap the main input using absolute mode
            "[0:v][xmap][ymap]remap"
        ),
        "-c:v", "ffv1", "-fps_mode", "vfr",
        out)
    # await run_command("ffplay", out)
    return out
