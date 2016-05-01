# utils.py - General use functions

from google.appengine.ext import ndb

# TODO: add error handling
def get_by_urlsafe(urlsafe_key, model):
    value = ndb.Key(urlsafe=urlsafe_key).get()
    if isinstance(value, model):
        return value