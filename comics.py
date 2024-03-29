#! /usr/bin/python3
# vim: set expandtab tabstop=4 shiftwidth=4 :
"""Module to retrieve webcomics"""

from comic_abstract import GenericComic, get_date_for_comic
import re
from datetime import date, timedelta
import datetime
from urlfunctions import (
    get_soup_at_url,
    urljoin_wrapper,
    convert_iri_to_plain_ascii_uri,
    load_json_at_url,
    urlopen_wrapper,
)
import json
import locale
import urllib

DEFAULT_LOCAL = "en_GB.UTF-8"
# Technical switch to have a faster feedback when things go wrong.
# This could lead to additional requests to be performed and/or
# additional diagnosis information to be printed to the user.
PERFORM_CHECK = False


class GenericNumberedComic(GenericComic):
    """Generic class for "numbered" comics.

    This class applies to comic where comics are given a number
    which can be used as an entry point to get the relevant info
    and the range for these numbers can be computed somehow.

    The method `get_next_comic` methods is implemented in terms of new
    more specialized methods to be implemented/overridden:
        - get_comic_info
        - get_first_and_last_numbers
    """

    _categories = ("NUMBERED",)

    @classmethod
    def get_next_comic(cls, last_comic):
        """Generator to get the next comic. Implementation of GenericComic's abstract method."""
        first_num, last_num = cls.get_first_and_last_numbers()
        if last_comic:
            first_num = last_comic["num"] + 1
        cls.log("first_num:%d, last_num:%d" % (first_num, last_num))
        for num in range(first_num, last_num + 1):
            comic = cls.get_comic_info(num)
            if comic is not None:
                assert "num" not in comic
                comic["num"] = num
                yield comic

    @classmethod
    def get_first_and_last_numbers(cls):
        """Get index of first and last available comics (as a tuple of int)."""
        raise NotImplementedError

    @classmethod
    def get_comic_info(cls, num):
        """Get information about a particular comics."""
        raise NotImplementedError


class Xkcd(GenericNumberedComic):
    """Class to retrieve Xkcd comics."""

    name = "xkcd"
    long_name = "xkcd"
    url = "http://xkcd.com"
    _categories = ("GEEKY",)

    @classmethod
    def get_first_and_last_numbers(cls):
        """Get index of first and last available comics (as a tuple of int)."""
        json_url = urljoin_wrapper(cls.url, "info.0.json")
        return 1, load_json_at_url(json_url)["num"]

    @classmethod
    def get_comic_info(cls, num):
        """Get information about a particular comics."""
        if num == 404:
            return None
        json_url = urljoin_wrapper(cls.url, "%d/info.0.json" % num)
        comic_json = load_json_at_url(json_url)
        assert comic_json["num"] == num, json_url
        return {
            "json_url": json_url,
            "url": urljoin_wrapper(cls.url, str(num)),
            "prefix": "%d-" % num,
            "img": [comic_json["img"]],
            "date": dict_to_date(comic_json),
            "link": comic_json["link"],
            "news": comic_json["news"],
            "safe_title": comic_json["safe_title"],
            "transcript": comic_json["transcript"],
            "alt": comic_json["alt"],
            "title": comic_json["title"],
        }


# Helper functions corresponding to get_url_from_link/get_url_from_archive_element


@classmethod
def get_href(cls, link):
    """Implementation of get_url_from_link/get_url_from_archive_element."""
    return link["href"]


@classmethod
def join_cls_url_to_href(cls, link):
    """Implementation of get_url_from_link/get_url_from_archive_element."""
    return urljoin_wrapper(cls.url, link["href"])


class GenericNavigableComic(GenericComic):
    """Generic class for "navigable" comics : with first/next arrows.

    This class applies to comic where previous and next comics can be
    accessed from a given comic. Once given a starting point (either
    the first comic or the last comic retrieved), it will handle the
    navigation, the retrieval of the soup object and the setting of
    the 'url' attribute on retrieved comics. This limits a lot the
    amount of boilerplate code in the different implementation classes.

    The method `get_next_comic` methods is implemented in terms of new
    more specialized methods to be implemented/overridden:
        - get_first_comic_link
        - get_navi_link
        - get_comic_info
        - get_url_from_link
    """

    _categories = ("NAVIGABLE",)

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
        """Get url corresponding to a link. Default implementation is similar to get_href."""
        return link["href"]

    @classmethod
    def get_next_link(cls, last_soup):
        """Get link to next comic."""
        link = cls.get_navi_link(last_soup, True)
        cls.log("Next link is %s" % link)
        return link

    @classmethod
    def get_prev_link(cls, last_soup):
        """Get link to previous comic."""
        link = cls.get_navi_link(last_soup, False)
        cls.log("Prev link is %s" % link)
        return link

    @classmethod
    def get_next_comic(cls, last_comic):
        """Generic implementation of get_next_comic for navigable comics."""
        url = last_comic["url"] if last_comic else None
        cls.log("starting 'get_next_comic' from %s" % url)
        next_comic = (
            cls.get_next_link(get_soup_at_url(url))
            if url
            else cls.get_first_comic_link()
        )
        cls.log("next/first comic will be %s (url is %s)" % (str(next_comic), url))
        if PERFORM_CHECK:
            cls.check_navigation(url)
        while next_comic:
            prev_url, url = url, cls.get_url_from_link(next_comic)
            if prev_url == url:
                cls.log("got same url %s" % url)
                break
            cls.log("about to get %s (%s)" % (url, str(next_comic)))
            soup = get_soup_at_url(url)
            comic = cls.get_comic_info(soup, next_comic)
            if comic is not None:
                assert "url" not in comic
                comic["url"] = url
                yield comic
            next_comic = cls.get_next_link(soup)
            cls.log("next comic will be %s" % str(next_comic))

    @classmethod
    def check_first_link(cls):
        """Check that navigation to first comic seems to be working - for dev purposes."""
        cls.log("about to check first link")
        ok = True
        firstlink = cls.get_first_comic_link()
        if firstlink is None:
            print("From %s : no first link" % cls.url)
            ok = False
        else:
            firsturl = cls.get_url_from_link(firstlink)
            try:
                get_soup_at_url(firsturl)
            except urllib.error.HTTPError:
                print("From %s : invalid first url" % cls.url)
                ok = False
        cls.log("checked first link -> returned %d" % ok)
        return ok

    @classmethod
    def check_prev_next_links(cls, url):
        """Check that navigation to prev/next from a given URL seems to be working - for dev purposes."""
        cls.log("about to check prev/next from %s" % url)
        ok = True
        if url is None:
            prevlink, nextlink = None, None
        else:
            soup = get_soup_at_url(url)
            prevlink, nextlink = cls.get_prev_link(soup), cls.get_next_link(soup)
        if prevlink is None and nextlink is None:
            print("From %s : no previous nor next" % url)
            ok = False
        else:
            if prevlink:
                prevurl = cls.get_url_from_link(prevlink)
                prevsoup = get_soup_at_url(prevurl)
                prevnextlink = cls.get_next_link(prevsoup)
                prevnext = (
                    cls.get_url_from_link(prevnextlink)
                    if prevnextlink is not None
                    else "NO URL"
                )
                if prevnext != url:
                    print(
                        "From %s, going backward then forward leads to %s"
                        % (url, prevnext)
                    )
                    ok = False
            if nextlink:
                nexturl = cls.get_url_from_link(nextlink)
                if nexturl != url:
                    nextsoup = get_soup_at_url(nexturl)
                    nextprevlink = cls.get_prev_link(nextsoup)
                    nextprev = (
                        cls.get_url_from_link(nextprevlink)
                        if nextprevlink is not None
                        else "NO URL"
                    )
                    if nextprev != url:
                        print(
                            "From %s, going forward then backward leads to %s"
                            % (url, nextprev)
                        )
                        ok = False
        cls.log("checked prev/next from %s -> returned %d" % (url, ok))
        return ok

    @classmethod
    def check_navigation(cls, url):
        """Check that navigation functions seem to be working - for dev purposes."""
        cls.log("about to check navigation from %s" % url)
        first = cls.check_first_link()
        prevnext = cls.check_prev_next_links(url)
        ok = first and prevnext
        cls.log("checked navigation from %s -> returned %d" % (url, ok))
        return ok


class GenericListableComic(GenericComic):
    """Generic class for "listable" comics : with a list of comics (aka 'archive')

    The method `get_next_comic` methods is implemented in terms of new
    more specialized methods to be implemented/overridden:
        - get_archive_elements
        - get_url_from_archive_element
        - get_comic_info
    """

    _categories = ("LISTABLE",)

    @classmethod
    def get_archive_elements(cls):
        """Get the archive elements (iterable) containing comics from older to newer."""
        raise NotImplementedError

    @classmethod
    def get_url_from_archive_element(cls, archive_elt):
        """Get url corresponding to an archive element."""
        raise NotImplementedError

    @classmethod
    def get_comic_info(cls, soup, archive_elt):
        """Get information about a particular comics."""
        raise NotImplementedError

    @classmethod
    def get_next_comic(cls, last_comic):
        """Generic implementation of get_next_comic for listable comics."""
        waiting_for_url = last_comic["url"] if last_comic else None
        archive_elts = list(cls.get_archive_elements())
        for archive_elt in archive_elts:
            url = cls.get_url_from_archive_element(archive_elt)
            cls.log("considering %s" % url)
            if waiting_for_url is None:
                cls.log("about to get %s (%s)" % (url, str(archive_elt)))
                soup = get_soup_at_url(url)
                comic = cls.get_comic_info(soup, archive_elt)
                if comic is not None:
                    assert "url" not in comic
                    comic["url"] = url
                    yield comic
            elif waiting_for_url == url:
                waiting_for_url = None
        if waiting_for_url is not None:
            print(
                "Did not find previous comic %s in the %d comics found: there might be a problem"
                % (waiting_for_url, len(archive_elts))
            )


class GenericPaginatedListableComic(GenericComic):
    """Generic class for "paginated listable" comics : with a list of comics
    accessible over multiple pages. Unlike GenericListableComic, getting the
    whole list can be a expensive operation so we only want to retrieve
    the part of the list we are interested in.

    The method `get_next_comic` methods is implemented in terms of new
    more specialized methods to be implemented/overridden:
        - yield_archive_elements
        - archive_element_corresponds_to_comic
        - get_comic_info
   """

    _categories = ("PAGINATEDLISTABLE",)

    @classmethod
    def get_next_comic(cls, last_comic):
        """Generic implementation of get_next_comic for GenericPaginatedListableComic."""
        if last_comic is not None and not cls.last_comic_is_valid(last_comic):
            return []

        for e in reversed(cls.get_archive_elements(last_comic)):
            comic = cls.get_comic_info(e)
            if comic is not None:
                yield comic

    @classmethod
    def get_archive_elements(cls, last_comic):
        """Get archive elements from newer to older, stopping at last_comic."""
        archive_elements = []
        for elt in cls.yield_archive_elements():
            if cls.archive_element_corresponds_to_comic(elt, last_comic):
                return archive_elements
            archive_elements.append(elt)
        if last_comic is None:
            return archive_elements
        print(
            "Did not find previous comic %s in the %d comics found: there might be a problem"
            % (last_comic["url"], len(archive_elements))
        )
        return []

    @classmethod
    def last_comic_is_valid(cls, last_comic):
        """Check that last comic seems to be valid.

        Retrieving the list of comics to find a comic which does not exist
        anymore can be time consumming. When it is possible, it can be easier
        to check that the comic we are looking for is valid.

        Default behavior is to assume that the last comic is valid but this
        can be overridden with a more precise implementation in subclasses."""
        return True

    @classmethod
    def get_comic_info(cls, elt):
        """Get information about a particular comics."""
        raise NotImplementedError

    @classmethod
    def yield_archive_elements(cls):
        """Yield archive elements from newer to older."""
        raise NotImplementedError

    @classmethod
    def archive_element_corresponds_to_comic(cls, elt, comic):
        """Check is elements corresponds to comic object - return Boolean."""
        raise NotImplementedError


# Helper functions corresponding to get_first_comic_link/get_navi_link


@classmethod
def get_link_rel_next(cls, last_soup, next_):
    """Implementation of get_navi_link."""
    return last_soup.find("link", rel="next" if next_ else "prev")


@classmethod
def get_a_rel_next(cls, last_soup, next_):
    """Implementation of get_navi_link."""
    return last_soup.find("a", rel="next" if next_ else "prev")


@classmethod
def get_a_next(cls, last_soup, next_):
    """Implementation of get_navi_link."""
    return last_soup.find("a", title="Next" if next_ else "Previous")


@classmethod
def get_a_navi_navinext(cls, last_soup, next_):
    """Implementation of get_navi_link."""
    # ComicPress (WordPress plugin)
    return last_soup.find("a", class_="navi navi-next" if next_ else "navi navi-prev")


@classmethod
def get_a_navi_comicnavnext_navinext(cls, last_soup, next_):
    """Implementation of get_navi_link."""
    return last_soup.find(
        "a",
        class_="navi comic-nav-next navi-next"
        if next_
        else "navi comic-nav-previous navi-prev",
    )


@classmethod
def get_a_comicnavbase_comicnavnext(cls, last_soup, next_):
    """Implementation of get_navi_link."""
    return last_soup.find(
        "a",
        class_="comic-nav-base comic-nav-next"
        if next_
        else "comic-nav-base comic-nav-previous",
    )


@classmethod
def get_a_navi_navifirst(cls):
    """Implementation of get_first_comic_link."""
    # ComicPress (WordPress plugin)
    return get_soup_at_url(cls.url).find("a", class_="navi navi-first")


@classmethod
def get_a_first(cls):
    """Implementation of get_first_comic_link."""
    return get_soup_at_url(cls.url).find("a", title="First")


@classmethod
def get_div_navfirst_a(cls):
    """Implementation of get_first_comic_link."""
    div = get_soup_at_url(cls.url).find("div", class_="nav-first")
    return None if div is None else div.find("a")


@classmethod
def get_a_comicnavbase_comicnavfirst(cls):
    """Implementation of get_first_comic_link."""
    return get_soup_at_url(cls.url).find("a", class_="comic-nav-base comic-nav-first")


@classmethod
def simulate_first_link(cls):
    """Implementation of get_first_comic_link creating a link-like object from
    an URL provided by the class.

    Note: The first URL can easily be found using :
    `get_first_comic_link = navigate_to_first_comic`.
    """
    return {"href": cls.first_url}


@classmethod
def navigate_to_first_comic(cls):
    """Implementation of get_first_comic_link navigating from a user provided
    URL to the first comic.

    Sometimes, the first comic cannot be reached directly so to start
    from the first comic one has to go to the previous comic until
    there is no previous comics. Once this URL is reached, it
    is better to hardcode it but for development purposes, it
    is convenient to have an automatic way to find it.

    Then, the URL found can easily be used via `simulate_first_link`.
    """
    url = getattr(cls, "first_url", None)
    if url is None or url == NotImplemented:
        prompt = "Get starting URL for %s (%s):" % (cls.name, cls.url)
        url = input(prompt)
    print(url)
    comic = cls.get_prev_link(get_soup_at_url(url))
    while comic:
        url = cls.get_url_from_link(comic)
        print(url)
        comic = cls.get_prev_link(get_soup_at_url(url))
    cls.first_url = url
    return {"href": url}


class GenericEmptyComic(GenericComic):
    """Generic class for comics where nothing is to be done.

    It can be useful to deactivate temporarily comics that do not work
    properly by replacing `def MyComic(GenericWhateverComic)` with
    `def MyComic(GenericEmptyComic, GenericWhateverComic)`."""

    _categories = ("EMPTY",)

    @classmethod
    def get_next_comic(cls, last_comic):
        """Implementation of get_next_comic returning no comics."""
        cls.log("comic is considered as empty - returning no comic")
        return []


class GenericComicNotWorking(GenericEmptyComic):
    """Subclass of GenericEmptyComic used when comic is not working.

    This is more explicit than GenericEmptyComic as it hilights that
    only the implementation is not working and it can be fixed."""

    _categories = ("NOTWORKING",)


class GenericUnavailableComic(GenericEmptyComic):
    """Subclass of GenericEmptyComic used when a comic is not available.

    This is more explicit than GenericEmptyComic as it hilights that
    the source of the comic is not available but we expect it to be back
    soonish. See also GenericDeletedComic."""

    _categories = ("UNAVAILABLE",)


class GenericDeletedComic(GenericEmptyComic):
    """Subclass of GenericEmptyComic used when a comic does not exist anymore.

    This is more explicit than GenericEmptyComic as it hilights that
    the source of the comic does not exist anymore and it probably cannot
    be fixed. Corresponding classes are kept as we can still use the
    downloaded data. See also GenericUnavailableComic."""

    _categories = ("DELETED",)


class ExtraFabulousComics(GenericNavigableComic):
    """Class to retrieve Extra Fabulous Comics."""

    # Also on https://extrafabulouscomics.tumblr.com
    name = "efc"
    long_name = "Extra Fabulous Comics"
    url = "http://extrafabulouscomics.com"
    _categories = ("EFC",)
    get_navi_link = get_link_rel_next
    get_first_comic_link = simulate_first_link
    first_url = "http://extrafabulouscomics.com/comic/buttfly/"

    @classmethod
    def get_comic_info(cls, soup, link):
        """Get information about a particular comics."""
        imgs = soup.find_all("meta", property="og:image")
        title = soup.find("meta", property="og:title")["content"]
        date_str = soup.find("meta", property="article:published_time")["content"]
        return {
            "title": title,
            "img": [i["content"] for i in imgs],
            "date": isoformat_to_date(date_str),
            "prefix": title + "-",
        }


class GenericLeMondeBlog(GenericNavigableComic):
    """Generic class to retrieve comics from Le Monde blogs."""

    _categories = ("LEMONDE", "FRANCAIS")
    get_navi_link = get_link_rel_next
    get_first_comic_link = simulate_first_link
    first_url = NotImplemented

    @classmethod
    def get_comic_info(cls, soup, link):
        """Get information about a particular comics."""
        url2 = soup.find("link", rel="shortlink")["href"]
        title_meta = soup.find("meta", property="og:title")
        title = "" if title_meta is None else title_meta["content"]
        imgs = soup.find_all("meta", property="og:image")
        date_str = soup.find("time", class_="published")["datetime"]
        return {
            "title": title,
            "url2": url2,
            "img": [convert_iri_to_plain_ascii_uri(i["content"]) for i in imgs],
            "date": isoformat_to_date(date_str),
        }


class ZepWorld(GenericLeMondeBlog):
    """Class to retrieve Zep World comics."""

    name = "zep"
    long_name = "Zep World"
    url = "http://zepworld.blog.lemonde.fr"
    first_url = "http://zepworld.blog.lemonde.fr/2014/10/31/bientot-le-blog-de-zep/"


class Vidberg(GenericLeMondeBlog):
    """Class to retrieve Vidberg comics."""

    name = "vidberg"
    long_name = "Vidberg - l'actu en patates"
    url = "http://vidberg.blog.lemonde.fr"
    # Not the first but I didn't find an efficient way to retrieve it
    first_url = "http://vidberg.blog.lemonde.fr/2012/02/09/revue-de-campagne-la-campagne-du-modem-semballe/"


class Plantu(GenericLeMondeBlog):
    """Class to retrieve Plantu comics."""

    name = "plantu"
    long_name = "Plantu"
    url = "http://plantu.blog.lemonde.fr"
    first_url = "http://plantu.blog.lemonde.fr/2014/10/28/stress-test-a-bruxelles/"


class XavierGorce(GenericLeMondeBlog):
    """Class to retrieve Xavier Gorce comics."""

    name = "gorce"
    long_name = "Xavier Gorce"
    url = "http://xaviergorce.blog.lemonde.fr"
    first_url = "http://xaviergorce.blog.lemonde.fr/2015/01/09/distinction/"


class CartooningForPeace(GenericLeMondeBlog):
    """Class to retrieve Cartooning For Peace comics."""

    name = "forpeace"
    long_name = "Cartooning For Peace"
    url = "http://cartooningforpeace.blog.lemonde.fr"
    first_url = "http://cartooningforpeace.blog.lemonde.fr/2014/12/15/bado/"


class Aurel(GenericDeletedComic, GenericLeMondeBlog):
    """Class to retrieve Aurel comics."""

    name = "aurel"
    long_name = "Aurel"
    url = "http://aurel.blog.lemonde.fr"
    first_url = "http://aurel.blog.lemonde.fr/2014/09/29/le-senat-repasse-a-droite/"


class LesCulottees(GenericDeletedComic, GenericLeMondeBlog):
    """Class to retrieve Les Culottees comics."""

    name = "culottees"
    long_name = "Les Culottees"
    url = "http://lesculottees.blog.lemonde.fr"
    first_url = "http://lesculottees.blog.lemonde.fr/2016/01/11/clementine-delait-femme-a-barbe/"


class UneAnneeAuLycee(GenericLeMondeBlog):
    """Class to retrieve Une Annee Au Lycee comics."""

    name = "lycee"
    long_name = "Une Annee au Lycee"
    url = "http://uneanneeaulycee.blog.lemonde.fr"
    first_url = "http://uneanneeaulycee.blog.lemonde.fr/2016/06/13/la-semaine-du-bac-est-arrivee/"


class LisaMandel(GenericDeletedComic, GenericLeMondeBlog):
    """Class to retrieve Lisa Mandel comics."""

    name = "mandel"
    long_name = "Lisa Mandel (HP, hors-service)"
    url = "http://lisamandel.blog.lemonde.fr"
    first_url = "http://lisamandel.blog.lemonde.fr/2016/02/23/premiers-jours-a-calais/"


class Avventura(GenericLeMondeBlog):
    """Class to retrieve L'Avventura comics."""

    name = "avventura"
    long_name = "Avventura"
    url = "http://lavventura.blog.lemonde.fr"
    first_url = "http://lavventura.blog.lemonde.fr/2013/11/23/roma-paris-aller-simple/"


class MorganNavarro(GenericLeMondeBlog):
    """Class to retrieve Morgan Navarro comics."""

    name = "navarro"
    long_name = "Morgan Navarro (Ma vie de reac)"
    url = "http://morgannavarro.blog.lemonde.fr"
    first_url = "http://morgannavarro.blog.lemonde.fr/2015/09/09/le-doute/"


class Micael(GenericLeMondeBlog):
    """Class to retrieve Micael comics."""

    name = "micael"
    long_name = "Micael (L'Air du temps)"
    url = "https://www.lemonde.fr/blog/micael/"
    first_url = "https://www.lemonde.fr/blog/micael/2014/07/21/sattaquer-a-sartre/"


class EveVelo(GenericNavigableComic):
    """Class to retrieve Eve Velo comics."""

    name = "evevelo"
    long_name = "Eve Velo - chroniques du velotaf"
    url = "http://evevelo.the-comic.org"
    _categories = ("FRANCAIS", "BIKE")
    get_url_from_link = join_cls_url_to_href
    get_navi_link = get_a_rel_next

    @classmethod
    def get_first_comic_link(cls):
        """Get link to first comics."""
        return get_soup_at_url(cls.url).find("a", rel="start")

    @classmethod
    def get_comic_info(cls, soup, link):
        """Get information about a particular comics."""
        title = soup.find("h2").string
        date_str = soup.find("div", class_="headingsub").find("b").string
        date_ = string_to_date(
            remove_st_nd_rd_th_from_date(date_str), "%d %b %Y, %I:%M %p"
        )  # 29th Mar 2018, 8:59 AM
        imgs = soup.find("div", id="comicimagewrap").find_all("img")
        return {
            "title": title,
            "date": date_,
            "img": [urljoin_wrapper(cls.url, i["src"]) for i in imgs],
        }


class BecksComics(GenericNavigableComic):
    """Class to retrieve Becks Comics."""

    # Also on https://www.instagram.com/beckscomics/
    # Also on https://tapas.io/series/beckscomics
    name = "becks"
    long_name = "Becks Comics"
    url = "https://www.beckscomics.com"
    _categories = ("BECKS",)

    @classmethod
    def get_first_comic_link(cls):
        """Get link to first comics."""
        return get_soup_at_url(cls.url).find("li", class_="link-first").find("a")

    @classmethod
    def get_navi_link(cls, last_soup, next_):
        """Get link to next or previous comic."""
        li = last_soup.find("li", class_="link-next" if next_ else "link-prev")
        return li.find("a") if li else None

    @classmethod
    def get_comic_info(cls, soup, link):
        """Get information about a particular comics."""
        title = soup.find("h1", class_="entry-title").string
        date_str = soup.find("time", class_="entry-date")["datetime"]
        author = soup.find("span", class_="author vcard").find("a").string
        imgs = soup.find("div", class_="entry-content").find_all("img")
        return {
            "title": title,
            "date": isoformat_to_date(date_str),
            "author": author,
            "img": [i["src"] for i in imgs],
        }


class Rall(GenericComicNotWorking, GenericNavigableComic):
    """Class to retrieve Ted Rall comics."""

    # Also on http://www.gocomics.com/tedrall
    name = "rall"
    long_name = "Ted Rall"
    url = "http://rall.com/comic"
    _categories = ("RALL",)
    get_navi_link = get_link_rel_next
    get_first_comic_link = simulate_first_link
    # Not the first but I didn't find an efficient way to retrieve it
    first_url = "http://rall.com/2014/01/30/los-angeles-times-cartoon-well-miss-those-california-flowers"

    @classmethod
    def get_comic_info(cls, soup, link):
        """Get information about a particular comics."""
        title = soup.find("meta", property="og:title")["content"]
        author = soup.find("span", class_="author vcard").find("a").string
        date_str = soup.find("span", class_="entry-date").string
        desc = soup.find("meta", property="og:description")["content"]
        imgs = soup.find("div", class_="entry-content").find_all("img")
        imgs = imgs[:-7]  # remove social media buttons
        return {
            "title": title,
            "author": author,
            "date": string_to_date(date_str, "%B %d, %Y"),
            "description": desc,
            "img": [i["src"] for i in imgs],
        }


class Dilem(GenericNavigableComic):
    """Class to retrieve Ali Dilem comics."""

    name = "dilem"
    long_name = "Ali Dilem"
    url = "http://information.tv5monde.com/dilem"
    _categories = ("FRANCAIS",)
    get_url_from_link = join_cls_url_to_href
    get_first_comic_link = simulate_first_link
    first_url = "http://information.tv5monde.com/dilem/2004-06-26"

    @classmethod
    def get_navi_link(cls, last_soup, next_):
        """Get link to next or previous comic."""
        # prev is next / next is prev
        li = last_soup.find("li", class_="prev" if next_ else "next")
        return li.find("a") if li else None

    @classmethod
    def get_comic_info(cls, soup, link):
        """Get information about a particular comics."""
        short_url = soup.find("link", rel="shortlink")["href"]
        title = soup.find("meta", attrs={"name": "twitter:title"})["content"]
        imgs = soup.find_all("meta", property="og:image")
        date_str = soup.find("span", property="dc:date")["content"]
        return {
            "short_url": short_url,
            "title": title,
            "img": [i["content"] for i in imgs],
            "date": isoformat_to_date(date_str),
        }


class SpaceAvalanche(GenericNavigableComic):
    """Class to retrieve Space Avalanche comics."""

    name = "avalanche"
    long_name = "Space Avalanche"
    url = "http://www.spaceavalanche.com"
    get_navi_link = get_link_rel_next

    @classmethod
    def get_first_comic_link(cls):
        """Get link to first comics."""
        return {
            "href": "http://www.spaceavalanche.com/2009/02/02/irish-sea/",
            "title": "Irish Sea",
        }

    @classmethod
    def get_navi_link(cls, last_soup, next_):
        """Get link to next or previous comic."""
        img = last_soup.find("img", alt="Next Comic" if next_ else "Previous Comic")
        return img.parent if img else None

    @classmethod
    def get_comic_info(cls, soup, link):
        """Get information about a particular comics."""
        url_date_re = re.compile(
            ".*/(?P<year>[0-9]*)/(?P<month>[0-9]*)/(?P<day>[0-9]*)/.*$"
        )
        title = link["title"]
        url = cls.get_url_from_link(link)
        imgs = soup.find("div", class_="entry").find_all("img")
        return {
            "title": title,
            "date": regexp_match_to_date(url_date_re.match(url)),
            "img": [i["src"] for i in imgs],
        }


class ZenPencils(GenericNavigableComic):
    """Class to retrieve ZenPencils comics."""

    # Also on https://zenpencils.tumblr.com
    # Also on http://www.gocomics.com/zen-pencils
    name = "zenpencils"
    long_name = "Zen Pencils"
    url = "http://zenpencils.com"
    _categories = ("ZENPENCILS",)
    get_navi_link = get_a_navi_comicnavnext_navinext
    get_first_comic_link = simulate_first_link
    first_url = "http://zenpencils.com/comic/1-ralph-waldo-emerson-make-them-cry/"

    @classmethod
    def get_comic_info(cls, soup, link):
        """Get information about a particular comics."""
        imgs = soup.find("div", id="comic").find_all("img")
        # imgs2 = soup.find_all('meta', property='og:image')
        post = soup.find("div", class_="post-content")
        author = post.find("span", class_="post-author").find("a").string
        title = soup.find("h2", class_="post-title").string
        date_str = post.find("span", class_="post-date").string
        assert imgs
        assert all(i["alt"] == i["title"] for i in imgs)
        assert all(i["alt"] in (title, "") for i in imgs)
        return {
            "title": title,
            "author": author,
            "date": string_to_date(date_str, "%B %d, %Y"),
            "img": [urljoin_wrapper(cls.url, i["src"]) for i in imgs],
        }


