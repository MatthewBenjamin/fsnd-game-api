# api.py - Baskin Robbins 31 Game API

import endpoints
from protorpc import messages, message_types, remote

from google.appengine.ext import ndb

from models import User, Game, MoveRecord, Score, StringMessage
from models import (
    GameForm, GameForms, NewGameForm, MakeMoveForm, GameHistoryForm,
    UserForms, ScoreForms)
from utils import get_by_urlsafe, get_games_by_username, get_user_by_gplus

EMAIL_SCOPE = endpoints.EMAIL_SCOPE
API_EXPLORER_CLIENT_ID = endpoints.API_EXPLORER_CLIENT_ID

# REQUEST MESSAGES
USER_REQUEST = endpoints.ResourceContainer(
    username=messages.StringField(1, required=True))
NEW_GAME_REQUEST = endpoints.ResourceContainer(NewGameForm)
MAKE_MOVE_REQUEST = endpoints.ResourceContainer(
    MakeMoveForm,
    urlsafe_game_key=messages.StringField(1, required=True))
GAME_REQUEST = endpoints.ResourceContainer(
    urlsafe_game_key=messages.StringField(1, required=True))


@endpoints.api(name='baskin_robbins_31', version='v1',
               allowed_client_ids=[API_EXPLORER_CLIENT_ID],
               scopes=[EMAIL_SCOPE])
class BaskinRobbins31Game(remote.Service):
    """BasketinRobbins31Game version 0.1"""

    # USER METHODS
    @endpoints.method(request_message=USER_REQUEST,
                      response_message=StringMessage,
                      path='create_user',
                      name='create_user',
                      http_method='POST')
    def create_user(self, request):
        """Create a new user from user's gplus account (by oauth2)"""
        g_user = endpoints.get_current_user()
        if not g_user:
            raise endpoints.UnauthorizedException('Authorization required')
        if User.query(User.name == request.username).get():
            raise endpoints.ConflictException(
                "A User with that name already exists.")
        if User.query(User.email == g_user.email()).get():
            raise endpoints.ConflictException(
                "A User with that Google plus account already exists.")
        user = User(name=request.username, email=g_user.email())
        user.put()
        return StringMessage(message="User %s created" % request.username)

    # TODO: add optional params to request for completed games, won, lost, etc.
    @endpoints.method(request_message=USER_REQUEST,
                      response_message=GameForms,
                      path='user/{username}/games',
                      name='get_user_games',
                      http_method='GET')
    def get_user_games(self, request):
        """Get a user's games (by unique username)"""
        games = get_games_by_username(request.username)
        return GameForms(games=[game.to_form() for game in games])

    @endpoints.method(request_message=USER_REQUEST,
                      response_message=ScoreForms,
                      path='user/{username}/scores',
                      name='get_user_scores',
                      http_method='GET')
    def get_user_scores(self, request):
        """Get a user's scores (by unique username)"""
        user = User.query(User.name == request.username).get()
        if not user:
            raise endpoints.NotFoundException("User doesn't exist")
        scores = Score.query(ancestor=user.key).fetch()
        if not scores:
            raise endpoints.NotFoundException(
                "That user hasn't recorded any scores yet")
        return ScoreForms(scores=[score.to_form() for score in scores])

    @endpoints.method(request_message=GAME_REQUEST,
                      response_message=GameForm,
                      path='quit_game',
                      name='quit_game',
                      http_method='POST')
    def quit_game(self, request):
        """Authorized user forfeits a current game"""
        user = get_user_by_gplus()
        users_games = get_games_by_username(user.name)
        game = get_by_urlsafe(request.urlsafe_game_key, Game)
        if game not in users_games:
            raise endpoints.ForbiddenException('User not part of game')
        if game.game_over:
            raise endpoints.ForbiddenException('Game has already finished')

        gameResultsToSave = game.quit_game(loser_name=user.name)

        self._save_move_results(**gameResultsToSave)
        return game.to_form(message="%s has quit. Game over!" % user.name)

    @endpoints.method(request_message=message_types.VoidMessage,
                      response_message=UserForms,
                      path='rankings',
                      name='get_user_rankings',
                      http_method='GET')
    def get_user_rankings(self, request):
        """Get list of all users, ordered by rating"""
        rankings = User.query().order(-User.rating).fetch(
            projection=[User.name, User.rating])
        return UserForms(users=[user.to_form() for user in rankings])

    # GAME METHODS
    @endpoints.method(request_message=NEW_GAME_REQUEST,
                      response_message=GameForm,
                      path='new_game',
                      name='new_game',
                      http_method='POST')
    def new_game(self, request):
        """Create a new game"""
        user = get_user_by_gplus()
        players = request.other_players

        for p in players:
            player = User.query(User.name == p).get()
            if not player:
                raise endpoints.NotFoundException(
                    "User %s doesn't not exist." % p)

        players.append(user.name)

        try:
            game = Game.new_game(current_int=request.starting_int,
                                 max_int=request.max_int,
                                 max_increment=request.max_increment,
                                 players=players)
        except ValueError as error:
            raise endpoints.BadRequestException(error)

        return game.to_form(message="New game created")

    @endpoints.method(request_message=GAME_REQUEST,
                      response_message=GameForm,
                      path='game/{urlsafe_game_key}',
                      name='get_game',
                      http_method='GET')
    def get_game(self, request):
        """Get game by URL safe key"""
        game = get_by_urlsafe(request.urlsafe_game_key, Game)
        return game.to_form()

    @endpoints.method(request_message=GAME_REQUEST,
                      response_message=ScoreForms,
                      path='game/{urlsafe_game_key}/scores',
                      name='get_game_scores',
                      http_method='GET')
    def get_game_scores(self, request):
        """Get game scores by game's urlsafe key"""
        game = get_by_urlsafe(request.urlsafe_game_key, Game)
        if not game.game_over:
            raise endpoints.BadRequestException("Game has not finished yet")
        scores = Score.query(Score.game_key == game.key).fetch()
        return ScoreForms(scores=[score.to_form() for score in scores])

    @endpoints.method(request_message=GAME_REQUEST,
                      response_message=GameHistoryForm,
                      path='game/{urlsafe_game_key}/history',
                      name='get_game_history',
                      http_method='GET')
    def get_game_history(self, request):
        """Get game history by game's urlsafe key"""
        game = get_by_urlsafe(request.urlsafe_game_key, Game)
        if game:
            moves = MoveRecord.query(
                ancestor=game.key).order(MoveRecord.datetime).fetch()
        return GameHistoryForm(moves=[move.to_form() for move in moves])

    @ndb.transactional(xg=True)
    def _save_move_results(self, game, move, winners=None,
                           loser=None, scores=None):
        """NDB Transaction to update datastore entities after valid move"""
        game.put()
        move.put()
        if winners and loser and scores:
            ndb.put_multi(winners)
            ndb.put_multi(scores)
            loser.put()

    @endpoints.method(request_message=MAKE_MOVE_REQUEST,
                      response_message=GameForm,
                      path='game/{urlsafe_game_key}',
                      name='make_move',
                      http_method='PUT')
    def make_move(self, request):
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

        moveResultsToSave, message = game.make_move(move_value)

        self._save_move_results(**moveResultsToSave)
        return game.to_form(message=message)

api = endpoints.api_server([BaskinRobbins31Game])
