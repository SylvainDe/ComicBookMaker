#! /usr/bin/python3
# vim: set expandtab tabstop=4 shiftwidth=4 :
"""Module to retrieve webcomics"""

import os
import json
import urllib.request
import urllib.parse
import shutil
import html
import re
from bs4 import BeautifulSoup
import time
import sys
from datetime import date, timedelta
import datetime
import argparse
from subprocess import call

KINDLEGEN_PATH = './kindlegen_linux_2.6_i386_v2_9/kindlegen'


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
            headers={'User-Agent': user_agent}))


def get_content(url):
    """Get content at url.

    url is a string
    Returns a string"""
    return urlopen_wrapper(url).read()


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


def get_date_for_comic(comic):
    """Return date object for a given comic."""
    return date(comic['year'], comic['month'], comic['day'])


def load_json_at_url(url):
    """Get content at url as JSON and return it."""
    return json.loads(get_content(url).decode())


def get_soup_at_url(url):
    """Get content at url as BeautifulSoup.

    url is a string
    Returns a BeautifulSoup object."""
    return BeautifulSoup(get_content(url))


class GenericComic(object):
    """Generic class to handle the logic common to all comics

    Attributes :
        name        Name of the comic (for logging and CLI)
        long_name   Long name of the comic (to be added in the comic info)
        output_dir  Output directory to put/get data (comics + database)
        json_file   Name of the JSON file used to store the database
        url         Base url for the comic (without trailing slash)."""
    name = None
    long_name = None
    output_dir = None
    json_file = None
    url = None

    @classmethod
    def create_output_dir(cls):
        """Create output directory for the comic on the file system."""
        os.makedirs(cls.output_dir, exist_ok=True)

    @classmethod
    def get_json_file_path(cls):
        """Get the full path to the JSON file."""
        return os.path.join(cls.output_dir, cls.json_file)

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
            cls.output_dir,
            ('' if prefix is None else prefix) +
            urllib.parse.unquote(url).split('/')[-1])
        return get_file_at_url(url, filename)

    @classmethod
    def check_everything_is_ok(cls):
        """Perform tests on the database to check that everything is ok."""
        print(cls.name, ': about to check')
        comics = cls.load_db()
        imgs_paths = {}
        imgs_urls = {}
        prev_date, prev_num = None, None
        for i, comic in enumerate(comics):
            cls.print_comic(comic)
            url = comic.get('url')
            assert isinstance(url, str), "Url %s not a string" % url
            assert comic.get('comic') == cls.long_name
            assert all(isinstance(comic.get(k), int)
                       for k in ['day', 'month', 'year']), \
                "Invalid date data (%s)" % url
            curr_date = get_date_for_comic(comic)
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
                    print(path, nums)
            for img_url, nums in imgs_urls.items():
                if len(nums) > 1:
                    print(img_url, nums)

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


class Xkcd(GenericComic):
    """Class to retrieve Xkcd comics."""
    name = 'xkcd'
    long_name = 'xkcd'
    output_dir = 'xkcd'
    json_file = 'xkcd.json'
    url = 'http://xkcd.com'

    @classmethod
    def get_next_comic(cls, last_comic):
        first_num = last_comic['num'] if last_comic else 0
        last_num = load_json_at_url(urllib.parse.urljoin(cls.url, 'info.0.json'))['num']

        for num in range(first_num + 1, last_num + 1):
            if num != 404:
                json_url = urllib.parse.urljoin(cls.url, '%d/info.0.json' % num)
                comic = load_json_at_url(json_url)
                comic['img'] = [comic['img']]
                comic['prefix'] = '%d-' % num
                comic['json_url'] = json_url
                comic['url'] = urllib.parse.urljoin(cls.url, str(num))
                comic['day'] = int(comic['day'])
                comic['month'] = int(comic['month'])
                comic['year'] = int(comic['year'])
                assert comic['num'] == num
                yield comic


