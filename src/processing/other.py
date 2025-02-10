import glob
import re
import traceback

import yt_dlp as youtube_dl

import config
import utils.tempfiles
from processing.ffmpeg.conversion import mediatopng
from processing.ffmpeg.ffprobe import *
from processing.run_command import run_command
from core.clogs import logger
from utils.tempfiles import reserve_tempfile


class MyLogger(object):
    def debug(self, msg: ""):
        logger.debug(msg.replace("\r", ""))

    def warning(self, msg: ""):
        logger.warning(msg.replace("\r", ""))

    def error(self, msg: ""):
        logger.error(msg.replace("\r", ""))


def ytdownload(vid, form):
    # file extension is unknown so we have to do it weirdly
    while True:
        name = f"{utils.tempfiles.temp_dir}/{utils.tempfiles.get_random_string(12)}"
        if len(glob.glob(name + ".*")) == 0:
            break

    def live_filter(info, *, incomplete):
        if info.get("is_live"):
            return "Livestreams cannot be downloaded"

    opts = {
        "quiet": True,
        "outtmpl": f"{name}.%(ext)s",
        "default_search": "auto",
        "merge_output_format": "mp4",
        # try to fit in upload size, then fall back to max upload size
        "format": f'((bestvideo+bestaudio/best)[filesize_approx<{config.file_upload_limit}])/'
                  f'((bestvideo+bestaudio/best)[filesize_approx<?{config.max_file_size}])',
        'format_sort': ['+acodec:mp3:aac', '+vcodec:h264'],  # prefer h264 and mp3/aac, discord embeds better
        "max_filesize": config.max_file_size,
        "logger": MyLogger(),  # this is stupid but its how ytdl works
        "match_filter": live_filter  # no livestreams because they break things
    }
    if form == "audio":
        opts['format'] = (f"bestaudio[filesize_approx<{config.file_upload_limit}]/"
                          f"bestaudio[filesize_approx<?{config.max_file_size}]")
        # opts['postprocessors'] = [{
        #     'key': 'FFmpegExtractAudio',
        #     'preferredcodec': 'mp3',
        # }]
    try:
        with youtube_dl.YoutubeDL(opts) as ydl:
            ydl.download([vid])
        filename = glob.glob(name + ".*")
        if len(filename) > 0:
            return reserve_tempfile(filename[0])
        else:
            return None
    except youtube_dl.DownloadError as e:
        # python tries to stringify terminal color characters which looks bad
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        cleaned_error = ansi_escape.sub('', str(e))
        # yt-dlp includes detailed HTTP errors that can't be pickled, quick and dirty workaround
        raise youtube_dl.DownloadError(cleaned_error) from Exception(traceback.format_exception(e))



async def magickone(media, strength):
    tosave = reserve_tempfile("png")
    media = await mediatopng(media)
    await run_command("magick", media, "-liquid-rescale", f"{strength}%x{strength}%", tosave)

    return tosave


async def tts(text: str, model: typing.Literal["male", "female", "retro"] = "male"):
    ttswav = reserve_tempfile("wav")
    if model == "retro":
        await run_command("node", "tts/sam.js", "--moderncmu", "--wav", ttswav, text)
    else:
        # espeak is a fucking nightmare on windows and windows has good native tts anyways sooooo
        if sys.platform == "win32":
            # https://docs.microsoft.com/en-us/dotnet/api/system.speech.synthesis.voicegender?view=netframework-4.8
            voice = str({"male": 1, "female": 2}[model])
            await run_command("powershell", "-File", "tts.ps1", ttswav, text, voice)
        else:
            await run_command("./tts/mimic", "-voice",
                              "tts/mycroft_voice_4.0.flitevox" if model == "male" else "tts/cmu_us_slt.flitevox",
                              "-o", ttswav, "-t", text)
    outname = reserve_tempfile("mp3")
    await run_command("ffmpeg", "-hide_banner", "-i", ttswav, "-c:a", "libmp3lame", outname)

    return outname
