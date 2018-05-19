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
from datetime import datetime, date, timedelta
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
        self.max_score = '5'
        self.content_detail = soup.find('section', class_='contentDetail')
        self.date_stuff = self.content_detail.find_all('li')[1].text.\
            replace('Released /','').strip().split(' ')

    def error_value(default):
        def wrap(f):
            def inner(*a):
                try:
                    return f(*a)
                except Exception, e:
                    logger.error("RA Error: %s",datetime.today().date())
                    return default
            return inner
        return wrap

    @error_value('')
    def score(self):
        """ Returns the album score. """
        return self.soup.find(class_='rating').get_text()[0:3]

    @error_value('')
    def editorial(self):
        """ Returns the text of the review. """
        return self.soup.find(class_='reviewContent').get_text()

    @error_value('')
    def cover(self):
        """ Returns the link to the album cover. """
        return self.soup.find('article', id='review-item').img['src']

    @error_value('')
    def artist(self):
        """ Returns the artist name. """
        return re.split('.-.', self.soup.find('h1').get_text())[0].strip()

    @error_value('')
    def album(self):
        """ Returns the album name. """
        return re.split('.-.', self.soup.find('h1').get_text())[1].strip()

    @error_value('')
    def label(self):
        """ Returns the name of the record label that released the album. """
        #review.soup.find('a', href=re.compile('.*record-label.*')).get_text()
        return self.content_detail.find_all('li')[0].a.text

    @error_value('')
    def genre(self):
        """ Returns genre. """
        #review.soup.find('a', href=re.compile('.*record-label.*')).get_text()
        return self.content_detail.find_all('li')[2].text.replace('Style /','').strip()

    @error_value('')
    def year(self):
        """
        Returns the year the album was released.
        In case of a reissue album, the year of original release as well as
        the year of the reissue is given separated by '/'.
        """
        return self.date_stuff[1]

    @error_value('')
    def date_reviewed(self):
        """
        Returns the date the album was reviewed.
        """
        date_string = self.soup.find(itemprop='dtreviewed')['datetime']
        return datetime.strptime(date_string,'%Y-%m-%d').date()

    @error_value('')
    def month(self):
        """
        Returns the month the album was released.
        """
        return datetime.strptime(self.date_stuff[0],'%B').strftime('%-m')

    @error_value('')
    def special(self):
        """Special flag"""
        recommended = bool(len(self.soup.find_all(class_='recommended')))
        return 'RA recommends' if recommended else ''

    def __repr__(self):
        return self.__class__.__name__+repr((self.artist(),self.album()))

def get_review(url):
    # fetch the review page
    request = Request(url=url,
                      data=None,
                      headers={'User-Agent': 'the-pulse/ra'})
    soup = BeautifulSoup(urlopen(request).read(), "lxml")

    # check if the review has multiple albums
    return Review(url, soup)

def remove_dupes(reviews):
    """Remove duplicate reviews based on artist and album"""
    
    if(len(reviews) == 0): 
        return(reviews)

    review_names = [r.artist() + " - " + r.album() for r in reviews]
    found_dupe = True
    while found_dupe:
        for i in range(len(reviews)):
            if review_names.count(review_names[i]) > 1:
                review_names.pop(i)
                reviews.pop(i)
                break
            if i == max(range(len(reviews))):
                found_dupe = False
    return(reviews)

def get_recent_reviews(n=None):
    """
    Get the n most recent reviews from Resident Advisor. 
    If n is not specefied, get all the posts from yesterday (usually 0-2).
    (Because RA posts reviews throughout the day, depending on when the scrip is run,
    some might get missed).
    Returns a list of Reviews or an empty list if none were published yesterday.
    """

    #start = time.clock()

    base_url = 'https://www.residentadvisor.net/'
    reviews = []

    review_sources = ['album','single','recommend']
    for review_source in review_sources:
        review_url = urljoin(base_url,'reviews.aspx?format={0}'.format(review_source))

        # fetch the review page
        request = Request(url=review_url,
                          data=None,
                          headers={'User-Agent': 'the-pulse/reviews-v0.1'})
        soup = BeautifulSoup(urlopen(request).read(), "lxml")

        urls = [x.a['href'] for x in soup.findAll('article')]
        
        today = datetime.today().date()
        yesterday = (datetime.today() - timedelta(1)).date()
        
        keep_going = True 
        i = 0
        imax = 5
        # loop through reviews, newest first, keeping all the ones published yesterday
        while keep_going or i >= imax:
            review = get_review(urljoin(base_url,urls[i]))
            i += 1
	    #print(i)
            if  i >= imax:
                keep_going = False
            if review.date_reviewed() == yesterday: 
                # the first review was published yesterday, so check for more
                reviews.append(review) 
            elif review.date_reviewed() == today:
                # skip over the reviews today, not ideal but allows us to be certain that 
                # no reviews are missed since ra releases reviews intermittently throughout the day
                pass
            else:
                # the current review is old, jump out
                keep_going = False

    #print(reviews)
    #print('Got {} RA reviews in {:.0} seconds'.format(len(reviews), time.clock() - start))
    return remove_dupes(reviews)


