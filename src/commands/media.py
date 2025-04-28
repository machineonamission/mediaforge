import typing

import discord
from discord.ext import commands

import config
import processing.ffmpeg.conversion
import processing.ffmpeg.handleanimated
import processing.other
import processing.vips.other
from core.process import process
from processing.mediatype import VIDEO, AUDIO, IMAGE, GIF


class Media(commands.Cog, name="Editing"):
    """
    Basic media editing/processing commands.
    """

    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(aliases=["copy", "nothing", "noop"])
    async def repost(self, ctx, media: discord.Attachment | None = None):
        """
        Reposts media as-is.

        :param ctx: discord context
        :param media: Any valid media.
        """
        await process(ctx, lambda x: x, [[VIDEO, IMAGE, GIF, AUDIO]], slashfiles=media)

    @commands.hybrid_command(aliases=["clean", "remake"])
    async def reencode(self, ctx, media: discord.Attachment | None = None):
        """
        Re-encodes media.
        Videos become libx264 mp4s, audio files become aac m4as, images become pngs.

        :param ctx: discord context
        :param media: A video, image, audio, or GIF file.
        """
        await process(ctx, processing.ffmpeg.conversion.allreencode, [[VIDEO, IMAGE, AUDIO, GIF]], slashfiles=media)

    @commands.hybrid_command(aliases=["audioadd", "dub"])
    async def addaudio(self, ctx, loops: commands.Range[int, -1, 100] = -1, media: discord.Attachment | None = None,
                       audio: discord.Attachment | None = None):
        """
        Adds audio to media.

        :param ctx: discord context
        :param loops: Amount of times to loop a gif. -1 loops infinitely, 0 only once. Must be between -1 and 100.
        :param media: Any valid media file.
        :param audio: An audio file.
        """
        await process(ctx, processing.ffmpeg.other.addaudio, [[IMAGE, GIF, VIDEO, AUDIO], [AUDIO]], loops,
                      slashfiles=[media, audio])

    @commands.hybrid_command()
    async def jpeg(self, ctx, strength: commands.Range[int, 1, 100] = 30,
                   stretch: commands.Range[int, 0, 40] = 20,
                   quality: commands.Range[int, 1, 95] = 10, media: discord.Attachment | None = None):
        """
        Makes media into a low quality jpeg

        :param ctx: discord context
        :param strength: amount of times to jpegify image. must be between 1 and 100.
        :param stretch: randomly stretch the image by up to this many pixels on each jpegification, simulates being reposted many
        times. set to 0 to disable. must be between 0 and 40.
        :param quality: quality of JPEG compression. must be between 1 and 95.
        :param media: An image, video, or GIF.
        """
        await process(ctx, processing.ffmpeg.other.handle_jpeg, [[IMAGE, VIDEO, GIF]], strength, stretch, quality,
                      slashfiles=media)

    @commands.hybrid_command()
    async def deepfry(self, ctx, brightness: commands.Range[float, -1, 1] = 0.5,
                      contrast: commands.Range[float, 0, 5] = 1.5,
                      sharpness: commands.Range[float, 0, 5] = 1.5,
                      saturation: commands.Range[float, 0, 3] = 1.5,
                      noise: commands.Range[float, 0, 100] = 20, media: discord.Attachment | None = None):
        """
        Applies many filters to the input to make it appear "deep-fried" in the style of deep-fried memes.


        :param ctx: discord context
        :param brightness: value of 0 makes no change to the image. must be between -1 and 1.
        :param contrast: value of 1 makes no change to the image. must be between 0 and 5.
        :param sharpness: value of 0 makes no change to the image. must be between 0 and 5.
        :param saturation: value of 1 makes no change to the image. must be between 0 and 3.
        :param noise: value of 0 makes no change to the image. must be between 0 and 100.
        :param media: A video, gif, or image.
        """
        await process(ctx, processing.ffmpeg.other.deepfry, [[VIDEO, GIF, IMAGE]], brightness, contrast,
                      sharpness,
                      saturation, noise, slashfiles=media)

    @commands.hybrid_command(aliases=["pad"])
    async def square(self, ctx, media: discord.Attachment | None = None):
        """
        Pads media into a square shape.

        :param ctx: discord context
        :param media: A video, gif, or image.
        """
        await process(ctx, processing.ffmpeg.other.pad, [[VIDEO, GIF, IMAGE]], slashfiles=media)

    @commands.hybrid_command(aliases=["size"])
    async def resize(self, ctx, width: int, height: int, media: discord.Attachment | None = None):
        """
        Resizes an image.

        :param ctx: discord context
        :param width: width of output image. set to -1 to determine automatically based on height and aspect ratio.
        :param height: height of output image. also can be set to -1.
        :param media: A video, gif, or image.
        """
        if not (1 <= width <= config.max_size or width == -1):
            raise commands.BadArgument(f"Width must be between 1 and "
                                       f"{config.max_size} or be -1.")
        if not (1 <= height <= config.max_size or height == -1):
            raise commands.BadArgument(f"Height must be between 1 and "
                                       f"{config.max_size} or be -1.")
        await process(ctx, processing.ffmpeg.ffutils.resize, [[VIDEO, GIF, IMAGE]], width, height, resize=False,
                      slashfiles=media)

    @commands.hybrid_command(aliases=["short", "kyle"])
    async def wide(self, ctx, media: discord.Attachment | None = None):
        """
        makes media twice as wide

        :param ctx: discord context
        :param media: A video, gif, or image.
        """
        await process(ctx, processing.ffmpeg.ffutils.resize, [[VIDEO, GIF, IMAGE]], "iw*2", "ih", slashfiles=media)

    @commands.hybrid_command(aliases=["tall", "long", "antikyle"])
    async def squish(self, ctx, media: discord.Attachment | None = None):
        """
        makes media twice as tall


        """
        await process(ctx, processing.ffmpeg.ffutils.resize, [[VIDEO, GIF, IMAGE]], "iw", "ih*2", slashfiles=media)

    @commands.hybrid_command(aliases=["magic", "magik", "contentawarescale", "liquidrescale"])
    async def magick(self, ctx, strength: commands.Range[int, 1, 99] = 50, media: discord.Attachment | None = None):
        """
        Apply imagemagick's liquid/"content-aware" scale to an image.
        This command is a bit slow.
        https://legacy.imagemagick.org/Usage/resize/#liquid-rescale

        :param ctx: discord context
        :param strength: how strongly to compress the image. smaller is stronger. output image will be strength% of
        the original size. must be between 1 and 99.
        :param media: An image, video, or GIF.
        """
        await process(ctx, processing.ffmpeg.handleanimated.animatedmultiplexer, [[IMAGE, VIDEO, GIF]],
                      processing.other.magickone, strength, slashfiles=media)

    @commands.hybrid_command(aliases=["repeat"], hidden=True)
    async def loop(self, ctx):
        """see $gifloop or $videoloop"""
        await ctx.reply("MediaForge has 2 loop commands.\nUse `$gifloop` to change/limit the amount of times a GIF "
                        "loops. This ONLY works on GIFs.\nUse `$videoloop` to loop a video. This command "
                        "duplicates the video contents.")

    @commands.hybrid_command(aliases=["gloop"])
    async def gifloop(self, ctx, loop: commands.Range[int, -1] = 0, gif: discord.Attachment | None = None):
        """
        Changes the amount of times a gif loops
        See $videoloop for videos.

        :param ctx: discord context
        :param loop: number of times to loop. -1 for no loop, 0 for infinite loop.
        :param gif: A gif.
        """

        await process(ctx, processing.ffmpeg.other.gifloop, [[GIF]], loop, slashfiles=gif)

    @commands.hybrid_command(aliases=["vloop", "contentloop"])
    async def videoloop(self, ctx, loop: commands.Range[int, 1, 15] = 1, video: discord.Attachment | None = None):
        """
        Loops a video
        See $gifloop for gifs.

        :param ctx: discord context
        :param loop: number of times to loop.
        :param video: A video.
        """
        await process(ctx, processing.ffmpeg.other.videoloop, [[VIDEO, AUDIO]], loop, slashfiles=video)

    @commands.hybrid_command(aliases=["flip", "rot"])
    async def rotate(self, ctx, rottype: typing.Literal["90", "90ccw", "180", "vflip", "hflip"],
                     media: discord.Attachment | None = None):
        """
        Rotates and/or flips media

        :param ctx: discord context
        :param rottype: 90: 90° clockwise, 90ccw: 90° counter clockwise, 180: 180°, vflip: vertical flip, hflip:
        horizontal flip
        :param media: A video, gif, or image.
        """
        await process(ctx, processing.ffmpeg.other.rotate, [[GIF, IMAGE, VIDEO]], rottype, slashfiles=media)

    @commands.hybrid_command()
    async def hue(self, ctx, h: float, media: discord.Attachment | None = None):
        """
        Change the hue of media.
        see https://ffmpeg.org/ffmpeg-filters.html#hue

        :param ctx: discord context
        :param h: The hue angle as a number of degrees.
        :param media: A video, gif, or image.
        """
        await process(ctx, processing.ffmpeg.other.hue, [[GIF, IMAGE, VIDEO]], h, slashfiles=media)

    @commands.hybrid_command(aliases=["color", "recolor"])
    async def tint(self, ctx, color: discord.Color, media: discord.Attachment | None = None):
        """
        Tint media to a color.
        This command first makes the image grayscale, then replaces white with your color.
        The resulting image should be nothing but shades of your color.

        :param ctx: discord context
        :param color: The hex or RGB color to tint to.
        :param media: A video, gif, or image.
        """
        await process(ctx, processing.ffmpeg.other.tint, [[GIF, IMAGE, VIDEO]], color, slashfiles=media)

    @commands.hybrid_command(aliases=["roundedcorners", "roundcrop", "round"])
    async def roundcorners(self, ctx, radius: int = 10, media: discord.Attachment | None = None):
        """
        Round corners of media
        see https://developer.mozilla.org/en-US/docs/Web/CSS/border-radius

        :param ctx: discord context
        :param radius: the size of the rounded corners in pixels
        :param media: A video, gif, or image.
        """
        if not 0 <= radius:
            raise commands.BadArgument(f"Border radius percent must be above 0")
        await process(ctx, processing.ffmpeg.other.round_corners, [[GIF, IMAGE, VIDEO]], radius, slashfiles=media)

    @commands.hybrid_command(aliases=["circlecrop"])
    async def circle(self, ctx, media: discord.Attachment | None = None):
        """
        Crops media into a circle
        :param ctx: discord context
        :param media: A video, gif, or image.
        """
        await process(ctx, processing.ffmpeg.other.circle, [[GIF, IMAGE, VIDEO]], slashfiles=media)

    @commands.hybrid_command()
    async def volume(self, ctx, volume: commands.Range[float, 0, 32], media: discord.Attachment | None = None):
        """
        Changes the volume of media.
        To make 2x as loud, use `$volume 2`.
        This command changes *perceived loudness*, not the raw audio level.
        WARNING: ***VERY*** LOUD AUDIO CAN BE CREATED

        :param ctx: discord context
        :param volume: number to multiply the perceived audio level by. Must be between 0 and 32.
        :param media: A video or audio file.
        """
        if not 0 <= volume <= 32:
            raise commands.BadArgument(f"{config.emojis['warning']} Volume must be between 0 and 32.")
        await process(ctx, processing.ffmpeg.other.volume, [[VIDEO, AUDIO]], volume, slashfiles=media)

    @commands.hybrid_command()
    async def mute(self, ctx, media: discord.Attachment | None = None):
        """
        alias for $volume 0

        :param ctx: discord context
        :param media: A video or audio file.
        """
        await process(ctx, processing.ffmpeg.other.volume, [[VIDEO, AUDIO]], 0, slashfiles=media)

    @commands.hybrid_command()
    async def vibrato(self, ctx, frequency: commands.Range[float, 0.1, 20000.0] = 5,
                      depth: commands.Range[float, 0, 1] = 1, media: discord.Attachment | None = None):
        """
        Applies a "wavy pitch"/vibrato effect to audio.
        officially described as "Sinusoidal phase modulation"
        see https://ffmpeg.org/ffmpeg-filters.html#tremolo

        :param ctx: discord context
        :param frequency: Modulation frequency in Hertz. must be between 0.1 and 20000.
        :param depth: Depth of modulation as a percentage. must be between 0 and 1.
        :param media: A video or audio file.
        """
        await process(ctx, processing.ffmpeg.other.vibrato, [[VIDEO, AUDIO]], frequency, depth, slashfiles=media)

    @commands.hybrid_command()
    async def pitch(self, ctx, numofhalfsteps: commands.Range[float, -12, 12] = 12,
                    media: discord.Attachment | None = None):
        """
        Changes pitch of audio

        :param ctx: discord context
        :param numofhalfsteps: the number of half steps to change the pitch by. `12` raises the pitch an octave and
        `-12` lowers the pitch an octave. must be between -12 and 12.
        :param media: A video or audio file.
        """
        if not -12 <= numofhalfsteps <= 12:
            raise commands.BadArgument(f"numofhalfsteps must be between -12 and 12.")
        await process(ctx, processing.ffmpeg.other.pitch, [[VIDEO, AUDIO]], numofhalfsteps, slashfiles=media)

    @commands.hybrid_command(aliases=["concat", "combinev"])
    async def concatv(self, ctx, media1: discord.Attachment | None = None, media2: discord.Attachment | None = None):
        """
        Makes one video file play right after another.
        The output video will take on all of the settings of the FIRST video.
        The second video will be scaled to fit.

        :param ctx: discord context
        :param media1: A video or gif.
        :param media2: A video or gif.
        """
        await process(ctx, processing.ffmpeg.other.concatv, [[VIDEO, GIF], [VIDEO, GIF]], slashfiles=[media1, media2])

    @commands.hybrid_command()
    async def hstack(self, ctx, media1: discord.Attachment | None = None, media2: discord.Attachment | None = None):
        """
        Stacks 2 videos horizontally

        :param ctx: discord context
        :param video1: A video, image, or gif.
        :param video2: A video, image, or gif.
        """
        await process(ctx, processing.ffmpeg.other.stack, [[VIDEO, GIF, IMAGE], [VIDEO, GIF, IMAGE]],
                      "hstack", slashfiles=[media1, media2])

    @commands.hybrid_command()
    async def vstack(self, ctx, media1: discord.Attachment | None = None, media2: discord.Attachment | None = None):
        """
        Stacks 2 videos horizontally

        :param ctx: discord context
        :param media1: A video, image, or gif.
        :param media2: A video, image, or gif.
        """
        await process(ctx, processing.ffmpeg.other.stack, [[VIDEO, GIF, IMAGE], [VIDEO, GIF, IMAGE]],
                      "vstack", slashfiles=[media1, media2])

    @commands.hybrid_command(aliases=["blend"])
    async def overlay(self, ctx, alpha: commands.Range[float, 0, 1] = 0.5, media1: discord.Attachment | None = None,
                      media2: discord.Attachment | None = None):
        """
        Overlays the second input over the first

        :param ctx: discord context
        :param alpha: the alpha (transparency) of the top video. must be between 0 and 1.
        :param media1: A video or gif.
        :param media2: A video or gif.
        """
        await process(ctx, processing.ffmpeg.other.overlay, [[VIDEO, GIF, IMAGE], [VIDEO, GIF, IMAGE]],
                      alpha,
                      "overlay", slashfiles=[media1, media2])

    @commands.hybrid_command(aliases=["overlayadd", "addition"])
    async def add(self, ctx, media1: discord.Attachment | None = None, media2: discord.Attachment | None = None):
        """
        Adds the pixel values of the second video to the first.

        :param ctx: discord context
        :param media1: A video or gif.
        :param media2: A video or gif.
        """
        await process(ctx, processing.ffmpeg.other.overlay, [[VIDEO, GIF, IMAGE], [VIDEO, GIF, IMAGE]], 1,
                      "add", slashfiles=[media1, media2])

    @commands.hybrid_command(name="speed")
    async def spcommand(self, ctx, speed: commands.Range[float, 0.25, 100.0] = 2,
                        media: discord.Attachment | None = None):
        """
        Changes the speed of media.
        This command preserves the original FPS, which means speeding up will drop frames. See $fps.

        :param ctx: discord context
        :param speed: Multiplies input video speed by this number. must be between 0.25 and 100.
        :param media: A video, gif, or audio.
        """
        await process(ctx, processing.ffmpeg.other.speed, [[VIDEO, GIF, AUDIO]], speed, slashfiles=media)

    @commands.hybrid_command(aliases=["shuffle", "stutter", "nervous"])
    async def random(self, ctx, frames: commands.Range[int, 2, 512] = 30, media: discord.Attachment | None = None):
        """
        Shuffles the frames of a video around.
        Currently, this command does NOT apply to audio. This is an FFmpeg limitation.
        see https://ffmpeg.org/ffmpeg-filters.html#random

        :param ctx: discord context
        :param frames: Set size in number of frames of internal cache. must be between 2 and 512. default is 30.
        :param media: A video or gif.
        """
        await process(ctx, processing.ffmpeg.other.random, [[VIDEO, GIF]], frames, slashfiles=media)

    @commands.hybrid_command()
    async def reverse(self, ctx, media: discord.Attachment | None = None):
        """
        Reverses media.

        :param ctx: discord context
        :param media: A video or gif.
        """
        await process(ctx, processing.ffmpeg.other.reverse, [[VIDEO, GIF]], slashfiles=media)

    @commands.hybrid_command(aliases=["compress", "quality", "lowerquality", "crf", "qa"])
    async def compressv(self, ctx, crf: commands.Range[float, 28, 51] = 51,
                        qa: commands.Range[float, 10, 112] = 20, media: discord.Attachment | None = None):
        """
        Makes videos terrible quality.
        The strange ranges on the numbers are because they are quality settings in FFmpeg's encoding.
        CRF info is found at https://trac.ffmpeg.org/wiki/Encode/H.264#crf
        audio quality info is found under https://trac.ffmpeg.org/wiki/Encode/AAC#fdk_cbr

        :param ctx: discord context
        :param crf: Controls video quality. Higher is worse quality. must be between 28 and 51.
        :param qa: Audio bitrate in kbps. Lower is worse quality. Must be between 10 and 112.
        :param video: A video or gif.
        """
        await process(ctx, processing.ffmpeg.other.quality, [[VIDEO, GIF]], crf, qa)

    @commands.hybrid_command(name="fps")
    async def fpschange(self, ctx, fps: commands.Range[float, 1, 60], media: discord.Attachment | None = None):
        """
        Changes the FPS of media.
        This command keeps the speed the same.
        BEWARE: Changing the FPS of gifs can create strange results due to the strange way GIFs store FPS data.
        GIFs are only stable at certain FPS values. These include 50, 30, 15, 10, and others.
        An important reminder that by default tenor "gifs" are interpreted as mp4s,
        which do not suffer this problem.

        :param ctx: discord context
        :param fps: Frames per second of the output. must be between 1 and 60.
        :param media: A video or gif.
        """
        await process(ctx, processing.ffmpeg.other.changefps, [[VIDEO, GIF]], fps, slashfiles=media)

    @commands.hybrid_command(aliases=["negate", "opposite"])
    async def invert(self, ctx, media: discord.Attachment | None = None):
        """
        Inverts colors of media

        :param ctx: discord context
        :param media: A video, gif, or image.
        """
        await process(ctx, processing.ffmpeg.other.invert, [[VIDEO, GIF, IMAGE]], slashfiles=media)

    @commands.hybrid_command()
    async def trim(self, ctx, length: commands.Range[float, 0, None],
                   start: commands.Range[float, 0, None] = 0, media: discord.Attachment | None = None):
        """
        Trims media.

        :param ctx: discord context
        :param length: Length in seconds to trim the media to.
        :param start: Time in seconds to start the trimmed media at.
        :param media: A video, gif, or audio file.
        """
        await process(ctx, processing.ffmpeg.ffutils.trim, [[VIDEO, GIF, AUDIO]], length, start, slashfiles=media)

    @commands.hybrid_command(aliases=["uncap", "nocaption", "nocap", "rmcap", "removecaption", "delcap", "delcaption",
                                      "deletecaption", "trimcap", "trimcaption"])
    async def uncaption(self, ctx, frame_to_try: int = 0, threshold: commands.Range[float, 0, 255] = 10,
                        media: discord.Attachment | None = None):
        """
        try to remove esm/default style captions from media
        scans the leftmost column of pixels on one frame to attempt to determine where the caption is.

        :param ctx:
        :param frame_to_try: which frame to run caption detection on. -1 uses the last frame.
        :param threshold: a number 0-255 how similar the caption background must be to white
        :param media: A video, image, or gif
        """
        await process(ctx, processing.vips.other.uncaption, [[VIDEO, IMAGE, GIF]], frame_to_try, threshold,
                      slashfiles=media)

    @commands.hybrid_command()
    async def speechbubble(self, ctx, position: typing.Literal["top", "bottom"] = "top",
                           color: typing.Literal["transparent", "white", "black"] = "transparent",
                           media: discord.Attachment | None = None):
        """
        gives an image a speech bubble

        :param ctx:
        :param position: where to put the speech bubble. must be "top" or "bottom".
        :param color: what color to make the speech bubble. must be "transparent", "white", or "black".
        :param media: A video, image, or GIF file
        """
        await process(ctx, processing.ffmpeg.other.speech_bubble, [[VIDEO, IMAGE, GIF]], position, color,
                      slashfiles=media)
