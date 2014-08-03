#! /usr/bin/python3
# vim: set expandtab tabstop=4 shiftwidth=4 :
"""Module to retrieve webcomics"""

import os
import json
import urllib.request
import urllib.parse
import re
from bs4 import BeautifulSoup


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
        filename = os.path.join(cls.output_dir, ('' if prefix is None else prefix) + urllib.parse.unquote(url).split('/')[-1])
        urllib.request.urlretrieve(url, filename)
        return filename

    @classmethod
    def check_everything_is_ok(cls):
        pass

# TODO
# def update_wrapper():
#   create_output_dir
#   comics = load_db()
#   new_comics = get_new_comics(comics[-1] if comics else None)
#   save(comics+new_comics)


class Xkcd(GenericComic):
    name = 'xkcd'
    long_name = 'xkcd'
    output_dir = 'xkcd'
    json_file = 'xkcd.json'

    @classmethod
    def update(cls):
        cls.create_output_dir()
        comics = cls.load_db()

        first_num = comics[-1]['num'] if comics else 0
        last_num = load_json_at_url("http://xkcd.com/info.0.json")['num']

        try:
            for num in range(first_num + 1, last_num + 1):
                try:
                    json_url = "http://xkcd.com/%d/info.0.json" % num
                    comic_info = load_json_at_url(json_url)
                    comic_info['local_img'] = cls.get_file_in_output_dir(comic_info['img'], '%d-' % num)
                    comic_info['json_url'] = json_url
                    comic_info['url'] = "http://xkcd.com/%d/" % num
                    assert comic_info['num'] == num
                    print(cls.name, ':', comic_info['year'], comic_info['month'], comic_info['day'], comic_info['num'], comic_info['img'], ' ' * 10, '\r', end='')
                    comics.append(comic_info)
                except urllib.error.HTTPError as e:
                    if num != 404:
                        print(e, num)
        finally:
            cls.save_db(comics)
            print(cls.long_name, "updated")

    def get_date_as_int(comic):
        return 10000 * int(comic['year']) + 100 * int(comic['month']) + int(comic['day'])

    @classmethod
    def check_everything_is_ok(cls):
        comics = cls.load_db()
        if not comics:
            return True
        for comic in comics:
            num = comic['num']
            assert isinstance(num, int)
            assert os.path.isfile(comic['local_img']), "Image does not exist" % num
        prev = comics[0]
        for comic in comics[1:]:
            prev_num, curr_num = prev['num'], comic['num']
            assert prev_num < curr_num, "Comics are not sorted by num (%d %d)" % (prev_num, curr_num)
            assert cls.get_date_as_int(prev) <= cls.get_date_as_int(comic), "Comics are not sorted by date (%d %d)" % (prev_num, curr_num)
            prev = comic
        images = dict()
        for c in comics:
            images.setdefault(c['img'], []).append(c['url'])
        for img, l in images.items():
            if len(l) > 1:
                print(img, l)


class ExtraFabulousComics(GenericComic):
    name = 'efc'
    long_name = 'extra fabulous comics'
    output_dir = 'efc'
    json_file = 'efc.json'

    @classmethod
    def update(cls):
        cls.create_output_dir()
        comics = [] # cls.load_db()
        home_url = 'http://extrafabulouscomics.com'
        reComicLink = re.compile('^http://extrafabulouscomics.com/wp-content/uploads/')
        next_comic = get_soup_at_url(comics[-1]['url']).find('a', title='next') if comics else \
                    get_soup_at_url(home_url).find('a', title='first')
        try:
            while next_comic:
                url = next_comic.get('href')
                soup = get_soup_at_url(url)
                image = soup.find('img', src=reComicLink)
                image_url = image.get('src')
                next_comic = soup.find('a', title='next')
                title = soup.find_all('meta', attrs={'name': 'twitter:title'})
                comic_info = {
                    'url': url,
                    'img': image_url,
                    'local_img': cls.get_file_in_output_dir(image_url),
                    'title': title
                }
                print(cls.name, ':', url, image_url, ' ' * 10, '\r', end='')
                comics.append(comic_info)
        finally:
            cls.save_db(comics)
            print(cls.long_name, "updated")


