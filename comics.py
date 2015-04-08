#! /usr/bin/python3
# vim: set expandtab tabstop=4 shiftwidth=4 :
"""Module to retrieve webcomics"""

from comic_abstract import GenericComic, get_date_for_comic
import re
from datetime import date, timedelta
import datetime
from urlfunctions import get_soup_at_url, urljoin_wrapper, convert_iri_to_plain_ascii_uri, load_json_at_url


class Xkcd(GenericComic):
    """Class to retrieve Xkcd comics."""
    name = 'xkcd'
    long_name = 'xkcd'
    url = 'http://xkcd.com'

    @classmethod
    def get_next_comic(cls, last_comic):
        first_num = last_comic['num'] if last_comic else 0
        last_num = load_json_at_url(
            urljoin_wrapper(cls.url, 'info.0.json'))['num']

        for num in range(first_num + 1, last_num + 1):
            if num != 404:
                json_url = urljoin_wrapper(cls.url, '%d/info.0.json' % num)
                comic = load_json_at_url(json_url)
                comic['img'] = [comic['img']]
                comic['prefix'] = '%d-' % num
                comic['json_url'] = json_url
                comic['url'] = urljoin_wrapper(cls.url, str(num))
                comic['day'] = int(comic['day'])
                comic['month'] = int(comic['month'])
                comic['year'] = int(comic['year'])
                assert comic['num'] == num
                yield comic


class ExtraFabulousComics(GenericComic):
    """Class to retrieve Extra Fabulous Comics."""
    name = 'efc'
    long_name = 'Extra Fabulous Comics'
    url = 'http://extrafabulouscomics.com'

    @classmethod
    def get_next_comic(cls, last_comic):
        img_src_re = re.compile('^%s/wp-content/uploads/' % cls.url)
        next_comic = \
            get_soup_at_url(last_comic['url']).find('a', title='next') \
            if last_comic else \
            get_soup_at_url(cls.url).find('a', title='first')
        while next_comic:
            url = next_comic['href']
            soup = get_soup_at_url(url)
            next_comic = soup.find('a', title='next')
            image = soup.find('img', src=img_src_re)
            title = soup.find(
                'meta',
                attrs={'name': 'twitter:title'}).get('content')
            yield {
                'url': url,
                'title': title,
                'img': [image['src']] if image else [],
                'prefix': title + '-'
            }