class ItsTheTie(GenericComicNotWorking, GenericNavigableComic):
    """Class to retrieve It's the tie comics."""

    # Also on https://itsthetie.tumblr.com
    # Also on https://tapas.io/series/itsthetie
    name = "tie"
    long_name = "It's the tie"
    url = "http://itsthetie.com"
    _categories = ("TIE",)
    get_first_comic_link = get_a_navi_navifirst
    get_navi_link = get_a_navi_comicnavnext_navinext

    @classmethod
    def get_comic_info(cls, soup, link):
        """Get information about a particular comics."""
        title = soup.find("title").string
        date_str = soup.find("time")["datetime"]
        imgs = soup.find("div", id="comic").find_all("img")
        imgs_src = [i.get("oversrc") or i.get("src") for i in imgs]
        return {
            "title": title,
            "date": isoformat_to_date(date_str),
            "img": imgs_src,
        }


class PenelopeBagieu(GenericNavigableComic):
    """Class to retrieve comics from Penelope Bagieu's blog."""

    name = "bagieu"
    long_name = "Ma vie est tout a fait fascinante (Bagieu)"
    url = "https://www.penelope-jolicoeur.com"
    _categories = ("FRANCAIS",)
    get_navi_link = get_link_rel_next
    get_first_comic_link = simulate_first_link
    first_url = "https://www.penelope-jolicoeur.com/2007/02/ma-vie-mon-oeuv.html"

    @classmethod
    def get_comic_info(cls, soup, link):
        """Get information about a particular comics."""
        date_str = soup.find("h2", class_="date-header").string
        imgs = soup.find("div", class_="entry-body").find_all("img")
        title = soup.find("h3", class_="entry-header").string
        return {
            "title": title,
            "img": [i["src"] for i in imgs],
            "date": string_to_date(date_str, "%A %d %B %Y", "fr_FR.utf8"),
        }


class OneOneOneOneComic(GenericNavigableComic):
    """Class to retrieve 1111 Comics."""

    # Also on https://comics1111.tumblr.com
    # Also on https://tapas.io/series/1111-Comics
    name = "1111"
    long_name = "1111 Comics"
    url = "http://www.1111comics.me"
    _categories = ("ONEONEONEONE",)
    get_url_from_link = join_cls_url_to_href
    get_navi_link = get_link_rel_next

    @classmethod
    def get_first_comic_link(cls):
        """Get link to first comics."""
        return get_soup_at_url(cls.url).find("div", class_="post-nav-oldest").parent

    @classmethod
    def get_navi_link(cls, last_soup, next_):
        """Get link to next or previous comic."""
        div = last_soup.find(
            "div", class_="post-nav-next" if next_ else "post-nav-previous"
        )
        return None if div is None else div.parent

    @classmethod
    def get_comic_info(cls, soup, link):
        """Get information about a particular comics."""
        title = soup.find("title").string
        date_str = (
            soup.find("div", class_="flex justify-between grey-3").find("p").string
        )
        imgs = soup.find("div", class_="cms mw6").find_all("img")
        return {
            "title": title,
            "date": string_to_date(date_str, "%a, %b %d, %Y"),  # Thu, Apr 24, 2014
            "img": [urljoin_wrapper(cls.url, i["src"]) for i in imgs],
        }


class AngryAtNothing(GenericDeletedComic, GenericNavigableComic):
    """Class to retrieve Angry at Nothing comics."""

    # Also on https://tapas.io/series/Comics-yeah-definitely-comics-
    # Also on https://angryatnothing.tumblr.com
    name = "angry"
    long_name = "Angry At Nothing"
    url = "http://www.angryatnothing.net"
    get_first_comic_link = get_div_navfirst_a
    get_navi_link = get_a_rel_next

    @classmethod
    def get_comic_info(cls, soup, link):
        """Get information about a particular comics."""
        title = soup.find("h1", class_="comic-title").find("a").string
        date_str = soup.find("header", class_="comic-meta entry-meta").find("a").string
        imgs = soup.find_all("meta", property="og:image")
        return {
            "title": title,
            "date": string_to_date(date_str, "%B %d, %Y"),
            "img": [i["content"] for i in imgs],
        }


class NeDroid(GenericNavigableComic):
    """Class to retrieve NeDroid comics."""

    name = "nedroid"
    long_name = "NeDroid"
    url = "http://nedroid.com"
    get_first_comic_link = get_div_navfirst_a
    get_navi_link = get_link_rel_next
    get_url_from_link = join_cls_url_to_href

    @classmethod
    def get_comic_info(cls, soup, link):
        """Get information about a particular comics."""
        short_url_re = re.compile("^%s/\\?p=([0-9]*)" % cls.url)
        short_url = cls.get_url_from_link(soup.find("link", rel="shortlink"))
        num = int(short_url_re.match(short_url).group(1))
        div_comic = soup.find("div", id="comic")
        if div_comic is None:
            imgs = []
            title = title2 = ""
        else:
            imgs = div_comic.find_all("img")
            assert len(imgs) == 1, imgs
            title = imgs[0]["alt"]
            title2 = imgs[0]["title"]
        return {
            "short_url": short_url,
            "title": title,
            "title2": title2,
            "img": [urljoin_wrapper(cls.url, i["src"]) for i in imgs],
            "num": num,
        }


class Garfield(GenericComicNotWorking, GenericNavigableComic):  # See issue #50
    """Class to retrieve Garfield comics."""

    # Also on http://www.gocomics.com/garfield
    name = "garfield"
    long_name = "Garfield"
    url = "https://garfield.com"
    _categories = ("GARFIELD",)
    get_first_comic_link = simulate_first_link
    first_url = "https://garfield.com/comic/1978/06/19"

    @classmethod
    def get_navi_link(cls, last_soup, next_):
        """Get link to next or previous comic."""
        return last_soup.find(
            "a", class_="comic-arrow-right" if next_ else "comic-arrow-left"
        )

    @classmethod
    def get_comic_info(cls, soup, link):
        """Get information about a particular comics."""
        url = cls.get_url_from_link(link)
        url_date_re = re.compile(
            "^%s/comic/(?P<year>[0-9]*)/(?P<month>[0-9]*)/(?P<day>[0-9]*)" % cls.url
        )
        imgs = soup.find("div", class_="comic-display").find_all(
            "img", class_="img-responsive"
        )
        return {
            "date": regexp_match_to_date(url_date_re.match(url)),
            "img": [i["src"] for i in imgs],
        }


class Dilbert(GenericComicNotWorking, GenericNavigableComic):  # Am I blacklisted?
    """Class to retrieve Dilbert comics."""

    # Also on http://www.gocomics.com/dilbert-classics
    name = "dilbert"
    long_name = "Dilbert"
    url = "http://dilbert.com"
    get_url_from_link = join_cls_url_to_href
    get_first_comic_link = simulate_first_link
    first_url = "http://dilbert.com/strip/1989-04-16"

    @classmethod
    def get_navi_link(cls, last_soup, next_):
        """Get link to next or previous comic."""
        link = last_soup.find(
            "div", class_="nav-comic nav-right" if next_ else "nav-comic nav-left"
        )
        return link.find("a") if link else None

    @classmethod
    def get_comic_info(cls, soup, link):
        """Get information about a particular comics."""
        title = soup.find("meta", property="og:title")["content"]
        imgs = soup.find_all("meta", property="og:image")
        desc = soup.find("meta", property="og:description")["content"]
        date_str = soup.find("meta", property="article:publish_date")["content"]
        author = soup.find("meta", property="article:author")["content"]
        tags = soup.find("meta", property="article:tag")["content"]
        return {
            "title": title,
            "description": desc,
            "img": [i["content"] for i in imgs],
            "author": author,
            "tags": tags,
            "date": string_to_date(date_str, "%B %d, %Y"),
        }


class VictimsOfCircumsolar(GenericDeletedComic, GenericNavigableComic):
    """Class to retrieve VictimsOfCircumsolar comics."""

    # Also on https://victimsofcomics.tumblr.com
    name = "circumsolar"
    long_name = "Victims Of Circumsolar"
    url = "http://www.victimsofcircumsolar.com"
    get_navi_link = get_a_navi_comicnavnext_navinext
    get_first_comic_link = simulate_first_link
    first_url = "http://www.victimsofcircumsolar.com/comic/modern-addiction"

    @classmethod
    def get_comic_info(cls, soup, link):
        """Get information about a particular comics."""
        # Date is on the archive page
        title = soup.find_all("meta", property="og:title")[-1]["content"]
        desc = soup.find_all("meta", property="og:description")[-1]["content"]
        imgs = soup.find("div", id="comic").find_all("img")
        assert all(i["title"] == i["alt"] == title for i in imgs)
        return {
            "title": title,
            "description": desc,
            "img": [i["src"] for i in imgs],
        }


class ThreeWordPhrase(GenericNavigableComic):
    """Class to retrieve Three Word Phrase comics."""

    # Also on https://www.threewordphrase.tumblr.com
    name = "threeword"
    long_name = "Three Word Phrase"
    url = "http://threewordphrase.com"
    get_url_from_link = join_cls_url_to_href

    @classmethod
    def get_first_comic_link(cls):
        """Get link to first comics."""
        return get_soup_at_url(cls.url).find("img", src="/firstlink.gif").parent

    @classmethod
    def get_navi_link(cls, last_soup, next_):
        """Get link to next or previous comic."""
        link = last_soup.find(
            "img", src="/nextlink.gif" if next_ else "/prevlink.gif"
        ).parent
        return None if link.get("href") is None else link

    @classmethod
    def get_comic_info(cls, soup, link):
        """Get information about a particular comics."""
        title = soup.find("title")
        imgs = [
            img
            for img in soup.find_all("img")
            if not img["src"].endswith(
                (
                    "link.gif",
                    "32.png",
                    "twpbookad.jpg",
                    "merchad.jpg",
                    "header.gif",
                    "tipjar.jpg",
                )
            )
        ]
        return {
            "title": title.string if title else None,
            "title2": "  ".join(img.get("alt") for img in imgs if img.get("alt")),
            "img": [urljoin_wrapper(cls.url, img["src"]) for img in imgs],
        }


class DeadlyPanel(
    GenericComicNotWorking, GenericNavigableComic
):  # Not working on my machine
    """Class to retrieve Deadly Panel comics."""

    # Also on https://tapas.io/series/deadlypanel
    # Also on https://deadlypanel.tumblr.com
    name = "deadly"
    long_name = "Deadly Panel"
    url = "http://www.deadlypanel.com"
    get_first_comic_link = get_a_navi_navifirst
    get_navi_link = get_a_navi_comicnavnext_navinext

    @classmethod
    def get_comic_info(cls, soup, link):
        """Get information about a particular comics."""
        imgs = soup.find("div", id="comic").find_all("img")
        assert all(i["alt"] == i["title"] for i in imgs)
        return {"img": [i["src"] for i in imgs]}


class ImogenQuest(GenericNavigableComic):
    """Class to retrieve Imogen Quest comics."""

    # Also on https://imoquest.tumblr.com
    # Also on https://www.gocomics.com/imogen-quest
    name = "imogen"
    long_name = "Imogen Quest"
    url = "http://imogenquest.net"
    _categories = ("IMOGEN",)
    get_first_comic_link = get_div_navfirst_a
    get_navi_link = get_a_rel_next

    @classmethod
    def get_comic_info(cls, soup, link):
        """Get information about a particular comics."""
        title = soup.find("h2", class_="post-title").string
        author = soup.find("span", class_="post-author").find("a").string
        date_str = soup.find("span", class_="post-date").string
        imgs = soup.find("div", class_="comicpane").find_all("img")
        assert all(i["alt"] == i["title"] for i in imgs)
        title2 = imgs[0]["title"]
        return {
            "date": string_to_date(date_str, "%B %d, %Y"),
            "img": [i["src"] for i in imgs],
            "title": title,
            "title2": title2,
            "author": author,
        }


class MyExtraLife(GenericDeletedComic):
    """Class to retrieve My Extra Life comics."""

    # Redirects to a new site https://www.frogpants.com
    name = "extralife"
    long_name = "My Extra Life"
    url = "http://www.myextralife.com"


class SaturdayMorningBreakfastCereal(GenericNavigableComic):
    """Class to retrieve Saturday Morning Breakfast Cereal comics."""

    # Also on http://www.gocomics.com/saturday-morning-breakfast-cereal
    # Also on https://smbc-comics.tumblr.com
    name = "smbc"
    long_name = "Saturday Morning Breakfast Cereal"
    url = "http://www.smbc-comics.com"
    _categories = ("SMBC",)
    get_navi_link = get_a_rel_next

    @classmethod
    def get_first_comic_link(cls):
        """Get link to first comics."""
        return get_soup_at_url(cls.url).find("a", rel="first")

    @classmethod
    def get_comic_info(cls, soup, link):
        """Get information about a particular comics."""
        image1 = soup.find("img", id="cc-comic")
        image_url1 = image1["src"]
        aftercomic = soup.find("div", id="aftercomic")
        image_url2 = aftercomic.find("img")["src"] if aftercomic else ""
        imgs = [image_url1] + ([image_url2] if image_url2 else [])
        ld_json = soup.find('script', type="application/ld+json").string
        json_content = json.loads(ld_json)
        return {
            "title": image1["title"],
            "img": [
                convert_iri_to_plain_ascii_uri(urljoin_wrapper(cls.url, i))
                for i in imgs
            ],
            "author": json_content["author"],
            "date": isoformat_to_date(json_content["datePublished"]),
        }


class PerryBibleFellowship(GenericListableComic):  # Is now navigable too
    """Class to retrieve Perry Bible Fellowship comics."""

    name = "pbf"
    long_name = "Perry Bible Fellowship"
    url = "http://pbfcomics.com"
    get_url_from_archive_element = join_cls_url_to_href

    @classmethod
    def get_archive_elements(cls):
        soup = get_soup_at_url(cls.url)
        thumbnails = soup.find("div", id="all_thumbnails")
        return reversed(thumbnails.find_all("a"))

    @classmethod
    def get_comic_info(cls, soup, link):
        """Get information about a particular comics."""
        name = soup.find("meta", property="og:title")["content"]
        imgs = soup.find_all("meta", property="og:image")
        assert len(imgs) == 1, imgs
        return {
            "name": name,
            "img": [i["content"] for i in imgs],
        }


class Mercworks(GenericDeletedComic):  # Moved to Webtoons
    """Class to retrieve Mercworks comics."""

    # Also on https://mercworks.tumblr.com
    # Also on http://www.webtoons.com/en/comedy/mercworks/list?title_no=426
    # Also on https://tapas.io/series/MercWorks
    name = "mercworks"
    long_name = "Mercworks"
    url = "http://mercworks.net"
    _categories = ("MERCWORKS",)
    get_first_comic_link = get_a_comicnavbase_comicnavfirst
    get_navi_link = get_link_rel_next

    @classmethod
    def get_comic_info(cls, soup, link):
        """Get information about a particular comics."""
        title = soup.find("meta", property="og:title")["content"]
        metadesc = soup.find("meta", property="og:description")
        desc = metadesc["content"] if metadesc else ""
        date_str = soup.find("meta", property="article:published_time")["content"]
        imgs = soup.find_all("meta", property="og:image")
        return {
            "img": [i["content"] for i in imgs],
            "title": title,
            "desc": desc,
            "date": isoformat_to_date(date_str),
        }


class BerkeleyMews(GenericListableComic):
    """Class to retrieve Berkeley Mews comics."""

    # Also on https://mews.tumblr.com
    # Also on http://www.gocomics.com/berkeley-mews
    name = "berkeley"
    long_name = "Berkeley Mews"
    url = "http://www.berkeleymews.com"
    _categories = ("BERKELEY",)
    get_url_from_archive_element = get_href
    comic_num_re = re.compile("%s/\\?p=([0-9]*)$" % url)

    @classmethod
    def get_archive_elements(cls):
        archive_url = urljoin_wrapper(cls.url, "?page_id=2")
        return reversed(
            get_soup_at_url(archive_url).find_all("a", href=cls.comic_num_re)
        )

    @classmethod
    def get_comic_info(cls, soup, link):
        """Get information about a particular comics."""
        url_date_re = re.compile(
            ".*/(?P<year>[0-9]*)-(?P<month>[0-9]*)-(?P<day>[0-9]*)-.*"
        )
        url = cls.get_url_from_archive_element(link)
        num = int(cls.comic_num_re.match(url).group(1))
        img = soup.find("div", id="comic").find("img")
        assert all(i["alt"] == i["title"] for i in [img])
        title2 = img["title"]
        img_url = img["src"]
        return {
            "num": num,
            "title": link.string,
            "title2": title2,
            "img": [img_url],
            "date": regexp_match_to_date(url_date_re.match(img_url)),
        }


class GenericBouletCorp(GenericNavigableComic):
    """Generic class to retrieve BouletCorp comics in different languages."""

    # Also on https://bouletcorp.tumblr.com
    _categories = ("BOULET",)
    get_navi_link = get_link_rel_next

    @classmethod
    def get_first_comic_link(cls):
        """Get link to first comics."""
        return get_soup_at_url(cls.url).find("div", id="centered_nav").find_all("a")[0]

    @classmethod
    def get_comic_info(cls, soup, link):
        """Get information about a particular comics."""
        url = cls.get_url_from_link(link)
        url_date_re = re.compile(
            "^%s/(?P<year>[0-9]*)/(?P<month>[0-9]*)/(?P<day>[0-9]*)/" % cls.url
        )
        imgs = (
            soup.find("div", id="notes")
            .find("div", class_="storycontent")
            .find_all("img")
        )
        texts = "  ".join(t for t in (i.get("title") for i in imgs) if t)
        title = soup.find("title").string
        return {
            "img": [
                convert_iri_to_plain_ascii_uri(i["src"])
                for i in imgs
                if i.get("src") is not None
            ],
            "title": title,
            "texts": texts,
            "date": regexp_match_to_date(url_date_re.match(url)),
        }


class BouletCorp(GenericBouletCorp):
    """Class to retrieve BouletCorp comics."""

    name = "boulet"
    long_name = "Boulet Corp"
    url = "http://www.bouletcorp.com"
    _categories = ("FRANCAIS",)


class BouletCorpEn(GenericBouletCorp):
    """Class to retrieve EnglishBouletCorp comics."""

    name = "boulet_en"
    long_name = "Boulet Corp English"
    url = "http://english.bouletcorp.com"


class AmazingSuperPowers(GenericNavigableComic):
    """Class to retrieve Amazing Super Powers comics."""

    name = "asp"
    long_name = "Amazing Super Powers"
    url = "http://www.amazingsuperpowers.com"
    get_first_comic_link = get_a_navi_navifirst
    get_navi_link = get_a_navi_navinext

    @classmethod
    def get_comic_info(cls, soup, link):
        """Get information about a particular comics."""
        author = soup.find("span", class_="post-author").find("a").string
        date_str = soup.find("span", class_="post-date").string
        imgs = soup.find("div", id="comic").find_all("img")
        title = " ".join(i["title"] for i in imgs)
        assert all(i["alt"] == i["title"] for i in imgs)
        return {
            "title": title,
            "author": author,
            "img": [img["src"] for img in imgs],
            "date": string_to_date(date_str, "%B %d, %Y"),
        }


class ToonHole(GenericNavigableComic):
    """Class to retrieve Toon Holes comics."""

    # Also on https://tapas.io/series/TOONHOLE
    name = "toonhole"
    long_name = "Toon Hole"
    url = "http://www.toonhole.com"
    get_first_comic_link = get_a_comicnavbase_comicnavfirst
    get_navi_link = get_a_comicnavbase_comicnavnext

    @classmethod
    def get_comic_info(cls, soup, link):
        """Get information about a particular comics."""
        date_str = soup.find("div", class_="entry-meta").contents[0].strip()
        imgs = soup.find("div", id="comic").find_all("img")
        if imgs:
            img = imgs[0]
            title = img["alt"]
            assert img["title"] == title
        else:
            title = ""
        return {
            "title": title,
            "date": string_to_date(date_str, "%B %d, %Y"),
            "img": [convert_iri_to_plain_ascii_uri(i["src"]) for i in imgs],
        }


class Channelate(GenericNavigableComic):
    """Class to retrieve Channelate comics."""

    name = "channelate"
    long_name = "Channelate"
    url = "http://www.channelate.com"
    get_first_comic_link = get_a_navi_navifirst
    get_navi_link = get_link_rel_next
    get_url_from_link = join_cls_url_to_href

    @classmethod
    def get_comic_info(cls, soup, link):
        """Get information about a particular comics."""
        author = soup.find("span", class_="post-author").find("a").string
        date_str = soup.find("span", class_="post-date").string
        title = soup.find("meta", property="og:title")["content"]
        post = soup.find("div", id="comic")
        imgs = post.find_all("img") if post else []
        extra_url = None
        extra_div = soup.find("div", id="extrapanelbutton")
        if extra_div:
            extra_url = extra_div.find("a")["href"]
            extra_soup = get_soup_at_url(extra_url)
            extra_imgs = extra_soup.find_all("img", class_="extrapanelimage")
            imgs.extend(extra_imgs)
        return {
            "url_extra": extra_url,
            "title": title,
            "author": author,
            "date": string_to_date(date_str, "%Y/%m/%d"),
            "img": [
                convert_iri_to_plain_ascii_uri(urljoin_wrapper(cls.url, i["src"]))
                for i in imgs
            ],
        }


class CyanideAndHappiness(GenericNavigableComic):
    """Class to retrieve Cyanide And Happiness comics."""

    name = "cyanide"
    long_name = "Cyanide and Happiness"
    url = "http://explosm.net"
    _categories = ("NSFW",)
    get_url_from_link = join_cls_url_to_href

    @classmethod
    def get_first_comic_link(cls):
        """Get link to first comics."""
        return get_soup_at_url(cls.url).find("a", title="Oldest comic")

    @classmethod
    def get_navi_link(cls, last_soup, next_):
        """Get link to next or previous comic."""
        link = last_soup.find("a", class_="nav-next" if next_ else "nav-previous")
        return None if link.get("href") is None else link

    @classmethod
    def get_comic_info(cls, soup, link):
        """Get information about a particular comics."""
        url2 = soup.find("meta", property="og:url")["content"]
        num = int(url2.split("/")[-2])
        date_str, _, author = (
            soup.find("div", id="comic-author").text.strip().partition("\nby ")
        )
        imgs = soup.find_all("img", id="main-comic")
        return {
            "num": num,
            "author": author,
            "date": string_to_date(date_str, "%Y.%m.%d"),
            "prefix": "%d-" % num,
            "img": [
                convert_iri_to_plain_ascii_uri(urljoin_wrapper(cls.url, i["src"]))
                for i in imgs
            ],
        }


class MrLovenstein(GenericNumberedComic):
    """Class to retrieve Mr Lovenstein comics."""

    # Also on https://tapas.io/series/MrLovenstein
    name = "mrlovenstein"
    long_name = "Mr. Lovenstein"
    url = "http://www.mrlovenstein.com"

    @classmethod
    def get_comic_info(cls, num):
        # TODO: more info from http://www.mrlovenstein.com/archive
        url = urljoin_wrapper(cls.url, "/comic/%d" % num)
        soup = get_soup_at_url(url)
        imgs = list(reversed(soup.find_all("img", src=re.compile("^/images/comics/"))))
        description = soup.find("meta", attrs={"name": "description"})["content"]
        return {
            "url": url,
            "texts": "  ".join(t for t in (i.get("title") for i in imgs) if t),
            "img": [urljoin_wrapper(url, i["src"]) for i in imgs],
            "description": description,
        }

    @classmethod
    def get_first_and_last_numbers(cls):
        """Get index of first and last available comics (as a tuple of int)."""
        comic_num_re = re.compile("^/comic/([0-9]*)$")
        nums = [
            int(comic_num_re.match(link["href"]).group(1))
            for link in get_soup_at_url(cls.url).find_all("a", href=comic_num_re)
        ]
        return min(nums), max(nums)


class DinosaurComics(GenericListableComic):
    """Class to retrieve Dinosaur Comics comics."""

    name = "dinosaur"
    long_name = "Dinosaur Comics"
    url = "http://www.qwantz.com"
    get_url_from_archive_element = get_href
    comic_link_re = re.compile("^%s/index.php\\?comic=([0-9]*)$" % url)

    @classmethod
    def get_archive_elements(cls):
        archive_url = urljoin_wrapper(cls.url, "archive.php")
        # first link is random -> skip it
        return reversed(
            get_soup_at_url(archive_url).find_all("a", href=cls.comic_link_re)[1:]
        )

    @classmethod
    def get_comic_info(cls, soup, link):
        """Get information about a particular comics."""
        url = cls.get_url_from_archive_element(link)
        num = int(cls.comic_link_re.match(url).group(1))
        date_str = link.string
        text = link.next_sibling.string
        imgs = soup.find_all("meta", property="og:image")
        title = soup.find("title").string
        desc = soup.find("meta", property="og:description")["content"]
        return {
            "date": string_to_date(remove_st_nd_rd_th_from_date(date_str), "%B %d, %Y"),
            "img": [i["content"] for i in imgs],
            "title": title,
            "description": desc,
            "text": text,
            "num": num,
        }


class ButterSafe(GenericListableComic):
    """Class to retrieve Butter Safe comics."""

    name = "butter"
    long_name = "ButterSafe"
    url = "https://www.buttersafe.com"
    get_url_from_archive_element = get_href
    comic_link_re = re.compile(
        "^%s/(?P<year>[0-9]*)/(?P<month>[0-9]*)/(?P<day>[0-9]*)/.*" % url
    )

    @classmethod
    def get_archive_elements(cls):
        archive_url = urljoin_wrapper(cls.url, "archive/")
        soup = get_soup_at_url(archive_url)
        return reversed(soup.find_all("a", href=cls.comic_link_re))

    @classmethod
    def get_comic_info(cls, soup, link):
        """Get information about a particular comics."""
        url = cls.get_url_from_archive_element(link)
        title = link.string
        img = soup.find("div", id="comic").find("img")
        assert img["alt"] == title
        return {
            "title": title,
            "date": regexp_match_to_date(cls.comic_link_re.match(url)),
            "img": [convert_iri_to_plain_ascii_uri(img["src"])],
        }


class CalvinAndHobbes(GenericDeletedComic, GenericComic):
    """Class to retrieve Calvin and Hobbes comics."""

    # Also on http://www.gocomics.com/calvinandhobbes/
    name = "calvin"
    long_name = "Calvin and Hobbes"
    # This is not through any official webpage but eh...
    url = "http://marcel-oehler.marcellosendos.ch/comics/ch/"


class AbstruseGoose(GenericListableComic):
    """Class to retrieve AbstruseGoose Comics."""

    name = "abstruse"
    long_name = "Abstruse Goose"
    url = "http://abstrusegoose.com"
    get_url_from_archive_element = get_href
    comic_url_re = re.compile("^%s/([0-9]*)$" % url)
    img_re = re.compile("^%s/strips/.*" % url)

    @classmethod
    def get_archive_elements(cls):
        archive_url = urljoin_wrapper(cls.url, "archive")
        return get_soup_at_url(archive_url).find_all("a", href=cls.comic_url_re)

    @classmethod
    def get_comic_info(cls, soup, archive_elt):
        comic_url = cls.get_url_from_archive_element(archive_elt)
        num = int(cls.comic_url_re.match(comic_url).group(1))
        imgs = soup.find_all("img", src=cls.img_re)
        return {
            "num": num,
            "title": archive_elt.string,
            "img": [convert_iri_to_plain_ascii_uri(i["src"]) for i in imgs],
        }


class PhDComics(GenericNavigableComic):
    """Class to retrieve PHD Comics."""

    name = "phd"
    long_name = "PhD Comics"
    url = "http://phdcomics.com/comics/archive.php"
    get_first_comic_link = simulate_first_link
    first_url = "http://phdcomics.com/comics/archive.php?comicid=1"

    @classmethod
    def get_navi_link(cls, last_soup, next_):
        """Get link to next or previous comic."""
        # Prev does not work ?
        url = "http://phdcomics.com/comics/images/%s_button.gif" % (
            "next" if next_ else "prev"
        )
        img = last_soup.find("img", src=url)
        return None if img is None else img.parent

    @classmethod
    def get_comic_info(cls, soup, link):
        """Get information about a particular comics."""
        title = soup.find("meta", attrs={"name": "twitter:title"})["content"]
        imgs = soup.find_all("meta", property="og:image")
        return {
            "img": [i["content"] for i in imgs],
            "title": title,
        }


class Quarktees(GenericNavigableComic):
    """Class to retrieve the Quarktees comics."""

    # Also on https://thequarkside.tumblr.com
    name = "quarktees"
    long_name = "Quarktees"
    url = "http://www.quarktees.com/blogs/news"
    _categories = ("QUARKSIDE",)
    get_url_from_link = join_cls_url_to_href
    get_first_comic_link = simulate_first_link
    first_url = "http://www.quarktees.com/blogs/news/12486621-coming-soon"

    @classmethod
    def get_navi_link(cls, last_soup, next_):
        """Get link to next or previous comic."""
        return last_soup.find("a", id="article-next" if next_ else "article-prev")

    @classmethod
    def get_comic_info(cls, soup, link):
        """Get information about a particular comics."""
        ogtitle = soup.find("meta", property="og:title")
        if ogtitle is None:
            cls.log("Not available for the time being?")
            return None
        title = ogtitle["content"]
        article = soup.find("div", class_="single-article")
        imgs = article.find_all("img")
        return {
            "title": title,
            "img": [urljoin_wrapper(cls.url, i["src"]) for i in imgs],
        }


class OverCompensating(GenericComicNotWorking, GenericNavigableComic):  # Now WIGU ?
    """Class to retrieve the Over Compensating comics."""

    name = "compensating"
    long_name = "Over Compensating"
    url = "http://www.overcompensating.com"
    get_url_from_link = join_cls_url_to_href

    @classmethod
    def get_first_comic_link(cls):
        """Get link to first comics."""
        return get_soup_at_url(cls.url).find("a", href=re.compile("comic=1$"))

    @classmethod
    def get_navi_link(cls, last_soup, next_):
        """Get link to next or previous comic."""
        return last_soup.find("a", title="next comic" if next_ else "go back already")

    @classmethod
    def get_comic_info(cls, soup, link):
        """Get information about a particular comics."""
        img_src_re = re.compile("^/oc/comics/.*")
        comic_num_re = re.compile(".*comic=([0-9]*)$")
        comic_url = cls.get_url_from_link(link)
        num = int(comic_num_re.match(comic_url).group(1))
        img = soup.find("img", src=img_src_re)
        return {
            "num": num,
            "img": [urljoin_wrapper(comic_url, img["src"])],
            "title": img.get("title"),
        }


