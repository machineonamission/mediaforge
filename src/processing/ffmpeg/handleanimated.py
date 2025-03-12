import glob
import inspect

from core.clogs import logger
from processing.common import run_parallel
from processing.ffmpeg.ffprobe import get_frame_rate
from processing.ffmpeg.ffutils import splitaudio, concat_demuxer
from processing.run_command import run_command
from utils.tempfiles import reserve_tempfile


async def ffmpegsplit(media):
    """
    splits the input file into frames
    :param media: file
    :return: [list of files, ffmpeg key to find files]
    """
    logger.info("Splitting frames...")
    await run_command("ffmpeg", "-hide_banner", "-i", media, "-vsync", "1", f"{media.split('.')[0]}_%09d.png")
    files = glob.glob(f"{media.split('.')[0]}_*.png")
    files = [reserve_tempfile(f) for f in files]

    return files


def run_sync_per_frame(syncfunc: callable, inoutfiles, *args, **kwargs):
    return [syncfunc(file, *args, **kwargs) for file in inoutfiles]


async def handleanimated(media, function: callable, *args, **kwargs):
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
        outnames = [await function(file, *args, **kwargs) for file in files]
    else:
        outnames = await run_parallel(run_sync_per_frame, function, files, *args, **kwargs)

    outdemuxer = await concat_demuxer(outnames)

    outfile = await reserve_tempfile("mkv")
    if audio:
        await run_command("ffmpeg", "-r", str(fps), "-f", " concat", "-safe", "0", "-i", outdemuxer, "-i", audio,
                          "-c:v", "ffv1", "-c:a", "copy", outfile)
    else:
        await run_command("ffmpeg", "-r", str(fps), "-f", " concat", "-safe", "0", "-i", outdemuxer, "-c:v", "ffv1",
                          outfile)

    return outfile