class NeDroid(GenericComic):
    """Class to retrieve NeDroid comics."""
    name = 'nedroid'
    long_name = 'NeDroid'
    url = 'http://nedroid.com'

    @classmethod
    def get_next_comic(cls, last_comic):
        comic_url_re = re.compile(
            '^%s/comics/([0-9]*)-([0-9]*)-([0-9]*).*' % cls.url)
        short_url_re = re.compile('^%s/\\?p=([0-9]*)' % cls.url)

        next_comic = \
            get_soup_at_url(last_comic['url']).find('div', class_='nav-next').find('a') \
            if last_comic else \
            get_soup_at_url(cls.url).find('div', class_='nav-first').find('a')

        while next_comic:
            url = next_comic['href']
            soup = get_soup_at_url(url)
            img = soup.find('img', src=comic_url_re)
            img_url = img['src']
            assert url == soup.find('link', rel='canonical')['href']
            next_comic = soup.find('div', class_='nav-next').find('a')
            short_url = soup.find('link', rel='shortlink')['href']
            year, month, day = [int(s)
                                for s in comic_url_re.match(img_url).groups()]
            num = int(short_url_re.match(short_url).groups()[0])
            yield {
                'url': url,
                'short_url': short_url,
                'title': img.get('alt'),
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
    url = 'http://garfield.com'

    @classmethod
    def get_next_comic(cls, last_comic):
        first_day = get_date_for_comic(last_comic) + timedelta(days=1) \
            if last_comic else date(1978, 6, 19)
        for i in range((date.today() - first_day).days + 1):
            day = first_day + timedelta(days=i)
            day_str = day.isoformat()
            yield {
                'url': urljoin_wrapper(cls.url, 'comic/%s' % day_str),
                'month': day.month,
                'year': day.year,
                'day': day.day,
                'img': [urljoin_wrapper(cls.url, 'uploads/strips/%s.jpg' % day_str)],
            }


class Dilbert(GenericComic):
    """Class to retrieve Dilbert comics."""
    # name = 'dilbert'
    long_name = 'Dilbert'
    url = 'http://dilbert.com'

    @classmethod
    def get_next_comic(cls, last_comic):
        img_src_re = re.compile('^/dyn/str_strip/')
        first_day = get_date_for_comic(last_comic) + timedelta(days=1) \
            if last_comic else date(1989, 4, 16)
        for i in range((date.today() - first_day).days + 1):
            day = first_day + timedelta(days=i)
            day_str = day.isoformat()
            url = urljoin_wrapper(cls.url, 'strips/comic/%s/' % day_str)
            img = get_soup_at_url(url).find('img', src=img_src_re)
            title = img.get('title')
            if title != "The Dilbert Strip for %s" % \
                    (day.strftime("%B %d, %Y").replace(" 0", " ")):
                return  # daily comic might not be published
            yield {
                'url': url,
                'month': day.month,
                'year': day.year,
                'day': day.day,
                'img': [urljoin_wrapper(url, img['src'])],
                'name': title,
                'prefix': '%s-' % day_str
            }


class ThreeWordPhrase(GenericComic):
    """Class to retrieve Three Word Phrase comics."""
    name = 'threeword'
    long_name = 'Three Word Phrase'
    url = 'http://threewordphrase.com'

    @classmethod
    def get_next_comic(cls, last_comic):
        next_url = (
            get_soup_at_url(last_comic['url']).find('img', src='/nextlink.gif')
            if last_comic else
            get_soup_at_url(cls.url).find('img', src='/firstlink.gif')
        ).parent.get('href')

        while next_url:
            comic_url = urljoin_wrapper(cls.url, next_url)
            soup = get_soup_at_url(comic_url)
            title = soup.find('title')
            # hackish way to get the image
            imgs = [img for img in soup.find_all('img')
                    if not img['src'].endswith(
                        ('link.gif', '32.png', 'twpbookad.jpg',
                         'merchad.jpg', 'header.gif', 'tipjar.jpg'))]
            yield {
                'url': comic_url,
                'title': title.string if title else None,
                'title2': '  '.join(img.get('alt') for img in imgs if img.get('alt')),
                'img': [urljoin_wrapper(comic_url, img['src']) for img in imgs],
            }
            next_url = soup.find('img', src='/nextlink.gif').parent.get('href')


class TheGentlemanArmchair(GenericComic):
    """Class to retrieve The Gentleman Armchair comics."""
    name = 'gentlemanarmchair'
    long_name = 'The Gentleman Armchair'
    url = 'http://thegentlemansarmchair.com'

    @classmethod
    def get_next_comic(cls, last_comic):
        waiting_for_url = last_comic['url'] if last_comic else None
        archive_url = urljoin_wrapper(cls.url, 'archive')
        for tr in reversed(get_soup_at_url(archive_url).find_all('tr', class_='archive-tr')):
            date_td, content_td = tr.children
            a_tag = content_td.find('a')
            url = a_tag['href']
            if waiting_for_url and waiting_for_url == url:
                waiting_for_url = None
            elif waiting_for_url is None:
                title = a_tag.string
                day = string_to_date(date_td.string, "%b %d %Y")
                soup = get_soup_at_url(url)
                imgs = soup.find('div', id='comic').find_all('img')
                yield {
                    'url': url,
                    'img': [i['src'] for i in imgs],
                    'title': title,
                    'month': day.month,
                    'year': day.year,
                    'day': day.day,
                }


class SaturdayMorningBreakfastCereal(GenericComic):
    """Class to retrieve Saturday Morning Breakfast Cereal comics."""
    name = 'smbc'
    long_name = 'Saturday Morning Breakfast Cereal'
    url = 'http://www.smbc-comics.com'

    @classmethod
    def get_next_comic(cls, last_comic):
        last_num = last_comic['num'] if last_comic else 0
        last_date = get_date_for_comic(last_comic) if last_comic else None

        archive_page = urljoin_wrapper(cls.url, '/archives.php')
        comic_link_re = re.compile('^/index.php\\?id=([0-9]*)$')

        for link in get_soup_at_url(archive_page).find_all('a', href=comic_link_re):
            link_url = link['href']
            num = int(comic_link_re.match(link_url).groups()[0])
            if num > last_num:
                url = urljoin_wrapper(cls.url, link_url)
                soup = get_soup_at_url(url)
                image_url1 = soup.find(
                    'div', id='comicimage').find('img')['src']
                image_url2 = soup.find(
                    'div', id='aftercomic').find('img')['src']
                title = link.string
                date_str = soup.find('p', class_='date').string  # many of them, take the first
                assert date_str == title
                day = last_date \
                    if date_str == '(no date)' else \
                    string_to_date(date_str, "%B %d, %Y")
                comic = {
                    'url': url,
                    'num': num,
                    'img': [image_url1] + ([image_url2] if image_url2 else []),
                    'title': title,
                    'month': day.month,
                    'year': day.year,
                    'day': day.day,
                }
                last_date = get_date_for_comic(comic)
                yield comic


class PerryBibleFellowship(GenericComic):
    """Class to retrieve Perry Bible Fellowship comics."""
    name = 'pbf'
    long_name = 'Perry Bible Fellowship'
    url = 'http://pbfcomics.com'

    @classmethod
    def get_next_comic(cls, last_comic):
        last_num = last_comic['num'] if last_comic else 0

        comic_link_re = re.compile('^/[0-9]*/$')
        comic_img_re = re.compile('^/archive_b/PBF.*')

        for link in reversed(get_soup_at_url(cls.url).find_all('a', href=comic_link_re)):
            num = int(link['name'])
            if num > last_num:
                href = link['href']
                assert href == '/%d/' % num
                url = urljoin_wrapper(cls.url, href)
                name = link.string
                image = get_soup_at_url(url).find('img', src=comic_img_re)
                assert image['alt'] == name
                yield {
                    'url': url,
                    'num': num,
                    'name': name,
                    'img': [urljoin_wrapper(url, image['src'])],
                    'prefix': '%d-' % num
                }


class BerkeleyMews(GenericComic):
    """Class to retrieve Berkeley Mews comics."""
    name = 'berkeley'
    long_name = 'Berkeley Mews'
    url = 'http://www.berkeleymews.com'

    @classmethod
    def get_next_comic(cls, last_comic):
        archive_url = urljoin_wrapper(cls.url, "?page_id=2")
        last_num = last_comic['num'] if last_comic else 0

        comic_num_re = re.compile('%s/\\?p=([0-9]*)$' % cls.url)
        comic_date_re = re.compile('.*/([0-9]*)-([0-9]*)-([0-9]*)-.*')
        for link in reversed(get_soup_at_url(archive_url).find_all('a', href=comic_num_re)):
            comic_url = link['href']
            num = int(comic_num_re.match(comic_url).groups()[0])
            if num > last_num:
                img = get_soup_at_url(comic_url).find(
                    'div', id='comic').find('img')
                img_url = img['src']
                year, month, day = [
                    int(s) for s in comic_date_re.match(img_url).groups()]
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


class GenericBouletCorp(GenericComic):
    """Generic class to retrieve BouletCorp comics in different languages.

    Attributes :
        date_re : regexp to get the date from the url."""

    @classmethod
    def get_next_comic(cls, last_comic):
        date_re = re.compile(cls.date_re % cls.url)

        prev_url = last_comic['url'] if last_comic else None
        comic_url = (
            get_soup_at_url(prev_url).find(
                'div', id='centered_nav').find_all('a')[3]
            if prev_url
            else get_soup_at_url(cls.url).find('div', id='centered_nav').find_all('a')[0]).get('href')

        while comic_url != prev_url:
            year, month, day = [int(s)
                                for s in date_re.match(comic_url).groups()]
            soup = get_soup_at_url(comic_url)
            imgs = soup.find('div', id='notes').find(
                'div', class_='storycontent').find_all('img')
            texts = '  '.join(t for t in (i.get('title') for i in imgs) if t)
            title = soup.find('title').string
            comic = {
                'url': comic_url,
                'img': [convert_iri_to_plain_ascii_uri(i['src']) for i in imgs],
                'title': title,
                'texts': texts,
                'year': year,
                'month': month,
                'day': day,
            }
            yield comic
            prev_url, comic_url = comic_url, soup.find(
                'div', id='centered_nav').find_all('a')[3].get('href')


class BouletCorp(GenericBouletCorp):
    """Class to retrieve BouletCorp comics."""
    name = 'boulet'
    long_name = 'Boulet Corp'
    url = 'http://www.bouletcorp.com'
    date_re = '^%s/([0-9]*)/([0-9]*)/([0-9]*)/'


class BouletCorpEn(GenericBouletCorp):
    """Class to retrieve EnglishBouletCorp comics."""
    name = 'boulet_en'
    long_name = 'Boulet Corp English'
    url = 'http://english.bouletcorp.com'
    date_re = '^%s/([0-9]*)/([0-9]*)/([0-9]*)/'


class AmazingSuperPowers(GenericComic):
    """Class to retrieve Amazing Super Powers comics."""
    name = 'asp'
    long_name = 'Amazing Super Powers'
    url = 'http://www.amazingsuperpowers.com'
    # images are not retrieved properly, I guess the user-agent it not ok

    @classmethod
    def get_next_comic(cls, last_comic):
        link_re = re.compile('^%s/([0-9]*)/([0-9]*)/.*$' % cls.url)
        img_re = re.compile('^%s/comics/.*$' % cls.url)
        archive_url = urljoin_wrapper(cls.url, 'category/comics/')
        last_date = get_date_for_comic(
            last_comic) if last_comic else date(2000, 1, 1)
        for link in reversed(get_soup_at_url(archive_url).find_all('a', href=link_re)):
            comic_date = string_to_date(link.parent.previous_sibling.string, "%b %d, %Y")
            if comic_date > last_date:
                title = link.string
                comic_url = link['href']
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


class ToonHole(GenericComic):
    """Class to retrieve Toon Holes comics."""
    name = 'toonhole'
    long_name = 'Toon Hole'
    url = 'http://www.toonhole.com'

    @classmethod
    def get_next_comic(cls, last_comic):
        waiting_for_url = last_comic['url'] if last_comic else None
        archive_url = urljoin_wrapper(cls.url, 'archive/')
        for link in reversed(get_soup_at_url(archive_url).find_all('a', rel='bookmark')):
            url = link['href']
            if waiting_for_url and waiting_for_url == url:
                waiting_for_url = None
            elif waiting_for_url is None:
                title = link.string
                soup = get_soup_at_url(url)
                day = string_to_date(remove_st_nd_rd_th_from_date(soup.find('div', class_='comicdate').string.strip()), "%B %d, %Y")
                imgs = soup.find('div', id='comic').find_all('img')
                assert all(i['alt'] == i['title'] == title for i in imgs)
                yield {
                    'url': url,
                    'title': title,
                    'month': day.month,
                    'year': day.year,
                    'day': day.day,
                    'img': [convert_iri_to_plain_ascii_uri(i['src']) for i in imgs],
                }


class Channelate(GenericComic):
    """Class to retrieve Channelate comics."""
    name = 'channelate'
    long_name = 'Channelate'
    url = 'http://www.channelate.com'

    @classmethod
    def get_next_comic(cls, last_comic):
        link_re = re.compile('^%s/([0-9]*)/([0-9]*)/([0-9]*)/.*$' % cls.url)
        archive_url = urljoin_wrapper(cls.url, 'note-to-self-archive/')
        prev_date = get_date_for_comic(
            last_comic) if last_comic else date(2000, 1, 1)

        for link in reversed(get_soup_at_url(archive_url).find_all('a', href=link_re, rel='bookmark')):
            comic_url = link['href']
            title = link.string
            year, month, day = [int(s)
                                for s in link_re.match(comic_url).groups()]
            if prev_date < date(year, month, day):
                soup = get_soup_at_url(comic_url)
                img = soup.find('div', id='comic-1').find('img')
                assert title == soup.find(
                    'meta', property='og:title')['content']
                img_urls = []
                if img:
                    # almost == title but not quite
                    assert img['alt'] == img['title']
                    img_urls.append(img['src'])
                extra_url = None
                extra_div = soup.find('div', id='extrapanelbutton')
                if extra_div:
                    extra_url = extra_div.find('a')['href']
                    img_urls.append(
                        get_soup_at_url(extra_url).find('img', class_='extrapanelimage')['src'])
                yield {
                    'url': comic_url,
                    'url_extra': extra_url,
                    'title': title,
                    'day': day,
                    'month': month,
                    'year': year,
                    'img': [img['src']] if img else [],
                }


class CyanideAndHappiness(GenericComic):
    """Class to retrieve Cyanide And Happiness comics."""
    name = 'cyanide'
    long_name = 'Cyanide and Happiness'
    url = 'http://explosm.net'

    @classmethod
    def get_next_comic(cls, last_comic):

        next_comic = \
            get_soup_at_url(last_comic['url']).find('a', class_='next-comic') \
            if last_comic else {'href': "/comics/15"}

        while next_comic['href'] != '#':
            comic_url = urljoin_wrapper(cls.url, next_comic['href'])
            soup = get_soup_at_url(comic_url)
            day_url = soup.find('h3').find('a')
            num = int(day_url['href'].split('/')[-1])
            day = string_to_date(day_url.string, '%Y.%m.%d')
            author = soup.find('small', class_="author-credit-name").string
            assert author.startswith('by ')
            author = author[3:]
            next_comic = soup.find('a', class_='next-comic')
            imgs = soup.find_all('img', id='main-comic')
            yield {
                'num': num,
                'url': comic_url,
                'author': author,
                'month': day.month,
                'year': day.year,
                'day': day.day,
                'prefix': '%d-' % num,
                'img': [convert_iri_to_plain_ascii_uri(urljoin_wrapper(cls.url, i['src'])) for i in imgs]
            }


class MrLovenstein(GenericComic):
    """Class to retrieve Mr Lovenstein comics."""
    name = 'mrlovenstein'
    long_name = 'Mr. Lovenstein'
    url = 'http://www.mrlovenstein.com'

    @classmethod
    def get_next_comic(cls, last_comic):
        # TODO: more info from http://www.mrlovenstein.com/archive
        comic_num_re = re.compile('^/comic/([0-9]*)$')
        nums = [int(comic_num_re.match(link['href']).groups()[0])
                for link in get_soup_at_url(cls.url).find_all('a', href=comic_num_re)]
        first, last = min(nums), max(nums)
        if last_comic:
            first = last_comic['num'] + 1
        for num in range(first, last + 1):
            url = urljoin_wrapper(cls.url, '/comic/%d' % num)
            soup = get_soup_at_url(url)
            imgs = list(
                reversed(soup.find_all('img', src=re.compile('^/images/comics/'))))
            yield {
                'url': url,
                'num': num,
                'texts': '  '.join(t for t in (i.get('title') for i in imgs) if t),
                'img': [urljoin_wrapper(url, i['src']) for i in imgs],
            }


class DinosaurComics(GenericComic):
    """Class to retrieve Dinosaur Comics comics."""
    name = 'dinosaur'
    long_name = 'Dinosaur Comics'
    url = 'http://www.qwantz.com'

    @classmethod
    def get_next_comic(cls, last_comic):
        last_num = last_comic['num'] if last_comic else 0
        comic_link_re = re.compile('^%s/index.php\\?comic=([0-9]*)$' % cls.url)
        comic_img_re = re.compile('^%s/comics/' % cls.url)
        archive_url = '%s/archive.php' % cls.url
        # first link is random -> skip it
        for link in reversed(get_soup_at_url(archive_url).find_all('a', href=comic_link_re)[1:]):
            url = link['href']
            num = int(comic_link_re.match(url).groups()[0])
            if num > last_num:
                text = link.next_sibling.string
                day = string_to_date(
                    remove_st_nd_rd_th_from_date(link.string),
                    "%B %d, %Y")
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
    url = 'http://buttersafe.com'

    @classmethod
    def get_next_comic(cls, last_comic):
        archive_url = '%s/archive/' % cls.url
        comic_link_re = re.compile(
            '^%s/([0-9]*)/([0-9]*)/([0-9]*)/.*' % cls.url)

        prev_date = get_date_for_comic(
            last_comic) if last_comic else date(2006, 1, 1)

        for link in reversed(get_soup_at_url(archive_url).find_all('a', href=comic_link_re)):
            url = link['href']
            title = link.string
            year, month, day = [int(s)
                                for s in comic_link_re.match(url).groups()]
            if prev_date < date(year, month, day):
                img = get_soup_at_url(url).find('div', id='comic').find('img')
                assert img['alt'] == title
                yield {
                    'title': title,
                    'day': day,
                    'month': month,
                    'year': year,
                    'url': url,
                    'img': [img['src']],
                }


class CalvinAndHobbes(GenericComic):
    """Class to retrieve Calvin and Hobbes comics."""
    name = 'calvin'
    long_name = 'Calvin and Hobbes'
    # This is not through any official webpage but eh...
    url = 'http://marcel-oehler.marcellosendos.ch/comics/ch/'

    @classmethod
    def get_next_comic(cls, last_comic):
        last_date = get_date_for_comic(
            last_comic) if last_comic else date(1985, 11, 1)
        link_re = re.compile('^([0-9]*)/([0-9]*)/')
        img_re = re.compile('')
        for link in get_soup_at_url(cls.url).find_all('a', href=link_re):
            url = link['href']
            year, month = link_re.match(url).groups()
            if date(int(year), int(month), 1) + timedelta(days=31) >= last_date:
                img_re = re.compile('^%s%s([0-9]*)' % (year, month))
                month_url = urljoin_wrapper(cls.url, url)
                for img in get_soup_at_url(month_url).find_all('img', src=img_re):
                    img_src = img['src']
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
    url = 'http://abstrusegoose.com'

    @classmethod
    def get_next_comic(cls, last_comic):
        archive_url = '%s/archive' % cls.url
        last_num = last_comic['num'] if last_comic else 0
        comic_url_re = re.compile('^%s/([0-9]*)$' % cls.url)
        comic_img_re = re.compile('^%s/strips/.*' % cls.url)
        for link in get_soup_at_url(archive_url).find_all('a', href=comic_url_re):
            comic_url = link['href']
            num = int(comic_url_re.match(comic_url).groups()[0])
            if num > last_num:
                yield {
                    'url': comic_url,
                    'num': num,
                    'title': link.string,
                    'img': [get_soup_at_url(comic_url).find('img', src=comic_img_re)['src']]
                }


class PhDComics(GenericComic):
    """Class to retrieve PHD Comics."""
    name = 'phd'
    long_name = 'PhD Comics'
    url = 'http://phdcomics.com'

    @classmethod
    def get_next_comic(cls, last_comic):
        archive_url = '%s/comics/archive_list.php' % cls.url
        comic_url_num_re = re.compile(
            '^http://www.phdcomics.com/comics/archive.php\\?comicid=([0-9]*)$')

        last_num = last_comic['num'] if last_comic else 0

        for link in get_soup_at_url(archive_url).find_all('a', href=comic_url_num_re):
            comic_url = link['href']
            num = int(comic_url_num_re.match(comic_url).groups()[0])
            if num > last_num:
                month, day, year = [int(s) for s in link.string.split('/')]
                yield {
                    'url': comic_url,
                    'num': num,
                    'year': year,
                    'month': month,
                    'day': day if day else 1,
                    'img': [get_soup_at_url(comic_url).find('img', id='comic')['src']],
                    'title': link.parent.parent.next_sibling.string
                }


class Octopuns(GenericComic):
    """Class to retrieve Octopuns comics."""
    name = None  # 'octopuns'
    long_name = 'Octopuns'
    url = 'http://www.octopuns.net'

    @classmethod
    def get_next_comic(cls, last_comic):
        next_comic = \
            get_soup_at_url(last_comic['url']).find('img', src=re.compile('.*/Next.png')).parent \
            if last_comic else \
            get_soup_at_url(cls.url).find(
                'img', src=re.compile('.*/First.png')).parent
        while 'href' in next_comic:
            comic_url = next_comic['href']
            soup = get_soup_at_url(comic_url)
            next_comic = soup.find('img', src=re.compile('.*/Next.png')).parent
            yield {
                'url': comic_url,
                'img': [],
                'title': soup.find('h3', class_='post-title entry-title').string,
                'date': soup.find('h2', class_='date-header').string,
            }


class OverCompensating(GenericComic):
    """Class to retrieve the Over Compensating comics."""
    name = 'compensating'
    long_name = 'Over Compensating'
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
            comic_url = urljoin_wrapper(cls.url, next_comic['href'])
            num = int(comic_num_re.match(comic_url).groups()[0])
            soup = get_soup_at_url(comic_url)
            img = soup.find('img', src=img_src_re)
            yield {
                'url': comic_url,
                'num': num,
                'img': [urljoin_wrapper(comic_url, img['src'])],
                'title': img.get('title')
            }
            next_comic = soup.find('a', title='next comic')


class SomethingOfThatIlk(GenericComic):
    """Class to retrieve the Something Of That Ilk comics."""
    name = 'somethingofthatilk'
    long_name = 'Something Of That Ilk'
    url = 'http://www.somethingofthatilk.com'

    @classmethod
    def get_next_comic(cls, last_comic):
        img_src_re = re.compile('^/comics/.*')
        comic_url_re = re.compile('^index.php\?id=([0-9]*)$')
        next_comic = \
            get_soup_at_url(last_comic['url']).find('a', class_='next', href=comic_url_re) \
            if last_comic else \
            get_soup_at_url(cls.url).find(
                'a', class_='first', href=comic_url_re)
        while next_comic:
            href = next_comic['href']
            comic_url = urljoin_wrapper(cls.url, href)
            soup = get_soup_at_url(comic_url)
            img = soup.find('img', src=img_src_re)
            next_comic = soup.find('a', class_='next', href=comic_url_re)
            yield {
                'url': comic_url,
                'img': [urljoin_wrapper(comic_url, img['src'])],
                'alt': img['alt'],
                'text': soup.find('p', id='captioning').string,
                'title': soup.find('h1').string,
                'num': int(comic_url_re.match(href).groups()[0])
            }


class Wondermark(GenericComic):
    """Class to retrieve the Wondermark comics."""
    name = 'wondermark'
    long_name = 'Wondermark'
    url = 'http://wondermark.com'

    @classmethod
    def get_next_comic(cls, last_comic):
        archive_url = urljoin_wrapper(cls.url, 'archive/')
        add = not last_comic
        for link in reversed(get_soup_at_url(archive_url).find_all('a', rel='bookmark')):
            comic_url = link['href']
            if add:
                soup = get_soup_at_url(comic_url)
                day = string_to_date(
                    remove_st_nd_rd_th_from_date(
                        soup.find('div', class_='postdate').find('em').string),
                    "%B %d, %Y")
                div = soup.find('div', id='comic')
                if div:
                    img = div.find('img')
                    img_src = [img['src']]
                    alt = img['alt']
                    assert alt == img['title']
                    title = soup.find('meta', property='og:title')['content']
                else:
                    img_src = []
                    alt = ''
                    title = ''
                yield {
                    'url': comic_url,
                    'month': day.month,
                    'year': day.year,
                    'day': day.day,
                    'img': img_src,
                    'title': title,
                    'alt': alt,
                    'tags': ' '.join(t.string for t in soup.find('div', class_='postmeta').find_all('a', rel='tag')),
                }
            else:
                assert not add and last_comic
                add = (last_comic['url'] == comic_url)


class WarehouseComic(GenericComic):
    """Class to retrieve Warehouse Comic comics."""
    name = 'warehouse'
    long_name = 'Warehouse Comic'
    url = 'http://warehousecomic.com'

    @classmethod
    def get_next_comic(cls, last_comic):
        next_comic = get_soup_at_url(last_comic['url']).find('a', class_='navi navi-next') \
            if last_comic else \
            get_soup_at_url(cls.url).find('a', class_='navi navi-first')
        while next_comic:
            comic_url = next_comic['href']
            soup = get_soup_at_url(comic_url)
            next_comic = soup.find('a', class_='navi navi-next')
            comic_date = string_to_date(
                soup.find('span', class_='post-date').string,
                "%B %d, %Y")
            yield {
                'url': comic_url,
                'img': [i['src'] for i in soup.find('div', id='comic').find_all('img')],
                'title': soup.find('h2', class_='post-title').string,
                'day': comic_date.day,
                'month': comic_date.month,
                'year': comic_date.year,
            }


class PicturesInBoxes(GenericComic):
    """Class to retrieve Pictures In Boxes comics."""
    name = 'picturesinboxes'
    long_name = 'Pictures in Boxes'
    url = 'http://www.picturesinboxes.com'

    @classmethod
    def get_next_comic(cls, last_comic):
        url_date_re = re.compile('.*/([0-9]+)/([0-9]+)/([0-9]+)')
        last_date = get_date_for_comic(
            last_comic) if last_comic else date(2000, 1, 1)
        for com in reversed(get_soup_at_url(cls.url).find('select', attrs={'name': 'archive-dropdown'}).find_all('option')):
            comic_url = com['value']
            if comic_url:
                year, month, day = [int(s)
                                    for s in url_date_re.match(comic_url).groups()]
                comic_date = date(year, month, day)
                if comic_date > last_date:
                    title = com.string.strip()
                    imgs = get_soup_at_url(comic_url).find(
                        'div', id='comic-1').find_all('img')
                    yield {
                        'url': comic_url,
                        'day': day,
                        'month': month,
                        'year': year,
                        'img': [i['src'] for i in imgs],
                        'title': title,
                    }


class Penmen(GenericComic):
    """Class to retrieve Penmen comics."""
    name = 'penmen'
    long_name = 'Penmen'
    url = 'http://penmen.com'

    @classmethod
    def get_next_comic(cls, last_comic):
        next_comic = \
            get_soup_at_url(last_comic['url']).find('a', class_='comic-nav-base comic-nav-next') \
            if last_comic else \
            get_soup_at_url(cls.url).find('a', class_='comic-nav-base comic-nav-first')

        while next_comic:
            url = next_comic['href']
            soup = get_soup_at_url(url)
            url2 = soup.find('link', rel='shortlink')['href']
            title = soup.find('meta', {'name': 'twitter:title'})['content']
            img = soup.find('meta', property='og:image')['content']
            day = string_to_date(soup.find('span', class_='post-date').string, '%Y/%m/%d')
            yield {
                'url': url,
                'url2': url2,
                'title': title,
                'month': day.month,
                'year': day.year,
                'day': day.day,
                'img': [img],
            }
            next_comic = soup.find('a', class_='comic-nav-base comic-nav-next')


class TheDoghouseDiaries(GenericComic):
    """Class to retrieve The Dog House Diaries comics."""
    name = 'doghouse'
    long_name = 'The Dog House Diaries'
    url = 'http://thedoghousediaries.com'

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
                'img': [urljoin_wrapper(comic_url, img['src'].strip())],
                'num': int(comic_url.split('/')[-1]),
            }
            prev_url, comic_url = comic_url, soup.find(
                'a', id='nextlink').get('href')


