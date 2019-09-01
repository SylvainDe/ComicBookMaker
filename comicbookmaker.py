#! /usr/bin/python3
# vim: set expandtab tabstop=4 shiftwidth=4 :
"""Module to retrieve webcomics and create ebooks"""

import book
import argparse
import logging
from comics import COMICS_DICT


def get_file_content_until_tag(path, tag):
    """Get content from a filepath up to a given tag.
    If tag is not is the file, an exception is thrown."""
    content = []
    with open(path) as f:
        for l in f:
            content.append(l)
            if tag == l.strip():
                return content
    raise ValueError('Could not find "%s" in file "%s"' % (tag, path))


def add_new_lines_after_tag(path, new_lines, tag):
    """Add lines to file from a given tag.
    All content until tag is kept, all content after is lost."""
    content = get_file_content_until_tag(path, tag)
    with open(path, 'w') as f:
        f.write(''.join(content + new_lines))


def main():
    """Main function"""
    logger = logging.getLogger()
    arg_to_method = {
        'list': 'print_name',
        'update': 'update',
        'info': 'info',
        'check': 'check_everything_is_ok',
        'fix': 'try_to_get_missing_resources',
        'reset_new': 'reset_new',
        'delete_last': 'delete_last',
        'delete_all': 'delete_all',
    }
    comic_names = sorted(COMICS_DICT.keys(), key=lambda s: s.lower())
    parser = argparse.ArgumentParser(
        description='Downloads webcomics and generates ebooks for offline reading')
    parser.add_argument(
        '--comic', '-c',
        action='append',
        help=('comics to be considered (default: ALL) - categories can be used'),
        choices=comic_names,
        default=[])
    parser.add_argument(
        '--excluded', '-e',
        action='append',
        help=('comics to be excluded - categories can be used'),
        choices=comic_names,
        default=[])
    parser.add_argument(
        '--action', '-a',
        action='append',
        help=('actions required'),
        choices=list(arg_to_method) + ['book', 'gitignore', 'readme'],
        default=[])
    parser.add_argument(
        '--loglevel', '-l',
        type=int,
        action='store',
        help=('log level (as per the Python logging module)'),
        default=logging.CRITICAL)
    args = parser.parse_args()
    logger.setLevel(args.loglevel)
    # Apply default value
    if not args.comic:
        args.comic = ['ALL']
    if not args.action:
        args.action = ['update']
    comic_classes = set()
    for name in args.comic:
        for klass in COMICS_DICT[name]:
            comic_classes.add(klass)
    for name in args.excluded:
        for klass in COMICS_DICT[name]:
            comic_classes.remove(klass)
    comic_classes = sorted(comic_classes, key=operator.attrgetter('name'))
    logging.debug('Starting')
    for action in args.action:
        method_name = arg_to_method.get(action)
        if method_name is not None:
            for com in comic_classes:
                getattr(com, method_name)()
        elif action == 'book':
            book.make_book(comic_classes)
        elif action == 'gitignore':
            path = '.gitignore'
            new_content = [com.gitignore() for com in comic_classes]
            add_new_lines_after_tag(path, new_content, '# Generated folders')
        elif action == 'readme':
            path = 'README.md'
            new_content = [com.readme() for com in comic_classes]
            add_new_lines_after_tag(path, new_content, '----------------')
        else:
            print("Unknown action : %s" % action)

if __name__ == "__main__":
    main()
