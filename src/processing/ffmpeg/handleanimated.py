import inspect

from processing.common import run_parallel
from processing.ffmpeg.ffprobe import get_frame_rate
from processing.ffmpeg.ffutils import splitaudio, concat_demuxer, ffmpegsplit
from processing.mediatype import VIDEO, GIF
from processing.run_command import run_command
from utils.tempfiles import reserve_tempfile, TempFile


def run_sync_per_frame(syncfunc: callable, inoutfiles, *args, **kwargs):
    return [syncfunc(file, *args, **kwargs) for file in inoutfiles]


async def handleanimated(media: TempFile, function: callable, *args, **kwargs):
    """
    handles animated media
    :param media: media
    :param function: function to apply to each frame
    :return: processed media
    """
    files = await ffmpegsplit(media)
    fps = await get_frame_rate(media)
    audio = await splitaudio(media)
    outnames: list[str]
    if inspect.iscoroutinefunction(function):
        outnames = [(await function(file, *args, **kwargs)) for file in files]
    else:
        outnames = await run_parallel(run_sync_per_frame, function, files, *args, **kwargs)

    outdemuxer = await concat_demuxer(outnames)

    outfile = reserve_tempfile("mkv")
    if audio:
        await run_command("ffmpeg", "-r", str(fps), "-f", "concat", "-safe", "0", "-i", outdemuxer, "-i", audio,
                          "-c:v", "ffv1", "-c:a", "copy", outfile)
    else:
        await run_command("ffmpeg", "-r", str(fps), "-f", "concat", "-safe", "0", "-i", outdemuxer, "-c:v", "ffv1",
                          outfile)
    if await media.mediatype() == GIF:
        outfile.mt = GIF
    return outfile


async def animatedmultiplexer(media: TempFile, function: callable, *args, **kwargs):
    mt = await media.mediatype()
    if mt in [VIDEO, GIF]:
        return await handleanimated(media, function, *args, **kwargs)
    else:
        if inspect.iscoroutinefunction(function):
            return await function(media, *args, **kwargs)
        else:
            return await run_parallel(function, *args, **kwargs)