class InvisibleBread(GenericComic):
    """Class to retrieve Invisible Bread comics."""
    name = 'invisiblebread'
    long_name = 'Invisible Bread'
    url = 'http://invisiblebread.com'

    @classmethod
    def get_next_comic(cls, last_comic):
        last_date = get_date_for_comic(
            last_comic) if last_comic else date(2000, 1, 1)
        link_re = re.compile('^%s/([0-9]+)/' % cls.url)
        for l in reversed(get_soup_at_url(urljoin_wrapper(cls.url, '/archives/')).find_all('td', class_='archive-title')):
            a = l.find('a')
            title = a.string
            url = a['href']
            month_and_day = l.previous_sibling.string
            year = link_re.match(url).groups()[0]
            date_com = string_to_date(month_and_day + ' ' + year, '%b %d %Y')
            if date_com > last_date:
                soup = get_soup_at_url(url)
                imgs = soup.find('div', id='comic').find_all('img')
                assert len(imgs) == 1
                assert all(i['title'] == i['alt'] == title for i in imgs)
                yield {
                    'url': url,
                    'month': date_com.month,
                    'year': date_com.year,
                    'day': date_com.day,
                    'img': [urljoin_wrapper(cls.url, i['src']) for i in imgs],
                    'title': title,
                }


