#! /usr/bin/python3
# vim: set expandtab tabstop=4 shiftwidth=4 :
"""Module to retrieve webcomics"""

import os
import json
import urllib.request
import urllib.parse
import re
from bs4 import BeautifulSoup
import time
from datetime import date, timedelta
import datetime
import argparse


def convert_iri_to_plain_ascii_uri(uri):
    """Convert IRI to plain ASCII URL
    Based on http://stackoverflow.com/questions/4389572/how-to-fetch-a-non-ascii-url-with-python-urlopen."""
    lis = list(urllib.parse.urlsplit(uri))
    lis[2] = urllib.parse.quote(lis[2])
    url = urllib.parse.urlunsplit(lis)
    if False and url != uri:
        print(uri, '->', url)
    return url


def get_content(url):
    """Get content at url."""
    user_agent = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/534.30 (KHTML, like Gecko) Ubuntu/11.04 Chromium/12.0.742.112 Chrome/12.0.742.112 Safari/534.30"
    return urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': user_agent})).read()


def get_file_at_url(url, path):
    """Save content at url in path on file system."""
    try:
        urllib.request.urlretrieve(url, path)
        return path
    except (ValueError, urllib.error.ContentTooShortError):
        return None


def get_date_for_comic(comic):
    """Return date object for a given comic."""
    return date(comic['year'], comic['month'], comic['day'])


def load_json_at_url(url):
    """Get content at url as JSON."""
    return json.loads(get_content(url).decode())


def get_soup_at_url(url):
    """Get content at url as BeautifulSoup."""
    return BeautifulSoup(get_content(url))


class GenericComic(object):
    """Generic class to handle the logic common to all comics

    Attributes :
        name        Name of the comic
        long_name   Long name of the comic
        output_dir  Output directory to put/get data (comics + database)
        json_file   Name of the JSON file used to store the database."""
    name = None
    long_name = None
    output_dir = None
    json_file = None

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
        prev_date = None
        for i, comic in enumerate(comics):
            cls.print_comic(comic)
            url = comic.get('url')
            assert isinstance(url, str)
            assert comic.get('comic') == cls.long_name
            assert all(isinstance(comic.get(k), int) for k in ['day', 'month', 'year'])
            curr_date = get_date_for_comic(comic)
            assert prev_date is None or prev_date <= curr_date
            prev_date = curr_date
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
        if False:  # To check if we imgs are not overriding themselves
            for path, nums in imgs_paths.items():
                if len(nums) > 1:
                    print(path, nums)
            for img_url, nums in imgs_urls.items():
                if len(nums) > 1:
                    print(img_url, nums)
        print()

    @classmethod
    def get_next_comic(cls, _):
        """Generator to get the next comic."""
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
        """Update the database : get the latest comics and save in the DB."""
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
                    comic['day'], comic['month'], comic['year'] = day.day, day.month, day.year
                prefix = comic.get('prefix', '')
                comic['local_img'] = [cls.get_file_in_output_dir(i, prefix) for i in comic['img']]
                comic['comic'] = cls.long_name
                new_comics.append(comic)
                cls.print_comic(comic)
        finally:
            end = time.time()
            if new_comics:
                print()
                cls.save_db(comics + new_comics)
                print(cls.long_name, ": added", len(new_comics),
                      "comics in", end-start, "seconds")
            else:
                print(cls.long_name, ": nothing new")

    @classmethod
    def try_to_get_missing_resources(cls):
        """Download images that might not have been downloaded properly in the first place."""
        print(cls.name, ': about to try to get missing resources')
        cls.create_output_dir()
        comics = cls.load_db()
        change = False
        for comic in comics:
            local = comic['local_img']
            for i, (path, url) in enumerate(zip(local, comic['img'])):
                if path is None:
                    new_path = cls.get_file_in_output_dir(url, comic.get('prefix', ''))
                    if new_path is not None:
                        print(cls.name, ': got', url, 'at', new_path)
                        local[i] = new_path
                        change = True
        if change:
            cls.save_db(comics)
            print(cls.long_name, ": some missing resources have been downloaded")


