import typing

import pyvips

from config import temp_vipscodec
from processing.vips.vipsutils import escape
from processing.vips.vipsutils import normalize, vips_text
from utils.tempfiles import reserve_tempfile


def yskysn(captions: typing.Sequence[str]):
    # load stuff
    im = normalize(pyvips.Image.new_from_file("rendering/images/yskysn.png"))
    # here for my sanity, dimensions of text area
    w = 500
    h = 582
    # generate text
    text_prerender, autofit_dict = vips_text(
        f"<span foreground='white'>"
        f"{escape(captions[0].upper())}\n<span size='150%'>{escape(captions[1].upper())}</span>"
        f"</span>",
        font=f"Tahoma",
        style="Bold 56",
        fontfile="rendering/fonts/TAHOMABD.TTF",
        align=pyvips.Align.CENTRE,
        width=w,
        height=h,
        autofit_dpi=True,
        wrap=pyvips.TextWrap.WORD_CHAR
    )
    autofit_dpi = autofit_dict["autofit_dpi"]
    if autofit_dpi <= 72:
        text = text_prerender
    else:
        # generate text
        text = vips_text(
            f"<span foreground='white'>"
            f"{escape(captions[0].upper())}\n<span size='150%'>{escape(captions[1].upper())}</span>"
            f"</span>",
            font=f"Tahoma",
            style="Bold 56",
            fontfile="rendering/fonts/TAHOMABD.TTF",
            align=pyvips.Align.CENTRE,
            width=w,
            height=h,
            dpi=72,
            wrap=pyvips.TextWrap.WORD_CHAR
        )
    # pad to expected size, 48 is margin
    text = text.gravity(pyvips.CompassDirection.CENTRE, w + 48, h + 48, extend=pyvips.Extend.BLACK)
    # add glow, similar technique to shadow
    mask = pyvips.Image.gaussmat(5 / 2, 0.0001, separable=True)
    glow = text[3].convsep(mask).cast(pyvips.BandFormat.UCHAR)
    glow = glow.new_from_image((255, 255, 255)) \
        .bandjoin(glow) \
        .copy(interpretation=pyvips.Interpretation.SRGB)

    text = glow.composite2(text, pyvips.BlendMode.OVER)

    out = im.composite2(text, pyvips.BlendMode.OVER)
    # save and return
    outfile = reserve_tempfile(temp_vipscodec)
    out.write_to_file(outfile)
    return outfile


def f1984(captions: typing.Sequence[str]):
    originaldate = captions[1].lower() == "january 1984"

    if originaldate:
        im = normalize(pyvips.Image.new_from_file("rendering/images/1984/1984originaldate.png"))
    else:
        im = normalize(pyvips.Image.new_from_file("rendering/images/1984/1984.png"))

    # generate text
    speech_bubble = vips_text(
        escape(captions[0]),
        font=f"Atkinson Hyperlegible",
        style="Bold",
        fontfile="rendering/fonts/AtkinsonHyperlegible-Bold.ttf",
        align=pyvips.Align.CENTRE,
        width=290,
        height=90,
        wrap=pyvips.TextWrap.WORD_CHAR
    )
    # pad to expected size
    speech_bubble = speech_bubble.gravity(pyvips.CompassDirection.CENTRE, 290, 90, extend=pyvips.Extend.BLACK)
    # add speech bubble
    im = im.composite2(speech_bubble, pyvips.BlendMode.OVER, x=60, y=20)

    if not originaldate:
        # generate text
        date = vips_text(
            escape(captions[1].upper()),
            font=f"ImpactMix",
            fontfile="rendering/fonts/ImpactMix.ttf",
            align=pyvips.Align.CENTRE,
            width=124,
            height=34,
            wrap=pyvips.TextWrap.WORD_CHAR
        )
        # pad to expected size
        date = date.gravity(pyvips.CompassDirection.CENTRE, 124, 34, extend=pyvips.Extend.BLACK)
        # equivelant to skewY(10deg)
        date = date.affine([1, 0, 0.176327, 1])
        # add date
        im = im.composite2(date, pyvips.BlendMode.OVER, x=454, y=138)
        # add cover
        im = im.composite2(normalize(pyvips.Image.new_from_file("rendering/images/1984/1984cover.png")),
                           pyvips.BlendMode.OVER)

    outfile = reserve_tempfile(temp_vipscodec)
    im.write_to_file(outfile)
    return outfile


def epicbirthdaytext(caption: str):
    # generate text
    text = vips_text(
        f"<span foreground=\"white\">{escape(caption.upper())}</span>",
        font=f"MarkerFeltWide",
        fontfile="rendering/fonts/MarkerFeltWide Regular.ttf",
        align=pyvips.Align.CENTRE,
        width=540,
        height=260,
        wrap=pyvips.TextWrap.WORD_CHAR
    )
    outfile = reserve_tempfile(temp_vipscodec)
    text.write_to_file(outfile)
    return outfile


def heartlockettext(caption: str):
    caption = escape(caption)

    # generate text
    out = vips_text(
        caption,
        font=f"Arial",
        style="0.225",
        fontfile="rendering/fonts/arial.ttf",
        align=pyvips.Align.CENTRE,
        width=384,
        height=384,
        wrap=pyvips.TextWrap.WORD_CHAR
    )
    # overlay white background
    out = out.composite((255, 255, 255, 255), mode=pyvips.BlendMode.DEST_OVER)
    # pad text to image width
    out = out.gravity(pyvips.CompassDirection.CENTRE, 384, 384, extend=pyvips.Extend.WHITE)
    outfile = reserve_tempfile(temp_vipscodec)
    out.write_to_file(outfile)
    return outfile
