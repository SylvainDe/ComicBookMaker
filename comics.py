#! /usr/bin/python3
# vim: set expandtab tabstop=4 shiftwidth=4 :
"""Module to retrieve webcomics"""

from comic_abstract import GenericComic, get_date_for_comic
import re
from datetime import date, timedelta
import datetime
from urlfunctions import get_soup_at_url, urljoin_wrapper,\
    convert_iri_to_plain_ascii_uri, load_json_at_url, urlopen_wrapper
import json
import locale

DEFAULT_LOCAL = 'en_GB.UTF-8'


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


class GenericNavigableComic(GenericComic):
    """Generic class for "navigable" comics : with first/next arrows.

    The method `get_next_comic` methods is implemented in terms of new
    more specialized methods to be implemented/overridden:
        - get_first_comic_link
        - get_next_comic_link
        - get_comic_info
        - get_url_from_link
    """

    @classmethod
    def get_first_comic_link(cls):
        raise NotImplementedError

    @classmethod
    def get_next_comic_link(cls, last_soup):
        raise NotImplementedError

    @classmethod
    def get_comic_info(cls, soup, link):
        raise NotImplementedError

    @classmethod
    def get_url_from_link(cls, link):
        return link['href']

    @classmethod
    def get_next_comic(cls, last_comic):
        url = last_comic['url'] if last_comic else None
        next_comic = \
            cls.get_next_comic_link(get_soup_at_url(url)) \
            if url else \
            cls.get_first_comic_link()
        while next_comic:
            prev_url, url = url, cls.get_url_from_link(next_comic)
            if prev_url == url:
                break
            soup = get_soup_at_url(url)
            comic = cls.get_comic_info(soup, next_comic)
            if comic is not None:
                assert 'url' not in comic
                comic['url'] = url
                yield comic
            next_comic = cls.get_next_comic_link(soup)


class GenericListableComic(GenericComic):
    """Generic class for "listable" comics : with a list of comics (aka 'archive')

    The method `get_next_comic` methods is implemented in terms of new
    more specialized methods to be implemented/overridden:
        - get_archive_elements
        - get_url_from_archive_element
        - get_comic_info
    """

    @classmethod
    def get_archive_elements(cls):
        raise NotImplementedError

    @classmethod
    def get_url_from_archive_element(cls, archive_elt):
        raise NotImplementedError

    @classmethod
    def get_comic_info(cls, soup, archive_element):
        raise NotImplementedError

    @classmethod
    def get_next_comic(cls, last_comic):
        waiting_for_url = last_comic['url'] if last_comic else None
        for archive_elt in cls.get_archive_elements():
            url = cls.get_url_from_archive_element(archive_elt)
            if waiting_for_url and waiting_for_url == url:
                waiting_for_url = None
            elif waiting_for_url is None:
                soup = get_soup_at_url(url)
                comic = cls.get_comic_info(soup, archive_elt)
                if comic is not None:
                    assert 'url' not in comic
                    comic['url'] = url
                    yield comic


class ExtraFabulousComics(GenericNavigableComic):
    """Class to retrieve Extra Fabulous Comics."""
    name = 'efc'
    long_name = 'Extra Fabulous Comics'
    url = 'http://extrafabulouscomics.com'

    @classmethod
    def get_first_comic_link(cls):
        return get_soup_at_url(cls.url).find('a', title='FIRST')

    @classmethod
    def get_next_comic_link(cls, last_soup):
        return last_soup.find('a', title='NEXT')

    @classmethod
    def get_comic_info(cls, soup, link):
        img_src_re = re.compile('^%s/wp-content/uploads/' % cls.url)
        imgs = soup.find_all('img', src=img_src_re)
        title = soup.find('h2', class_='post-title').string
        return {
            'title': title,
            'img': [i['src'] for i in imgs],
            'prefix': title + '-'
        }


class GenericLeMondeBlog(GenericNavigableComic):
    """Generic class to retrieve comics from Le Monde blogs."""

    @classmethod
    def get_first_comic_url(cls):
        # First comic cannot be reached directly so to start from
        # the first comic one has to go to the previous comic until
        # there is no previous comics. Once this URL is reached, it
        # is better to hardcode it but for development purposes, it
        # is convenient to have an automatic way to find it.
        if True:
            raise NotImplementedError
        else:
            url = input("Get starting URL: ")
            prev_comic = cls.get_prev_comic_link(get_soup_at_url(url))
            print(url)
            while prev_comic:
                url = prev_comic['href']
                print(url)
                soup = get_soup_at_url(url)
                prev_comic = cls.get_prev_comic_link(soup)
            return url

    @classmethod
    def get_first_comic_link(cls):
        return {'href': cls.get_first_comic_url()}

    @classmethod
    def get_next_comic_link(cls, last_soup):
        return last_soup.find('link', rel='next')

    @classmethod
    def get_prev_comic_link(cls, last_soup):
        return last_soup.find('link', rel='prev')

    @classmethod
    def get_comic_info(cls, soup, link):
        url2 = soup.find('link', rel='shortlink')['href']
        title = soup.find('meta', property='og:title')['content']
        date_str = soup.find("span", class_="entry-date").string
        day = string_to_date(date_str, "%d %B %Y", "fr_FR.utf8")
        imgs = soup.find_all('meta', property='og:image')
        return {
            'title': title,
            'url2': url2,
            'img': [convert_iri_to_plain_ascii_uri(i['content']) for i in imgs],
            'month': day.month,
            'year': day.year,
            'day': day.day,
        }


class ZepWorld(GenericLeMondeBlog):
    """Class to retrieve Zep World comics."""
    name = "zep"
    long_name = "Zep World"
    url = "http://zepworld.blog.lemonde.fr"

    @classmethod
    def get_first_comic_url(cls):
        return "http://zepworld.blog.lemonde.fr/2014/10/31/bientot-le-blog-de-zep/"


class Vidberg(GenericLeMondeBlog):
    """Class to retrieve Vidberg comics."""
    name = 'vidberg'
    long_name = "Vidberg -l'actu en patates"
    url = "http://vidberg.blog.lemonde.fr"

    @classmethod
    def get_first_comic_url(cls):
        # Not the first but I didn't find an efficient way to retrieve it
        return "http://vidberg.blog.lemonde.fr/2012/02/09/revue-de-campagne-la-campagne-du-modem-semballe/"


class Plantu(GenericLeMondeBlog):
    """Class to retrieve Plantu comics."""
    name = 'plantu'
    long_name = "Plantu"
    url = "http://plantu.blog.lemonde.fr"

    @classmethod
    def get_first_comic_url(cls):
        return "http://plantu.blog.lemonde.fr/2014/10/28/stress-test-a-bruxelles/"


class XavierGorce(GenericLeMondeBlog):
    """Class to retrieve Xavier Gorce comics."""
    name = 'gorce'
    long_name = "Xavier Gorce"
    url = "http://xaviergorce.blog.lemonde.fr"

    @classmethod
    def get_first_comic_url(cls):
        return "http://xaviergorce.blog.lemonde.fr/2015/01/09/distinction/"


class CartooningForPeace(GenericLeMondeBlog):
    """Class to retrieve Cartooning For Peace comics."""
    name = 'forpeace'
    long_name = "Cartooning For Peace"
    url = "http://cartooningforpeace.blog.lemonde.fr"

    @classmethod
    def get_first_comic_url(cls):
        return "http://cartooningforpeace.blog.lemonde.fr/2014/12/15/bado/"


class Aurel(GenericLeMondeBlog):
    """Class to retrieve Aurel comics."""
    name = 'aurel'
    long_name = "Aurel"
    url = "http://aurel.blog.lemonde.fr"

    @classmethod
    def get_first_comic_url(cls):
        return "http://aurel.blog.lemonde.fr/2014/09/29/le-senat-repasse-a-droite/"


class Rall(GenericNavigableComic):
    """Class to retrieve Ted Rall comics."""
    # Also on : http://www.gocomics.com/tedrall
    name = 'rall'
    long_name = "Ted Rall"
    url = "http://rall.com/comic"

    @classmethod
    def get_first_comic_link(cls):
        # Not the first but I didn't find an efficient way to retrieve it
        return {'href': "http://rall.com/2014/01/30/los-angeles-times-cartoon-well-miss-those-california-flowers"}

    @classmethod
    def get_next_comic_link(cls, last_soup):
        return last_soup.find('link', rel='next')

    @classmethod
    def get_comic_info(cls, soup, link):
        title = soup.find('meta', property='og:title')['content']
        author = soup.find("span", class_="author vcard").find("a").string
        date_str = soup.find("span", class_="entry-date").string
        day = string_to_date(date_str, "%B %d, %Y")
        desc = soup.find('meta', property='og:description')['content']
        imgs = soup.find('div', class_='entry-content').find_all('img')
        imgs = imgs[:-7]  # remove social media buttons
        return {
            'title': title,
            'author': author,
            'month': day.month,
            'year': day.year,
            'day': day.day,
            'description': desc,
            'img': [i['src'] for i in imgs],
        }