class Xkcd(GenericComic):
    """Class to retrieve Xkcd comics."""
    name = 'xkcd'
    long_name = 'xkcd'
    output_dir = 'xkcd'
    json_file = 'xkcd.json'

    @classmethod
    def get_next_comic(cls, last_comic):
        first_num = last_comic['num'] if last_comic else 0
        last_num = load_json_at_url("http://xkcd.com/info.0.json")['num']

        for num in range(first_num + 1, last_num + 1):
            if num != 404:
                json_url = "http://xkcd.com/%d/info.0.json" % num
                comic = load_json_at_url(json_url)
                comic['img'] = [comic['img']]
                comic['prefix'] = '%d-' % num
                comic['json_url'] = json_url
                comic['url'] = "http://xkcd.com/%d/" % num
                comic['day'] = int(comic['day'])
                comic['month'] = int(comic['month'])
                comic['year'] = int(comic['year'])
                assert comic['num'] == num
                yield comic

#     @classmethod
#     def check_everything_is_ok(cls):
#         comics = cls.load_db()
#         if not comics:
#             return True
#         for comic in comics:
#             num = comic['num']
#             assert isinstance(num, int)
#             assert os.path.isfile(comic['local_img']), \
#                 "Image %s does not exist" % num
#
#         prev = comics[0]
#         for comic in comics[1:]:
#             prev_num, curr_num = prev['num'], comic['num']
#             assert prev_num < curr_num, \
#                 "Comics are not sorted by num (%d %d)" % (prev_num, curr_num)
#             assert get_date_as_int(prev) <= get_date_as_int(comic), \
#                 "Comics are not sorted by date (%d %d)" % (prev_num, curr_num)
#             prev = comic
#         images = dict()
#         for com in comics:
#             images.setdefault(com['img'], []).append(com['url'])
#         for img, lis in images.items():
#             if len(lis) > 1:
#                 print(img, lis)


class ExtraFabulousComics(GenericComic):
    """Class to retrieve Extra Fabulous Comics."""
    name = 'efc'
    long_name = 'Extra Fabulous Comics'
    output_dir = 'efc'
    json_file = 'efc.json'

    @classmethod
    def get_next_comic(cls, last_comic):
        home_url = 'http://extrafabulouscomics.com'
        img_src_re = re.compile(
            '^http://extrafabulouscomics.com/wp-content/uploads/')
        next_comic = \
            get_soup_at_url(last_comic['url']).find('a', title='next') \
            if last_comic else \
            get_soup_at_url(home_url).find('a', title='first')
        while next_comic:
            url = next_comic.get('href')
            soup = get_soup_at_url(url)
            next_comic = soup.find('a', title='next')
            image = soup.find('img', src=img_src_re)
            title = soup.find('meta', attrs={'name': 'twitter:title'}).get('content')
            yield {
                'url': url,
                'title': title,
                'img': [image.get('src')] if image else [],
                'prefix': title + '-'
            }


class Garfield(GenericComic):
    """Class to retrieve Garfield comics."""
    name = 'garfield'
    long_name = 'Garfield'
    output_dir = 'garfield'
    json_file = 'garfield.json'

    @classmethod
    def get_next_comic(cls, last_comic):
        first_day = get_date_for_comic(last_comic) + timedelta(days=1) \
            if last_comic else date(1978, 6, 19)
        home_url = 'http://garfield.com'
        for i in range((date.today() - first_day).days + 1):
            day = first_day + timedelta(days=i)
            day_str = day.isoformat()
            yield {
                'url': "%s/comic/%s" % (home_url, day_str),
                'month': day.month,
                'year': day.year,
                'day': day.day,
                'img': ["%s/uploads/strips/%s.jpg" % (home_url, day_str)],
            }


class Dilbert(GenericComic):
    """Class to retrieve Dilbert comics."""
    name = 'dilbert'
    long_name = 'Dilbert'
    output_dir = 'dilbert'
    json_file = 'dilbert.json'

    @classmethod
    def get_next_comic(cls, last_comic):
        img_src_re = re.compile('^/dyn/str_strip/')
        home_url = 'http://dilbert.com'
        first_day = get_date_for_comic(last_comic) + timedelta(days=1) \
            if last_comic else date(1989, 4, 16)
        for i in range((date.today() - first_day).days + 1):
            day = first_day + timedelta(days=i)
            day_str = day.isoformat()
            url = "%s/strips/comic/%s/" % (home_url, day_str)
            img = get_soup_at_url(url).find('img', src=img_src_re)
            title = img.get('title')
            assert title == "The Dilbert Strip for %s" % \
                (day.strftime("%B %d, %Y").replace(" 0", " "))
            yield {
                'url': url,
                'month': day.month,
                'year': day.year,
                'day': day.day,
                'img': [home_url + img.get('src')],
                'name': title,
                'prefix': '%s-' % day_str
            }


