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
        - get_navi_link
        - get_comic_info
        - get_url_from_link
    """

    @classmethod
    def get_first_comic_link(cls):
        """Get link to first comics.

        Sometimes this can be retrieved of any comic page, sometimes on
        the archive page, sometimes it doesn't exist at all and one has
        to iterate backward to find it before hardcoding the result found.
        """
        raise NotImplementedError

    @classmethod
    def get_navi_link(cls, last_soup, next_):
        """Get link to next (or previous - for dev purposes) comic."""
        raise NotImplementedError

    @classmethod
    def get_comic_info(cls, soup, link):
        """Get information about a particular comics."""
        raise NotImplementedError

    @classmethod
    def get_url_from_link(cls, link):
        """Get url correponding to a link."""
        return link['href']

    @classmethod
    def get_next_link(cls, last_soup):
        """Get link to next comic."""
        return cls.get_navi_link(last_soup, True)

    @classmethod
    def get_prev_link(cls, last_soup):
        """Get link to previous comic."""
        return cls.get_navi_link(last_soup, False)

    @classmethod
    def get_next_comic(cls, last_comic):
        """Generic implementation of get_next_comic for navigable comics."""
        url = last_comic['url'] if last_comic else None
        next_comic = \
            cls.get_next_link(get_soup_at_url(url)) \
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
            next_comic = cls.get_next_link(soup)

    @classmethod
    def check_navigation(cls, url):
        """Check that navigation functions seem to be working - for dev purposes."""
        soup = get_soup_at_url(url)
        prevlink, nextlink = cls.get_prev_link(soup), cls.get_next_link(soup)
        if prevlink is None and nextlink is None:
            print("From %s : no previous nor next" % url)
        else:
            if prevlink:
                prevurl = cls.get_url_from_link(prevlink)
                prevsoup = get_soup_at_url(prevurl)
                prevnext = cls.get_url_from_link(cls.get_next_link(prevsoup))
                if prevnext != url:
                    print("From %s, going backward then forward leads to %s" % (url, prevnext))
            if nextlink:
                nexturl = cls.get_url_from_link(nextlink)
                if nexturl != url:
                    nextsoup = get_soup_at_url(nexturl)
                    nextprev = cls.get_url_from_link(cls.get_prev_link(nextsoup))
                    if nextprev != url:
                        print("From %s, going forward then backward leads to %s" % (url, nextprev))

    # This method is not defined by default and is not part of this class'API.
    # It is only used:
    # - during development
    # - in subclasses implementing it correctly
    if False:
        @classmethod
        def get_first_comic_url(cls):
            """Get first comic url

            Sometimes, the first comic cannot be reached directly so to start
            from the first comic one has to go to the previous comic until
            there is no previous comics. Once this URL is reached, it
            is better to hardcode it but for development purposes, it
            is convenient to have an automatic way to find it.
            """
            url = input("Get starting URL: ")
            print(url)
            comic = cls.get_prev_link(get_soup_at_url(url))
            while comic:
                url = cls.get_url_from_link(comic)
                print(url)
                comic = cls.get_prev_link(get_soup_at_url(url))
            return url


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
        """Get the archive elements (iterable)."""
        raise NotImplementedError

    @classmethod
    def get_url_from_archive_element(cls, archive_elt):
        """Get url correponding to an archive element."""
        raise NotImplementedError

    @classmethod
    def get_comic_info(cls, soup, archive_element):
        """Get information about a particular comics."""
        raise NotImplementedError

    @classmethod
    def get_next_comic(cls, last_comic):
        """Generic implementation of get_next_comic for listable comics."""
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
        if waiting_for_url is not None:
            print("Did not find %s : there might be a problem" % waiting_for_url)

# Helper functions corresponding to get_first_comic_link/get_navi_link


@classmethod
def get_link_rel_next(cls, last_soup, next_):
    """Implementation of get_navi_link."""
    return last_soup.find('link', rel='next' if next_ else 'prev')


@classmethod
def get_a_rel_next(cls, last_soup, next_):
    """Implementation of get_navi_link."""
    return last_soup.find('a', rel='next' if next_ else 'prev')


@classmethod
def get_a_navi_navinext(cls, last_soup, next_):
    """Implementation of get_navi_link."""
    return last_soup.find('a', class_='navi navi-next' if next_ else 'navi navi-prev')


@classmethod
def get_a_navi_comicnavnext_navinext(cls, last_soup, next_):
    """Implementation of get_navi_link."""
    return last_soup.find('a', class_='navi comic-nav-next navi-next' if next_ else 'navi comic-nav-previous navi-prev')


@classmethod
def get_a_comicnavbase_comicnavnext(cls, last_soup, next_):
    """Implementation of get_navi_link."""
    return last_soup.find('a', class_='comic-nav-base comic-nav-next' if next_ else 'comic-nav-base comic-nav-previous')


@classmethod
def get_a_navi_navifirst(cls):
    """Implementation of get_first_comic_link."""
    return get_soup_at_url(cls.url).find('a', class_='navi navi-first')


@classmethod
def get_div_navfirst_a(cls):
    """Implementation of get_first_comic_link."""
    return get_soup_at_url(cls.url).find('div', class_="nav-first").find('a')


@classmethod
def get_a_comicnavbase_comicnavfirst(cls):
    """Implementation of get_first_comic_link."""
    return get_soup_at_url(cls.url).find('a', class_='comic-nav-base comic-nav-first')


class GenericEmptyComic(GenericComic):
    """Generic class for comics where nothing is to be done."""

    @classmethod
    def get_next_comic(cls, last_comic):
        return []


class ExtraFabulousComics(GenericNavigableComic):
    """Class to retrieve Extra Fabulous Comics."""
    name = 'efc'
    long_name = 'Extra Fabulous Comics'
    url = 'http://extrafabulouscomics.com'
    get_navi_link = get_link_rel_next

    @classmethod
    def get_first_comic_link(cls):
        return get_soup_at_url(cls.url).find('a', title='FIRST')

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
    get_navi_link = get_link_rel_next

    @classmethod
    def get_first_comic_url(cls):
        """Get first comic url."""
        raise NotImplementedError

    @classmethod
    def get_first_comic_link(cls):
        return {'href': cls.get_first_comic_url()}

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


class LesCulottees(GenericLeMondeBlog):
    """Class to retrieve Les Culottees comics."""
    name = 'culottees'
    long_name = 'Les Culottees'
    url = "http://lesculottees.blog.lemonde.fr"

    @classmethod
    def get_first_comic_url(cls):
        return "http://lesculottees.blog.lemonde.fr/2016/01/11/clementine-delait-femme-a-barbe/"


class Rall(GenericNavigableComic):
    """Class to retrieve Ted Rall comics."""
    # Also on : http://www.gocomics.com/tedrall
    name = 'rall'
    long_name = "Ted Rall"
    url = "http://rall.com/comic"
    get_navi_link = get_link_rel_next

    @classmethod
    def get_first_comic_link(cls):
        # Not the first but I didn't find an efficient way to retrieve it
        return {'href': "http://rall.com/2014/01/30/los-angeles-times-cartoon-well-miss-those-california-flowers"}

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


class Dilem(GenericNavigableComic):
    """Class to retrieve Ali Dilem comics."""
    name = 'dilem'
    long_name = 'Ali Dilem'
    url = 'http://information.tv5monde.com/dilem'

    @classmethod
    def get_first_comic_link(cls):
        return {'href': "http://information.tv5monde.com/dilem/2004-06-26"}

    @classmethod
    def get_url_from_link(cls, link):
        return urljoin_wrapper(cls.url, link['href'])

    @classmethod
    def get_navi_link(cls, last_soup, next_):
        # prev is next / next is prev
        li = last_soup.find('li', class_='prev' if next_ else 'next')
        return li.find('a') if li else None

    @classmethod
    def get_comic_info(cls, soup, link):
        short_url = soup.find('link', rel='shortlink')['href']
        title = soup.find('meta', attrs={'name': 'twitter:title'})['content']
        imgs = soup.find_all('meta', property='og:image')
        date_str = soup.find('span', property='dc:date')['content']
        date_str = date_str[:10]
        day = string_to_date(date_str, "%Y-%m-%d")
        return {
            'short_url': short_url,
            'title': title,
            'img': [i['content'] for i in imgs],
            'day': day.day,
            'month': day.month,
            'year': day.year,
        }


class SpaceAvalanche(GenericNavigableComic):
    """Class to retrieve Space Avalanche comics."""
    name = 'avalanche'
    long_name = 'Space Avalanche'
    url = 'http://www.spaceavalanche.com'
    get_navi_link = get_link_rel_next

    @classmethod
    def get_first_comic_link(cls):
        return {'href': "http://www.spaceavalanche.com/2009/02/02/irish-sea/", 'title': "Irish Sea"}

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
    # Also on http://zenpencils.tumblr.com
    name = 'zenpencils'
    long_name = 'Zen Pencils'
    url = 'http://zenpencils.com'
    get_navi_link = get_link_rel_next

    @classmethod
    def get_first_comic_link(cls):
        return {'href': "http://zenpencils.com/comic/1-ralph-waldo-emerson-make-them-cry/"}

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
    get_first_comic_link = get_div_navfirst_a
    get_navi_link = get_a_rel_next

    @classmethod
    def get_comic_info(cls, soup, link):
        title = soup.find('h1', class_='comic-title').find('a').string
        date_str = soup.find('header', class_='comic-meta entry-meta').find('a').string
        day = string_to_date(date_str, "%B %d, %Y")
        # Bonus images may or may not be in meta og:image.
        imgs = soup.find_all('meta', property='og:image')
        imgs_src = [i['content'] for i in imgs]
        bonus = soup.find_all('img', attrs={'data-oversrc': True})
        bonus_src = [b['data-oversrc'] for b in bonus]
        all_imgs_src = imgs_src + [s for s in bonus_src if s not in imgs_src]
        all_imgs_src = [s for s in all_imgs_src if not s.endswith("/2016/01/bonus-panel.png")]
        tag_meta = soup.find('meta', property='article:tag')
        tags = tag_meta['content'] if tag_meta else ""
        return {
            'title': title,
            'month': day.month,
            'year': day.year,
            'day': day.day,
            'img': all_imgs_src,
            'tags': tags,
        }


class PenelopeBagieu(GenericNavigableComic):
    """Class to retrieve comics from Penelope Bagieu's blog."""
    name = 'bagieu'
    long_name = 'Ma vie est tout a fait fascinante (Bagieu)'
    url = 'http://www.penelope-jolicoeur.com'
    get_navi_link = get_link_rel_next

    @classmethod
    def get_first_comic_link(cls):
        return {'href': 'http://www.penelope-jolicoeur.com/2007/02/ma-vie-mon-oeuv.html'}

    @classmethod
    def get_comic_info(cls, soup, link):
        date_str = soup.find('h2', class_='date-header').string
        day = string_to_date(date_str, "%A %d %B %Y", "fr_FR.utf8")
        imgs = soup.find('div', class_='entry-body').find_all('img')
        title = soup.find('h3', class_='entry-header').string
        return {
            'title': title,
            'img': [i['src'] for i in imgs],
            'month': day.month,
            'year': day.year,
            'day': day.day,
        }