class ExtraFabulousComics(GenericComic):
    """Class to retrieve Extra Fabulous Comics."""
    name = 'efc'
    long_name = 'Extra Fabulous Comics'
    output_dir = 'efc'
    json_file = 'efc.json'
    url = 'http://extrafabulouscomics.com',

    @classmethod
    def get_next_comic(cls, last_comic):
        img_src_re = re.compile('^%s/wp-content/uploads/' % cls.url)
        next_comic = \
            get_soup_at_url(last_comic['url']).find('a', title='next') \
            if last_comic else \
            get_soup_at_url(cls.url).find('a', title='first')
        while next_comic:
            url = next_comic.get('href')
            soup = get_soup_at_url(url)
            next_comic = soup.find('a', title='next')
            image = soup.find('img', src=img_src_re)
            title = soup.find(
                'meta',
                attrs={'name': 'twitter:title'}).get('content')
            yield {
                'url': url,
                'title': title,
                'img': [image.get('src')] if image else [],
                'prefix': title + '-'
            }


class NeDroid(GenericComic):
    """Class to retrieve NeDroid comics."""
    name = 'nedroid'
    long_name = 'NeDroid'
    output_dir = 'nedroid'
    json_file = 'nedroid.json'
    url = 'http://nedroid.com'

    @classmethod
    def get_next_comic(cls, last_comic):
        comic_url_re = re.compile('^%s/comics/([0-9]*)-([0-9]*)-([0-9]*).*' % cls.url)
        short_url_re = re.compile('^%s/\\?p=([0-9]*)' % cls.url)

        next_comic = \
            get_soup_at_url(last_comic['url']).find('div', class_='nav-next').find('a') \
            if last_comic else \
            get_soup_at_url(cls.url).find('div', class_='nav-first').find('a')

        while next_comic:
            url = next_comic.get('href')
            soup = get_soup_at_url(url)
            img = soup.find('img', src=comic_url_re)
            img_url = img.get('src')
            title = img.get('alt')
            assert title == soup.find_all('h2')[-1].string
            assert url == soup.find('link', rel='canonical').get('href')
            next_comic = soup.find('div', class_='nav-next').find('a')
            short_url = soup.find('link', rel='shortlink').get('href')
            year, month, day = [int(s) for s in comic_url_re.match(img_url).groups()]
            num = int(short_url_re.match(short_url).groups()[0])
            yield {
                'url': url,
                'short_url': short_url,
                'title': title,
                'title2': img.get('title'),
                'img': [img_url],
                'day': day,
                'month': month,
                'year': year,
                'num': num,
            }


class Garfield(GenericComic):
    """Class to retrieve Garfield comics."""
    name = 'garfield'
    long_name = 'Garfield'
    output_dir = 'garfield'
    json_file = 'garfield.json'
    url = 'http://garfield.com'

    @classmethod
    def get_next_comic(cls, last_comic):
        first_day = get_date_for_comic(last_comic) + timedelta(days=1) \
            if last_comic else date(1978, 6, 19)
        for i in range((date.today() - first_day).days + 1):
            day = first_day + timedelta(days=i)
            day_str = day.isoformat()
            yield {
                'url': urllib.parse.urljoin(cls.url, 'comic/%s' % day_str),
                'month': day.month,
                'year': day.year,
                'day': day.day,
                'img': [urllib.parse.urljoin(cls.url, 'uploads/strips/%s.jpg' % day_str)],
            }


class Dilbert(GenericComic):
    """Class to retrieve Dilbert comics."""
    name = 'dilbert'
    long_name = 'Dilbert'
    output_dir = 'dilbert'
    json_file = 'dilbert.json'
    url = 'http://dilbert.com'

    @classmethod
    def get_next_comic(cls, last_comic):
        img_src_re = re.compile('^/dyn/str_strip/')
        first_day = get_date_for_comic(last_comic) + timedelta(days=1) \
            if last_comic else date(1989, 4, 16)
        for i in range((date.today() - first_day).days + 1):
            day = first_day + timedelta(days=i)
            day_str = day.isoformat()
            url = urllib.parse.urljoin(cls.url, 'strips/comic/%s/' % day_str)
            img = get_soup_at_url(url).find('img', src=img_src_re)
            title = img.get('title')
            assert title == "The Dilbert Strip for %s" % \
                (day.strftime("%B %d, %Y").replace(" 0", " "))
            yield {
                'url': url,
                'month': day.month,
                'year': day.year,
                'day': day.day,
                'img': [urllib.parse.urljoin(url, img.get('src'))],
                'name': title,
                'prefix': '%s-' % day_str
            }


