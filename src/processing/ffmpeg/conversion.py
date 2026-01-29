from config import temp_vipscodec
from processing.ffmpeg.ffprobe import va_codecs, get_acodec, get_vcodec, get_frame_rate
from processing.mediatype import VIDEO, AUDIO, IMAGE, GIF
from processing.run_command import run_command
from utils.tempfiles import reserve_tempfile


async def videotogif(video):
    if (await get_vcodec(video))["codec_name"] == "gif":
        return video
    outname = reserve_tempfile("gif")
    fps = await get_frame_rate(video)
    lc = await video.gif_loop_count()
    await run_command("ffmpeg", "-i", video,
                      # prevent partial frames, makes filesize worse but fixes issues with transparency
                      "-gifflags", "-transdiff",
                      "-loop", str(lc),
                      "-vf",
                      # cap fps because gifs are wackyyyyyy
                      # TODO: https://superuser.com/q/1854904/1001487
                      f"{'fps=fps=50,' if fps > 50 else ''}"
                      "split[s0][s1];"
                      "[s0]"
                      # "What happens is that the color values are rounded to the nearest value that has a remainder of 4 when divided by 8."
                      # https://glq.pages.dev/posts/high_quality_gifs/
                      # this is only in the image preview, the effect goes away when downloaded, but thats where most of these are viewed from
                      # there's still 32^3 (32768) possible colors with this crushing, so a constant palette isnt viable
                      # code directly taken from lilliput, fast and accurate, and only decimated to feed to palettegen
                      # https://github.com/discord/lilliput/blob/e1547514bd5f32800c612e5564b18a60f046b1af/giflib.cpp#L848
                      "geq=r='bitor(bitand(r(X,Y), 248), 4)':g='bitor(bitand(g(X,Y), 248), 4)':b='bitor(bitand(b(X,Y), 248), 4)',"
                      # make and use nice palette
                      # from what i can tell, discord does preserve multi frame palettes
                      "palettegen=reserve_transparent=1:stats_mode=single"
                      "[p];"
                      # for some god forsaken reason, discord destroys any dither that isn't bayer
                      "[s1][p]paletteuse=dither=bayer:bayer_scale=3:new=1",
                      # i fucking hate gifs so much man
                      "-fps_mode", "vfr",
                      outname)
    # outname.glc = lc
    return outname


async def video_reencode(
        video):  # reencodes mp4 as libx264 since the png format used cant be played by like literally anything
    assert (mt := await video.mediatype()) in [VIDEO, GIF], f"file {video} with type {mt} passed to reencode()"
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


async def allreencode(file):
    if file.lock_codec:
        return file
    mt = await file.mediatype()
    if mt == IMAGE:
        return await mediatopng(file)
    elif mt == VIDEO:
        return await video_reencode(file)
    elif mt == AUDIO:
        return await audio_reencode(file)
    elif mt == GIF:
        return await videotogif(file)
    else:
        raise Exception(f"{file} of type {mt} cannot be re-encoded")


async def forcereencode(file):
    # this function always forces a reencode, allreencode doesnt reencode if codec is already good
    mt = await file.mediatype()
    if mt == IMAGE:
        outname = reserve_tempfile("png")
        await run_command("ffmpeg", "-hide_banner", "-i", file, "-frames:v", "1", "-c:v",
                          "png", "-pix_fmt", "rgba",
                          outname)

        return outname
    elif mt == VIDEO:
        outname = reserve_tempfile("mp4")
        await run_command("ffmpeg", "-hide_banner", "-i", file, "-c:v", "libx264", "-pix_fmt", "yuv420p", "-vf",
                          "scale=ceil(iw/2)*2:ceil(ih/2)*2,"
                          # turns transparency into blackness
                          "premultiply=inplace=1", "-c:a", "aac", "-q:a", "2",
                          "-max_muxing_queue_size", "9999", "-movflags", "+faststart", outname)

        return outname
    elif mt == AUDIO:
        outname = reserve_tempfile("m4a")
        await run_command("ffmpeg", "-hide_banner", "-i", file, "-c:a", "aac", "-q:a", "2", outname)
        return outname
    elif mt == GIF:
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


async def mediatoimage(media, imagetype):
    outname = reserve_tempfile(imagetype)
    await run_command("ffmpeg", "-hide_banner", "-i", media, "-frames:v", "1", "-c:v",
                      "copy" if (await get_vcodec(media))["codec_name"] == imagetype else imagetype, "-pix_fmt", "rgba",
                      outname)

    return outname


async def mediatopng(media):
    """
    converts media to png
    :param media: media
    :return: png
    """
    return await mediatoimage(media, "png")


async def mediatotempimage(media):
    return await mediatoimage(media, temp_vipscodec)


# this shit brokey, discord fucks apngs
async def toapng(video):
    outname = reserve_tempfile("apng")
    outname.lock_codec = True
    await run_command("ffmpeg", "-i", video, "-f", "apng", "-plays", "0",
                      # "-filter_complex", "split[v],palettegen,[v]paletteuse",
                      # "-fps_mode", "vfr",
                      outname)

    return outname
    # ffmpeg method, removes dependence on apngasm but bigger and worse quality
    # outname = reserve_tempfile("png")
    # await run_command("ffmpeg", "-i", video, "-f", "apng", "-plays", "0", outname)