class TubeyToons(GenericComic):
    """Class to retrieve TubeyToons comics."""
    name = 'tubeytoons'
    long_name = 'Tubey Toons'
    url = 'http://tubeytoons.com'

    @classmethod
    def get_next_comic(cls, last_comic):
        img_src_re = re.compile('^/img/comics/([0-9]+)\..*')
        img_date_re = re.compile('^Comic posted ([0-9]*)-([0-9]*)-([0-9]*) ')
        last_num = int(img_src_re.match(get_soup_at_url(cls.url).find('img', src=img_src_re)['src']).groups()[0])
        first_num = last_comic['num'] + 1 if last_comic else 1
        for i in range(first_num, last_num + 1):
            url = urljoin_wrapper(cls.url, str(i))
            soup = get_soup_at_url(url)
            title = soup.find('div', class_='title').string
            img = soup.find('img', src=img_src_re)
            title2 = img['title']
            date = img['alt']
            year, month, day = [int(s)
                                for s in img_date_re.match(date).groups()]
            yield {
                'url': url,
                'num': i,
                'day': day,
                'month': month,
                'year': year,
                'img': [urljoin_wrapper(cls.url, img['src'])],
                'title': title,
                'title2': title2,
            }


class CompletelySeriousComics(GenericComic):
    """Class to retrieve Completely Serious comics."""
    name = 'completelyserious'
    long_name = 'Completely Serious Comics'
    url = 'http://completelyseriouscomics.com/'

    @classmethod
    def get_next_comic(cls, last_comic):
        next_comic = \
            get_soup_at_url(last_comic['url']).find('a', class_='navi navi-next') \
            if last_comic else \
            get_soup_at_url(cls.url).find('a', class_='navi navi-first')
        while next_comic:
            url = next_comic['href']
            soup = get_soup_at_url(url)
            title = soup.find('h2', class_='post-title').string
            author = soup.find('span', class_='post-author').contents[1].string
            day = string_to_date(
                soup.find('span', class_='post-date').string,
                '%B %d, %Y')
            imgs = soup.find('div', class_='comicpane').find_all('img')
            assert imgs
            alt = imgs[0]['title']
            assert all(i['title'] == i['alt'] == alt for i in imgs)
            next_comic = soup.find('a', class_='navi navi-next')
            yield {
                'url': url,
                'month': day.month,
                'year': day.year,
                'day': day.day,
                'img': [i['src'] for i in imgs],
                'title': title,
                'alt': alt,
                'author': author,
            }


