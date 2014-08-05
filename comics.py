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


def get_content(url):
    """Get content at url."""
    return urllib.request.urlopen(url).read()


def load_json_at_url(url):
    """Get content at url as JSON."""
    return json.loads(get_content(url).decode())


def get_soup_at_url(url):
    """Get content at url as BeautifulSoup."""
    return BeautifulSoup(get_content(url))


def get_date_as_int(comic):
    """Tmp function to convert comic to dummy date."""
    return 10000 * int(comic['year']) + \
        100 * int(comic['month']) + \
        int(comic['day'])


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
        urllib.request.urlretrieve(url, filename)
        return filename

    @classmethod
    def check_everything_is_ok(cls):
        """Perform tests on the database to check that everything is ok."""
        pass

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
        cls.create_output_dir()
        comics = cls.load_db()
        new_comics = []
        start = time.time()
        try:
            for comic in cls.get_next_comic(comics[-1] if comics else None):
                new_comics.append(comic)
                cls.print_comic(comic)
        finally:
            end = time.time()
            if new_comics:
                print()
                cls.save_db(comics + new_comics)
                print(cls.long_name, ": added", len(new_comics),
                      "comics in ", end-start, "seconds")
            else:
                print(cls.long_name, ": nothing new")


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
                comic['local_img'] = cls.get_file_in_output_dir(
                    comic['img'], '%d-' % num)
                comic['json_url'] = json_url
                comic['url'] = "http://xkcd.com/%d/" % num
                assert comic['num'] == num
                yield comic

    @classmethod
    def check_everything_is_ok(cls):
        comics = cls.load_db()
        if not comics:
            return True
        for comic in comics:
            num = comic['num']
            assert isinstance(num, int)
            assert os.path.isfile(comic['local_img']), \
                "Image %s does not exist" % num

        prev = comics[0]
        for comic in comics[1:]:
            prev_num, curr_num = prev['num'], comic['num']
            assert prev_num < curr_num, \
                "Comics are not sorted by num (%d %d)" % (prev_num, curr_num)
            assert get_date_as_int(prev) <= get_date_as_int(comic), \
                "Comics are not sorted by date (%d %d)" % (prev_num, curr_num)
            prev = comic
        images = dict()
        for com in comics:
            images.setdefault(com['img'], []).append(com['url'])
        for img, lis in images.items():
            if len(lis) > 1:
                print(img, lis)


class ExtraFabulousComics(GenericComic):
    """Class to retrieve Extra Fabulous Comics."""
    name = 'efc'
    long_name = 'extra fabulous comics'
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
            comic = {
                'url': url,
                'title': soup.find('meta', attrs={'name': 'twitter:title'}).get('content')
            }
            image = soup.find('img', src=img_src_re)
            if image:
                image_url = image.get('src')
                comic['img'] = image_url
                comic['local_img'] = cls.get_file_in_output_dir(image_url)
            else:
                comic['error'] = 'no image'  # weird shit man
            yield comic


class Dilbert(GenericComic):
    """Class to retrieve Dilbert comics."""
    name = 'dilbert'
    long_name = 'dilbert'
    output_dir = 'dilbert'
    json_file = 'dilbert.json'

    @classmethod
    def get_next_comic(cls, last_comic):
        img_src_re = re.compile('^/dyn/str_strip/')
        home_url = 'http://dilbert.com'
        first_day = date(last_comic['year'],
                         last_comic['month'],
                         last_comic['day']) + timedelta(days=1) \
            if last_comic else date(1989, 4, 16)
        for i in range((date.today() - first_day).days + 1):
            day = first_day + timedelta(days=i)
            day_str = day.isoformat()
            url = "%s/strips/comic/%s/" % (home_url, day_str)
            img = get_soup_at_url(url).find('img', src=img_src_re)
            img_url = home_url + img.get('src')
            title = img.get('title')
            assert title == "The Dilbert Strip for %s" % \
                (day.strftime("%B %d, %Y").replace(" 0", " "))
            yield {
                'url': url,
                'month': day.month,
                'year': day.year,
                'day': day.day,
                'img': img_url,
                'name': title,
                'local_img': cls.get_file_in_output_dir(
                    img_url,
                    '%s-' % day_str)
            }


class SaturdayMorningBreakfastCereal(GenericComic):
    """Class to retrieve Saturday Morning Breakfast Cereal comics."""
    name = 'smbc'
    long_name = 'saturday morning breakfast cereal'
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
                image_url = soup.find('div', id='comicimage').find('img').get('src')
                comic = {
                    'url': url,
                    'num': num,
                    'img': image_url,
                    'local_img': cls.get_file_in_output_dir(image_url),
                    'title': title
                }
                image_url2 = soup.find('div', id='aftercomic').find('img').get('src')
                if image_url2:
                    comic['img2'] = image_url2
                    comic['local_img2'] = cls.get_file_in_output_dir(image_url2)
                yield comic


class PerryBibleFellowship(GenericComic):
    """Class to retrieve Perry Bible Fellowship comics."""
    name = 'pbf'
    long_name = 'perry bible fellowship'
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
                image_url = home_url + image.get('src')
                yield {
                    'url': url,
                    'num': num,
                    'name': name,
                    'img': image_url,
                    'local_img': cls.get_file_in_output_dir(
                        image_url,
                        '%d-' % num)
                }


class CyanideAndHappiness(GenericComic):
    """Class to retrieve Cyanide And Happiness comics."""
    name = 'cyanide'
    long_name = 'cyanide and happiness'
    output_dir = 'cyanide'
    json_file = 'cyanide.json'

    @classmethod
    def get_next_comic(cls, last_comic):
        base_url = "http://explosm.net"
        author_url_re = re.compile('^http://explosm.net/comics/author/.*')
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
            author = soup.find('a', href=author_url_re)
            comic = {
                'num': num,
                'url': comic_url,
                'author': author.string if author is not None else 'none'
                }
            image = soup.find('img', src=img_src_re)
            if image:
                img = image.get('src')
                comic['img'] = img
                comic['local_img'] = cls.get_file_in_output_dir(
                    img,
                    '%d-' % num)
            else:
                comic['error'] = 'no image'  # weird shit man
            yield comic


def main():
    """Main function"""
    for comic in [SaturdayMorningBreakfastCereal,
                  Xkcd,
                  CyanideAndHappiness,
                  PerryBibleFellowship,
                  ExtraFabulousComics,
                  Dilbert]:
        comic.update()

if __name__ == "__main__":
    main()
