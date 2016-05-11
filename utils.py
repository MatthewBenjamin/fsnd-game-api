# utils.py - General use functions

import endpoints
from google.appengine.ext import ndb

from models import Game

def get_by_urlsafe(urlsafe_key, model):
    try:
        key = ndb.Key(urlsafe=urlsafe_key)
    except TypeError:
        raise endpoints.BadRequestException('Invalid Key')
    except Exception, e:
        if e.__class__.__name__ == 'ProtocolBufferDecodeError':
            raise endpoints.BadRequestException('Invalid Key')
        else:
            raise

    entity = key.get()
    if not entity:
        return None
    if not isinstance(entity, model):
        raise ValueError('Incorrect Kind')
    return entity

def get_games_by_username(username):
    games = Game.query(Game.users.IN((username,))).fetch()
    return games