class PoorlyDrawnLines(GenericComic):
    """Class to retrieve Poorly Drawn Lines comics."""
    name = 'poorlydrawn'
    long_name = 'Poorly Drawn Lines'
    url = 'http://poorlydrawnlines.com'

    @classmethod
    def get_next_comic(cls, last_comic):
        waiting_for_url = last_comic['url'] if last_comic else None
        url_re = re.compile('^%s/comic/.' % cls.url)
        for l in reversed(get_soup_at_url(urljoin_wrapper(cls.url, 'archive')).find_all('a', href=url_re)):
            url = l['href']
            if waiting_for_url and waiting_for_url == url:
                waiting_for_url = None
            elif waiting_for_url is None:
                soup = get_soup_at_url(url)
                imgs = soup.find('div', id='post').find_all('img')
                assert len(imgs) <= 1
                yield {
                    'url': url,
                    'img': [i['src'] for i in imgs],
                    'title': imgs[0].get('title', "") if imgs else "",
                }


class ChuckleADuck(GenericComic):
    """Class to retrieve Chuckle-A-Duck comics."""
    name = 'chuckleaduck'
    long_name = 'Chuckle-A-duck'
    url = 'http://chuckleaduck.com/'

    @classmethod
    def get_next_comic(cls, last_comic):
        next_comic = \
            get_soup_at_url(last_comic['url']).find('div', class_='nav-next').find('a') \
            if last_comic else \
            get_soup_at_url(cls.url).find('div', class_='nav-first').find('a')
        while next_comic:
            url = next_comic['href']
            soup = get_soup_at_url(url)
            day = string_to_date(
                remove_st_nd_rd_th_from_date(soup.find('span', class_='post-date').string),
                "%B %d, %Y")
            author = soup.find('span', class_='post-author').string
            imgs = soup.find('div', id='comic').find_all('img')
            assert imgs
            title = imgs[0]['title']
            assert all(i['title'] == i['alt'] == title for i in imgs)
            yield {
                'url': url,
                'month': day.month,
                'year': day.year,
                'day': day.day,
                'img': [i['src'] for i in imgs],
                'title': title,
                'author': author,
            }
            next_comic = soup.find('div', class_='nav-next').find('a')