class Dilbert(GenericComic):
    name = 'dilbert'
    long_name = 'dilbert'
    output_dir = 'dilbert'
    json_file = 'dilbert.json'


class SaturdayMorningBreakfastCereal(GenericComic):
    name = 'smbc'
    long_name = 'saturday morning breakfast cereal'
    output_dir = 'smbc'
    json_file = 'smbc.json'

    @classmethod
    def update(cls):
        cls.create_output_dir()
        base_url = "http://www.smbc-comics.com"
        next_comic = {'href': "?id=1#comic"}
        while next_comic:
            comic_url = base_url + next_comic.get('href')
            soup = get_soup_at_url(comic_url)
            print(soup)
            next_comic = False


class PerryBibleFellowship(GenericComic):
    name = 'perry bible fellowship'
    long_name = 'pbf'
    output_dir = 'pbf'
    json_file = 'pbf.json'

    @classmethod
    def update(cls):
        cls.create_output_dir()
        comics = cls.load_db()
        last_num = comics[-1]['num'] if comics else 0

        home_url = 'http://pbfcomics.com'
        reComicLink = re.compile('^/[0-9]*/$')
        soup = get_soup_at_url(home_url)
        links = soup.find_all('a', href=reComicLink)

        try:
            for l in reversed(links):
                num = int(l.get('name'))
                if num > last_num:
                    url = home_url + l.get('href')
                    assert url == home_url + "/" + str(num) + "/"
                    name = l.string
                    image = get_soup_at_url(url).find('img', src=re.compile('^/archive_b/PBF.*'))
                    assert image.get('alt') == name
                    image_url = home_url + image.get('src')
                    comic_info = {
                        'url': url,
                        'num': num,
                        'name': name,
                        'img': image_url,
                        'local_img': cls.get_file_in_output_dir(image_url, '%d-' % num)
                    }
                    print(cls.name, ':', url, num, name, image_url, ' ' * 10, '\r', end='')
                    comics.append(comic_info)
        finally:
            cls.save_db(comics)
            print(cls.long_name, "updated")


class CyanideAndHappiness(GenericComic):
    long_name = 'cyanide and happiness'
    name = 'cyanide'
    output_dir = 'cyanide'
    json_file = 'cyanide.json'

    @classmethod
    def update(cls):
        base_url = "http://explosm.net"
        reAuthorSrc = re.compile('^http://explosm.net/comics/author/.*')
        reComicSrc = re.compile('^http://(www.)?explosm.net/db/files/Comics/.*')
        reComicUrl = re.compile('^http://explosm.net/comics/([0-9]*)/$')

        cls.create_output_dir()
        comics = cls.load_db()

        next_comic = \
            get_soup_at_url(comics[-1]['url']).find('a', rel='next') if comics else \
            get_soup_at_url("http://explosm.net/comics/").find('a', rel='first')

        try:
            while next_comic:
                comic_url = base_url + next_comic.get('href')
                num = int(reComicUrl.match(comic_url).groups()[0])
                soup = get_soup_at_url(comic_url)
                next_comic = soup.find('a', rel='next')
                author = soup.find('a', href=reAuthorSrc)
                comic_info = {
                    'num': num,
                    'url': comic_url,
                    'author': author.string if author is not None else 'none'
                    }
                image = soup.find('img', src=reComicSrc)
                if image:
                    img = image.get('src')
                    comic_info['img'] = img
                    comic_info['local_img'] = cls.get_file_in_output_dir(img, '%d-' % num)
                else:
                    comic_info['error'] = 'no image'  # weird shit man
                print(cls.name, ':', comic_url, comic_info['author'], ' ' * 10, '\r', end='')
                comics.append(comic_info)
        finally:
            cls.save_db(comics)
            print(cls.long_name, "updated")


def main():
    """Main function"""
    print("Hello, world!")
    # for c in [SaturdayMorningBreakfastCereal]:
    for c in [Xkcd, PerryBibleFellowship, CyanideAndHappiness, ExtraFabulousComics]:
        c.update()

if __name__ == "__main__":
    main()