class OneOneOneOneComic(GenericNavigableComic):
    """Class to retrieve 1111 Comics."""
    name = '1111'
    long_name = '1111 Comics'
    url = 'http://www.1111comics.me'
    get_first_comic_link = get_div_navfirst_a
    get_navi_link = get_link_rel_next

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


class AngryAtNothing(GenericNavigableComic):
    """Class to retrieve Angry at Nothing comics."""
    # Also on http://tapastic.com/series/Comics-yeah-definitely-comics-
    name = 'angry'
    long_name = 'Angry At Nothing'
    url = 'http://www.angryatnothing.net'
    get_first_comic_link = get_div_navfirst_a
    get_navi_link = get_a_rel_next

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
    get_first_comic_link = get_div_navfirst_a
    get_navi_link = get_link_rel_next

    @classmethod
    def get_url_from_link(cls, link):
        return urljoin_wrapper(cls.url, link['href'])

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
    def get_navi_link(cls, last_soup, next_):
        link = last_soup.find('div', class_='nav-comic nav-right' if next_ else 'nav-comic nav-left')
        return link.find('a') if link else None

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
    get_navi_link = get_a_navi_comicnavnext_navinext

    @classmethod
    def get_first_comic_link(cls):
        return {'href': 'http://www.victimsofcircumsolar.com/comic/modern-addiction'}

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
    # Also on http://www.threewordphrase.tumblr.com
    name = 'threeword'
    long_name = 'Three Word Phrase'
    url = 'http://threewordphrase.com'

    @classmethod
    def get_first_comic_link(cls):
        return get_soup_at_url(cls.url).find('img', src='/firstlink.gif').parent

    @classmethod
    def get_navi_link(cls, last_soup, next_):
        link = last_soup.find('img', src='/nextlink.gif' if next_ else '/prevlink.gif').parent
        return None if link.get('href') is None else link

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


class DeadlyPanel(GenericNavigableComic):
    """Class to retrieve Deadly Panel comics."""
    name = 'deadly'
    long_name = 'Deadly Panel'
    url = 'http://www.deadlypanel.com'
    get_first_comic_link = get_a_navi_navifirst
    get_navi_link = get_a_navi_comicnavnext_navinext

    @classmethod
    def get_comic_info(cls, soup, link):
        imgs = soup.find('div', id='comic').find_all('img')
        assert all(i['alt'] == i['title'] for i in imgs)
        return {
            'img': [i['src'] for i in imgs],
        }


class TheGentlemanArmchair(GenericNavigableComic):
    """Class to retrieve The Gentleman Armchair comics."""
    name = 'gentlemanarmchair'
    long_name = 'The Gentleman Armchair'
    url = 'http://thegentlemansarmchair.com'
    get_first_comic_link = get_a_navi_navifirst
    get_navi_link = get_link_rel_next

    @classmethod
    def get_comic_info(cls, soup, link):
        title = soup.find('h2', class_='post-title').string
        author = soup.find("span", class_="post-author").find("a").string
        date_str = soup.find('span', class_='post-date').string
        day = string_to_date(date_str, "%B %d, %Y")
        imgs = soup.find('div', id='comic').find_all('img')
        return {
            'img': [i['src'] for i in imgs],
            'title': title,
            'author': author,
            'month': day.month,
            'year': day.year,
            'day': day.day,
        }


class MyExtraLife(GenericNavigableComic):
    """Class to retrieve My Extra Life comics."""
    name = 'extralife'
    long_name = 'My Extra Life'
    url = 'http://www.myextralife.com'
    get_navi_link = get_link_rel_next

    @classmethod
    def get_first_comic_link(cls):
        return get_soup_at_url(cls.url).find('a', class_='comic_nav_link first_comic_link')

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
    get_navi_link = get_a_rel_next

    @classmethod
    def get_first_comic_link(cls):
        return get_soup_at_url(cls.url).find('a', rel='start')

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


class PerryBibleFellowship(GenericListableComic):
    """Class to retrieve Perry Bible Fellowship comics."""
    name = 'pbf'
    long_name = 'Perry Bible Fellowship'
    url = 'http://pbfcomics.com'

    @classmethod
    def get_archive_elements(cls):
        comic_link_re = re.compile('^/[0-9]*/$')
        return reversed(get_soup_at_url(cls.url).find_all('a', href=comic_link_re))

    @classmethod
    def get_url_from_archive_element(cls, link):
        return urljoin_wrapper(cls.url, link['href'])

    @classmethod
    def get_comic_info(cls, soup, link):
        url = cls.get_url_from_archive_element(link)
        comic_img_re = re.compile('^/archive_b/PBF.*')
        name = link.string
        num = int(link['name'])
        href = link['href']
        assert href == '/%d/' % num
        imgs = soup.find_all('img', src=comic_img_re)
        assert len(imgs) == 1
        assert imgs[0]['alt'] == name
        return {
            'num': num,
            'name': name,
            'img': [urljoin_wrapper(url, i['src']) for i in imgs],
            'prefix': '%d-' % num,
        }


class Mercworks(GenericNavigableComic):
    """Class to retrieve Mercworks comics."""
    # Also on http://mercworks.tumblr.com
    name = 'mercworks'
    long_name = 'Mercworks'
    url = 'http://mercworks.net'
    get_first_comic_link = get_a_comicnavbase_comicnavfirst
    get_navi_link = get_a_rel_next

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


