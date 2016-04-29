from google.appengine.ext import ndb
from protorpc import messages

class User(ndb.Model):
    name = ndb.StringProperty(required=True)
    email = ndb.StringProperty()

class Game(ndb.Model):
    current_int = ndb.IntegerProperty(required=True, default=31)
    max_increment = ndb.IntegerProperty(required=True, default=3)
    game_over = ndb.BooleanProperty(required=True, default=False)
    user_keys = ndb.KeyProperty(repeated=True, kind='User')

class GameForm(messages.Message):
    current_int = messages.IntegerField(1, variant=messages.Variant.INT32)
    max_increment = messages.IntegerField(2, variant=messages.Variant.INT32)
    game_over = messages.BooleanField(3)
    # return user keys?
    # return websafe game key?
class Result(ndb.Model):
    # descendant of user
    # game = ndb.keyProperty(required=True, kind='Game') ?
    datetime  = ndb.DateTimeProperty(required=True)
    won = ndb.BooleanProperty(required=True)
    # num of opponents? or just link to game?

class StringMessage(messages.Message):
    """StringMessage -- outbound (single) string message"""
    message = messages.StringField(1, required=True)