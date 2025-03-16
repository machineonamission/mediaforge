import asyncio
import glob
import math
import os
import sys
import typing

import discord
import humanize
from discord.ext import commands

import config
import utils
from core.clogs import logger
from processing.common import NonBugError, ReturnedNothing
from processing.ffmpeg.ffprobe import get_frame_rate, get_duration, get_resolution
from processing.ffmpeg.ffutils import changefps, trim, resize
from processing.mediatype import VIDEO, IMAGE, GIF
from processing.run_command import run_command
from utils.tempfiles import reserve_tempfile


async def edit_msg_with_webhookmessage_polyfill(msg: typing.Union[discord.Message, discord.WebhookMessage],
                                                delete_after=None, **kwargs):
    """
    helper function to add `delete_after` support to WebhookMessage
    """
    if isinstance(msg, discord.WebhookMessage):
        async def wait_and_delete(msg):
            await asyncio.sleep(delete_after)
            await msg.delete()

        await msg.edit(**kwargs)  # WebhookMessage doesn't have a delete_after attribute!
        if delete_after:
            asyncio.create_task(wait_and_delete(msg))
    else:
        await msg.edit(**kwargs, delete_after=delete_after)


async def ensureduration(media, ctx: commands.Context):
    """
    ensures that media is under or equal to the config minimum frame count and fps
    :param media: media to trim
    :param ctx: discord context
    :return: processed media or original media, within config.max_frames
    """
    if await ctx.bot.is_owner(ctx.author):
        logger.debug(f"bot owner is exempt from duration checks.")
        return media
    if await media.mediatype() not in [VIDEO, GIF]:
        return media
    max_fps = config.max_fps if hasattr(config, "max_fps") else None
    fps = await get_frame_rate(media)
    if fps > max_fps:
        logger.debug(f"Capping FPS of {media} from {fps} to {max_fps}")
        media = await changefps(media, max_fps)
    # the function that splits frames actually has a vsync thing so this is more accurate to what's generated
    max_frames = config.max_frames if hasattr(config, "max_frames") else None
    fps = await get_frame_rate(media)
    try:
        dur = await get_duration(media)
    except Exception as e:
        dur = 0
        logger.debug(e)
    frames = int(fps * dur)
    if max_frames is None or frames <= max_frames:
        return media
    else:
        newdur = max_frames / fps
        tmsg = f"{config.emojis['warning']} input file is too long (~{frames} frames)! " \
               f"Trimming to {round(newdur, 1)}s (~{max_frames} frames)..."
        logger.debug(tmsg)
        msg = await ctx.reply(tmsg)
        media = await trim(media, newdur)
        try:
            await edit_msg_with_webhookmessage_polyfill(msg, delete_after=5, content=tmsg + " Done!")
        except discord.NotFound as e:
            logger.debug(e)
        return media


TOLERANCES = [.98, .95, .90, .75, .5, .25, .1]


async def twopasscapvideo(video, maxsize: int, audio_bitrate=128000):
    """
    attempts to intelligently cap video filesize with two pass encoding

    :param video: video file (str path)
    :param maxsize: max size (in bytes) of output file
    :param audio_bitrate: optionally specify an audio bitrate in bits per second
    :return: new video file below maxsize
    """
    if (size := os.path.getsize(video)) < maxsize:
        return video
    # https://trac.ffmpeg.org/wiki/Encode/H.264#twopass
    duration = await get_duration(video)
    # bytes to bits
    target_total_bitrate = (maxsize * 8) / duration
    for tolerance in TOLERANCES:
        target_video_bitrate = (target_total_bitrate - audio_bitrate) * tolerance
        if target_video_bitrate <= 0:
            raise NonBugError("Cannot fit video into Discord.")
        logger.info(f"trying to force {video} ({humanize.naturalsize(size)}) "
                    f"under {humanize.naturalsize(maxsize)} with tolerance {tolerance}. "
                    f"trying {humanize.naturalsize(target_video_bitrate / 8)}/s")
        pass1log = utils.tempfiles.temp_file_name()
        outfile = reserve_tempfile("mp4")
        await run_command('ffmpeg', '-y', '-i', video, '-c:v', 'h264', '-b:v', str(target_video_bitrate), '-pass', '1',
                          '-f', 'mp4', '-passlogfile', pass1log,
                          'NUL' if sys.platform == "win32" else "/dev/null")
        await run_command('ffmpeg', '-i', video, '-c:v', 'h264', '-b:v', str(target_video_bitrate), '-pass', '2',
                          '-passlogfile', pass1log, '-c:a', 'aac', '-b:a', str(audio_bitrate), "-f", "mp4", "-movflags",
                          "+faststart", outfile)
        # log files are pass1log-N.log and pass1log-N.log.mbtree where N is an int, easiest to just glob them all
        for f in glob.glob(pass1log + "*"):
            reserve_tempfile(f)
        if (size := os.path.getsize(outfile)) < maxsize:
            logger.info(f"successfully created {humanize.naturalsize(size)} video!")
            return outfile
        else:
            logger.info(f"tolerance {tolerance} failed. output is {humanize.naturalsize(size)}")
    raise NonBugError(f"Unable to fit {video} within {humanize.naturalsize(maxsize)}")


