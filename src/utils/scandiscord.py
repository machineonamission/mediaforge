"""
Miscellaneous helper functions for commands
"""

import json

import discord
import regex as re
from discord.ext import commands

import config
from core.clogs import logger
from utils.common import fetch
from utils.tempfiles import GifvUrl
from utils.web import contentlength


async def handlemessagesave(m: discord.Message, ignoreatts: list[discord.Attachment] | None = None):
    """
    handles saving of media from discord messages
    :param m: a discord message
    :param ignoreatts: list of discord attachments to ignore
    :return: list of file URLs detected in the message
    """
    # weird half-message thing that starts threads, get the actual parent message
    if m.type == discord.MessageType.thread_starter_message:
        m = m.reference.resolved
    detectedfiles = []
    if len(m.embeds):
        for embed in m.embeds:
            if embed.type == "gifv" and embed.video:
                detectedfiles.append(GifvUrl(embed.video.url))
            elif embed.type in ["image", "video", "audio"]:
                if await contentlength(embed.url):  # prevent adding youtube videos and such
                    detectedfiles.append(embed.url)
                elif embed.type == "image" and await contentlength(embed.thumbnail.url):  # fix for modern embeds
                    detectedfiles.append(embed.thumbnail.url)
    if len(m.attachments):
        for att in m.attachments:
            if ignoreatts is None or att not in ignoreatts:  # ignore duplicate atts
                if not att.filename.endswith("txt"):  # it was reading traceback attachments >:(
                    detectedfiles.append(att.url)
    if len(m.stickers):
        for sticker in m.stickers:
            if sticker.format != discord.StickerFormatType.lottie:
                detectedfiles.append(str(sticker.url))
            else:
                logger.info("lottie sticker ignored.")
            # this is commented out due to the lottie render code being buggy
            # if sticker.format == discord.StickerType.lottie:
            #     detectedfiles.append("LOTTIE|" + lottiestickers.stickerurl(sticker))
    return detectedfiles


async def imagesearch(ctx, nargs=1, ignore: list[discord.Attachment] | None = None):
    """
    searches the channel for nargs media
    :param ctx: command context
    :param nargs: amount of media to return
    :param startfiles: start the search with these files, will be ignored from the current message
    :return: list of file paths if found or empty list
    """
    messageschecked = []
    outfiles = []

    m = ctx.message
    messageschecked.append(m)
    hm = await handlemessagesave(m, ignoreatts=ignore)
    outfiles += hm
    if len(outfiles) >= nargs:
        return outfiles[:nargs]

    if ctx.message.reference:
        m = ctx.message.reference.resolved
        messageschecked.append(m)
        hm = await handlemessagesave(m)
        outfiles += hm
        if len(outfiles) >= nargs:
            return outfiles[:nargs]
    async for m in ctx.channel.history(limit=50, before=ctx.message):
        logger.debug(m.type)
        if m not in messageschecked:
            messageschecked.append(m)
            hm = await handlemessagesave(m)
            outfiles += hm
            if len(outfiles) >= nargs:
                return outfiles[:nargs]
    return []