class SaturdayMorningBreakfastCereal(GenericComic):
    """Class to retrieve Saturday Morning Breakfast Cereal comics."""
    name = 'smbc'
    long_name = 'Saturday Morning Breakfast Cereal'
    output_dir = 'smbc'
    json_file = 'smbc.json'

    @classmethod
    def get_next_comic(cls, last_comic):
        last_num = last_comic['num'] if last_comic else 0

        base_url = "http://www.smbc-comics.com"
        archive_page = base_url + "/archives.php"
        comic_link_re = re.compile('^/index.php\\?id=([0-9]*)$')

        for link in get_soup_at_url(archive_page).find_all('a', href=comic_link_re):
            link_url = link.get('href')
            num = int(comic_link_re.match(link_url).groups()[0])
            if num > last_num:
                title = link.string
                url = base_url + link_url
                soup = get_soup_at_url(url)
                image_url1 = soup.find('div', id='comicimage').find('img').get('src')
                image_url2 = soup.find('div', id='aftercomic').find('img').get('src')
                comic = {
                    'url': url,
                    'num': num,
                    'img': [image_url1] + ([image_url2] if image_url2 else []),
                    'title': title
                }
                yield comic


class PerryBibleFellowship(GenericComic):
    """Class to retrieve Perry Bible Fellowship comics."""
    name = 'pbf'
    long_name = 'Perry Bible Fellowship'
    output_dir = 'pbf'
    json_file = 'pbf.json'

    @classmethod
    def get_next_comic(cls, last_comic):
        last_num = last_comic['num'] if last_comic else 0

        home_url = 'http://pbfcomics.com'
        comic_link_re = re.compile('^/[0-9]*/$')
        comic_img_re = re.compile('^/archive_b/PBF.*')

        for link in reversed(get_soup_at_url(home_url).find_all('a', href=comic_link_re)):
            num = int(link.get('name'))
            if num > last_num:
                url = home_url + link.get('href')
                assert url == home_url + "/" + str(num) + "/"
                name = link.string
                image = get_soup_at_url(url).find('img', src=comic_img_re)
                assert image.get('alt') == name
                yield {
                    'url': url,
                    'num': num,
                    'name': name,
                    'img': [home_url + image.get('src')],
                    'prefix': '%d-' % num
                }


class BouletCorp(GenericComic):
    """Class to retrieve BouletCorp comics."""
    name = 'boulet'
    long_name = 'Boulet Corp'
    output_dir = 'boulet'
    json_file = 'boulet.json'

    @classmethod
    def get_next_comic(cls, last_comic):
        home_url = 'http://www.bouletcorp.com'
        date_re = re.compile('^%s/blog/([0-9]*)/([0-9]*)/([0-9]*)/' % home_url)
        prev_url = last_comic['url'] if last_comic else None
        comic_url = (
            get_soup_at_url(prev_url).find('div', id='centered_nav').find_all('a')[3]
            if prev_url
            else get_soup_at_url(home_url).find('div', id='centered_nav').find_all('a')[0]).get('href')

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


class CyanideAndHappiness(GenericComic):
    """Class to retrieve Cyanide And Happiness comics."""
    name = 'cyanide'
    long_name = 'Cyanide and Happiness'
    output_dir = 'cyanide'
    json_file = 'cyanide.json'

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
        base_url = "http://explosm.net"
        img_src_re = re.compile('^http://(www.)?explosm.net/db/files/Comics/.*')
        comic_num_re = re.compile('^http://explosm.net/comics/([0-9]*)/$')

        next_comic = \
            get_soup_at_url(last_comic['url']).find('a', rel='next') \
            if last_comic else \
            get_soup_at_url("http://explosm.net/comics/").find('a', rel='first')

        while next_comic:
            comic_url = base_url + next_comic.get('href')
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

    @classmethod
    def get_next_comic(cls, last_comic):
        # TODO: more info from http://www.mrlovenstein.com/archive
        home_url = 'http://www.mrlovenstein.com'
        comic_num_re = re.compile('^/comic/([0-9]*)$')
        nums = [int(comic_num_re.match(link.get('href')).groups()[0]) for link in get_soup_at_url(home_url).find_all('a', href=comic_num_re)]
        first, last = min(nums), max(nums)
        if last_comic:
            first = last_comic['num'] + 1
        for num in range(first, last+1):
            url = "%s/comic/%d" % (home_url, num)
            soup = get_soup_at_url(url)
            imgs = list(reversed(soup.find_all('img', src=re.compile('^/images/comics/'))))
            yield {
                'url': url,
                'num': num,
                'texts': '  '.join(t for t in (i.get('title') for i in imgs) if t),
                'img': [home_url + i.get('src') for i in imgs],
            }