class ThreeWordPhrase(GenericComic):
    """Class to retrieve Three Word Phrase comics."""
    name = 'threeword'
    long_name = 'Three Word Phrase'
    output_dir = 'threeword'
    json_file = 'threeword.json'
    url = 'http://threewordphrase.com'

    @classmethod
    def get_next_comic(cls, last_comic):
        next_url = (
            get_soup_at_url(last_comic['url']).find('img', src='/nextlink.gif')
            if last_comic else
            get_soup_at_url(cls.url).find('img', src='/firstlink.gif')
            ).parent.get('href')

        while next_url:
            comic_url = urllib.parse.urljoin(cls.url, next_url)
            soup = get_soup_at_url(comic_url)
            title = soup.find('title')
            # hackish way to get the image
            imgs = [img for img in soup.find_all('img')
                    if not img.get('src').endswith(
                        ('link.gif', '32.png', 'twpbookad.jpg',
                         'merchad.jpg', 'header.gif', 'tipjar.jpg'))]
            yield {
                'url': comic_url,
                'title': title.string if title else None,
                'title2': '  '.join(img.get('alt') for img in imgs if img.get('alt')),
                'img': [urllib.parse.urljoin(comic_url, img.get('src')) for img in imgs],
            }
            next_url = soup.find('img', src='/nextlink.gif').parent.get('href')


class SaturdayMorningBreakfastCereal(GenericComic):
    """Class to retrieve Saturday Morning Breakfast Cereal comics."""
    name = 'smbc'
    long_name = 'Saturday Morning Breakfast Cereal'
    output_dir = 'smbc'
    json_file = 'smbc.json'
    url = 'http://www.smbc-comics.com'

    @classmethod
    def get_next_comic(cls, last_comic):
        last_num = last_comic['num'] if last_comic else 0

        archive_page = urllib.parse.urljoin(cls.url, '/archives.php')
        comic_link_re = re.compile('^/index.php\\?id=([0-9]*)$')

        for link in get_soup_at_url(archive_page).find_all('a', href=comic_link_re):
            link_url = link.get('href')
            num = int(comic_link_re.match(link_url).groups()[0])
            if num > last_num:
                url = urllib.parse.urljoin(cls.url, link_url)
                soup = get_soup_at_url(url)
                image_url1 = soup.find('div', id='comicimage').find('img').get('src')
                image_url2 = soup.find('div', id='aftercomic').find('img').get('src')
                comic = {
                    'url': url,
                    'num': num,
                    'img': [image_url1] + ([image_url2] if image_url2 else []),
                    'title': link.string
                }
                yield comic


class PerryBibleFellowship(GenericComic):
    """Class to retrieve Perry Bible Fellowship comics."""
    name = 'pbf'
    long_name = 'Perry Bible Fellowship'
    output_dir = 'pbf'
    json_file = 'pbf.json'
    url = 'http://pbfcomics.com'

    @classmethod
    def get_next_comic(cls, last_comic):
        last_num = last_comic['num'] if last_comic else 0

        comic_link_re = re.compile('^/[0-9]*/$')
        comic_img_re = re.compile('^/archive_b/PBF.*')

        for link in reversed(get_soup_at_url(cls.url).find_all('a', href=comic_link_re)):
            num = int(link.get('name'))
            if num > last_num:
                href = link.get('href')
                assert href == '/%d/' % num
                url = urllib.parse.urljoin(cls.url, href)
                name = link.string
                image = get_soup_at_url(url).find('img', src=comic_img_re)
                assert image.get('alt') == name
                yield {
                    'url': url,
                    'num': num,
                    'name': name,
                    'img': [urllib.parse.urljoin(url, image.get('src'))],
                    'prefix': '%d-' % num
                }


