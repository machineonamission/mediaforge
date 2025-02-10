import asyncio
import concurrent.futures
import functools
import typing

import utils.tempfiles
from utils.tempfiles import handle_tfs_parallel


class NonBugError(Exception):
    """When this is raised instead of a normal Exception, on_command_error() will not attach a traceback or github
    link. """
    pass


class ReturnedNothing(Exception):
    """raised by process()"""
    pass


async def run_parallel(syncfunc: typing.Callable, *args, **kwargs):
    """
    uses concurrent.futures.ProcessPoolExecutor to run CPU-bound functions in their own process

    :param syncfunc: the blocking function
    :return: the result of the blocking function
    """
    # this is only used for essentially async code that just isnt asyncio, ie pyvips and ffmpeg, so a threadpool
    # executor is fine
    with concurrent.futures.ThreadPoolExecutor(1) as pool:
        success, res, files = await asyncio.get_running_loop().run_in_executor(
            pool, functools.partial(handle_tfs_parallel, syncfunc, *args, **kwargs)
        )
    if files:
        tfs = utils.tempfiles.session.get()
        tfs += files
        utils.tempfiles.session.set(tfs)
    if success:
        return res
    else:
        raise res


