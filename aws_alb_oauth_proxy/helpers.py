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


async def _instance_document() -> Optional[str]:
    """This is a wrapper around |aiohttp.request|_ to make it usable in a synchronous way.

    As only one request is done per proxy, there normally is no need to use a session.
    There is however a bug (`#3628`_) in ``aiohttp`` that leaks the session when an exception is raised.
    The manual session handling for only one request is a workaround while waiting for `PR #3640`_ to be merged.

    :return: The region name as a string

    .. |aiohttp.request| replace:: ``aiohttp.request``
    .. _aiohttp.request: https://docs.aiohttp.org/en/latest/client_reference.html#aiohttp.request
    .. _#3628: https://github.com/aio-libs/aiohttp/issues/3628
    .. _PR #3640: https://github.com/aio-libs/aiohttp/pull/3640
    """
    token = ""
    headers = {"x-aws-ec2-metadata-token-ttl-seconds": "21600"}
    async with aiohttp.ClientSession(raise_for_status=True, timeout=aiohttp.ClientTimeout(total=1), headers=headers) as session:
        try:
            async with session.put("http://169.254.169.254/latest/api/token") as response:
                token = await response.text().strip()
        except TimeoutError:
            logger.debug("Timeout while attempting to get IMDS token")
            
    token_header = {"x-aws-ec2-metadata-token", token}
    async with aiohttp.ClientSession(raise_for_status=True, timeout=aiohttp.ClientTimeout(total=1), headers=token_header) as session:
        try:
            async with session.get("http://169.254.169.254/latest/dynamic/instance-identity/document") as response:
                document = await response.text()
        except TimeoutError:
            logger.debug("Timeout while attempting to get instance document.")
        else:
            return json.loads(document)["region"]


def _aws_region() -> Optional[str]:
    """Attempts to query the AWS region where this instance is running.

    Returns None if endpoint is not available, which means we're probably not running on AWS.

    `Related Amazon docs <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/instance-identity-documents.html>`_
    """

    try:
        event_loop = asyncio.get_event_loop()
    except RuntimeError:
        event_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(event_loop)

    return event_loop.run_until_complete(_instance_document())
