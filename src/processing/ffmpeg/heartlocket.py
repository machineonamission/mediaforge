import asyncio
from enum import Enum

import processing.mediatype
import processing.vips.creation
from processing.common import run_parallel
from processing.ffmpeg.ffprobe import hasaudio
from processing.mediatype import VIDEO, IMAGE, GIF
from processing.run_command import run_command
from utils.tempfiles import TempFile, reserve_tempfile


class ArgType(Enum):
    MEDIA_MEDIA = 0
    TEXT_MEDIA = 1
    MEDIA_TEXT = 2
    TEXT_TEXT = 3


async def heart_locket(arg1, arg2, type: ArgType):
    media1: TempFile
    media2: TempFile
    # processing always does in order of media, text, so
    match type:
        case ArgType.MEDIA_MEDIA:
            media1 = arg1
            media2 = arg2
        case ArgType.TEXT_MEDIA:
            media1 = await run_parallel(processing.vips.creation.heartlockettext, arg2)
            media2 = arg1
        case ArgType.MEDIA_TEXT:
            media1 = arg1
            media2 = await run_parallel(processing.vips.creation.heartlockettext, arg2)
        case ArgType.TEXT_TEXT:
            media1, media2 = await asyncio.gather(
                run_parallel(processing.vips.creation.heartlockettext, arg1),
                run_parallel(processing.vips.creation.heartlockettext, arg2)
            )

    fps = 10.13
    # force codec to be video codec so stream_loop works
    # also force fps otherwise ffmpeg gets confused
    ffv1m1 = reserve_tempfile("mkv")
    ffv1m2 = reserve_tempfile("mkv")
    mt1, mt2 = await asyncio.gather(media1.mediatype(), media2.mediatype())
    for media, out, mt in ((media1, ffv1m1, mt1), (media2, ffv1m2, mt2)):
        if mt == IMAGE:
            await run_command("ffmpeg", "-r", str(fps), "-i", media, "-c:v", "ffv1", "-c:a", "flac", out)
        else:
            await run_command("ffmpeg", "-i", media, "-filter:v", f"fps={fps}", "-c:v", "ffv1", "-c:a", "flac", out)
    # input is RTL, but filter is LTR
    media1, media2 = ffv1m2, ffv1m1

    out = reserve_tempfile("mkv")
    match (await asyncio.gather(hasaudio(media1), hasaudio(media2))):
        case (True, True):
            mixer = "[0:a][1:a]amix=inputs=2:dropout_transition=0:duration=longest"
        case (True, False):
            mixer = "[0:a]anull"
        case (False, True):
            mixer = "[1:a]anull"
        case (False, False):
            mixer = ""

    fixedres = 384
    virtualres = fixedres * 2
    # you would not FUCKING believe how painful these equations were to derive.
    # hours of trying random things and chatgpt
    red = "floor(r(X,Y)/255)"
    green = "floor(g(X,Y)/255)"
    blue = "floor(b(X,Y)/255)"
    xmap = f"({red} + 256*mod({blue},16)) * ({virtualres} / 4096)"
    ymap = f"({green} + 256*floor({blue}/16)) * ({virtualres} / 4096)"
    # 39 frames
    length = 39 / fps


    await run_command(
        "ffmpeg",
        "-r", str(fps), "-stream_loop", "-1", "-i", media1,
        "-r", str(fps), "-stream_loop", "-1", "-i", media2,
        "-r", str(fps), "-i", "rendering/heartlocket/mapper.mkv",  # The color "every pixel" map
        "-r", str(fps), "-i", "rendering/heartlocket/mapper2.mkv",  # maps each half of the locket
        "-r", str(fps), "-i", "rendering/heartlocket/neutral.mkv",  # the background
        "-r", str(fps), "-i", "rendering/heartlocket/light.mkv",  # shading
        "-r", str(fps), "-i", "rendering/heartlocket/dark.mkv",  # highlighting
        "-max_muxing_queue_size", "9999", "-sws_flags",
        "spline+accurate_rnd+full_chroma_int+full_chroma_inp+bitexact",
        "-filter_complex",
        (
            # pre-process
            "[2:v]format=rgba64,split=4[colormapx1][colormapy1][colormapx2][colormapy2];"
            # convert from weird proprietary color thing to x map
            f"[colormapx1]geq=r='{xmap}':g='{xmap}':b='{xmap}',format=gray16le[xmap1];"
            # convert from weird proprietary color thing to y map
            f"[colormapy1]geq=r='{ymap}':g='{ymap}':b='{ymap}',format=gray16le[ymap1];"
            # convert from weird proprietary color thing to x map
            f"[colormapx2]geq=r='{xmap}':g='{xmap}':b='{xmap}',format=gray16le[xmap2];"
            # convert from weird proprietary color thing to y map
            f"[colormapy2]geq=r='{ymap}':g='{ymap}':b='{ymap}',format=gray16le[ymap2];"
            # resize input to right size for aliasing, then make bigger to avoid weird distortion
            # also fix fps
            f"[0:v]scale={fixedres}:{fixedres},scale={virtualres}:{virtualres},setsar=1:1[media0];"
            f"[1:v]scale={fixedres}:{fixedres},scale={virtualres}:{virtualres},setsar=1:1[media1];"
            # remove alpha
            "[media0]split=2[bg1][fg1];[bg1]drawbox=c=white@1:replace=1:t=fill[bg1];"
            "[bg1][fg1]overlay=format=auto[media0r];"
            "[media1]split=2[bg2][fg2];[bg2]drawbox=c=white@1:replace=1:t=fill[bg2];"
            "[bg2][fg2]overlay=format=auto[media1r];"''
            # map the input image onto the locket
            "[media0r][xmap1][ymap1]remap[mapped1];"
            "[media1r][xmap2][ymap2]remap[mapped2];"
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
            "[combined1][trimmed2]overlay;"
            f"{mixer}"
        ),
        "-c:v", "ffv1", "-c:a", "flac", "-t", str(length),
        out)
    if VIDEO not in [mt1, mt2]:
        out.mt = GIF
    # await run_command("ffplay", out)
    return out
