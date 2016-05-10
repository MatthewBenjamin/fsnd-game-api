from google.appengine.ext import ndb
from protorpc import messages

from random import shuffle

class User(ndb.Model):
    name = ndb.StringProperty(required=True)
    email = ndb.StringProperty()
    rating = ndb.FloatProperty(default=0)

    def to_form(self):
        form = UserForm()
        form.name = self.name
        #form.email = self.email
        form.rating = self.rating
        return form

class UserForm(messages.Message):
    name = messages.StringField(1, required=True)
    #email = messages.StringField(2)
    rating = messages.FloatField(3)

class UserForms(messages.Message):
    users = messages.MessageField(UserForm, 1, repeated=True)

class Game(ndb.Model):
    current_int = ndb.IntegerProperty(required=True, default=0)
    max_int = ndb.IntegerProperty(required=True, default=31)
    max_increment = ndb.IntegerProperty(required=True, default=3)
    game_over = ndb.BooleanProperty(required=True, default=False)
    users = ndb.StringProperty(repeated=True)
    created = ndb.DateTimeProperty(auto_now_add=True)
    last_update = ndb.DateTimeProperty(auto_now=True)

    @classmethod
    def new_game(cls, creator_name, players, current_int, max_int, max_increment):
        if len(players) < 1:
            raise ValueError("You must specify at least one other player")
            #raise endpoints.BadRequestException("You must specify at least one other player")
        if len(players) != len(set(players)) or creator_name in players:
            raise ValueError("You must only specify unique players")
            #raise endpoints.BadRequestException("You must only specify unique players")
        if max_increment < 2:
            raise ValueError("max_increment must be at least 2")
            #raise endpoints.BadRequestException("max_increment must be at least 2")
        if max_int <= current_int:
            raise ValueError("Starting value must be smaller than ending value")
            #raise endpoints.BadRequestException("Starting value must be smaller than ending value")

        for p in players:
            player = User.query(User.name == p).get()
            if not player:
                raise endpoints.NotFoundException("User %s doesn't not exist." % p)

        players.append(creator_name)
        shuffle(players)
        #game = Game()
        #game.users = players
        game = Game(current_int=current_int,
                    max_int=max_int,
                    max_increment=max_increment,
                    game_over=False,
                    users=players)
        game.put()
        return game

    def to_form(self, message=None):
        form = GameForm()
        form.current_int = self.current_int
        form.max_int = self.max_int
        form.max_increment = self.max_increment
        form.game_over = self.game_over
        form.urlsafe_game_key = self.key.urlsafe()
        form.users = self.users
        form.message = message
        form.created = str(self.created)
        form.last_update = str(self.last_update)
        return form

    #TODO: get loser by index or name?
    def end_game(self, loserindex=0):
        self.game_over = True
        loser = self.users[loserindex]
        winners = self.users[:loserindex] + self.users[loserindex+1:]
        winner_score = 1.0 / len(winners)
        winners = User.query(User.name.IN(winners)).fetch()
        scores = []
        for user in winners:
            user.rating += winner_score
            # TODO allocate multiple ids outside of loop(size=len(winners), then assign in loop?
            score_id = Score.allocate_ids(size=1, parent=user.key)[0]
            score_key = ndb.Key(Score, score_id, parent=user.key)
            score = Score(points=winner_score, game_key=self.key, key=score_key)
            scores.append(score)

        loser = User.query(User.name == loser).get()
        loser.rating -= 1
        score_id = Score.allocate_ids(size=1, parent=loser.key)[0]
        score_key = ndb.Key(Score, score_id, parent=loser.key)
        score = Score(points=-1,game_key=self.key, key=score_key)
        scores.append(score)

        transaction = {
            'winners': winners,
            'loser': loser,
            'scores':scores
        }
        return transaction

    def quit_game(self, loser_name):
        game_history = GameHistory.query(ancestor=self.key).get()
        game_history.add_move(loser_name, 'quit')

        transaction = self.end_game(loserindex=self.users.index(loser_name))
        transaction['game'] = self
        transaction['game_history'] = game_history

        return transaction

class GameForm(messages.Message):
    current_int = messages.IntegerField(1, variant=messages.Variant.INT32)
    max_int = messages.IntegerField(2, variant=messages.Variant.INT32)
    max_increment = messages.IntegerField(3, variant=messages.Variant.INT32)
    game_over = messages.BooleanField(4)
    users = messages.StringField(5, repeated=True)
    urlsafe_game_key = messages.StringField(6)
    message = messages.StringField(7)
    created = messages.StringField(8)
    last_update = messages.StringField(9)

class GameForms(messages.Message):
    games = messages.MessageField(GameForm, 1, repeated=True)

class MoveRecord(ndb.Model):
    username = ndb.StringProperty(required=True)
    move = ndb.StringProperty(required=True)
    datetime = ndb.DateTimeProperty(auto_now_add=True)

    def to_form(self):
        form = MoveRecordForm()
        form.name = self.username
        form.move = self.move
        form.datetime = str(self.datetime)
        return form

class MoveRecordForm(messages.Message):
    name = messages.StringField(1, required=True)
    move = messages.StringField(2, required=True)
    datetime = messages.StringField(3)

class GameHistory(ndb.Model):
    moves = ndb.StructuredProperty(MoveRecord, repeated=True)

    @classmethod
    def new_history(cls, game):
        history_id = cls.allocate_ids(size=1, parent=game.key)[0]
        history_key = ndb.Key(cls, history_id, parent=game.key)
        cls(key=history_key).put()

    def add_move(self,username,move):
        self.moves.append(MoveRecord(username=username,move=move))

    def to_form(self):
        return GameHistoryForm(moves=[move.to_form() for move in self.moves])

class GameHistoryForm(messages.Message):
    moves = messages.MessageField(MoveRecordForm, 1, repeated=True)

class Score(ndb.Model):
    created = ndb.DateTimeProperty(auto_now_add=True)
    points = ndb.FloatProperty(required=True) # 1.0 / number of winners
    game_key = ndb.KeyProperty(required=True, kind="Game")

    def to_form(self):
        form = ScoreForm()
        form.created = str(self.created)
        form.points = self.points
        form.game_key = self.game_key.urlsafe()

class ScoreForm(messages.Message):
    created = messages.StringField(1)
    points = messages.FloatField(2)
    game_key = messages.StringField(3)

class StringMessage(messages.Message):
    """StringMessage -- outbound (single) string message"""
    message = messages.StringField(1, required=True)