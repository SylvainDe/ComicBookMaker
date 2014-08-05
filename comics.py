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
    return urllib.request.urlopen(url).read()


def load_json_at_url(url):
    return json.loads(get_content(url).decode())


def get_soup_at_url(url):
    return BeautifulSoup(get_content(url))


class GenericComic(object):
    name = None
    long_name = None
    output_dir = None
    json_file = None

    @classmethod
    def create_output_dir(cls):
        os.makedirs(cls.output_dir, exist_ok=True)

    @classmethod
    def get_json_file_path(cls):
        return os.path.join(cls.output_dir, cls.json_file)

    @classmethod
    def load_db(cls):
        try:
            with open(cls.get_json_file_path()) as file:
                return json.load(file)
        except IOError:
            return []

    @classmethod
    def save_db(cls, data):
        with open(cls.get_json_file_path(), 'w+') as file:
            json.dump(data, file, indent=4)

    @classmethod
    def get_file_in_output_dir(cls, url, prefix=None):
        filename = os.path.join(
            cls.output_dir,
            ('' if prefix is None else prefix) +
            urllib.parse.unquote(url).split('/')[-1])
        urllib.request.urlretrieve(url, filename)
        return filename

    @classmethod
    def check_everything_is_ok(cls):
        pass

    @classmethod
    def get_next_comic(cls, _):
        pass

    @classmethod
    def update(cls):
        cls.create_output_dir()
        comics = cls.load_db()
        new_comics = []
        start = time.time()
        try:
            for comic in cls.get_next_comic(comics[-1] if comics else None):
                new_comics.append(comic)
        finally:
            end = time.time()
            if new_comics:
                print()
                cls.save_db(comics + new_comics)
                print(cls.long_name, ": added", len(new_comics), "comics in ", end-start, "seconds")
            else:
                print(cls.long_name, ": nothing new")


class Xkcd(GenericComic):
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
                print(cls.name, ':', comic['year'], comic['month'], comic['day'], comic['num'], comic['img'], ' ' * 10, '\r', end='')
                yield comic

    def get_date_as_int(comic):
        return 10000 * int(comic['year']) + \
            100 * int(comic['month']) + \
            int(comic['day'])

    @classmethod
    def check_everything_is_ok(cls):
        comics = cls.load_db()
        if not comics:
            return True
        for comic in comics:
            num = comic['num']
            assert isinstance(num, int)
            assert os.path.isfile(comic['local_img']), "Image %s does not exist" % num
        prev = comics[0]
        for comic in comics[1:]:
            prev_num, curr_num = prev['num'], comic['num']
            assert prev_num < curr_num, "Comics are not sorted by num (%d %d)" % (prev_num, curr_num)
            assert cls.get_date_as_int(prev) <= cls.get_date_as_int(comic), "Comics are not sorted by date (%d %d)" % (prev_num, curr_num)
            prev = comic
        images = dict()
        for com in comics:
            images.setdefault(com['img'], []).append(com['url'])
        for img, lis in images.items():
            if len(lis) > 1:
                print(img, lis)


class ExtraFabulousComics(GenericComic):
    name = 'efc'
    long_name = 'extra fabulous comics'
    output_dir = 'efc'
    json_file = 'efc.json'

    @classmethod
    def get_next_comic(cls, last_comic):
        home_url = 'http://extrafabulouscomics.com'
        img_src_re = re.compile('^http://extrafabulouscomics.com/wp-content/uploads/')
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
            print(cls.name, ':', url, ' ' * 10, '\r', end='')
            yield comic


class Dilbert(GenericComic):
    name = 'dilbert'
    long_name = 'dilbert'
    output_dir = 'dilbert'
    json_file = 'dilbert.json'

    @classmethod
    def get_next_comic(cls, last_comic):
        img_src_re = re.compile('^/dyn/str_strip/')
        home_url = 'http://dilbert.com'
        first_day = date(last_comic['year'], last_comic['month'], last_comic['day']) + timedelta(days=1) if last_comic else date(1989, 4, 16)
        for i in range((date.today() - first_day).days + 1):
            day = first_day + timedelta(days=i)
            day_str = day.isoformat()
            url = "%s/strips/comic/%s/" % (home_url, day_str)
            img = get_soup_at_url(url).find('img', src=img_src_re)
            img_url = home_url + img.get('src')
            title = img.get('title')  # "The Dilbert Strip for January 4, 2014"
            assert title == "The Dilbert Strip for %s" % (day.strftime("%B %d, %Y").replace(" 0", " "))
            comic = {
                'url': url,
                'month': day.month,
                'year': day.year,
                'day': day.day,
                'img': img_url,
                'name': title,
                'local_img': cls.get_file_in_output_dir(img_url, '%s-' % day_str)
            }
            print(cls.name, ':', url, ' ' * 10, '\r', end='')
            yield comic


class SaturdayMorningBreakfastCereal(GenericComic):
    name = 'smbc'
    long_name = 'saturday morning breakfast cereal'
    output_dir = 'smbc'
    json_file = 'smbc.json'

    @classmethod
    def get_next_comic(cls, last_comic):
        base_url = "http://www.smbc-comics.com"
        next_comic = {'href': "?id=1#comic"}
        print(last_comic)
        while next_comic:
            comic_url = base_url + next_comic.get('href')
            soup = get_soup_at_url(comic_url)
            print(soup)
            next_comic = False


class PerryBibleFellowship(GenericComic):
    name = 'pbf'
    long_name = 'perry bible fellowship'
    output_dir = 'pbf'
    json_file = 'pbf.json'

    @classmethod
    def get_next_comic(cls, last_comic):
        last_num = last_comic['num'] if last_comic else 0

        home_url = 'http://pbfcomics.com'
        comic_link_re = re.compile('^/[0-9]*/$')

        for link in reversed(get_soup_at_url(home_url).find_all('a', href=comic_link_re)):
            num = int(link.get('name'))
            if num > last_num:
                url = home_url + link.get('href')
                assert url == home_url + "/" + str(num) + "/"
                name = link.string
                image = get_soup_at_url(url).find('img', src=re.compile('^/archive_b/PBF.*'))
                assert image.get('alt') == name
                image_url = home_url + image.get('src')
                comic = {
                    'url': url,
                    'num': num,
                    'name': name,
                    'img': image_url,
                    'local_img': cls.get_file_in_output_dir(image_url, '%d-' % num)
                }
                print(cls.name, ':', url, num, name, image_url, ' ' * 10, '\r', end='')
                yield comic


class CyanideAndHappiness(GenericComic):
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
            get_soup_at_url(last_comic['url']).find('a', rel='next') if last_comic else \
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
                comic['local_img'] = cls.get_file_in_output_dir(img, '%d-' % num)
            else:
                comic['error'] = 'no image'  # weird shit man
            print(cls.name, ':', comic_url, comic['author'], ' ' * 10, '\r', end='')
            yield comic


def main():
    """Main function"""
    for comic in [Xkcd,
                  CyanideAndHappiness,
                  PerryBibleFellowship,
                  ExtraFabulousComics,
                  Dilbert]:
        comic.update()

if __name__ == "__main__":
    main()
