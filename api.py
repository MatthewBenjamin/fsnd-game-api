import endpoints
from protorpc import messages, remote
from google.appengine.api import taskqueue
from google.appengine.ext import ndb

from models import User, Game, GameHistory, Result, StringMessage
from models import GameForm, GameHistoryForm

# REQUEST MESSAGES
CREATE_USER_REQUEST = endpoints.ResourceContainer(user_name=messages.StringField(1, required=True),
                                                  email=messages.StringField(2))

NEW_GAME_REQUEST = endpoints.ResourceContainer(players = messages.StringField(1, repeated=True))

MAKE_MOVE_REQUEST = endpoints.ResourceContainer(user_key=messages.StringField(1, required=True),
                                                game_key=messages.StringField(2, required=True),
                                                value=messages.IntegerField(3,
                                                    variant=messages.Variant.INT32, required=True)
                                                )
GET_GAME_REQUEST = endpoints.ResourceContainer(urlsafe_game_key=messages.StringField(1, required=True),)
# TODO: allowed_client_ids & scopes (for oauth)
@endpoints.api(name='baskin_robbins_31', version='v1')
class BaskinRobbins31Game(remote.Service):
    """BasketinRobbins31Game version 0.1"""

    #####################################################
    # TODO: Methods to implement
    #       - get_user(get user by user key (and/or user_name? - get_key_by_username?))
    #
    #       - get_user_games - get list of games by user(current or complete? cancelled games?)
    #
    #       - cancel_game (what if multiple players? -quit/leave_game instead?)
    #
    #       - get_user_rankings - generate player rankings, return each player's name and
    #                           - performance indicator (e.g. won/loss percentage)
    #
    #####################################################

    @endpoints.method(request_message=CREATE_USER_REQUEST,
                      response_message=StringMessage,
                      path='user',
                      name='create_user',
                      http_method='POST')
    def create_user(self, request):
        """Create a new user."""
        if User.query(User.name == request.user_name).get():
            raise endpoints.ConflictException("A User with that name already exists.")
        user = User(name=request.user_name, email=request.email)
        user.put()
        return StringMessage(message="User %s created" % request.user_name)

    @endpoints.method(request_message=NEW_GAME_REQUEST,
                      response_message=GameForm,
                      path='new_game',
                      name='new_game',
                      http_method='POST')
    def new_game(self, request):
        players = request.players
        if len(players) < 2:
            raise endpoints.BadRequestException("You must specify at least two players.")
        elif len(players) != len(set(players)):
            raise endpoints.BadRequestException("You must only specify unique players.")
        else:
            game = Game()
            for p in players:
                player = User.query(User.name == p).get()
                if not player:
                    raise endpoints.BadRequestException("User %s doesn't not exist." % p)
                else:
                    game.user_keys.append(player.key)
            # TODO: treat this endpoint as a ndb transaction because of game & GameHistory puts?
            game.put()
            history_id = GameHistory.allocate_ids(size=1, parent=game.key)[0]
            history_key = ndb.Key(GameHistory, history_id, parent=game.key)
            GameHistory(key=history_key).put()

        return game.to_form()

    # get simple game info by key
    @endpoints.method(request_message=GET_GAME_REQUEST,
                      response_message=GameForm,
                      path='game/{urlsafe_game_key}',
                      name='get_game',
                      http_method='GET')
    def get_game(self, request):
        # TODO: raise bad request, etc. errors
        game = ndb.Key(urlsafe=request.urlsafe_game_key).get()
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
        # TODO: raise bad request, etc. errors
        game_history = GameHistory.query(ancestor=ndb.Key(urlsafe=request.urlsafe_game_key)).get()
        return game_history.to_form()

    # TODO: make move method - user's whose turn it is submits next move
    @endpoints.method(request_message=MAKE_MOVE_REQUEST,
                      response_message=GameForm,
                      path='make_move',
                      name='make_move',
                      http_method='POST')
    def make_move(self, request):
        print request
        return GameForm()

api = endpoints.api_server([BaskinRobbins31Game])