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
import zipfile
from comic_abstract import get_date_for_comic, get_info_before_comic, get_info_after_comic
from PIL import Image

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
        <a name='%d'/><h2><a href='%s'>%s</a></h2>
            %s %s<br>"""
HTML_COMIC_ADDITIONAL_INFO = """
            %s<br>"""
HTML_COMIC_IMG = """
            <img src='%s' style='width:100%%'><br>"""
HTML_FOOTER = """
    </body>
</html>"""

XHTML_HEADER = """
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
"http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">

<head>
  <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
  <title>%s</title>
  <meta name='cover' content='%s'/>
</head>

<body>
  Generated with '%s' at %s
"""

XHTML_TOC_ITEM = """
        <a href='#%d'>%s</a><br/>"""

XHTML_START = """
    <h1>Comics</h1>"""

XHTML_COMIC_INFO = """
        <a name='%d'/><h2><a href='%s'>%s</a></h2>
            %s %s<br/>"""

XHTML_COMIC_ADDITIONAL_INFO = """
            %s<br/>"""

XHTML_COMIC_IMG = """
            <img src='%s' style='width:100%%'><br>"""

XHTML_FOOTER = """
</body>

</html>"""

HTML_TAGS = HTML_HEADER, HTML_TOC_ITEM, HTML_START, HTML_COMIC_INFO, HTML_COMIC_ADDITIONAL_INFO, HTML_COMIC_IMG, HTML_FOOTER
XHTML_TAGS = XHTML_HEADER, XHTML_TOC_ITEM, XHTML_START, XHTML_COMIC_INFO, XHTML_COMIC_ADDITIONAL_INFO, XHTML_COMIC_IMG, XHTML_FOOTER


def collect_comics(comic_classes):
    """Retrieve all comics for the list of comic classes provided."""
    return chain.from_iterable(c.get_comics() for c in comic_classes)


def filter_comics(comics):
    """Filter comics based on (hardcoded) criterias.

    On the long run, I'd like the criteria to be provided via command-line
    arguments."""
    comics = list(comics)
    initial_len = len(comics)
    filtered_comics = [c for c in comics if 'new' in c]
    filtered_len = len(filtered_comics)
    if initial_len != filtered_len:
        print("After filtering, %d out of %d comics were kept" % (filtered_len, initial_len))
    return filtered_comics


def sort_comics(comics):
    """Sort comics based on (hardcoded) criterias.

    On the long run, I'd like the criteria to be provided via command-line
    arguments."""
    return sorted(comics, key=get_date_for_comic)


def truncate_comics(comics):
    """Truncate the list of comics based on (hardcoded) criterias.

    On the long run, I'd like the criteria to be provided via command-line
    arguments."""
    limit = 3000
    len_comics = len(comics)
    if len_comics > limit:
        print("Keeping %d comics out of %d" % (limit, len_comics))
    return comics[-limit:]


def make_book(comic_classes):
    """Create ebook - not finished."""
    comics = truncate_comics(sort_comics(filter_comics(collect_comics(comic_classes))))
    for i, c in enumerate(comics):
        print(i, c['url'], get_date_for_comic(c))
    if comics:
        make_book_from_comic_list(
            comics,
            '%s from %s to %s' %
            (' - '.join(sorted({c['comic'] for c in comics})),
             min(get_date_for_comic(c) for c in comics).strftime('%x'),
             max(get_date_for_comic(c) for c in comics).strftime('%x')),
            'book.html')


def convert_unicode_to_html(text):
    """Convert unicode text to HTML by escaping it."""
    return html.escape(text).encode('ascii', 'xmlcharrefreplace').decode()


def split_image(img):
    return [img]

def make_book_from_comic_list(comics, title, file_name, mobi=True):
    """Create book from a list of comics."""
    cover = 'empty.jpg'
    output_dir = 'generated_books'
    os.makedirs(output_dir, exist_ok=True)
    html_book = os.path.join(output_dir, file_name)

    header, toc_item, start, com_info, com_add_info, com_img, footer = HTML_TAGS if mobi else XHTML_TAGS

    with open(html_book, 'w+') as book:
        book.write(header % (
            title,
            cover,
            ' '.join(sys.argv),
            datetime.datetime.now().strftime('%c')
        ))

        for i, com in enumerate(comics):
            book.write(toc_item % (i, com['url']))

        book.write(start)

        for i, com in enumerate(comics):
            book.write(com_info % (
                i, com['url'], com['url'],
                com['comic'], get_date_for_comic(com).strftime('%x')))
            for info in get_info_before_comic(com):
                book.write(com_add_info % convert_unicode_to_html(info))
            for img in com['local_img']:
                for path in split_image(img):
                    if path is not None:
                        if os.path.isfile(path):
                            book.write(com_img % urllib.parse.quote(os.path.relpath(path, output_dir)))
                        else:
                            print("Oops, %s is not a file" % path)
            for info in get_info_after_comic(com):
                book.write(com_add_info % convert_unicode_to_html(info))
        book.write(footer)

    if mobi:
        subprocess.call([KINDLEGEN_PATH, '-verbose', '-dont_append_source', html_book])
