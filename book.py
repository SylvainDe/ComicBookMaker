#! /usr/bin/python3
# vim: set expandtab tabstop=4 shiftwidth=4 :
"""Module to create ebooks"""

import html
import sys
import subprocess
import os
import urllib.parse
import datetime
from itertools import chain
from comic_abstract import get_date_for_comic, get_info_before_comic, get_info_after_comic

# http://www.amazon.com/gp/feature.html?ie=UTF8&docId=1000234621
KINDLEGEN_PATH = './kindlegen_linux_2.6_i386_v2_9/kindlegen'
HTML_HEADER = """
<html>
    <head>
        <title>%s</title>
        <meta name='book-type' content='comic'/>
        <meta name='orientation-lock' content='landscape'/>
        <meta name='cover' content='%s'>
    </head>
    <body>
        Generated with '%s' at %s<br>
        <a name='TOC'><h1>Table of Contents</h1></a>"""
HTML_TOC_ITEM = """
        <a href='#%d'>%s</a><br>"""
HTML_START = """
    <mbp:pagebreak />
    <h1>Comics</h1>
    <a name='start' />"""
HTML_COMIC_INFO = """
        <mbp:pagebreak />
        <a name='%d'/><h2>%s</h2>
            %s %s<br>"""
HTML_COMIC_ADDITIONAL_INFO = """
            %s<br>"""
HTML_COMIC_IMG = """
            <img src='%s' style='width:100%%'><br>"""
HTML_FOOTER = """
    </body>
</html>"""


def collect_comics(comic_classes):
    """Retrieve all comics for the list of comic classes provided."""
    return chain.from_iterable(c.load_db() for c in comic_classes)


def filter_comics(comics):
    """Filter comics based on (hardcoded) criterias.

    On the long run, I'd like the criteria to be provided via command-line
    arguments."""
    return [c for c in comics if 'new' in c]


def sort_comics(comics):
    """Sort comics based on (hardcoded) criterias.

    On the long run, I'd like the criteria to be provided via command-line
    arguments."""
    return sorted(comics, key=get_date_for_comic, reverse=True)


def truncate_comics(comics):
    """Truncate the list of comics based on (hardcoded) criterias.

    On the long run, I'd like the criteria to be provided via command-line
    arguments."""
    return comics[:3000]


def make_book(comic_classes):
    """Create ebook - not finished."""
    comics = truncate_comics(sort_comics(filter_comics(collect_comics(comic_classes))))
    for i, c in enumerate(comics):
        print(i, c['url'], get_date_for_comic(c))
    if comics:
        make_book_from_comic_list(
            comics,
            '{0!s} from {1!s} to {2!s}'.format(' - '.join(sorted({c['comic'] for c in comics})),
             min(get_date_for_comic(c) for c in comics).strftime('%x'),
             max(get_date_for_comic(c) for c in comics).strftime('%x')),
            'book.html')


def convert_unicode_to_html(text):
    """Convert unicode text to HTML by escaping it."""
    return html.escape(text).encode('ascii', 'xmlcharrefreplace').decode()


def make_book_from_comic_list(comics, title, file_name):
    """Create book from a list of comics."""
    cover = 'empty.jpg'
    output_dir = 'generated_books'
    os.makedirs(output_dir, exist_ok=True)
    html_book = os.path.join(output_dir, file_name)

    with open(html_book, 'w+') as book:
        book.write(HTML_HEADER % (
            title,
            cover,
            ' '.join(sys.argv),
            datetime.datetime.now().strftime('%c')
        ))

        for i, com in enumerate(comics):
            book.write(HTML_TOC_ITEM % (i, com['url']))

        book.write(HTML_START)

        for i, com in enumerate(comics):
            book.write(HTML_COMIC_INFO % (
                i, com['url'], com['comic'], get_date_for_comic(com).strftime('%x')))
            for info in get_info_before_comic(com):
                book.write(HTML_COMIC_ADDITIONAL_INFO % convert_unicode_to_html(info))
            for path in com['local_img']:
                if path is not None:
                    assert os.path.isfile(path)
                    book.write(
                        HTML_COMIC_IMG % urllib.parse.quote(os.path.relpath(path, output_dir)))
            for info in get_info_after_comic(com):
                book.write(HTML_COMIC_ADDITIONAL_INFO % convert_unicode_to_html(info))
        book.write(HTML_FOOTER)

    subprocess.call([KINDLEGEN_PATH, '-verbose', '-dont_append_source', html_book])