class BerkeleyMews(GenericComic):
    """Class to retrieve Berkeley Mews comics."""
    name = 'berkeley'
    long_name = 'Berkeley Mews'
    output_dir = 'berkeley'
    json_file = 'berkeley.json'
    url = 'http://www.berkeleymews.com'

    @classmethod
    def get_next_comic(cls, last_comic):
        last_num = last_comic['num'] if last_comic else 0

        comic_num_re = re.compile('%s/\\?p=([0-9]*)$' % cls.url)
        comic_date_re = re.compile('.*/([0-9]*)-([0-9]*)-([0-9]*)-.*')
        for link in reversed(get_soup_at_url(cls.url).find_all('a', href=comic_num_re, class_='')):
            comic_url = link.get('href')
            num = int(comic_num_re.match(comic_url).groups()[0])
            if num > last_num:
                img = get_soup_at_url(comic_url).find('div', id='comic').find('img')
                img_url = img.get('src')
                year, month, day = [int(s) for s in comic_date_re.match(img_url).groups()]
                title2 = img.get('title')
                assert title2 == img.get('alt')
                yield {
                    'url': comic_url,
                    'num': num,
                    'title': link.string,
                    'title2': title2,
                    'img': [img_url],
                    'year': year,
                    'month': month,
                    'day': day,
                }


class BouletCorp(GenericComic):
    """Class to retrieve BouletCorp comics."""
    name = 'boulet'
    long_name = 'Boulet Corp'
    output_dir = 'boulet'
    json_file = 'boulet.json'
    url = 'http://www.bouletcorp.com'

    @classmethod
    def get_next_comic(cls, last_comic):
        date_re = re.compile('^%s/blog/([0-9]*)/([0-9]*)/([0-9]*)/' % cls.url)
        prev_url = last_comic['url'] if last_comic else None
        comic_url = (
            get_soup_at_url(prev_url).find('div', id='centered_nav').find_all('a')[3]
            if prev_url
            else get_soup_at_url(cls.url).find('div', id='centered_nav').find_all('a')[0]).get('href')

        while comic_url != prev_url:
            year, month, day = [int(s) for s in date_re.match(comic_url).groups()]
            soup = get_soup_at_url(comic_url)
            imgs = soup.find('div', id='notes').find('div', class_='storycontent').find_all('img')
            image_urls = [convert_iri_to_plain_ascii_uri(i.get('src')) for i in imgs]
            texts = '  '.join(t for t in (i.get('title') for i in imgs) if t)
            title = soup.find('title').string
            comic = {
                'url': comic_url,
                'img': image_urls,
                'title': title,
                'texts': texts,
                'year': year,
                'month': month,
                'day': day,
            }
            yield comic
            prev_url, comic_url = comic_url, soup.find('div', id='centered_nav').find_all('a')[3].get('href')


class AmazingSuperPowers(GenericComic):
    """Class to retrieve Amazing Super Powers comics."""
    name = 'asp'
    long_name = 'Amazing Super Powers'
    output_dir = 'asp'
    json_file = 'asp.json'
    url = 'http://www.amazingsuperpowers.com'
    # images are not retrieved properly, I guess the user-agent it not ok

    @classmethod
    def get_next_comic(cls, last_comic):
        link_re = re.compile('^%s/([0-9]*)/([0-9]*)/.*$' % cls.url)
        img_re = re.compile('^%s/comics/.*$' % cls.url)
        archive_url = urllib.parse.urljoin(cls.url, 'category/comics/')
        last_date = get_date_for_comic(last_comic) if last_comic else date(2000, 1, 1)
        for link in reversed(get_soup_at_url(archive_url).find_all('a', href=link_re)):
            comic_date = datetime.datetime.strptime(link.parent.previous_sibling.string, "%b %d, %Y").date()
            if comic_date > last_date:
                title = link.string
                comic_url = link.get('href')
                imgs = get_soup_at_url(comic_url).find_all('img', src=img_re)
                title = ' '.join(img.get('title') for img in imgs)
                assert ' '.join(img.get('alt') for img in imgs) == title
                yield {
                    'url': comic_url,
                    'title': title,
                    'img': [img.get('src') for img in imgs],
                    'day': comic_date.day,
                    'month': comic_date.month,
                    'year': comic_date.year
                }


