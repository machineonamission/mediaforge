import typing

import config
import processing.common
from processing import vips as vips
from processing.ffmpeg.ffprobe import get_resolution, frame_n
from processing.ffmpeg.ffutils import gif_output
from processing.ffmpeg.other import imageaudio, concatv
from processing.run_command import run_command
from utils.tempfiles import reserve_tempfile


@gif_output
async def motivate(media, captions: typing.Sequence[str]):
    width, height = await get_resolution(media)
    text = await processing.common.run_parallel(vips.caption.motivate_text, captions,
                                                vips.vipsutils.ImageSize(width, height))
    outfile = reserve_tempfile("mkv")

    # do pixel math in python to guarantee no rounding issues
    wtext, htext = await get_resolution(text)

    pad1_w = width + width // 60
    pad1_h = height + width // 60
    pad1_x = width // 120
    pad1_y = width // 120

    pad2_w = pad1_w + width // 30
    pad2_h = pad1_h + width // 30
    pad2_x = width // 60
    pad2_y = width // 60

    pad3_w = pad2_w
    pad3_h = pad2_h + width // 30

    pad4_w = pad3_w + width // 5
    pad4_h = pad3_h + htext + width // 10 + width // 30
    pad4_x = width // 10
    pad4_y = width // 10

    await run_command("ffmpeg", "-i", media, "-i", text, "-filter_complex",
                      f"[0]format=rgba,"  # THIS IS CRUCIAL OR ELSE THE SIZE GETS ROUNDED TO NEAREST EVEN INTEGER
                      f"pad=w={pad1_w}:h={pad1_h}:x={pad1_x}:y={pad1_y}:color=black,"
                      f"pad=w={pad2_w}:h={pad2_h}:x={pad2_x}:y={pad2_y}:color=white,"
                      f"pad=w={pad3_w}:h={pad3_h}:x=0:y=0[i];"
                      f"[i][1]vstack=inputs=2,"
                      f"pad=w={pad4_w}:h={pad4_h}:x={pad4_x}:y={pad4_y}:color=black",
                      "-c:v", config.temp_vcodec, "-pix_fmt", config.temp_vpixfmt,
                      "-c:a", "copy", "-fps_mode", "vfr",
                      outfile)
    return outfile


async def freezemotivateaudio(video, audio, *caption):
    """
    ends video with motivate caption
    :param video: video
    :param audio: audio
    :param caption: caption to pass to motivate()
    :return: processed media
    """
    lastframe = await frame_n(video, -1)
    clastframe = await motivate(lastframe, caption)
    freezeframe = await imageaudio(clastframe, audio)
    final = await concatv(video, freezeframe)
    return final


async def freezemotivate(video, *caption):
    return await freezemotivateaudio(video, "rendering/what.mp3", *caption)


@gif_output
async def twitter_caption(media, captions, dark=True):
    # get_resolution call is separate so we can use for border radius
    width, height = await get_resolution(media)
    # get text
    text = await processing.common.run_parallel(vips.caption.twitter_text, captions,
                                                vips.vipsutils.ImageSize(width, height), dark)
    border_radius = width * (16 / 500)
    outfile = reserve_tempfile("mkv")
    await run_command("ffmpeg", "-i", media, "-i", text, "-filter_complex",
                      # round corners
                      # https://stackoverflow.com/a/62400465/9044183
                      # copied from round_corners here for efficiency as 1 ffmpeg stream
                      f"[0]format=rgba,"
                      f"geq=lum='p(X,Y)':a='"
                      f"if(gt(abs(W/2-X),W/2-{border_radius})*gt(abs(H/2-Y),"
                      f"H/2-{border_radius}),"
                      f"if(lte(hypot({border_radius}-(W/2-abs(W/2-X)),"
                      f"{border_radius}-(H/2-abs(H/2-Y))),"
                      f"{border_radius}),255,0),255)'[media];"
                      # add padding around media
                      f"[media]pad=w=iw+(iw*(12/500)*2):"
                      f"h=ih+(iw*(12/500)):"
                      f"x=(iw*(12/500)):"
                      f"y=0:color=#00000000[media];"
                      # stack
                      f"[1][media]vstack=inputs=2[stacked];"
                      # add background
                      f"[stacked]split=2[bg][fg];"
                      f"[bg]drawbox=c={'#15202b' if dark else '#ffffff'}:replace=1:t=fill[bg];"
                      f"[bg][fg]overlay=format=auto",
                      "-c:v", config.temp_vcodec, "-pix_fmt", config.temp_vpixfmt,
                      "-c:a", "copy", "-fps_mode", "vfr",
                      outfile)
    return outfile
