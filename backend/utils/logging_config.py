"""
Logging setup.

Logs go to stdout as single-line key=value records. Cloud platforms
(Render, AWS CloudWatch, Azure Monitor, Google Cloud Logging) collect
stdout automatically, so no log files are needed on the server.
"""

import logging
import sys


def configure_logging(level: str = "INFO") -> None:
    root = logging.getLogger()
    if getattr(root, "_portal_configured", False):
        return
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter("%(asctime)s level=%(levelname)s logger=%(name)s %(message)s", "%Y-%m-%dT%H:%M:%S%z")
    )
    root.handlers = [handler]
    root.setLevel(level)
    root._portal_configured = True  # type: ignore[attr-defined]