class CyanideAndHappiness(GenericComic):
    """Class to retrieve Cyanide And Happiness comics."""
    name = 'cyanide'
    long_name = 'Cyanide and Happiness'
    output_dir = 'cyanide'
    json_file = 'cyanide.json'
    url = 'http://explosm.net'

    @classmethod
    def get_author_and_data_from_str(cls, data):
        """Extract author and date from the string which can have different formats."""
        author_date_re = re.compile('^by (.*)  ([0-9]*).([0-9]*).([0-9]*)$')
        date_author_re = re.compile('^([0-9]*).([0-9]*).([0-9]*) by (.*)$')

        match = author_date_re.match(data)
        if match:
            author, month, day, year = match.groups()
        else:
            match = date_author_re.match(data)
            if match:
                month, day, year, author = match.groups()
            else:
                assert False
        return (int(day), int(month), int(year), author.strip())

    @classmethod
    def get_next_comic(cls, last_comic):
        img_src_re = re.compile('^http://(www.)?explosm.net/db/files/Comics/.*')
        comic_num_re = re.compile('^%s/comics/([0-9]*)/$' % cls.url)

        next_comic = \
            get_soup_at_url(last_comic['url']).find('a', rel='next') \
            if last_comic else \
            get_soup_at_url(urllib.parse.urljoin(cls.url, '/comics/')).find('a', rel='first')

        while next_comic:
            comic_url = urllib.parse.urljoin(cls.url, next_comic.get('href'))
            num = int(comic_num_re.match(comic_url).groups()[0])
            soup = get_soup_at_url(comic_url)
            next_comic = soup.find('a', rel='next')
            day, month, year, author = cls.get_author_and_data_from_str(soup.find('table').find('tr').find('td').text)
            image = soup.find('img', src=img_src_re)
            yield {
                'num': num,
                'url': comic_url,
                'author': author,
                'day': day,
                'month': month,
                'year': year,
                'prefix': '%d-' % num,
                'img': [image.get('src')] if image else []
                }


class MrLovenstein(GenericComic):
    """Class to retrieve Mr Lovenstein comics."""
    name = 'mrlovenstein'
    long_name = 'Mr. Lovenstein'
    json_file = 'mrlovenstein.json'
    output_dir = 'mrlovenstein'
    url = 'http://www.mrlovenstein.com'

    @classmethod
    def get_next_comic(cls, last_comic):
        # TODO: more info from http://www.mrlovenstein.com/archive
        comic_num_re = re.compile('^/comic/([0-9]*)$')
        nums = [int(comic_num_re.match(link.get('href')).groups()[0]) for link in get_soup_at_url(cls.url).find_all('a', href=comic_num_re)]
        first, last = min(nums), max(nums)
        if last_comic:
            first = last_comic['num'] + 1
        for num in range(first, last + 1):
            url = urllib.parse.urljoin(cls.url, '/comic/%d' % num)
            soup = get_soup_at_url(url)
            imgs = list(reversed(soup.find_all('img', src=re.compile('^/images/comics/'))))
            yield {
                'url': url,
                'num': num,
                'texts': '  '.join(t for t in (i.get('title') for i in imgs) if t),
                'img': [urllib.parse.urljoin(url, i.get('src')) for i in imgs],
            }


class DinosaurComics(GenericComic):
    """Class to retrieve Dinosaur Comics comics."""
    name = 'dinosaur'
    long_name = 'Dinosaur Comics'
    output_dir = 'dinosaur'
    json_file = 'dinosaur.json'
    url = 'http://www.qwantz.com'

    @classmethod
    def get_next_comic(cls, last_comic):
        last_num = last_comic['num'] if last_comic else 0
        comic_link_re = re.compile('^%s/index.php\\?comic=([0-9]*)$' % cls.url)
        comic_img_re = re.compile('^%s/comics/' % cls.url)
        archive_url = '%s/archive.php' % cls.url
        # first link is random -> skip it
        for link in reversed(get_soup_at_url(archive_url).find_all('a', href=comic_link_re)[1:]):
            url = link.get('href')
            num = int(comic_link_re.match(url).groups()[0])
            if num > last_num:
                text = link.next_sibling.string
                # Hackish way to convert string with numeral "1st"/"2nd"/etc to date
                day = datetime.datetime.strptime(
                    link.string
                    .replace('st', '')
                    .replace('nd', '')
                    .replace('rd', '')
                    .replace('th', '')
                    .replace('Augu', 'August'), "%B %d, %Y").date()
                soup = get_soup_at_url(url)
                img = soup.find('img', src=comic_img_re)
                yield {
                    'url': url,
                    'month': day.month,
                    'year': day.year,
                    'day': day.day,
                    'img': [img.get('src')],
                    'title': img.get('title'),
                    'text': text,
                    'num': num,
                }


