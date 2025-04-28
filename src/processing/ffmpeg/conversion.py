from processing.common import image_format
from processing.ffmpeg.ffprobe import va_codecs, get_acodec, get_vcodec, get_frame_rate, has_alpha, is_avif
from processing.mediatype import VIDEO, AUDIO, IMAGE, GIF
from processing.run_command import ffmpeg
from utils.tempfiles import reserve_tempfile


async def video_to_gif(video):
    if (await get_vcodec(video))["codec_name"] == "gif":
        return video
    outname = reserve_tempfile("gif")
    fps = await get_frame_rate(video)
    lc = await video.gif_loop_count()
    await ffmpeg("-i", video,
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


async def video_to_animated_avif(video):
    if video.endswith("avif"):
        return video
    out = reserve_tempfile("avif")
    # simplified from https://jakearchibald.com/2024/video-with-transparency/#encoding-animated-avif
    if await has_alpha(video):
        await ffmpeg("-i", video, "-filter_complex",
                     "-pix_fmt:0", "yuv420p",
                     "-pix_fmt:1", "gray8",
                     # the website i got this from forces a yuva format, but we already know it has alpha, so we can skip that
                     "[0:v]split[main][alpha];"
                     "[alpha]alphaextract[alpha];",
                     "-map", "[main]:v",
                     "-map", "[alpha]:v",
                     "-c:v:0", "libsvtav1",
                     "-preset", "8",
                     # the nicer av1 encoders dont support grayscale for transparency, so we have to use a shit one.
                     # shouldnt be too slow hopefully
                     "-c:v:1", "libaom-av1",
                     "-cpu-used", "8",
                     "-max_muxing_queue_size", "9999",
                     "-movflags", "+faststart",
                     out)
    else:
        # most of the manual avif shit is for handling transparency. if there is none, its rather shrimple!
        await ffmpeg("-i", video,
                     "-pix_fmt", "yuv420p",
                     "-c:v", "libsvtav1",
                     "-map", "0:v",
                     "-preset", "8",
                     "-max_muxing_queue_size", "9999",
                     "-movflags", "+faststart",
                     out)

    out.mt = GIF
    return out


async def image_to_avif(image):
    if image.endswith("avif"):
        return image
    out = reserve_tempfile("avif")
    # simplified from https://jakearchibald.com/2024/video-with-transparency/#encoding-animated-avif
    if await has_alpha(image):
        await ffmpeg("-i", image, "-filter_complex",
                     "-pix_fmt:0", "yuv420p",
                     "-pix_fmt:1", "gray8",
                     # the website i got this from forces a yuva format, but we already know it has alpha, so we can skip that
                     "[0:v]split[main][alpha];"
                     "[alpha]alphaextract[alpha];",
                     "-map", "[main]:v",
                     "-map", "[alpha]:v",
                     # i read that libsvt isnt great for images
                     "-c:v", "libaom-av1",
                     "-cpu-used", "8",
                     "-frames:v", "1", "-still-picture", "1",
                     out)
    else:
        # most of the manual avif shit is for handling transparency. if there is none, its rather shrimple!
        await ffmpeg("-i", image,
                     "-pix_fmt", "yuv420p",
                     "-c:v", "libaom-av1",
                     "-map", "0:v",
                     "-cpu_used", "8",
                     "-frames:v", "1", "-still-picture", "1",
                     out)

    out.mt = IMAGE
    return out


async def video_to_av1(video):
    outname = reserve_tempfile("mp4")
    await ffmpeg("-i", video,
                 "-c:v", "libsvtav1",
                 "-preset", "8",
                 "-pix_fmt", "yuv420p",
                 # turns transparency into blackness
                 "premultiply=inplace=1",
                 "-c:a", "aac", "-q:a", "2",
                 "-max_muxing_queue_size", "9999",
                 "-movflags", "+faststart",
                 outname)

    return outname


async def audio_to_aac(audio):
    outname = reserve_tempfile("m4a")
    await ffmpeg("-i", audio, "-c:a", "aac", "-q:a", "2", outname)
    return outname


async def allreencode(file):
    if file.lock_codec:
        return file
    mt = await file.mediatype()
    if mt == IMAGE:
        return await image_to_avif(file)
    elif mt == VIDEO:
        return await video_to_av1(file)
    elif mt == AUDIO:
        return await audio_to_aac(file)
    elif mt == GIF:
        return await video_to_animated_avif(file)
    else:
        raise Exception(f"{file} of type {mt} cannot be re-encoded")


async def giftomp4(gif):
    """
    converts gif to mp4
    :param gif: gif
    :return: mp4
    """
    outname = reserve_tempfile("mp4")
    await ffmpeg("-i", gif, "-movflags", "faststart", "-pix_fmt", "yuv420p",
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
    await ffmpeg("-i", media, "-c:a", "aac", "-vn", name)

    return name


async def mediatoimage(media, imagetype):
    outname = reserve_tempfile(imagetype)
    await ffmpeg("-i", media, "-frames:v", "1", "-c:v",
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
    return await mediatoimage(media, image_format)


# this shit brokey, discord fucks apngs
async def toapng(video):
    outname = reserve_tempfile("apng")
    outname.lock_codec = True
    await ffmpeg("-i", video, "-f", "apng", "-plays", "0",
                 # "-filter_complex", "split[v],palettegen,[v]paletteuse",
                 # "-fps_mode", "vfr",
                 outname)

    return outname
    # ffmpeg method, removes dependence on apngasm but bigger and worse quality
    # outname = reserve_tempfile("png")
    # await ffmpeg( "-i", video, "-f", "apng", "-plays", "0", outname)

async def normalize(file):
    # normalize bad behaving codecs/containers
    if await is_avif(file):
        out = reserve_tempfile("mkv")

    else:
        # this is extensible
        return file
