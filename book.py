#! /usr/bin/python3
# vim: set expandtab tabstop=4 shiftwidth=4 :
"""Module to create ebooks"""

import html
import sys
import subprocess
import os
import urllib.parse
import datetime
from comics import get_date_for_comic, get_info_before_comic, get_info_after_comic

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
    <a name='start' />"""
HTML_COMIC_INFO = """
        <mbp:pagebreak />
        <a name='%d'/><h1>%s</h1>
            %s %s<br>"""
HTML_COMIC_ADDITIONAL_INFO = """
            %s<br>"""
HTML_COMIC_IMG = """
            <img src='%s'><br>"""
HTML_FOOTER = """
    </body>
</html>"""


def make_book(comic_classes):
    """Create ebook - not finished."""
    output_dir = 'generated_books'
    cover = 'empty.jpg'
    comics = sum((c.load_db() for c in comic_classes), [])
    html_book = os.path.join(
        output_dir,
        'book_%s.html' % ("_".join(c.name for c in comic_classes))
    )
    os.makedirs(output_dir, exist_ok=True)
    with open(html_book, 'w+') as book:
        book.write(HTML_HEADER % (
            ' - '.join(c.long_name for c in comic_classes),
            cover,
            ' '.join(sys.argv),
            datetime.datetime.now().strftime('%c')
        ))

        for i, com in enumerate(comics):
            book.write(HTML_TOC_ITEM % (i, com['url']))

        book.write(HTML_START)

        for i, com in enumerate(comics):
            book.write(HTML_COMIC_INFO % (i, com['url'], com['comic'], get_date_for_comic(com).strftime('%x')))
            for info in get_info_before_comic(com):
                book.write(HTML_COMIC_ADDITIONAL_INFO % html.escape(info))
            for path in com['local_img']:
                if path is not None:
                    assert os.path.isfile(path)
                    book.write(HTML_COMIC_IMG % urllib.parse.quote(os.path.relpath(path, output_dir)))
            for info in get_info_after_comic(com):
                book.write(HTML_COMIC_ADDITIONAL_INFO % html.escape(info))
        book.write(HTML_FOOTER)

    subprocess.call([KINDLEGEN_PATH, html_book])
