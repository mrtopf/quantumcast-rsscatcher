# -*- coding: utf8 -*-
import pymongo
import feedparser
import calendar
import hashlib
from time import mktime
from datetime import datetime
from bs4 import BeautifulSoup
import lxml.html
import textwrap

VALID_TAGS = ['strong', 'em', 'p', 'ul', 'li', 'br']

def sanitize_html(value):

    soup = BeautifulSoup(value)

    for tag in soup.findAll(True):
        if tag.name not in VALID_TAGS:
            tag.hidden = True
    return soup.prettify()

def extract_text(html):
    t = lxml.html.fromstring(html)
    return t.text_content()

def shorten(text, w=50):
    """shorten a text to ``w`` words"""
    l = text.split()
    if len(l)<=w:
        return text
    return " ".join(l[:w])+" ..."


class FeedCatcher:
    """The FeedCatcher class is responsible for reading pre-registered RSS or Atom feeds
    to a MongoDB collection"""

    def __init__(self, sources, items):
        """initialize the ``FeedCatcher`` class. 

        :param sources: The MongoDB collection object pointing to the collection holding the sources.
            Sources needs to consists of title and RSS/Atom url.
        :param items: The MongoDB collection object pointing to the collection where feed items will 
            be stored
        """
        self.sources = sources
        self.items   = items

    def catch(self):
        """update all feeds"""
        for source in self.sources.find():
            feed = feedparser.parse(source['url'])

            print "Updating %s" % source['title']
            for entry in feed.entries:
                item = {
                    'link' : entry.link,
                    'title' : entry.title,
                }
                if "updated" in entry:
                    d = entry.updated_parsed
                elif "published" in entry:
                    d = entry.published_parsed
                else:
                    d = None
                if d is not None:
                    d = datetime.fromtimestamp(mktime(d))
                else:
                    d = datetime.datetime.now()
                item['date'] = d

                if "content" in entry:
                    summary = extract_text(" ".join([l['value'] for l in entry.content]))
                elif "summary" in entry:
                    summary = extract_text(entry.summary)
                else:
                    summary = ""
                item['summary'] = summary
                item['short_summary'] = shorten(summary)
                item['_id'] = hashlib.new("MD5", entry.link).hexdigest()
                item['source'] = {
                    '_id' : source['_id'],
                    'title' : source['title'],
                    'url' : source['url'],
                }
                self.items.save(item)

if __name__ == '__main__':
    db = pymongo.Connection().rss
    fc = FeedCatcher(db.sources, db.items)
    fc.catch()

