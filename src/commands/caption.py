import discord
from discord.ext import commands

import processing.ffmpeg.caption
import processing.vips.caption
import processing.vips.vipsutils
from core.process import process
from processing.mediatype import VIDEO, AUDIO, IMAGE, GIF


class Caption(commands.Cog, name="Captioning"):
    """
    Commands to caption media.
    """

    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(aliases=["demotivate", "motivational", "demotivational", "inspire", "uninspire"])
    async def motivate(self, ctx, *, caption: str, media: discord.Attachment | None = None):
        """
        Captions media in the style of demotivational posters.

        :param ctx: discord context
        :param caption: The caption text. Optionally add a bottom text with a `|` character.
        :param media: A video, gif, or image.
        """
        caption = caption.split("|")
        if len(caption) == 1:
            caption.append("")
        await process(ctx, processing.ffmpeg.caption.motivate, [[VIDEO, GIF, IMAGE]], caption, slashfiles=media)

    @commands.hybrid_command(aliases=["toptextbottomtext", "impact", "adviceanimal"])
    async def meme(self, ctx, *, caption: str, media: discord.Attachment | None = None):
        """
        Captions media in the style of top text + bottom text memes.

        :param ctx: discord context
        :param caption: The caption text. Optionally add a bottom text with a `|` character.
        :param media: A video, gif, or image.
        """
        caption = caption.split("|")
        if len(caption) == 1:
            caption.append("")
        await process(ctx, processing.vips.vipsutils.generic_caption_overlay, [[VIDEO, GIF, IMAGE]],
                      processing.vips.caption.meme, caption, slashfiles=media)

    @commands.hybrid_command(aliases=["snapchat", "snap", "snapcap", "snapcaption", "snapchatcap", "classiccaption"])
    async def snapchatcaption(self, ctx, *, caption: str, media: discord.Attachment | None = None):
        """
        Captions media in the style of the classic Snapchat caption.

        :param ctx: discord context
        :param caption: The caption text.
        :param media: A video, gif, or image.
        """
        await process(ctx, processing.vips.vipsutils.generic_caption_overlay, [[VIDEO, GIF, IMAGE]],
                      processing.vips.caption.snapchat, [caption], slashfiles=media)

    @commands.hybrid_command(aliases=["whisper", "wcap", "wcaption"])
    async def whispercaption(self, ctx, *, caption: str, media: discord.Attachment | None = None):
        """
        Captions media in the style of the confession website Whisper.

        :param ctx: discord context
        :param caption: The caption text.
        :param media: A video, gif, or image.
        """
        await process(ctx, processing.vips.vipsutils.generic_caption_overlay, [[VIDEO, GIF, IMAGE]],
                      processing.vips.caption.whisper, [caption], slashfiles=media)

    @commands.hybrid_command(aliases=["tenor"])
    async def tenorcap(self, ctx, *, caption: str, media: discord.Attachment | None = None):
        """
        Captions media in the style of tenor.

        :param ctx: discord context
        :param caption: The caption text. Optionally add a bottom text with a `|` character.
        :param media: A video, gif, or image.
        """
        caption = caption.split("|")
        if len(caption) == 1:
            caption.append("")
        await process(ctx, processing.vips.vipsutils.generic_caption_overlay, [[VIDEO, GIF, IMAGE]],
                      processing.vips.caption.tenor, caption, slashfiles=media)

    @commands.hybrid_command(name="caption", aliases=["cap"])
    async def captioncommand(self, ctx, *, caption: str, media: discord.Attachment | None = None):
        """
        Captions media.

        :param ctx: discord context
        :param caption: The caption text.
        :param media: A video, gif, or image.
        """
        await process(ctx, processing.vips.vipsutils.generic_caption_stack, [[VIDEO, GIF, IMAGE]],
                      processing.vips.caption.mediaforge_caption, [caption], slashfiles=media)

    @commands.hybrid_command(aliases=["imstuff"])
    async def stuff(self, ctx, *, caption: str, media: discord.Attachment | None = None):
        """
        Captions media in the style of the "i'm stuff" meme

        :param ctx: discord context
        :param caption: The caption text.
        :param media: A video, gif, or image.
        """
        await process(ctx, processing.vips.vipsutils.generic_caption_stack, [[VIDEO, GIF, IMAGE]],
                      processing.vips.caption.generic_image_caption, [caption], "rendering/images/Stuff.PNG",
                      reverse=True, slashfiles=media)

    @commands.hybrid_command(aliases=["eminemcaption", "eminemcap"])
    async def eminem(self, ctx, *, caption: str, media: discord.Attachment | None = None):
        """
        Eminem says something below your media.

        :param ctx: discord context
        :param caption: The caption text.
        :param media: A video, gif, or image.
        """
        await process(ctx, processing.vips.vipsutils.generic_caption_stack, [[VIDEO, GIF, IMAGE]],
                      processing.vips.caption.generic_image_caption, [caption], "rendering/images/eminem.png",
                      reverse=True, slashfiles=media)

    @commands.hybrid_command(aliases=["peter", "peterexplain", "petersay", "petergriffinexplain", "petergriffinsay"])
    async def petergriffin(self, ctx, *, caption: str, media: discord.Attachment | None = None):
        """
        Peter Griffin says something below your media.

        :param ctx: discord context
        :param caption: The caption text.
        :param media: A video, gif, or image.
        """
        await process(ctx, processing.vips.vipsutils.generic_caption_stack, [[VIDEO, GIF, IMAGE]],
                      processing.vips.caption.generic_image_caption, [caption], "rendering/images/Peter_Griffin.png",
                      reverse=True, slashfiles=media)

    @commands.hybrid_command()
    async def imagecaption(self, ctx, *, caption: str, media: discord.Attachment | None = None,
                           image: discord.Attachment | None = None):
        """
        a custom image of your choice says something below your media.

        :param ctx: discord context
        :param caption: The caption text.
        :param media: A video, gif, or image.
        :param image: An image that will say something.
        """

        async def func(media, image, gic, caption):
            # generic_image_caption takes params in a different order than process can natively provide, so we have to rearrange
            return await processing.vips.vipsutils.generic_caption_stack(media, gic, caption, image, reverse=True)

        await process(ctx, func, [[VIDEO, GIF, IMAGE], [IMAGE]], processing.vips.caption.generic_image_caption,
                      [caption], slashfiles=[media, image])

    @commands.hybrid_command(aliases=["bottomcap", "botcap"])
    async def bottomcaption(self, ctx, *, caption: str, media: discord.Attachment | None = None):
        """
        Captions underneath media.

        :param ctx: discord context
        :param caption: The caption text.
        :param media: A video, gif, or image.
        """
        await process(ctx, processing.vips.vipsutils.generic_caption_stack, [[VIDEO, GIF, IMAGE]],
                      processing.vips.caption.mediaforge_caption, [caption], reverse=True, slashfiles=media)

    @commands.hybrid_command(aliases=["esm", "&caption", "essemcaption", "esmbotcaption", "esmcap"])
    async def esmcaption(self, ctx, *, caption: str, media: discord.Attachment | None = None):
        """
        Captions media in the style of Essem's esmBot.

        :param ctx: discord context
        :param caption: The caption text.
        :param media: A video, gif, or image.
        """
        await process(ctx, processing.vips.vipsutils.generic_caption_stack, [[VIDEO, GIF, IMAGE]],
                      processing.vips.caption.esmcaption, [caption], slashfiles=media)

    @commands.hybrid_command(aliases=["twitter", "twitcap", "twittercap"])
    async def twittercaption(self, ctx, *, caption: str, media: discord.Attachment | None = None):
        """
        Captions media in the style of a Twitter screenshot.

        :param ctx: discord context
        :param caption: The caption text.
        :param media: A video, gif, or image.
        """
        await process(ctx, processing.ffmpeg.caption.twitter_caption, [[VIDEO, GIF, IMAGE]], [caption], False,
                      slashfiles=media)

    @commands.hybrid_command(aliases=["twitterdark", "twitcapdark", "twittercapdark"])
    async def twittercaptiondark(self, ctx, *, caption: str, media: discord.Attachment | None = None):
        """
        Captions media in the style of a dark mode Twitter screenshot.

        :param ctx: discord context
        :param caption: The caption text.
        :param media: A video, gif, or image.
        """
        await process(ctx, processing.ffmpeg.caption.twitter_caption, [[VIDEO, GIF, IMAGE]], [caption], True,
                      slashfiles=media)

    @commands.hybrid_command()
    async def freezemotivate(self, ctx, *, caption: str, video: discord.Attachment | None = None):
        """
        Ends video with a freeze frame from $motivate.

        :param ctx: discord context
        :param caption: The caption text.
        :param video: A video or gif.
        """
        caption = caption.split("|")
        if len(caption) == 1:
            caption.append("")
        await process(ctx, processing.ffmpeg.caption.freezemotivate, [[VIDEO, GIF]], *caption, slashfiles=video)

    @commands.hybrid_command()
    async def freezemotivateaudio(self, ctx, *, caption: str, video: discord.Attachment | None = None,
                                  audio: discord.Attachment | None = None):
        # TODO: merge this into freezemotivate
        """
        Ends video with a freeze frame from $motivate with custom audio.

        :param ctx: discord context
        :param caption: The caption text.
        :param video: A video or gif.
        :param audio: An audio file.
        """
        caption = caption.split("|")
        if len(caption) == 1:
            caption.append("")
        await process(ctx, processing.ffmpeg.caption.freezemotivateaudio, [[VIDEO, GIF], [AUDIO]], *caption,
                      slashfiles=[video, audio])
