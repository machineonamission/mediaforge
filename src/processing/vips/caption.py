import math
import typing

import pyvips

from processing.common import image_format
from processing.vips.vipsutils import ImageSize, escape, outline, overlay_in_middle, vips_text
from processing.vips.vipsutils import normalize
from utils.tempfiles import reserve_tempfile

twemoji = "rendering/fonts/TwemojiCOLR0.otf"


def esmcaption(captions: typing.Sequence[str], size: ImageSize):
    captions = escape(captions)
    # https://github.com/esmBot/esmBot/blob/121615df63bdcff8ee42330d8a67a33a18bb463b/natives/caption.cc#L28-L50
    # constants used by esmbot
    fontsize = size.width / 10
    textwidth = size.width * .92
    # generate text
    out = vips_text(
        captions[0],
        font=f"FuturaExtraBlackCondensed",
        style=f"Black {fontsize}px",
        fontfile="rendering/fonts/caption.otf",
        align=pyvips.Align.CENTRE,
        width=textwidth,
        wrap=pyvips.TextWrap.WORD_CHAR
    )
    # overlay white background
    out = out.composite((255, 255, 255, 255), mode=pyvips.BlendMode.DEST_OVER)
    # pad text to image width
    out = out.gravity(pyvips.CompassDirection.CENTRE, size.width, out.height + fontsize, extend=pyvips.Extend.WHITE)
    # save and return
    # because it's run in executor, tempfiles
    outfile = reserve_tempfile(image_format)
    out.write_to_file(outfile)
    return outfile


def mediaforge_caption(captions: typing.Sequence[str], size: ImageSize):
    captions = escape(captions)
    # https://github.com/esmBot/esmBot/blob/121615df63bdcff8ee42330d8a67a33a18bb463b/natives/caption.cc#L28-L50
    # constants used by esmbot
    fontsize = size.width / 10
    textwidth = size.width * .92
    # generate text
    out = vips_text(
        captions[0],
        font=f"Atkinson Hyperlegible",
        style=f"Bold {fontsize}px",
        fontfile="rendering/fonts/AtkinsonHyperlegible-Bold.ttf",
        align=pyvips.Align.CENTRE,
        width=textwidth,
        wrap=pyvips.TextWrap.WORD_CHAR
    )
    # overlay white background
    out = out.composite((255, 255, 255, 255), mode=pyvips.BlendMode.DEST_OVER)
    # pad text to image width
    out = out.gravity(pyvips.CompassDirection.CENTRE, size.width, out.height + fontsize, extend=pyvips.Extend.WHITE)
    # save and return
    # because it's run in executor, tempfiles
    outfile = reserve_tempfile(image_format)
    out.write_to_file(outfile)
    return outfile


def motivate_text(captions: typing.Sequence[str], size: ImageSize):
    captions = escape(captions)
    textsize = size.width / 5

    # its verbose but it exactly matches the code in ffmpeg.caption.motivate
    width, height = size.width, size.height

    pad1_w = width + width // 60
    pad1_h = height + width // 60

    pad2_w = pad1_w + width // 30
    pad2_h = pad1_h + width // 30

    pad3_w = pad2_w
    pad3_h = pad2_h + width // 30

    width, height = pad3_w, pad3_h

    toptext = None
    bottomtext = None
    if captions[0]:
        # generate text
        toptext = vips_text(
            f"<span foreground=\"white\">{captions[0]}</span>",
            font=f"Times New Roman Cyr",
            style=f"{textsize}px",
            fontfile="rendering/fonts/times new roman.ttf",
            align=pyvips.Align.CENTRE,
            width=width,
            wrap=pyvips.TextWrap.WORD_CHAR
        )
        toptext = toptext.gravity(pyvips.CompassDirection.CENTRE, width, toptext.height + (textsize / 4),
                                  extend=pyvips.Extend.BLACK)
    if captions[1]:
        # generate text
        bottomtext = vips_text(
            f"<span foreground=\"white\">{captions[1]}</span>",
            font=f"Times New Roman Cyr",
            style=f"{int(textsize * 0.4)}px",
            fontfile="rendering/fonts/times new roman.ttf",
            align=pyvips.Align.CENTRE,
            width=width,
            wrap=pyvips.TextWrap.WORD_CHAR
        )
        bottomtext = bottomtext.gravity(pyvips.CompassDirection.CENTRE, width,
                                        bottomtext.height + (textsize / 4),
                                        extend=pyvips.Extend.BLACK)
    if toptext and bottomtext:
        out = toptext.join(bottomtext, pyvips.Direction.VERTICAL, expand=True, background=[0, 0, 0, 255],
                           align=pyvips.Align.CENTRE)
    else:
        if toptext:
            out = toptext
        elif bottomtext:
            out = bottomtext
        else:  # shouldnt happen but why not
            raise Exception("missing toptext and bottomtext")
            # out = pyvips.Image.new_from_list([[0, 0, 0, 255]])
    # overlay black background
    out = out.composite2((0, 0, 0, 255), pyvips.BlendMode.DEST_OVER)
    # pad text to target width
    out = out.gravity(pyvips.CompassDirection.CENTRE, width, out.height, extend=pyvips.Extend.BACKGROUND,
                      background=[0, 0, 0, 255])
    outfile = reserve_tempfile(image_format)
    out.write_to_file(outfile)
    return outfile