class ThingsInSquares(GenericComic):
    """Class to retrieve Things In Squares comics."""
    # This can be retrieved in other languages
    name = 'squares'
    long_name = 'Things in squares'
    url = 'http://www.thingsinsquares.com'

    @classmethod
    def get_next_comic(cls, last_comic):
        waiting_for_url = last_comic['url'] if last_comic else None
        archive_url = urljoin_wrapper(cls.url, 'archive')
        for tr in reversed(get_soup_at_url(archive_url).find('tbody').find_all('tr')):
            _, td2, td3 = tr.find_all('td')
            a = td2.find('a')
            url = a['href']
            if waiting_for_url and waiting_for_url == url:
                waiting_for_url = None
            elif waiting_for_url is None:
                day = string_to_date(td3.string, "%m.%d.%y")
                soup = get_soup_at_url(url)
                title = a.string
                title2 = soup.find('meta', property='og:title')['content']
                desc = soup.find('meta', property='og:description')
                description = desc['content'] if desc else ''
                tags = ' '.join(t['content'] for t in soup.find_all('meta', property='article:tag'))
                imgs = soup.find('div', class_='entry-content').find_all('img')
                yield {
                    'url': url,
                    'day': day.day,
                    'month': day.month,
                    'year': day.year,
                    'title': title,
                    'title2': title2,
                    'descriptions': description,
                    'tags': tags,
                    'img': [i['src'] for i in imgs],
                    'alt': ' '.join(i['alt'] for i in imgs),
                }


