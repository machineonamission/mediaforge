import json
import re

from core.clogs import logger
from processing.common import ffmpeg
from processing.run_command import run_command


async def get_gif_loop_count(gif):
    # i cannot import get_vcodec cause circular shit UGH
    out = await run_command("ffprobe", "-v", "panic", "-select_streams", "v:0", "-show_entries",
                            "stream=codec_name", "-print_format", "json", gif)
    out = json.loads(out)
    # if its not actually a gif codec but its treated as a gif, default to always loop
    if out["streams"] and out["streams"][0]["codec_name"] != "gif":
        return 0
    # 'NUL' if sys.platform == "win32" else "/dev/null"
    # evil hack https://superuser.com/a/1663570/1001487
    out = await ffmpeg("-i", gif, "-v", "debug", "-f", "null", "-")
    if (match := re.search(r"Loop count is (\d+)", out)) is None:
        # -1 (no loop) seems to remain unspecified but 0 loop is specified. no idea.
        # chatgpt says without a netscape header, there are no loops, so like idk
        lc = -1
    else:
        lc = int(match.group(1))
    logger.debug(f"Detected {gif} loop count as {lc}")
    return lc
