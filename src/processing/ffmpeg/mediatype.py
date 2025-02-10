import enum
import json

import magic
from PIL import Image, UnidentifiedImageError

from core.clogs import logger
from processing.common import run_command
from utils.tempfiles import TempFile


class InvalidMediaType(Exception):
    pass


class MediaType(enum.StrEnum):
    VIDEO = VIDEO
    AUDIO = AUDIO
    IMAGE = IMAGE
    GIF = GIF


VIDEO = MediaType.VIDEO
AUDIO = MediaType.AUDIO
IMAGE = MediaType.IMAGE
GIF = MediaType.GIF


async def mediatype(image: str | TempFile) -> MediaType:
    """
    Gets basic type of media
    :param image: filename of media
    :return: can be VIDEO, AUDIO, GIF, IMAGE or None (invalid or other).
    """
    if isinstance(image, TempFile) and image.mt is not None:
        return image.mt
    # ffmpeg doesn't work well with detecting images so let PIL do that
    mime = magic.from_file(image, mime=True)
    try:
        with Image.open(image) as im:
            anim = getattr(im, "is_animated", False)
        if anim:
            logger.debug(f"identified type {mime} with animated frames as GIF")
            return MediaType.GIF  # gifs dont have to be animated but if they aren't its easier to treat them like pngs
        else:
            logger.debug(f"identified type {mime} with no animated frames as IMAGE")
            return MediaType.IMAGE
    except UnidentifiedImageError:
        logger.debug(f"UnidentifiedImageError on {image}")
    # PIL isn't sure so let ffmpeg take control
    probe = await run_command('ffprobe', '-v', 'panic', '-count_packets', '-show_entries',
                              'stream=codec_type,codec_name,nb_read_packets',
                              '-print_format', 'json', image)
    props = {
        "video": False,
        "audio": False,
        "gif": False,
        "image": False
    }
    probe = json.loads(probe)
    for stream in probe["streams"]:
        if stream["codec_type"] == "audio":  # only can be pure audio
            props["audio"] = True
        elif stream["codec_type"] == "video":  # could be video or image or gif sadly
            if "nb_read_packets" in stream and int(stream["nb_read_packets"]) != 1:  # if there are multiple frames
                if stream["codec_name"] == "gif":  # if gif
                    # should have been detected in the previous step but cant hurt to be too sure
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