def meme(captions: typing.Sequence[str], size: ImageSize):
    # blank image
    overlay = pyvips.Image.black(size.width, size.height).new_from_image([0, 0, 0, 0]).copy(
        interpretation=pyvips.enums.Interpretation.SRGB)

    if captions[0]:
        # generate text
        toptext = vips_text(
            f"<span foreground=\"white\">{escape(captions[0].upper())}</span>",
            font=f"ImpactMix",
            fontfile="rendering/fonts/ImpactMix.ttf",
            align=pyvips.Align.CENTRE,
            width=int(size.width * .95),
            height=int((size.height * .95) / 3),
            wrap=pyvips.TextWrap.WORD_CHAR
        )
        overlay = overlay.composite2(toptext, pyvips.BlendMode.OVER,
                                     x=((size.width - toptext.width) / 2),
                                     y=int(size.height * .025))
    if captions[1]:
        # generate text
        bottomtext = vips_text(
            f"<span foreground=\"white\">{escape(captions[1].upper())}</span>",
            font=f"ImpactMix",
            fontfile="rendering/fonts/ImpactMix.ttf",
            align=pyvips.Align.CENTRE,
            width=int(size.width * .95),
            height=int((size.height * .95) / 3),
            wrap=pyvips.TextWrap.WORD_CHAR
        )
        overlay = overlay.composite2(bottomtext, pyvips.BlendMode.OVER,
                                     x=((size.width - bottomtext.width) / 2),
                                     y=int((size.height * .975) - bottomtext.height))

    overlay = outline(overlay, overlay.width / 200)
    outfile = reserve_tempfile(image_format)
    overlay.write_to_file(outfile)
    return outfile


def tenor(captions: typing.Sequence[str], size: ImageSize):
    captions = escape(captions)
    # blank image
    overlay = pyvips.Image.black(size.width, size.height).new_from_image([0, 0, 0, 0]).copy(
        interpretation=pyvips.enums.Interpretation.SRGB)
    textsize = size.width // 10
    if captions[0]:
        # generate text
        toptext = vips_text(
            f"<span foreground=\"white\">{captions[0]}</span>",
            font=f"Ubuntu",
            style=f"{textsize}px",
            fontfile="rendering/fonts/Ubuntu-R.ttf",
            align=pyvips.Align.CENTRE,
            width=int(size.width * .95),
            height=int((size.height * .95) / 3),
            wrap=pyvips.TextWrap.WORD_CHAR
        )
        overlay = overlay.composite2(toptext, pyvips.BlendMode.OVER,
                                     x=((size.width - toptext.width) / 2),
                                     y=int(size.height * .025))
    if captions[1]:
        # generate text
        bottomtext = vips_text(
            f"<span foreground=\"white\">{captions[1]}</span>",
            font=f"Ubuntu",
            style=f"{textsize}px",
            fontfile="rendering/fonts/Ubuntu-R.ttf",
            align=pyvips.Align.CENTRE,
            width=int(size.width * .95),
            height=int((size.height * .95) / 3),
            wrap=pyvips.TextWrap.WORD_CHAR
        )
        overlay = overlay.composite2(bottomtext, pyvips.BlendMode.OVER,
                                     x=((size.width - bottomtext.width) / 2),
                                     y=int((size.height * .975) - bottomtext.height))

    overlay = outline(overlay, overlay.width / 250)
    outfile = reserve_tempfile(image_format)
    overlay.write_to_file(outfile)
    return outfile


