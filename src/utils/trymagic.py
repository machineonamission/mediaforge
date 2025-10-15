import sys

from core.clogs import logger

try:
    if sys.platform == "win32":  # this hopefully wont cause any problems :>
        from winmagic import magic
    else:
        import magic
except OSError as e:
    logger.warn("Failed to import libmagic")
    logger.warn(e)
    magic = None

def from_file(*args, **kwargs):
    if magic:
        return magic.from_file(*args, **kwargs)
    else:
        logger.debug(f"attempted to call magic.from_file with args {args} {kwargs}, but magic failed to import.")
        return "libmagic unavailable"