class Oglaf(GenericNavigableComic):
    """Class to retrieve Oglaf comics."""

    name = "oglaf"
    long_name = "Oglaf [NSFW]"
    url = "http://oglaf.com"
    _categories = ("NSFW",)
    get_url_from_link = join_cls_url_to_href
    get_navi_link = get_a_rel_next
    get_first_comic_link = simulate_first_link
    first_url = "https://www.oglaf.com/cumsprite/"

    @classmethod
    def get_comic_info(cls, soup, link):
        """Get information about a particular comics."""
        title = soup.find("title").string
        title_imgs = soup.find("div", id="tt").find_all("img")
        assert len(title_imgs) == 1, title_imgs
        strip_imgs = soup.find_all("img", id="strip")
        assert len(strip_imgs) == 1, strip_imgs
        imgs = title_imgs + strip_imgs
        desc = " ".join(i["title"] for i in imgs)
        return {
            "title": title,
            "img": [i["src"] for i in imgs],
            "description": desc,
        }


class ScandinaviaAndTheWorld(GenericNavigableComic):
    """Class to retrieve Scandinavia And The World comics."""

    name = "satw"
    long_name = "Scandinavia And The World"
    url = "http://satwcomic.com"
    get_first_comic_link = simulate_first_link
    first_url = "http://satwcomic.com/sweden-denmark-and-norway"

    @classmethod
    def get_navi_link(cls, last_soup, next_):
        """Get link to next or previous comic."""
        return last_soup.find("a", accesskey="n" if next_ else "p")

    @classmethod
    def get_comic_info(cls, soup, link):
        """Get information about a particular comics."""
        title = soup.find("meta", attrs={"name": "twitter:label1"})["content"]
        desc = soup.find("meta", property="og:description")["content"]
        imgs = soup.find_all("img", itemprop="image")
        return {
            "title": title,
            "description": desc,
            "img": [i["src"] for i in imgs],
        }


class SomethingOfThatIlk(GenericDeletedComic):
    """Class to retrieve the Something Of That Ilk comics."""

    name = "somethingofthatilk"
    long_name = "Something Of That Ilk"
    url = "http://www.somethingofthatilk.com"


class MonkeyUser(GenericNavigableComic):
    """Class to retrieve Monkey User comics."""

    name = "monkeyuser"
    long_name = "Monkey User"
    url = "http://www.monkeyuser.com"
    get_first_comic_link = simulate_first_link
    first_url = "http://www.monkeyuser.com/2016/project-lifecycle/"
    get_url_from_link = join_cls_url_to_href

    @classmethod
    def get_navi_link(cls, last_soup, next_):
        """Get link to next or previous comic."""
        div = last_soup.find("div", title="next" if next_ else "previous")
        return None if div is None else div.find("a")

    @classmethod
    def get_comic_info(cls, soup, link):
        """Get information about a particular comics."""
        title = soup.find("meta", property="og:title")["content"]
        desc = soup.find("meta", property="og:description")["content"]
        imgs = soup.find_all("meta", property="og:image")
        date_str = soup.find("span", class_="post-date").find("time").string
        return {
            "date": string_to_date(date_str, "%d %b %Y"),
            "img": [i["content"] for i in imgs],
            "title": title,
            "description": desc,
        }


class InfiniteMonkeyBusiness(GenericNavigableComic):
    """Class to retrieve InfiniteMonkeyBusiness comics."""

    name = "monkey"
    long_name = "Infinite Monkey Business"
    url = "http://infinitemonkeybusiness.net"
    get_navi_link = get_a_navi_comicnavnext_navinext
    get_first_comic_link = simulate_first_link
    first_url = "http://infinitemonkeybusiness.net/comic/pillory/"

    @classmethod
    def get_comic_info(cls, soup, link):
        """Get information about a particular comics."""
        title = soup.find("meta", property="og:title")["content"]
        imgs = soup.find("div", id="comic").find_all("img")
        return {
            "title": title,
            "img": [i["src"] for i in imgs],
        }


class Wondermark(GenericListableComic):
    """Class to retrieve the Wondermark comics."""

    name = "wondermark"
    long_name = "Wondermark"
    url = "http://wondermark.com"
    get_url_from_archive_element = get_href

    @classmethod
    def get_archive_elements(cls):
        archive_url = urljoin_wrapper(cls.url, "archive/")
        return reversed(get_soup_at_url(archive_url).find_all("a", rel="bookmark"))

    @classmethod
    def get_comic_info(cls, soup, link):
        """Get information about a particular comics."""
        date_str = soup.find("div", class_="postdate").find("em").string
        div = soup.find("div", id="comic")
        if div:
            img = div.find("img")
            img_src = [img["src"]]
            alt = img["alt"]
            assert alt == img["title"]
            title = soup.find("meta", property="og:title")["content"]
        else:
            img_src = []
            alt = ""
            title = ""
        return {
            "date": string_to_date(remove_st_nd_rd_th_from_date(date_str), "%B %d, %Y"),
            "img": img_src,
            "title": title,
            "alt": alt,
            "tags": " ".join(
                t.string
                for t in soup.find("div", class_="postmeta").find_all("a", rel="tag")
            ),
        }


class WarehouseComic(GenericDeletedComic, GenericNavigableComic):
    """Class to retrieve Warehouse Comic comics."""

    name = "warehouse"
    long_name = "Warehouse Comic"
    url = "http://warehousecomic.com"
    get_url_from_link = join_cls_url_to_href

    @classmethod
    def get_nav(cls, soup):
        """Get the navigation elements from soup object."""
        divnav = soup.find("div", id="comicNav")
        first, prev, next_, new = divnav.find_all("a")
        prev_n, next_n = (
            int(re.search("[0-9]+", href).group(0))
            for href in [prev["href"], next_["href"]]
        )
        # Workaround around navigation bug:
        # After last comic n, we still have a next button to comic with n+1 in the url
        # but it actually contains image for comic n (and a next link to n)
        if next_n - prev_n != 2:
            next_ = None
        return (first, prev, next_)

    @classmethod
    def get_first_comic_link(cls):
        """Get link to first comics."""
        return cls.get_nav(get_soup_at_url(cls.url))[0]

    @classmethod
    def get_navi_link(cls, last_soup, next_):
        """Get link to next or previous comic."""
        return cls.get_nav(last_soup)[2 if next_ else 1]

    @classmethod
    def get_comic_info(cls, soup, link):
        """Get information about a particular comics."""
        # Workaround around navigation bug
        next_ = cls.get_nav(soup)[2]
        if next_ is None:
            return None
        return {
            "img": [
                urljoin_wrapper(cls.url, i["src"])
                for i in [soup.find("div", align="center").find("img")]
            ],
        }


class JustSayEh(GenericDeletedComic, GenericNavigableComic):
    """Class to retrieve Just Say Eh comics."""

    # Also on https://tapas.io/series/Just-Say-Eh
    name = "justsayeh"
    long_name = "Just Say Eh"
    url = "http://www.justsayeh.com"
    get_first_comic_link = get_a_navi_navifirst
    get_navi_link = get_a_navi_comicnavnext_navinext

    @classmethod
    def get_comic_info(cls, soup, link):
        """Get information about a particular comics."""
        title = soup.find("h2", class_="post-title").string
        imgs = soup.find("div", id="comic").find_all("img")
        assert all(i["alt"] == i["title"] for i in imgs)
        alt = imgs[0]["alt"]
        return {
            "img": [i["src"] for i in imgs],
            "title": title,
            "alt": alt,
        }


class MouseBearComedy(GenericComicNotWorking):  # Website has changed
    """Class to retrieve Mouse Bear Comedy comics."""

    # Also on https://mousebearcomedy.tumblr.com
    name = "mousebear"
    long_name = "Mouse Bear Comedy"
    url = "http://www.mousebearcomedy.com/category/comics/"


class BigFootJustice(GenericNavigableComic):
    """Class to retrieve Big Foot Justice comics."""

    # Also on https://tapas.io/series/bigfoot-justice
    name = "bigfoot"
    long_name = "Big Foot Justice"
    url = "http://bigfootjustice.com"
    get_first_comic_link = simulate_first_link
    first_url = "https://bigfootjustice.com/comic/iscale/"
    get_navi_link = get_link_rel_next

    @classmethod
    def get_comic_info(cls, soup, link):
        """Get information about a particular comics."""
        imgs = soup.find("div", id="one-comic-option").find_all("img")
        title = soup.find("title").string
        return {
            "img": [i["src"] for i in imgs],
            "title": title,
        }


class RespawnComic(
    GenericDeletedComic
):  # The website still exists but comics seem to be on Tapas now
    """Class to retrieve Respawn Comic."""

    # Also on https://respawncomic.tumblr.com
    # Also on https://tapas.io/series/respawncomic
    name = "respawn"
    long_name = "Respawn Comic"
    url = "http://respawncomic.com "
    _categories = ("RESPAWN",)


class SafelyEndangered(GenericNavigableComic):
    """Class to retrieve Safely Endangered comics."""

    # Also on https://tumblr.safelyendangered.com
    name = "endangered"
    long_name = "Safely Endangered"
    url = "https://www.safelyendangered.com"
    get_navi_link = get_link_rel_next
    get_first_comic_link = simulate_first_link
    first_url = "https://www.safelyendangered.com/comic/clone/"

    @classmethod
    def get_comic_info(cls, soup, link):
        """Get information about a particular comics."""
        title = soup.find("h2", class_="post-title").string
        date_str = soup.find("span", class_="post-date").string
        imgs = soup.find("div", id="comic").find_all("img")
        alt = imgs[0]["alt"]
        assert all(i["alt"] == i["title"] for i in imgs)
        return {
            "date": string_to_date(date_str, "%B %d, %Y"),
            "img": [i["src"] for i in imgs],
            "title": title,
            "alt": alt,
        }


class PicturesInBoxes(GenericDeletedComic, GenericNavigableComic):
    """Class to retrieve Pictures In Boxes comics."""

    # Also on https://picturesinboxescomic.tumblr.com
    # Also on https://www.gocomics.com/pictures-in-boxes
    name = "picturesinboxes"
    long_name = "Pictures in Boxes"
    url = "http://www.picturesinboxes.com"
    get_navi_link = get_a_navi_navinext
    get_first_comic_link = simulate_first_link
    first_url = "http://www.picturesinboxes.com/2013/10/26/tetris/"
    _categories = ("PICTURESINBOXES",)

    @classmethod
    def get_comic_info(cls, soup, link):
        """Get information about a particular comics."""
        title = soup.find("h2", class_="post-title").string
        author = soup.find("span", class_="post-author").find("a").string
        date_str = soup.find("span", class_="post-date").string
        imgs = soup.find("div", class_="comicpane").find_all("img")
        assert imgs
        assert all(i["title"] == i["alt"] == title for i in imgs)
        return {
            "date": string_to_date(date_str, "%B %d, %Y"),
            "img": [i["src"] for i in imgs],
            "title": title,
            "author": author,
        }


class Penmen(GenericComicNotWorking, GenericNavigableComic):
    """Class to retrieve Penmen comics."""

    name = "penmen"
    long_name = "Penmen"
    url = "http://penmen.com"
    get_navi_link = get_link_rel_next
    get_first_comic_link = simulate_first_link
    first_url = "http://penmen.com/index.php/2016/09/12/penmen-announces-grin-big-brand-clothing/"

    @classmethod
    def get_comic_info(cls, soup, link):
        """Get information about a particular comics."""
        title = soup.find("title").string
        imgs = soup.find("div", class_="entry-content").find_all("img")
        short_url = soup.find("link", rel="shortlink")["href"]
        tags = " ".join(t.string for t in soup.find_all("a", rel="tag"))
        date_str = soup.find("time")["datetime"]
        return {
            "title": title,
            "short_url": short_url,
            "img": [i["src"] for i in imgs],
            "tags": tags,
            "date": isoformat_to_date(date_str),
        }


class TheDoghouseDiaries(GenericComicNotWorking, GenericNavigableComic):
    """Class to retrieve The Dog House Diaries comics."""

    name = "doghouse"
    long_name = "The Dog House Diaries"
    url = "http://thedoghousediaries.com"

    @classmethod
    def get_first_comic_link(cls):
        """Get link to first comics."""
        return get_soup_at_url(cls.url).find("a", id="firstlink")

    @classmethod
    def get_navi_link(cls, last_soup, next_):
        """Get link to next or previous comic."""
        return last_soup.find("a", id="nextlink" if next_ else "previouslink")

    @classmethod
    def get_comic_info(cls, soup, link):
        """Get information about a particular comics."""
        img_re = re.compile("^dhdcomics/.*")
        img = soup.find("img", src=img_re)
        comic_url = cls.get_url_from_link(link)
        return {
            "title": soup.find("h2", id="titleheader").string,
            "title2": soup.find("div", id="subtext").string,
            "alt": img.get("title"),
            "img": [urljoin_wrapper(comic_url, img["src"].strip())],
            "num": int(comic_url.split("/")[-1]),
        }


class InvisibleBread(GenericListableComic):
    """Class to retrieve Invisible Bread comics."""

    # Also on http://www.gocomics.com/invisible-bread
    name = "invisiblebread"
    long_name = "Invisible Bread"
    url = "https://invisiblebread.com"

    @classmethod
    def get_archive_elements(cls):
        archive_url = urljoin_wrapper(cls.url, "archives/")
        return reversed(
            get_soup_at_url(archive_url).find_all("td", class_="archive-title")
        )

    @classmethod
    def get_url_from_archive_element(cls, td):
        return td.find("a")["href"]

    @classmethod
    def get_comic_info(cls, soup, td):
        """Get information about a particular comics."""
        url = cls.get_url_from_archive_element(td)
        title = td.find("a").string
        month_and_day = td.previous_sibling.string
        link_re = re.compile("^%s/([0-9]+)/" % cls.url)
        year = link_re.match(url).group(1)
        date_str = month_and_day + " " + year
        imgs = [soup.find("div", id="comic").find("img")]
        assert len(imgs) == 1, imgs
        assert all(i["title"] == i["alt"] == title for i in imgs)
        return {
            "date": string_to_date(date_str, "%b %d %Y"),
            "img": [urljoin_wrapper(cls.url, i["src"]) for i in imgs],
            "title": title,
        }


class DiscoBleach(GenericDeletedComic):
    """Class to retrieve Disco Bleach Comics."""

    name = "discobleach"
    long_name = "Disco Bleach"
    url = "http://discobleach.com"


class TubeyToons(GenericDeletedComic):
    """Class to retrieve TubeyToons comics."""

    # Also on https://tapas.io/series/Tubey-Toons
    # Also on https://tubeytoons.tumblr.com
    name = "tubeytoons"
    long_name = "Tubey Toons"
    url = "http://tubeytoons.com"
    _categories = ("TUBEYTOONS",)


class CompletelySeriousComics(GenericNavigableComic):
    """Class to retrieve Completely Serious comics."""

    name = "completelyserious"
    long_name = "Completely Serious Comics"
    url = "http://completelyseriouscomics.com"
    get_first_comic_link = get_a_navi_navifirst
    get_navi_link = get_a_navi_navinext

    @classmethod
    def get_comic_info(cls, soup, link):
        """Get information about a particular comics."""
        title = soup.find("h2", class_="post-title").string
        author = soup.find("span", class_="post-author").contents[1].string
        date_str = soup.find("span", class_="post-date").string
        imgs = soup.find("div", class_="comicpane").find_all("img")
        assert imgs
        alt = imgs[0]["title"]
        assert all(i["title"] == i["alt"] == alt for i in imgs)
        return {
            "date": string_to_date(date_str, "%B %d, %Y"),
            "img": [i["src"] for i in imgs],
            "title": title,
            "alt": alt,
            "author": author,
        }


class PoorlyDrawnLines(GenericListableComic):
    """Class to retrieve Poorly Drawn Lines comics."""

    # Also on https://pdlcomics.tumblr.com
    name = "poorlydrawn"
    long_name = "Poorly Drawn Lines"
    url = "https://poorlydrawnlines.com"
    _categories = ("POORLYDRAWN",)
    get_url_from_archive_element = get_href

    @classmethod
    def get_comic_info(cls, soup, link):
        """Get information about a particular comics."""
        imgs = soup.find("div", class_="post").find_all("img")
        return {
            "img": [i["src"] for i in imgs],
            "title": imgs[0].get("title", "") if imgs else "",
        }

    @classmethod
    def get_archive_elements(cls):
        archive_url = urljoin_wrapper(cls.url, "archive")
        url_re = re.compile("^%s/comic/." % cls.url)
        return reversed(get_soup_at_url(archive_url).find_all("a", href=url_re))


class LoadingComics(GenericNavigableComic):
    """Class to retrieve Loading Artist comics."""

    name = "loadingartist"
    long_name = "Loading Artist"
    url = "http://www.loadingartist.com/latest"
    get_navi_link = get_a_next
    get_first_comic_link = get_a_first

    @classmethod
    def get_comic_info(cls, soup, link):
        """Get information about a particular comics."""
        title = soup.find("h1").string
        date_str = soup.find("span", class_="date").string.strip()
        imgs = soup.find("div", class_="comic").find_all("img", alt="", title="")
        return {
            "title": title,
            "img": [i["src"] for i in imgs],
            "date": string_to_date(date_str, "%B %d, %Y"),
        }


class ChuckleADuck(GenericDeletedComic):
    """Class to retrieve Chuckle-A-Duck comics."""

    # Now, Crowden Satz posts on https://crowdensatz.com
    name = "chuckleaduck"
    long_name = "Chuckle-A-duck"
    url = "http://chuckleaduck.com"


class DepressedAlien(GenericNavigableComic):
    """Class to retrieve Depressed Alien Comics."""

    name = "depressedalien"
    long_name = "Depressed Alien"
    url = "http://depressedalien.com"
    get_url_from_link = join_cls_url_to_href

    @classmethod
    def get_first_comic_link(cls):
        """Get link to first comics."""
        return get_soup_at_url(cls.url).find("img", attrs={"name": "beginArrow"}).parent

    @classmethod
    def get_navi_link(cls, last_soup, next_):
        """Get link to next or previous comic."""
        return last_soup.find(
            "img", attrs={"name": "rightArrow" if next_ else "leftArrow"}
        ).parent

    @classmethod
    def get_comic_info(cls, soup, link):
        """Get information about a particular comics."""
        title = soup.find("meta", attrs={"name": "twitter:title"})["content"]
        imgs = soup.find_all("meta", property="og:image")
        return {
            "title": title,
            "img": [i["content"] for i in imgs],
        }


class TurnOffUs(GenericListableComic):
    """Class to retrieve TurnOffUs comics."""

    name = "turnoffus"
    long_name = "Turn Off Us"
    url = "http://turnoff.us"
    _categories = ("GEEKY",)
    get_url_from_archive_element = join_cls_url_to_href

    @classmethod
    def get_archive_elements(cls):
        archive_url = urljoin_wrapper(cls.url, "all")
        post_list = get_soup_at_url(archive_url).find("ul", class_="post-list")
        return reversed(post_list.find_all("a", class_="post-link"))

    @classmethod
    def get_comic_info(cls, soup, archive_elt):
        """Get information about a particular comics."""
        title = soup.find("meta", property="og:title")["content"]
        imgs = soup.find_all("meta", property="og:image")
        return {
            "title": title,
            "img": [i["content"] for i in imgs],
        }


class ThingsInSquares(GenericListableComic):
    """Class to retrieve Things In Squares comics."""

    # This can be retrieved in other languages
    # Also on https://tapas.io/series/Things-in-Squares
    name = "squares"
    long_name = "Things in squares"
    url = "http://www.thingsinsquares.com"

    @classmethod
    def get_comic_info(cls, soup, tr):
        """Get information about a particular comics."""
        _, td2, td3 = tr.find_all("td")
        a = td2.find("a")
        date_str = td3.string
        title = a.string
        title2 = soup.find("meta", property="og:title")["content"]
        desc = soup.find("meta", property="og:description")
        description = desc["content"] if desc else ""
        tags = " ".join(
            t["content"] for t in soup.find_all("meta", property="article:tag")
        )
        imgs = soup.find_all("meta", property="og:image")
        return {
            "date": string_to_date(date_str, "%m.%d.%y"),
            "title": title,
            "title2": title2,
            "description": description,
            "tags": tags,
            "img": [i["content"] for i in imgs],
        }

    @classmethod
    def get_url_from_archive_element(cls, tr):
        _, td2, __ = tr.find_all("td")
        return td2.find("a")["href"]

    @classmethod
    def get_archive_elements(cls):
        archive_url = urljoin_wrapper(cls.url, "archive-2")
        return reversed(get_soup_at_url(archive_url).find("tbody").find_all("tr"))


class HappleTea(GenericNavigableComic):
    """Class to retrieve Happle Tea Comics."""

    name = "happletea"
    long_name = "Happle Tea"
    url = "http://www.happletea.com"
    get_first_comic_link = get_a_navi_navifirst
    get_navi_link = get_link_rel_next

    @classmethod
    def get_comic_info(cls, soup, link):
        """Get information about a particular comics."""
        imgs = soup.find("div", id="comic").find_all("img")
        post = soup.find("div", class_="post-content")
        title = post.find("h2", class_="post-title").string
        author = post.find("a", rel="author").string
        date_str = post.find("span", class_="post-date").string
        assert all(i["alt"] == i["title"] for i in imgs)
        return {
            "title": title,
            "img": [i["src"] for i in imgs],
            "alt": "".join(i["alt"] for i in imgs),
            "date": string_to_date(date_str, "%B %d, %Y"),
            "author": author,
        }


class RockPaperScissors(GenericNavigableComic):
    """Class to retrieve Rock Paper Scissors comics."""

    name = "rps"
    long_name = "Rock Paper Scissors"
    url = "http://rps-comics.com"
    get_first_comic_link = get_a_navi_navifirst
    get_navi_link = get_a_navi_comicnavnext_navinext

    @classmethod
    def get_comic_info(cls, soup, link):
        """Get information about a particular comics."""
        title = soup.find("title").string
        imgs = soup.find_all("meta", property="og:image")
        short_url = soup.find("link", rel="shortlink")["href"]
        transcript = soup.find("div", id="transcript-content").string
        return {
            "title": title,
            "transcript": transcript,
            "short_url": short_url,
            "img": [i["content"] for i in imgs],
        }


class FatAwesomeComics(GenericDeletedComic):
    """Class to retrieve Fat Awesome Comics."""

    # Also on https://fatawesomecomedy.tumblr.com
    name = "fatawesome"
    long_name = "Fat Awesome"
    url = "http://fatawesome.com/comics"


class PeterLauris(GenericNavigableComic):
    """Class to retrieve Peter Lauris comics."""

    name = "peterlauris"
    long_name = "Peter Lauris"
    url = "http://peterlauris.com/comics"
    get_navi_link = get_a_rel_next
    get_first_comic_link = simulate_first_link
    first_url = "http://peterlauris.com/comics/just-in-case/"

    @classmethod
    def get_comic_info(cls, soup, link):
        """Get information about a particular comics."""
        title = soup.find("meta", attrs={"name": "twitter:title"})["content"]
        date_str = soup.find("meta", property="article:published_time")["content"]
        imgs = soup.find_all("meta", property="og:image")
        return {
            "title": title,
            "img": [i["content"] for i in imgs],
            "date": isoformat_to_date(date_str),
        }


class RandomCrab(GenericNavigableComic):
    """Class to retrieve Random Crab comics."""

    name = "randomcrab"
    long_name = "Random Crab"
    url = "https://randomcrab.com"
    get_navi_link = get_a_rel_next
    get_first_comic_link = simulate_first_link
    first_url = "https://randomcrab.com/natural-elephant/"

    @classmethod
    def get_comic_info(cls, soup, link):
        """Get information about a particular comics."""
        title = soup.find("meta", property="og:title")["content"]
        desc = soup.find("meta", property="og:description")
        desc_str = "" if desc is None else desc["content"]
        date_str = soup.find("meta", property="article:published_time")["content"]
        imgs = soup.find_all("meta", property="og:image")
        author = soup.find("a", rel="author").string
        return {
            "title": title,
            "desc": desc_str,
            "img": [i["content"] for i in imgs],
            "date": isoformat_to_date(date_str),
            "author": author,
        }


class JuliasDrawings(GenericListableComic):
    """Class to retrieve Julia's Drawings."""

    name = "julia"
    long_name = "Julia's Drawings"
    url = "https://drawings.jvns.ca"
    _categories = ("GEEKY",)
    get_url_from_archive_element = get_href

    @classmethod
    def get_archive_elements(cls):
        div = get_soup_at_url(cls.url).find("div", class_="drawings")
        return reversed(div.find_all("a"))

    @classmethod
    def get_comic_info(cls, soup, archive_elt):
        """Get information about a particular comics."""
        date_str = soup.find("meta", property="og:article:published_time")["content"]
        title = soup.find("h3", class_="p-post-title").string
        imgs = soup.find("section", class_="post-content").find_all("img")
        return {
            "title": title,
            "img": [urljoin_wrapper(cls.url, i["src"]) for i in imgs],
            "date": isoformat_to_date(date_str),
        }


class AnythingComic(GenericComicNotWorking, GenericListableComic):
    """Class to retrieve Anything Comics."""

    # Also on https://www.smackjeeves.com/discover/articleList?titleNo=50399
    # Also on https://tapas.io/series/anything
    name = "anythingcomic"
    long_name = "Anything Comic"
    url = "http://www.anythingcomic.com"
    _categories = ("ANYTHING",)

    @classmethod
    def get_archive_elements(cls):
        archive_url = urljoin_wrapper(cls.url, "archive/")
        # The first 2 <tr>'s do not correspond to comics
        return (
            get_soup_at_url(archive_url)
            .find("table", id="chapter_table")
            .find_all("tr")[2:]
        )

    @classmethod
    def get_url_from_archive_element(cls, tr):
        """Get url corresponding to an archive element."""
        _, td_comic, td_date, _ = tr.find_all("td")
        link = td_comic.find("a")
        return urljoin_wrapper(cls.url, link["href"])

    @classmethod
    def get_comic_info(cls, soup, tr):
        """Get information about a particular comics."""
        td_num, td_comic, td_date, _ = tr.find_all("td")
        num = int(td_num.string)
        link = td_comic.find("a")
        title = link.string
        imgs = soup.find_all("img", id="comic_image")
        date_str = td_date.string
        assert len(imgs) == 1, imgs
        assert all(i.get("alt") == i.get("title") for i in imgs)
        return {
            "num": num,
            "title": title,
            "alt": imgs[0].get("alt", ""),
            "img": [urljoin_wrapper(cls.url, i["src"]) for i in imgs],
            "date": string_to_date(
                remove_st_nd_rd_th_from_date(date_str), "%B %d, %Y, %I:%M %p"
            ),
        }


class RaeTheDoe(GenericListableComic):
    """Class to retrieve Rae The Doe comics."""

    # Also on https://raethedoe.tumblr.com
    name = "rae"
    long_name = "Rae the Doe"
    url = "https://www.raethedoe.com"
    get_url_from_archive_element = get_href

    @classmethod
    def get_archive_elements(cls):
        archive_url = urljoin_wrapper(cls.url, "p/archive.html")
        soup = get_soup_at_url(archive_url)
        div_content = soup.find("div", class_="post-body entry-content")
        return div_content.find_all("a")[:-1]

    @classmethod
    def get_comic_info(cls, soup, a):
        """Get information about a particular comics."""
        title = soup.find("meta", property="og:title")["content"]
        imgs = soup.find_all("link", rel="image_src")
        return {
            "img": [i["href"] for i in imgs],
            "title": title,
        }


class HowDnsWorksComics(GenericListableComic):
    """Class to retrieve How DNS Works Comics."""

    name = "dns"
    long_name = "How DNS works"
    url = "https://howdns.works"
    get_url_from_archive_element = join_cls_url_to_href
    _categories = ("GEEKY",)

    @classmethod
    def get_archive_elements(cls):
        soup = get_soup_at_url(urljoin_wrapper(cls.url, "episodes"))
        return soup.find("ul", class_="episode-list").find_all("a")

    @classmethod
    def get_comic_info(cls, soup, archive_elt):
        """Get information about a particular comics."""
        author = soup.find("meta", attrs={"name": "author"})["content"]
        tags = soup.find("meta", attrs={"name": "keywords"})["content"]
        title = soup.find("h1").string
        # TODO: How to handle SVGs ?
        imgs = soup.find("ul", class_="group").find_all("svg")
        cls.log("% svg ignored" % len(imgs))
        return {
            "img": [],
            "author": author,
            "title": title,
            "tags": tags,
        }


class HowHttpsWorksComics(GenericListableComic):
    """Class to retrieve How HTTPS Works Comics."""

    name = "https"
    long_name = "How HTTPS works"
    url = "https://howhttps.works"
    get_url_from_archive_element = join_cls_url_to_href
    _categories = ("GEEKY",)

    @classmethod
    def get_archive_elements(cls):
        soup = get_soup_at_url(urljoin_wrapper(cls.url, "episodes"))
        return soup.find_all("a", class_="db link black dim")

    @classmethod
    def get_comic_info(cls, soup, archive_elt):
        """Get information about a particular comics."""
        author = soup.find("meta", attrs={"name": "twitter:creator"})["content"]
        title = soup.find("title").string
        # TODO: How to handle SVGs ?
        imgs = soup.find("div", class_="flex flex-wrap comic pv3").find_all("svg")
        cls.log("% svg ignored" % len(imgs))
        return {
            "img": [],
            "author": author,
            "title": title,
        }