class ButterSafe(GenericComic):
    """Class to retrieve Butter Safe comics."""
    name = 'butter'
    long_name = 'ButterSafe'
    output_dir = 'butter'
    json_file = 'butter.json'
    url = 'http://buttersafe.com'

    @classmethod
    def get_next_comic(cls, last_comic):
        archive_url = '%s/archive/' % cls.url
        comic_link_re = re.compile('^%s/([0-9]*)/([0-9]*)/([0-9]*)/.*' % cls.url)

        prev_date = get_date_for_comic(last_comic) if last_comic else date(2006, 1, 1)

        for link in reversed(get_soup_at_url(archive_url).find_all('a', href=comic_link_re)):
            url = link.get('href')
            title = link.string
            year, month, day = [int(s) for s in comic_link_re.match(url).groups()]
            if prev_date < date(year, month, day):
                img = get_soup_at_url(url).find('div', id='comic').find('img')
                assert img.get('alt') == title
                yield {
                    'title': title,
                    'day': day,
                    'month': month,
                    'year': year,
                    'url': url,
                    'img': [img.get('src')],
                }


class CalvinAndHobbes(GenericComic):
    """Class to retrieve Calvin and Hobbes comics."""
    name = 'calvin'
    long_name = 'Calvin and Hobbes'
    output_dir = 'calvin'
    json_file = 'calvin.json'
    # This is not through any official webpage but eh...
    url = 'http://marcel-oehler.marcellosendos.ch/comics/ch/'

    @classmethod
    def get_next_comic(cls, last_comic):
        last_date = get_date_for_comic(last_comic) if last_comic else date(1985, 11, 1)
        link_re = re.compile('^([0-9]*)/([0-9]*)/')
        img_re = re.compile('')
        for link in get_soup_at_url(cls.url).find_all('a', href=link_re):
            url = link.get('href')
            year, month = link_re.match(url).groups()
            if date(int(year), int(month), 1) + timedelta(days=31) >= last_date:
                img_re = re.compile('^%s%s([0-9]*)' % (year, month))
                month_url = urllib.parse.urljoin(cls.url, url)
                for img in get_soup_at_url(month_url).find_all('img', src=img_re):
                    img_src = img.get('src')
                    day = int(img_re.match(img_src).groups()[0])
                    comic_date = date(int(year), int(month), day)
                    if comic_date > last_date:
                        yield {
                            'url': month_url,
                            'year': int(year),
                            'month': int(month),
                            'day': int(day),
                            'img': ['%s%s/%s/%s' % (cls.url, year, month, img_src)],
                        }
                        last_date = comic_date


class AbstruseGoose(GenericComic):
    """Class to retrieve AbstruseGoose Comics."""
    name = 'abstruse'
    long_name = 'Abstruse Goose'
    output_dir = 'abstruse'
    json_file = 'abstruse.json'
    url = 'http://abstrusegoose.com'

    @classmethod
    def get_next_comic(cls, last_comic):
        archive_url = '%s/archive' % cls.url
        last_num = last_comic['num'] if last_comic else 0
        comic_url_re = re.compile('^%s/([0-9]*)$' % cls.url)
        comic_img_re = re.compile('^%s/strips/.*' % cls.url)
        for link in get_soup_at_url(archive_url).find_all('a', href=comic_url_re):
            url_comic = link.get('href')
            num = int(comic_url_re.match(url_comic).groups()[0])
            if num > last_num:
                yield {
                    'url': url_comic,
                    'num': num,
                    'title': link.string,
                    'img': [get_soup_at_url(url_comic).find('img', src=comic_img_re).get('src')]
                }


