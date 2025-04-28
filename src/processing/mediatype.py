import enum
import json
import sys

if sys.platform == "win32":  # this hopefully wont cause any problems :>
    from winmagic import magic
else:
    import magic
from PIL import Image, UnidentifiedImageError

from core.clogs import logger
from processing.run_command import run_command


class InvalidMediaType(Exception):
    pass


class MediaType(enum.StrEnum):
    VIDEO = "VIDEO"
    AUDIO = "AUDIO"
    IMAGE = "IMAGE"
    GIF = "GIF"


VIDEO = MediaType.VIDEO
AUDIO = MediaType.AUDIO
IMAGE = MediaType.IMAGE
GIF = MediaType.GIF


async def mediatype(image) -> MediaType:
    """
    Gets basic type of media
    :param image: filename of media
    :return: can be VIDEO, AUDIO, GIF, IMAGE or None (invalid or other).
    """
    # ffmpeg doesn't work well with detecting images so let PIL do that
    mime = magic.from_file(image, mime=True)
    probe = await run_command('ffprobe', '-v', 'panic', '-count_packets', '-show_entries',
                              'stream=codec_type,codec_name,nb_read_packets:format_tags=major_brand',
                              '-print_format', 'json', image)
    props = {
        "video": False,
        "audio": False,
        "gif": False,
        "image": False
    }
    probe = json.loads(probe)
    animated_image = False
    # detect AVIF
    if "format_tags" in probe:
        if "tags" in probe["format_tags"]:
            if "major_brand" in probe["format_tags"]["tags"]:
                mb = probe["format_tags"]["tags"]["major_brand"]
                # animated AVIF
                if mb in ["avif", "avis"]:
                    animated_image = True
    # i shit you not, ffmepg does not support decoding animated webps.
    # there's patches in the work but none have been merged. cool
    # TODO: jxl, apng, gif, etc
    for stream in probe["streams"]:
        if stream["codec_type"] == "audio":  # only can be pure audio
            props["audio"] = True
            # if its audio, it cannot be a gif
            props["gif"] = False
        elif stream["codec_type"] == "video":  # could be video or image or gif sadly
            if "nb_read_packets" in stream and int(stream["nb_read_packets"]) != 1:  # if there are multiple frames
                if animated_image and not props["audio"]:  # animated image
                    props["gif"] = True  # gif
                else:  # multiple frames, not gif
                    props["video"] = True  # video!!
            else:  # if there is only one frame
                props["image"] = True  # it's an image
                # yes, this will mark 1 frame/non-animated gifs as images.
                # this is intentional behavior as most commands treat gifs as videos
    # ok so a container can have multiple formats, we need to return based on expected priority
    if props["video"]:
        return VIDEO
    if props["gif"]:
        return GIF
    if props["audio"]:
        return AUDIO
    if props["image"]:
        return IMAGE
    raise InvalidMediaType(f"Unknown media type for {image} due to unclassified type {mime}")