class DinosaurComics(GenericComic):
    """Class to retrieve Dinosaur Comics comics."""
    name = 'dinosaur'
    long_name = 'Dinosaur Comics'
    output_dir = 'dinosaur'
    json_file = 'dinosaur.json'

    @classmethod
    def get_next_comic(cls, last_comic):
        last_num = last_comic['num'] if last_comic else 0
        comic_link_re = re.compile('^http://www.qwantz.com/index.php\\?comic=([0-9]*)$')
        archive_url = 'http://www.qwantz.com/archive.php'
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
                img = soup.find('img', src=re.compile('^http://www.qwantz.com/comics/'))
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

    @classmethod
    def get_next_comic(cls, last_comic):
        archive_url = 'http://buttersafe.com/archive/'
        comic_link_re = re.compile('^http://buttersafe.com/([0-9]*)/([0-9]*)/([0-9]*)/.*')

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

    @classmethod
    def get_next_comic(cls, last_comic):
        last_date = get_date_for_comic(last_comic) if last_comic else date(1985, 11, 1)

        # This is not through any official webpage but eh...
        base_url = 'http://marcel-oehler.marcellosendos.ch/comics/ch/'
        link_re = re.compile('^([0-9]*)/([0-9]*)/')
        img_re = re.compile('')
        for link in get_soup_at_url(base_url).find_all('a', href=link_re):
            url = link.get('href')
            year, month = link_re.match(url).groups()
            if date(int(year), int(month), 1) + timedelta(days=31) >= last_date:
                img_re = re.compile('^%s%s([0-9]*)' % (year, month))
                month_url = base_url + url
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
                            'img': ['%s%s/%s/%s' % (base_url, year, month, img_src)],
                        }
                        last_date = comic_date


class GenericGoComic(GenericComic):
    """Generic class to handle the logic common to retrieve comics from gocomics.com

    Attributes :
        gocomic_name        Name of the comic on gocomics."""
    gocomic_name = None

    @classmethod
    def get_next_comic(cls, last_comic):
        # logic here will probably be the same for all gocomic comics
        gocomics = 'http://www.gocomics.com'
        url = gocomics + '/' + cls.gocomic_name
        url_date_re = re.compile('.*/([0-9]*)/([0-9]*)/([0-9]*)$')

        next_comic = \
            get_soup_at_url(last_comic['url']).find('a', class_='next') \
            if last_comic else \
            get_soup_at_url(url).find('a', class_='beginning')

        while next_comic:
            url_comic = gocomics + next_comic.get('href')
            year, month, day = [int(s) for s in url_date_re.match(url_comic).groups()]
            soup = get_soup_at_url(url_comic)
            next_comic = soup.find('a', class_='next')
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
    gocomic_name = 'pearlsbeforeswine'


class Peanuts(GenericGoComic):
    """Class to retrieve Peanuts comics."""
    name = 'peanuts'
    long_name = 'Peanuts'
    output_dir = 'peanuts'
    json_file = 'peanuts.json'
    gocomic_name = 'peanuts'


def get_subclasses(klass):
    """Gets the list of direct/indirect subclasses of a class"""
    subclasses = klass.__subclasses__()
    for derived in list(subclasses):
        subclasses.extend(get_subclasses(derived))
    return subclasses

COMIC_NAMES = {c.name: c for c in get_subclasses(GenericComic) if c.name is not None}


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
    args = parser.parse_args()
    if not args.comic:
        args.comic = comic_names
    assert all(c in COMIC_NAMES for c in args.comic)
    for c in args.comic:
        COMIC_NAMES[c].update()

if __name__ == "__main__":
    main()
