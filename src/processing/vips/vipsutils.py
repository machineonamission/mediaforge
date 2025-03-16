import dataclasses
import typing

import pyvips

import processing.ffmpeg.ffprobe
from processing.common import run_parallel
from utils.tempfiles import reserve_tempfile


@dataclasses.dataclass
class ImageSize:
    width: int
    height: int


async def generic_caption_stack(media, capfunc: callable, captions: typing.Sequence[str], *args, reverse=False):
    size = ImageSize(*await processing.ffmpeg.ffprobe.get_resolution(media))
    captext = await run_parallel(capfunc, *args, captions, size)
    vargs = (media, captext) if reverse else (captext, media)
    return await processing.ffmpeg.ffutils.naive_vstack(*vargs)


async def generic_caption_overlay(media: str, capfunc: callable, captions: typing.Sequence[str], *args):
    size = ImageSize(*await processing.ffmpeg.ffprobe.get_resolution(media))
    captext = await run_parallel(capfunc, captions, size, *args)
    return await processing.ffmpeg.ffutils.naive_overlay(media, captext)


def glib_escape(arg: str) -> str:
    # https://github.com/bratsche/glib/blob/abfef39da9a11f59051dfa23a50bc374c0b8ad6e/glib/gmarkup.c#L2110-L2128
    return (
        arg
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("\\", "&apos;")
        .replace("'", "&quot;")
    )


def escape(arg: str | typing.Sequence[str]):
    if isinstance(arg, str):
        return glib_escape(arg)
    else:
        return [glib_escape(s) for s in arg]


def outline(image: pyvips.Image, radius: int | float | None = None,
            color: typing.Sequence[int] | None = None) -> pyvips.Image:
    if color is None:
        color = [0, 0, 0]
    if radius is None:
        radius = image.width / 1000
    if radius <= 1:
        radius = 1
    # dilate the text with a squared-off gaussian mask
    # https://github.com/libvips/libvips/discussions/2123#discussioncomment-3950916
    mask = pyvips.Image.gaussmat(radius / 2, 0.0001, separable=True)
    mask *= 10
    shadow = image[3].convsep(mask).cast(pyvips.BandFormat.UCHAR)
    # recolor shadow
    shadow = shadow.new_from_image(color) \
        .bandjoin(shadow) \
        .copy(interpretation=pyvips.Interpretation.SRGB)
    # composite
    text = shadow.composite2(image, pyvips.BlendMode.OVER)
    return text


def overlay_in_middle(background: pyvips.Image, foreground: pyvips.Image) -> pyvips.Image:
    return background.composite2(foreground, pyvips.BlendMode.OVER,
                                 x=((background.width - foreground.width) // 2),
                                 y=((background.height - foreground.height) // 2))


def naive_stack(file0, file1):
    # load files
    im0 = normalize(pyvips.Image.new_from_file(file0))
    im1 = normalize(pyvips.Image.new_from_file(file1))
    # stack
    out = im0.join(im1, pyvips.Direction.VERTICAL, expand=True, align=pyvips.Align.CENTRE)
    # save
    outfile = reserve_tempfile("bmp")
    out.write_to_file(outfile)

    return outfile


def stack(file0, file1, style):
    # load files
    im0 = normalize(pyvips.Image.new_from_file(file0))
    im1 = normalize(pyvips.Image.new_from_file(file1))
    # resize im1 to fit im2
    if style == "vstack":
        im1 = im1.resize(im0.width / im1.width)
    else:
        im1 = im1.resize(im0.height / im1.height)
    # stack
    out = im0.join(im1, pyvips.Direction.VERTICAL if style == "vstack" else pyvips.Direction.HORIZONTAL, expand=True,
                   align=pyvips.Align.CENTRE)
    # save
    outfile = reserve_tempfile("bmp")
    out.write_to_file(outfile)

    return outfile


def resize(img: pyvips.Image, width: int, height: int) -> pyvips.Image:
    return img.resize(width / img.width, vscale=height / img.height)


def normalize(img: pyvips.Image) -> pyvips.Image:
    # mono -> rgb
    if img.bands < 3:
        img = img.colourspace("srgb")
    # make sure there's an alpha
    if img.bands == 3:
        img = img.bandjoin(255)

    return img


def vips_text(intext: str, *args, font: str, style: str = "", **kwargs):
    # weird syntax for adding extra font files
    # adds noto for multi script support font
    out = pyvips.Image.text(".", fontfile="rendering/fonts/NotoSans.ttf")
    # adds twemoji font for emojis
    out = pyvips.Image.text(".", fontfile="rendering/fonts/TwemojiCOLR0.otf")
    # generate text
    out = pyvips.Image.text(
        intext,
        font=f"{font},Twemoji Color Emoji,Noto Sans{f' {style}' if style else ''}",
        rgba=True,
        *args,
        **kwargs
    )
    return out
