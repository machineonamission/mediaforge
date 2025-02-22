from processing.ffmpeg.ffprobe import get_resolution
from processing.ffmpeg.ffutils import resize
from processing.run_command import run_command
from utils.tempfiles import TempFile, reserve_tempfile


async def heart_locket(media: TempFile):
    out = reserve_tempfile("mkv")
    w,h = await get_resolution(media)

    # you would not FUCKING believe how painful these equations were to derive.
    # hours of trying random things and chatgpt
    xmap = (
        f"(floor(r(X,Y)/255)"
        f" + 256*mod(floor(b(X,Y)/255),16) )"  # 0..255
        f" * {w} / 4096"                  # scale to 0..w
    )
    ymap = (
        f"(floor(g(X,Y)/255)"
        f" + 256*floor(floor(b(X,Y)/255)/16) )"  # 0..255
        f" * {h} / 4096"                    # scale to 0..h
    )
    await run_command(
        "ffmpeg",
        "-i", media,  # Your main image/video
        "-i", "rendering/images/heartlocket/mapper/38.png",  # The color "every pixel" map
        "-filter_complex",
        (
            # pre-process
            "[1:v]format=rgba64,split=2[1v1][1v2];"
            # convert from weird proprietary color thing to x map
            f"[1v1]geq=r='{xmap}':g='{xmap}':b='{xmap}',format=gray16le[xmap];"
            # convert from weird proprietary color thing to y map
            f"[1v2]geq=r='{ymap}':g='{ymap}':b='{ymap}',format=gray16le[ymap];"
            # map the input image onto the locket
            "[0:v][xmap][ymap]remap,format=rgba"#,split=2[mapped1][mapped2];"
        ),
        "-c:v", "ffv1", "-fps_mode", "vfr",# "-shortest",
        out)
    # await run_command("ffplay", out)
    return out
