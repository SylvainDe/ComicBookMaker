#! /usr/bin/python3
# vim: set expandtab tabstop=4 shiftwidth=4 :
"""Module with functions wrapping urllib"""

import urllib.request
import urllib.parse
import json
import shutil
from bs4 import BeautifulSoup


def convert_iri_to_plain_ascii_uri(uri):
    """Convert IRI to plain ASCII URL
    Based on http://stackoverflow.com/questions/4389572/how-to-fetch-a-non-ascii-url-with-python-urlopen."""
    lis = list(urllib.parse.urlsplit(uri))
    lis[2] = urllib.parse.quote(lis[2])
    url = urllib.parse.urlunsplit(lis)
    if False and url != uri:
        print(uri, '->', url)
    return url


def urlopen_wrapper(url):
    """Wrapper around urllib.request.urlopen (user-agent, etc).

    url is a string
    Returns a byte object."""
    user_agent = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/534.30 (KHTML, like Gecko) Ubuntu/11.04 Chromium/12.0.742.112 Chrome/12.0.742.112 Safari/534.30'
    return urllib.request.urlopen(
        urllib.request.Request(
            url,
            headers={'User-Agent': user_agent, 'Accept': '*/*'}))


def urljoin_wrapper(base, url):
    """Wrapper around urllib.parse.urljoin.
    Construct a full ("absolute") URL by combining a "base URL" (base) with
    another URL (url)."""
    return urllib.parse.urljoin(base, url)


def get_content(url):
    """Get content at url.

    url is a string
    Returns a string"""
    try:
        return urlopen_wrapper(url).read()
    except (urllib.error.HTTPError):
        print(url)
        raise


def get_file_at_url(url, path):
    """Save content at url in path on file system.
    In theory, this could have been achieved with urlretrieve but it seems
    to be about to get deprecated and adding a user-agent seems to be quite
    awkward.

    url is a string
    path is a string corresponding to the file location
    Returns the path if the file is retrieved properly, None otherwise."""
    try:
        with urlopen_wrapper(url) as response, open(path, 'wb') as out_file:
            shutil.copyfileobj(response, out_file)
            return path
    except (urllib.error.HTTPError):
        return None


def get_filename_from_url(url):
    """Get filename from url

    url is a string
    Returns a string corresponding to the name of the file."""
    return urllib.parse.unquote(url).split('/')[-1]


def load_json_at_url(url):
    """Get content at url as JSON and return it."""
    return json.loads(get_content(url).decode())


def get_soup_at_url(url):
    """Get content at url as BeautifulSoup.

    url is a string
    Returns a BeautifulSoup object."""
    return BeautifulSoup(get_content(url))
