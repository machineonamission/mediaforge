import asyncio
import inspect
import typing
from urllib.parse import urlparse

import discord
from discord.ext import commands

import config
import processing.common
import processing.ffmpeg.conversion
import processing.ffmpeg.ensuresize
import processing.ffmpeg.ffprobe
import processing.mediatype
import utils.tempfiles
from core import queue
from core.clogs import logger
from utils.scandiscord import imagesearch
from utils.web import saveurls


async def process(ctx: commands.Context, func: callable, inputs: list, *args,
                  slashfiles: list[discord.Attachment] | None = None,
                  resize=True, expectimage=True, uploadresult=True, run_parallel=False, spoiler=False,
                  name: str | None = None, **kwargs):
    """
    The core function of the bot. Gathers media and sends it to the proper function.

    :param ctx: discord context. media is gathered using imagesearch() with this.
    :param func: function to process input media with
    :param inputs: list of lists of strings. each inner list is an argument, the strings it contains are the
        types that arg must be. or just False/[] if no media needed
    :param args: any non-media arguments, passed into func()
    :param resize: automatically up/downsize the inputs?
    :param expectimage: is func() supposed to return a result? if true, it expects an image. if false, can use a
        string.
    :param uploadresult: if true, uploads the result automatically.
    :param run_parallel: for sync functions only, run without blocking
    :return: filename of processed media
    """

    result = None
    msg: typing.Optional[discord.Message] = None

    async def reply(st):
        return await ctx.reply(f"{config.emojis['working']} {st}", mention_author=False)

    async def updatestatus(st):
        nonlocal msg
        try:
            if msg is None:
                msg = await reply(st)
            else:
                msg = await msg.edit(content=f"{config.emojis['working']} {st}",
                                     allowed_mentions=discord.AllowedMentions.none())
        except discord.NotFound:
            msg = await reply(st)

    if inputs:
        # nothing to download sometimes
        await updatestatus(f"Downloading...")

    try:
        async with utils.tempfiles.TempFileSession():
            # get media from channel
            if inputs:
                if isinstance(slashfiles, discord.Attachment):
                    slashfiles = [slashfiles]
                elif slashfiles is None:
                    slashfiles = []
                slashfiles: list[discord.Attachment]
                # pad a list to the length, given the slashfiles
                urls = [s.url if s is not None else None for s in slashfiles] + [None] * (len(inputs) - len(slashfiles))
                # trim excess
                urls = urls[:len(inputs)]
                missing_file_count = urls.count(None)
                if missing_file_count > 0:
                    # search for any missing
                    # pass the slashfiles so if we get attachments via the param via a text command, we can ignore them
                    searched_urls = await imagesearch(ctx, missing_file_count, [s for s in slashfiles if s is not None])
                    # insert into list
                    index = 0
                    for i, url in enumerate(urls):
                        if url is None:
                            urls[i] = searched_urls[index]
                            index += 1
                # spoiler if needed
                spoiler = spoiler or any([urlparse(u).path.split("/")[-1].startswith("SPOILER_") for u in urls])
                files = await saveurls(urls)
            else:
                files = []
            # if media found or none needed
            if files or not inputs:
                # check that each file is correct type
                for i, file in enumerate(files):
                    # if file is incorrect type
                    if (imtype := await file.mediatype()) not in inputs[i]:
                        # send message and break
                        await ctx.reply(
                            f"{config.emojis['warning']} Media #{i + 1} is {imtype}, it must be: "
                            f"{', '.join(inputs[i])}")
                        logger.info(f"Media {i} type {imtype} is not in {inputs[i]}")
                        break
                    # send warning for apng
                    if await processing.ffmpeg.ffprobe.is_apng(file):
                        asyncio.create_task(
                            ctx.reply(f"{config.emojis['warning']} Media #{i + 1} is an apng, w"
                                      f"hich FFmpeg and MediaForge have limited support for. Ex"
                                      f"pect errors.", delete_after=10))
                # files are of correcte type, begin to process
                else:
                    # only update with queue message if there is a queue
                    if queue.queue_enabled and queue.sem.locked():
                        await updatestatus("Your command is in the queue...")

                    # run func
                    async def run():
                        nonlocal args
                        nonlocal files
                        logger.info("Processing...")
                        await updatestatus("Forging...")

                        # remove too long videossss
                        for i in range(len(files)):
                            if resize:
                                files[i] = await processing.ffmpeg.ensuresize.ensuresize(ctx, files[i], config.min_size,
                                                                                         config.max_size)
                            files[i] = await processing.ffmpeg.ensuresize.ensureduration(files[i], ctx)
                        # prepare args
                        if inputs:
                            args = files + list(args)
                        # some commands arent coros (usually no-ops) so this is a good check to make
                        if inspect.iscoroutinefunction(func):
                            command_result = await func(*args, **kwargs)
                        else:
                            if run_parallel:
                                command_result = await processing.common.run_parallel(func, *args, **kwargs)
                            else:
                                logger.warning(f"{func} is not coroutine")
                                command_result = func(*args, **kwargs)
                        if expectimage and command_result:
                            re_encoded = await processing.ffmpeg.conversion.allreencode(command_result)
                            ensured_size = await processing.ffmpeg.ensuresize.assurefilesize(re_encoded, command_result)
                            command_result = ensured_size
                        return command_result

                    result = await queue.enqueue(run())
                    # check results are as expected
                    if expectimage:  # file expected
                        if not result:
                            raise processing.common.ReturnedNothing(f"Expected image, {func} returned nothing.")
                    else:  # status string expected
                        if not result:
                            raise processing.common.ReturnedNothing(f"Expected string, {func} returned nothing.")
                        else:
                            await ctx.reply(result)

                    # if we need to upload image, do that
                    if result and expectimage:
                        logger.info("Uploading...")
                        await updatestatus("Uploading...")
                        if uploadresult:
                            if ctx.interaction:
                                await msg.edit(content="",
                                               attachments=[discord.File(result, spoiler=spoiler, filename=name)])
                            else:
                                await ctx.reply(file=discord.File(result, spoiler=spoiler, filename=name))

            else:  # no media found but media expected
                logger.info("No media found.")
                if ctx.interaction:
                    await msg.edit(content=f"{config.emojis['x']} No file found.")
                else:
                    await ctx.reply(f"{config.emojis['x']} No file found.")
    except Exception as e:
        if msg is not None and not ctx.interaction:
            await msg.delete()
        raise e
    # delete message
    if msg is not None and not ctx.interaction:
        await msg.delete()
    return result