async def intelligentdownsize(media, maxsize: int):
    """
    tries to intelligently downsize media to fit within maxsize

    :param media: media path str
    :param maxsize: max size in bytes
    :return: new media file below maxsize
    """

    size = os.path.getsize(media)
    w, h = await get_resolution(media)
    for tolerance in TOLERANCES:
        reduction_ratio = (maxsize / size) * tolerance
        # this took me longer to figure out than i am willing to admit
        new_w = math.floor(math.sqrt(reduction_ratio * (w ** 2)))
        new_h = math.floor(math.sqrt(reduction_ratio * (h ** 2)))
        logger.info(f"trying to resize from {w}x{h} to {new_w}x{new_h} (~{reduction_ratio} reduction)")
        resized = await resize(media, new_w, new_h, lock_codec=True)
        if (newsize := os.path.getsize(resized)) < maxsize:
            logger.info(f"successfully created {humanize.naturalsize(newsize)} media!")
            return resized
        else:
            logger.info(f"tolerance {tolerance} failed. output is {humanize.naturalsize(newsize)}")
    raise NonBugError(f"Unable to fit {media} within {humanize.naturalsize(maxsize)}")


async def assurefilesize(media):
    """
    compresses files to fit within config set discord limit

    :param media: media to check size of
    :param original: original media to actually downsize
    :return: filename of fixed media if it works, False if it still is too big.
    """
    if not media:
        raise ReturnedNothing(f"assurefilesize() was passed no media.")
    mt = await media.mediatype()
    size = os.path.getsize(media)
    if size > config.way_too_big_size:
        raise NonBugError(f"Resulting file is {humanize.naturalsize(size)}. "
                          f"Aborting upload since resulting file is over "
                          f"{humanize.naturalsize(config.way_too_big_size)}")
    if size < config.file_upload_limit:
        return media
    if mt == VIDEO:
        # fancy ffmpeg based video thing
        return await twopasscapvideo(media, config.file_upload_limit)
    elif mt in [IMAGE, GIF]:
        # file size should be roughly proportional to # of pixels so we can work with that :3
        return await intelligentdownsize(media, config.file_upload_limit)
    else:
        raise NonBugError(f"File is too big to upload.")


async def ensuresize(ctx, file, minsize, maxsize):
    """
    Ensures valid media is between minsize and maxsize in resolution
    :param ctx: discord context
    :param file: media
    :param minsize: minimum width/height in pixels
    :param maxsize: maximum height in pixels
    :return: original or resized media
    """
    resized = False
    if await file.mediatype() not in [IMAGE, VIDEO, GIF]:
        return file
    w, h = await get_resolution(file)
    owidth = w
    oheight = h
    if w < minsize:
        # the min(-1,maxsize) thing is to prevent a case where someone puts in like a 1x1000 image and it gets resized
        # to 200x200000 which is very large so even though it wont preserve aspect ratio it's an edge case anyways

        file = await resize(file, minsize, f"min(-1, {maxsize * 2})")
        w, h = await get_resolution(file)
        resized = True
    if h < minsize:
        file = await resize(file, f"min(-1, {maxsize * 2})", minsize)
        w, h = await get_resolution(file)
        resized = True
    # if await ctx.bot.is_owner(ctx.author):
    #     logger.debug(f"bot owner is exempt from downsize checks")
    #     return file
    if w > maxsize:
        file = await resize(file, maxsize, "-1")
        w, h = await get_resolution(file)
        resized = True
    if h > maxsize:
        file = await resize(file, "-1", maxsize)
        w, h = await get_resolution(file)
        resized = True
    if resized:
        logger.info(f"Resized from {owidth}x{oheight} to {w}x{h}")
        await ctx.reply(f"Resized input media from {int(owidth)}x{int(oheight)} to {int(w)}x{int(h)}.", delete_after=5,
                        mention_author=False)
    return file