class AnythingComic(GenericComic):
    """Class to retrieve Anything Comics."""
    name = 'anythingcomic'
    long_name = 'Anything Comic'
    url = 'http://www.anythingcomic.com'

    @classmethod
    def get_next_comic(cls, last_comic):
        last_num = last_comic['num'] if last_comic else 0
        archive_url = urljoin_wrapper(cls.url, 'archive')
        for i, tr in enumerate(get_soup_at_url(archive_url).find('table', id='chapter_table').find_all('tr')):
            if i > 1:
                td_num, td_comic, td_date, td_com = tr.find_all('td')
                num = int(td_num.string)
                assert num + 1 == i
                if num > last_num:
                    link = td_comic.find('a')
                    comic_url = urljoin_wrapper(cls.url, link['href'])
                    title = link.string
                    soup = get_soup_at_url(comic_url)
                    imgs = soup.find_all('img', id='comic_image')
                    day = string_to_date(td_date.string, '%d %b %Y %I:%M %p')
                    assert len(imgs) == 1
                    assert all(i.get('alt') == i.get('title') for i in imgs)
                    yield {
                        'url': comic_url,
                        'num': num,
                        'title': title,
                        'alt': imgs[0].get('alt', ''),
                        'img': [i['src'] for i in imgs],
                        'month': day.month,
                        'year': day.year,
                        'day': day.day,
                    }


