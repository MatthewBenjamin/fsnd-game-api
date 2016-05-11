    #####################################################
    # TODOs
    # ### - add graceful error handling - ###
    #
    #   -add/check oauth support for client-side?
    #
    #   -readme
    #   -check other project specs
    #
    #   -check code comments
    #   -write design.txt (see project rubric/description)
    # Methods to implement:
    #
    #       - add PC players?
    #
    #####################################################
import endpoints
from protorpc import messages, message_types, remote
from google.appengine.api import taskqueue
from google.appengine.ext import ndb

from models import User, Game, GameHistory, Score, StringMessage
from models import GameForm, GameForms, GameHistoryForm, UserForms

from utils import get_by_urlsafe, get_games_by_username, get_user_by_gplus

WEB_CLIENT_ID = '1076330149728-67iteco8l0sk3i9teeh86k8ouma2rdjm.apps.googleusercontent.com'
EMAIL_SCOPE = endpoints.EMAIL_SCOPE
API_EXPLORER_CLIENT_ID = endpoints.API_EXPLORER_CLIENT_ID

# REQUEST MESSAGES
CREATE_USER_REQUEST = endpoints.ResourceContainer(username=messages.StringField(1, required=True))
REQUEST_BY_USERNAME = endpoints.ResourceContainer(username = messages.StringField(1, required=True))
NEW_GAME_REQUEST = endpoints.ResourceContainer(other_players = messages.StringField(1, repeated=True),
                                               starting_int=messages.IntegerField(2, default=0),
                                               max_int=messages.IntegerField(3, default=31),
                                               max_increment=messages.IntegerField(4, default=3))

MAKE_MOVE_REQUEST = endpoints.ResourceContainer(urlsafe_game_key=messages.StringField(1, required=True),
                                                value=messages.IntegerField(2, required=True))
GAME_REQUEST = endpoints.ResourceContainer(urlsafe_game_key=messages.StringField(1, required=True),)

@endpoints.api(name='baskin_robbins_31', version='v1',
    allowed_client_ids=[WEB_CLIENT_ID, API_EXPLORER_CLIENT_ID],
    scopes=[EMAIL_SCOPE])
class BaskinRobbins31Game(remote.Service):
    """BasketinRobbins31Game version 0.1"""

    ##### USER METHODS #####
    @endpoints.method(request_message=CREATE_USER_REQUEST,
                      response_message=StringMessage,
                      path='create_user',
                      name='create_user',
                      http_method='POST')
    def create_user(self, request):
        """Create a new user"""
        g_user = endpoints.get_current_user()
        if not g_user:
            raise endpoints.UnauthorizedException('Authorization required')
        if User.query(User.name == request.username).get():
            raise endpoints.ConflictException("A User with that name already exists.")
        if User.query(User.email == g_user.email()).get():
            raise endpoints.ConflictException("A User with that Google plus account already exists.")
        user = User(name=request.username, email=g_user.email())
        user.put()
        return StringMessage(message="User %s created" % request.username)

    # TODO: add optional params to request for completed games, cancelled(?), won, lost, etc.
    @endpoints.method(request_message=REQUEST_BY_USERNAME,
                      response_message=GameForms,
                      path='user/{username}/games',
                      name='get_user_games',
                      http_method='GET')
    def get_user_games(self, request):
        """Get a user's games (by unique username)"""
        games = get_games_by_username(request.username)
        return GameForms(games = [game.to_form() for game in games])

    @endpoints.method(request_message=GAME_REQUEST,
                      response_message=GameForm,
                      path='quit_game',
                      name='quit_game',
                      http_method='POST')
    def quit_game(self, request):
        """Authorized user forfeits a current game"""
        user = get_user_by_gplus()
        users_games = get_games_by_username(request.username)
        game = get_by_urlsafe(request.urlsafe_game_key, Game)
        if game not in users_games:
            # TODO: proper error msg?
            raise endpoints.NotFoundException('User not part of game')
        if game.game_over:
            raise endpoints.BadRequestException('Game has already finished')


        transaction = game.quit_game(loser_name=user.name)

        self._save_move_results(**transaction)
        return game.to_form(message="%s has quit. Game over!" % user.name)

    # TODO: error handling?
    @endpoints.method(request_message=message_types.VoidMessage,
                      response_message=UserForms,
                      path='rankings',
                      name='get_user_rankings',
                      http_method='GET')
    def get_user_rankings(self, request):
        """Get list of all users order by rating"""
        rankings = User.query().order(-User.rating).fetch(projection=[User.name, User.rating])
        return UserForms(users=[user.to_form() for user in rankings])

    ##### GAME METHODS #####
    @endpoints.method(request_message=NEW_GAME_REQUEST,
                      response_message=GameForm,
                      path='new_game',
                      name='new_game',
                      http_method='POST')
    def new_game(self, request):
        """Create a new game"""
        user = get_user_by_gplus()
        try:
            game = Game.new_game(current_int = request.starting_int,
                                 max_int = request.max_int,
                                 max_increment = request.max_increment,
                                 creator_name = user.name,
                                 players = request.other_players)
        except ValueError as error:
            raise endpoints.BadRequestException(error)

        GameHistory.new_history(game)
        return game.to_form(message="New game created")

    # get simple game info by key
    @endpoints.method(request_message=GAME_REQUEST,
                      response_message=GameForm,
                      path='game/{urlsafe_game_key}',
                      name='get_game',
                      http_method='GET')
    def get_game(self, request):
        """Get game by URL safe key"""
        # TODO: raise bad request, etc. errors (in utils?)
        game = get_by_urlsafe(request.urlsafe_game_key, Game)
        return game.to_form()

    @endpoints.method(request_message=GAME_REQUEST,
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

    @endpoints.method(request_message=MAKE_MOVE_REQUEST,
                      response_message=GameForm,
                      path='make_move',
                      name='make_move',
                      http_method='POST')
    def make_move(self, request):
        # TODO: DRY: check g_user and user in many funcs...
        """Next player makes their move. Returns the updated game state"""
        user = get_user_by_gplus()
        game = get_by_urlsafe(request.urlsafe_game_key, Game)
        move_value = request.value

        if game.game_over:
            return game.to_form(message="Game has already finished!")
        if user.name not in game.users:
            return game.to_form(message="User not part of game")
        if user.name != game.users[0]:
            return game.to_form(message="Not user's turn yet")
        if move_value > game.max_increment or move_value < 1:
            return game.to_form(message="Invalid move value")

        transaction, message = game.make_move(move_value)

        self._save_move_results(**transaction)
        return game.to_form(message=message)

api = endpoints.api_server([BaskinRobbins31Game])
