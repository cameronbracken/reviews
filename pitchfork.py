#!/usr/bin/env python

"""
An unofficial API for pitchfork.com reviews.

author: Cameron Bracken 
email: cameron.bracken@gmail.com

heavily modified from code by:
    Michal Czaplinski <mmczaplinski@gmail.com>
"""

from __future__ import absolute_import, division, print_function, unicode_literals
import json
import re
import difflib
import sys
from bs4 import BeautifulSoup
from datetime import datetime, date
import time


if sys.version_info >= (3, 0):
    from urllib.parse import urljoin
    from urllib.request import urlopen
    from urllib.request import Request
else:
    from urllib2 import urlopen, Request
    from urlparse import urljoin

import logging 

logger = logging.getLogger(__name__)
logger.setLevel(logging.ERROR)

# create a file handler
handler_error = logging.FileHandler('error.log')
handler_error.setLevel(logging.ERROR)

# add the handlers to the logger
logger.addHandler(handler_error)

class Review(object):
    """
    Class representing the fetched review.
    Includes methods for getting the score, the text of the review
    (editorial), the album cover, label, year as well as the true
    (matched) album and artist names.
    """

    def __init__(self, url, soup):
        self.url = url
        self.soup = soup
        self.max_score = '10'

    def error_value(default):
        def wrap(f):
            def inner(*a):
                try:
                    return f(*a)
                except Exception, e:
                    logger.error("Pitchfork Error: %s",datetime.today().date())
                    return default
            return inner
        return wrap

    @error_value('')
    def score(self):
        """ Returns the album score. """
        return self.soup.find(class_='score').text.strip()

    @error_value('')
    def editorial(self):
        """ Returns the text of the review. """
        return self.soup.find(class_='review-text').get_text()

    @error_value('')
    def cover(self):
        """ Returns the link to the album cover. """
        return self.soup.find(class_='album-art').img['src'].strip()

    @error_value('')
    def artist(self):
        """ Returns the artist name. """
        return self.soup.find(class_='artist-links').get_text().strip()

    @error_value('')
    def album(self):
        """ Returns the album name. """
        return self.soup.find(class_='review-title').get_text().strip()

    @error_value('')
    def label(self):
        """ Returns the name of the record label that released the album. """
        return self.soup.find(class_='labels-list').get_text()

    @error_value('')
    def genre(self):
        """Returns the genre."""
        return self.soup.find(class_='genre-list').get_text(separator='/') 

    @error_value('')
    def date_reviewed(self):
        """Returns the date the review was published."""
        return datetime.strptime(self.soup.find(class_='pub-date')['datetime'],
                                 '%Y-%m-%dT%H:%M:%S').date()

    @error_value('')
    def special(self):
        """BNM/BNR tag"""
        special = self.soup.find(class_='bnm-txt')
        return '' if special is None else special.text

    @error_value('')
    def year(self):
        """
        Returns the year the album was released.
        In case of a reissue album, the year of original release as well as
        the year of the reissue is given separated by '/'.
        """
        return self.soup.find(class_='year').contents[1].get_text()

    def __repr__(self):
        return self.__class__.__name__+repr((self.artist(),self.album()))


class MultiReview(Review):

    def __init__(self, url, soup):
        self.url = url
        self.soup = soup
        self.max_score = '10'

    def score(self):
        """ Returns a list of album scores. """
        return [x.get_text() for x in self.soup.findAll(class_='score')]

    def album(self):
        """ Returns the name of the record label that released the album. """
        return [x.get_text() for x in self.soup.findAll(class_='review-title')]

    def label(self):
        """ Returns the name of the record label that released the album. """
        return [x.get_text() for x in self.soup.findAll(class_='label-list')]

    def cover(self):
        """ Returns a list of links to the album covers. """
        return [x.img['src'] for x in self.soup.findAll(class_='album-art')]

    def year(self):
        """
        Returns the year the album was released.
        In case of a reissue album, the year of original release as well as
        the year of the reissue is given separated by '/'.
        """
        raw_years = self.soup.findAll(class_='year')
        return [x.get_text()[2:].strip() for x in raw_years]

def get_review(url):
    # fetch the review page
    request = Request(url=url,
                      data=None,
                      headers={'User-Agent': 'the-pulse/pitchfork'})
    soup = BeautifulSoup(urlopen(request).read(), "lxml")

    # check if the review has multiple albums
    if soup.find(class_='album-picker') is None:
        return Review(url, soup)
    else:
        return MultiReview(url, soup)


def get_recent_reviews(n=None):
    """
    Get the n most recent reviews from Pitchfork. If n is not specefied,
    get all the posts today (usually 4-5).
    Returns a list of Review or MultiReview objects depending on
    the type of review because some pitchfork reviews cover multiple albums.
    """
    from datetime import datetime, date, timedelta

    #start = time.clock()

    # get 5 most recent links
    review_url = 'http://pitchfork.com/reviews/albums/'

    # fetch the review page
    request = Request(url=review_url,
                      data=None,
                      headers={'User-Agent': 'the-pulse/pitchfork-v0.1'})
    soup = BeautifulSoup(urlopen(request).read(), "lxml")

    pub_dates = [datetime.strptime(x['datetime'],'%Y-%m-%dT%H:%M:%S') 
                    for x in soup.findAll(class_='pub-date')]
    
    today = datetime.today().date() #- timedelta(days=1)
    
    # these two for testing
    #next_year = datetime(2017,1,1).date()
    #a_date = datetime(2016,9,13).date()

    matches = [pub_date.date() >= today for pub_date in pub_dates]

    #import pdb; pdb.set_trace()

    # if there are no reviews (such as on a weekend), return an empty list
    reviews = []
    if sum(matches) > 0:
        all_urls = [x['href'] for x in soup.findAll(class_='review__link')]
        if n == None:
            urls = []
            for url,match in zip(all_urls,matches):
                if match is True:
                    urls.append(url)
        else: 
            urls = all_urls[0:n]    
        reviews = [get_review('http://pitchfork.com' + url) for url in urls]

    #print('Got {} Pitchfork reviews in {:.0} seconds'.format(len(reviews), 
    #       time.clock() - start))
    return list(set(reviews))

    
