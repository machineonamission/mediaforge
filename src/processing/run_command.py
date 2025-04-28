import asyncio
import os
import re
import subprocess
import sys

from core.clogs import logger


async def run_command(*args: str):
    """
    run a cli command

    :param args: the args of the command, what would normally be seperated by a space
    :return: the result of the command
    """

    # https://stackoverflow.com/a/56884806/9044183
    # set proccess priority low
    if sys.platform == "win32":
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.BELOW_NORMAL_PRIORITY_CLASS
        nicekwargs = {"startupinfo": startupinfo}
    else:
        nicekwargs = {"preexec_fn": lambda: os.nice(10)}

    # Create subprocess
    process = await asyncio.create_subprocess_exec(
        *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        **nicekwargs
    )

    # Status
    logger.info(f"'{args[0]}' started with PID {process.pid}")
    logger.debug(f"PID {process.pid}: {args}")

    # Wait for the subprocess to finish
    stdout, stderr = await process.communicate()

    try:
        result = stdout.decode().strip() + stderr.decode().strip()
    except UnicodeDecodeError:
        result = stdout.decode("ascii", 'ignore').strip() + stderr.decode("ascii", 'ignore').strip()
    # no ffmpeg you cannot hide from me
    result = re.sub(r'\r(?!\n)', '\n', result)
    # Progress
    if process.returncode == 0:
        logger.debug(f"PID {process.pid} Done.")
        logger.debug(f"Results: {result}")
    else:

        logger.error(
            f"PID {process.pid} Failed: {args} result: {result}",
        )
        # adds command output to traceback
        raise CMDError(f"Command failed with exit code {process.returncode}: {args}.") from CMDError(result)
    # Result

    # Return stdout
    return result


class CMDError(Exception):
    """raised by run_command"""
    pass


async def ffmpeg(*args):
    return await run_command("ffmpeg", *args)
