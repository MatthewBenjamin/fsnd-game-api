from google.appengine.ext import ndb
from protorpc import messages

class User(ndb.Model):
    name = ndb.StringProperty(required=True)
    email = ndb.StringProperty()

# ?
#class UserForm(messages.Message)
#    name = messages.StringField(1)
#    email = messages.StringField(2)
#    user_key = messages.StringField(3)

class Game(ndb.Model):
    current_int = ndb.IntegerProperty(required=True, default=0)
    max_int = ndb.IntegerProperty(required=True, default=31)
    max_increment = ndb.IntegerProperty(required=True, default=3)
    game_over = ndb.BooleanProperty(required=True, default=False)
    user_keys = ndb.KeyProperty(repeated=True, kind='User')

    def to_form(self):
        form = GameForm()
        form.current_int = self.current_int
        form.max_int = self.max_int
        form.max_increment = self.max_increment
        form.game_over = self.game_over
        form.urlsafe_game_key = self.key.urlsafe()
        for user_key in self.user_keys:
            form.urlsafe_user_keys.append(user_key.urlsafe())
        return form

class GameForm(messages.Message):
    current_int = messages.IntegerField(1, variant=messages.Variant.INT32)
    max_int = messages.IntegerField(2, variant=messages.Variant.INT32)
    max_increment = messages.IntegerField(3, variant=messages.Variant.INT32)
    game_over = messages.BooleanField(4)
    urlsafe_user_keys = messages.StringField(5, repeated=True)
    urlsafe_game_key = messages.StringField(6)

class GameHistory(ndb.Model):
    user_name = ndb.StringProperty(repeated=True)
    move = ndb.IntegerProperty(repeated=True)

class GameHistoryForm(messages.Message):
    user_name = messages.StringField(1, repeated=True)
    move = messages.StringField(2, repeated=True)

class Result(ndb.Model):
    # descendant of user
    # game = ndb.keyProperty(required=True, kind='Game') ?
    datetime  = ndb.DateTimeProperty(required=True)
    won = ndb.BooleanProperty(required=True)
    #points = float? (1.0 / winning # of players - i.e. 1 point for win divided among winners)
    #           - still need won bool?

class StringMessage(messages.Message):
    """StringMessage -- outbound (single) string message"""
    message = messages.StringField(1, required=True)