class PhDComics(GenericComic):
    """Class to retrieve PHD Comics."""
    name = 'phd'
    long_name = 'PhD Comics'
    output_dir = 'phd'
    json_file = 'phd.json'
    url = 'http://phdcomics.com'

    @classmethod
    def get_next_comic(cls, last_comic):
        archive_url = '%s/comics/archive_list.php' % cls.url
        comic_url_num_re = re.compile('^http://www.phdcomics.com/comics/archive.php\\?comicid=([0-9]*)$')

        last_num = last_comic['num'] if last_comic else 0

        for link in get_soup_at_url(archive_url).find_all('a', href=comic_url_num_re):
            comic_url = link.get('href')
            num = int(comic_url_num_re.match(comic_url).groups()[0])
            if num > last_num:
                month, day, year = [int(s) for s in link.string.split('/')]
                yield {
                    'url': comic_url,
                    'num': num,
                    'year': year,
                    'month': month,
                    'day': day if day else 1,
                    'img': [get_soup_at_url(comic_url).find('img', id='comic').get('src')],
                    'title': link.parent.parent.next_sibling.string
                }


class OverCompensating(GenericComic):
    """Class to retrieve the Over Compensating comics."""
    name = 'compensating'
    long_name = 'Over Compensating'
    output_dir = 'compensating'
    json_file = 'compensating.json'
    url = 'http://www.overcompensating.com'

    @classmethod
    def get_next_comic(cls, last_comic):
        img_src_re = re.compile('^/oc/comics/.*')
        comic_num_re = re.compile('.*comic=([0-9]*)$')
        next_comic = \
            get_soup_at_url(last_comic['url']).find('a', title='next comic') \
            if last_comic else \
            get_soup_at_url(cls.url).find('a', href=re.compile('comic=1$'))
        while next_comic:
            comic_url = urllib.parse.urljoin(cls.url, next_comic.get('href'))
            num = int(comic_num_re.match(comic_url).groups()[0])
            soup = get_soup_at_url(comic_url)
            img = soup.find('img', src=img_src_re)
            yield {
                'url': comic_url,
                'num': num,
                'img': [urllib.parse.urljoin(comic_url, img.get('src'))],
                'title': img.get('title')
            }
            next_comic = soup.find('a', title='next comic')


class TheDoghouseDiaries(GenericComic):
    """Class to retrieve The Dog House Diaries comics."""
    name = 'doghouse'
    long_name = 'The Dog House Diaries'
    output_dir = 'doghouse'
    json_file = 'doghouse.json'
    url = 'http://thedoghousediaries.com/'

    @classmethod
    def get_next_comic(cls, last_comic):
        comic_img_re = re.compile('^dhdcomics/.*')
        prev_url = last_comic['url'] if last_comic else None
        comic_url = (
            get_soup_at_url(prev_url).find('a', id='nextlink')
            if prev_url else
            get_soup_at_url(cls.url).find('a', id='firstlink')).get('href')

        while comic_url != prev_url:
            soup = get_soup_at_url(comic_url)
            img = soup.find('img', src=comic_img_re)
            # TODO : date
            yield {
                'url': comic_url,
                'title': soup.find('h2', id='titleheader').string,
                'title2': soup.find('div', id='subtext').string,
                'alt': img.get('title'),
                'img': [urllib.parse.urljoin(comic_url, img.get('src').strip())],
                'num': int(comic_url.split('/')[-1]),
            }
            prev_url, comic_url = comic_url, soup.find('a', id='nextlink').get('href')


class GenericGoComic(GenericComic):
    """Generic class to handle the logic common to comics from gocomics.com."""
    gocomic_name = None

    @classmethod
    def get_next_comic(cls, last_comic):
        gocomics = 'http://www.gocomics.com'
        url_date_re = re.compile('.*/([0-9]*)/([0-9]*)/([0-9]*)$')

        next_comic = \
            get_soup_at_url(last_comic['url']).find('a', class_='next', href=url_date_re) \
            if last_comic else \
            get_soup_at_url(cls.url).find('a', class_='beginning')

        while next_comic:
            url_comic = urllib.parse.urljoin(gocomics, next_comic.get('href'))
            year, month, day = [int(s) for s in url_date_re.match(url_comic).groups()]
            soup = get_soup_at_url(url_comic)
            next_comic = soup.find('a', class_='next', href=url_date_re)
            yield {
                'url': url_comic,
                'day': day,
                'month': month,
                'year': year,
                'img': [soup.find_all('img', class_='strip')[-1].get('src')],
                'author': soup.find('meta', attrs={'name': 'author'}).get('content')
            }


