import endpoints
from protorpc import messages, message_types, remote
from google.appengine.api import taskqueue
from google.appengine.ext import ndb

from models import User, Game, GameHistory, Score, StringMessage
from models import GameForm, GameForms, GameHistoryForm, UserForms

from utils import get_by_urlsafe

from random import shuffle

# REQUEST MESSAGES
CREATE_USER_REQUEST = endpoints.ResourceContainer(user_name=messages.StringField(1, required=True),
                                                  email=messages.StringField(2))
REQUEST_BY_USERNAME = endpoints.ResourceContainer(username = messages.StringField(1, required=True))
NEW_GAME_REQUEST = endpoints.ResourceContainer(players = messages.StringField(1, repeated=True),
                                               starting_int=messages.IntegerField(2, variant=messages.Variant.INT32),
                                               max_int=messages.IntegerField(3, variant=messages.Variant.INT32),
                                               max_increment=messages.IntegerField(4, variant=messages.Variant.INT32))

MAKE_MOVE_REQUEST = endpoints.ResourceContainer(username=messages.StringField(1, required=True),
                                                urlsafe_game_key=messages.StringField(2, required=True),
                                                value=messages.IntegerField(3,
                                                    variant=messages.Variant.INT32, required=True)
                                                )
GET_GAME_REQUEST = endpoints.ResourceContainer(urlsafe_game_key=messages.StringField(1, required=True),)
QUIT_GAME_REQUEST = endpoints.ResourceContainer(username=messages.StringField(1, required=True),
                                                urlsafe_game_key=messages.StringField(2, required=True))