class SpaceAvalanche(GenericNavigableComic):
    """Class to retrieve Space Avalanche comics."""
    name = 'avalanche'
    long_name = 'Space Avalanche'
    url = 'http://www.spaceavalanche.com'

    @classmethod
    def get_first_comic_link(cls):
        return {'href': "http://www.spaceavalanche.com/2009/02/02/irish-sea/", 'title': "Irish Sea"}

    @classmethod
    def get_next_comic_link(cls, last_soup):
        return last_soup.find('link', rel='next')

    @classmethod
    def get_comic_info(cls, soup, link):
        url_date_re = re.compile('.*/([0-9]*)/([0-9]*)/([0-9]*)/.*$')
        title = link['title']
        url = cls.get_url_from_link(link)
        year, month, day = [int(s)
                            for s in url_date_re.match(url).groups()]
        imgs = soup.find("div", class_="entry").find_all("img")
        return {
            'title': title,
            'day': day,
            'month': month,
            'year': year,
            'img': [i['src'] for i in imgs],
        }


class ZenPencils(GenericNavigableComic):
    """Class to retrieve ZenPencils comics."""
    name = 'zenpencils'
    long_name = 'Zen Pencils'
    url = 'http://zenpencils.com'

    @classmethod
    def get_first_comic_link(cls):
        return {'href': "http://zenpencils.com/comic/1-ralph-waldo-emerson-make-them-cry/"}

    @classmethod
    def get_next_comic_link(cls, last_soup):
        return last_soup.find('link', rel='next')

    @classmethod
    def get_comic_info(cls, soup, link):
        imgs = soup.find('div', id='comic').find_all('img')
        post = soup.find('div', class_='post-content')
        author = post.find("span", class_="post-author").find("a").string
        title = post.find('h2', class_='post-title').string
        date_str = post.find('span', class_='post-date').string
        day = string_to_date(date_str, "%B %d, %Y")
        assert imgs
        assert all(i['alt'] == i['title'] == "" for i in imgs)
        desc = soup.find('meta', property='og:description')['content']
        return {
            'title': title,
            'description': desc,
            'author': author,
            'day': day.day,
            'month': day.month,
            'year': day.year,
            'img': [i['src'] for i in imgs],
        }


class ItsTheTie(GenericNavigableComic):
    """Class to retrieve It's the tie comics."""
    # Also on http://itsthetie.tumblr.com
    name = 'tie'
    long_name = "It's the tie"
    url = "http://itsthetie.com"

    @classmethod
    def get_first_comic_link(cls):
        return get_soup_at_url(cls.url).find('div', class_="nav-first").find('a')

    @classmethod
    def get_next_comic_link(cls, last_soup):
        return last_soup.find('div', class_="nav-next").find('a')

    @classmethod
    def get_comic_info(cls, soup, link):
        title = soup.find('h1', class_='comic-title').find('a').string
        date_str = soup.find('header', class_='comic-meta entry-meta').find('a').string
        day = string_to_date(date_str, "%B %d, %Y")
        imgs = soup.find_all('meta', property='og:image')
        return {
            'title': title,
            'month': day.month,
            'year': day.year,
            'day': day.day,
            'img': [i['content'] for i in imgs],
        }


class OneOneOneOneComic(GenericNavigableComic):
    """Class to retrieve 1111 Comics."""
    name = '1111'
    long_name = '1111 Comics'
    url = 'http://www.1111comics.me'

    @classmethod
    def get_first_comic_link(cls):
        return get_soup_at_url(cls.url).find('div', class_="nav-first").find('a')

    @classmethod
    def get_next_comic_link(cls, last_soup):
        return last_soup.find('div', class_="nav-next").find('a')

    @classmethod
    def get_comic_info(cls, soup, link):
        title = soup.find('h1', class_='comic-title').find('a').string
        date_str = soup.find('header', class_='comic-meta entry-meta').find('a').string
        day = string_to_date(date_str, "%B %d, %Y")
        imgs = soup.find_all('meta', property='og:image')
        return {
            'title': title,
            'month': day.month,
            'year': day.year,
            'day': day.day,
            'img': [i['content'] for i in imgs],
        }