class LonnieMillsap(GenericNavigableComic):
    """Class to retrieve Lonnie Millsap's comics."""

    name = "millsap"
    long_name = "Lonnie Millsap"
    url = "http://www.lonniemillsap.com"
    get_navi_link = get_link_rel_next
    get_first_comic_link = simulate_first_link
    first_url = "http://www.lonniemillsap.com/?p=42"

    @classmethod
    def get_comic_info(cls, soup, link):
        """Get information about a particular comics."""
        title = soup.find("h2", class_="post-title").string
        post = soup.find("div", class_="post-content")
        author = post.find("span", class_="post-author").find("a").string
        date_str = post.find("span", class_="post-date").string
        imgs = post.find("div", class_="entry").find_all("img")
        return {
            "title": title,
            "author": author,
            "img": [i["src"] for i in imgs],
            "date": string_to_date(date_str, "%B %d, %Y"),
        }


class LinsEditions(GenericDeletedComic):  # Permanently moved to warandpeas
    """Class to retrieve L.I.N.S. Editions comics."""

    # Also on https://linscomics.tumblr.com
    # Now on https://warandpeas.com
    name = "lins"
    long_name = "L.I.N.S. Editions"
    url = "https://linsedition.com"
    _categories = ("WARANDPEAS", "LINS")


class WarAndPeas(GenericComicNotWorking, GenericNavigableComic):
    """Class to retrieve War And Peas comics."""

    name = "warandpeas"
    long_name = "War And Peas"
    url = "https://warandpeas.com"
    get_navi_link = get_link_rel_next
    get_first_comic_link = simulate_first_link
    first_url = "https://warandpeas.com/2011/11/07/565/"
    _categories = ("WARANDPEAS", "LINS")

    @classmethod
    def get_comic_info(cls, soup, link):
        """Get information about a particular comics."""
        title = soup.find("meta", property="og:title")["content"]
        imgs = soup.find_all("meta", property="og:image")
        date_str = soup.find("meta", property="article:published_time")["content"]
        return {
            "title": title,
            "img": [i["content"] for i in imgs],
            "date": isoformat_to_date(date_str),
        }


class ThorsThundershack(GenericNavigableComic):
    """Class to retrieve Thor's Thundershack comics."""

    # Also on https://tapas.io/series/Thors-Thundershac
    name = "thor"
    long_name = "Thor's Thundershack"
    url = "http://www.thorsthundershack.com"
    _categories = ("THOR",)
    get_url_from_link = join_cls_url_to_href

    @classmethod
    def get_first_comic_link(cls):
        """Get link to first comics."""
        return get_soup_at_url(cls.url).find("a", class_="first navlink")

    @classmethod
    def get_navi_link(cls, last_soup, next_):
        """Get link to next or previous comic."""
        for link in last_soup.find_all("a", rel="next" if next_ else "prev"):
            if link["href"] != "/comic":
                return link
        return None

    @classmethod
    def get_comic_info(cls, soup, link):
        """Get information about a particular comics."""
        title = soup.find("meta", attrs={"name": "description"})["content"]
        description = soup.find("div", itemprop="articleBody").text
        author = soup.find("span", itemprop="author copyrightHolder").string
        imgs = soup.find_all("img", itemprop="image")
        assert all(i["title"] == i["alt"] for i in imgs)
        alt = imgs[0]["alt"] if imgs else ""
        date_str = soup.find("time", itemprop="datePublished")["datetime"]
        return {
            "img": [urljoin_wrapper(cls.url, i["src"]) for i in imgs],
            "date": string_to_date(date_str, "%Y-%m-%d %H:%M:%S"),
            "author": author,
            "title": title,
            "alt": alt,
            "description": description,
        }


class GerbilWithAJetpack(GenericNavigableComic):
    """Class to retrieve GerbilWithAJetpack comics."""

    name = "gerbil"
    long_name = "Gerbil With A Jetpack"
    url = "http://gerbilwithajetpack.com"
    get_first_comic_link = get_a_navi_navifirst
    get_navi_link = get_a_rel_next

    @classmethod
    def get_comic_info(cls, soup, link):
        """Get information about a particular comics."""
        title = soup.find("h2", class_="post-title").string
        author = soup.find("span", class_="post-author").find("a").string
        date_str = soup.find("span", class_="post-date").string
        imgs = soup.find("div", id="comic").find_all("img")
        alt = imgs[0]["alt"]
        assert all(i["alt"] == i["title"] == alt for i in imgs)
        return {
            "img": [i["src"] for i in imgs],
            "title": title,
            "alt": alt,
            "author": author,
            "date": string_to_date(date_str, "%B %d, %Y"),
        }


