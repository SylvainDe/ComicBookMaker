#! /usr/bin/python3
# vim: set expandtab tabstop=4 shiftwidth=4 :
"""Module to define logic common to all comics."""

import json
import time
import os
from datetime import date
from urlfunctions import get_filename_from_url, get_file_at_url


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
    for name in ['alt', 'title', 'title2', 'texts', 'name']:
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

    @classmethod
    def get_output_dir(cls):
        """Returns the name of the output directory (for comics and JSON file).
        To be overridden if needed."""
        return cls.name

    @classmethod
    def create_output_dir(cls):
        """Create output directory for the comic on the file system."""
        os.makedirs(cls.get_output_dir(), exist_ok=True)

    @classmethod
    def get_json_file_path(cls):
        """Get the full path to the JSON file."""
        return os.path.join(cls.get_output_dir(), cls.name + '.json')

    @classmethod
    def load_db(cls):
        """Load the JSON file to return a list of comics."""
        try:
            with open(cls.get_json_file_path()) as file:
                return json.load(file)
        except IOError:
            return []

    @classmethod
    def save_db(cls, data):
        """Save the list of comics in the JSON file."""
        with open(cls.get_json_file_path(), 'w+') as file:
            json.dump(data, file, indent=4)

    @classmethod
    def get_file_in_output_dir(cls, url, prefix=None):
        """Download file from URL and save it in output folder."""
        filename = os.path.join(
            cls.get_output_dir(),
            ('' if prefix is None else prefix) +
            get_filename_from_url(url))
        return get_file_at_url(url, filename)

    @classmethod
    def check_everything_is_ok(cls):
        """Perform tests on the database to check that everything is ok."""
        print(cls.name, ': about to check')
        comics = cls.load_db()
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
            json = cls.get_json_file_path()
            output_dir = cls.get_output_dir()
            for file_ in os.listdir(output_dir):
                file_path = os.path.join(output_dir, file_)
                if file_path not in imgs_paths and file_path != json:
                    print("Unused image", file_path)

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
        return

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
        print(cls.name, ': about to update')
        cls.create_output_dir()
        comics = cls.load_db()
        new_comics = []
        start = time.time()
        try:
            for comic in cls.get_next_comic(comics[-1] if comics else None):
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
                cls.save_db(comics + new_comics)
                print(cls.name, ": added", len(new_comics),
                      "comics in", end - start, "seconds")
            else:
                print(cls.name, ": nothing new")

    @classmethod
    def try_to_get_missing_resources(cls):
        """Download images that might not have been downloaded properly in
        the first place."""
        print(cls.name, ': about to try to get missing resources')
        cls.create_output_dir()
        comics = cls.load_db()
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
        if change:
            cls.save_db(comics)
            print(cls.name, ": some missing resources have been downloaded")

    @classmethod
    def reset_new(cls):
        """Remove the 'new' flag on comics in the DB."""
        cls.create_output_dir()
        cls.save_db([{key: val for key, val in c.items() if key != 'new'} for c in cls.load_db()])
