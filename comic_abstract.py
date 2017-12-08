#! /usr/bin/python3
# vim: set expandtab tabstop=4 shiftwidth=4 :
"""Module to define logic common to all comics."""

import json
import time
import os
from datetime import date
from urlfunctions import get_filename_from_url, get_file_at_url
import inspect
import logging


def get_date_for_comic(comic):
    """Return date object for a given comic."""
    return date(comic['year'], comic['month'], comic['day'])


def get_info_before_comic(comic):
    """Generates the info to be put before the images."""
    author = comic.get('author')
    if author:
        yield 'by ' + author


def get_info_after_comic(comic):
    """Generates the info to be put after the images."""
    for name in ['alt', 'title', 'title2', 'texts', 'name', 'description']:
        info = comic.get(name)
        if info:
            yield info


class GenericComic(object):
    """Generic class to handle the logic common to all comics

    Attributes :
        name        Name of the comic (for logging, CLI and default output dir)
        long_name   Long name of the comic (to be added in the comic info)
        url         Base url for the comic (without trailing slash)."""
    name = None
    long_name = None
    url = None
    _categories = ('ALL', )

    @classmethod
    def log(cls, string):
        """Dirty logging function."""
        # TODO: https://docs.python.org/2/library/logging.html#logrecord-attributes
        # we do not need to retrieve the function name manually
        logging.debug(inspect.stack()[1][3] + " " + cls.name + " " + string)

    @classmethod
    def _get_output_dir(cls):
        """Returns the name of the output directory (for comics and JSON file).
        To be overridden if needed."""
        return cls.name

    @classmethod
    def _create_output_dir(cls):
        """Create output directory for the comic on the file system."""
        cls.log("start")
        os.makedirs(cls._get_output_dir(), exist_ok=True)
        cls.log("done")

    @classmethod
    def _get_json_file_path(cls):
        """Get the full path to the JSON file."""
        return os.path.join(cls._get_output_dir(), cls.name + '.json')

    @classmethod
    def _load_db(cls):
        """Load the JSON file to return the list of comics."""
        cls.log("start")
        try:
            with open(cls._get_json_file_path()) as file:
                return json.load(file)
        except IOError:
            return []

    @classmethod
    def get_comics(cls):
        """Return the list of comics."""
        return [c for c in cls._load_db() if 'deleted' not in c]

    @classmethod
    def get_last_comic(cls, comics):
        """Return the last (non-deleted) comic."""
        return next((c for c in reversed(comics) if 'deleted' not in c), None)

    @classmethod
    def _save_db(cls, data):
        """Save the list of comics in the JSON file."""
        cls.log("start")
        with open(cls._get_json_file_path(), 'w+') as file:
            json.dump(data, file, indent=4, sort_keys=True)
        cls.log("done")

    @classmethod
    def get_file_in_output_dir(cls, url, prefix=None):
        """Download file from URL and save it in output folder."""
        cls.log("start (url:%s)" % url)
        filename = os.path.join(
            cls._get_output_dir(),
            ('' if prefix is None else prefix) +
            get_filename_from_url(url))
        return get_file_at_url(url, filename)

    @classmethod
    def check_everything_is_ok(cls):
        """Perform tests on the database to check that everything is ok."""
        cls.log("start")
        print(cls.name, ': about to check')
        comics = cls.get_comics()  # cls._load_db()
        imgs_paths = {}
        imgs_urls = {}
        prev_date, prev_num = None, None
        today = date.today()
        for i, comic in enumerate(comics):
            cls.print_comic(comic)
            url = comic.get('url')
            assert isinstance(url, str), "Url %s not a string" % url
            assert comic.get('comic') == cls.long_name
            assert all(isinstance(comic.get(k), int)
                       for k in ['day', 'month', 'year']), \
                "Invalid date data (%s)" % url
            curr_date = get_date_for_comic(comic)
            assert curr_date <= today
            curr_num = comic.get('num', 0)
            assert isinstance(curr_num, int)
            assert prev_date is None or prev_date <= curr_date or \
                prev_num < curr_num, \
                "Comics are not in order (%s)" % url
            prev_date, prev_num = curr_date, curr_num
            img = comic.get('img')
            local_img = comic.get('local_img')
            assert isinstance(img, list)
            assert isinstance(local_img, list)
            assert len(local_img) == len(img)
            for path in local_img:
                if path is not None:
                    assert os.path.isfile(path)
                    imgs_paths.setdefault(path, set()).add(i)
            for img_url in img:
                imgs_urls.setdefault(img_url, set()).add(i)
        print()
        if False:  # To check if imgs are not overriding themselves
            for path, nums in imgs_paths.items():
                if len(nums) > 1:
                    print("Image used multiple times", path, nums)
            for img_url, nums in imgs_urls.items():
                if len(nums) > 1:
                    print("Url used multiple times", img_url, nums)
        if False:  # To check that all files in folder are useful
            json = cls._get_json_file_path()
            output_dir = cls._get_output_dir()
            for file_ in os.listdir(output_dir):
                file_path = os.path.join(output_dir, file_)
                if file_path not in imgs_paths and file_path != json:
                    print("Unused image", file_path)
        cls.log("done")

    @classmethod
    def get_next_comic(cls, _):
        """Generator to get the next comic.

        First argument is the last properly downloaded comic which gives
        a starting point to download more.

        This is the method called by update(). It should yield comics which
        are basically dictionnaries with the following property :
            - 'url' is linked to a string
            - 'img' is linked to a list of url (that will get downloaded)
            - 'day'/'month'/'year' are self explicit. They are linked to
                integers corresponding to the comic dates. There should be
                all of them or none of them
            - more fields can be provided."""
        raise NotImplementedError

    @classmethod
    def print_text(cls, text):
        """Print text by returning to the beginning of the line every time."""
        print(cls.name, ':', text, ' ' * 10, '\r', end='')

    @classmethod
    def print_comic(cls, comic):
        """Print information about a comic."""
        cls.print_text(comic['url'])

    @classmethod
    def update(cls):
        """Update the database : get the latest comics and save in the DB.

        This is a wrapper around get_next_comic() providing the following
        generic features :
            - logging
            - database handling (open and save)
            - exception handling (properly retrieved data are always saved)
            - file download
            - data management (adds current date if no date is provided)."""
        cls.log("start")
        print(cls.name, ': about to update')
        cls._create_output_dir()
        comics = cls._load_db()
        new_comics = []
        start = time.time()
        try:
            last_comic = cls.get_last_comic(comics)
            cls.log("last comic is %s" % ('None' if last_comic is None else last_comic['url']))
            for comic in cls.get_next_comic(last_comic):
                cls.log("got %s" % str(comic))
                assert 'url' in comic
                assert 'img' in comic
                if 'day' in comic:
                    assert all(isinstance(comic.get(k), int) for k in ['day', 'month', 'year'])
                else:
                    assert all(k not in comic for k in ['day', 'month', 'year'])
                    day = date.today()
                    comic['day'], comic['month'], comic['year'] = \
                        day.day, day.month, day.year
                prefix = comic.get('prefix', '')
                comic['local_img'] = [cls.get_file_in_output_dir(i, prefix)
                                      for i in comic['img']]
                comic['comic'] = cls.long_name
                comic['new'] = None  # "'new' in comic" to check if new
                new_comics.append(comic)
                cls.print_comic(comic)
        finally:
            end = time.time()
            if new_comics:
                print()
                cls._save_db(comics + new_comics)
                print(cls.name, ": added", len(new_comics),
                      "comics in", end - start, "seconds")
            else:
                print(cls.name, ": nothing new")
        cls.log("done")

    @classmethod
    def try_to_get_missing_resources(cls):
        """Download images that might not have been downloaded properly in
        the first place."""
        cls.log("start")
        print(cls.name, ': about to try to get missing resources')
        cls._create_output_dir()
        comics = cls._load_db()
        change = False
        for comic in comics:
            local = comic['local_img']
            prefix = comic.get('prefix', '')
            for i, (path, url) in enumerate(zip(local, comic['img'])):
                if path is None:
                    new_path = cls.get_file_in_output_dir(url, prefix)
                    if new_path is None:
                        print(cls.name, ': failed to get', url)
                    else:
                        print(cls.name, ': got', url, 'at', new_path)
                        local[i] = new_path
                        change = True
                        comic['new'] = None
        if change:
            cls._save_db(comics)
            print(cls.name, ": some missing resources have been downloaded")
        cls.log("done")

    @classmethod
    def reset_new(cls):
        """Remove the 'new' flag on comics in the DB."""
        cls.log("start")
        cls._create_output_dir()
        cls._save_db([{key: val for key, val in c.items() if key != 'new'} for c in cls._load_db()])
        cls.log("done")

    @classmethod
    def delete_last(cls):
        """Delete last (non-deleted) comic."""
        cls.log("start")
        comics = cls._load_db()
        last_comic = cls.get_last_comic(comics)
        if last_comic is None:
            cls.log("no comic to delete")
        else:
            cls.log("about to delete %s" % last_comic['url'])
            last_comic['deleted'] = None  # "'deleted' in comic" to check if deleted
            cls._save_db(comics)
        cls.log("done")

    @classmethod
    def delete_all(cls):
        """Delete all comics."""
        cls.log("start")
        comics = cls._load_db()
        if comics:
            for c in comics:
                c['deleted'] = None  # "'deleted' in comic" to check if deleted
            cls._save_db(comics)
        cls.log("done")

    @classmethod
    def print_name(cls):
        """Print name."""
        cls.log("start")
        print(cls.name)
        cls.log("end")

    @classmethod
    def info(cls):
        """Print information about the comics."""
        cls.log("start")
        print("%s (%s) : " % (cls.long_name, cls.url))
        print("In " + ', '.join(cls.get_categories()))
        cls._create_output_dir()
        comics = cls.get_comics()  # cls._load_db()
        dates = [get_date_for_comic(c) for c in comics]
        print("%d comics (%d new)" % (len(comics), sum(1 for c in comics if 'new' in c)))
        print("%d images" % sum(len(c['img']) for c in comics))
        if dates:
            date_min, date_max = min(dates), max(dates)
            print("from %s to %s (%d days)" % (date_min, date_max, (date_max - date_min).days))
        print()
        cls.log("done")

    @classmethod
    def readme(cls):
        """Return information to generate README."""
        return ' * [%s](%s)\n' % (cls.long_name, cls.url)

    @classmethod
    def gitignore(cls):
        """Return information to generate gitignore."""
        return '%s\n' % (cls.name)

    @classmethod
    def get_categories(cls):
        """Return categories to be able to group comics.

        Categories are such that all classes have their ancestrors'
        categories and their own (provided as an iterable in the
        `_categories` class member)."""
        return sorted(set(cat
                          for klass in cls.__mro__
                          for cat in getattr(klass, '_categories', [])))
