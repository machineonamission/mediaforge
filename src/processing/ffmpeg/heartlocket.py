import asyncio

import processing.vips.creation
from processing.common import run_parallel
from processing.ffmpeg.conversion import mediatopng
from processing.ffmpeg.ffprobe import get_resolution
import processing.mediatype
from processing.run_command import run_command

from utils.tempfiles import TempFile, reserve_tempfile
from enum import Enum


class ArgType(Enum):
    MEDIA_MEDIA = 0
    TEXT_MEDIA = 1
    MEDIA_TEXT = 2
    TEXT_TEXT = 3


async def heart_locket(arg1, arg2, type: ArgType):
    # processing always does in order of media, text, so
    match type:
        case ArgType.MEDIA_MEDIA:
            media1: TempFile = arg1
            media2: TempFile = arg2
        case ArgType.TEXT_MEDIA:
            media1: TempFile = await run_parallel(processing.vips.creation.heartlockettext, arg2)
            media2: TempFile = arg1
        case ArgType.MEDIA_TEXT:
            media1: TempFile = arg1
            media2: TempFile = await run_parallel(processing.vips.creation.heartlockettext, arg2)
        case ArgType.TEXT_TEXT:
            media1: TempFile = await run_parallel(processing.vips.creation.heartlockettext, arg1)
            media2: TempFile = await run_parallel(processing.vips.creation.heartlockettext, arg2)

    # input is RTL, but filter is LTR
    media1, media2 = await asyncio.gather(mediatopng(media2), mediatopng(media1))
    out = reserve_tempfile("mkv")
    w1, h1 = await get_resolution(media1)
    w2, h2 = await get_resolution(media2)

    # you would not FUCKING believe how painful these equations were to derive.
    # hours of trying random things and chatgpt
    xmap1 = (
        f"(floor(r(X,Y)/255)"
        f" + 256*mod(floor(b(X,Y)/255),16) )"  # 0..255
        f" * {w1} / 4096"  # scale to 0..w
    )
    ymap1 = (
        f"(floor(g(X,Y)/255)"
        f" + 256*floor(floor(b(X,Y)/255)/16) )"  # 0..255
        f" * {h1} / 4096"  # scale to 0..h
    )

    xmap2 = (
        f"(floor(r(X,Y)/255)"
        f" + 256*mod(floor(b(X,Y)/255),16) )"  # 0..255
        f" * {w2} / 4096"  # scale to 0..w
    )
    ymap2 = (
        f"(floor(g(X,Y)/255)"
        f" + 256*floor(floor(b(X,Y)/255)/16) )"  # 0..255
        f" * {h2} / 4096"  # scale to 0..h
    )
    length = 39 / 10.13
    await run_command(
        "ffmpeg",
        # "-r", "10.13",
        # "-start_number", "9",
        "-r", "10.13", "-loop", "1", "-i", media1,
        "-r", "10.13", "-loop", "1", "-i", media2,
        "-r", "10.13", "-i", "rendering/heartlocket/mapper.mkv",  # The color "every pixel" map
        "-r", "10.13", "-i", "rendering/heartlocket/mapper2.mkv",  # maps each half of the locket
        "-r", "10.13", "-i", "rendering/heartlocket/neutral.mkv",  # the background
        "-r", "10.13", "-i", "rendering/heartlocket/light.mkv",  # shading
        "-r", "10.13", "-i", "rendering/heartlocket/dark.mkv",  # highlighting
        "-filter_complex",
        (
            # pre-process
            "[2:v]format=rgba64,split=4[colormapx1][colormapy1][colormapx2][colormapy2];"
            # convert from weird proprietary color thing to x map
            f"[colormapx1]geq=r='{xmap1}':g='{xmap1}':b='{xmap1}',format=gray16le[xmap1];"
            # convert from weird proprietary color thing to y map
            f"[colormapy1]geq=r='{ymap1}':g='{ymap1}':b='{ymap1}',format=gray16le[ymap1];"
            # convert from weird proprietary color thing to x map
            f"[colormapx2]geq=r='{xmap2}':g='{xmap2}':b='{xmap2}',format=gray16le[xmap2];"
            # convert from weird proprietary color thing to y map
            f"[colormapy2]geq=r='{ymap2}':g='{ymap2}':b='{ymap2}',format=gray16le[ymap2];"
            # remove alpha
            "[0:v]split=2[bg1][fg1];[bg1]drawbox=c=white@1:replace=1:t=fill[bg1];"
            "[bg1][fg1]overlay=format=auto[media0];"
            "[1:v]split=2[bg2][fg2];[bg2]drawbox=c=white@1:replace=1:t=fill[bg2];"
            "[bg2][fg2]overlay=format=auto[media1];"
            # map the input image onto the locket
            "[media0][xmap1][ymap1]remap[mapped1];"
            "[media1][xmap2][ymap2]remap[mapped2];"
            # add the shading
            # TODO: the shading doesn't perfectly replicate the original.
            #  the original does some indecipherable pixel math
            #  the main difference is that the blending between the edges is smooth, but this will do
            "[5:v]geq=r='0':g='0':b='0':a='255-r(X,Y)',format=rgba,split=2[shading1][shading2];"
            "[6:v]geq=r='255':g='255':b='255':a='r(X,Y)',format=rgba,split=2[highlight1][highlight2];"
            "[mapped1][shading1]overlay[shaded1];"
            "[shaded1][highlight1]overlay[highlighted1];"
            "[mapped2][shading2]overlay[shaded2];"
            "[shaded2][highlight2]overlay[highlighted2];"
            # trim the image to each half of the locket
            "[3:v]split=2[2v1][2v2];"
            "[2v1]geq=r='0':g='0':b='0':a='if(eq(r(X, Y), 1), 255, 0)',format=rgba,alphaextract[mask1];"
            "[2v2]geq=r='0':g='0':b='0':a='if(eq(r(X, Y), 2), 255, 0)',format=rgba,alphaextract[mask2];"
            "[highlighted1][mask1]alphamerge[trimmed1];"
            "[highlighted2][mask2]alphamerge[trimmed2];"
            # combine everything
            "[4:v][trimmed1]overlay[combined1];"
            "[combined1][trimmed2]overlay"
            # "[2v1]geq=if(eq(r(X,Y),2),255,0)[mask2]"
        ),
        "-c:v", "ffv1", "-t", str(length),
        out)
    out.mt = processing.mediatype.MediaType.GIF
    # await run_command("ffplay", out)
    return out