class HorovitzComics(GenericComic):
    """Generic class to handle the logic common to the different comics from Horovitz."""
    url = 'http://www.horovitzcomics.com'

    @classmethod
    def get_next_comic(cls, last_comic):
        link_re = re.compile('^' + cls.suffix + '/([0-9]+)$')
        img_re = re.compile('.*comics/([0-9]*)/([0-9]*)/([0-9]*)/.*$')
        archive = 'http://www.horovitzcomics.com/comics/archive/'
        waiting_for_url = last_comic['url'] if last_comic else None
        for a in reversed(get_soup_at_url(archive).find_all('a', href=link_re)):
            href = a['href']
            url = urljoin_wrapper(cls.url, href)
            if waiting_for_url and waiting_for_url == url:
                waiting_for_url = None
            elif waiting_for_url is None:
                num = int(link_re.match(href).groups()[0])
                title = a.string
                soup = get_soup_at_url(url)
                imgs = soup.find_all('img', id='comic')
                assert len(imgs) == 1
                year, month, day = [int(s)
                                    for s in img_re.match(imgs[0]['src']).groups()]
                yield {
                    'url': url,
                    'title': title,
                    'day': day,
                    'month': month,
                    'year': year,
                    'img': [i['src'] for i in imgs],
                    'num': num,
                }


class HorovitzNew(HorovitzComics):
    name = 'horovitznew'
    long_name = 'Horovitz New'
    suffix = '/comics/new'


class HorovitzClassic(HorovitzComics):
    name = 'horovitzclassic'
    long_name = 'Horovitz Classic'
    suffix = '/comics/classic'


class GenericGoComic(GenericComic):
    """Generic class to handle the logic common to comics from gocomics.com."""

    @classmethod
    def get_next_comic(cls, last_comic):
        gocomics = 'http://www.gocomics.com'
        url_date_re = re.compile('.*/([0-9]*)/([0-9]*)/([0-9]*)$')

        next_comic = \
            get_soup_at_url(last_comic['url']).find('a', class_='next', href=url_date_re) \
            if last_comic else \
            get_soup_at_url(cls.url).find('a', class_='beginning')

        while next_comic:
            comic_url = urljoin_wrapper(gocomics, next_comic['href'])
            year, month, day = [int(s)
                                for s in url_date_re.match(comic_url).groups()]
            soup = get_soup_at_url(comic_url)
            next_comic = soup.find('a', class_='next', href=url_date_re)
            yield {
                'url': comic_url,
                'day': day,
                'month': month,
                'year': year,
                'img': [soup.find_all('img', class_='strip')[-1]['src']],
                'author': soup.find('meta', attrs={'name': 'author'})['content']
            }


class PearlsBeforeSwine(GenericGoComic):
    """Class to retrieve Pearls Before Swine comics."""
    name = 'pearls'
    long_name = 'Pearls Before Swine'
    url = 'http://www.gocomics.com/pearlsbeforeswine'


class Peanuts(GenericGoComic):
    """Class to retrieve Peanuts comics."""
    name = 'peanuts'
    long_name = 'Peanuts'
    url = 'http://www.gocomics.com/peanuts'


class MattWuerker(GenericGoComic):
    """Class to retrieve Matt Wuerker comics."""
    name = 'wuerker'
    long_name = 'Matt Wuerker'
    url = 'http://www.gocomics.com/mattwuerker'


class TomToles(GenericGoComic):
    """Class to retrieve Tom Toles comics."""
    name = 'toles'
    long_name = 'Tom Toles'
    url = 'http://www.gocomics.com/tomtoles'


class BreakOfDay(GenericGoComic):
    """Class to retrieve Break Of Day comics."""
    name = 'breakofday'
    long_name = 'Break Of Day'
    url = 'http://www.gocomics.com/break-of-day'


class MichaelRamirez(GenericGoComic):
    """Class to retrieve Michael Ramirez comics."""
    name = 'ramirez'
    long_name = 'Michael Ramirez'
    url = 'http://www.gocomics.com/michaelramirez'


def get_subclasses(klass):
    """Gets the list of direct/indirect subclasses of a class"""
    subclasses = klass.__subclasses__()
    for derived in list(subclasses):
        subclasses.extend(get_subclasses(derived))
    return subclasses


def remove_st_nd_rd_th_from_date(string):
    """Function to transform 1st/2nd/3rd/4th in a parsable date format."""
    # Hackish way to convert string with numeral "1st"/"2nd"/etc to date
    return (string.replace('st', '')
            .replace('nd', '')
            .replace('rd', '')
            .replace('th', '')
            .replace('Augu', 'August'))


def string_to_date(string, date_format):
    """Function to convert string to date object.
    Wrapper around datetime.datetime.strptime."""
    # format described in https://docs.python.org/2/library/datetime.html#strftime-and-strptime-behavior
    return datetime.datetime.strptime(string, date_format).date()


COMIC_NAMES = {c.name: c for c in get_subclasses(
    GenericComic) if c.name is not None}
