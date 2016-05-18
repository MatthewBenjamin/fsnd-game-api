# utils.py - General use functions

import endpoints
from google.appengine.ext import ndb

from models import Game, User

def get_by_urlsafe(urlsafe_key, model):
    """Returns a datastore entity by urlsafe key"""
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
        raise endpoints.NotFoundException("Entity not found")
    if not isinstance(entity, model):
        raise ValueError('Incorrect Kind')
    return entity


def get_games_by_username(username):
    """Get games by unique username"""
    games = Game.query(Game.users.IN((username,))).fetch()
    if not games and not User.query(User.name == username).get():
        raise endpoints.NotFoundException('User does not exist')
    return games

def get_user_by_gplus():
    """Returns User associated with gplus account"""
    g_user = endpoints.get_current_user()
    if not g_user:
        raise endpoints.UnauthorizedException('Authorization required')
    user = User.query(User.email == g_user.email()).get()
    if not user:
        raise endpoints.NotFoundException('User with %s gplus account does not exist' % g_user.email())
    return user