class NeDroid(GenericNavigableComic):
    """Class to retrieve NeDroid comics."""
    name = 'nedroid'
    long_name = 'NeDroid'
    url = 'http://nedroid.com'

    @classmethod
    def get_first_comic_link(cls):
        return get_soup_at_url(cls.url).find('div', class_="nav-first").find('a')

    @classmethod
    def get_next_comic_link(cls, last_soup):
        return last_soup.find('div', class_="nav-next").find('a')

    @classmethod
    def get_comic_info(cls, soup, link):
        short_url_re = re.compile('^%s/\\?p=([0-9]*)' % cls.url)
        comic_url_re = re.compile('//nedroid.com/comics/([0-9]*)-([0-9]*)-([0-9]*).*')
        short_url = urljoin_wrapper(cls.url, soup.find('link', rel='shortlink')['href'])
        num = int(short_url_re.match(short_url).groups()[0])
        imgs = soup.find('div', id='comic').find_all('img')
        year, month, day = [int(s) for s in comic_url_re.match(imgs[0]['src']).groups()]
        assert len(imgs) == 1
        title = imgs[0]['alt']
        title2 = imgs[0]['title']
        return {
            'short_url': short_url,
            'title': title,
            'title2': title2,
            'img': [urljoin_wrapper(cls.url, i['src']) for i in imgs],
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


class Dilbert(GenericNavigableComic):
    """Class to retrieve Dilbert comics."""
    name = 'dilbert'
    long_name = 'Dilbert'
    url = 'http://dilbert.com'

    @classmethod
    def get_first_comic_link(cls):
        return {'href': 'http://dilbert.com/strip/1989-04-16'}

    @classmethod
    def get_next_comic_link(cls, last_soup):
        next_ = last_soup.find('div', class_="nav-comic nav-right")
        return next_.find('a') if next_ else None

    @classmethod
    def get_comic_info(cls, soup, link):
        title = soup.find('meta', property='og:title')['content']
        imgs = soup.find_all('meta', property='og:image')
        desc = soup.find('meta', property='og:description')['content']
        date_str = soup.find('meta', property='article:publish_date')['content']
        day = string_to_date(date_str, "%B %d, %Y")
        author = soup.find('meta', property='article:author')['content']
        tags = soup.find('meta', property='article:tag')['content']
        return {
            'title': title,
            'description': desc,
            'img': [i['content'] for i in imgs],
            'author': author,
            'tags': tags,
            'day': day.day,
            'month': day.month,
            'year': day.year
        }

    @classmethod
    def get_url_from_link(cls, link):
        return urljoin_wrapper(cls.url, link['href'])


class VictimsOfCircumsolar(GenericNavigableComic):
    """Class to retrieve VictimsOfCircumsolar comics."""
    name = 'circumsolar'
    long_name = 'Victims Of Circumsolar'
    url = 'http://www.victimsofcircumsolar.com'

    @classmethod
    def get_first_comic_link(cls):
        return {'href': 'http://www.victimsofcircumsolar.com/comic/modern-addiction'}

    @classmethod
    def get_next_comic_link(cls, last_soup):
        return last_soup.find('a', class_='navi comic-nav-next navi-next')

    @classmethod
    def get_comic_info(cls, soup, link):
        # Date is on the archive page
        title = soup.find_all('meta', property='og:title')[-1]['content']
        desc = soup.find_all('meta', property='og:description')[-1]['content']
        imgs = soup.find('div', id='comic').find_all('img')
        assert all(i['title'] == i['alt'] == title for i in imgs)
        return {
            'title': title,
            'description': desc,
            'img': [i['src'] for i in imgs],
        }


class ThreeWordPhrase(GenericNavigableComic):
    """Class to retrieve Three Word Phrase comics."""
    name = 'threeword'
    long_name = 'Three Word Phrase'
    url = 'http://threewordphrase.com'

    @classmethod
    def get_first_comic_link(cls):
        return get_soup_at_url(cls.url).find('img', src='/firstlink.gif').parent

    @classmethod
    def get_next_comic_link(cls, last_soup):
        next_ = last_soup.find('img', src='/nextlink.gif').parent
        return None if next_.get('href', None) is None else next_

    @classmethod
    def get_url_from_link(cls, link):
        return urljoin_wrapper(cls.url, link['href'])

    @classmethod
    def get_comic_info(cls, soup, link):
        title = soup.find('title')
        imgs = [img for img in soup.find_all('img')
                if not img['src'].endswith(
                    ('link.gif', '32.png', 'twpbookad.jpg',
                     'merchad.jpg', 'header.gif', 'tipjar.jpg'))]
        return {
            'title': title.string if title else None,
            'title2': '  '.join(img.get('alt') for img in imgs if img.get('alt')),
            'img': [urljoin_wrapper(cls.url, img['src']) for img in imgs],
        }


class TheGentlemanArmchair(GenericListableComic):
    """Class to retrieve The Gentleman Armchair comics."""
    name = 'gentlemanarmchair'
    long_name = 'The Gentleman Armchair'
    url = 'http://thegentlemansarmchair.com'

    @classmethod
    def get_comic_info(cls, soup, tr):
        date_td, content_td = tr.children
        date_str = date_td.string
        a_tag = content_td.find('a')
        title = a_tag.string
        day = string_to_date(date_str, "%b %d")
        imgs = soup.find('div', id='comic').find_all('img')
        return {
            'img': [i['src'] for i in imgs],
            'title': title,
            'month': day.month,
            'year': day.year,
            'day': day.day,
        }

    @classmethod
    def get_url_from_archive_element(cls, tr):
        _, content_td = tr.children
        return content_td.find('a')['href']

    @classmethod
    def get_archive_elements(cls):
        # FIXME: archive is actually spread on multiple pages corresponding to the
        # different years. Default is to reach the one for the current year.
        # Proper solution would be to iterate over the different relevant years.
        archive_url = urljoin_wrapper(cls.url, 'archive')
        return reversed(get_soup_at_url(archive_url).find_all('tr', class_='archive-tr'))


class MyExtraLife(GenericNavigableComic):
    """Class to retrieve My Extra Life comics."""
    name = 'extralife'
    long_name = 'My Extra Life'
    url = 'http://www.myextralife.com'

    @classmethod
    def get_first_comic_link(cls):
        return get_soup_at_url(cls.url).find('a', class_='comic_nav_link first_comic_link')

    @classmethod
    def get_next_comic_link(cls, last_soup):
        return last_soup.find('link', rel='next')

    @classmethod
    def get_comic_info(cls, soup, link):
        title = soup.find("h1", class_="comic_title").string
        date_str = soup.find("span", class_="comic_date").string
        day = string_to_date(date_str, "%B %d, %Y")
        imgs = soup.find_all("img", class_="comic")
        assert all(i['alt'] == i['title'] == title for i in imgs)
        return {
            'title': title,
            'img': [i['src'] for i in imgs if i["src"]],
            'day': day.day,
            'month': day.month,
            'year': day.year
        }


class SaturdayMorningBreakfastCereal(GenericNavigableComic):
    """Class to retrieve Saturday Morning Breakfast Cereal comics."""
    name = 'smbc'
    long_name = 'Saturday Morning Breakfast Cereal'
    url = 'http://www.smbc-comics.com'

    @classmethod
    def get_first_comic_link(cls):
        return get_soup_at_url(cls.url).find('a', rel='start')

    @classmethod
    def get_next_comic_link(cls, last_soup):
        return last_soup.find('a', rel='next')

    @classmethod
    def get_url_from_link(cls, link):
        return urljoin_wrapper(cls.url, link['href'])

    @classmethod
    def get_comic_info(cls, soup, link):
        comic_link_re = re.compile('^/index.php\\?id=([0-9]*)$')
        num = int(comic_link_re.match(link['href']).groups()[0])
        image1 = soup.find('div', id='comicbody').find('img')
        image_url1 = image1['src']
        aftercomic = soup.find('div', id='aftercomic')
        image_url2 = aftercomic.find('img')['src'] if aftercomic else ''
        imgs = [image_url1] + ([image_url2] if image_url2 else [])
        date_str = soup.find('div', class_='cc-publishtime').contents[0]
        day = string_to_date(date_str, "%B %d, %Y")
        return {
            'num': num,
            'title': image1['title'],
            'img': [urljoin_wrapper(cls.url, i) for i in imgs],
            'day': day.day,
            'month': day.month,
            'year': day.year
        }


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


class Mercworks(GenericNavigableComic):
    """Class to retrieve Mercworks comics."""
    name = 'mercworks'
    long_name = 'Mercworks'
    url = 'http://mercworks.net'

    @classmethod
    def get_first_comic_link(cls):
        return get_soup_at_url(cls.url).find('a', class_='comic-nav-base comic-nav-first')

    @classmethod
    def get_next_comic_link(cls, last_soup):
        return last_soup.find('a', class_='comic-nav-base comic-nav-next')

    @classmethod
    def get_comic_info(cls, soup, link):
        title = soup.find('meta', property='og:title')['content']
        metadesc = soup.find('meta', property='og:description')
        desc = metadesc['content'] if metadesc else ""
        author = soup.find('meta', attrs={'name': 'shareaholic:article_author_name'})['content']
        date_str = soup.find('meta', attrs={'name': 'shareaholic:article_published_time'})['content']
        date_str = date_str[:10]
        day = string_to_date(date_str, "%Y-%m-%d")
        imgs = soup.find_all('meta', property='og:image')
        return {
            'img': [i['content'] for i in imgs],
            'title': title,
            'author': author,
            'desc': desc,
            'day': day.day,
            'month': day.month,
            'year': day.year
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


class GenericBouletCorp(GenericNavigableComic):
    """Generic class to retrieve BouletCorp comics in different languages."""

    @classmethod
    def get_first_comic_link(cls):
        return get_soup_at_url(cls.url).find('div', id='centered_nav').find_all('a')[0]

    @classmethod
    def get_next_comic_link(cls, last_soup):
        return last_soup.find('div', id='centered_nav').find_all('a')[3]

    @classmethod
    def get_comic_info(cls, soup, link):
        url = cls.get_url_from_link(link)
        date_re = re.compile('^%s/([0-9]*)/([0-9]*)/([0-9]*)/' % cls.url)
        year, month, day = [int(s) for s in date_re.match(url).groups()]
        imgs = soup.find('div', id='notes').find('div', class_='storycontent').find_all('img')
        texts = '  '.join(t for t in (i.get('title') for i in imgs) if t)
        title = soup.find('title').string
        return {
            'img': [convert_iri_to_plain_ascii_uri(i['src']) for i in imgs],
            'title': title,
            'texts': texts,
            'year': year,
            'month': month,
            'day': day,
        }


class BouletCorp(GenericBouletCorp):
    """Class to retrieve BouletCorp comics."""
    name = 'boulet'
    long_name = 'Boulet Corp'
    url = 'http://www.bouletcorp.com'


class BouletCorpEn(GenericBouletCorp):
    """Class to retrieve EnglishBouletCorp comics."""
    name = 'boulet_en'
    long_name = 'Boulet Corp English'
    url = 'http://english.bouletcorp.com'


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


class ToonHole(GenericListableComic):
    """Class to retrieve Toon Holes comics."""
    name = 'toonhole'
    long_name = 'Toon Hole'
    url = 'http://www.toonhole.com'

    @classmethod
    def get_comic_info(cls, soup, link):
        title = link.string
        date_str = remove_st_nd_rd_th_from_date(soup.find('div', class_='comicdate').string.strip())
        day = string_to_date(date_str, "%B %d, %Y")
        imgs = soup.find('div', id='comic').find_all('img')
        assert all(i['alt'] == i['title'] == title for i in imgs)
        return {
            'title': title,
            'month': day.month,
            'year': day.year,
            'day': day.day,
            'img': [convert_iri_to_plain_ascii_uri(i['src']) for i in imgs],
        }

    @classmethod
    def get_url_from_archive_element(cls, link):
        return link['href']

    @classmethod
    def get_archive_elements(cls):
        archive_url = urljoin_wrapper(cls.url, 'archive/')
        return reversed(get_soup_at_url(archive_url).find_all('a', rel='bookmark'))


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


class CyanideAndHappiness(GenericNavigableComic):
    """Class to retrieve Cyanide And Happiness comics."""
    name = 'cyanide'
    long_name = 'Cyanide and Happiness'
    url = 'http://explosm.net'

    @classmethod
    def get_first_comic_link(cls):
        return get_soup_at_url(cls.url).find('a', title='Oldest comic')

    @classmethod
    def get_next_comic_link(cls, last_soup):
        next_ = last_soup.find('a', class_='next-comic')
        return None if next_.get('href', None) is None else next_

    @classmethod
    def get_url_from_link(cls, link):
        return urljoin_wrapper(cls.url, link['href'])

    @classmethod
    def get_comic_info(cls, soup, link):
        url2 = soup.find('meta', property='og:url')['content']
        num = int(url2.split('/')[-2])
        date_str = soup.find('h3').find('a').string
        day = string_to_date(date_str, '%Y.%m.%d')
        author = soup.find('small', class_="author-credit-name").string
        assert author.startswith('by ')
        author = author[3:]
        imgs = soup.find_all('img', id='main-comic')
        return {
            'num': num,
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
    # Also on http://www.gocomics.com/calvinandhobbes/
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


class Octopuns(GenericNavigableComic):
    """Class to retrieve Octopuns comics."""
    name = 'octopuns'
    long_name = 'Octopuns'
    url = 'http://www.octopuns.net'

    @classmethod
    def get_first_comic_link(cls):
        return get_soup_at_url(cls.url).find('img', src=re.compile('.*/First.png')).parent

    @classmethod
    def get_next_comic_link(cls, last_soup):
        next_ = last_soup.find('img', src=re.compile('.*/Next.png')).parent
        return None if next_.get('href', None) is None else next_

    @classmethod
    def get_comic_info(cls, soup, link):
        title = soup.find('h3', class_='post-title entry-title').string
        date_str = soup.find('h2', class_='date-header').string
        day = string_to_date(date_str, "%A, %B %d, %Y")
        imgs = soup.find_all('link', rel='image_src')
        return {
            'img': [i['href'] for i in imgs],
            'title': title,
            'day': day.day,
            'month': day.month,
            'year': day.year,
        }


class OverCompensating(GenericNavigableComic):
    """Class to retrieve the Over Compensating comics."""
    name = 'compensating'
    long_name = 'Over Compensating'
    url = 'http://www.overcompensating.com'

    @classmethod
    def get_first_comic_link(cls):
        return get_soup_at_url(cls.url).find('a', href=re.compile('comic=1$'))

    @classmethod
    def get_next_comic_link(cls, last_soup):
        return last_soup.find('a', title='next comic')

    @classmethod
    def get_url_from_link(cls, link):
        return urljoin_wrapper(cls.url, link['href'])

    @classmethod
    def get_comic_info(cls, soup, link):
        img_src_re = re.compile('^/oc/comics/.*')
        comic_num_re = re.compile('.*comic=([0-9]*)$')
        comic_url = cls.get_url_from_link(link)
        num = int(comic_num_re.match(comic_url).groups()[0])
        img = soup.find('img', src=img_src_re)
        return {
            'num': num,
            'img': [urljoin_wrapper(comic_url, img['src'])],
            'title': img.get('title')
        }


class Oglaf(GenericNavigableComic):
    """Class to retrieve Oglaf comics."""
    name = 'oglaf'
    long_name = 'Oglaf [NSFW]'
    url = 'http://oglaf.com'

    @classmethod
    def get_first_comic_link(cls):
        return get_soup_at_url(cls.url).find("div", id="st").parent

    @classmethod
    def get_next_comic_link(cls, last_soup):
        div = last_soup.find("div", id="nx")
        return div.parent if div else None

    @classmethod
    def get_url_from_link(cls, link):
        return urljoin_wrapper(cls.url, link['href'])

    @classmethod
    def get_comic_info(cls, soup, link):
        title = soup.find('title').string
        title_imgs = soup.find('div', id='tt').find_all('img')
        assert len(title_imgs) == 1
        strip_imgs = soup.find_all('img', id='strip')
        assert len(strip_imgs) == 1
        imgs = title_imgs + strip_imgs
        desc = ' '.join(i['title'] for i in imgs)
        return {
            'title': title,
            'img': [i['src'] for i in imgs],
            'description': desc,
        }


class ScandinaviaAndTheWorld(GenericNavigableComic):
    """Class to retrieve Scandinavia And The World comics."""
    name = 'satw'
    long_name = 'Scandinavia And The World'
    url = 'http://satwcomic.com'

    @classmethod
    def get_first_comic_link(cls):
        return {'href': 'http://satwcomic.com/sweden-denmark-and-norway'}

    @classmethod
    def get_next_comic_link(cls, last_soup):
        return last_soup.find('a', accesskey='n')

    @classmethod
    def get_comic_info(cls, soup, link):
        title = soup.find('meta', attrs={'name': 'twitter:label1'})['content']
        desc = soup.find('meta', property='og:description')['content']
        imgs = soup.find('img', itemprop="image")
        return {
            'title': title,
            'description': desc,
            'img': [i['src'] for i in imgs],
        }


class SomethingOfThatIlk(GenericComic):
    """Class to retrieve the Something Of That Ilk comics."""
    name = 'somethingofthatilk'
    long_name = 'Something Of That Ilk'
    url = 'http://www.somethingofthatilk.com'

    @classmethod
    def get_next_comic(cls, last_comic):
        return []  # Does not exist anymore


class InfiniteMonkeyBusiness(GenericNavigableComic):
    """Generic class to retrieve InfiniteMonkeyBusiness comics."""
    name = 'monkey'
    long_name = 'Infinite Monkey Business'
    url = 'http://infinitemonkeybusiness.net'

    @classmethod
    def get_first_comic_link(cls):
        return {'href': 'http://infinitemonkeybusiness.net/comic/pillory/'}

    @classmethod
    def get_next_comic_link(cls, last_soup):
        return last_soup.find('a', class_='navi comic-nav-next navi-next')

    @classmethod
    def get_comic_info(cls, soup, link):
        title = soup.find('meta', property='og:title')['content']
        imgs = soup.find_all('meta', property='og:image')
        return {
            'title': title,
            'img': [i['content'] for i in imgs],
        }


class Wondermark(GenericListableComic):
    """Class to retrieve the Wondermark comics."""
    name = 'wondermark'
    long_name = 'Wondermark'
    url = 'http://wondermark.com'

    @classmethod
    def get_url_from_archive_element(cls, link):
        return link['href']

    @classmethod
    def get_archive_elements(cls):
        archive_url = urljoin_wrapper(cls.url, 'archive/')
        return reversed(get_soup_at_url(archive_url).find_all('a', rel='bookmark'))

    @classmethod
    def get_comic_info(cls, soup, link):
        date_str = soup.find('div', class_='postdate').find('em').string
        day = string_to_date(remove_st_nd_rd_th_from_date(date_str), "%B %d, %Y")
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
        return {
            'month': day.month,
            'year': day.year,
            'day': day.day,
            'img': img_src,
            'title': title,
            'alt': alt,
            'tags': ' '.join(t.string for t in soup.find('div', class_='postmeta').find_all('a', rel='tag')),
        }


class WarehouseComic(GenericNavigableComic):
    """Class to retrieve Warehouse Comic comics."""
    name = 'warehouse'
    long_name = 'Warehouse Comic'
    url = 'http://warehousecomic.com'

    @classmethod
    def get_first_comic_link(cls):
        return get_soup_at_url(cls.url).find('a', class_='navi navi-first')

    @classmethod
    def get_next_comic_link(cls, last_soup):
        return last_soup.find('link', rel='next')

    @classmethod
    def get_comic_info(cls, soup, link):
        date_str = soup.find('span', class_='post-date').string
        day = string_to_date(date_str, "%B %d, %Y")
        return {
            'img': [i['src'] for i in soup.find('div', id='comic').find_all('img')],
            'title': soup.find('h2', class_='post-title').string,
            'day': day.day,
            'month': day.month,
            'year': day.year,
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


class Penmen(GenericNavigableComic):
    """Class to retrieve Penmen comics."""
    name = 'penmen'
    long_name = 'Penmen'
    url = 'http://penmen.com'

    @classmethod
    def get_first_comic_link(cls):
        return {'href': 'http://penmen.com/comic/penmen-comic-strip-the-sprinkler/'}

    @classmethod
    def get_next_comic_link(cls, last_soup):
        return last_soup.find('link', rel='next')

    @classmethod
    def get_comic_info(cls, soup, link):
        url2 = soup.find('link', rel='shortlink')['href']
        title = soup.find("h1", class_="entry-title").string
        img = soup.find('meta', property='og:image')['content']
        author = soup.find("span", class_="author vcard").find("a").string
        date_str = soup.find("time", class_="entry-date published").string
        day = string_to_date(date_str, '%Y/%m/%d')
        return {
            'url2': url2,
            'title': title,
            'author': author,
            'month': day.month,
            'year': day.year,
            'day': day.day,
            'img': [img],
        }


class TheDoghouseDiaries(GenericNavigableComic):
    """Class to retrieve The Dog House Diaries comics."""
    name = 'doghouse'
    long_name = 'The Dog House Diaries'
    url = 'http://thedoghousediaries.com'

    @classmethod
    def get_first_comic_link(cls):
        return get_soup_at_url(cls.url).find('a', id='firstlink')

    @classmethod
    def get_next_comic_link(cls, last_soup):
        return last_soup.find('a', id='nextlink')

    @classmethod
    def get_comic_info(cls, soup, link):
        comic_img_re = re.compile('^dhdcomics/.*')
        img = soup.find('img', src=comic_img_re)
        comic_url = cls.get_url_from_link(link)
        return {
            'title': soup.find('h2', id='titleheader').string,
            'title2': soup.find('div', id='subtext').string,
            'alt': img.get('title'),
            'img': [urljoin_wrapper(comic_url, img['src'].strip())],
            'num': int(comic_url.split('/')[-1]),
        }


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
                imgs = [soup.find('div', id='comic').find('img')]
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


class DiscoBleach(GenericComic):
    """Class to retrieve Disco Bleach Comics."""
    name = 'discobleach'
    long_name = 'Disco Bleach'
    url = 'http://discobleach.com'

    @classmethod
    def get_next_comic(cls, last_comic):
        return []  # FIXME: Does not work anymore


class TubeyToons(GenericComic):
    """Class to retrieve TubeyToons comics."""
    # Also on http://tapastic.com/series/Tubey-Toons
    name = 'tubeytoons'
    long_name = 'Tubey Toons'
    url = 'http://tubeytoons.com'

    @classmethod
    def get_next_comic(cls, last_comic):
        return []  # FIXME: Does not work anymore


class CompletelySeriousComics(GenericNavigableComic):
    """Class to retrieve Completely Serious comics."""
    name = 'completelyserious'
    long_name = 'Completely Serious Comics'
    url = 'http://completelyseriouscomics.com'

    @classmethod
    def get_first_comic_link(cls):
        return get_soup_at_url(cls.url).find('a', class_='navi navi-first')

    @classmethod
    def get_next_comic_link(cls, last_soup):
        return last_soup.find('a', class_='navi navi-next')

    @classmethod
    def get_comic_info(cls, soup, link):
        title = soup.find('h2', class_='post-title').string
        author = soup.find('span', class_='post-author').contents[1].string
        date_str = soup.find('span', class_='post-date').string
        day = string_to_date(date_str, '%B %d, %Y')
        imgs = soup.find('div', class_='comicpane').find_all('img')
        assert imgs
        alt = imgs[0]['title']
        assert all(i['title'] == i['alt'] == alt for i in imgs)
        return {
            'month': day.month,
            'year': day.year,
            'day': day.day,
            'img': [i['src'] for i in imgs],
            'title': title,
            'alt': alt,
            'author': author,
        }


class PoorlyDrawnLines(GenericListableComic):
    """Class to retrieve Poorly Drawn Lines comics."""
    name = 'poorlydrawn'
    long_name = 'Poorly Drawn Lines'
    url = 'http://poorlydrawnlines.com'

    @classmethod
    def get_comic_info(cls, soup, link):
        imgs = soup.find('div', class_='post').find_all('img')
        assert len(imgs) <= 1
        return {
            'img': [i['src'] for i in imgs],
            'title': imgs[0].get('title', "") if imgs else "",
        }

    @classmethod
    def get_url_from_archive_element(cls, link):
        return link['href']

    @classmethod
    def get_archive_elements(cls):
        url_re = re.compile('^%s/comic/.' % cls.url)
        return reversed(get_soup_at_url(urljoin_wrapper(cls.url, 'archive')).find_all('a', href=url_re))


class LoadingComics(GenericNavigableComic):
    """Class to retrieve Loading Artist comics."""
    name = 'loadingartist'
    long_name = 'Loading Artist'
    url = 'http://www.loadingartist.com/latest'

    @classmethod
    def get_first_comic_link(cls):
        return get_soup_at_url(cls.url).find('a', title="First")

    @classmethod
    def get_next_comic_link(cls, last_soup):
        return last_soup.find('a', title='Next')

    @classmethod
    def get_comic_info(cls, soup, link):
        title = soup.find('h1').string
        date_str = soup.find('span', class_='date').string.strip()
        day = string_to_date(date_str, "%B %d, %Y")
        imgs = soup.find('div', class_='comic').find_all('img', alt='', title='')
        return {
            'title': title,
            'img': [i['src'] for i in imgs],
            'month': day.month,
            'year': day.year,
            'day': day.day,
        }


class ChuckleADuck(GenericNavigableComic):
    """Class to retrieve Chuckle-A-Duck comics."""
    name = 'chuckleaduck'
    long_name = 'Chuckle-A-duck'
    url = 'http://chuckleaduck.com'

    @classmethod
    def get_first_comic_link(cls):
        return get_soup_at_url(cls.url).find('div', class_='nav-first').find('a')

    @classmethod
    def get_next_comic_link(cls, last_soup):
        return last_soup.find('div', class_='nav-next').find('a')

    @classmethod
    def get_comic_info(cls, soup, link):
        date_str = soup.find('span', class_='post-date').string
        day = string_to_date(remove_st_nd_rd_th_from_date(date_str), "%B %d, %Y")
        author = soup.find('span', class_='post-author').string
        imgs = soup.find('div', id='comic').find_all('img')
        title = imgs[0]['title'] if imgs else ""
        assert all(i['title'] == i['alt'] == title for i in imgs)
        return {
            'month': day.month,
            'year': day.year,
            'day': day.day,
            'img': [i['src'] for i in imgs],
            'title': title,
            'author': author,
        }


class DepressedAlien(GenericNavigableComic):
    """Class to retrieve Depressed Alien Comics."""
    name = 'depressedalien'
    long_name = 'Depressed Alien'
    url = 'http://depressedalien.com'

    @classmethod
    def get_first_comic_link(cls):
        return get_soup_at_url(cls.url).find('img', attrs={'name': 'beginArrow'}).parent

    @classmethod
    def get_next_comic_link(cls, last_soup):
        return last_soup.find('img', attrs={'name': 'rightArrow'}).parent

    @classmethod
    def get_url_from_link(cls, link):
        return urljoin_wrapper(cls.url, link['href'])

    @classmethod
    def get_comic_info(cls, soup, link):
        title = soup.find('meta', attrs={'name': 'twitter:title'})['content']
        imgs = soup.find_all('meta', property='og:image')
        return {
            'title': title,
            'img': [i['content'] for i in imgs],
        }


class ThingsInSquares(GenericListableComic):
    """Class to retrieve Things In Squares comics."""
    # This can be retrieved in other languages
    name = 'squares'
    long_name = 'Things in squares'
    url = 'http://www.thingsinsquares.com'

    @classmethod
    def get_comic_info(cls, soup, tr):
        _, td2, td3 = tr.find_all('td')
        a = td2.find('a')
        date_str = td3.string
        day = string_to_date(date_str, "%m.%d.%y")
        title = a.string
        title2 = soup.find('meta', property='og:title')['content']
        desc = soup.find('meta', property='og:description')
        description = desc['content'] if desc else ''
        tags = ' '.join(t['content'] for t in soup.find_all('meta', property='article:tag'))
        imgs = soup.find('div', class_='entry-content').find_all('img')
        return {
            'day': day.day,
            'month': day.month,
            'year': day.year,
            'title': title,
            'title2': title2,
            'description': description,
            'tags': tags,
            'img': [i['src'] for i in imgs],
            'alt': ' '.join(i['alt'] for i in imgs),
        }

    @classmethod
    def get_url_from_archive_element(cls, tr):
        _, td2, td3 = tr.find_all('td')
        return td2.find('a')['href']

    @classmethod
    def get_archive_elements(cls):
        archive_url = urljoin_wrapper(cls.url, 'archive')
        return reversed(get_soup_at_url(archive_url).find('tbody').find_all('tr'))


class HappleTea(GenericNavigableComic):
    """Class to retrieve Happle Tea Comics."""
    name = 'happletea'
    long_name = 'Happle Tea'
    url = 'http://www.happletea.com'

    @classmethod
    def get_first_comic_link(cls):
        return get_soup_at_url(cls.url).find('a', class_='navi navi-first')

    @classmethod
    def get_next_comic_link(cls, last_soup):
        return last_soup.find('a', class_='navi navi-next')

    @classmethod
    def get_comic_info(cls, soup, link):
        imgs = soup.find('div', id='comic').find_all('img')
        post = soup.find('div', class_='post-content')
        title = post.find('h2', class_='post-title').string
        author = post.find('a', rel='author').string
        date_str = post.find('span', class_='post-date').string
        day = string_to_date(date_str, "%B %d, %Y")
        assert all(i['alt'] == i['title'] for i in imgs)
        return {
            'title': title,
            'img': [i['src'] for i in imgs],
            'alt': ''.join(i['alt'] for i in imgs),
            'month': day.month,
            'year': day.year,
            'day': day.day,
            'author': author,
        }


class FatAwesomeComics(GenericNavigableComic):
    """Class to retrieve Fat Awesome Comics."""
    name = 'fatawesome'
    long_name = 'Fat Awesome'
    url = 'http://fatawesome.com/comics'

    @classmethod
    def get_first_comic_link(cls):
        return {'href': 'http://fatawesome.com/shortbus/'}

    @classmethod
    def get_next_comic_link(cls, last_soup):
        return last_soup.find('a', rel='next')

    @classmethod
    def get_comic_info(cls, soup, link):
        title = soup.find('meta', attrs={'name': 'twitter:title'})['content']
        description = soup.find('meta', attrs={'name': 'description'})['content']
        tags_prop = soup.find('meta', property='article:tag')
        tags = tags_prop['content'] if tags_prop else ""
        date_str = soup.find('meta', property='article:published_time')['content'][:10]
        day = string_to_date(date_str, "%Y-%m-%d")
        imgs = soup.find_all('img', attrs={'data-recalc-dims': "1"})
        assert len(imgs) == 1
        return {
            'title': title,
            'description': description,
            'tags': tags,
            'alt': "".join(i['alt'] for i in imgs),
            'img': [i['src'].rsplit('?', 1)[0] for i in imgs],
            'month': day.month,
            'year': day.year,
            'day': day.day,
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


class GoneIntoRapture(GenericNavigableComic):
    """Class to retrieve Gone Into Rapture comics."""
    name = 'rapture'
    long_name = 'Gone Into Rapture'
    url = 'http://www.goneintorapture.com'

    @classmethod
    def get_first_comic_link(cls):
        return get_soup_at_url(cls.url).find('a', class_='navi navi-first')

    @classmethod
    def get_next_comic_link(cls, last_soup):
        return last_soup.find('a', class_='navi navi-next')

    @classmethod
    def get_comic_info(cls, soup, link):
        imgs = soup.find('div', id='comic').find_all('img')
        assert all(i['alt'] == i['title'] == '' for i in imgs)
        date_str = soup.find('meta', property='article:published_time')['content'][:10]
        day = string_to_date(date_str, "%Y-%m-%d")
        title = soup.find('meta', property='og:title')['content']
        desc = soup.find('meta', property='og:description')['content']
        return {
            'img': [i['src'] for i in imgs],
            'month': day.month,
            'year': day.year,
            'day': day.day,
            'title': title,
            'description': desc,
        }


class LonnieMillsap(GenericNavigableComic):
    """Class to retrieve Lonnie Millsap's comics."""
    name = 'millsap'
    long_name = 'Lonnie Millsap'
    url = 'http://www.lonniemillsap.com'

    @classmethod
    def get_first_comic_link(cls):
        return {'href': 'http://www.lonniemillsap.com/?p=42'}

    @classmethod
    def get_next_comic_link(cls, last_soup):
        return last_soup.find('link', rel='next')

    @classmethod
    def get_comic_info(cls, soup, link):
        title = soup.find('h2', class_='post-title').string
        post = soup.find('div', class_='post-content')
        author = post.find("span", class_="post-author").find("a").string
        date_str = post.find("span", class_="post-date").string
        day = string_to_date(date_str, "%B %d, %Y")
        imgs = post.find("div", class_="entry").find_all("img")
        return {
            'title': title,
            'author': author,
            'img': [i['src'] for i in imgs],
            'month': day.month,
            'year': day.year,
            'day': day.day,
        }


class ThorsThundershack(GenericNavigableComic):
    """Class to retrieve Thor's Thundershack comics."""
    name = 'thor'
    long_name = 'Thor\'s Thundershack'
    url = 'http://www.thorsthundershack.com'

    @classmethod
    def get_first_comic_link(cls):
        return get_soup_at_url(cls.url).find('a', class_='first navlink')

    @classmethod
    def get_next_comic_link(cls, last_soup):
        return last_soup.find('a', class_='next navlink')

    @classmethod
    def get_url_from_link(cls, link):
        return urljoin_wrapper(cls.url, link['href'])

    @classmethod
    def get_comic_info(cls, soup, link):
        title = soup.find('meta', attrs={'name': 'description'})["content"]
        description = soup.find('div', itemprop='articleBody').text
        date_str = soup.find('time', itemprop='datePublished')["datetime"]
        author = soup.find('span', itemprop='author copyrightHolder').string
        imgs = soup.find_all('img', itemprop='image')
        assert all(i['title'] == i['alt'] for i in imgs)
        alt = imgs[0]['alt'] if imgs else ""
        day = string_to_date(date_str, "%Y-%m-%d %H:%M:%S")
        return {
            'img': [urljoin_wrapper(cls.url, i['src']) for i in imgs],
            'month': day.month,
            'year': day.year,
            'day': day.day,
            'author': author,
            'title': title,
            'alt': alt,
            'description': description,
        }


class EveryDayBlues(GenericNavigableComic):
    """Class to retrieve EveryDayBlues Comics."""
    name = "blues"
    long_name = "Every Day Blues"
    url = "http://everydayblues.net"

    @classmethod
    def get_first_comic_link(cls):
        return get_soup_at_url(cls.url).find('a', class_='navi navi-first')

    @classmethod
    def get_next_comic_link(cls, last_soup):
        return last_soup.find('a', class_='navi navi-next')

    @classmethod
    def get_comic_info(cls, soup, link):
        title = soup.find("h2", class_="post-title").string
        author = soup.find("span", class_="post-author").find("a").string
        date_str = soup.find("span", class_="post-date").string
        day = string_to_date(date_str, "%d. %B %Y", "de_DE.utf8")
        imgs = soup.find("div", id="comic").find_all("img")
        assert all(i['alt'] == i['title'] == title for i in imgs)
        assert len(imgs) <= 1
        return {
            'img': [i['src'] for i in imgs],
            'title': title,
            'author': author,
            'day': day.day,
            'month': day.month,
            'year': day.year
        }


class BiterComics(GenericNavigableComic):
    """Class to retrieve Biter Comics."""
    name = "biter"
    long_name = "Biter Comics"
    url = "http://www.bitercomics.com"

    @classmethod
    def get_first_comic_link(cls):
        return get_soup_at_url(cls.url).find('a', class_='navi navi-first')

    @classmethod
    def get_next_comic_link(cls, last_soup):
        return last_soup.find('a', class_='navi comic-nav-next navi-next')

    @classmethod
    def get_comic_info(cls, soup, link):
        title = soup.find("h1", class_="entry-title").string
        author = soup.find("span", class_="author vcard").find("a").string
        date_str = soup.find("span", class_="entry-date").string
        day = string_to_date(date_str, "%B %d, %Y")
        imgs = soup.find("div", id="comic").find_all("img")
        assert all(i['alt'] == i['title'] for i in imgs)
        assert len(imgs) == 1
        alt = imgs[0]['alt']
        return {
            'img': [i['src'] for i in imgs],
            'title': title,
            'alt': alt,
            'author': author,
            'day': day.day,
            'month': day.month,
            'year': day.year
        }


class TheAwkwardYeti(GenericNavigableComic):
    """Class to retrieve The Awkward Yeti comics."""
    name = 'yeti'
    long_name = 'The Awkward Yeti'
    url = 'http://theawkwardyeti.com'

    @classmethod
    def get_first_comic_link(cls):
        return get_soup_at_url(cls.url).find('a', class_='navi navi-first')

    @classmethod
    def get_next_comic_link(cls, last_soup):
        return last_soup.find('a', class_='navi comic-nav-next navi-next')

    @classmethod
    def get_comic_info(cls, soup, link):
        title = soup.find('h2', class_='post-title').string
        date_str = soup.find("span", class_="post-date").string
        day = string_to_date(date_str, "%B %d, %Y")
        imgs = soup.find("div", id="comic").find_all("img")
        assert all(idx > 0 or i['alt'] == i['title'] for idx, i in enumerate(imgs))
        return {
            'img': [i['src'] for i in imgs],
            'title': title,
            'day': day.day,
            'month': day.month,
            'year': day.year
        }


class LastPlaceComics(GenericNavigableComic):
    """Class to retrieve Last Place Comics."""
    name = 'lastplace'
    long_name = 'LastPlaceComics'
    url = "http://lastplacecomics.com"

    @classmethod
    def get_first_comic_link(cls):
        return get_soup_at_url(cls.url).find('a', class_='comic-nav-base comic-nav-first')

    @classmethod
    def get_next_comic_link(cls, last_soup):
        return last_soup.find('a', class_='comic-nav-base comic-nav-next')

    @classmethod
    def get_comic_info(cls, soup, link):
        title = soup.find('h2', class_='post-title').string
        author = soup.find("span", class_="post-author").find("a").string
        date_str = soup.find("span", class_="post-date").string
        day = string_to_date(date_str, "%B %d, %Y")
        imgs = soup.find("div", id="comic").find_all("img")
        assert all(i['alt'] == i['title'] for i in imgs)
        assert len(imgs) <= 1
        alt = imgs[0]['alt'] if imgs else ""
        return {
            'img': [i['src'] for i in imgs],
            'title': title,
            'alt': alt,
            'author': author,
            'day': day.day,
            'month': day.month,
            'year': day.year
        }


class TalesOfAbsurdity(GenericNavigableComic):
    """Class to retrieve Tales Of Absurdity comics."""
    # Also on http://tapastic.com/series/Tales-Of-Absurdity
    name = 'absurdity'
    long_name = 'Tales of Absurdity'
    url = 'http://talesofabsurdity.com'

    @classmethod
    def get_first_comic_link(cls):
        return get_soup_at_url(cls.url).find('a', class_='navi navi-first')

    @classmethod
    def get_next_comic_link(cls, last_soup):
        return last_soup.find('link', rel='next')

    @classmethod
    def get_comic_info(cls, soup, link):
        title = soup.find('h2', class_='post-title').string
        author = soup.find("span", class_="post-author").find("a").string
        date_str = soup.find("span", class_="post-date").string
        day = string_to_date(date_str, "%B %d, %Y")
        imgs = soup.find("div", id="comic").find_all("img")
        assert all(i['alt'] == i['title'] for i in imgs)
        alt = imgs[0]['alt'] if imgs else ""
        return {
            'img': [i['src'] for i in imgs],
            'title': title,
            'alt': alt,
            'author': author,
            'day': day.day,
            'month': day.month,
            'year': day.year
        }


class EndlessOrigami(GenericNavigableComic):
    """Class to retrieve Endless Origami Comics."""
    name = "origami"
    long_name = "Endless Origami"
    url = "http://endlessorigami.com"

    @classmethod
    def get_first_comic_link(cls):
        return get_soup_at_url(cls.url).find('a', class_='navi navi-first')

    @classmethod
    def get_next_comic_link(cls, last_soup):
        return last_soup.find('link', rel='next')

    @classmethod
    def get_comic_info(cls, soup, link):
        title = soup.find('h2', class_='post-title').string
        author = soup.find("span", class_="post-author").find("a").string
        date_str = soup.find("span", class_="post-date").string
        day = string_to_date(date_str, "%B %d, %Y")
        imgs = soup.find("div", id="comic").find_all("img")
        assert all(i['alt'] == i['title'] for i in imgs)
        alt = imgs[0]['alt'] if imgs else ""
        return {
            'img': [i['src'] for i in imgs],
            'title': title,
            'alt': alt,
            'author': author,
            'day': day.day,
            'month': day.month,
            'year': day.year
        }


class BuniComic(GenericNavigableComic):
    """Class to retrieve Buni Comics."""
    name = 'buni'
    long_name = 'BuniComics'
    url = 'http://www.bunicomic.com'

    @classmethod
    def get_first_comic_link(cls):
        return get_soup_at_url(cls.url).find('a', class_='comic-nav-base comic-nav-first')

    @classmethod
    def get_next_comic_link(cls, last_soup):
        return last_soup.find('a', class_='comic-nav-base comic-nav-next')

    @classmethod
    def get_comic_info(cls, soup, link):
        imgs = soup.find('div', id='comic').find_all('img')
        assert all(i['alt'] == i['title'] for i in imgs)
        assert len(imgs) == 1
        return {
            'img': [i['src'] for i in imgs],
            'title': imgs[0]['title'],
        }


class UnearthedComics(GenericNavigableComic):
    """Class to retrieve Unearthed comics."""
    # Also on http://tapastic.com/series/UnearthedComics
    # Also on http://unearthedcomics.tumblr.com
    name = 'unearthed'
    long_name = 'Unearthed Comics'
    url = 'http://unearthedcomics.com'

    @classmethod
    def get_first_comic_link(cls):
        return {'href': 'http://unearthedcomics.com/comics/world-with-turn-signals/'}

    @classmethod
    def get_next_comic_link(cls, last_soup):
        return last_soup.find('link', rel='next')

    @classmethod
    def get_comic_info(cls, soup, link):
        short_url = soup.find('link', rel='shortlink')['href']
        title_elt = soup.find('h1') or soup.find('h2')
        title = title_elt.string if title_elt else ""
        desc = soup.find('meta', property='og:description')
        date_str = soup.find('time', class_='published updated hidden')['datetime']
        day = string_to_date(date_str, "%Y-%m-%d")
        post = soup.find('div', class_="entry content entry-content type-portfolio")
        imgs = post.find_all('img')
        return {
            'title': title,
            'description': desc,
            'url2': short_url,
            'img': [i['src'] for i in imgs],
            'month': day.month,
            'year': day.year,
            'day': day.day,
        }


class PainTrainComic(GenericNavigableComic):
    """Class to retrieve Pain Train Comics."""
    name = 'paintrain'
    long_name = 'Pain Train Comics'
    url = 'http://paintraincomic.com'

    @classmethod
    def get_first_comic_link(cls):
        return get_soup_at_url(cls.url).find('a', class_='navi navi-first')

    @classmethod
    def get_next_comic_link(cls, last_soup):
        return last_soup.find('link', rel='next')

    @classmethod
    def get_comic_info(cls, soup, link):
        title = soup.find('h2', class_='post-title').string
        short_url = soup.find('link', rel='shortlink')['href']
        short_url_re = re.compile('^%s/\\?p=([0-9]*)' % cls.url)
        num = int(short_url_re.match(short_url).groups()[0])
        imgs = soup.find('div', id='comic').find_all('img')
        alt = imgs[0]['title']
        assert all(i['alt'] == i['title'] == alt for i in imgs)
        date_str = soup.find('span', class_='post-date').string
        day = string_to_date(date_str, "%d/%m/%Y")
        return {
            'short_url': short_url,
            'num': num,
            'img': [i['src'] for i in imgs],
            'month': day.month,
            'year': day.year,
            'day': day.day,
            'alt': alt,
            'title': title,
        }


class MakeItStoopid(GenericNavigableComic):
    """Class to retrieve Make It Stoopid Comics."""
    name = 'stoopid'
    long_name = 'Make it stoopid'
    url = 'http://makeitstoopid.com/comic.php'

    @classmethod
    def get_nav(cls, soup):
        cnav = soup.find_all(class_='cnav')
        nav1, nav2 = cnav[:5], cnav[5:]
        assert nav1 == nav2
        # begin, prev, archive, next_, end = nav1
        return [None if i.get('href', None) is None else i for i in nav1]

    @classmethod
    def get_first_comic_link(cls):
        return cls.get_nav(get_soup_at_url(cls.url))[0]

    @classmethod
    def get_next_comic_link(cls, last_soup):
        return cls.get_nav(last_soup)[3]

    @classmethod
    def get_comic_info(cls, soup, link):
        title = link['title']
        imgs = soup.find_all('img', id='comicimg')
        return {
            'title': title,
            'img': [i['src'] for i in imgs],
        }


class GenericTumblr(GenericNavigableComic):
    """Generic class to retrieve comics from Tumblr."""

    @classmethod
    def get_first_comic_link(cls):
        return {'href': cls.get_first_comic_url()}

    @classmethod
    def get_next_comic_link(cls, last_soup):
        return last_soup.find('div', class_='nextprev').find('a', class_='prev')  # prev is next

    @classmethod
    def get_prev_comic_link(cls, last_soup):
        return last_soup.find('div', class_='nextprev').find('a', class_='next')  # next is prev

    @classmethod
    def get_comic_info(cls, soup, link):
        desc = soup.find('meta', property='og:description')
        title = desc['content'] if desc else ""
        imgs = soup.find_all('meta', property='og:image')
        date_li = soup.find('li', class_='date') or soup.find('li', class_='date-reblogged')
        date_str = date_li.find('a')['title']
        day = string_to_date(date_str, "%a. %B %d, %Y @ %I:%M %p")
        return {
            'title': title,
            'img': [i['content'] for i in imgs],
            'day': day.day,
            'month': day.month,
            'year': day.year,
        }


class IrwinCardozo(GenericTumblr):
    """Class to retrieve Irwin Cardozo Comics."""
    name = 'irwinc'
    long_name = 'Irwin Cardozo'
    url = 'http://irwincardozocomics.tumblr.com'

    @classmethod
    def get_first_comic_url(cls):
        return "http://irwincardozocomics.tumblr.com/post/72201129995/only-human-irwinc"


class AccordingToDevin(GenericTumblr):
    """Class to retrieve According To Devin comics."""
    name = 'devin'
    long_name = 'According To Devin'
    url = 'http://accordingtodevin.tumblr.com'

    @classmethod
    def get_first_comic_url(cls):
        return "http://accordingtodevin.tumblr.com/post/40112722337"


class HorovitzComics(GenericListableComic):
    """Generic class to handle the logic common to the different comics from Horovitz."""
    url = 'http://www.horovitzcomics.com'
    img_re = re.compile('.*comics/([0-9]*)/([0-9]*)/([0-9]*)/.*$')
    link_re = NotImplemented

    @classmethod
    def get_comic_info(cls, soup, link):
        href = link['href']
        num = int(cls.link_re.match(href).groups()[0])
        title = link.string
        imgs = soup.find_all('img', id='comic')
        assert len(imgs) == 1
        year, month, day = [int(s)
                            for s in cls.img_re.match(imgs[0]['src']).groups()]
        return {
            'title': title,
            'day': day,
            'month': month,
            'year': year,
            'img': [i['src'] for i in imgs],
            'num': num,
        }

    @classmethod
    def get_url_from_archive_element(cls, link):
        return urljoin_wrapper(cls.url, link['href'])

    @classmethod
    def get_archive_elements(cls):
        archive = 'http://www.horovitzcomics.com/comics/archive/'
        return reversed(get_soup_at_url(archive).find_all('a', href=cls.link_re))


class HorovitzNew(HorovitzComics):
    name = 'horovitznew'
    long_name = 'Horovitz New'
    link_re = re.compile('^/comics/new/([0-9]+)$')


class HorovitzClassic(HorovitzComics):
    name = 'horovitzclassic'
    long_name = 'Horovitz Classic'
    link_re = re.compile('^/comics/classic/([0-9]+)$')


class GenericGoComic(GenericNavigableComic):
    """Generic class to handle the logic common to comics from gocomics.com."""
    url_date_re = re.compile('.*/([0-9]*)/([0-9]*)/([0-9]*)$')

    @classmethod
    def get_first_comic_link(cls):
        return get_soup_at_url(cls.url).find('a', class_='beginning')

    @classmethod
    def get_next_comic_link(cls, last_soup):
        return last_soup.find('a', class_='next', href=cls.url_date_re)

    @classmethod
    def get_url_from_link(cls, link):
        gocomics = 'http://www.gocomics.com'
        return urljoin_wrapper(gocomics, link['href'])

    @classmethod
    def get_comic_info(cls, soup, link):
        url = cls.get_url_from_link(link)
        year, month, day = [int(s)
                            for s in cls.url_date_re.match(url).groups()]
        return {
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


class Brevity(GenericGoComic):
    """Class to retrieve Brevity comics."""
    name = 'brevity'
    long_name = 'Brevity'
    url = 'http://www.gocomics.com/brevity'


class MichaelRamirez(GenericGoComic):
    """Class to retrieve Michael Ramirez comics."""
    name = 'ramirez'
    long_name = 'Michael Ramirez'
    url = 'http://www.gocomics.com/michaelramirez'


class MikeLuckovich(GenericGoComic):
    """Class to retrieve Mike Luckovich comics."""
    name = 'luckovich'
    long_name = 'Mike Luckovich'
    url = 'http://www.gocomics.com/mikeluckovich'


class JimBenton(GenericGoComic):
    """Class to retrieve Jim Benton comics."""
    name = 'benton'
    long_name = 'Jim Benton'
    url = 'http://www.gocomics.com/jim-benton-cartoons'


class TheArgyleSweater(GenericGoComic):
    """Class to retrieve the Argyle Sweater comics."""
    name = 'argyle'
    long_name = 'Argyle Sweater'
    url = 'http://www.gocomics.com/theargylesweater'


class SunnyStreet(GenericGoComic):
    """Class to retrieve Sunny Street comics."""
    name = 'sunny'
    long_name = 'Sunny Street'
    url = 'http://www.gocomics.com/sunny-street'


class OffTheMark(GenericGoComic):
    """Class to retrieve Off The Mark comics."""
    # From gocomics, not offthemark.com
    name = 'offthemark'
    long_name = 'Off The Mark'
    url = 'http://www.gocomics.com/offthemark'


class WuMo(GenericGoComic):
    """Class to retrieve WuMo comics."""
    # From gocomics, not wumo.com
    name = 'wumo'
    long_name = 'WuMo'
    url = 'http://www.gocomics.com/wumo'


class LunarBaboon(GenericGoComic):
    """Class to retrieve Lunar Baboon comics."""
    # From gocomics, not lunarbaboon.com
    name = 'lunarbaboon'
    long_name = 'Lunar Baboon'
    url = 'http://www.gocomics.com/lunarbaboon'


class SandersenGocomic(GenericGoComic):
    """Class to retrieve Sarah Andersen comics."""
    # From gocomics, not tapastic or http://sarahcandersen.com/
    name = 'sandersen-goc'
    long_name = 'Sarah Andersen (from GoComics)'
    url = 'http://www.gocomics.com/sarahs-scribbles'


class CalvinAndHobbesGoComic(GenericGoComic):
    """Class to retrieve Calvin and Hobbes comics."""
    # From gocomics, not http://marcel-oehler.marcellosendos.ch/comics/ch/
    name = 'calvin-goc'
    long_name = 'Calvin and Hobbes (from GoComics)'
    url = 'http://www.gocomics.com/calvinandhobbes'


class TapasticComic(GenericListableComic):
    """Generic class to handle the logic common to comics from tapastic.com."""

    @classmethod
    def get_comic_info(cls, soup, archive_element):
        date_str = archive_element['publishDate'].split()[0]
        year, month, day = [int(e) for e in date_str.split('-')]
        imgs = soup.find_all('img', class_='art-image')
        return {
            'day': day,
            'year': year,
            'month': month,
            'img': [i['src'] for i in imgs],
            'title': archive_element['title'],
        }

    @classmethod
    def get_url_from_archive_element(cls, archive_element):
        return 'http://tapastic.com/episode/' + str(archive_element['id'])

    @classmethod
    def get_archive_elements(cls):
        pref, suff = 'episodeList : ', ','
        # Information is stored in the javascript part
        # I don't know the clean way to get it so this is the ugly way.
        string = [s[len(pref):-len(suff)] for s in (s.decode('utf-8').strip() for s in urlopen_wrapper(cls.url).readlines()) if s.startswith(pref) and s.endswith(suff)][0]
        return json.loads(string)


class VegetablesForDessert(TapasticComic):
    """Class to retrieve Vegetables For Dessert comics."""
    name = 'vegetables'
    long_name = 'Vegetables For Dessert'
    url = 'http://tapastic.com/series/vegetablesfordessert'


class FowlLanguageComics(TapasticComic):
    """Class to retrieve Fowl Language comics."""
    # From tapastic, not http://www.fowllanguagecomics.com
    name = 'fowllanguage'
    long_name = 'Fowl Language Comics'
    url = 'http://tapastic.com/series/Fowl-Language-Comics'


class OscillatingProfundities(TapasticComic):
    """Class to retrieve Oscillating Profundities comics."""
    name = 'oscillating'
    long_name = 'Oscillating Profundities'
    url = 'http://tapastic.com/series/oscillatingprofundities'


class ZnoflatsComics(TapasticComic):
    """Class to retrieve Znoflats comics."""
    name = 'znoflats'
    long_name = 'Znoflats Comics'
    url = 'http://tapastic.com/series/Znoflats-Comics'


class SandersenTapastic(TapasticComic):
    """Class to retrieve Sarah Andersen comics."""
    # From tapastic, not gocomics or http://sarahcandersen.com/
    name = 'sandersen-tapa'
    long_name = 'Sarah Andersen (from Tapastic)'
    url = 'http://tapastic.com/series/Doodle-Time'


class TubeyToonsTapastic(TapasticComic):
    """Class to retrieve TubeyToons comics."""
    # From tapastic, not http://tubeytoons.com
    name = 'tubeytoons-tapa'
    long_name = 'Tubey Toons (from Tapastic)'
    url = 'http://tapastic.com/series/Tubey-Toons'


class UnearthedComicsTapastic(TapasticComic):
    """Class to retrieve Unearthed comics."""
    # Also on http://unearthedcomics.com
    # Also on http://unearthedcomics.tumblr.com
    name = 'unearthed-tapa'
    long_name = 'Unearthed Comics (from Tapastic)'
    url = 'http://tapastic.com/series/UnearthedComics'


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


def string_to_date(string, date_format, local=DEFAULT_LOCAL):
    """Function to convert string to date object.
    Wrapper around datetime.datetime.strptime."""
    # format described in https://docs.python.org/2/library/datetime.html#strftime-and-strptime-behavior
    prev_locale = locale.setlocale(locale.LC_ALL)
    if locale != prev_locale:
        locale.setlocale(locale.LC_ALL, local)
    ret = datetime.datetime.strptime(string, date_format).date()
    if locale != prev_locale:
        locale.setlocale(locale.LC_ALL, prev_locale)
    return ret


COMIC_NAMES = {c.name: c for c in get_subclasses(
    GenericComic) if c.name is not None}
