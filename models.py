from google.appengine.ext import ndb
from protorpc import messages

from random import shuffle

class User(ndb.Model):
    """User profile"""
    name = ndb.StringProperty(required=True)
    email = ndb.StringProperty()
    rating = ndb.FloatProperty(default=0)

    def to_form(self, show_email=False):
        """Returns a UserForm representation of the User"""
        form = UserForm()
        form.name = self.name
        form.rating = self.rating
        if show_email:
            form.email = self.email
        return form

class UserForm(messages.Message):
    """UserForm for outbound User profile"""
    name = messages.StringField(1, required=True)
    email = messages.StringField(2)
    rating = messages.FloatField(3)

class UserForms(messages.Message):
    """Return multiple UserForms"""
    users = messages.MessageField(UserForm, 1, repeated=True)

class Game(ndb.Model):
    """Game object"""
    current_int = ndb.IntegerProperty(required=True, default=0)
    max_int = ndb.IntegerProperty(required=True, default=31)
    max_increment = ndb.IntegerProperty(required=True, default=3)
    game_over = ndb.BooleanProperty(required=True, default=False)
    users = ndb.StringProperty(repeated=True)
    created = ndb.DateTimeProperty(auto_now_add=True)
    last_update = ndb.DateTimeProperty(auto_now=True)

    @classmethod
    def new_game(cls, players, current_int, max_int, max_increment):
        """Creates and returns a new game"""
        if len(players) < 2:
            raise ValueError("You must specify at least one other player")
        if len(players) != len(set(players)):
            raise ValueError("You must only specify unique players")
        if max_increment < 2:
            raise ValueError("max_increment must be at least 2")
        if max_int <= current_int:
            raise ValueError("Starting value must be smaller than ending value")

        shuffle(players)
        game = Game(current_int=current_int,
                    max_int=max_int,
                    max_increment=max_increment,
                    game_over=False,
                    users=players)
        game.put()
        return game

    def make_move(self, move_value):
        """Implements a move and return entities for datastore transaction"""
        self.current_int += move_value
        move = MoveRecord.new_move(self, str(move_value))

        if self.current_int >= self.max_int:
            transaction = self.end_game()
            message = "Game Over! %s is the loser." % (self.users[0])
        else:
            self.users.append(self.users.pop(0))
            message = "Move successful!"
            transaction = {}

        transaction['game'] = self
        transaction['move'] = move
        return transaction, message

    def to_form(self, message=None):
        """Return a GameForm representation of the Game"""
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

    def end_game(self, loserindex=0):
        """Ends the game and creates score entities for all players. Returns score and
           player entities for datastore transaction"""
        self.game_over = True
        loser = self.users[loserindex]
        winners = self.users[:loserindex] + self.users[loserindex+1:]
        winner_score = 1.0 / len(winners)
        winners = User.query(User.name.IN(winners)).fetch()
        scores = []
        for user in winners:
            user.rating += winner_score
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
        """Ends the game with the quitting player as the loser. Return entities for
           datastore transaction"""
        move = MoveRecord.new_move(self, 'quit')

        transaction = self.end_game(loserindex=self.users.index(loser_name))
        transaction['game'] = self
        transaction['move'] = move

        return transaction

class GameForm(messages.Message):
    """GameForm for outbound game state information"""
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
    """Return multiple GameForms"""
    games = messages.MessageField(GameForm, 1, repeated=True)

class NewGameForm(messages.Message):
    """Used to created a new game"""
    other_players = messages.StringField(1, repeated=True)
    starting_int=messages.IntegerField(2, default=0)
    max_int=messages.IntegerField(3, default=31)
    max_increment=messages.IntegerField(4, default=3)

class MakeMoveForm(messages.Message):
    """Form to submit move"""
    value = messages.IntegerField(1, required=True)

class MoveRecord(ndb.Model):
    """Stores record of a single move in a Game. Child of Game"""
    username = ndb.StringProperty(required=True)
    move = ndb.StringProperty(required=True)
    datetime = ndb.DateTimeProperty(auto_now_add=True)

    @classmethod
    def new_move(cls, game, move):
        """Creates and returns a new move"""
        move_id = cls.allocate_ids(size=1, parent=game.key)[0]
        move_key = ndb.Key(cls, move_id, parent=game.key)
        move = cls(username = game.users[0],
                   move = move,
                   key=move_key)
        return move

    def to_form(self):
        """Returns a MoveRecordForm representation of MoveRecord"""
        form = MoveRecordForm()
        form.name = self.username
        form.move = self.move
        form.datetime = str(self.datetime)
        return form

class MoveRecordForm(messages.Message):
    """MoveRecordForm for outbound MoveRecord information"""
    name = messages.StringField(1, required=True)
    move = messages.StringField(2, required=True)
    datetime = messages.StringField(3)

class GameHistoryForm(messages.Message):
    """Return multiple MoveRecordForms"""
    moves = messages.MessageField(MoveRecordForm, 1, repeated=True)

class Score(ndb.Model):
    """Score object - stores user's points for a single game"""
    points = ndb.FloatProperty(required=True) # 1.0 / number of winners or -1 (for loser)
    game_key = ndb.KeyProperty(required=True, kind="Game")

    def to_form(self):
        """Returns a ScoreForm representation of Score"""
        form = ScoreForm()
        form.points = self.points
        form.game_key = self.game_key.urlsafe()
        # TODO: just store username in Score model?
        #form.username = self.key.parent().get().name
        return form

class ScoreForm(messages.Message):
    """ScoreForm for outbound Score information"""
    points = messages.FloatField(1)
    game_key = messages.StringField(2)
    #username = messages.StringField(4)

class ScoreForms(messages.Message):
    """Return multiple ScoreForms"""
    scores = messages.MessageField(ScoreForm, 1, repeated=True)

class StringMessage(messages.Message):
    """StringMessage -- outbound (single) string message"""
    message = messages.StringField(1, required=True)