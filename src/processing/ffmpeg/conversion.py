from processing.common import run_command
from processing.ffmpeg.ffprobe import mediatype, va_codecs, get_acodec, get_vcodec, get_frame_rate
from utils.tempfiles import reserve_tempfile


async def videotogif(video):
    outname = reserve_tempfile("gif")
    fps = await get_frame_rate(video)
    await run_command("ffmpeg", "-i", video,
                      # prevent partial frames, makes filesize worse but fixes issues with transparency
                      "-gifflags", "-transdiff",
                      "-vf",
                      # cap fps because gifs are wackyyyyyy
                      # TODO: https://superuser.com/q/1854904/1001487
                      ("fps=fps=50," if fps > 50 else "") + \
                      # make and use nice palette
                      "split[s0][s1];[s0]palettegen=reserve_transparent=1[p];[s1][p]paletteuse=bayer",
                      # i fucking hate gifs so much man
                      "-fps_mode", "vfr",
                      outname)

    return outname


async def video_reencode(
        video):  # reencodes mp4 as libx264 since the png format used cant be played by like literally anything
    assert (mt := await mediatype(video)) in ["VIDEO", "GIF"], f"file {video} with type {mt} passed to reencode()"
    # only reencode if need to ;)
    vcodec, acodec = await va_codecs(video)
    vcode = ["copy"] if vcodec == "h264" else ["libx264", "-pix_fmt", "yuv420p", "-vf",
                                               "scale=ceil(iw/2)*2:ceil(ih/2)*2,"
                                               # turns transparency into blackness
                                               "premultiply=inplace=1"]
    acode = ["copy"] if acodec == "aac" else ["aac", "-q:a", "2"]
    outname = reserve_tempfile("mp4")
    await run_command("ffmpeg", "-hide_banner", "-i", video, "-c:v", *vcode, "-c:a", *acode,
                      "-max_muxing_queue_size", "9999", "-movflags", "+faststart", outname)

    return outname


async def audio_reencode(audio):
    acodec = await get_acodec(audio)
    acode = ["copy"] if acodec == "aac" else ["aac", "-q:a", "2"]
    outname = reserve_tempfile("m4a")
    await run_command("ffmpeg", "-hide_banner", "-i", audio, "-c:a", *acode, outname)
    return outname


async def allreencode(file, fail_if_gif=True):
    mt = await mediatype(file)
    if mt == "IMAGE":
        return await mediatopng(file)
    elif mt == "VIDEO":
        return await video_reencode(file)
    elif mt == "AUDIO":
        return await audio_reencode(file)
    elif mt == "GIF" and not fail_if_gif:
        return file
    else:
        raise Exception(f"{file} of type {mt} cannot be re-encoded")


async def forcereencode(file):
    # cant use the other reencode functions cause this function never copies
    mt = await mediatype(file)
    if mt == "IMAGE":
        outname = reserve_tempfile("png")
        await run_command("ffmpeg", "-hide_banner", "-i", file, "-frames:v", "1", "-c:v",
                          "png", "-pix_fmt", "rgba",
                          outname)

        return outname
    elif mt == "VIDEO":
        outname = reserve_tempfile("mp4")
        await run_command("ffmpeg", "-hide_banner", "-i", file, "-c:v", "libx264", "-pix_fmt", "yuv420p", "-vf",
                          "scale=ceil(iw/2)*2:ceil(ih/2)*2,"
                          # turns transparency into blackness
                          "premultiply=inplace=1", "-c:a", "aac", "-q:a", "2",
                          "-max_muxing_queue_size", "9999", "-movflags", "+faststart", outname)

        return outname
    elif mt == "AUDIO":
        outname = reserve_tempfile("m4a")
        await run_command("ffmpeg", "-hide_banner", "-i", file, "-c:a", "aac", "-q:a", "2", outname)
        return outname
    elif mt == "GIF":
        return await videotogif(file)
    else:
        raise Exception(f"{file} of type {mt} cannot be re-encoded")


async def giftomp4(gif):
    """
    converts gif to mp4
    :param gif: gif
    :return: mp4
    """
    outname = reserve_tempfile("mp4")
    await run_command("ffmpeg", "-hide_banner", "-i", gif, "-movflags", "faststart", "-pix_fmt", "yuv420p",
                      "-sws_flags", "spline+accurate_rnd+full_chroma_int+full_chroma_inp", "-vf",
                      "scale=trunc(iw/2)*2:trunc(ih/2)*2", "-fps_mode", "vfr", outname)

    return outname


async def toaudio(media):
    """
    converts video to only audio
    :param media: video or audio ig
    :return: aac
    """
    name = reserve_tempfile("m4a")
    await run_command("ffmpeg", "-hide_banner", "-i", media, "-c:a", "aac", "-vn", name)

    return name


async def mediatopng(media):
    """
    converts media to png
    :param media: media
    :return: png
    """
    outname = reserve_tempfile("png")
    await run_command("ffmpeg", "-hide_banner", "-i", media, "-frames:v", "1", "-c:v",
                      "copy" if (await get_vcodec(media))["codec_name"] == "png" else "png", "-pix_fmt", "rgba",
                      outname)

    return outname


async def toapng(video):
    outname = reserve_tempfile("png")
    await run_command("ffmpeg", "-i", video, "-f", "apng", "-fps_mode", "vfr", outname)

    return outname
    # ffmpeg method, removes dependence on apngasm but bigger and worse quality
    # outname = reserve_tempfile("png")
    # await run_command("ffmpeg", "-i", video, "-f", "apng", "-plays", "0", outname)
