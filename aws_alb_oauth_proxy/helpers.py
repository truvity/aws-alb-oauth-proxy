import asyncio
from concurrent.futures import TimeoutError
import json
import logging
from typing import Optional

import aiohttp
from aiohttp import web
from multidict import CIMultiDictProxy


logger = logging.getLogger(__name__)


DEFAULT_REMOVED_RESPONSE_HEADERS = {"Content-Length", "Content-Encoding", "Transfer-Encoding"}


def clean_response_headers(request: web.Request) -> CIMultiDictProxy:
    """Removes HTTP headers from an upstream response and add auth header if present.

    :param request: A web.Request containing the request whose headers are to be cleaned.
    :return: A CIMultiDictProxy containing the clean headers.
    """
    clean_headers = request.headers.copy()
    for header in DEFAULT_REMOVED_RESPONSE_HEADERS:
        clean_headers.popall(header, None)
    try:
        auth_header = request.pop("auth_payload")
    except KeyError:
        pass
    else:
        clean_headers.popall(auth_header[0], None)
        clean_headers.add(*auth_header)
    return CIMultiDictProxy(clean_headers)