def whisper(captions: typing.Sequence[str], size: ImageSize):
    captions = escape(captions)
    # blank image
    overlay = pyvips.Image.black(size.width, size.height).new_from_image([0, 0, 0, 0]).copy(
        interpretation=pyvips.enums.Interpretation.SRGB)

    # generate text
    text = vips_text(
        f"<span foreground=\"white\">{captions[0]}</span>",
        font=f"Upright",
        style=f"{size.width // 6}px",
        fontfile="rendering/fonts/whisper.otf",
        align=pyvips.Align.CENTRE,
        width=int(size.width * .95),
        height=int(size.height * .95),
        wrap=pyvips.TextWrap.WORD_CHAR
    )
    overlay = overlay_in_middle(overlay, text)

    overlay = outline(overlay, overlay.width / 175)
    outfile = reserve_tempfile(image_format)
    overlay.write_to_file(outfile)
    return outfile


def snapchat(captions: typing.Sequence[str], size: ImageSize):
    # generate text
    text = vips_text(
        f"<span foreground=\"white\">{captions[0]}</span>",
        font=f"Helvetica Neue",
        style=f"{size.width // 20}px",
        fontfile="rendering/fonts/HelveticaNeue.otf",
        align=pyvips.Align.CENTRE,
        width=int(size.width * .98),
        height=size.height // 3,
        wrap=pyvips.TextWrap.WORD_CHAR
    )
    # background
    bg = pyvips.Image.black(size.width, text.height + size.width // 25).new_from_image([0, 0, 0, 178]).copy(
        interpretation=pyvips.enums.Interpretation.SRGB)
    # overlay
    text = overlay_in_middle(bg, text)
    # pad to image size
    blank_bg = pyvips.Image.black(size.width, size.height).new_from_image([0, 0, 0, 0]).copy(
        interpretation=pyvips.enums.Interpretation.SRGB)
    # overlay
    out = overlay_in_middle(blank_bg, text)
    # save
    outfile = reserve_tempfile(image_format)
    out.write_to_file(outfile)
    return outfile


def generic_image_caption(image: str, captions: typing.Sequence[str], size: ImageSize):
    # constants used by esmbot
    fontsize = size.width / 10
    textwidth = size.width * (2 / 3) * .92

    # generate text
    out = vips_text(
        captions[0],
        font=f"Atkinson Hyperlegible",
        style=f"Bold {fontsize}px",
        fontfile="rendering/fonts/AtkinsonHyperlegible-Bold.ttf",
        align=pyvips.Align.CENTRE,
        width=textwidth,
        wrap=pyvips.TextWrap.WORD_CHAR
    )
    # load stuff
    im = normalize(pyvips.Image.new_from_file(image))

    # resize
    im = im.resize((size.width / 3) / im.width)
    # pad text to image width
    padded = out.gravity(pyvips.CompassDirection.CENTRE, size.width - im.width, max(out.height + fontsize, im.height),
                         extend=pyvips.Extend.BLACK)

    # join
    final = padded.join(im, pyvips.Direction.HORIZONTAL, expand=True, background=0xffffff)

    # overlay white background
    final = final.composite((255, 255, 255, 255), mode=pyvips.BlendMode.DEST_OVER)
    # save
    outfile = reserve_tempfile(image_format)
    final.write_to_file(outfile)
    return outfile


def twitter_text(captions: typing.Sequence[str], size: ImageSize, dark: bool):
    captions = escape(captions)
    fontsize = size.width / 20

    # generate text
    out = vips_text(
        f"<span foreground=\"{'white' if dark else 'black'}\">{captions[0]}</span>",
        font=f"TwitterChirp",
        style=f"{fontsize}px",
        fontfile="rendering/fonts/TwitterChirp.otf",
        align=pyvips.Align.LOW,
        width=size.width,
        wrap=pyvips.TextWrap.WORD_CHAR
    )
    # pad text to image width left aligned
    out = out.gravity(pyvips.CompassDirection.WEST, size.width, out.height + fontsize,
                      extend=pyvips.Extend.BLACK)
    # add padding
    out = out.gravity(pyvips.CompassDirection.CENTRE, size.width + math.floor(size.width * (12 / 500) * 2),
                      out.height,
                      extend=pyvips.Extend.BLACK)

    # save and return
    # because it's run in executor, tempfiles
    outfile = reserve_tempfile(image_format)
    out.write_to_file(outfile)
    return outfile
