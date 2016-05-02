from google.appengine.ext import ndb
from protorpc import messages

class User(ndb.Model):
    name = ndb.StringProperty(required=True)
    email = ndb.StringProperty()

class Game(ndb.Model):
    current_int = ndb.IntegerProperty(required=True, default=0)
    max_int = ndb.IntegerProperty(required=True, default=31)
    max_increment = ndb.IntegerProperty(required=True, default=3)
    game_over = ndb.BooleanProperty(required=True, default=False)
    users = ndb.StringProperty(repeated=True)

    def to_form(self, message=None):
        form = GameForm()
        form.current_int = self.current_int
        form.max_int = self.max_int
        form.max_increment = self.max_increment
        form.game_over = self.game_over
        form.urlsafe_game_key = self.key.urlsafe()
        form.users = self.users
        form.message = message
        return form

class GameForm(messages.Message):
    current_int = messages.IntegerField(1, variant=messages.Variant.INT32)
    max_int = messages.IntegerField(2, variant=messages.Variant.INT32)
    max_increment = messages.IntegerField(3, variant=messages.Variant.INT32)
    game_over = messages.BooleanField(4)
    users = messages.StringField(5, repeated=True)
    urlsafe_game_key = messages.StringField(6)
    message = messages.StringField(7)

class GameForms(messages.Message):
    games = messages.MessageField(GameForm, 1, repeated=True)

class MoveRecord(ndb.Model):
    username = ndb.StringProperty(required=True)
    move = ndb.IntegerProperty(required=True)

    #TODO to_form()
    def to_form(self):
        form = MoveRecordForm()
        form.name = self.username
        form.move = self.move
        return form

class GameHistory(ndb.Model):
    moves = ndb.StructuredProperty(MoveRecord, repeated=True)

    def add_move(self,username,move):
        self.moves.append(MoveRecord(username=username,move=move))

    def to_form(self):
        return GameHistoryForm(moves=[move.to_form() for move in self.moves])

class MoveRecordForm(messages.Message):
    name = messages.StringField(1, required=True)
    move = messages.IntegerField(2, required=True, variant=messages.Variant.INT32)

class GameHistoryForm(messages.Message):
    moves = messages.MessageField(MoveRecordForm, 1, repeated=True)

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