class BerkeleyMews(GenericListableComic):
    """Class to retrieve Berkeley Mews comics."""
    name = 'berkeley'
    long_name = 'Berkeley Mews'
    url = 'http://www.berkeleymews.com'
    comic_num_re = re.compile('%s/\\?p=([0-9]*)$' % url)

    @classmethod
    def get_archive_elements(cls):
        archive_url = urljoin_wrapper(cls.url, "?page_id=2")
        return reversed(get_soup_at_url(archive_url).find_all('a', href=cls.comic_num_re))

    @classmethod
    def get_url_from_archive_element(cls, link):
        return link['href']

    @classmethod
    def get_comic_info(cls, soup, link):
        comic_date_re = re.compile('.*/([0-9]*)-([0-9]*)-([0-9]*)-.*')
        url = cls.get_url_from_archive_element(link)
        num = int(cls.comic_num_re.match(url).groups()[0])
        img = soup.find('div', id='comic').find('img')
        assert all(i['alt'] == i['title'] for i in [img])
        title2 = img['title']
        img_url = img['src']
        year, month, day = [int(s) for s in comic_date_re.match(img_url).groups()]
        return {
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
    get_navi_link = get_link_rel_next

    @classmethod
    def get_first_comic_link(cls):
        return get_soup_at_url(cls.url).find('div', id='centered_nav').find_all('a')[0]

    @classmethod
    def get_comic_info(cls, soup, link):
        url = cls.get_url_from_link(link)
        date_re = re.compile('^%s/([0-9]*)/([0-9]*)/([0-9]*)/' % cls.url)
        year, month, day = [int(s) for s in date_re.match(url).groups()]
        imgs = soup.find('div', id='notes').find('div', class_='storycontent').find_all('img')
        texts = '  '.join(t for t in (i.get('title') for i in imgs) if t)
        title = soup.find('title').string
        return {
            'img': [convert_iri_to_plain_ascii_uri(i['src']) for i in imgs if i.get('src') is not None],
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


class AmazingSuperPowers(GenericNavigableComic):
    """Class to retrieve Amazing Super Powers comics."""
    name = 'asp'
    long_name = 'Amazing Super Powers'
    url = 'http://www.amazingsuperpowers.com'
    get_first_comic_link = get_a_navi_navifirst
    get_navi_link = get_a_navi_navinext

    @classmethod
    def get_comic_info(cls, soup, link):
        author = soup.find("span", class_="post-author").find("a").string
        date_str = soup.find('span', class_='post-date').string
        day = string_to_date(date_str, "%B %d, %Y")
        imgs = soup.find('div', id='comic').find_all('img')
        title = ' '.join(i['title'] for i in imgs)
        assert all(i['alt'] == i['title'] for i in imgs)
        return {
            'title': title,
            'author': author,
            'img': [img['src'] for img in imgs],
            'day': day.day,
            'month': day.month,
            'year': day.year
        }


class ToonHole(GenericListableComic):
    """Class to retrieve Toon Holes comics."""
    # Also on http://tapastic.com/series/TOONHOLE
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


class Channelate(GenericNavigableComic):
    """Class to retrieve Channelate comics."""
    name = 'channelate'
    long_name = 'Channelate'
    url = 'http://www.channelate.com'
    get_first_comic_link = get_div_navfirst_a
    get_navi_link = get_link_rel_next

    @classmethod
    def get_comic_info(cls, soup, link):
        author = soup.find("span", class_="post-author").find("a").string
        date_str = soup.find('span', class_='post-date').string
        day = string_to_date(date_str, '%Y/%m/%d')
        title = soup.find('meta', property='og:title')['content']
        post = soup.find('div', id='comic')
        imgs = post.find_all('img') if post else []
        assert all(i['alt'] == i['title'] for i in imgs)
        extra_url = None
        extra_div = soup.find('div', id='extrapanelbutton')
        if extra_div:
            extra_url = extra_div.find('a')['href']
            extra_soup = get_soup_at_url(extra_url)
            extra_imgs = extra_soup.find_all('img', class_='extrapanelimage')
            imgs.extend(extra_imgs)
        return {
            'url_extra': extra_url,
            'title': title,
            'author': author,
            'month': day.month,
            'year': day.year,
            'day': day.day,
            'img': [i['src'] for i in imgs],
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
    def get_navi_link(cls, last_soup, next_):
        link = last_soup.find('a', class_='next-comic' if next_ else 'previous-comic ')
        return None if link.get('href') is None else link

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


class DinosaurComics(GenericListableComic):
    """Class to retrieve Dinosaur Comics comics."""
    name = 'dinosaur'
    long_name = 'Dinosaur Comics'
    url = 'http://www.qwantz.com'
    comic_link_re = re.compile('^%s/index.php\\?comic=([0-9]*)$' % url)

    @classmethod
    def get_archive_elements(cls):
        archive_url = '%s/archive.php' % cls.url
        # first link is random -> skip it
        return reversed(get_soup_at_url(archive_url).find_all('a', href=cls.comic_link_re)[1:])

    @classmethod
    def get_url_from_archive_element(cls, link):
        return link['href']

    @classmethod
    def get_comic_info(cls, soup, link):
        url = cls.get_url_from_archive_element(link)
        num = int(cls.comic_link_re.match(url).groups()[0])
        date_str = link.string
        text = link.next_sibling.string
        day = string_to_date(remove_st_nd_rd_th_from_date(date_str), "%B %d, %Y")
        comic_img_re = re.compile('^%s/comics/' % cls.url)
        img = soup.find('img', src=comic_img_re)
        return {
            'month': day.month,
            'year': day.year,
            'day': day.day,
            'img': [img.get('src')],
            'title': img.get('title'),
            'text': text,
            'num': num,
        }


class ButterSafe(GenericListableComic):
    """Class to retrieve Butter Safe comics."""
    name = 'butter'
    long_name = 'ButterSafe'
    url = 'http://buttersafe.com'
    comic_link_re = re.compile('^%s/([0-9]*)/([0-9]*)/([0-9]*)/.*' % url)

    @classmethod
    def get_archive_elements(cls):
        archive_url = '%s/archive/' % cls.url
        return reversed(get_soup_at_url(archive_url).find_all('a', href=cls.comic_link_re))

    @classmethod
    def get_url_from_archive_element(cls, link):
        return link['href']

    @classmethod
    def get_comic_info(cls, soup, link):
        url = cls.get_url_from_archive_element(link)
        title = link.string
        year, month, day = [int(s) for s in cls.comic_link_re.match(url).groups()]
        img = soup.find('div', id='comic').find('img')
        assert img['alt'] == title
        return {
            'title': title,
            'day': day,
            'month': month,
            'year': year,
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


class PhDComics(GenericNavigableComic):
    """Class to retrieve PHD Comics."""
    name = 'phd'
    long_name = 'PhD Comics'
    url = 'http://phdcomics.com/comics/archive.php'

    @classmethod
    def get_url_from_link(cls, link):
        """Get url correponding to a link."""
        return urljoin_wrapper(cls.url, link['href'])

    @classmethod
    def get_first_comic_link(cls):
        return get_soup_at_url(cls.url).find('img', src='images/first_button.gif').parent

    @classmethod
    def get_navi_link(cls, last_soup, next_):
        img = last_soup.find('img', src='images/next_button.gif' if next_ else 'images/prev_button.gif')
        return None if img is None else img.parent

    @classmethod
    def get_url_from_archive_element(cls, link):
        return link['href']

    @classmethod
    def get_comic_info(cls, soup, link):
        date_str = soup.find('font', face='Arial,Helvetica,Geneva,Swiss,SunSans-Regular', color='white').string.strip()
        try:
            day = string_to_date(date_str, '%m/%d/%Y')
        except ValueError:
            print("Invalid date %s" % date_str)
            day = date.today()
        title = soup.find('meta', attrs={'name': 'twitter:title'})['content']
        return {
            'year': day.year,
            'month': day.month,
            'day': day.day,
            'img': [soup.find('img', id='comic')['src']],
            'title': title,
        }


class Octopuns(GenericNavigableComic):
    """Class to retrieve Octopuns comics."""
    # Also on http://octopuns.tumblr.com
    name = 'octopuns'
    long_name = 'Octopuns'
    url = 'http://www.octopuns.net'

    def get_first_comic_link(cls):
        return get_soup_at_url(cls.url).find('img', src=re.compile('.*/First.png')).parent

    @classmethod
    def get_navi_link(cls, last_soup, next_):
        link = last_soup.find('img', src=re.compile('.*/Next.png' if next_ else '.*/Back.png')).parent
        return None if link.get('href') is None else link

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


class Quarktees(GenericNavigableComic):
    """Class to retrieve the Quarktees comics."""
    name = 'quarktees'
    long_name = 'Quarktees'
    url = 'http://www.quarktees.com/blogs/news'

    @classmethod
    def get_first_comic_link(cls):
        return {'href': 'http://www.quarktees.com/blogs/news/12486621-coming-soon'}

    @classmethod
    def get_navi_link(cls, last_soup, next_):
        return last_soup.find('a', id='article-next' if next_ else 'article-prev')

    @classmethod
    def get_comic_info(cls, soup, link):
        title = soup.find('meta', property='og:title')['content']
        article = soup.find('div', class_='single-article')
        imgs = article.find_all('img')
        return {
            'title': title,
            'img': [urljoin_wrapper(cls.url, i['src']) for i in imgs],
        }

    @classmethod
    def get_url_from_link(cls, link):
        """Get url correponding to a link."""
        return urljoin_wrapper(cls.url, link['href'])


class OverCompensating(GenericNavigableComic):
    """Class to retrieve the Over Compensating comics."""
    name = 'compensating'
    long_name = 'Over Compensating'
    url = 'http://www.overcompensating.com'

    @classmethod
    def get_first_comic_link(cls):
        return get_soup_at_url(cls.url).find('a', href=re.compile('comic=1$'))

    @classmethod
    def get_navi_link(cls, last_soup, next_):
        return last_soup.find('a', title='next comic' if next_ else 'go back already')

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
    def get_navi_link(cls, last_soup, next_):
        div = last_soup.find("div", id="nx" if next_ else "pvs")
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
    def get_navi_link(cls, last_soup, next_):
        return last_soup.find('a', accesskey='n' if next_ else 'p')

    @classmethod
    def get_comic_info(cls, soup, link):
        title = soup.find('meta', attrs={'name': 'twitter:label1'})['content']
        desc = soup.find('meta', property='og:description')['content']
        imgs = soup.find_all('img', itemprop="image")
        return {
            'title': title,
            'description': desc,
            'img': [i['src'] for i in imgs],
        }


class SomethingOfThatIlk(GenericEmptyComic):  # Does not exist anymore
    """Class to retrieve the Something Of That Ilk comics."""
    name = 'somethingofthatilk'
    long_name = 'Something Of That Ilk'
    url = 'http://www.somethingofthatilk.com'


class InfiniteMonkeyBusiness(GenericNavigableComic):
    """Generic class to retrieve InfiniteMonkeyBusiness comics."""
    name = 'monkey'
    long_name = 'Infinite Monkey Business'
    url = 'http://infinitemonkeybusiness.net'
    get_navi_link = get_a_navi_comicnavnext_navinext

    @classmethod
    def get_first_comic_link(cls):
        return {'href': 'http://infinitemonkeybusiness.net/comic/pillory/'}

    @classmethod
    def get_comic_info(cls, soup, link):
        title = soup.find('meta', property='og:title')['content']
        imgs = soup.find('div', id='comic').find_all('img')
        return {
            'title': title,
            'img': [i['src'] for i in imgs],
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
    get_first_comic_link = get_a_navi_navifirst
    get_navi_link = get_link_rel_next

    @classmethod
    def get_comic_info(cls, soup, link):
        title = soup.find('h2', class_='post-title').string
        date_str = soup.find('span', class_='post-date').string
        day = string_to_date(date_str, "%B %d, %Y")
        imgs = soup.find('div', id='comic').find_all('img')
        return {
            'img': [i['src'] for i in imgs],
            'title': title,
            'day': day.day,
            'month': day.month,
            'year': day.year,
        }


class JustSayEh(GenericNavigableComic):
    """Class to retrieve Just Say Eh comics."""
    # Also on http//tapastic.com/series/Just-Say-Eh
    name = 'justsayeh'
    long_name = 'Just Say Eh'
    url = 'http://www.justsayeh.com'
    get_first_comic_link = get_a_navi_navifirst
    get_navi_link = get_a_navi_comicnavnext_navinext

    @classmethod
    def get_comic_info(cls, soup, link):
        title = soup.find('h2', class_='post-title').string
        imgs = soup.find("div", id="comic").find_all("img")
        assert all(i['alt'] == i['title'] for i in imgs)
        alt = imgs[0]['alt']
        return {
            'img': [i['src'] for i in imgs],
            'title': title,
            'alt': alt,
        }


class MouseBearComedy(GenericNavigableComic):
    """Class to retrieve Mouse Bear Comedy comics."""
    # Also on http://mousebearcomedy.tumblr.com
    name = 'mousebear'
    long_name = 'Mouse Bear Comedy'
    url = 'http://www.mousebearcomedy.com'
    get_first_comic_link = get_a_navi_navifirst
    get_navi_link = get_a_navi_comicnavnext_navinext

    @classmethod
    def get_comic_info(cls, soup, link):
        title = soup.find('h2', class_='post-title').string
        author = soup.find("span", class_="post-author").find("a").string
        date_str = soup.find("span", class_="post-date").string
        day = string_to_date(date_str, '%B %d, %Y')
        imgs = soup.find("div", id="comic").find_all("img")
        assert all(i['alt'] == i['title'] == title for i in imgs)
        return {
            'day': day.day,
            'month': day.month,
            'year': day.year,
            'img': [i['src'] for i in imgs],
            'title': title,
            'author': author,
        }


class BigFootJustice(GenericNavigableComic):
    """Class to retrieve Big Foot Justice comics."""
    # Also on http://tapastic.com/series/bigfoot-justice
    name = 'bigfoot'
    long_name = 'Big Foot Justice'
    url = 'http://bigfootjustice.com'
    get_first_comic_link = get_a_navi_navifirst
    get_navi_link = get_a_navi_comicnavnext_navinext

    @classmethod
    def get_comic_info(cls, soup, link):
        imgs = soup.find('div', id='comic').find_all('img')
        assert all(i['title'] == i['alt'] for i in imgs)
        title = ' '.join(i['title'] for i in imgs)
        return {
            'img': [i['src'] for i in imgs],
            'title': title,
        }


class SafelyEndangered(GenericNavigableComic):
    """Class to retrieve Safely Endangered comics."""
    # Also on http://tumblr.safelyendangered.com
    name = 'endangered'
    long_name = 'Safely Endangered'
    url = 'http://www.safelyendangered.com'
    get_navi_link = get_link_rel_next

    @classmethod
    def get_first_comic_link(cls):
        return {'href': 'http://www.safelyendangered.com/comic/ignored/'}

    @classmethod
    def get_comic_info(cls, soup, link):
        title = soup.find('h2', class_='post-title').string
        date_str = soup.find('span', class_='post-date').string
        day = string_to_date(date_str, '%B %d, %Y')
        imgs = soup.find('div', id='comic').find_all('img')
        alt = imgs[0]['alt']
        assert all(i['alt'] == i['title'] for i in imgs)
        return {
            'day': day.day,
            'month': day.month,
            'year': day.year,
            'img': [i['src'] for i in imgs],
            'title': title,
            'alt': alt,
        }


class PicturesInBoxes(GenericNavigableComic):
    """Class to retrieve Pictures In Boxes comics."""
    # Also on http://picturesinboxescomic.tumblr.com
    name = 'picturesinboxes'
    long_name = 'Pictures in Boxes'
    url = 'http://www.picturesinboxes.com'
    get_navi_link = get_a_navi_navinext

    @classmethod
    def get_first_comic_link(cls):
        return {'href': 'http://www.picturesinboxes.com/2013/10/26/tetris/'}

    @classmethod
    def get_comic_info(cls, soup, link):
        title = soup.find('h2', class_='post-title').string
        author = soup.find("span", class_="post-author").find("a").string
        date_str = soup.find('span', class_='post-date').string
        day = string_to_date(date_str, '%B %d, %Y')
        imgs = soup.find('div', class_='comicpane').find_all('img')
        assert imgs
        assert all(i['title'] == i['alt'] == title for i in imgs)
        return {
            'day': day.day,
            'month': day.month,
            'year': day.year,
            'img': [i['src'] for i in imgs],
            'title': title,
            'author': author,
        }


class Penmen(GenericEmptyComic):
    """Class to retrieve Penmen comics."""
    name = 'penmen'
    long_name = 'Penmen'
    url = 'http://penmen.com'


class TheDoghouseDiaries(GenericNavigableComic):
    """Class to retrieve The Dog House Diaries comics."""
    name = 'doghouse'
    long_name = 'The Dog House Diaries'
    url = 'http://thedoghousediaries.com'

    @classmethod
    def get_first_comic_link(cls):
        return get_soup_at_url(cls.url).find('a', id='firstlink')

    @classmethod
    def get_navi_link(cls, last_soup, next_):
        return last_soup.find('a', id='nextlink' if next_ else 'previouslink')

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


class InvisibleBread(GenericListableComic):
    """Class to retrieve Invisible Bread comics."""
    name = 'invisiblebread'
    long_name = 'Invisible Bread'
    url = 'http://invisiblebread.com'

    @classmethod
    def get_archive_elements(cls):
        archive_url = urljoin_wrapper(cls.url, '/archives/')
        return reversed(get_soup_at_url(archive_url).find_all('td', class_='archive-title'))

    @classmethod
    def get_url_from_archive_element(cls, td):
        return td.find('a')['href']

    @classmethod
    def get_comic_info(cls, soup, td):
        url = cls.get_url_from_archive_element(td)
        title = td.find('a').string
        month_and_day = td.previous_sibling.string
        link_re = re.compile('^%s/([0-9]+)/' % cls.url)
        year = link_re.match(url).groups()[0]
        date_str = month_and_day + ' ' + year
        day = string_to_date(date_str, '%b %d %Y')
        imgs = [soup.find('div', id='comic').find('img')]
        assert len(imgs) == 1
        assert all(i['title'] == i['alt'] == title for i in imgs)
        return {
            'month': day.month,
            'year': day.year,
            'day': day.day,
            'img': [urljoin_wrapper(cls.url, i['src']) for i in imgs],
            'title': title,
        }


class DiscoBleach(GenericEmptyComic):  # Does not work anymore
    """Class to retrieve Disco Bleach Comics."""
    name = 'discobleach'
    long_name = 'Disco Bleach'
    url = 'http://discobleach.com'


class TubeyToons(GenericEmptyComic):  # Does not work anymore
    """Class to retrieve TubeyToons comics."""
    # Also on http://tapastic.com/series/Tubey-Toons
    # Also on http://tubeytoons.tumblr.com
    name = 'tubeytoons'
    long_name = 'Tubey Toons'
    url = 'http://tubeytoons.com'


class CompletelySeriousComics(GenericNavigableComic):
    """Class to retrieve Completely Serious comics."""
    name = 'completelyserious'
    long_name = 'Completely Serious Comics'
    url = 'http://completelyseriouscomics.com'
    get_first_comic_link = get_a_navi_navifirst
    get_navi_link = get_a_navi_navinext

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
    # Also on http://pdlcomics.tumblr.com
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
    def get_navi_link(cls, last_soup, next_):
        return last_soup.find('a', title='Next' if next_ else 'Previous')

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
    get_first_comic_link = get_div_navfirst_a
    get_navi_link = get_link_rel_next

    @classmethod
    def get_comic_info(cls, soup, link):
        date_str = soup.find('span', class_='post-date').string
        day = string_to_date(remove_st_nd_rd_th_from_date(date_str), "%B %d, %Y")
        author = soup.find('span', class_='post-author').string
        div = soup.find('div', id='comic')
        imgs = div.find_all('img') if div else []
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
    def get_navi_link(cls, last_soup, next_):
        return last_soup.find('img', attrs={'name': 'rightArrow' if next_ else 'leftArrow'}).parent

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
    get_first_comic_link = get_a_navi_navifirst
    get_navi_link = get_link_rel_next

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
    get_navi_link = get_a_rel_next

    @classmethod
    def get_first_comic_link(cls):
        return {'href': 'http://fatawesome.com/shortbus/'}

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
    # Also on http://tapastic.com/series/anything
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


class LonnieMillsap(GenericNavigableComic):
    """Class to retrieve Lonnie Millsap's comics."""
    name = 'millsap'
    long_name = 'Lonnie Millsap'
    url = 'http://www.lonniemillsap.com'
    get_navi_link = get_link_rel_next

    @classmethod
    def get_first_comic_link(cls):
        return {'href': 'http://www.lonniemillsap.com/?p=42'}

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
    # Also on http://tapastic.com/series/Thors-Thundershac
    name = 'thor'
    long_name = 'Thor\'s Thundershack'
    url = 'http://www.thorsthundershack.com'
    get_navi_link = get_a_rel_next

    @classmethod
    def get_first_comic_link(cls):
        return get_soup_at_url(cls.url).find('a', class_='first navlink')

    @classmethod
    def get_url_from_link(cls, link):
        return urljoin_wrapper(cls.url, link['href'])

    @classmethod
    def get_comic_info(cls, soup, link):
        title = soup.find('meta', attrs={'name': 'description'})["content"]
        description = soup.find('div', itemprop='articleBody').text
        author = soup.find('span', itemprop='author copyrightHolder').string
        imgs = soup.find_all('img', itemprop='image')
        assert all(i['title'] == i['alt'] for i in imgs)
        alt = imgs[0]['alt'] if imgs else ""
        date_str = soup.find('time', itemprop='datePublished')["datetime"]
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


class GerbilWithAJetpack(GenericNavigableComic):
    """Class to retrieve GerbilWithAJetpack comics."""
    name = 'gerbil'
    long_name = 'Gerbil With A Jetpack'
    url = 'http://gerbilwithajetpack.com'
    get_first_comic_link = get_a_navi_navifirst
    get_navi_link = get_a_rel_next

    @classmethod
    def get_comic_info(cls, soup, link):
        title = soup.find('h2', class_='post-title').string
        author = soup.find("span", class_="post-author").find("a").string
        date_str = soup.find("span", class_="post-date").string
        day = string_to_date(date_str, "%B %d, %Y")
        imgs = soup.find("div", id="comic").find_all("img")
        alt = imgs[0]['alt']
        assert all(i['alt'] == i['title'] == alt for i in imgs)
        return {
            'img': [i['src'] for i in imgs],
            'title': title,
            'alt': alt,
            'author': author,
            'day': day.day,
            'month': day.month,
            'year': day.year
        }


class EveryDayBlues(GenericNavigableComic):
    """Class to retrieve EveryDayBlues Comics."""
    name = "blues"
    long_name = "Every Day Blues"
    url = "http://everydayblues.net"
    get_first_comic_link = get_a_navi_navifirst
    get_navi_link = get_link_rel_next

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
    get_first_comic_link = get_a_navi_navifirst
    get_navi_link = get_link_rel_next

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
    get_first_comic_link = get_a_navi_navifirst
    get_navi_link = get_link_rel_next

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
    get_first_comic_link = get_a_comicnavbase_comicnavfirst
    get_navi_link = get_link_rel_next

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
    get_first_comic_link = get_a_navi_navifirst
    get_navi_link = get_link_rel_next

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
    get_first_comic_link = get_a_navi_navifirst
    get_navi_link = get_link_rel_next

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


class PlanC(GenericNavigableComic):
    """Class to retrieve Plan C comics."""
    name = 'planc'
    long_name = 'Plan C'
    url = 'http://www.plancomic.com'
    get_first_comic_link = get_a_comicnavbase_comicnavfirst
    get_navi_link = get_a_comicnavbase_comicnavnext

    @classmethod
    def get_comic_info(cls, soup, link):
        title = soup.find('h2', class_='post-title').string
        date_str = soup.find("span", class_="post-date").string
        day = string_to_date(date_str, "%B %d, %Y")
        imgs = soup.find('div', id='comic').find_all('img')
        return {
            'title': title,
            'img': [i['src'] for i in imgs],
            'month': day.month,
            'year': day.year,
            'day': day.day,
        }


class BuniComic(GenericNavigableComic):
    """Class to retrieve Buni Comics."""
    name = 'buni'
    long_name = 'BuniComics'
    url = 'http://www.bunicomic.com'
    get_first_comic_link = get_a_comicnavbase_comicnavfirst
    get_navi_link = get_link_rel_next

    @classmethod
    def get_comic_info(cls, soup, link):
        imgs = soup.find('div', id='comic').find_all('img')
        assert all(i['alt'] == i['title'] for i in imgs)
        assert len(imgs) == 1
        return {
            'img': [i['src'] for i in imgs],
            'title': imgs[0]['title'],
        }


class GenericCommitStrip(GenericNavigableComic):
    """Generic class to retrieve Commit Strips in different languages."""
    get_navi_link = get_a_rel_next

    @classmethod
    def get_comic_info(cls, soup, link):
        desc = soup.find('meta', property='og:description')['content']
        title = soup.find('meta', property='og:title')['content']
        imgs = soup.find('div', class_='entry-content').find_all('img')
        title2 = ' '.join(i.get('title', '') for i in imgs)
        return {
            'title': title,
            'title2': title2,
            'description': desc,
            'img': [urljoin_wrapper(cls.url, convert_iri_to_plain_ascii_uri(i['src'])) for i in imgs],
        }


class CommitStripFr(GenericCommitStrip):
    """Class to retrieve Commit Strips in French."""
    name = 'commit_fr'
    long_name = 'Commit Strip (Fr)'
    url = 'http://www.commitstrip.com/fr'

    @classmethod
    def get_first_comic_link(cls):
        return {'href': 'http://www.commitstrip.com/fr/2012/02/22/interview/'}


class CommitStripEn(GenericCommitStrip):
    """Class to retrieve Commit Strips in English."""
    name = 'commit_en'
    long_name = 'Commit Strip (En)'
    url = 'http://www.commitstrip.com/en'

    @classmethod
    def get_first_comic_link(cls):
        return {'href': 'http://www.commitstrip.com/en/2012/02/22/interview/'}


class GenericBoumerie(GenericNavigableComic):
    """Generic class to retrieve Boumeries comics in different languages."""
    get_first_comic_link = get_a_navi_navifirst
    get_navi_link = get_link_rel_next
    date_format = NotImplemented
    lang = NotImplemented

    @classmethod
    def get_comic_info(cls, soup, link):
        title = soup.find('h2', class_='post-title').string
        short_url = soup.find('link', rel='shortlink')['href']
        author = soup.find("span", class_="post-author").find("a").string
        date_str = soup.find('span', class_='post-date').string
        day = string_to_date(date_str, cls.date_format, cls.lang)
        imgs = soup.find('div', id='comic').find_all('img')
        assert all(i['alt'] == i['title'] for i in imgs)
        return {
            'short_url': short_url,
            'img': [i['src'] for i in imgs],
            'title': title,
            'author': author,
            'month': day.month,
            'year': day.year,
            'day': day.day,
        }


class BoumerieEn(GenericBoumerie):
    """Class to retrieve Boumeries comics in English."""
    name = 'boumeries_en'
    long_name = 'Boumeries (En)'
    url = 'http://comics.boumerie.com'
    date_format = "%B %d, %Y"
    lang = 'en_GB.UTF-8'


class BoumerieFr(GenericBoumerie):
    """Class to retrieve Boumeries comics in French."""
    name = 'boumeries_fr'
    long_name = 'Boumeries (Fr)'
    url = 'http://bd.boumerie.com'
    date_format = "%A, %d %B %Y"
    lang = "fr_FR.utf8"


class UnearthedComics(GenericNavigableComic):
    """Class to retrieve Unearthed comics."""
    # Also on http://tapastic.com/series/UnearthedComics
    # Also on http://unearthedcomics.tumblr.com
    name = 'unearthed'
    long_name = 'Unearthed Comics'
    url = 'http://unearthedcomics.com'
    get_navi_link = get_link_rel_next

    @classmethod
    def get_first_comic_link(cls):
        return {'href': 'http://unearthedcomics.com/comics/world-with-turn-signals/'}

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


class Optipess(GenericNavigableComic):
    """Class to retrieve Optipess comics."""
    name = 'optipess'
    long_name = 'Optipess'
    url = 'http://www.optipess.com'
    get_first_comic_link = get_a_navi_navifirst
    get_navi_link = get_link_rel_next

    @classmethod
    def get_comic_info(cls, soup, link):
        title = soup.find('h2', class_='post-title').string
        author = soup.find("span", class_="post-author").find("a").string
        comic = soup.find('div', id='comic')
        imgs = comic.find_all('img') if comic else []
        alt = imgs[0]['title'] if imgs else ""
        assert all(i['alt'] == i['title'] == alt for i in imgs)
        date_str = soup.find('span', class_='post-date').string
        day = string_to_date(date_str, "%B %d, %Y")
        return {
            'title': title,
            'alt': alt,
            'author': author,
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
    get_first_comic_link = get_a_navi_navifirst
    get_navi_link = get_link_rel_next

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


class AHamADay(GenericNavigableComic):
    """Class to retrieve class A Ham A Day comics."""
    name = 'ham'
    long_name = 'A Ham A Day'
    url = 'http://www.ahammaday.com'

    @classmethod
    def get_first_comic_link(cls):
        return {'href': 'http://www.ahammaday.com/today/3/6/french'}

    @classmethod
    def get_navi_link(cls, last_soup, next_):
        # prev is next / next is prev
        return last_soup.find('a', class_='prev-item' if next_ else 'next-item')

    @classmethod
    def get_url_from_link(cls, link):
        return urljoin_wrapper(cls.url, link['href'])

    @classmethod
    def get_comic_info(cls, soup, link):
        date_str = soup.find('time', itemprop='datePublished')["datetime"]
        day = string_to_date(date_str, "%Y-%m-%d")
        author = soup.find('a', rel='author').string
        title = soup.find('meta', property='og:title')['content']
        imgs = soup.find_all('meta', itemprop='image')
        return {
            'img': [i['content'] for i in imgs],
            'title': title,
            'author': author,
            'day': day.day,
            'month': day.month,
            'year': day.year,
        }


class EverythingsStupid(GenericNavigableComic):
    """Class to retrieve Everything's stupid Comics."""
    # Also on http://tapastic.com/series/EverythingsStupid
    # Also on http://www.webtoons.com/en/challenge/everythings-stupid/list?title_no=14591
    name = 'stupid'
    long_name = "Everything's Stupid"
    url = 'http://everythingsstupid.net'
    get_navi_link = get_link_rel_next

    @classmethod
    def get_first_comic_link(cls):
        return get_soup_at_url(cls.url).find('a', class_='webcomic-link webcomic1-link first-webcomic-link first-webcomic1-link')

    @classmethod
    def get_comic_info(cls, soup, link):
        title = soup.find('meta', property='og:title')['content']
        imgs = soup.find('div', class_='webcomic-image').find_all('img')
        date_str = soup.find('meta', property='article:published_time')['content'][:10]
        day = string_to_date(date_str, "%Y-%m-%d")
        return {
            'title': title,
            'day': day.day,
            'month': day.month,
            'year': day.year,
            'img': [i['src'] for i in imgs],
        }


class ElectricBunnyComic(GenericNavigableComic):
    """Class to retrieve Electric Bunny Comics."""
    name = 'bunny'
    long_name = 'Electric Bunny Comic'
    url = 'http://www.electricbunnycomics.com/View/Comic/153/Welcome+to+Hell'

    @classmethod
    def get_url_from_link(cls, link):
        return urljoin_wrapper(cls.url, link['href'])

    @classmethod
    def get_first_comic_link(cls):
        return get_soup_at_url(cls.url).find('img', alt='First').parent

    @classmethod
    def get_navi_link(cls, last_soup, next_):
        img = last_soup.find('img', alt='Next' if next_ else 'Prev')
        return img.parent if img else None

    @classmethod
    def get_comic_info(cls, soup, link):
        title = soup.find('meta', property='og:title')['content']
        imgs = soup.find_all('meta', property='og:image')
        return {
            'title': title,
            'img': [i['content'] for i in imgs],
        }


class SheldonComics(GenericNavigableComic):
    """Class to retrieve Sheldon comics."""
    name = 'sheldon'
    long_name = 'Sheldon Comics'
    url = 'http://www.sheldoncomics.com'

    @classmethod
    def get_first_comic_link(cls):
        return get_soup_at_url(cls.url).find("a", id="nav-first")

    @classmethod
    def get_navi_link(cls, last_soup, next_):
        return last_soup.find("a", id="nav-next" if next_ else "nav-prev")

    @classmethod
    def get_comic_info(cls, soup, link):
        imgs = soup.find("div", id="comic-foot").find_all("img")
        assert all(i['alt'] == i['title'] for i in imgs)
        assert len(imgs) == 1
        title = imgs[0]['title']
        return {
            'title': title,
            'img': [i['src'] for i in imgs],
        }


class CubeDrone(GenericNavigableComic):
    """Class to retrieve Cube Drone comics."""
    name = 'cubedrone'
    long_name = 'Cube Drone'
    url = 'http://cube-drone.com/comics'

    @classmethod
    def get_url_from_link(cls, link):
        return urljoin_wrapper(cls.url, link['href'])

    @classmethod
    def get_first_comic_link(cls):
        return get_soup_at_url(cls.url).find('span', class_='glyphicon glyphicon-backward').parent

    @classmethod
    def get_navi_link(cls, last_soup, next_):
        class_ = 'glyphicon glyphicon-chevron-' + ('right' if next_ else 'left')
        return last_soup.find('span', class_=class_).parent

    @classmethod
    def get_comic_info(cls, soup, link):
        title = soup.find('meta', attrs={'name': 'twitter:title'})['content']
        url2 = soup.find('meta', attrs={'name': 'twitter:url'})['content']
        # date_str = soup.find('h2', class_='comic_title').find('small').string
        # day = string_to_date(date_str, "%B %d, %Y, %I:%M %p")
        imgs = soup.find_all('img', class_='comic img-responsive')
        title2 = imgs[0]['title']
        alt = imgs[0]['alt']
        return {
                'url2': url2,
                'title': title,
                'title2': title2,
                'alt': alt,
                'img': [i['src'] for i in imgs],
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
        return [None if i.get('href') is None else i for i in nav1]

    @classmethod
    def get_first_comic_link(cls):
        return cls.get_nav(get_soup_at_url(cls.url))[0]

    @classmethod
    def get_navi_link(cls, last_soup, next_):
        return cls.get_nav(last_soup)[3 if next_ else 1]

    @classmethod
    def get_comic_info(cls, soup, link):
        title = link['title']
        imgs = soup.find_all('img', id='comicimg')
        return {
            'title': title,
            'img': [i['src'] for i in imgs],
        }


class GeekAndPoke(GenericNavigableComic):
    """Class to retrieve Geek And Poke comics."""
    name = 'geek'
    long_name = 'Geek And Poke'
    url = 'http://geek-and-poke.com'

    @classmethod
    def get_url_from_link(cls, link):
        return urljoin_wrapper(cls.url, link['href'])

    @classmethod
    def get_first_comic_link(cls):
        return {'href': 'http://geek-and-poke.com/geekandpoke/2006/8/27/a-new-place-for-a-not-so-old-blog.html'}

    @classmethod
    def get_navi_link(cls, last_soup, next_):
        return last_soup.find('a', class_='prev-item' if next_ else 'next-item')

    @classmethod
    def get_comic_info(cls, soup, link):
        title = soup.find('meta', property='og:title')['content']
        desc = soup.find('meta', property='og:description')['content']
        date_str = soup.find('time', class_='published')['datetime']
        day = string_to_date(date_str, "%Y-%m-%d")
        author = soup.find('a', rel='author').string
        div_content = (soup.find('div', class_="body entry-content") or
                       soup.find('div', class_="special-content"))
        imgs = div_content.find_all('img')
        imgs = [i for i in imgs if i.get('src') is not None]
        assert all('title' not in i or i['alt'] == i['title'] for i in imgs)
        alt = imgs[0].get('alt', "") if imgs else []
        return {
            'title': title,
            'alt': alt,
            'description': desc,
            'author': author,
            'day': day.day,
            'month': day.month,
            'year': day.year,
            'img': [urljoin_wrapper(cls.url, i['src']) for i in imgs],
        }


class GenericTumblrV1(GenericComic):
    """Generic class to retrieve comics from Tumblr using the V1 API."""

    @classmethod
    def get_next_comic(cls, last_comic):
        for p in cls.get_posts(last_comic):
            comic = cls.get_comic_info(p)
            if comic is not None:
                yield comic

    @classmethod
    def get_url_from_post(cls, post):
        return post['url']

    @classmethod
    def get_api_url(cls):
        return urljoin_wrapper(cls.url, '/api/read/')

    @classmethod
    def get_comic_info(cls, post):
        """Get information about a particular comics."""
        # print(post)
        type_ = post['type']
        if type_ != 'photo':
            # print("Type is %s" % type_)
            return None
        tumblr_id = int(post['id'])
        api_url = cls.get_api_url() + '?id=%d' % (tumblr_id)
        day = datetime.datetime.fromtimestamp(int(post['unix-timestamp'])).date()
        caption = post.find('photo-caption')
        title = caption.string if caption else ""
        tags = ' '.join(t.string for t in post.find_all('tag'))
        # Photos may appear in 'photo' tags and/or straight in the post
        photo_tags = post.find_all('photo')
        if not photo_tags:
            photo_tags = [post]
        # Images are in multiple resolutions - taking the first one
        imgs = [photo.find('photo-url') for photo in photo_tags]
        return {
            'url': cls.get_url_from_post(post),
            'url2': post['url-with-slug'],
            'day': day.day,
            'month': day.month,
            'year': day.year,
            'title': title,
            'tags': tags,
            'img': [i.string for i in imgs],
            'tumblr-id': tumblr_id,
            'api_url': api_url,  # for debug purposes
        }

    @classmethod
    def get_posts(cls, last_comic, nb_post_per_call=10):
        """Get posts using API. nb_post_per_call is max 50.

        Posts are retrieved from newer to older as per the tumblr v1 api
        but are returned in chronological order."""
        waiting_for_url = last_comic['url'] if last_comic else None
        posts_acc = []
        api_url = cls.get_api_url()
        posts = get_soup_at_url(api_url).find('posts')
        start, total = int(posts['start']), int(posts['total'])
        assert start == 0
        for starting_num in range(0, total, nb_post_per_call):
            api_url2 = api_url + '?start=%d&num=%d' % (starting_num, nb_post_per_call)
            # print(api_url2)
            posts2 = get_soup_at_url(api_url2).find('posts')
            start2, total2 = int(posts2['start']), int(posts2['total'])
            assert starting_num == start2, "%d != %d" % (starting_num, start2)
            # This may happen and should be handled in the future
            assert total == total2, "%d != %d" % (total, total2)
            for p in posts2.find_all('post'):
                if waiting_for_url and waiting_for_url == cls.get_url_from_post(p):
                    return reversed(posts_acc)
                posts_acc.append(p)
        if waiting_for_url is None:
            return reversed(posts_acc)
        print("Did not find %s : there might be a problem" % waiting_for_url)
        return []


class IrwinCardozo(GenericTumblrV1):
    """Class to retrieve Irwin Cardozo Comics."""
    name = 'irwinc'
    long_name = 'Irwin Cardozo'
    url = 'http://irwincardozocomics.tumblr.com'


class AccordingToDevin(GenericTumblrV1):
    """Class to retrieve According To Devin comics."""
    name = 'devin'
    long_name = 'According To Devin'
    url = 'http://accordingtodevin.tumblr.com'


class ItsTheTieTumblr(GenericTumblrV1):
    """Class to retrieve It's the tie comics."""
    # Also on http://itsthetie.com
    name = 'tie-tumblr'
    long_name = "It's the tie (from Tumblr)"
    url = "http://itsthetie.tumblr.com"


class OctopunsTumblr(GenericTumblrV1):
    """Class to retrieve Octopuns comics."""
    # Also on http://www.octopuns.net
    name = 'octopuns-tumblr'
    long_name = 'Octopuns (from Tumblr)'
    url = 'http://octopuns.tumblr.com'


class PicturesInBoxesTumblr(GenericTumblrV1):
    """Class to retrieve Pictures In Boxes comics."""
    # Also on http://www.picturesinboxes.com
    name = 'picturesinboxes-tumblr'
    long_name = 'Pictures in Boxes (from Tumblr)'
    url = 'http://picturesinboxescomic.tumblr.com'


class TubeyToonsTumblr(GenericTumblrV1):
    """Class to retrieve TubeyToons comics."""
    # Also on http://tapastic.com/series/Tubey-Toons
    # Also on http://tubeytoons.com
    name = 'tubeytoons-tumblr'
    long_name = 'Tubey Toons (from Tumblr)'
    url = 'http://tubeytoons.tumblr.com'


class UnearthedComicsTumblr(GenericTumblrV1):
    """Class to retrieve Unearthed comics."""
    # Also on http://tapastic.com/series/UnearthedComics
    # Also on http://unearthedcomics.com
    name = 'unearthed-tumblr'
    long_name = 'Unearthed Comics (from Tumblr)'
    url = 'http://unearthedcomics.tumblr.com'


class PieComic(GenericTumblrV1):
    """Class to retrieve Pie Comic comics."""
    name = 'pie'
    long_name = 'Pie Comic'
    url = "http://piecomic.tumblr.com"


class MrEthanDiamond(GenericTumblrV1):
    """Class to retrieve Mr Ethan Diamond comics."""
    name = 'diamond'
    long_name = 'Mr Ethan Diamond'
    url = 'http://mrethandiamond.tumblr.com'


class Flocci(GenericTumblrV1):
    """Class to retrieve floccinaucinihilipilification comics."""
    name = 'flocci'
    long_name = 'floccinaucinihilipilification'
    url = "http://floccinaucinihilipilificationa.tumblr.com"


class UpAndOut(GenericTumblrV1):
    """Class to retrieve Up & Out comics."""
    # Also on http://tapastic.com/series/UP-and-OUT
    name = 'upandout'
    long_name = 'Up And Out (from Tumblr)'
    url = 'http://upandoutcomic.tumblr.com'


class Pundemonium(GenericTumblrV1):
    """Class to retrieve Pundemonium comics."""
    name = 'pundemonium'
    long_name = 'Pundemonium'
    url = 'http://monstika.tumblr.com'


class PoorlyDrawnLinesTumblr(GenericTumblrV1):
    """Class to retrieve Poorly Drawn Lines comics."""
    # Also on http://poorlydrawnlines.com
    name = 'poorlydrawn-tumblr'
    long_name = 'Poorly Drawn Lines (from Tumblr)'
    url = 'http://pdlcomics.tumblr.com'


class PearShapedComics(GenericTumblrV1):
    """Class to retrieve Pear Shaped Comics."""
    name = 'pearshaped'
    long_name = 'Pear-Shaped Comics'
    url = 'http://pearshapedcomics.com'


class PondScumComics(GenericTumblrV1):
    """Class to retrieve Pond Scum Comics."""
    name = 'pond'
    long_name = 'Pond Scum'
    url = 'http://pondscumcomic.tumblr.com'


class MercworksTumblr(GenericTumblrV1):
    """Class to retrieve Mercworks comics."""
    # Also on http://mercworks.net
    name = 'mercworks-tumblr'
    long_name = 'Mercworks (from Tumblr)'
    url = 'http://mercworks.tumblr.com'


class OwlTurdTumblr(GenericTumblrV1):
    """Class to retrieve Owl Turd comics."""
    # Also on http://tapastic.com/series/Owl-Turd-Comix
    name = 'owlturd-tumblr'
    long_name = 'Owl Turd (from Tumblr)'
    url = 'http://owlturd.com'


class VectorBelly(GenericTumblrV1):
    """Class to retrieve Vector Belly comics."""
    # Also on http://vectorbelly.com
    name = 'vector'
    long_name = 'Vector Belly'
    url = 'http://vectorbelly.tumblr.com'


class GoneIntoRapture(GenericTumblrV1):
    """Class to retrieve Gone Into Rapture comics."""
    # Also on http://goneintorapture.tumblr.com
    # Also on http://tapastic.com/series/Goneintorapture
    name = 'rapture'
    long_name = 'Gone Into Rapture'
    url = 'http://www.goneintorapture.com'


class TheOatmealTumblr(GenericTumblrV1):
    """Class to retrieve The Oatmeal comics."""
    # Also on http://theoatmeal.com
    name = 'oatmeal-tumblr'
    long_name = 'The Oatmeal (from Tumblr)'
    url = 'http://oatmeal.tumblr.com'


class HeckIfIKnowComicsTumblr(GenericTumblrV1):
    """Class to retrieve Heck If I Know Comics."""
    # Also on http://tapastic.com/series/Regular
    name = 'heck-tumblr'
    long_name = 'Heck if I Know comics (from Tumblr)'
    url = 'http://heckifiknowcomics.com'


class MyJetPack(GenericTumblrV1):
    """Class to retrieve My Jet Pack comics."""
    name = 'jetpack'
    long_name = 'My Jet Pack'
    url = 'http://myjetpack.tumblr.com'


class CheerUpEmoKidTumblr(GenericTumblrV1):
    """Class to retrieve CheerUpEmoKid comics."""
    # Also on http://www.cheerupemokid.com
    # Also on http://tapastic.com/series/CUEK
    name = 'cuek-tumblr'
    long_name = 'Cheer Up Emo Kid (from Tumblr)'
    url = 'http://enzocomics.tumblr.com'


class ForLackOfABetterComic(GenericTumblrV1):
    """Class to retrieve For Lack Of A Better Comics."""
    # Also on http://forlackofabettercomic.com
    name = 'lack'
    long_name = 'For Lack Of A Better Comic'
    url = 'http://forlackofabettercomic.tumblr.com'


class ZenPencilsTumblr(GenericTumblrV1):
    """Class to retrieve ZenPencils comics."""
    # Also on http://zenpencils.com
    name = 'zenpencils-tumblr'
    long_name = 'Zen Pencils (from Tumblr)'
    url = 'http://zenpencils.tumblr.com'


class ThreeWordPhraseTumblr(GenericTumblrV1):
    """Class to retrieve Three Word Phrase comics."""
    # Also on http://threewordphrase.com
    name = 'threeword-tumblr'
    long_name = 'Three Word Phrase (from Tumblr)'
    url = 'http://www.threewordphrase.tumblr.com'


class TimeTrabbleTumblr(GenericTumblrV1):
    """Class to retrieve Time Trabble comics."""
    # Also on http://timetrabble.com
    name = 'timetrabble-tumblr'
    long_name = 'Time Trabble (from Tumblr)'
    url = 'http://timetrabble.tumblr.com'


class SafelyEndangeredTumblr(GenericTumblrV1):
    """Class to retrieve Safely Endangered comics."""
    # Also on http://www.safelyendangered.com
    name = 'endangered-tumblr'
    long_name = 'Safely Endangered (from Tumblr)'
    url = 'http://tumblr.safelyendangered.com'


class MouseBearComedyTumblr(GenericTumblrV1):
    """Class to retrieve Mouse Bear Comedy comics."""
    # Also on http://www.mousebearcomedy.com
    name = 'mousebear-tumblr'
    long_name = 'Mouse Bear Comedy (from Tumblr)'
    url = 'http://mousebearcomedy.tumblr.com'


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
    """Class to retrieve Horovitz new comics."""
    name = 'horovitznew'
    long_name = 'Horovitz New'
    link_re = re.compile('^/comics/new/([0-9]+)$')


class HorovitzClassic(HorovitzComics):
    """Class to retrieve Horovitz classic comics."""
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
    def get_navi_link(cls, last_soup, next_):
        return last_soup.find('a', class_='next' if next_ else 'prev', href=cls.url_date_re)

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


class RallGoComic(GenericGoComic):
    """Class to retrieve Ted Rall comics."""
    # Also on : http://rall.com/comic
    name = 'rall-goc'
    long_name = "Ted Rall (from GoComics)"
    url = "http://www.gocomics.com/tedrall"


class TapasticComic(GenericListableComic):
    """Generic class to handle the logic common to comics from tapastic.com."""

    @classmethod
    def get_comic_info(cls, soup, archive_element):
        timestamp = int(archive_element['publishDate']) / 1000.0
        day = datetime.datetime.fromtimestamp(timestamp).date()
        imgs = soup.find_all('img', class_='art-image')
        if not imgs:
            print("Comic %s is being uploaded, retry later" % cls.get_url_from_archive_element(archive_element))
            return None
        assert len(imgs) > 0
        return {
            'day': day.day,
            'year': day.year,
            'month': day.month,
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
    # Also on http://tubeytoons.tumblr.com/
    name = 'tubeytoons-tapa'
    long_name = 'Tubey Toons (from Tapastic)'
    url = 'http://tapastic.com/series/Tubey-Toons'


class AnythingComicTapastic(TapasticComic):
    """Class to retrieve Anything Comics."""
    # Also on http://www.anythingcomic.com
    name = 'anythingcomic-tapa'
    long_name = 'Anything Comic (from Tapastic)'
    url = 'http://tapastic.com/series/anything'


class UnearthedComicsTapastic(TapasticComic):
    """Class to retrieve Unearthed comics."""
    # Also on http://unearthedcomics.com
    # Also on http://unearthedcomics.tumblr.com
    name = 'unearthed-tapa'
    long_name = 'Unearthed Comics (from Tapastic)'
    url = 'http://tapastic.com/series/UnearthedComics'


class EverythingsStupidTapastic(TapasticComic):
    """Class to retrieve Everything's stupid Comics."""
    # Also on http://www.webtoons.com/en/challenge/everythings-stupid/list?title_no=14591
    # Also on http://everythingsstupid.net
    name = 'stupid-tapa'
    long_name = "Everything's Stupid (from Tapastic)"
    url = 'http://tapastic.com/series/EverythingsStupid'


class JustSayEhTapastic(TapasticComic):
    """Class to retrieve Just Say Eh comics."""
    # Also on http://www.justsayeh.com
    name = 'justsayeh-tapa'
    long_name = 'Just Say Eh (from Tapastic)'
    url = 'http://tapastic.com/series/Just-Say-Eh'


class ThorsThundershackTapastic(TapasticComic):
    """Class to retrieve Thor's Thundershack comics."""
    # Also on http://www.thorsthundershack.com
    name = 'thor-tapa'
    long_name = 'Thor\'s Thundershack (from Tapastic)'
    url = 'http://tapastic.com/series/Thors-Thundershac'


class OwlTurdTapastic(TapasticComic):
    """Class to retrieve Owl Turd comics."""
    # Also on http://owlturd.com
    name = 'owlturd-tapa'
    long_name = 'Owl Turd (from Tapastic)'
    url = 'http://tapastic.com/series/Owl-Turd-Comix'


class GoneIntoRaptureTapastic(TapasticComic):
    """Class to retrieve Gone Into Rapture comics."""
    # Also on http://goneintorapture.tumblr.com
    # Also on http://www.goneintorapture.com
    name = 'rapture-tapa'
    long_name = 'Gone Into Rapture (from Tapastic)'
    url = 'http://tapastic.com/series/Goneintorapture'


class HeckIfIKnowComicsTapa(TapasticComic):
    """Class to retrieve Heck If I Know Comics."""
    # Also on http://heckifiknowcomics.com
    name = 'heck-tapa'
    long_name = 'Heck if I Know comics (from Tapastic)'
    url = 'http://tapastic.com/series/Regular'


class CheerUpEmoKidTapa(TapasticComic):
    """Class to retrieve CheerUpEmoKid comics."""
    # Also on http://www.cheerupemokid.com
    # Also on http://enzocomics.tumblr.com
    name = 'cuek-tapa'
    long_name = 'Cheer Up Emo Kid (from Tapastic)'
    url = 'http://tapastic.com/series/CUEK'


class BigFootJusticeTapa(TapasticComic):
    """Class to retrieve Big Foot Justice comics."""
    # Also on http://bigfootjustice.com
    name = 'bigfoot-tapa'
    long_name = 'Big Foot Justice (from Tapastic)'
    url = 'http://tapastic.com/series/bigfoot-justice'


class UpAndOutTapa(TapasticComic):
    """Class to retrieve Up & Out comics."""
    # Also on http://upandoutcomic.tumblr.com
    name = 'upandout-tapa'
    long_name = 'Up And Out (from Tapastic)'
    url = 'http://tapastic.com/series/UP-and-OUT'


class ToonHoleTapa(TapasticComic):
    """Class to retrieve Toon Holes comics."""
    # Also on http://www.toonhole.com
    name = 'toonhole-tapa'
    long_name = 'Toon Hole (from Tapastic)'
    url = 'http://tapastic.com/series/TOONHOLE'


class AngryAtNothingTapa(TapasticComic):
    """Class to retrieve Angry at Nothing comics."""
    # Also on http://www.angryatnothing.net
    name = 'angry-tapa'
    long_name = 'Angry At Nothing (from Tapastic)'
    url = 'http://tapastic.com/series/Comics-yeah-definitely-comics-'


class HappyMondayTapa(TapasticComic):
    """Class to retrieve Happy Monday comics."""
    # Also on http://happymondaycomics.com
    name = 'happymonday-tapa'
    long_name = 'Happy Monday (from Tapastic)'
    url = 'https://tapastic.com/series/HappyMondayComics'


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