class EveryDayBlues(GenericDeletedComic, GenericNavigableComic):
    """Class to retrieve EveryDayBlues Comics."""

    name = "blues"
    long_name = "Every Day Blues"
    url = "http://everydayblues.net"
    get_first_comic_link = get_a_navi_navifirst
    get_navi_link = get_link_rel_next

    @classmethod
    def get_comic_info(cls, soup, link):
        """Get information about a particular comics."""
        title = soup.find("h2", class_="post-title").string
        author = soup.find("span", class_="post-author").find("a").string
        date_str = soup.find("span", class_="post-date").string
        imgs = soup.find("div", id="comic").find_all("img")
        assert all(i["alt"] == i["title"] == title for i in imgs)
        assert len(imgs) <= 1, imgs
        return {
            "img": [i["src"] for i in imgs],
            "title": title,
            "author": author,
            "date": string_to_date(date_str, "%d. %B %Y", "de_DE.utf8"),
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
        """Get information about a particular comics."""
        title = soup.find("h1", class_="entry-title").string
        author = soup.find("span", class_="author vcard").find("a").string
        date_str = soup.find("span", class_="entry-date").string
        imgs = soup.find("div", id="comic").find_all("img")
        assert all(i["alt"] == i["title"] for i in imgs)
        assert len(imgs) == 1, imgs
        alt = imgs[0]["alt"]
        return {
            "img": [i["src"] for i in imgs],
            "title": title,
            "alt": alt,
            "author": author,
            "date": string_to_date(date_str, "%B %d, %Y"),
        }


class TheAwkwardYeti(GenericNavigableComic):
    """Class to retrieve The Awkward Yeti comics."""

    # Also on http://www.gocomics.com/the-awkward-yeti
    # Also on https://larstheyeti.tumblr.com
    # Also on https://tapas.io/series/TheAwkwardYeti
    name = "yeti"
    long_name = "The Awkward Yeti"
    url = "http://theawkwardyeti.com"
    _categories = ("YETI",)
    get_first_comic_link = simulate_first_link
    first_url = "https://theawkwardyeti.com/comic/0912-reading/"

    @classmethod
    def get_navi_link(cls, last_soup, next_):
        """Get link to next or previous comic."""
        link = last_soup.find("link", rel="next" if next_ else "prev")
        # Workaround because a page leads to 404 error
        if link:
            url = cls.get_url_from_link(link)
            if url == "http://theawkwardyeti.com/comic/change/":
                next_url = "http://theawkwardyeti.com/comic/hypothyroidism/"
                prev_url = "http://theawkwardyeti.com/comic/hyperthyroidism-works/"
                return {"href": next_url if next_ else prev_url}
        return link

    @classmethod
    def get_comic_info(cls, soup, link):
        """Get information about a particular comics."""
        title = soup.find("a", class_="c-blog-title").string
        imgs = soup.find_all("meta", property="og:image")
        return {
            "img": [i["content"] for i in imgs],
            "title": title,
        }


class PleasantThoughts(GenericDeletedComic, GenericNavigableComic):
    """Class to retrieve Pleasant Thoughts comics."""

    name = "pleasant"
    long_name = "Pleasant Thoughts"
    url = "http://pleasant-thoughts.com"
    get_first_comic_link = get_a_navi_navifirst
    get_navi_link = get_link_rel_next

    @classmethod
    def get_comic_info(cls, soup, link):
        """Get information about a particular comics."""
        post = soup.find("div", class_="post-content")
        title = post.find("h2", class_="post-title").string
        imgs = post.find("div", class_="entry").find_all("img")
        return {
            "title": title,
            "img": [i["src"] for i in imgs],
        }


class MisterAndMe(GenericNavigableComic):
    """Class to retrieve Mister & Me Comics."""

    # Also on http://www.gocomics.com/mister-and-me
    # Also on https://tapas.io/series/Mister-and-Me
    name = "mister"
    long_name = "Mister & Me"
    url = "http://www.mister-and-me.com"
    get_first_comic_link = get_a_comicnavbase_comicnavfirst
    get_navi_link = get_link_rel_next

    @classmethod
    def get_comic_info(cls, soup, link):
        """Get information about a particular comics."""
        title = soup.find("h2", class_="post-title").string
        author = soup.find("span", class_="post-author").find("a").string
        date_str = soup.find("span", class_="post-date").string
        imgs = soup.find("div", id="comic").find_all("img")
        assert all(i["alt"] == i["title"] for i in imgs)
        assert len(imgs) <= 1, imgs
        alt = imgs[0]["alt"] if imgs else ""
        return {
            "img": [i["src"] for i in imgs],
            "title": title,
            "alt": alt,
            "author": author,
            "date": string_to_date(date_str, "%B %d, %Y"),
        }


class LastPlaceComics(GenericNavigableComic):
    """Class to retrieve Last Place Comics."""

    name = "lastplace"
    long_name = "Last Place Comics"
    url = "http://lastplacecomics.com"
    get_navi_link = get_a_rel_next
    get_first_comic_link = simulate_first_link
    first_url = "https://lastplacecomics.com/corona-face/"

    @classmethod
    def get_comic_info(cls, soup, link):
        """Get information about a particular comics."""
        title = soup.find("meta", property="og:title")["content"]
        author = soup.find("meta", attrs={"name": "twitter:data1"})["content"]
        date_str = soup.find("meta", property="article:published_time")["content"]
        desc = soup.find("meta", property="og:description")["content"]
        imgs = soup.find_all("meta", property="og:image")
        return {
            "img": [i["content"] for i in imgs],
            "title": title,
            "author": author,
            "description": desc,
            "date": isoformat_to_date(date_str),
        }


class TalesOfAbsurdity(GenericNavigableComic):
    """Class to retrieve Tales Of Absurdity comics."""

    # Also on https://tapas.io/series/Tales-Of-Absurdity
    # Also on http://talesofabsurdity.tumblr.com
    name = "absurdity"
    long_name = "Tales of Absurdity"
    url = "http://talesofabsurdity.com"
    _categories = ("ABSURDITY",)
    get_first_comic_link = get_a_navi_navifirst
    get_navi_link = get_a_navi_comicnavnext_navinext

    @classmethod
    def get_comic_info(cls, soup, link):
        """Get information about a particular comics."""
        title = soup.find("h2", class_="post-title").string
        author = soup.find("span", class_="post-author").find("a").string
        date_str = soup.find("span", class_="post-date").string
        imgs = soup.find("div", id="comic").find_all("img")
        assert all(i["alt"] == i["title"] for i in imgs)
        alt = imgs[0]["alt"] if imgs else ""
        return {
            "img": [i["src"] for i in imgs],
            "title": title,
            "alt": alt,
            "author": author,
            "date": string_to_date(date_str, "%B %d, %Y"),
        }


class EndlessOrigami(GenericDeletedComic):
    """Class to retrieve Endless Origami Comics."""

    name = "origami"
    long_name = "Endless Origami"
    url = "http://endlessorigami.com"


class PlanC(GenericDeletedComic):
    """Class to retrieve Plan C comics."""

    # Also on https://www.webtoons.com/en/challenge/plan-c/list?title_no=77831
    name = "planc"
    long_name = "Plan C"
    url = "http://www.plancomic.com"


class BuniComic(GenericNavigableComic):
    """Class to retrieve Buni Comics."""

    name = "buni"
    long_name = "BuniComics"
    url = "http://www.bunicomic.com"
    get_first_comic_link = get_a_comicnavbase_comicnavfirst
    get_navi_link = get_link_rel_next

    @classmethod
    def get_comic_info(cls, soup, link):
        """Get information about a particular comics."""
        imgs = soup.find("div", id="comic").find_all("img")
        assert all(i["alt"] == i["title"] for i in imgs)
        title = imgs[0]["title"] if imgs else soup.find("title").string
        return {
            "img": [i["src"] for i in imgs],
            "title": title,
        }


class GenericCommitStrip(GenericNavigableComic):
    """Generic class to retrieve Commit Strips in different languages."""

    get_navi_link = get_a_rel_next
    get_first_comic_link = simulate_first_link
    first_url = NotImplemented
    _categories = ("GEEKY",)

    @classmethod
    def get_comic_info(cls, soup, link):
        """Get information about a particular comics."""
        desc = soup.find("meta", property="og:description")["content"]
        title = soup.find("meta", property="og:title")["content"]
        imgs = soup.find("div", class_="entry-content").find_all("img")
        title2 = " ".join(i.get("title", "") for i in imgs)
        return {
            "title": title,
            "title2": title2,
            "description": desc,
            "img": [
                urljoin_wrapper(cls.url, convert_iri_to_plain_ascii_uri(i["src"]))
                for i in imgs
            ],
        }


class CommitStripFr(GenericCommitStrip):
    """Class to retrieve Commit Strips in French."""

    name = "commit_fr"
    long_name = "Commit Strip (Fr)"
    url = "http://www.commitstrip.com/fr"
    _categories = ("FRANCAIS",)
    first_url = "http://www.commitstrip.com/fr/2012/02/22/interview/"


class CommitStripEn(GenericCommitStrip):
    """Class to retrieve Commit Strips in English."""

    name = "commit_en"
    long_name = "Commit Strip (En)"
    url = "http://www.commitstrip.com/en"
    first_url = "http://www.commitstrip.com/en/2012/02/22/interview/"


class GenericBoumerie(GenericNavigableComic):
    """Generic class to retrieve Boumeries comics in different languages."""

    # Also on https://boumeries.tumblr.com
    get_first_comic_link = get_a_navi_navifirst
    get_navi_link = get_link_rel_next
    date_format = NotImplemented
    lang = NotImplemented

    @classmethod
    def get_comic_info(cls, soup, link):
        """Get information about a particular comics."""
        title = soup.find("h2", class_="post-title").string
        short_url = soup.find("link", rel="shortlink")["href"]
        author = soup.find("span", class_="post-author").find("a").string
        date_str = soup.find("span", class_="post-date").string
        imgs = soup.find("div", id="comic").find_all("img")
        assert all(i["alt"] == i["title"] for i in imgs)
        return {
            "short_url": short_url,
            "img": [i["src"] for i in imgs],
            "title": title,
            "author": author,
            "date": string_to_date(date_str, cls.date_format, cls.lang),
        }


class BoumerieEn(GenericBoumerie):
    """Class to retrieve Boumeries comics in English."""

    name = "boumeries_en"
    long_name = "Boumeries (En)"
    url = "http://comics.boumerie.com"
    _categories = ("BOUMERIES",)
    date_format = "%B %d, %Y"
    lang = "en_GB.UTF-8"


class BoumerieFr(GenericBoumerie):
    """Class to retrieve Boumeries comics in French."""

    name = "boumeries_fr"
    long_name = "Boumeries (Fr)"
    url = "http://bd.boumerie.com"
    _categories = ("BOUMERIES", "FRANCAIS")
    date_format = "%d %B %Y"  # Used to be "%A, %d %B %Y", then "%B %d, %Y"
    lang = "fr_FR.utf8"


class UnearthedComics(GenericDeletedComic, GenericNavigableComic):
    """Class to retrieve Unearthed comics."""

    # Also on https://tapas.io/series/UnearthedComics
    # Also on https://unearthedcomics.tumblr.com
    name = "unearthed"
    long_name = "Unearthed Comics"
    url = "http://unearthedcomics.com"
    _categories = ("UNEARTHED",)
    get_navi_link = get_link_rel_next
    get_first_comic_link = simulate_first_link
    first_url = "http://unearthedcomics.com/comics/world-with-turn-signals/"

    @classmethod
    def get_comic_info(cls, soup, link):
        """Get information about a particular comics."""
        short_url = soup.find("link", rel="shortlink")["href"]
        title_elt = soup.find("h1") or soup.find("h2")
        title = title_elt.string if title_elt else ""
        desc = soup.find("meta", property="og:description")
        date_str = soup.find("time", class_="published updated hidden")["datetime"]
        post = soup.find("div", class_="entry content entry-content type-portfolio")
        imgs = post.find_all("img")
        return {
            "title": title,
            "description": desc,
            "url2": short_url,
            "img": [i["src"] for i in imgs],
            "date": string_to_date(date_str, "%Y-%m-%d"),
        }


class Optipess(GenericNavigableComic):
    """Class to retrieve Optipess comics."""

    name = "optipess"
    long_name = "Optipess"
    url = "http://www.optipess.com"
    get_first_comic_link = get_a_navi_navifirst
    get_navi_link = get_link_rel_next

    @classmethod
    def get_comic_info(cls, soup, link):
        """Get information about a particular comics."""
        title = soup.find("h2", class_="post-title").string
        author = soup.find("span", class_="post-author").find("a").string
        comic = soup.find("div", id="comic")
        imgs = comic.find_all("img") if comic else []
        alt = imgs[0]["title"] if imgs else ""
        assert all(i["alt"] == i["title"] == alt for i in imgs)
        date_str = soup.find("span", class_="post-date").string
        return {
            "title": title,
            "alt": alt,
            "author": author,
            "img": [i["src"] for i in imgs],
            "date": string_to_date(date_str, "%B %d, %Y"),
        }


class PainTrainComic(GenericNavigableComic):
    """Class to retrieve Pain Train Comics."""

    # Also on https://paintraincomic.tumblr.com
    name = "paintrain"
    long_name = "Pain Train Comics"
    url = "http://paintraincomic.com"
    get_first_comic_link = get_a_navi_navifirst
    get_navi_link = get_link_rel_next

    @classmethod
    def get_comic_info(cls, soup, link):
        """Get information about a particular comics."""
        title = soup.find("h2", class_="post-title").string
        short_url = soup.find("link", rel="shortlink")["href"]
        short_url_re = re.compile("^%s/\\?p=([0-9]*)" % cls.url)
        num = int(short_url_re.match(short_url).group(1))
        imgs = soup.find("div", id="comic").find_all("img")
        alt = imgs[0]["title"]
        assert all(i["alt"] == i["title"] == alt for i in imgs)
        date_str = soup.find("span", class_="post-date").string
        return {
            "short_url": short_url,
            "num": num,
            "img": [i["src"] for i in imgs],
            "date": string_to_date(date_str, "%d/%m/%Y"),
            "alt": alt,
            "title": title,
        }


class MoonBeard(GenericNavigableComic):
    """Class to retrieve MoonBeard comics."""

    # Also on https://squireseses.tumblr.com
    # Also on http://www.webtoons.com/en/comedy/moon-beard/list?title_no=471
    name = "moonbeard"
    long_name = "Moon Beard"
    url = "https://moonbeard.com"
    _categories = ("MOONBEARD",)
    get_first_comic_link = get_a_navi_navifirst
    get_navi_link = get_a_navi_navinext

    @classmethod
    def get_comic_info(cls, soup, link):
        """Get information about a particular comics."""
        title = soup.find("h2", class_="post-title").string
        short_url = soup.find("link", rel="shortlink")["href"]
        short_url_re = re.compile("^%s/\\?p=([0-9]*)" % cls.url)
        num = int(short_url_re.match(short_url).group(1))
        imgs = soup.find("div", id="comic").find_all("img")
        alt = imgs[0]["title"]
        assert all(i["alt"] == i["title"] == alt for i in imgs)
        date_str = soup.find("span", class_="post-date").string
        tags = " ".join(
            t["content"] for t in soup.find_all("meta", property="article:tag")
        )
        author = soup.find("span", class_="post-author").string
        return {
            "short_url": short_url,
            "num": num,
            "img": [i["src"] for i in imgs],
            "date": string_to_date(date_str, "%B %d, %Y"),
            "title": title,
            "tags": tags,
            "alt": alt,
            "author": author,
        }


class SystemComic(GenericNavigableComic):
    """Class to retrieve System Comic."""

    name = "system"
    long_name = "System Comic"
    url = "http://www.systemcomic.com"
    get_navi_link = get_a_rel_next

    @classmethod
    def get_first_comic_link(cls):
        """Get link to first comics."""
        return get_soup_at_url(cls.url).find("li", class_="first").find("a")

    @classmethod
    def get_comic_info(cls, soup, link):
        """Get information about a particular comics."""
        title = soup.find("meta", property="og:title")["content"]
        desc = soup.find("meta", property="og:description")["content"]
        date_str = soup.find("time")["datetime"]
        imgs = soup.find("figure").find_all("img")
        return {
            "title": title,
            "description": desc,
            "date": string_to_date(date_str, "%Y-%m-%d"),
            "img": [i["src"] for i in imgs],
        }


class LittleLifeLines(GenericNavigableComic):
    """Class to retrieve Little Life Lines comics."""

    # Also on https://little-life-lines.tumblr.com
    name = "life"
    long_name = "Little Life Lines"
    url = "http://www.littlelifelines.com"
    get_url_from_link = join_cls_url_to_href
    get_first_comic_link = simulate_first_link
    first_url = "http://www.littlelifelines.com/comics/well-done"

    @classmethod
    def get_navi_link(cls, last_soup, next_):
        """Get link to next or previous comic."""
        # prev is next / next is prev
        li = last_soup.find("li", class_="prev" if next_ else "next")
        return li.find("a") if li else None

    @classmethod
    def get_comic_info(cls, soup, link):
        """Get information about a particular comics."""
        title = soup.find("meta", property="og:title")["content"]
        desc = soup.find("meta", property="og:description")
        desc_str = "" if desc is None else desc["content"]
        date_str = soup.find("time", class_="published")["datetime"]
        author = soup.find("a", rel="author").string
        div_content = soup.find("div", class_="body entry-content")
        imgs = div_content.find_all("img")
        imgs = [i for i in imgs if i.get("src") is not None]
        alt = imgs[0]["alt"]
        return {
            "title": title,
            "alt": alt,
            "description": desc_str,
            "author": author,
            "date": string_to_date(date_str, "%Y-%m-%d"),
            "img": [i["src"] for i in imgs],
        }


class Jenkins(GenericNavigableComic):
    """Class to retrieve The Jenkins comics."""

    name = "jenkins"
    long_name = "The Jenkins"
    url = "https://thejenkinscomic.wordpress.com"
    get_navi_link = get_a_rel_next
    get_first_comic_link = simulate_first_link
    first_url = "https://thejenkinscomic.wordpress.com/2016/10/15/first-blog-post/"

    @classmethod
    def get_comic_info(cls, soup, link):
        """Get information about a particular comics."""
        title = soup.find("meta", property="og:title")["content"]
        date_str = soup.find("meta", property="article:published_time")["content"]
        imgs = soup.find_all("meta", property="og:image")
        author = soup.find("span", class_="author vcard").find("a").string
        return {
            "title": title,
            "date": isoformat_to_date(date_str),
            "img": [i["content"] for i in imgs],
            "author": author,
        }


class GenericWordPressInkblot(GenericNavigableComic):
    """Generic class to retrieve comics using WordPress with Inkblot."""

    get_navi_link = get_link_rel_next

    @classmethod
    def get_first_comic_link(cls):
        """Get link to first comics."""
        return get_soup_at_url(cls.url).find(
            "a",
            class_="webcomic-link webcomic1-link first-webcomic-link first-webcomic1-link",
        )

    @classmethod
    def get_comic_info(cls, soup, link):
        """Get information about a particular comics."""
        title = soup.find("meta", property="og:title")["content"]
        imgs = soup.find("div", class_="webcomic-image").find_all("img")
        date_str = soup.find("meta", property="article:published_time")["content"]
        return {
            "title": title,
            "date": isoformat_to_date(date_str),
            "img": [i["src"] for i in imgs],
        }


class EverythingsStupid(GenericWordPressInkblot):
    """Class to retrieve Everything's stupid Comics."""

    # Also on https://tapas.io/series/EverythingsStupid
    # Also on http://www.webtoons.com/en/challenge/everythings-stupid/list?title_no=14591
    # Also on http://everythingsstupidcomics.tumblr.com
    name = "stupid"
    long_name = "Everything's Stupid"
    url = "http://everythingsstupid.net"
    get_navi_link = get_a_rel_next


class TheIsmComics(GenericDeletedComic, GenericWordPressInkblot):
    """Class to retrieve The Ism Comics."""

    # Also on https://tapas.io/series/TheIsm (?)
    name = "theism"
    long_name = "The Ism"
    url = "http://www.theism-comics.com"


class WoodenPlankStudios(GenericNavigableComic):
    """Class to retrieve Wooden Plank Studios comics."""

    name = "woodenplank"
    long_name = "Wooden Plank Studios"
    url = "https://www.woodenplankstudios.com"

    @classmethod
    def get_first_comic_link(cls):
        """Get link to first comics."""
        return get_soup_at_url(cls.url).find(
            "a",
            class_="webcomic-link webcomic1-link first-webcomic-link first-webcomic1-link",
        )

    @classmethod
    def get_navi_link(cls, last_soup, next_):
        """Get link to next or previous comic."""
        return last_soup.find(
            "a", class_="webcomic-link webcomic1-link next-webcomic-link next-webcomic1-link" if next_ else "webcomic-link webcomic1-link previous-webcomic-link previous-webcomic1-link"
        )

    @classmethod
    def get_comic_info(cls, soup, link):
        """Get information about a particular comics."""
        title = soup.find("h1").string
        imgs = soup.find("div", class_="webcomic-image").find_all("img")
        return {
            "title": title,
            "img": [i["src"] for i in imgs],
        }


class ElectricBunnyComic(GenericNavigableComic):
    """Class to retrieve Electric Bunny Comics."""

    # Also on http://electricbunnycomics.tumblr.com
    name = "bunny"
    long_name = "Electric Bunny Comic"
    url = "http://www.electricbunnycomics.com/View/Comic/153/Welcome+to+Hell"
    get_url_from_link = join_cls_url_to_href

    @classmethod
    def get_first_comic_link(cls):
        """Get link to first comics."""
        return get_soup_at_url(cls.url).find("img", alt="First").parent

    @classmethod
    def get_navi_link(cls, last_soup, next_):
        """Get link to next or previous comic."""
        img = last_soup.find("img", alt="Next" if next_ else "Back")
        return img.parent if img else None

    @classmethod
    def get_comic_info(cls, soup, link):
        """Get information about a particular comics."""
        title = soup.find("meta", property="og:title")["content"]
        imgs = soup.find_all("meta", property="og:image")
        return {
            "title": title,
            "img": [i["content"] for i in imgs],
        }


class SheldonComics(GenericNavigableComic):
    """Class to retrieve Sheldon comics."""

    # Also on http://www.gocomics.com/sheldon
    name = "sheldon"
    long_name = "Sheldon Comics"
    url = "http://www.sheldoncomics.com"

    @classmethod
    def get_first_comic_link(cls):
        """Get link to first comics."""
        return get_soup_at_url(cls.url).find("a", id="nav-first")

    @classmethod
    def get_navi_link(cls, last_soup, next_):
        """Get link to next or previous comic."""
        for link in last_soup.find_all("a", id="nav-next" if next_ else "nav-prev"):
            if link["href"] != "http://www.sheldoncomics.com":
                return link
        return None

    @classmethod
    def get_comic_info(cls, soup, link):
        """Get information about a particular comics."""
        imgs = soup.find("div", id="comic-foot").find_all("img")
        assert all(i["alt"] == i["title"] for i in imgs)
        assert len(imgs) == 1, imgs
        title = imgs[0]["title"]
        return {
            "title": title,
            "img": [i["src"] for i in imgs],
        }


class ManVersusManatee(GenericComicNotWorking, GenericNavigableComic):
    """Class to retrieve Man Versus Manatee comics."""

    url = "http://manvsmanatee.com"
    name = "manvsmanatee"
    long_name = "Man Versus Manatee"
    get_first_comic_link = get_a_comicnavbase_comicnavfirst
    get_navi_link = get_a_comicnavbase_comicnavnext

    @classmethod
    def get_comic_info(cls, soup, link):
        """Get information about a particular comics."""
        title = soup.find("h2", class_="post-title").string
        imgs = soup.find("div", id="comic").find_all("img")
        date_str = soup.find("span", class_="post-date").string
        return {
            "img": [i["src"] for i in imgs],
            "title": title,
            "date": string_to_date(date_str, "%B %d, %Y"),
        }


class TheMeerkatguy(GenericNavigableComic):
    """Class to retrieve The Meerkatguy comics."""

    long_name = "The Meerkatguy"
    url = "http://www.themeerkatguy.com"
    name = "meerkatguy"
    get_first_comic_link = get_a_comicnavbase_comicnavfirst
    get_navi_link = get_a_comicnavbase_comicnavnext

    @classmethod
    def get_comic_info(cls, soup, link):
        """Get information about a particular comics."""
        title = soup.find("title").string
        imgs = soup.find_all("meta", property="og:image")
        return {
            "img": [i["content"] for i in imgs],
            "title": title,
        }


class Ubertool(GenericNavigableComic):
    """Class to retrieve Ubertool comics."""

    # Also on https://ubertool.tumblr.com
    # Also on https://tapas.io/series/ubertool
    name = "ubertool"
    long_name = "Ubertool"
    url = "http://ubertoolcomic.com"
    _categories = ("UBERTOOL",)
    get_first_comic_link = get_a_comicnavbase_comicnavfirst
    get_navi_link = get_a_comicnavbase_comicnavnext

    @classmethod
    def get_comic_info(cls, soup, link):
        """Get information about a particular comics."""
        title = soup.find("h2", class_="post-title").string
        date_str = soup.find("span", class_="post-date").string
        imgs = soup.find("div", id="comic").find_all("img")
        return {
            "img": [i["src"] for i in imgs],
            "title": title,
            "date": string_to_date(date_str, "%B %d, %Y"),
        }


class ObscureGentlemen(GenericNavigableComic):
    """Class to retrieve The Obscure Gentlemen comics."""

    # Also on https://www.webtoons.com/en/challenge/the-obscure-gentlemen/list?title_no=25110&page=1
    name = "obscuregentlemen"
    long_name = "The Obscure Gentlemen"
    url = "https://theobscuregentlemen.com"
    get_first_comic_link = get_a_comicnavbase_comicnavfirst

    @classmethod
    def get_navi_link(cls, last_soup, next_):
        """Get link to next or previous comic."""
        # Based on get_a_comicnavbase_comicnavnext but with workaround
        link = last_soup.find(
            "a",
            class_="comic-nav-base comic-nav-next"
            if next_
            else "comic-nav-base comic-nav-previous",
        )
        # Workaround because a page leads to 404 error
        if link:
            url = cls.get_url_from_link(link)
            if url == "https://theobscuregentlemen.com/comic/4848/":
                next_url = "https://theobscuregentlemen.com/comic/let-him-win/"
                prev_url = "https://theobscuregentlemen.com/comic/kiss-of-steel/"
                return {"href": next_url if next_ else prev_url}
        return link

    @classmethod
    def get_comic_info(cls, soup, link):
        """Get information about a particular comics."""
        author = soup.find("a", rel="author").string
        title = soup.find("h2", class_="post-title").string
        imgs = soup.find("div", id="comic").find_all("img")
        return {
            "img": [convert_iri_to_plain_ascii_uri(i["src"]) for i in imgs],
            "title": title,
            "author": author,
        }


class EarthExplodes(GenericDeletedComic, GenericNavigableComic):
    """Class to retrieve The Earth Explodes comics."""

    name = "earthexplodes"
    long_name = "The Earth Explodes"
    url = "http://www.earthexplodes.com"
    get_url_from_link = join_cls_url_to_href
    get_first_comic_link = simulate_first_link
    first_url = "http://www.earthexplodes.com/comics/000/"

    @classmethod
    def get_navi_link(cls, last_soup, next_):
        """Get link to next or previous comic."""
        return last_soup.find("a", id="next" if next_ else "prev")

    @classmethod
    def get_comic_info(cls, soup, link):
        """Get information about a particular comics."""
        title = soup.find("title").string
        imgs = soup.find("div", id="image").find_all("img")
        alt = imgs[0].get("title", "")
        return {
            "img": [
                convert_iri_to_plain_ascii_uri(urljoin_wrapper(cls.url, i["src"]))
                for i in imgs
            ],
            "title": title,
            "alt": alt,
        }


class PomComics(GenericNavigableComic):
    """Class to retrieve PomComics."""

    name = "pom"
    long_name = "Pom Comics / Piece of Me"
    url = "http://www.pomcomic.com"
    get_url_from_link = join_cls_url_to_href

    @classmethod
    def get_first_comic_link(cls):
        """Get link to first comics."""
        return get_soup_at_url(cls.url).find("a", class_="btn-first")

    @classmethod
    def get_navi_link(cls, last_soup, next_):
        """Get link to next or previous comic."""
        return last_soup.find("a", class_="btn-next" if next_ else "btn-prev")

    @classmethod
    def get_comic_info(cls, soup, link):
        """Get information about a particular comics."""
        title = soup.find("h1").string
        desc = soup.find("meta", property="og:description")["content"]
        tags = soup.find("meta", attrs={"name": "keywords"})["content"]
        imgs = soup.find("div", class_="comic").find_all("img")
        return {
            "title": title,
            "desc": desc,
            "tags": tags,
            "img": [urljoin_wrapper(cls.url, i["src"]) for i in imgs],
        }


class CubeDrone(GenericComicNotWorking, GenericNavigableComic):  # Website has changed
    """Class to retrieve Cube Drone comics."""

    name = "cubedrone"
    long_name = "Cube Drone"
    url = "http://cube-drone.com/comics"
    get_url_from_link = join_cls_url_to_href

    @classmethod
    def get_first_comic_link(cls):
        """Get link to first comics."""
        return (
            get_soup_at_url(cls.url)
            .find("span", class_="glyphicon glyphicon-backward")
            .parent
        )

    @classmethod
    def get_navi_link(cls, last_soup, next_):
        """Get link to next or previous comic."""
        class_ = "glyphicon glyphicon-chevron-" + ("right" if next_ else "left")
        return last_soup.find("span", class_=class_).parent

    @classmethod
    def get_comic_info(cls, soup, link):
        """Get information about a particular comics."""
        title = soup.find("meta", attrs={"name": "twitter:title"})["content"]
        url2 = soup.find("meta", attrs={"name": "twitter:url"})["content"]
        # date_str = soup.find('h2', class_='comic_title').find('small').string
        # day = string_to_date(date_str, "%B %d, %Y, %I:%M %p")
        imgs = soup.find_all("img", class_="comic img-responsive")
        title2 = imgs[0]["title"]
        alt = imgs[0]["alt"]
        return {
            "url2": url2,
            "title": title,
            "title2": title2,
            "alt": alt,
            "img": [i["src"] for i in imgs],
        }


class MakeItStoopid(GenericDeletedComic, GenericNavigableComic):
    """Class to retrieve Make It Stoopid Comics."""

    name = "stoopid"
    long_name = "Make it stoopid"
    url = "http://makeitstoopid.com/comic.php"

    @classmethod
    def get_nav(cls, soup):
        """Get the navigation elements from soup object."""
        cnav = soup.find_all(class_="cnav")
        nav1, nav2 = cnav[:5], cnav[5:]
        assert nav1 == nav2
        # begin, prev, archive, next_, end = nav1
        return [None if i.get("href") is None else i for i in nav1]

    @classmethod
    def get_first_comic_link(cls):
        """Get link to first comics."""
        return cls.get_nav(get_soup_at_url(cls.url))[0]

    @classmethod
    def get_navi_link(cls, last_soup, next_):
        """Get link to next or previous comic."""
        return cls.get_nav(last_soup)[3 if next_ else 1]

    @classmethod
    def get_comic_info(cls, soup, link):
        """Get information about a particular comics."""
        title = link["title"]
        imgs = soup.find_all("img", id="comicimg")
        return {
            "title": title,
            "img": [i["src"] for i in imgs],
        }


class OffTheLeashDog(GenericNavigableComic):
    """Class to retrieve Off The Leash Dog comics."""

    # Also on https://rupertfawcettsdoggyblog.tumblr.com
    # Also on http://www.rupertfawcettcartoons.com
    name = "offtheleash"
    long_name = "Off The Leash Dog"
    url = "http://offtheleashdogcartoons.com"
    _categories = ("FAWCETT",)
    get_navi_link = get_a_rel_next
    get_first_comic_link = simulate_first_link
    first_url = "http://offtheleashdogcartoons.com/uncategorized/can-i-help-you/"

    @classmethod
    def get_comic_info(cls, soup, link):
        """Get information about a particular comics."""
        title = soup.find("h1", class_="entry-title").string
        imgs = soup.find("div", class_="entry-content").find_all("img")
        return {
            "title": title,
            "img": [i["src"] for i in imgs],
        }


class MacadamValley(GenericDeletedComic, GenericNavigableComic):
    """Class to retrieve Macadam Valley comics."""

    name = "macadamvalley"
    long_name = "Macadam Valley"
    url = "http://macadamvalley.com"
    get_navi_link = get_a_rel_next
    get_first_comic_link = simulate_first_link
    first_url = "http://macadamvalley.com/le-debut-de-la-fin/"

    @classmethod
    def get_comic_info(cls, soup, link):
        """Get information about a particular comics."""
        title = soup.find("h1", class_="entry-title").string
        img = soup.find("div", class_="entry-content").find("img")
        date_str = soup.find("time", class_="entry-date")["datetime"]
        author = soup.find("a", rel="author").string
        return {
            "title": title,
            "img": [i["src"] for i in [img]],
            "date": isoformat_to_date(date_str),
            "author": author,
        }


class WorkChroniclesComics(GenericNavigableComic):
    """Class to retrieve Work Chronicles Comics."""

    name = 'workchronicles'
    long_name = 'Work Chronicles'
    url = 'https://workchronicles.com/comics/'
    get_navi_link = get_a_rel_next
    get_first_comic_link = simulate_first_link
    first_url = "https://workchronicles.com/we-need-innovative-features/"

    @classmethod
    def get_comic_info(cls, soup, link):
        """Get information about a particular comics."""
        title = soup.find("meta", property="og:title")["content"]
        date_str = soup.find("meta", property="article:published_time")["content"]
        imgs = soup.find_all("meta", property="og:image")
        return {
            "img": [i["content"] for i in imgs],
            "date": isoformat_to_date(date_str),
            "title": title,
        }


class LightRoastComics(GenericNavigableComic):
    """Class to retrieve Light Roast Comics."""

    # Also on https://tapas.io/series/Light-Roast-Comics
    # Also on https://www.webtoons.com/en/challenge/light-roast-comics/list?title_no=171110&page=1
    # Also on https://www.instagram.com/lightroastcomics/?hl=fr
    name = "lightroast"
    long_name = "Light Roast Comics"
    url = "http://lightroastcomics.com"
    get_navi_link = get_link_rel_next
    get_first_comic_link = simulate_first_link
    first_url = "http://lightroastcomics.com/oh-thats-why"
    _categories = ("LIGHTROAST",)

    @classmethod
    def get_comic_info(cls, soup, link):
        """Get information about a particular comics."""
        imgs = soup.find_all("meta", property="og:image")
        date_str = soup.find("meta", property="article:published_time")["content"]
        title = soup.find("meta", property="og:title")["content"]
        author = soup.find("span", class_="author vcard").find("a").string
        return {
            "img": [i["content"] for i in imgs],
            "date": isoformat_to_date(date_str),
            "title": title,
            "author": author,
            "tags": " ".join(t.string for t in soup.find_all("a", rel="category tag")),
        }


class MarketoonistComics(GenericNavigableComic):
    """Class to retrieve Marketoonist Comics."""

    name = "marketoonist"
    long_name = "Marketoonist"
    url = "https://marketoonist.com/cartoons"
    get_first_comic_link = simulate_first_link
    get_navi_link = get_link_rel_next
    first_url = "https://marketoonist.com/2002/10/the-8-types-of-brand-managers-2.html"

    @classmethod
    def get_comic_info(cls, soup, link):
        """Get information about a particular comics."""
        imgs = soup.find_all("meta", property="og:image")
        date_str = soup.find("meta", property="article:published_time")["content"]
        title = soup.find("meta", property="og:title")["content"]
        return {
            "img": [i["content"] for i in imgs],
            "date": isoformat_to_date(date_str),
            "title": title,
        }


class ConsoliaComics(GenericNavigableComic):
    """Class to retrieve Consolia comics."""

    name = "consolia"
    long_name = "consolia"
    url = "https://consolia-comic.com"
    get_url_from_link = join_cls_url_to_href

    @classmethod
    def get_first_comic_link(cls):
        """Get link to first comics."""
        return get_soup_at_url(cls.url).find("a", class_="first")

    @classmethod
    def get_navi_link(cls, last_soup, next_):
        """Get link to next or previous comic."""
        return last_soup.find("a", class_="next" if next_ else "prev")

    @classmethod
    def get_comic_info(cls, soup, link):
        """Get information about a particular comics."""
        title = soup.find("meta", property="og:title")["content"]
        date_str = soup.find("time")["datetime"]
        imgs = soup.find_all("meta", property="og:image")
        return {
            "title": title,
            "img": [i["content"] for i in imgs],
            "date": string_to_date(date_str, "%Y-%m-%d"),
        }


class GenericBlogspotComic(GenericNavigableComic):
    """Generic class to retrieve comics from Blogspot."""

    get_first_comic_link = simulate_first_link
    first_url = NotImplemented
    _categories = ("BLOGSPOT",)

    @classmethod
    def get_navi_link(cls, last_soup, next_):
        """Get link to next or previous comic."""
        return last_soup.find(
            "a",
            id="Blog1_blog-pager-newer-link"
            if next_
            else "Blog1_blog-pager-older-link",
        )


class TuMourrasMoinsBete(GenericBlogspotComic):
    """Class to retrieve Tu Mourras Moins Bete comics."""

    name = "mourrasmoinsbete"
    long_name = "Tu Mourras Moins Bete"
    url = "http://tumourrasmoinsbete.blogspot.fr"
    _categories = ("FRANCAIS",)
    first_url = "http://tumourrasmoinsbete.blogspot.fr/2008/06/essai.html"

    @classmethod
    def get_comic_info(cls, soup, link):
        """Get information about a particular comics."""
        title = soup.find("title").string
        imgs = soup.find("div", itemprop="description articleBody").find_all("img")
        author = soup.find("span", itemprop="author").string
        return {
            "img": [i["src"] for i in imgs],
            "author": author,
            "title": title,
        }


class Octopuns(GenericBlogspotComic):
    """Class to retrieve Octopuns comics."""

    # Also on http://octopuns.tumblr.com
    name = "octopuns"
    long_name = "Octopuns"
    url = "http://www.octopuns.net"  # or http://octopuns.blogspot.fr/
    first_url = "http://octopuns.blogspot.com/2010/12/17122010-always-read-label.html"

    @classmethod
    def get_comic_info(cls, soup, link):
        """Get information about a particular comics."""
        title = soup.find("h3", class_="post-title entry-title").string
        date_str = soup.find("h2", class_="date-header").string
        imgs = soup.find_all("link", rel="image_src")
        return {
            "img": [i["href"] for i in imgs],
            "title": title,
            "date": string_to_date(date_str, "%A, %B %d, %Y"),
        }


class GeekAndPoke(GenericNavigableComic):
    """Class to retrieve Geek And Poke comics."""

    name = "geek"
    long_name = "Geek And Poke"
    url = "http://geek-and-poke.com"
    _categories = ("GEEKY",)
    get_url_from_link = join_cls_url_to_href
    get_first_comic_link = simulate_first_link
    first_url = "http://geek-and-poke.com/geekandpoke/2006/8/27/a-new-place-for-a-not-so-old-blog.html"

    @classmethod
    def get_navi_link(cls, last_soup, next_):
        """Get link to next or previous comic."""
        return last_soup.find("a", class_="prev-item" if next_ else "next-item")

    @classmethod
    def get_comic_info(cls, soup, link):
        """Get information about a particular comics."""
        title = soup.find("meta", property="og:title")["content"]
        desc = soup.find("meta", property="og:description")
        desc_str = "" if desc is None else desc["content"]
        date_str = soup.find("time", class_="published")["datetime"]
        author = soup.find("a", rel="author").string
        div_content = soup.find("div", class_="body entry-content") or soup.find(
            "div", class_="special-content"
        )
        imgs = div_content.find_all("img")
        imgs = [i for i in imgs if i.get("src") is not None]
        assert all("title" not in i or i["alt"] == i["title"] for i in imgs)
        alt = imgs[0].get("alt", "") if imgs else []
        return {
            "title": title,
            "alt": alt,
            "description": desc_str,
            "author": author,
            "date": string_to_date(date_str, "%Y-%m-%d"),
            "img": [urljoin_wrapper(cls.url, i["src"]) for i in imgs],
        }


class GloryOwlComix(GenericBlogspotComic):
    """Class to retrieve Glory Owl comics."""

    name = "gloryowl"
    long_name = "Glory Owl"
    url = "http://gloryowlcomix.blogspot.fr"
    _categories = ("NSFW", "FRANCAIS")
    first_url = "http://gloryowlcomix.blogspot.fr/2013/02/1_7.html"

    @classmethod
    def get_comic_info(cls, soup, link):
        """Get information about a particular comics."""
        title = soup.find("title").string
        imgs = soup.find_all("link", rel="image_src")
        author = soup.find("a", rel="author").string
        return {
            "img": [i["href"] for i in imgs],
            "author": author,
            "title": title,
        }


class AtRandomComics(GenericNavigableComic):
    """Class to retrieve At Random Comics."""

    name = "atrandom"
    long_name = "At Random Comics"
    url = "http://www.atrandomcomics.com"
    first_url = (
        "http://www.atrandomcomics.com/at-random-comics-home/2015/5/5/can-of-worms"
    )
    get_url_from_link = join_cls_url_to_href
    get_first_comic_link = simulate_first_link

    @classmethod
    def get_navi_link(cls, last_soup, next_):
        """Get link to next or previous comic."""
        li = last_soup.find("li", class_="prev" if next_ else "next")
        return li.find("a") if li else None

    @classmethod
    def get_comic_info(cls, soup, link):
        """Get information about a particular comics."""
        title = soup.find("meta", property="og:title")["content"]
        desc = soup.find("meta", property="og:description")
        description = desc["content"] if desc else ""
        date_str = soup.find("time", itemprop="datePublished")["datetime"]
        author = soup.find("a", rel="author").string
        imgs = soup.find_all("meta", property="og:image")
        return {
            "title": title,
            "img": [i["content"] for i in imgs],
            "date": string_to_date(date_str, "%Y-%m-%d"),
            "author": author,
            "description": description,
        }


class NothingSuspicious(GenericDeletedComic, GenericNavigableComic):
    """Class to retrieve Nothing Suspicious comics."""

    name = "nothingsuspicious"
    long_name = "Nothing Suspicious"
    url = "https://nothingsuspicio.us"
    first_url = "https://nothingsuspicio.us/comic/0001-automatic-faucets"
    get_url_from_link = join_cls_url_to_href
    get_first_comic_link = simulate_first_link

    @classmethod
    def get_navi_link(cls, last_soup, next_):
        """Get link to next or previous comic."""
        nav = last_soup.find("nav", class_="pagination")
        links = nav.find_all("a")
        expected_string = "Prev" if next_ else "Next"
        for link in links:
            if link.string == expected_string:
                return link
        return None

    @classmethod
    def get_comic_info(cls, soup, link):
        """Get information about a particular comics."""
        title = soup.find("meta", property="og:title")["content"]
        date_str = soup.find("meta", itemprop="datePublished")["content"]
        author = soup.find("meta", itemprop="author")["content"]
        imgs = soup.find_all("meta", property="og:image")
        return {
            "title": title,
            "img": [i["content"] for i in imgs],
            "date": isoformat_to_date(date_str),
            "author": author,
        }


class DeathBulge(GenericNumberedComic):
    """Class to retrieve the DeathBulge comics."""

    name = "deathbulge"
    long_name = "Death Bulge"
    url = "http://www.deathbulge.com"

    @classmethod
    def get_comic_info(cls, num):
        json_url = urljoin_wrapper(cls.url, "api/comics/%d" % num)
        json = load_json_at_url(json_url)
        pagination = json["pagination_links"]
        comic_json = json["comic"]
        return {
            "json_url": json_url,
            "url": urljoin_wrapper(cls.url, "comics/%d" % num),
            "alt": comic_json["alt_text"],
            "title": comic_json["title"],
            "img": [urljoin_wrapper(cls.url, comic_json["comic"])],
            "date": isoformat_to_date(comic_json["timestamp"]),
        }

    @classmethod
    def get_first_and_last_numbers(cls):
        """Get index of first and last available comics (as a tuple of int)."""
        json_url = urljoin_wrapper(cls.url, "api/comics/1")
        json = load_json_at_url(json_url)
        pagination = json["pagination_links"]
        return pagination["first"], pagination["last"]


class Ptbd(GenericComic):
    "Class to retrieve Pretends to be drawing comics." ""
    # Also on https://tapas.io/series/ptbd
    # Also on https://www.webtoons.com/en/challenge/pretends-to-be-drawing/list?title_no=109952
    # Also on https://www.instagram.com/pretendstobedrawing/
    name = "ptbd"
    long_name = "Pretends to be drawing"
    url = "https://ptbd.jwels.berlin"
    _categories = ("PTBD",)

    @classmethod
    def get_next_comic(cls, last_comic):
        """Generator to get the next comic. Implementation of GenericComic's abstract method."""
        json_url = urljoin_wrapper(cls.url, "feed/json/")
        json = load_json_at_url(json_url)
        first_num = last_comic["num"] if last_comic else 0
        for comic_json in json["items"]:
            if comic_json["id"] > first_num:
                comic = cls.get_comic_info(comic_json)
                if comic is not None:
                    yield comic

    @classmethod
    def get_comic_info(cls, comic_json):
        """Get information about a particular comics."""
        # print(comic_json)
        return {
            "url": comic_json["url"],
            "title": comic_json["title"],
            "author": comic_json["author"]["name"],
            "img": [comic_json["image"]],
            "date": isoformat_to_date(comic_json["date_modified"]),
            "description": comic_json["content_html"],  # TODO: to be decoded
            "num": comic_json["id"],
        }


class GenericTumblrV1(GenericPaginatedListableComic):
    """Generic class to retrieve comics from Tumblr using the V1 API."""

    _categories = ("TUMBLR",)

    @classmethod
    def check_url(cls, url):
        if not url.startswith(cls.url):
            print("url '%s' does not start with '%s'" % (url, cls.url))
        return url

    @classmethod
    def get_api_url(cls):
        return urljoin_wrapper(cls.url, "/api/read/")

    @classmethod
    def get_api_url_for_id(cls, tumblr_id):
        return cls.get_api_url() + "?id=%d" % (tumblr_id)

    @classmethod
    def get_comic_info(cls, elt):
        """Get information about a particular comics."""
        type_ = elt["type"].lower()
        if type_ != "photo":
            return None
        tumblr_id = int(elt["id"])
        api_url = cls.get_api_url_for_id(tumblr_id)
        caption = elt.find("photo-caption")
        title = caption.string if caption else ""
        tags = " ".join(t.string for t in elt.find_all("tag"))
        # Photos may appear in 'photo' tags and/or straight in the element
        photo_tags = elt.find_all("photo")
        if not photo_tags:
            photo_tags = [elt]
        # Images are in multiple resolutions - taking the first one
        imgs = [photo.find("photo-url") for photo in photo_tags]
        return {
            "url": cls.check_url(elt["url"]),
            "url2": elt["url-with-slug"],
            "date": datetime.datetime.fromtimestamp(int(elt["unix-timestamp"])).date(),
            "title": title,
            "tags": tags,
            "img": [i.string for i in imgs],
            "tumblr-id": tumblr_id,
            "api_url": api_url,
        }

    @classmethod
    def last_comic_is_valid(cls, last_comic):
        """Check that last comic seems to be valid."""
        # Sometimes, tumblr posts are deleted. When previous post is deleted, we
        # might end up spending a lot of time looking for something that
        # doesn't exist. Failing early and clearly might be a better option.
        assert last_comic is not None
        cls.check_url(last_comic["api_url"])
        last_api_url = cls.get_api_url_for_id(last_comic["tumblr-id"])
        try:
            get_soup_at_url(last_api_url)
        except urllib.error.HTTPError:
            try:
                get_soup_at_url(cls.url)
            except urllib.error.HTTPError:
                print("Did not find previous post nor main url %s" % cls.url)
            else:
                print(
                    "Did not find previous post %s : it might have been deleted"
                    % last_api_url
                )
            return False

    @classmethod
    def archive_element_corresponds_to_comic(cls, elt, comic):
        return comic is not None and comic["tumblr-id"] == int(elt["id"])

    @classmethod
    def yield_archive_elements(cls):
        """Yield archive elements from newer to older.

        Elements are retrieved as per the tumblr v1 api."""
        nb_post_per_call = 10  # max 50
        api_url = cls.get_api_url()
        soup = get_soup_at_url(api_url)
        posts = soup.find("posts")
        if posts is None:
            cls.log(
                "Could not get post info from url %s - problem with GDPR disclaimer?"
                % api_url
            )
            return

        start, total = int(posts["start"]), int(posts["total"])
        assert start == 0
        for starting_num in range(0, total, nb_post_per_call):
            api_url2 = api_url + "?start=%d&num=%d" % (starting_num, nb_post_per_call)
            posts2 = get_soup_at_url(api_url2).find("posts")
            start2, total2 = int(posts2["start"]), int(posts2["total"])
            assert starting_num == start2, "%d != %d" % (starting_num, start2)
            # This may happen and should be handled in the future
            assert total == total2, "%d != %d" % (total, total2)
            for e in posts2.find_all("post"):
                yield e


class GenericDeletedTumblrV1(GenericDeletedComic, GenericTumblrV1):
    """Generic class for deleted tumblrs.

    It can be useful to check that the comic is indeed still deleted."""

    _categories = ("DELETEDTUMBLR",)

    @classmethod
    def url_is_reachable(cls, url):
        "Check if a given url is reachable. Return True or False."""
        try:
            get_soup_at_url(url)
            return True
        except urllib.error.HTTPError:
            return False
        except urllib.error.URLError:
            return False

    @classmethod
    def check_urls(cls, last_comic):
        """Check if URLs are reachable. Log something if they are."""
        urls = [cls.url]
        if last_comic is not None:
            urls.append(last_comic["api_url"])
            urls.append(last_comic["url"])
        for url in urls:
            if cls.url_is_reachable(url):
                print(
                    "Tumblr is expected to be deleted but URL %s is reachable" % (url)
                )

    @classmethod
    def get_next_comic(cls, last_comic):
        """Implementation of get_next_comic returning no comics."""
        if PERFORM_CHECK:
            cls.check_urls(last_comic)
        cls.log("comic is considered as empty - returning no comic")
        return []


class SaturdayMorningBreakfastCerealTumblr(GenericTumblrV1):
    """Class to retrieve Saturday Morning Breakfast Cereal comics."""

    # Also on http://www.gocomics.com/saturday-morning-breakfast-cereal
    # Also on http://www.smbc-comics.com
    name = "smbc-tumblr"
    long_name = "Saturday Morning Breakfast Cereal (from Tumblr)"
    url = "https://smbc-comics.tumblr.com"
    _categories = ("SMBC",)


class AHammADay(GenericTumblrV1):  # Seems to be empty
    """Class to retrieve class A Hamm A Day comics."""

    name = "hamm"
    long_name = "A Hamm A Day"
    url = "http://www.ahammaday.com"


class IrwinCardozo(GenericTumblrV1):
    """Class to retrieve Irwin Cardozo Comics."""

    name = "irwinc"
    long_name = "Irwin Cardozo"
    url = "https://irwincardozocomics.tumblr.com"


class AccordingToDevin(GenericTumblrV1):
    """Class to retrieve According To Devin comics."""

    name = "devin"
    long_name = "According To Devin"
    url = "https://accordingtodevin.tumblr.com"


class ItsTheTieTumblr(GenericTumblrV1):
    """Class to retrieve It's the tie comics."""

    # Also on http://itsthetie.com
    # Also on https://tapas.io/series/itsthetie
    name = "tie-tumblr"
    long_name = "It's the tie (from Tumblr)"
    url = "https://itsthetie.tumblr.com"
    _categories = ("TIE",)


class OctopunsTumblr(GenericDeletedTumblrV1):
    """Class to retrieve Octopuns comics."""

    # Also on http://www.octopuns.net
    name = "octopuns-tumblr"
    long_name = "Octopuns (from Tumblr)"
    url = "http://octopuns.tumblr.com"


class PicturesInBoxesTumblr(GenericComicNotWorking, GenericTumblrV1):
    """Class to retrieve Pictures In Boxes comics."""

    # Also on http://www.picturesinboxes.com
    # Also on https://www.gocomics.com/pictures-in-boxes
    name = "picturesinboxes-tumblr"
    long_name = "Pictures in Boxes (from Tumblr)"
    url = "https://picturesinboxescomic.tumblr.com"
    _categories = ("PICTURESINBOXES",)


class TubeyToonsTumblr(GenericTumblrV1):
    """Class to retrieve TubeyToons comics."""

    # Also on https://tapas.io/series/Tubey-Toons
    # Also on http://tubeytoons.com
    name = "tubeytoons-tumblr"
    long_name = "Tubey Toons (from Tumblr)"
    url = "https://tubeytoons.tumblr.com"
    _categories = ("TUBEYTOONS",)


class UnearthedComicsTumblr(GenericTumblrV1):
    """Class to retrieve Unearthed comics."""

    # Also on https://tapas.io/series/UnearthedComics
    # Also on http://unearthedcomics.com
    name = "unearthed-tumblr"
    long_name = "Unearthed Comics (from Tumblr)"
    url = "https://unearthedcomics.tumblr.com"
    _categories = ("UNEARTHED",)


class PieComic(GenericTumblrV1):
    """Class to retrieve Pie Comic comics."""

    name = "pie"
    long_name = "Pie Comic"
    url = "https://piecomic.tumblr.com"


class MrEthanDiamond(GenericTumblrV1):
    """Class to retrieve Mr Ethan Diamond comics."""

    name = "diamond"
    long_name = "Mr Ethan Diamond"
    url = "https://mrethandiamond.tumblr.com"


class Flocci(GenericTumblrV1):
    """Class to retrieve floccinaucinihilipilification comics."""

    name = "flocci"
    long_name = "floccinaucinihilipilification"
    url = "https://floccinaucinihilipilificationa.tumblr.com"


class UpAndOut(GenericTumblrV1):
    """Class to retrieve Up & Out comics."""

    # Also on https://tapas.io/series/UP-and-OUT
    name = "upandout"
    long_name = "Up And Out (from Tumblr)"
    url = "https://upandoutcomic.tumblr.com"


class Pundemonium(GenericTumblrV1):
    """Class to retrieve Pundemonium comics."""

    name = "pundemonium"
    long_name = "Pundemonium"
    url = "https://monstika.tumblr.com"


class PoorlyDrawnLinesTumblr(GenericTumblrV1):
    """Class to retrieve Poorly Drawn Lines comics."""

    # Also on http://poorlydrawnlines.com
    name = "poorlydrawn-tumblr"
    long_name = "Poorly Drawn Lines (from Tumblr)"
    url = "https://pdlcomics.tumblr.com"
    _categories = ("POORLYDRAWN",)


class PearShapedComics(GenericTumblrV1):
    """Class to retrieve Pear Shaped Comics."""

    name = "pearshaped"
    long_name = "Pear-Shaped Comics"
    url = "https://pearshapedcomics.com"


class PondScumComics(GenericTumblrV1):
    """Class to retrieve Pond Scum Comics."""

    name = "pond"
    long_name = "Pond Scum"
    url = "https://pondscumcomic.tumblr.com"


class MercworksTumblr(GenericTumblrV1):
    """Class to retrieve Mercworks comics."""

    # Also on http://mercworks.net
    # Also on http://www.webtoons.com/en/comedy/mercworks/list?title_no=426
    # Also on https://tapas.io/series/MercWorks
    name = "mercworks-tumblr"
    long_name = "Mercworks (from Tumblr)"
    url = "https://mercworks.tumblr.com"
    _categories = ("MERCWORKS",)


class OwlTurdTumblr(GenericTumblrV1):
    """Class to retrieve Owl Turd / Shen comix."""

    # Also on https://tapas.io/series/Shen-Comix
    # Also on http://shencomix.com
    # Also on https://www.gocomics.com/shen-comix
    name = "owlturd-tumblr"
    long_name = "Owl Turd / Shen Comix (from Tumblr)"
    url = "https://shencomix.tumblr.com"
    _categories = ("OWLTURD", "SHENCOMIX")


class VectorBelly(GenericTumblrV1):
    """Class to retrieve Vector Belly comics."""

    # Also on http://vectorbelly.com
    name = "vector"
    long_name = "Vector Belly"
    url = "https://vectorbelly.tumblr.com"


class GoneIntoRapture(GenericTumblrV1):
    """Class to retrieve Gone Into Rapture comics."""

    # Also on http://goneintorapture.tumblr.com
    # Also on https://tapas.io/series/Goneintorapture
    name = "rapture"
    long_name = "Gone Into Rapture"
    url = "https://goneintorapture.com"


class TheOatmealTumblr(GenericTumblrV1):
    """Class to retrieve The Oatmeal comics."""

    # Also on http://theoatmeal.com
    name = "oatmeal-tumblr"
    long_name = "The Oatmeal (from Tumblr)"
    url = "https://oatmeal.tumblr.com"


class HeckIfIKnowComicsTumblr(GenericDeletedTumblrV1):
    """Class to retrieve Heck If I Know Comics."""

    # Also on https://tapas.io/series/Regular
    name = "heck-tumblr"
    long_name = "Heck if I Know comics (from Tumblr)"
    url = "https://heckifiknowcomics.com"


class MyJetPack(GenericTumblrV1):
    """Class to retrieve My Jet Pack comics."""

    name = "jetpack"
    long_name = "My Jet Pack"
    url = "https://myjetpack.tumblr.com"


class CheerUpEmoKidTumblr(GenericTumblrV1):
    """Class to retrieve CheerUpEmoKid comics."""

    # Also on http://www.cheerupemokid.com
    # Also on https://tapas.io/series/CUEK
    name = "cuek-tumblr"
    long_name = "Cheer Up Emo Kid (from Tumblr)"
    url = "https://enzocomics.tumblr.com"


class ForLackOfABetterComic(GenericDeletedTumblrV1):
    """Class to retrieve For Lack Of A Better Comics."""

    # Also on http://forlackofabettercomic.com
    name = "lack"
    long_name = "For Lack Of A Better Comic"
    url = "https://forlackofabettercomic.tumblr.com"


class ZenPencilsTumblr(GenericTumblrV1):
    """Class to retrieve ZenPencils comics."""

    # Also on http://zenpencils.com
    # Also on http://www.gocomics.com/zen-pencils
    name = "zenpencils-tumblr"
    long_name = "Zen Pencils (from Tumblr)"
    url = "https://zenpencils.tumblr.com"
    _categories = ("ZENPENCILS",)


class ThreeWordPhraseTumblr(GenericTumblrV1):
    """Class to retrieve Three Word Phrase comics."""

    # Also on http://threewordphrase.com
    name = "threeword-tumblr"
    long_name = "Three Word Phrase (from Tumblr)"
    url = "https://threewordphrase.tumblr.com"


class TimeTrabbleTumblr(GenericTumblrV1):
    """Class to retrieve Time Trabble comics."""

    # Also on http://timetrabble.com
    name = "timetrabble-tumblr"
    long_name = "Time Trabble (from Tumblr)"
    url = "https://timetrabble.tumblr.com"


class SafelyEndangeredTumblr(GenericDeletedTumblrV1):
    """Class to retrieve Safely Endangered comics."""

    # Also on https://www.safelyendangered.com
    name = "endangered-tumblr"
    long_name = "Safely Endangered (from Tumblr)"
    url = "https://tumblr.safelyendangered.com"


class MouseBearComedyTumblr(GenericTumblrV1):
    """Class to retrieve Mouse Bear Comedy comics."""

    # Also on http://www.mousebearcomedy.com/category/comics/
    name = "mousebear-tumblr"
    long_name = "Mouse Bear Comedy (from Tumblr)"
    url = "https://mousebearcomedy.tumblr.com"


class BouletCorpTumblr(GenericTumblrV1):
    """Class to retrieve BouletCorp comics."""

    # Also on http://www.bouletcorp.com
    name = "boulet-tumblr"
    long_name = "Boulet Corp (from Tumblr)"
    url = "https://bouletcorp.tumblr.com"
    _categories = ("BOULET",)


class TheAwkwardYetiTumblr(GenericTumblrV1):
    """Class to retrieve The Awkward Yeti comics."""

    # Also on http://www.gocomics.com/the-awkward-yeti
    # Also on http://theawkwardyeti.com
    # Also on https://tapas.io/series/TheAwkwardYeti
    name = "yeti-tumblr"
    long_name = "The Awkward Yeti (from Tumblr)"
    url = "https://larstheyeti.tumblr.com"
    _categories = ("YETI",)


class NellucNhoj(GenericTumblrV1):
    """Class to retrieve NellucNhoj comics."""

    name = "nhoj"
    long_name = "Nelluc Nhoj"
    url = "https://nellucnhoj.com"


class DownTheUpwardSpiralTumblr(GenericTumblrV1):
    """Class to retrieve Down The Upward Spiral comics."""

    # Also on https://tapas.io/series/Down-the-Upward-Spiral
    name = "spiral-tumblr"
    long_name = "Down the Upward Spiral (from Tumblr)"
    url = "https://downtheupwardspiral.com"


class AsPerUsualTumblr(GenericTumblrV1):
    """Class to retrieve As Per Usual comics."""

    # Also on https://tapas.io/series/AsPerUsual
    name = "usual-tumblr"
    long_name = "As Per Usual (from Tumblr)"
    url = "https://as-per-usual.tumblr.com"
    _categories = ("DAMILEE",)


class HotComicsForCoolPeopleTumblr(GenericTumblrV1):
    """Class to retrieve Hot Comics For Cool People."""

    # Also on https://tapas.io/series/Hot-Comics-For-Cool-People
    # Also on http://hotcomics.biz (links to tumblr)
    # Also on http://hcfcp.com (links to tumblr)
    name = "hotcomics-tumblr"
    long_name = "Hot Comics For Cool People (from Tumblr)"
    url = "https://hotcomicsforcoolpeople.tumblr.com"
    _categories = ("DAMILEE",)


class OneOneOneOneComicTumblr(GenericTumblrV1):
    """Class to retrieve 1111 Comics."""

    # Also on http://www.1111comics.me
    # Also on https://tapas.io/series/1111-Comics
    name = "1111-tumblr"
    long_name = "1111 Comics (from Tumblr)"
    url = "https://comics1111.tumblr.com"
    _categories = ("ONEONEONEONE",)


class JhallComicsTumblr(GenericTumblrV1):
    """Class to retrieve Jhall Comics."""

    # Also on http://jhallcomics.com
    name = "jhall-tumblr"
    long_name = "Jhall Comics (from Tumblr)"
    url = "https://jhallcomics.tumblr.com"


class BerkeleyMewsTumblr(GenericTumblrV1):
    """Class to retrieve Berkeley Mews comics."""

    # Also on http://www.gocomics.com/berkeley-mews
    # Also on http://www.berkeleymews.com
    name = "berkeley-tumblr"
    long_name = "Berkeley Mews (from Tumblr)"
    url = "https://mews.tumblr.com"
    _categories = ("BERKELEY",)


class JoanCornellaTumblr(GenericTumblrV1):
    """Class to retrieve Joan Cornella comics."""

    # Also on http://joancornella.net
    name = "cornella-tumblr"
    long_name = "Joan Cornella (from Tumblr)"
    url = "https://cornellajoan.tumblr.com"


class RespawnComicTumblr(GenericTumblrV1):
    """Class to retrieve Respawn Comic."""

    # Also on http://respawncomic.com
    # Also on https://tapas.io/series/respawncomic
    name = "respawn-tumblr"
    long_name = "Respawn Comic (from Tumblr)"
    url = "https://respawncomic.tumblr.com"
    _categories = ("RESPAWN",)


class ChrisHallbeckTumblr(GenericTumblrV1):
    """Class to retrieve Chris Hallbeck comics."""

    # Also on https://tapas.io/ChrisHallbeck
    # Also on http://maximumble.com
    # Also on http://minimumble.com
    # Also on http://thebookofbiff.com
    name = "hallbeck-tumblr"
    long_name = "Chris Hallback (from Tumblr)"
    url = "https://chrishallbeck.tumblr.com"
    _categories = ("HALLBACK",)


class ComicNuggets(GenericTumblrV1):
    """Class to retrieve Comic Nuggets."""

    name = "nuggets"
    long_name = "Comic Nuggets"
    url = "https://comicnuggets.com"


class PigeonGazetteTumblr(GenericTumblrV1):
    """Class to retrieve The Pigeon Gazette comics."""

    # Also on https://tapas.io/series/The-Pigeon-Gazette
    name = "pigeon-tumblr"
    long_name = "The Pigeon Gazette (from Tumblr)"
    url = "https://thepigeongazette.tumblr.com"


class CancerOwl(GenericTumblrV1):
    """Class to retrieve Cancer Owl comics."""

    # Also on http://cancerowl.com
    name = "cancerowl-tumblr"
    long_name = "Cancer Owl (from Tumblr)"
    url = "https://cancerowl.tumblr.com"


class FowlLanguageTumblr(GenericTumblrV1):
    """Class to retrieve Fowl Language comics."""

    # Also on http://www.fowllanguagecomics.com
    # Also on https://tapas.io/series/Fowl-Language-Comics
    # Also on http://www.gocomics.com/fowl-language
    name = "fowllanguage-tumblr"
    long_name = "Fowl Language Comics (from Tumblr)"
    url = "https://fowllanguagecomics.tumblr.com"
    _categories = ("FOWLLANGUAGE",)


class TheOdd1sOutTumblr(GenericTumblrV1):
    """Class to retrieve The Odd 1s Out comics."""

    # Also on http://theodd1sout.com
    # Also on https://tapas.io/series/Theodd1sout
    name = "theodd-tumblr"
    long_name = "The Odd 1s Out (from Tumblr)"
    url = "https://theodd1sout.tumblr.com"


class TheUnderfoldTumblr(GenericDeletedTumblrV1):
    """Class to retrieve The Underfold comics."""

    # Also on http://theunderfold.com
    name = "underfold-tumblr"
    long_name = "The Underfold (from Tumblr)"
    url = "http://theunderfold.tumblr.com"


class LolNeinTumblr(GenericTumblrV1):
    """Class to retrieve Lol Nein comics."""

    # Also on http://lolnein.com
    name = "lolnein-tumblr"
    long_name = "Lol Nein (from Tumblr)"
    url = "https://lolnein.tumblr.com"


class FatAwesomeComicsTumblr(GenericTumblrV1):
    """Class to retrieve Fat Awesome Comics."""

    # Also on http://fatawesome.com/comics
    name = "fatawesome-tumblr"
    long_name = "Fat Awesome (from Tumblr)"
    url = "https://fatawesomecomedy.tumblr.com"


class TheWorldIsFlatTumblr(GenericTumblrV1):
    """Class to retrieve The World Is Flat Comics."""

    # Also on https://tapas.io/series/The-World-is-Flat
    name = "flatworld-tumblr"
    long_name = "The World Is Flat (from Tumblr)"
    url = "https://theworldisflatcomics.com"


class DorrisMc(GenericTumblrV1):
    """Class to retrieve Dorris Mc Comics"""

    # Also on http://www.gocomics.com/dorris-mccomics
    name = "dorrismc"
    long_name = "Dorris Mc"
    url = "https://dorrismccomics.com"


class LeleozTumblr(GenericDeletedTumblrV1):
    """Class to retrieve Leleoz comics."""

    # Also on https://tapas.io/series/Leleoz
    name = "leleoz-tumblr"
    long_name = "Leleoz (from Tumblr)"
    url = "http://leleozcomics.tumblr.com"


class MoonBeardTumblr(GenericTumblrV1):
    """Class to retrieve MoonBeard comics."""

    # Also on http://moonbeard.com
    # Also on http://www.webtoons.com/en/comedy/moon-beard/list?title_no=471
    name = "moonbeard-tumblr"
    long_name = "Moon Beard (from Tumblr)"
    url = "https://squireseses.tumblr.com"
    _categories = ("MOONBEARD",)


class AComik(GenericTumblrV1):
    """Class to retrieve A Comik"""

    name = "comik"
    long_name = "A Comik"
    url = "https://acomik.com"


class ClassicRandy(GenericTumblrV1):
    """Class to retrieve Classic Randy comics."""

    name = "randy"
    long_name = "Classic Randy"
    url = "https://classicrandy.tumblr.com"


class DagssonTumblr(GenericTumblrV1):
    """Class to retrieve Dagsson comics."""

    # Also on http://www.dagsson.com
    name = "dagsson-tumblr"
    long_name = "Dagsson Hugleikur (from Tumblr)"
    url = "https://hugleikurdagsson.tumblr.com"


class LinsEditionsTumblr(GenericTumblrV1):
    """Class to retrieve L.I.N.S. Editions comics."""

    # Also on https://linsedition.com
    # Now on https://warandpeas.tumblr.com
    name = "lins-tumblr"
    long_name = "L.I.N.S. Editions (from Tumblr)"
    url = "https://linscomics.tumblr.com"
    _categories = ("WARANDPEAS", "LINS")


class WarAndPeasTumblr(GenericTumblrV1):
    """Class to retrieve War And Peas comics."""

    # Was on https://linscomics.tumblr.com
    name = "warandpeas-tumblr"
    long_name = "War And Peas (from Tumblr)"
    url = "https://warandpeas.tumblr.com"
    _categories = ("WARANDPEAS", "LINS")


class OrigamiHotDish(GenericTumblrV1):
    """Class to retrieve Origami Hot Dish comics."""

    name = "origamihotdish"
    long_name = "Origami Hot Dish"
    url = "https://origamihotdish.com"


class HitAndMissComicsTumblr(GenericTumblrV1):
    """Class to retrieve Hit and Miss Comics."""

    name = "hitandmiss"
    long_name = "Hit and Miss Comics"
    url = "https://hitandmisscomics.tumblr.com"


class HMBlanc(GenericTumblrV1):
    """Class to retrieve HM Blanc comics."""

    name = "hmblanc"
    long_name = "HM Blanc"
    url = "https://hmblanc.tumblr.com"


class TalesOfAbsurdityTumblr(GenericTumblrV1):
    """Class to retrieve Tales Of Absurdity comics."""

    # Also on http://talesofabsurdity.com
    # Also on https://tapas.io/series/Tales-Of-Absurdity
    name = "absurdity-tumblr"
    long_name = "Tales of Absurdity (from Tumblr)"
    url = "https://talesofabsurdity.tumblr.com"
    _categories = ("ABSURDITY",)


class RobbieAndBobby(GenericTumblrV1):
    """Class to retrieve Robbie And Bobby comics."""

    # Also on http://robbieandbobby.com
    name = "robbie-tumblr"
    long_name = "Robbie And Bobby (from Tumblr)"
    url = "https://robbieandbobby.tumblr.com"


class ElectricBunnyComicTumblr(GenericDeletedTumblrV1):
    """Class to retrieve Electric Bunny Comics."""

    # Also on http://www.electricbunnycomics.com/View/Comic/153/Welcome+to+Hell
    name = "bunny-tumblr"
    long_name = "Electric Bunny Comic (from Tumblr)"
    url = "http://electricbunnycomics.tumblr.com"


class Hoomph(GenericDeletedTumblrV1):
    """Class to retrieve Hoomph comics."""

    name = "hoomph"
    long_name = "Hoomph"
    url = "https://hoom.ph"


class BFGFSTumblr(GenericTumblrV1):
    """Class to retrieve BFGFS comics."""

    # Also on https://tapas.io/series/BFGFS
    # Also on http://bfgfs.com
    name = "bfgfs-tumblr"
    long_name = "BFGFS (from Tumblr)"
    url = "https://bfgfs.tumblr.com"


class DoodleForFood(GenericTumblrV1):
    """Class to retrieve Doodle For Food comics."""

    # Also on https://tapas.io/series/Doodle-for-Food
    name = "doodle"
    long_name = "Doodle For Food"
    url = "https://www.doodleforfood.com"


class CassandraCalinTumblr(GenericTumblrV1):
    """Class to retrieve C. Cassandra comics."""

    # Also on http://cassandracalin.com
    # Also on https://tapas.io/series/CassandraComics
    name = "cassandra-tumblr"
    long_name = "Cassandra Calin (from Tumblr)"
    url = "https://c-cassandra.tumblr.com"


class DougWasTaken(GenericTumblrV1):
    """Class to retrieve Doug Was Taken comics."""

    name = "doug"
    long_name = "Doug Was Taken"
    url = "https://dougwastaken.tumblr.com"


class MandatoryRollerCoaster(GenericTumblrV1):
    """Class to retrieve Mandatory Roller Coaster comics."""

    name = "rollercoaster"
    long_name = "Mandatory Roller Coaster"
    url = "https://mandatoryrollercoaster.com"


class CEstPasEnRegardantSesPompes(GenericTumblrV1):
    """Class to retrieve C'Est Pas En Regardant Ses Pompes (...)  comics."""

    name = "cperspqccltt"
    long_name = "C Est Pas En Regardant Ses Pompes (...)"
    url = "https://marcoandco.tumblr.com"


class TheGrohlTroll(
    GenericDeletedComic, GenericTumblrV1
):  # It takes a long time to err
    """Class to retrieve The Grohl Troll comics."""

    name = "grohltroll"
    long_name = "The Grohl Troll"
    url = "http://thegrohltroll.com"


class WebcomicName(GenericTumblrV1):
    """Class to retrieve Webcomic Name comics."""

    name = "webcomicname"
    long_name = "Webcomic Name"
    url = "https://webcomicname.com"


class BooksOfAdam(GenericTumblrV1):
    """Class to retrieve Books of Adam comics."""

    # Also on http://www.booksofadam.com
    name = "booksofadam"
    long_name = "Books of Adam"
    url = "http://booksofadam.tumblr.com"


class HarkAVagrant(GenericTumblrV1):
    """Class to retrieve Hark A Vagrant comics."""

    # Also on http://www.harkavagrant.com
    name = "hark-tumblr"
    long_name = "Hark A Vagrant (from Tumblr)"
    url = "https://beatonna.tumblr.com"


class OurSuperAdventureTumblr(GenericTumblrV1):
    """Class to retrieve Our Super Adventure comics."""

    # Also on https://tapas.io/series/OurSuperAdventure
    # Also on http://www.oursuperadventure.com
    # http://sarahgraley.com
    name = "superadventure-tumblr"
    long_name = "Our Super Adventure (from Tumblr)"
    url = "https://sarahssketchbook.tumblr.com"


class JakeLikesOnions(GenericTumblrV1):
    """Class to retrieve Jake Likes Onions comics."""

    name = "jake"
    long_name = "Jake Likes Onions"
    url = "https://jakelikesonions.com"


class InYourFaceCakeTumblr(GenericTumblrV1):
    """Class to retrieve In Your Face Cake comics."""

    # Also on https://tapas.io/series/In-Your-Face-Cake
    name = "inyourfacecake-tumblr"
    long_name = "In Your Face Cake (from Tumblr)"
    url = "https://in-your-face-cake.tumblr.com"
    _categories = ("INYOURFACECAKE",)


class Robospunk(GenericTumblrV1):
    """Class to retrieve Robospunk comics."""

    name = "robospunk"
    long_name = "Robospunk"
    url = "https://robospunk.com"


class BananaTwinky(GenericTumblrV1):
    """Class to retrieve Banana Twinky comics."""

    name = "banana"
    long_name = "Banana Twinky"
    url = "https://bananatwinky.tumblr.com"


class YesterdaysPopcornTumblr(GenericTumblrV1):
    """Class to retrieve Yesterday's Popcorn comics."""

    # Also on http://www.yesterdayspopcorn.com
    # Also on https://tapas.io/series/Yesterdays-Popcorn
    name = "popcorn-tumblr"
    long_name = "Yesterday's Popcorn (from Tumblr)"
    url = "https://yesterdayspopcorn.tumblr.com"


class TwistedDoodles(GenericTumblrV1):
    """Class to retrieve Twisted Doodles comics."""

    name = "twisted"
    long_name = "Twisted Doodles"
    url = "https://www.twisteddoodles.com"


class UbertoolTumblr(GenericTumblrV1):
    """Class to retrieve Ubertool comics."""

    # Also on http://ubertoolcomic.com
    # Also on https://tapas.io/series/ubertool
    name = "ubertool-tumblr"
    long_name = "Ubertool (from Tumblr)"
    url = "https://ubertool.tumblr.com"
    _categories = ("UBERTOOL",)


class LittleLifeLinesTumblr(GenericDeletedTumblrV1):
    """Class to retrieve Little Life Lines comics."""

    # Also on http://www.littlelifelines.com
    name = "life-tumblr"
    long_name = "Little Life Lines (from Tumblr)"
    url = "https://little-life-lines.tumblr.com"


class TheyCanTalk(GenericTumblrV1):
    """Class to retrieve They Can Talk comics."""

    name = "theycantalk"
    long_name = "They Can Talk"
    url = "https://theycantalk.com"


class Will5NeverCome(GenericTumblrV1):
    """Class to retrieve Will 5:00 Never Come comics."""

    name = "will5"
    long_name = "Will 5:00 Never Come ?"
    url = "https://will5nevercome.com"


class Sephko(GenericTumblrV1):
    """Class to retrieve Sephko Comics."""

    # Also on http://www.sephko.com
    name = "sephko"
    long_name = "Sephko"
    url = "https://sephko.tumblr.com"


class BlazersAtDawn(GenericTumblrV1):
    """Class to retrieve Blazers At Dawn Comics."""

    name = "blazers"
    long_name = "Blazers At Dawn"
    url = "https://blazersatdawn.tumblr.com"


class ArtByMoga(
    GenericEmptyComic, GenericTumblrV1
):  # Deactivated because it downloads too many things
    """Class to retrieve Art By Moga Comics."""

    name = "moga"
    long_name = "Art By Moga"
    url = "http://artbymoga.tumblr.com"


class VerbalVomitTumblr(GenericTumblrV1):
    """Class to retrieve Verbal Vomit comics."""

    # Also on http://www.verbal-vomit.com
    name = "vomit-tumblr"
    long_name = "Verbal Vomit (from Tumblr)"
    url = "https://verbalvomits.tumblr.com"


class LibraryComic(GenericTumblrV1):
    """Class to retrieve LibraryComic."""

    # Also on http://librarycomic.com
    name = "library-tumblr"
    long_name = "LibraryComic (from Tumblr)"
    url = "https://librarycomic.tumblr.com"


class TizzyStitchBirdTumblr(GenericTumblrV1):
    """Class to retrieve Tizzy Stitch Bird comics."""

    # Also on http://tizzystitchbird.com
    # Also on https://tapas.io/series/TizzyStitchbird
    # Also on http://www.webtoons.com/en/challenge/tizzy-stitchbird/list?title_no=50082
    name = "tizzy-tumblr"
    long_name = "Tizzy Stitch Bird (from Tumblr)"
    url = "https://tizzystitchbird.tumblr.com"


class VictimsOfCircumsolarTumblr(GenericTumblrV1):
    """Class to retrieve VictimsOfCircumsolar comics."""

    # Also on http://www.victimsofcircumsolar.com
    name = "circumsolar-tumblr"
    long_name = "Victims Of Circumsolar (from Tumblr)"
    url = "https://victimsofcomics.tumblr.com"


class RockPaperCynicTumblr(GenericTumblrV1):
    """Class to retrieve RockPaperCynic comics."""

    # Also on http://www.rockpapercynic.com
    # Also on https://tapas.io/series/rockpapercynic
    name = "rpc-tumblr"
    long_name = "Rock Paper Cynic (from Tumblr)"
    url = "https://rockpapercynic.tumblr.com"


class DeadlyPanelTumblr(GenericDeletedTumblrV1):
    """Class to retrieve Deadly Panel comics."""

    # Also on http://www.deadlypanel.com
    # Also on https://tapas.io/series/deadlypanel
    name = "deadly-tumblr"
    long_name = "Deadly Panel (from Tumblr)"
    url = "https://deadlypanel.tumblr.com"


class CatanaComics(GenericComicNotWorking):  # Not a tumblr anymore - an instagram ?
    """Class to retrieve Catana comics."""

    name = "catana"
    long_name = "Catana"
    url = "http://www.catanacomics.com"


class AngryAtNothingTumblr(GenericTumblrV1):
    """Class to retrieve Angry at Nothing comics."""

    # Also on http://www.angryatnothing.net
    # Also on https://tapas.io/series/Comics-yeah-definitely-comics-
    name = "angry-tumblr"
    long_name = "Angry At Nothing (from Tumblr)"
    url = "https://angryatnothing.tumblr.com"


class ShanghaiTango(GenericTumblrV1):
    """Class to retrieve Shanghai Tango comic."""

    name = "tango"
    long_name = "Shanghai Tango"
    url = "http://tango2010weibo.tumblr.com"


class OffTheLeashDogTumblr(GenericTumblrV1):
    """Class to retrieve Off The Leash Dog comics."""

    # Also on http://offtheleashdogcartoons.com
    # Also on http://www.rupertfawcettcartoons.com
    name = "offtheleash-tumblr"
    long_name = "Off The Leash Dog (from Tumblr)"
    url = "https://rupertfawcettsdoggyblog.tumblr.com"
    _categories = ("FAWCETT",)


class ImogenQuestTumblr(GenericTumblrV1):
    """Class to retrieve Imogen Quest comics."""

    # Also on http://imogenquest.net
    # Also on https://www.gocomics.com/imogen-quest
    name = "imogen-tumblr"
    long_name = "Imogen Quest (from Tumblr)"
    url = "https://imoquest.tumblr.com"
    _categories = ("IMOGEN",)


class Shitfest(GenericTumblrV1):
    """Class to retrieve Shitfest comics."""

    name = "shitfest"
    long_name = "Shitfest"
    url = "https://shitfestcomic.com"


class IceCreamSandwichComics(GenericTumblrV1):
    """Class to retrieve Ice Cream Sandwich Comics."""

    name = "icecream"
    long_name = "Ice Cream Sandwich Comics"
    url = "https://icecreamsandwichcomics.com"


class Dustinteractive(GenericTumblrV1):
    """Class to retrieve Dustinteractive comics."""

    name = "dustinteractive"
    long_name = "Dustinteractive"
    url = "https://dustinteractive.com"


class StickyCinemaFloor(GenericTumblrV1):
    """Class to retrieve Sticky Cinema Floor comics."""

    name = "stickycinema"
    long_name = "Sticky Cinema Floor"
    url = "https://stickycinemafloor.tumblr.com"


class IncidentalComicsTumblr(GenericTumblrV1):
    """Class to retrieve Incidental Comics."""

    # Also on http://www.incidentalcomics.com
    name = "incidental-tumblr"
    long_name = "Incidental Comics (from Tumblr)"
    url = "https://incidentalcomics.tumblr.com"


class APleasantWasteOfTimeTumblr(GenericTumblrV1):
    """Class to retrieve A Pleasant Waste Of Time comics."""

    # Also on https://tapas.io/series/A-Pleasant-
    name = "pleasant-waste-tumblr"
    long_name = "A Pleasant Waste Of Time (from Tumblr)"
    url = "https://artjcf.tumblr.com"
    _categories = ("WASTE",)


class HorovitzComicsTumblr(GenericTumblrV1):
    """Class to retrieve Horovitz new comics."""

    # Also on http://www.horovitzcomics.com
    name = "horovitz-tumblr"
    long_name = "Horovitz (from Tumblr)"
    url = "https://horovitzcomics.tumblr.com"
    _categories = ("HOROVITZ",)


class DeepDarkFearsTumblr(GenericTumblrV1):
    """Class to retrieve DeepvDarkvFears comics."""

    name = "deep-dark-fears-tumblr"
    long_name = "Deep Dark Fears (from Tumblr)"
    url = "https://deep-dark-fears.tumblr.com"


class DakotaMcDadzean(GenericTumblrV1):
    """Class to retrieve Dakota McDadzean comics."""

    name = "dakota"
    long_name = "Dakota McDadzean"
    url = "https://dakotamcfadzean.tumblr.com"


class ExtraFabulousComicsTumblr(GenericTumblrV1):
    """Class to retrieve Extra Fabulous Comics."""

    # Also on http://extrafabulouscomics.com
    name = "efc-tumblr"
    long_name = "Extra Fabulous Comics (from Tumblr)"
    url = "https://extrafabulouscomics.tumblr.com"
    _categories = ("EFC",)


class AlexLevesque(GenericComicNotWorking, GenericTumblrV1):
    """Class to retrieve AlexLevesque comics."""

    name = "alevesque"
    long_name = "Alex Levesque"
    url = "https://alexlevesque.com"
    _categories = ("FRANCAIS",)


class JamesOfNoTradesTumblr(GenericTumblrV1):
    """Class to retrieve JamesOfNoTrades comics."""

    # Also on http://jamesofnotrades.com
    # Also on http://www.webtoons.com/en/challenge/james-of-no-trades/list?title_no=43422
    # Also on https://tapas.io/series/James-of-No-Trades
    name = "jamesofnotrades-tumblr"
    long_name = "James Of No Trades (from Tumblr)"
    url = "https://jamesfregan.tumblr.com"
    _categories = ("JAMESOFNOTRADES",)


class InfiniteGuff(GenericDeletedTumblrV1):  # Used to be a Tumblr
    """Class to retrieve Infinite Guff comics."""

    # Also on https://www.instagram.com/infiniteguff/
    name = "infiniteguff"
    long_name = "Infinite Guff"
    url = "http://infiniteguff.com"


class SkeletonClaw(GenericTumblrV1):
    """Class to retrieve Skeleton Claw comics."""

    name = "skeletonclaw"
    long_name = "Skeleton Claw"
    url = "https://skeletonclaw.com"


class MrsFrolleinTumblr(GenericDeletedTumblrV1):
    """Class to retrieve Mrs Frollein comics."""

    # Also on http://www.webtoons.com/en/challenge/mrsfrollein/list?title_no=51710
    name = "frollein"
    long_name = "Mrs Frollein (from Tumblr)"
    url = "https://mrsfrollein.tumblr.com"


class GoodBearComicsTumblr(GenericTumblrV1):
    """Class to retrieve GoodBearComics."""

    # Also on https://goodbearcomics.com
    name = "goodbear-tumblr"
    long_name = "Good Bear Comics (from Tumblr)"
    url = "https://goodbearcomics.tumblr.com"


class BrooklynCartoonsTumblr(GenericTumblrV1):
    """Class to retrieve Brooklyn Cartoons."""

    # Also on https://www.brooklyncartoons.com
    # Also on https://www.instagram.com/brooklyncartoons
    name = "brooklyn-tumblr"
    long_name = "Brooklyn Cartoons (from Tumblr)"
    url = "https://brooklyncartoons.tumblr.com"


class GemmaCorrellTumblr(GenericTumblrV1):
    # Also on http://www.gemmacorrell.com/portfolio/comics/
    name = "gemma-tumblr"
    long_name = "Gemma Correll (from Tumblr)"
    url = "https://gemmacorrell.tumblr.com"


class RobotatertotTumblr(GenericTumblrV1):
    """Class to retrieve Robotatertot comics."""

    # Also on https://www.instagram.com/robotatertotcomics
    name = "robotatertot-tumblr"
    long_name = "Robotatertot (from Tumblr)"
    url = "https://robotatertot.tumblr.com"


class HuffyPenguin(GenericTumblrV1):
    """Class to retrieve Huffy Penguin comics."""

    name = "huffypenguin"
    long_name = "Huffy Penguin"
    url = "https://huffy-penguin.tumblr.com"


class CowardlyComicsTumblr(GenericTumblrV1):
    """Class to retrieve Cowardly Comics."""

    # Also on https://tapas.io/series/CowardlyComics
    # Also on http://www.webtoons.com/en/challenge/cowardly-comics/list?title_no=65893
    name = "cowardly-tumblr"
    long_name = "Cowardly Comics (from Tumblr)"
    url = "https://cowardlycomics.tumblr.com"


class Caw4hwTumblr(GenericTumblrV1):
    """Class to retrieve Caw4hw comics."""

    # Also on https://tapas.io/series/CAW4HW
    name = "caw4hw-tumblr"
    long_name = "Caw4hw (from Tumblr)"
    url = "https://caw4hw.tumblr.com"


class WeFlapsTumblr(GenericTumblrV1):
    """Class to retrieve WeFlaps comics."""

    name = "weflaps-tumblr"
    long_name = "We Flaps (from Tumblr)"
    url = "https://weflaps.tumblr.com"


class TheseInsideJokesTumblr(GenericDeletedComic, GenericTumblrV1):
    """Class to retrieve These Inside Jokes comics."""

    # Also on http://www.theseinsidejokes.com
    name = "theseinsidejokes-tumblr"
    long_name = "These Inside Jokes (from Tumblr)"
    url = "http://theseinsidejokes.tumblr.com"


class SinewynTumblr(GenericTumblrV1):
    """Class to retrieve Sinewyn comics."""

    # Also on https://sinewyn.wordpress.com
    name = "sinewyn-tumblr"
    long_name = "Sinewyn (from Tumblr)"
    url = "https://sinewyn.tumblr.com"


class ItFoolsAMonster(GenericNavigableComic):
    """Class to retrieve It Fools A Monster comics."""

    name = "itfoolsamonster"
    long_name = "It Fools A Monster"
    url = "http://itfoolsamonster.com"
    get_first_comic_link = get_a_navi_navifirst
    get_navi_link = get_a_navi_comicnavnext_navinext

    @classmethod
    def get_comic_info(cls, soup, link):
        """Get information about a particular comics."""
        title = soup.find("h2", class_="post-title").string
        author = soup.find("a", rel="author").string
        date_str = soup.find("span", class_="post-date").string
        imgs = soup.find("div", id="comic").find_all("img")
        return {
            "img": [i["src"] for i in imgs],
            "title": title,
            "author": author,
            "date": string_to_date(date_str, "%B %d, %Y"),
        }


class EatMyPaint(GenericNavigableComic):
    """Class to retrieve Eat My Paint comics."""

    # Also on https://eatmypaint.tumblr.com
    # Also on https://www.webtoons.com/en/challenge/eatmypaint/list?title_no=31150&page=1
    # Also on https://tapas.io/series/eatmypaint
    name = "eatmypaint"
    long_name = "Eat My Paint"
    url = "https://www.eatmypaint.co.uk"
    _categories = ("EATMYPAINT",)
    get_first_comic_link = get_a_navi_navifirst
    get_navi_link = get_a_navi_comicnavnext_navinext

    @classmethod
    def get_comic_info(cls, soup, link):
        """Get information about a particular comics."""
        imgs = soup.find("div", id="comic").find_all("img") + soup.find_all(
            "img", class_="hiddenPanel"
        )
        return {
            "img": [i["src"] for i in imgs],
        }


class RustledJimmies(GenericNavigableComic):
    """Class to retrieve Rustled Jimmies comics."""

    name = "rustled"
    long_name = "Rustled Jimmies"
    url = "http://rustledjimmies.net"
    get_url_from_link = join_cls_url_to_href

    @classmethod
    def get_first_comic_link(cls):
        """Get link to first comics."""
        return get_soup_at_url(cls.url).find("a", class_="page-last")

    @classmethod
    def get_navi_link(cls, last_soup, next_):
        """Get link to next or previous comic."""
        link = last_soup.find("a", class_="page-prev" if next_ else "page-next")
        # Workaround because a next arrow links to https://rustledjimmies.net/comic/
        if link:
            url = cls.get_url_from_link(link)
            if url == "https://rustledjimmies.net/comic/ ":
                return None
        return link

    @classmethod
    def get_comic_info(cls, soup, link):
        """Get information about a particular comics."""
        title = soup.find("meta", property="og:title")["content"]
        author = soup.find("meta", attrs={"name": "author"})["content"]
        post = soup.find("article", class_="post")
        imgs = post.find_all("img")
        date_str = soup.find("meta", property="article:published_time")["content"]
        return {
            "title": title,
            "author": author,
            "date": isoformat_to_date(date_str),
            "img": [
                urljoin_wrapper(
                    cls.url, i["data-src"] if i.has_attr("data-src") else i["src"]
                )
                for i in imgs
            ],
        }


class KickstandComics(GenericNavigableComic):
    """Class to retrieve Kickstand Comics."""

    name = "kickstand"
    long_name = "Kickstand Comics featuring Yehuda Moon"
    url = "http://yehudamoon.com"
    _categories = ("BIKE",)
    get_first_comic_link = get_a_comicnavbase_comicnavfirst
    get_navi_link = get_a_comicnavbase_comicnavnext

    @classmethod
    def get_comic_info(cls, soup, link):
        """Get information about a particular comics."""
        title = soup.find("h2", class_="post-title").string
        imgs = soup.find("div", id="comic").find_all("img")
        return {
            "img": [i["src"] for i in imgs],
            "title": title,
        }


class BoumeriesTumblr(GenericTumblrV1):
    """Class to retrieve Boumeries comics."""

    # Also on http://bd.boumerie.com
    # Also on http://comics.boumerie.com
    name = "boumeries-tumblr"
    long_name = "Boumeries (from Tumblr)"
    url = "https://boumeries.tumblr.com/"
    _categories = ("BOUMERIES",)


class InfiniteImmortalBensTumblr(GenericTumblrV1):
    """Class to retrieve Infinite Immortal Bens comics."""

    # Also on http://www.webtoons.com/en/challenge/infinite-immortal-bens/list?title_no=32847
    # Also on https://tapas.io/series/Infinite-Immortal-Bens
    url = "https://infiniteimmortalbens.tumblr.com"
    name = "infiniteimmortal-tumblr"
    long_name = "Infinite Immortal Bens (from Tumblr)"
    _categories = ("INFINITEIMMORTAL",)


class CheeseCornzTumblr(GenericTumblrV1):
    """Class to retrieve Cheese Cornz comics."""

    name = "cheesecornz-tumblr"
    long_name = "Cheese Cornz (from Tumblr)"
    url = "https://cheesecornz.tumblr.com"


class CinismoIlustrado(GenericTumblrV1):
    """Class to retrieve CinismoIlustrado comics."""

    name = "cinismo"
    long_name = "Cinismo Ilustrado"
    url = "https://cinismoilustrado.com"
    _categories = ("ESPANOL",)


class EatMyPaintTumblr(GenericTumblrV1):
    """Class to retrieve Eat My Paint comics."""

    # Also on https://tapas.io/series/eatmypaint
    # Also on https://www.webtoons.com/en/challenge/eatmypaint/list?title_no=31150&page=1
    # Also on https://www.eatmypaint.co.uk
    name = "eatmypaint-tumblr"
    long_name = "Eat My Paint (from Tumblr)"
    url = "https://eatmypaint.tumblr.com"
    _categories = ("EATMYPAINT",)


class AnomalyTownFromTumblr(GenericTumblrV1):
    """Class to retrieve Anomaly Town."""

    name = "anomalytown-tumblr"
    long_name = "Anomaly Town (from Tumblr)"
    url = "https://anomalytown.tumblr.com"


class RoryTumblr(GenericTumblrV1):
    """Class to retrieve Rory comics."""

    # Also on https://tapas.io/series/rorycomics
    name = "rory-tumblr"
    long_name = "Rory (from Tumblr)"
    url = "https://rorycomics.tumblr.com"
    _categories = ("RORY",)


class OneGiantHand(GenericTumblrV1):
    """Class to retrieve One Giant Hand comics."""

    # Also on https://www.instagram.com/onegianthand
    name = "onegianthand"
    long_name = "One Giant Hand"
    url = "https://onegianthand.com"


class RaeTheDoeTumblr(GenericTumblrV1):
    """Class to retrieve Rae The Doe comics."""

    # Also on https://www.raethedoe.com
    name = "rae-tumblr"
    long_name = "Rae the Doe (from Tumblr)"
    url = "https://raethedoe.tumblr.com"


class PainTrainComicTumblr(GenericTumblrV1):
    """Class to retrieve Pain Train Comics."""

    # Also on http://paintraincomic.com
    name = "paintrain-tumblr"
    long_name = "Pain Train Comics (from Tumblr)"
    url = "https://paintraincomic.tumblr.com"


class TheGentlemanArmchair(GenericTumblrV1):
    """Class to retrieve The Gentleman Armchair comics."""

    # Used to be on https://thegentlemansarmchair.com
    # Also on https://www.gocomics.com/the-gentlemans-armchair
    # Also on https://www.webtoons.com/en/comedy/the-gentlemans-armchair/list?title_no=469
    name = "gentlemanarmchair"
    long_name = "The Gentleman Armchair"
    url = "https://thegentlemansarmchair.tumblr.com"


class SpfComics(GenericDeletedTumblrV1):
    """Class to retrieve SPF comics."""

    name = "spf"
    long_name = "SPF Comics"
    url = "https://spfcomics.com"


class ThreeMbComics(GenericTumblrV1):
    """Class to retrieve 3mb Comics."""

    name = "3mb"
    long_name = "3MB Comics"
    url = "https://www.3mbcomics.com"


class FalseKneesTumblr(GenericTumblrV1):
    """Class to retrieve False Knees comics."""

    # Also on https://falseknees.com
    # Also on https://tapas.io/series/FalseKnees
    # Also on http://www.webtoons.com/en/challenge/false-knees/list?title_no=79544
    name = "falseknees-tumblr"
    long_name = "False Knees (from Tumblr)"
    url = "https://falseknees.tumblr.com"
    _categories = ("FALSEKNEES",)


class QuarkSideTumblr(GenericTumblrV1):
    """Class to retrieve Quark Side comics."""

    # Also on http://www.quarktees.com/blogs/news
    name = "quarkside-tumblr"
    long_name = "The Quark Side (from Tumblr)"
    url = "https://thequarkside.tumblr.com"
    _categories = ("QUARKSIDE",)


class HorovitzComics(GenericDeletedComic, GenericListableComic):
    """Generic class to handle the logic common to the different comics from Horovitz."""

    # Also on https://horovitzcomics.tumblr.com
    url = "http://www.horovitzcomics.com"
    _categories = ("HOROVITZ",)
    img_re = re.compile(
        ".*comics/(?P<year>[0-9]*)/(?P<month>[0-9]*)/(?P<day>[0-9]*)/.*$"
    )
    link_re = NotImplemented
    get_url_from_archive_element = join_cls_url_to_href

    @classmethod
    def get_comic_info(cls, soup, link):
        """Get information about a particular comics."""
        href = link["href"]
        num = int(cls.link_re.match(href).group(1))
        title = link.string
        imgs = soup.find_all("img", id="comic")
        assert len(imgs) == 1, imgs
        return {
            "title": title,
            "date": regexp_match_to_date(cls.img_re.match(imgs[0]["src"])),
            "img": [i["src"] for i in imgs],
            "num": num,
        }

    @classmethod
    def get_archive_elements(cls):
        archive_url = "http://www.horovitzcomics.com/comics/archive/"
        return reversed(get_soup_at_url(archive_url).find_all("a", href=cls.link_re))


class HorovitzNew(HorovitzComics):
    """Class to retrieve Horovitz new comics."""

    name = "horovitznew"
    long_name = "Horovitz New"
    link_re = re.compile("^/comics/new/([0-9]+)$")


class HorovitzClassic(HorovitzComics):
    """Class to retrieve Horovitz classic comics."""

    name = "horovitzclassic"
    long_name = "Horovitz Classic"
    link_re = re.compile("^/comics/classic/([0-9]+)$")


class GenericGoComic(GenericNavigableComic):
    """Generic class to handle the logic common to comics from gocomics.com."""

    _categories = ("GOCOMIC",)

    @classmethod
    def get_first_comic_link(cls):
        """Get link to first comics."""
        comics_link = get_soup_at_url(cls.url).find("a", attrs={"data-link": "comics"})
        comics_page = get_soup_at_url(cls.get_url_from_link(comics_link))
        class_ = "fa btn btn-outline-secondary btn-circle fa fa-backward sm"
        return comics_page.find("a", class_=class_) or comics_page.find(
            "a", class_=class_ + " "
        )

    @classmethod
    def get_navi_link(cls, last_soup, next_):
        """Get link to next or previous comic."""
        PREV = (
            "fa btn btn-outline-secondary btn-circle fa-caret-left sm js-previous-comic"
        )
        NEXT = "fa btn btn-outline-secondary btn-circle fa-caret-right sm"
        class_ = NEXT if next_ else PREV
        return last_soup.find("a", class_=class_) or last_soup.find(
            "a", class_=class_ + " "
        )

    @classmethod
    def get_url_from_link(cls, link):
        gocomics = "http://www.gocomics.com"
        return urljoin_wrapper(gocomics, link["href"])

    @classmethod
    def get_comic_info(cls, soup, link):
        """Get information about a particular comics."""
        date_str = soup.find("meta", property="article:published_time")["content"]
        imgs = soup.find_all("meta", property="og:image")
        author = soup.find("meta", property="article:author")["content"]
        tags = soup.find("meta", property="article:tag")["content"]
        return {
            "date": string_to_date(date_str, "%Y-%m-%d"),
            "img": [i["content"] for i in imgs],
            "author": author,
            "tags": tags,
        }


class PearlsBeforeSwine(GenericGoComic):
    """Class to retrieve Pearls Before Swine comics."""

    name = "pearls"
    long_name = "Pearls Before Swine"
    url = "http://www.gocomics.com/pearlsbeforeswine"


class Peanuts(GenericGoComic):
    """Class to retrieve Peanuts comics."""

    name = "peanuts"
    long_name = "Peanuts"
    url = "http://www.gocomics.com/peanuts"


class MattWuerker(GenericGoComic):
    """Class to retrieve Matt Wuerker comics."""

    name = "wuerker"
    long_name = "Matt Wuerker"
    url = "http://www.gocomics.com/mattwuerker"


class TomToles(GenericGoComic):
    """Class to retrieve Tom Toles comics."""

    name = "toles"
    long_name = "Tom Toles"
    url = "http://www.gocomics.com/tomtoles"


class BreakOfDay(GenericGoComic):
    """Class to retrieve Break Of Day comics."""

    name = "breakofday"
    long_name = "Break Of Day"
    url = "http://www.gocomics.com/break-of-day"


class Brevity(GenericGoComic):
    """Class to retrieve Brevity comics."""

    name = "brevity"
    long_name = "Brevity"
    url = "http://www.gocomics.com/brevity"


class MichaelRamirez(GenericGoComic):
    """Class to retrieve Michael Ramirez comics."""

    name = "ramirez"
    long_name = "Michael Ramirez"
    url = "http://www.gocomics.com/michaelramirez"


class MikeLuckovich(GenericGoComic):
    """Class to retrieve Mike Luckovich comics."""

    name = "luckovich"
    long_name = "Mike Luckovich"
    url = "http://www.gocomics.com/mikeluckovich"


class JimBenton(GenericGoComic):
    """Class to retrieve Jim Benton comics."""

    # Also on http://jimbenton.tumblr.com
    name = "benton"
    long_name = "Jim Benton"
    url = "http://www.gocomics.com/jim-benton-cartoons"


class TheArgyleSweater(GenericGoComic):
    """Class to retrieve the Argyle Sweater comics."""

    name = "argyle"
    long_name = "Argyle Sweater"
    url = "http://www.gocomics.com/theargylesweater"


class SunnyStreet(GenericGoComic):
    """Class to retrieve Sunny Street comics."""

    # Also on http://www.sunnystreetcomics.com
    name = "sunny"
    long_name = "Sunny Street"
    url = "http://www.gocomics.com/sunny-street"


class OffTheMark(GenericGoComic):
    """Class to retrieve Off The Mark comics."""

    # Also on https://www.offthemark.com
    name = "offthemark"
    long_name = "Off The Mark"
    url = "http://www.gocomics.com/offthemark"


class WuMo(GenericGoComic):
    """Class to retrieve WuMo comics."""

    # Also on http://wumo.com
    name = "wumo"
    long_name = "WuMo"
    url = "http://www.gocomics.com/wumo"


class LunarBaboon(GenericGoComic):
    """Class to retrieve Lunar Baboon comics."""

    # Also on http://www.lunarbaboon.com
    # Also on https://tapas.io/series/Lunarbaboon
    name = "lunarbaboon"
    long_name = "Lunar Baboon"
    url = "http://www.gocomics.com/lunarbaboon"


class SandersenGocomic(GenericGoComic):
    """Class to retrieve Sarah Andersen comics."""

    # Also on http://sarahcandersen.com
    # Also on https://tapas.io/series/Doodle-Time
    name = "sandersen-goc"
    long_name = "Sarah Andersen (from GoComics)"
    url = "http://www.gocomics.com/sarahs-scribbles"


class SaturdayMorningBreakfastCerealGoComic(GenericGoComic):
    """Class to retrieve Saturday Morning Breakfast Cereal comics."""

    # Also on https://smbc-comics.tumblr.com
    # Also on http://www.smbc-comics.com
    name = "smbc-goc"
    long_name = "Saturday Morning Breakfast Cereal (from GoComics)"
    url = "http://www.gocomics.com/saturday-morning-breakfast-cereal"
    _categories = ("SMBC",)


class CalvinAndHobbesGoComic(GenericGoComic):
    """Class to retrieve Calvin and Hobbes comics."""

    # From gocomics, not http://marcel-oehler.marcellosendos.ch/comics/ch/
    name = "calvin-goc"
    long_name = "Calvin and Hobbes (from GoComics)"
    url = "http://www.gocomics.com/calvinandhobbes"


class RallGoComic(GenericGoComic):
    """Class to retrieve Ted Rall comics."""

    # Also on http://rall.com/comic
    name = "rall-goc"
    long_name = "Ted Rall (from GoComics)"
    url = "http://www.gocomics.com/ted-rall"
    _categories = ("RALL",)


class TheAwkwardYetiGoComic(GenericGoComic):
    """Class to retrieve The Awkward Yeti comics."""

    # Also on https://larstheyeti.tumblr.com
    # Also on http://theawkwardyeti.com
    # Also on https://tapas.io/series/TheAwkwardYeti
    name = "yeti-goc"
    long_name = "The Awkward Yeti (from GoComics)"
    url = "http://www.gocomics.com/the-awkward-yeti"
    _categories = ("YETI",)


class BerkeleyMewsGoComics(GenericGoComic):
    """Class to retrieve Berkeley Mews comics."""

    # Also on https://mews.tumblr.com
    # Also on http://www.berkeleymews.com
    name = "berkeley-goc"
    long_name = "Berkeley Mews (from GoComics)"
    url = "http://www.gocomics.com/berkeley-mews"
    _categories = ("BERKELEY",)


class SheldonGoComics(GenericDeletedComic, GenericGoComic):
    """Class to retrieve Sheldon comics."""

    # Also on http://www.sheldoncomics.com
    name = "sheldon-goc"
    long_name = "Sheldon Comics (from GoComics)"
    url = "http://www.gocomics.com/sheldon"


class FowlLanguageGoComics(GenericGoComic):
    """Class to retrieve Fowl Language comics."""

    # Also on http://www.fowllanguagecomics.com
    # Also on https://tapas.io/series/Fowl-Language-Comics
    # Also on https://fowllanguagecomics.tumblr.com
    name = "fowllanguage-goc"
    long_name = "Fowl Language Comics (from GoComics)"
    url = "http://www.gocomics.com/fowl-language"
    _categories = ("FOWLLANGUAGE",)


class NickAnderson(GenericGoComic):
    """Class to retrieve Nick Anderson comics."""

    name = "nickanderson"
    long_name = "Nick Anderson"
    url = "http://www.gocomics.com/nickanderson"


class GarfieldGoComics(GenericGoComic):
    """Class to retrieve Garfield comics."""

    # Also on http://garfield.com
    name = "garfield-goc"
    long_name = "Garfield (from GoComics)"
    url = "http://www.gocomics.com/garfield"
    _categories = ("GARFIELD",)


class DorrisMcGoComics(GenericDeletedComic, GenericGoComic):
    """Class to retrieve Dorris Mc Comics"""

    # Also on https://dorrismccomics.com
    name = "dorrismc-goc"
    long_name = "Dorris Mc (from GoComics)"
    url = "http://www.gocomics.com/dorris-mccomics"


class FoxTrot(GenericGoComic):
    """Class to retrieve FoxTrot comics."""

    name = "foxtrot"
    long_name = "FoxTrot"
    url = "http://www.gocomics.com/foxtrot"


class FoxTrotClassics(GenericGoComic):
    """Class to retrieve FoxTrot Classics comics."""

    name = "foxtrot-classics"
    long_name = "FoxTrot Classics"
    url = "http://www.gocomics.com/foxtrotclassics"


class DilbertClassics(GenericGoComic):
    """Class to retrieve Dilbert comics."""

    # Also on http://dilbert.com
    name = "dilbert-goc"
    long_name = "Dilbert Classics (from GoComics)"
    url = "http://www.gocomics.com/dilbert-classics"


class MisterAndMeGoComics(GenericDeletedComic, GenericGoComic):
    """Class to retrieve Mister & Me Comics."""

    # Also on http://www.mister-and-me.com
    # Also on https://tapas.io/series/Mister-and-Me
    name = "mister-goc"
    long_name = "Mister & Me (from GoComics)"
    url = "http://www.gocomics.com/mister-and-me"


class NonSequitur(GenericGoComic):
    """Class to retrieve Non Sequitur (Wiley Miller) comics."""

    name = "nonsequitur"
    long_name = "Non Sequitur"
    url = "http://www.gocomics.com/nonsequitur"


class JoeyAlisonSayers(GenericGoComic):
    """Class to retrieve Joey Alison Sayers comics."""

    name = "joeyalison"
    long_name = "Joey Alison Sayers (from GoComics)"
    url = "http://www.gocomics.com/joey-alison-sayers-comics"


class SavageChickenGoComics(GenericGoComic):
    """Class to retrieve Savage Chicken comics."""

    # Also on http://www.savagechickens.com
    name = "savage-goc"
    long_name = "Savage Chicken (from GoComics)"
    url = "http://www.gocomics.com/savage-chickens"


class OwlTurdGoComics(GenericGoComic):
    """Class to retrieve Owl Turd / Shen comix."""

    # Also on https://tapas.io/series/Shen-Comix
    # Also on http://shencomix.com
    # Also on http://shencomix.tumblr.com
    name = "owlturd-goc"
    long_name = "Owl Turd / Shen Comix (from GoComics)"
    url = "https://www.gocomics.com/shen-comix"
    _categories = ("OWLTURD", "SHENCOMIX")


class ImogenQuestGoComics(GenericGoComic):
    """Class to retrieve Imogen Quest comics."""

    # Also on http://imogenquest.net
    # Also on https://imoquest.tumblr.com
    name = "imogen-goc"
    long_name = "Imogen Quest (from GoComics)"
    url = "https://www.gocomics.com/imogen-quest"
    _categories = ("IMOGEN",)


class PicturesInBoxesGoComics(GenericDeletedComic, GenericGoComic):
    """Class to retrieve Pictures In Boxes comics."""

    # Also on http://www.picturesinboxes.com
    # Also on https://picturesinboxescomic.tumblr.com
    name = "picturesinboxes-goc"
    long_name = "Pictures in Boxes (from GoComics)"
    url = "https://www.gocomics.com/pictures-in-boxes"
    _categories = ("PICTURESINBOXES",)


class GenericTapasComic(GenericPaginatedListableComic):
    """Generic class to handle the logic common to comics from https://tapas.io ."""

    _categories = ("TAPAS",)

    @classmethod
    def last_comic_is_valid(cls, last_comic):
        """Check that last comic seems to be valid."""
        last_url = last_comic["url"]
        try:
            get_soup_at_url(last_url)
        except urllib.error.HTTPError:
            try:
                get_soup_at_url(cls.url)
            except urllib.error.HTTPError:
                print("Did not find previous post nor main url %s" % cls.url)
            else:
                print(
                    "Did not find previous post %s : it might have been deleted"
                    % last_url
                )
            return False

    @classmethod
    def get_comic_info(cls, archive_elt):
        """Get information about a particular comics."""
        url = cls.get_url_from_archive_element(archive_elt)
        coming_soon = archive_elt["class"] == [
            "ga-tracking",
            "js-episode",
            "js-coming-soon",
        ]
        if coming_soon:
            print("Comic %s is being uploaded, retry later" % url)
            return None
        info_title = archive_elt.find("div", class_="info__title")
        title_raw = info_title.get_text()
        title = title_raw.strip()
        episode_num = int(archive_elt["data-scene-number"])
        episode_id = int(archive_elt["data-id"])
        info = archive_elt.find("div", class_="info__tag").string
        date, sep, views = info.partition("&bullet")
        views = views.strip()
        soup = get_soup_at_url(url)
        imgs = soup.find_all("img", class_="content__img js-lazy")
        assert len(imgs) > 0, imgs
        return {
            "url": url,
            "date": string_to_date(date.strip(), "%b %d, %Y"),
            "img": [i["data-src"] for i in imgs],
            "title": title,
            "episode_num": episode_num,
            "episode_id": episode_id,
        }

    @classmethod
    def archive_element_corresponds_to_comic(cls, elt, comic):
        return comic is not None and int(elt["data-id"]) == comic["episode_id"]

    @classmethod
    def yield_archive_elements(cls):
        """Yield archive elements from newer to older."""
        url = cls.url
        while True:
            soup = get_soup_at_url(url)
            for li in soup.find_all("li", class_="content__item"):
                a = li.find("a")
                assert a
                yield a
            next_button = soup.find(
                "a",
                class_="paging__button paging__button--img paging__button--next g-act",
            )
            if next_button is None:
                return
            url = urljoin_wrapper(url, next_button["href"])

    @classmethod
    def get_url_from_archive_element(cls, archive_elt):
        return urljoin_wrapper(cls.url, archive_elt["href"])


class VegetablesForDessert(GenericTapasComic):
    """Class to retrieve Vegetables For Dessert comics."""

    # Also on http://vegetablesfordessert.tumblr.com
    name = "vegetables"
    long_name = "Vegetables For Dessert"
    url = "https://tapas.io/series/vegetablesfordessert"


class FowlLanguageTapas(GenericTapasComic):
    """Class to retrieve Fowl Language comics."""

    # Also on http://www.fowllanguagecomics.com
    # Also on https://fowllanguagecomics.tumblr.com
    # Also on http://www.gocomics.com/fowl-language
    name = "fowllanguage-tapa"
    long_name = "Fowl Language Comics (from Tapas.io)"
    url = "https://tapas.io/series/Fowl-Language-Comics"
    _categories = ("FOWLLANGUAGE",)


class OscillatingProfundities(GenericTapasComic):
    """Class to retrieve Oscillating Profundities comics."""

    name = "oscillating"
    long_name = "Oscillating Profundities"
    url = "https://tapas.io/series/oscillatingprofundities"


class ZnoflatsComics(GenericTapasComic):
    """Class to retrieve Znoflats comics."""

    name = "znoflats"
    long_name = "Znoflats Comics"
    url = "https://tapas.io/series/Znoflats-Comics"


class SandersenTapas(GenericTapasComic):
    """Class to retrieve Sarah Andersen comics."""

    # Also on http://sarahcandersen.com
    # Also on http://www.gocomics.com/sarahs-scribbles
    name = "sandersen-tapa"
    long_name = "Sarah Andersen (from Tapas.io)"
    url = "https://tapas.io/series/Doodle-Time"


class TubeyToonsTapas(GenericTapasComic):
    """Class to retrieve TubeyToons comics."""

    # Also on http://tubeytoons.com
    # Also on https://tubeytoons.tumblr.com
    name = "tubeytoons-tapa"
    long_name = "Tubey Toons (from Tapas.io)"
    url = "https://tapas.io/series/Tubey-Toons"
    _categories = ("TUBEYTOONS",)


class AnythingComicTapas(GenericTapasComic):
    """Class to retrieve Anything Comics."""

    # Also on http://www.anythingcomic.com
    # Also on https://www.smackjeeves.com/discover/articleList?titleNo=50399
    name = "anythingcomic-tapa"
    long_name = "Anything Comic (from Tapas.io)"
    url = "https://tapas.io/series/anything"
    _categories = ("ANYTHING",)


class UnearthedComicsTapas(GenericTapasComic):
    """Class to retrieve Unearthed comics."""

    # Also on http://unearthedcomics.com
    # Also on https://unearthedcomics.tumblr.com
    name = "unearthed-tapa"
    long_name = "Unearthed Comics (from Tapas.io)"
    url = "https://tapas.io/series/UnearthedComics"
    _categories = ("UNEARTHED",)


class EverythingsStupidTapas(GenericTapasComic):
    """Class to retrieve Everything's stupid Comics."""

    # Also on http://www.webtoons.com/en/challenge/everythings-stupid/list?title_no=14591
    # Also on http://everythingsstupid.net
    name = "stupid-tapa"
    long_name = "Everything's Stupid (from Tapas.io)"
    url = "https://tapas.io/series/EverythingsStupid"


class JustSayEhTapas(GenericTapasComic):
    """Class to retrieve Just Say Eh comics."""

    # Also on http://www.justsayeh.com
    name = "justsayeh-tapa"
    long_name = "Just Say Eh (from Tapas.io)"
    url = "https://tapas.io/series/Just-Say-Eh"


class ThorsThundershackTapas(GenericTapasComic):
    """Class to retrieve Thor's Thundershack comics."""

    # Also on http://www.thorsthundershack.com
    name = "thor-tapa"
    long_name = "Thor's Thundershack (from Tapas.io)"
    url = "https://tapas.io/series/Thors-Thundershac"
    _categories = ("THOR",)


class OwlTurdTapas(GenericTapasComic):
    """Class to retrieve Owl Turd / Shen comix."""

    # Also on http://shencomix.com
    # Also on http://shencomix.tumblr.com
    # Also on https://www.gocomics.com/shen-comix
    name = "owlturd-tapa"
    long_name = "Owl Turd / Shen Comix (from Tapas.io)"
    url = "https://tapas.io/series/Shen-Comix"
    _categories = ("OWLTURD", "SHENCOMIX")


class GoneIntoRaptureTapas(GenericTapasComic):
    """Class to retrieve Gone Into Rapture comics."""

    # Also on http://goneintorapture.tumblr.com
    # Also on https://goneintorapture.com
    name = "rapture-tapa"
    long_name = "Gone Into Rapture (from Tapas.io)"
    url = "https://tapas.io/series/Goneintorapture"


class HeckIfIKnowComicsTapas(GenericTapasComic):
    """Class to retrieve Heck If I Know Comics."""

    # Also on https://heckifiknowcomics.com
    name = "heck-tapa"
    long_name = "Heck if I Know comics (from Tapas.io)"
    url = "https://tapas.io/series/Regular"


class CheerUpEmoKidTapas(GenericTapasComic):
    """Class to retrieve CheerUpEmoKid comics."""

    # Also on http://www.cheerupemokid.com
    # Also on https://enzocomics.tumblr.com
    name = "cuek-tapa"
    long_name = "Cheer Up Emo Kid (from Tapas.io)"
    url = "https://tapas.io/series/CUEK"


class BigFootJusticeTapas(GenericTapasComic):
    """Class to retrieve Big Foot Justice comics."""

    # Also on http://bigfootjustice.com
    name = "bigfoot-tapa"
    long_name = "Big Foot Justice (from Tapas.io)"
    url = "https://tapas.io/series/bigfoot-justice"


class UpAndOutTapas(GenericTapasComic):
    """Class to retrieve Up & Out comics."""

    # Also on https://upandoutcomic.tumblr.com
    name = "upandout-tapa"
    long_name = "Up And Out (from Tapas.io)"
    url = "https://tapas.io/series/UP-and-OUT"


class ToonHoleTapas(GenericTapasComic):
    """Class to retrieve Toon Holes comics."""

    # Also on http://www.toonhole.com
    name = "toonhole-tapa"
    long_name = "Toon Hole (from Tapas.io)"
    url = "https://tapas.io/series/TOONHOLE"


class AngryAtNothingTapas(GenericTapasComic):
    """Class to retrieve Angry at Nothing comics."""

    # Also on http://www.angryatnothing.net
    # Also on https://angryatnothing.tumblr.com
    name = "angry-tapa"
    long_name = "Angry At Nothing (from Tapas.io)"
    url = "https://tapas.io/series/Comics-yeah-definitely-comics-"


class LeleozTapas(GenericTapasComic):
    """Class to retrieve Leleoz comics."""

    # Also on http://leleozcomics.tumblr.com
    name = "leleoz-tapa"
    long_name = "Leleoz (from Tapas.io)"
    url = "https://tapas.io/series/Leleoz"


class TheAwkwardYetiTapas(GenericTapasComic):
    """Class to retrieve The Awkward Yeti comics."""

    # Also on http://www.gocomics.com/the-awkward-yeti
    # Also on http://theawkwardyeti.com
    # Also on https://larstheyeti.tumblr.com
    name = "yeti-tapa"
    long_name = "The Awkward Yeti (from Tapas.io)"
    url = "https://tapas.io/series/TheAwkwardYeti"
    _categories = ("YETI",)


class AsPerUsualTapas(GenericTapasComic):
    """Class to retrieve As Per Usual comics."""

    # Also on https://as-per-usual.tumblr.com
    name = "usual-tapa"
    long_name = "As Per Usual (from Tapas.io)"
    url = "https://tapas.io/series/AsPerUsual"
    categories = ("DAMILEE",)


class HotComicsForCoolPeopleTapas(GenericTapasComic):
    """Class to retrieve Hot Comics For Cool People."""

    # Also on https://hotcomicsforcoolpeople.tumblr.com
    # Also on http://hotcomics.biz (links to tumblr)
    # Also on http://hcfcp.com (links to tumblr)
    name = "hotcomics-tapa"
    long_name = "Hot Comics For Cool People (from Tapas.io)"
    url = "https://tapas.io/series/Hot-Comics-For-Cool-People"
    _categories = ("DAMILEE",)


class OneOneOneOneComicTapas(GenericTapasComic):
    """Class to retrieve 1111 Comics."""

    # Also on http://www.1111comics.me
    # Also on https://comics1111.tumblr.com
    name = "1111-tapa"
    long_name = "1111 Comics (from Tapas.io)"
    url = "https://tapas.io/series/1111-Comics"
    _categories = ("ONEONEONEONE",)


class TumbleDryTapas(GenericTapasComic):
    """Class to retrieve Tumble Dry comics."""

    # Also on http://tumbledrycomics.com
    name = "tumbledry-tapa"
    long_name = "Tumble Dry (from Tapas.io)"
    url = "https://tapas.io/series/TumbleDryComics"


class DeadlyPanelTapas(GenericTapasComic):
    """Class to retrieve Deadly Panel comics."""

    # Also on http://www.deadlypanel.com
    # Also on https://deadlypanel.tumblr.com
    name = "deadly-tapa"
    long_name = "Deadly Panel (from Tapas.io)"
    url = "https://tapas.io/series/deadlypanel"


class ChrisHallbeckMaxiTapas(GenericTapasComic):
    """Class to retrieve Chris Hallbeck comics."""

    # Also on https://chrishallbeck.tumblr.com
    # Also on http://maximumble.com
    name = "hallbeckmaxi-tapa"
    long_name = "Chris Hallback - Maximumble (from Tapas.io)"
    url = "https://tapas.io/series/Maximumble"
    _categories = ("HALLBACK",)


class ChrisHallbeckMiniTapas(GenericDeletedComic, GenericTapasComic):
    """Class to retrieve Chris Hallbeck comics."""

    # Also on https://chrishallbeck.tumblr.com
    # Also on http://minimumble.com
    name = "hallbeckmini-tapa"
    long_name = "Chris Hallback - Minimumble (from Tapas.io)"
    url = "https://tapas.io/series/Minimumble"
    _categories = ("HALLBACK",)


class ChrisHallbeckBiffTapas(GenericTapasComic):
    """Class to retrieve Chris Hallbeck comics."""

    # Also on https://chrishallbeck.tumblr.com
    # Also on http://thebookofbiff.com
    name = "hallbeckbiff-tapa"
    long_name = "Chris Hallback - The Book of Biff (from Tapas.io)"
    url = "https://tapas.io/series/The-Book-of-Biff"
    _categories = ("HALLBACK",)


class RandoWisTapas(GenericTapasComic):
    """Class to retrieve RandoWis comics."""

    # Also on https://randowis.com
    name = "randowis-tapa"
    long_name = "RandoWis (from Tapas.io)"
    url = "https://tapas.io/series/RandoWis"


class PigeonGazetteTapas(GenericTapasComic):
    """Class to retrieve The Pigeon Gazette comics."""

    # Also on https://thepigeongazette.tumblr.com
    name = "pigeon-tapa"
    long_name = "The Pigeon Gazette (from Tapas.io)"
    url = "https://tapas.io/series/The-Pigeon-Gazette"


class TheOdd1sOutTapas(GenericTapasComic):
    """Class to retrieve The Odd 1s Out comics."""

    # Also on http://theodd1sout.com
    # Also on https://theodd1sout.tumblr.com
    name = "theodd-tapa"
    long_name = "The Odd 1s Out (from Tapas.io)"
    url = "https://tapas.io/series/Theodd1sout"


class TheWorldIsFlatTapas(GenericTapasComic):
    """Class to retrieve The World Is Flat Comics."""

    # Also on https://theworldisflatcomics.tumblr.com
    name = "flatworld-tapa"
    long_name = "The World Is Flat (from Tapas.io)"
    url = "https://tapas.io/series/The-World-is-Flat"


class MisterAndMeTapas(GenericTapasComic):
    """Class to retrieve Mister & Me Comics."""

    # Also on http://www.mister-and-me.com
    # Also on http://www.gocomics.com/mister-and-me
    name = "mister-tapa"
    long_name = "Mister & Me (from Tapas.io)"
    url = "https://tapas.io/series/Mister-and-Me"


class TalesOfAbsurdityTapas(GenericDeletedComic, GenericTapasComic):
    """Class to retrieve Tales Of Absurdity comics."""

    # Also on http://talesofabsurdity.com
    # Also on http://talesofabsurdity.tumblr.com
    name = "absurdity-tapa"
    long_name = "Tales of Absurdity (from Tapas.io)"
    url = "https://tapas.io/series/Tales-Of-Absurdity"
    _categories = ("ABSURDITY",)


class BFGFSTapas(GenericTapasComic):
    """Class to retrieve BFGFS comics."""

    # Also on http://bfgfs.com
    # Also on https://bfgfs.tumblr.com
    name = "bfgfs-tapa"
    long_name = "BFGFS (from Tapas.io)"
    url = "https://tapas.io/series/BFGFS"


class DoodleForFoodTapas(GenericTapasComic):
    """Class to retrieve Doodle For Food comics."""

    # Also on https://www.doodleforfood.com
    name = "doodle-tapa"
    long_name = "Doodle For Food (from Tapas.io)"
    url = "https://tapas.io/series/Doodle-for-Food"


class MrLovensteinTapas(GenericTapasComic):
    """Class to retrieve Mr Lovenstein comics."""

    # Also on http://www.mrlovenstein.com
    name = "mrlovenstein-tapa"
    long_name = "Mr. Lovenstein (from Tapas.io)"
    url = "https://tapas.io/series/MrLovenstein"


class CassandraCalinTapas(GenericTapasComic):
    """Class to retrieve C. Cassandra comics."""

    # Also on http://cassandracalin.com
    # Also on https://c-cassandra.tumblr.com
    name = "cassandra-tapa"
    long_name = "Cassandra Calin (from Tapas.io)"
    url = "https://tapas.io/series/CassandraComics"


class WafflesAndPancakes(GenericTapasComic):
    """Class to retrieve Waffles And Pancakes comics."""

    # Also on http://wandpcomic.com
    name = "waffles"
    long_name = "Waffles And Pancakes"
    url = "https://tapas.io/series/Waffles-and-Pancakes"


class YesterdaysPopcornTapas(GenericTapasComic):
    """Class to retrieve Yesterday's Popcorn comics."""

    # Also on http://www.yesterdayspopcorn.com
    # Also on https://yesterdayspopcorn.tumblr.com
    name = "popcorn-tapa"
    long_name = "Yesterday's Popcorn (from Tapas.io)"
    url = "https://tapas.io/series/Yesterdays-Popcorn"


class OurSuperAdventureTapas(GenericTapasComic):
    """Class to retrieve Our Super Adventure comics."""

    # Also on http://www.oursuperadventure.com
    # https://sarahssketchbook.tumblr.com
    # http://sarahgraley.com
    name = "superadventure-tapa"
    long_name = "Our Super Adventure (from Tapas.io)"
    url = "https://tapas.io/series/OurSuperAdventure"


class NamelessPCs(GenericTapasComic):
    """Class to retrieve Nameless PCs comics."""

    # Also on http://namelesspcs.com
    name = "namelesspcs-tapa"
    long_name = "NamelessPCs (from Tapas.io)"
    url = "https://tapas.io/series/NamelessPC"
    _categories = ("WESLEYHALL",)


class PizzaDad(GenericTapasComic):
    """Class to retrieve Pizza Dad comics."""

    # Also on http://pizzadad.pizza
    name = "pizzadad-tapa"
    long_name = "Pizza Dad (from Tapas.io)"
    url = "https://tapas.io/series/PizzaDad"
    _categories = ("WESLEYHALL",)


class DownTheUpwardSpiralTapas(GenericDeletedComic, GenericTapasComic):
    """Class to retrieve Down The Upward Spiral comics."""

    # Also on http://www.downtheupwardspiral.com
    name = "spiral-tapa"
    long_name = "Down the Upward Spiral (from Tapas.io)"
    url = "https://tapas.io/series/Down-the-Upward-Spiral"


class FalseKneesTapas(GenericTapasComic):
    """Class to retrieve False Knees comics."""

    # Also on https://falseknees.com
    # Also on https://falseknees.tumblr.com
    # Also on http://www.webtoons.com/en/challenge/false-knees/list?title_no=79544
    name = "falseknees-tapa"
    long_name = "False Knees (from Tapas.io)"
    url = "https://tapas.io/series/FalseKnees"
    _categories = ("FALSEKNEES",)


class UbertoolTapas(GenericTapasComic):
    """Class to retrieve Ubertool comics."""

    # Also on http://ubertoolcomic.com
    # Also on https://ubertool.tumblr.com
    name = "ubertool-tapa"
    long_name = "Ubertool (from Tapas.io)"
    url = "https://tapas.io/series/ubertool"
    _categories = ("UBERTOOL",)


class BarteNerdsTapas(GenericTapasComic):
    """Class to retrieve BarteNerds comics."""

    # Also on http://www.bartenerds.com
    name = "bartenerds-tapa"
    long_name = "BarteNerds (from Tapas.io)"
    url = "https://tapas.io/series/BarteNERDS"


class SmallBlueYonderTapas(GenericTapasComic):
    """Class to retrieve Small Blue Yonder comics."""

    # Also on http://www.smallblueyonder.com
    name = "smallblue-tapa"
    long_name = "Small Blue Yonder (from Tapas.io)"
    url = "https://tapas.io/series/Small-Blue-Yonder"


class TizzyStitchBirdTapas(GenericTapasComic):
    """Class to retrieve Tizzy Stitch Bird comics."""

    # Also on http://tizzystitchbird.com
    # Also on https://tizzystitchbird.tumblr.com
    # Also on http://www.webtoons.com/en/challenge/tizzy-stitchbird/list?title_no=50082
    name = "tizzy-tapa"
    long_name = "Tizzy Stitch Bird (from Tapas.io)"
    url = "https://tapas.io/series/TizzyStitchbird"


class RockPaperCynicTapas(GenericTapasComic):
    """Class to retrieve RockPaperCynic comics."""

    # Also on http://www.rockpapercynic.com
    # Also on https://rockpapercynic.tumblr.com
    name = "rpc-tapa"
    long_name = "Rock Paper Cynic (from Tapas.io)"
    url = "https://tapas.io/series/rockpapercynic"


class IsItCanonTapas(GenericTapasComic):
    """Class to retrieve Is It Canon comics."""

    # Also on http://www.isitcanon.com
    name = "canon-tapa"
    long_name = "Is It Canon (from Tapas.io)"
    url = "https://tapas.io/series/isitcanon"


class ItsTheTieTapas(GenericDeletedComic, GenericTapasComic):
    """Class to retrieve It's the tie comics."""

    # Also on http://itsthetie.com
    # Also on https://itsthetie.tumblr.com
    name = "tie-tapa"
    long_name = "It's the tie (from Tapas.io)"
    url = "https://tapas.io/series/itsthetie"
    _categories = ("TIE",)


class JamesOfNoTradesTapas(GenericTapasComic):
    """Class to retrieve JamesOfNoTrades comics."""

    # Also on http://jamesofnotrades.com
    # Also on http://www.webtoons.com/en/challenge/james-of-no-trades/list?title_no=43422
    # Also on https://jamesfregan.tumblr.com
    name = "jamesofnotrades-tapa"
    long_name = "James Of No Trades (from Tapas.io)"
    url = "https://tapas.io/series/James-of-No-Trades"
    _categories = ("JAMESOFNOTRADES",)


class MomentumTapas(GenericTapasComic):
    """Class to retrieve Momentum comics."""

    # Also on http://www.momentumcomic.com
    name = "momentum-tapa"
    long_name = "Momentum (from Tapas.io)"
    url = "https://tapas.io/series/momentum"


class InYourFaceCakeTapas(GenericTapasComic):
    """Class to retrieve In Your Face Cake comics."""

    # Also on https://in-your-face-cake.tumblr.com
    name = "inyourfacecake-tapa"
    long_name = "In Your Face Cake (from Tapas.io)"
    url = "https://tapas.io/series/In-Your-Face-Cake"
    _categories = ("INYOURFACECAKE",)


class CowardlyComicsTapas(GenericTapasComic):
    """Class to retrieve Cowardly Comics."""

    # Also on https://cowardlycomics.tumblr.com
    # Also on http://www.webtoons.com/en/challenge/cowardly-comics/list?title_no=65893
    name = "cowardly-tapa"
    long_name = "Cowardly Comics (from Tapas.io)"
    url = "https://tapas.io/series/CowardlyComics"


class Caw4hwTapas(GenericTapasComic):
    """Class to retrieve Caw4hw comics."""

    # Also on https://caw4hw.tumblr.com
    name = "caw4hw-tapa"
    long_name = "Caw4hw (from Tapas.io)"
    url = "https://tapas.io/series/CAW4HW"


class DontBeDadTapas(GenericTapasComic):
    """Class to retrieve Don't Be Dad comics."""

    # Also on https://dontbedad.com/
    # Also on http://www.webtoons.com/en/challenge/dontbedad/list?title_no=123074
    name = "dontbedad-tapa"
    long_name = "Don't Be Dad (from Tapas.io)"
    url = "https://tapas.io/series/DontBeDad-Comics"


class APleasantWasteOfTimeTapas(GenericTapasComic):
    """Class to retrieve A Pleasant Waste Of Time comics."""

    # Also on https://artjcf.tumblr.com
    name = "pleasant-waste-tapa"
    long_name = "A Pleasant Waste Of Time (from Tapas.io)"
    url = "https://tapas.io/series/A-Pleasant-"
    _categories = ("WASTE",)


class InfiniteImmortalBensTapas(GenericTapasComic):
    """Class to retrieve Infinite Immortal Bens comics."""

    # Also on http://www.webtoons.com/en/challenge/infinite-immortal-bens/list?title_no=32847
    # Also on https://infiniteimmortalbens.tumblr.com
    url = "https://tapas.io/series/Infinite-Immortal-Bens"
    name = "infiniteimmortal-tapa"
    long_name = "Infinite Immortal Bens (from Tapas.io)"
    _categories = ("INFINITEIMMORTAL",)


class EatMyPaintTapas(GenericTapasComic):
    """Class to retrieve Eat My Paint comics."""

    # Also on https://eatmypaint.tumblr.com
    # Also on https://www.webtoons.com/en/challenge/eatmypaint/list?title_no=31150&page=1
    # Also on https://www.eatmypaint.co.uk
    name = "eatmypaint-tapa"
    long_name = "Eat My Paint (from Tapas.io)"
    url = "https://tapas.io/series/eatmypaint"
    _categories = ("EATMYPAINT",)


class RoryTapas(GenericTapasComic):
    """Class to retrieve Rory comics."""

    # Also on https://rorycomics.tumblr.com/
    name = "rory-tapa"
    long_name = "Rory (from Tapas.io)"
    url = "https://tapas.io/series/rorycomics"
    _categories = ("RORY",)


class LightRoastComicsTapas(GenericTapasComic):
    """Class to retrieve Light Roast Comics."""

    # Also on http://lightroastcomics.com
    # Also on https://www.webtoons.com/en/challenge/light-roast-comics/list?title_no=171110&page=1
    # Also on https://www.instagram.com/lightroastcomics/?hl=fr
    name = "lightroast-tapa"
    long_name = "Light Roast Comics (from Tapas.io)"
    url = "https://tapas.io/series/Light-Roast-Comics"
    _categories = ("LIGHTROAST",)


class MercworksTapas(GenericTapasComic):
    """Class to retrieve Mercworks comics."""

    # Also on http://mercworks.net
    # Also on http://www.webtoons.com/en/comedy/mercworks/list?title_no=426
    # Also on https://mercworks.tumblr.com
    name = "mercworks-tapa"
    long_name = "Mercworks (from Tapas.io)"
    url = "https://tapas.io/series/MercWorks"
    _categories = ("MERCWORKS",)


class PtbdTapas(GenericTapasComic):
    "Class to retrieve Pretends to be drawing comics." ""
    # Also on https://ptbd.jwels.berlin
    # Also on https://www.webtoons.com/en/challenge/pretends-to-be-drawing/list?title_no=109952
    # Also on https://www.instagram.com/pretendstobedrawing/
    name = "ptbd-tapa"
    long_name = "Pretends to be drawing (from Tapas.io)"
    url = "https://tapas.io/series/ptbd"
    _categories = ("PTBD",)


class BecksComicsTapas(GenericTapasComic):
    """Class to retrieve Becks Comics."""

    # Also on https://www.beckscomics.com
    # Also on https://www.instagram.com/beckscomics/
    name = "becks-tapa"
    long_name = "Becks Comics (from Tapas.io)"
    url = "https://tapas.io/series/beckscomics"
    _categories = ("BECKS",)


class RespawnComicTapas(GenericTapasComic):
    """Class to retrieve Respawn Comic."""

    # Also on http://respawncomic.com
    # Also on https://respawncomic.tumblr.com
    name = "respawn-tapa"
    long_name = "Respawn Comic (from Tapas.io)"
    url = "https://tapas.io/series/respawncomic"
    _categories = ("RESPAWN",)


class AbsurdoLapin(GenericNavigableComic):
    """Class to retrieve Absurdo Lapin comics."""

    name = "absurdo"
    long_name = "Absurdo"
    url = "https://absurdo.lapin.org"
    get_url_from_link = join_cls_url_to_href

    @classmethod
    def get_nav(cls, soup):
        """Get the navigation elements from soup object."""
        cont = soup.find("div", id="content1")
        _, b2 = cont.find_all("div", class_="buttons")
        links = b2.find_all("a")
        nb_links = len(links)
        if nb_links == 4:  # on most pages
            prev, first, last, next_ = links
        elif nb_links == 3:  # on first page
            first, last, next_ = links
            prev = None
        elif nb_links == 2:  # on last page
            prev, first = links
            next_ = last = None
        else:
            assert False
        return (prev, first, last, next_)

    @classmethod
    def get_first_comic_link(cls):
        """Get link to first comics."""
        return cls.get_nav(get_soup_at_url(cls.url))[1]

    @classmethod
    def get_navi_link(cls, last_soup, next_):
        """Get link to next or previous comic."""
        return cls.get_nav(last_soup)[3 if next_ else 0]

    @classmethod
    def get_comic_info(cls, soup, link):
        """Get information about a particular comics."""
        author = soup.find("meta", attrs={"name": "author"})["content"]
        tags = soup.find("meta", attrs={"name": "keywords"})["content"]
        title = soup.find("title").string
        imgs = soup.find("div", id="content1").find_all("img")
        return {
            "title": title,
            "img": [
                convert_iri_to_plain_ascii_uri(urljoin_wrapper(cls.url, i["src"]))
                for i in imgs
            ],
            "tags": tags,
            "author": author,
        }


class AuFondDuTrou(GenericNavigableComic):

    name = "fonddutrou"
    long_name = "Au fond du trou"
    url = "http://aufonddutrou.fr"
    _categories = ("FRANCAIS",)
    get_first_comic_link = simulate_first_link
    first_url = "http://aufonddutrou.fr/strip-1/"

    @classmethod
    def get_navi_link(cls, last_soup, next_):
        """Get link to next or previous comic."""
        return last_soup.find("a", class_="single-navigation previous-post" if next_ else "single-navigation next-post")

    @classmethod
    def get_comic_info(cls, soup, link):
        date_str = soup.find("span", class_="post-date").string
        imgs = soup.find("div", class_="post-content").find_all("img")
        title = soup.find("h1", class_="post-title").string
        return {
            "date": string_to_date(date_str, "%d %B %Y", "fr_FR.utf8"),
            "img": [convert_iri_to_plain_ascii_uri(i["src"]) for i in imgs],
            "title": title,
        }


class DogmoDog(GenericComicNotWorking, GenericNavigableComic):
    """Class to retrieve Dogmo Dogs comics."""

    name = "dogmo"
    long_name = "Dogmo Dog"
    url = "http://www.dogmodog.com"
    get_url_from_link = join_cls_url_to_href

    @classmethod
    def get_nav(cls, soup, title):
        """Get the navigation elements from soup object."""
        img = soup.find("img", title=title)
        return None if img is None else img.parent

    @classmethod
    def get_first_comic_link(cls):
        """Get link to first comics."""
        return cls.get_nav(get_soup_at_url(cls.url), "First")

    @classmethod
    def get_navi_link(cls, last_soup, next_):
        """Get link to next or previous comic."""
        link = cls.get_nav(last_soup, "Next" if next_ else "Previous")
        # Trick because a next can lead to an error page
        if link:
            url = cls.get_url_from_link(link)
            if url == "http://www.dogmodog.com/error.php":
                return None
        return link

    @classmethod
    def get_comic_info(cls, soup, link):
        """Get information about a particular comics."""
        div = soup.find("div", id="Comic")
        if div is None:
            return None
        imgs = div.find_all("img")
        return {
            "img": [urljoin_wrapper(cls.url, i["src"]) for i in imgs],
        }


def get_subclasses(klass):
    """Gets the list of direct/indirect subclasses of a class"""
    subclasses = klass.__subclasses__()
    for derived in list(subclasses):
        subclasses.extend(get_subclasses(derived))
    return subclasses


def remove_st_nd_rd_th_from_date(string):
    """Function to transform 1st/2nd/3rd/4th in a parsable date format."""
    # Hackish way to convert string with numeral "1st"/"2nd"/etc to date
    return (
        string.replace("st", "")
        .replace("nd", "")
        .replace("rd", "")
        .replace("th", "")
        .replace("Augu", "August")
    )


def string_to_date(string, date_format, local=DEFAULT_LOCAL):
    """Function to convert string to date object.
    Wrapper around datetime.datetime.strptime."""
    # format described in https://docs.python.org/3.8/library/datetime.html#strftime-and-strptime-behavior
    prev_locale = locale.setlocale(locale.LC_ALL)
    if local != prev_locale:
        locale.setlocale(locale.LC_ALL, local)
    ret = datetime.datetime.strptime(string, date_format).date()
    if local != prev_locale:
        locale.setlocale(locale.LC_ALL, prev_locale)
    return ret


def isoformat_to_date(string):
    """Fonction to convert string in isoformat to date object."""
    # 2019-08-17T14:25:35+00:00
    return string_to_date(string[:10], "%Y-%m-%d")


def dict_to_date(d):
    """Function to get date from dict with keys 'year', 'month' & 'day'."""
    return date(int(d["year"]), int(d["month"]), int(d["day"]))


def regexp_match_to_date(match):
    """Function to get date from re match object (with named capture)."""
    return dict_to_date(match.groupdict())


# Collect comics
COMICS = set(get_subclasses(GenericComic))
VALID_COMICS = [c for c in COMICS if c.name is not None]
# Create dict mapping names and categories to comics
COMICS_DICT = {}
for comic in VALID_COMICS:
    name = comic.name
    assert name not in COMICS_DICT
    assert name.lower() == name
    COMICS_DICT[name] = [comic]
    for cat in comic.get_categories():
        assert cat.upper() == cat
        assert cat.lower() != cat
        COMICS_DICT.setdefault(cat, []).append(comic)