# TODO: allowed_client_ids & scopes (for oauth)
@endpoints.api(name='baskin_robbins_31', version='v1')
class BaskinRobbins31Game(remote.Service):
    """BasketinRobbins31Game version 0.1"""

    #####################################################
    # TODO: Methods to implement
    #
    #       - get_user_rankings - generate player rankings, return each player's name and
    #                           - performance indicator (e.g. won/loss percentage)
    #
    #       - add PC players
    #####################################################

    ##### USER METHODS #####
    @endpoints.method(request_message=CREATE_USER_REQUEST,
                      response_message=StringMessage,
                      path='create_user',
                      name='create_user',
                      http_method='POST')
    def create_user(self, request):
        """Create a new user"""
        if User.query(User.name == request.user_name).get():
            raise endpoints.ConflictException("A User with that name already exists.")
        user = User(name=request.user_name, email=request.email)
        user.put()
        return StringMessage(message="User %s created" % request.user_name)

    #- get_user_games - get list of games by user(current or complete? cancelled games?)
    @endpoints.method(request_message=REQUEST_BY_USERNAME,
                      response_message=GameForms,
                      path='user/{username}/games',
                      name='get_user_games',
                      http_method='GET')
    def get_user_games(self, request):
        """Get a user's games (by unique username)"""
        games = Game.query(Game.users.IN((request.username,))).fetch()
        return GameForms(games = [game.to_form() for game in games])

    @endpoints.method(request_message=QUIT_GAME_REQUEST,
                      response_message=GameForm,
                      path='quit_game',
                      name='quit_game',
                      http_method='POST')
    def quit_game(self, request):
        game = get_by_urlsafe(request.urlsafe_game_key, Game)
        game_history = GameHistory.query(ancestor=game.key).get()
        game_history.add_move(request.username, 'quit')
        #TODO: DRY transactions (see make_move)?
        transaction = game.end_game(loserindex=game.users.index(request.username))
        transaction['game'] = game
        transaction['game_history'] = game_history
        self._save_move_results(**transaction)
        return game.to_form(message="%s has quit. Game over!" % request.username)

    @endpoints.method(request_message=message_types.VoidMessage,
                      response_message=UserForms,
                      path='rankings',
                      name='get_user_rankings',
                      http_method='GET')
    def get_user_rankings(self, request):
        rankings = User.query().order(-User.rating).fetch()
        return UserForms(users=[user.to_form() for user in rankings])

    ##### GAME METHODS #####
    @endpoints.method(request_message=NEW_GAME_REQUEST,
                      response_message=GameForm,
                      path='new_game',
                      name='new_game',
                      http_method='POST')
    def new_game(self, request):
        """Create a new game"""
        players = request.players
        starting_int = request.starting_int
        max_int = request.max_int
        max_increment = request.max_increment

        if len(players) < 2:
            raise endpoints.BadRequestException("You must specify at least two players.")
        if len(players) != len(set(players)):
            raise endpoints.BadRequestException("You must only specify unique players.")
        if max_increment and max_increment < 2:
            raise endpoints.BadRequestException("max_increment must be at least 2")
        if max_int and starting_int and max_int <= starting_int:
            raise endpoints.BadRequestException("Starting value must be smaller than ending value")
        elif max_int and max_int <1:
            raise endpoints.BadRequestException("max_int must be at least 1")
        elif starting_int and starting_int > 30:
            raise endpoints.BadRequestException("starting_int is too big")

        shuffle(players)
        game = Game()
        for p in players:
            player = User.query(User.name == p).get()
            if not player:
                raise endpoints.NotFoundException("User %s doesn't not exist." % p)
            else:
                game.users.append(player.name)
        if starting_int:
            game.current_int = starting_int
        if max_int:
            game.max_int = max_int
        if max_increment:
            game.max_increment = max_increment
        # TODO: treat this endpoint as a ndb transaction because of game & GameHistory puts?
        #game.put()
        history_id = GameHistory.allocate_ids(size=1, parent=game.key)[0]
        history_key = ndb.Key(GameHistory, history_id, parent=game.key)
        game_history = GameHistory(key=history_key)
        self._save_move_results(game=game, game_history=game_history)

        return game.to_form(message="New game created with a starting value of %s - The first player is %s" % (game.current_int, game.users[0]))

    # get simple game info by key
    @endpoints.method(request_message=GET_GAME_REQUEST,
                      response_message=GameForm,
                      path='game/{urlsafe_game_key}',
                      name='get_game',
                      http_method='GET')
    def get_game(self, request):
        """Get game by URL safe key"""
        # TODO: raise bad request, etc. errors
        #game = ndb.Key(urlsafe=request.urlsafe_game_key).get()
        game = get_by_urlsafe(request.urlsafe_game_key, Game)
        return game.to_form()

    # get game history by key
    #       - get_game_history  - return history of moves in a game
    #                           - i.e. [(matt, 3), (john, 2), (bill, 3) ....(john, 1)]
    @endpoints.method(request_message=GET_GAME_REQUEST,
                      response_message=GameHistoryForm,
                      path='game/{urlsafe_game_key}/history',
                      name='get_game_history',
                      http_method='GET')
    def get_game_history(self, request):
        """Get game history by game's urlsafe key"""
        # TODO: raise bad request, etc. errors
        game_history = GameHistory.query(ancestor=ndb.Key(urlsafe=request.urlsafe_game_key)).get()
        return game_history.to_form()

    @ndb.transactional(xg=True)
    def _save_move_results(self, game, game_history, winners=None, loser=None, scores=None):
        game.put()
        game_history.put()
        if winners and loser and scores:
            ndb.put_multi(winners)
            ndb.put_multi(scores)
            loser.put()

    def _make_move(self, request):
        username = request.username
        move_value = request.value
        # TODO: invalid game key doesn't work, so 1st error never has chance to fire - is it needed?
        game = get_by_urlsafe(request.urlsafe_game_key, Game)
        game_history = GameHistory.query(ancestor=game.key).get()
        if game.game_over:
            return game.to_form(message="Game has already finished!")
        if username not in game.users:
            return game.to_form(message="User not part of game")
        if username != game.users[0]:
            return game.to_form(message="Not user's turn yet")
        if move_value > game.max_increment or move_value < 1:
            return game.to_form(message="Invalid move value")

        # Valid game, user, and move. proceed
        # game logic
        game.current_int += move_value
        game_history.add_move(username, str(move_value))

        if game.current_int >= game.max_int:
            transaction = game.end_game()
            message = "Game Over! %s is the loser." % (username)
        else:
            game.users.append(game.users.pop(0))
            message = "Current value: %s - It's now %s's turn." % (game.current_int, game.users[0])
            #TODO: transaction is declared twice...(kinda)  ?
            transaction = {}

        transaction['game'] = game
        transaction['game_history'] = game_history

        self._save_move_results(**transaction)
        return game.to_form(message=message)

    @endpoints.method(request_message=MAKE_MOVE_REQUEST,
                      response_message=GameForm,
                      path='make_move',
                      name='make_move',
                      http_method='POST')
    def make_move(self, request):
        """Next player makes their move. Returns the updated game state"""
        return self._make_move(request)


api = endpoints.api_server([BaskinRobbins31Game])
