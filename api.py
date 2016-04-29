import endpoints
from protorpc import messages, remote
from google.appengine.api import taskqueue

from models import User, Game, Result, StringMessage
from model import GameForm

# REQUEST MESSAGES
CREATE_USER_REQUEST = endpoints.ResourceContainer(user_name=messages.StringField(1, required=True),
                                                  email=messages.StringField(2))

NEW_GAME_REQUEST = endpoints.ResourceContainer(players = messages.StringField(1, repeated=True))

# TODO: allowed_client_ids & scopes (for oauth)
@endpoints.api(name='baskin_robbins_31', version='v1')
class BaskinRobbins31Game(remote.Service):
    """BasketinRobbins31Game version 0.1"""

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
                      response_message=StringMessage,
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
            game.put()

        return StringMessage(message="Game created with %s players" % len(players))

    # TODO: make move method
    @endpoints.method(request_message=MAKE_MOVE_REQUEST,
                      response_message=GameForm,
                      path='make_move',
                      name='make_move',
                      http_method='POST')
api = endpoints.api_server([BaskinRobbins31Game])