class PearlsBeforeSwine(GenericGoComic):
    """Class to retrieve Pearls Before Swine comics."""
    name = 'pearls'
    long_name = 'Pearls Before Swine'
    output_dir = 'pearls'
    json_file = 'pearls.json'
    url = 'http://www.gocomics.com/pearlsbeforeswine'


class Peanuts(GenericGoComic):
    """Class to retrieve Peanuts comics."""
    name = 'peanuts'
    long_name = 'Peanuts'
    output_dir = 'peanuts'
    json_file = 'peanuts.json'
    url = 'http://www.gocomics.com/peanuts'


def get_subclasses(klass):
    """Gets the list of direct/indirect subclasses of a class"""
    subclasses = klass.__subclasses__()
    for derived in list(subclasses):
        subclasses.extend(get_subclasses(derived))
    return subclasses

COMIC_NAMES = {c.name: c for c in get_subclasses(GenericComic) if c.name is not None}


def make_book(comic_classes):
    """Create ebook - not finished."""
    cover = 'empty.jpg'
    comics = sum((c.load_db() for c in comic_classes), [])
    html_book = 'book_%s.html' % ("_".join(c.name for c in comic_classes))
    with open(html_book, 'w+') as book:
        book.write("""
<html>
    <head>
        <title>%s</title>
        <meta name='book-type' content='comic'/>
        <meta name='orientation-lock' content='landscape'/>
        <meta name='cover' content='%s'>
    </head>
    <body>
        Generated with '%s' at %s<br>
        <a name='TOC'><h1>Table of Contents</h1></a>""" % (
            ' - '.join(c.long_name for c in comic_classes),
            cover,
            ' '.join(sys.argv),
            datetime.datetime.now().strftime('%c')
            ))

        for i, com in enumerate(comics):
            book.write("""
        <a href='#%d'>%s</a><br>""" % (i, com['url']))

        book.write("""
    <mbp:pagebreak />
    <a name='start' />""")

        for i, com in enumerate(comics):
            book.write("""
        <mbp:pagebreak />
        <a name='%d'/><h1>%s</h1>
            %s %s<br>""" % (i, com['url'], com['comic'], get_date_for_comic(com).strftime('%x')))
            author = com.get('author')
            if author:
                book.write("""
            by %s<br>""" % author)
            for path in com['local_img']:
                if path is not None:
                    assert os.path.isfile(path)
                    book.write("""
            <img src='%s'>""" % urllib.parse.quote(path))
            alt = com.get('alt')
            if alt:
                book.write("""
            %s<br>""" % html.escape(alt))
        book.write("""
    </body>
</html>""")

    call([KINDLEGEN_PATH, html_book])


def main():
    """Main function"""
    comic_names = sorted(COMIC_NAMES.keys())
    parser = argparse.ArgumentParser(
        description='Downloads webcomics and generates ebooks for offline reading (not yet)')
    parser.add_argument(
        '--comic', '-c',
        action='append',
        help=('comics to be considered (default: ALL)'),
        choices=comic_names,
        default=[])
    parser.add_argument(
        '--action', '-a',
        action='append',
        help=('actions required'),
        default=[])
    args = parser.parse_args()
    if not args.comic:
        args.comic = comic_names
    if not args.action:
        args.action = ['update']
    comic_classes = [COMIC_NAMES[c] for c in args.comic]
    for action in args.action:
        if action == 'book':
            make_book(comic_classes)
        elif action == 'update':
            for com in comic_classes:
                com.update()
        elif action == 'check':
            for com in comic_classes:
                com.check_everything_is_ok()
        elif action == 'fix':
            for com in comic_classes:
                com.try_to_get_missing_resources()
        else:
            print("Unknown action : %s" % action)

if __name__ == "__main__":
    main()
