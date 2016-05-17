# Baskin Robbins 31 - Counting Game

##Game Description:
Baskin Robbins 31 is a Korean counting game for 2 or more players. In the game,
players take turns adding to the game's count, incrementing by their choice of
1, 2, or 3 numbers at a time. The player that is forced to count to 31 loses.
For example, a game with two players might progress like this:

Player1: "1,2"

Player2: "3,4,5"

Player1: "6,7,8"

Player2: "9"

...

...

Player1: "24,25,26"

Player2: "27"

Player1: "28,29,30"

Player2: "31"

\- GAME OVER -

In the above example, since Player2 was forced to count to 31, that player loses.
All other players win.

### Scoring:
Upon completion of the game, the losing player receives -1 point, whereas all
winning players receive 1.0 point divided by the total number of winners. For
example, imagine a completed game with 3 players:
Player1 (winner): 0.5 point
Player2 (winner): 0.5 point
Player3 (loser) : -1 point

### Game Options:
By default, the starting count is 1, the game will end when the count reaches 31,
and the maximum increment is 3, however these values can be changed during game setup.

## Set-Up Instructions:
1.  Update the value of application in app.yaml to the app ID you have registered
 in the App Engine admin console and would like to use to host your instance of this sample.
2.  Run the app with the devserver using dev_appserver.py DIR, and ensure it's
 running by visiting the API Explorer - by default localhost:8080/_ah/api/explorer.
3.  If deploying in conjunction with a client-side  that will require oauth2 authorization
to access the API server, such as a web front end for the game, add the client ids to the
allow_client_ids parameter of the endpoints.api declaration.
Deploy your application.

##Files Included:
 - api.py: Contains endpoints and logic to handle requests.
 - app.yaml: App configuration.
 - cron.yaml: Cronjob configuration.
 - index.yaml: Indexes for datastore queries.
 - main.py: Handler for cronjob handler.
 - models.py: Entity and message definitions. Includes game logic and helper methods.
 - utils.py: Helper functions for retrieving ndb.Models and verifying user authentication.

##Endpoints Included:

 - **create_user**
    - Path: 'create_user'
    - Method: POST
    - Parameters: user_name
    - Returns: Message confirming creation of the User.
    - Authorization: oauth2 for user's gplus account.
    - Description: Creates a new User. Gplus account and user_name provided
                   must be unique. Will raise a ConflictException if a User
                   with that user_name or gplus account already exists.

 - **get_user_games**
    - Path: 'user/{username}/games'
    - Method: GET
    - Parameters: username
    - Returns: GameForms with game states.
    - Authorization: none
    - Description: Returns all games associated with the username. Will raise
                   a NotFoundException if a User with that user_name does not
                   exist.

 - **get_user_scores**
    - Path: 'user/{username}/scores'
    - Method: GET
    - Parameters: username
    - Returns: ScoreForms with user's scores.
    - Authorization: none
    - Description: Returns all scores associated with the username. Will raise
                   a NotFoundException if a User with that user_name does not
                   exist, or if the User does exist but has not completed any
                   games yet.

 - **quit_game**
    - Path: 'quit_game'
    - Method: POST
    - Parameters: urlsafe_game_key
    - Returns: GameForm with final game state.
    - Authorization: oauth2 for user's gplus account.
    - Description: Forfeit's the game associated with the urlsafe game key
                   for the authorized user. Counts as a loss for the user
                   and a win for all opponents. Will raise a ForbiddenException
                   if the authorized user is not a part of the game, or if the
                   game has already finished.

 - **get_user_rankings**
    - Path: 'rankings'
    - Method: GET
    - Parameters: none
    - Returns: UserForms sorted by user rating.
    - Authorization: none
    - Description: Returns all users sorted by their current rating.

 - **new_game**
    - Path: 'new_game'
    - Method: POST
    - Parameters: other_players, starting_int(optional),
                  max_int(optional), max_increment(optional)
    - Returns: GameForm with initial game state.
    - Authorization: oauth2 for user's gplus account.
    - Description: Creates a new game between the authorized user and any users
                   listed in the 'other_players' parameter. There must be at least
                   one other player. Will raise a NotFoundException if the gplus
                   account is not associated with a user, or if any player listed
                   in other_players does not exist. Will return a BadRequestException
                   if there are no other_players, if starting_int isn't less than
                   max_int, or if max_increment must is not at least 2.

 - **get_game**
    - Path: 'game/{urlsafe_game_key}'
    - Method: GET
    - Parameters: urlsafe_game_key
    - Returns: GameForm with current game state.
    - Authorization: none
    - Description: Returns the current state of a game.

 - **get_game_scores**
    - Path: 'game/{urlsafe_game_key}/scores'
    - Method: GET
    - Parameters: urlsafe_game_key
    - Returns: ScoreForms with users' scores for that game.
    - Authorization: none
    - Description: Return a list of scores for the requested game. Will raise
                   a BadRequestException if the game hasn't finished yet.

 - **get_game_history**
    - Path: 'game/{urlsafe_game_key}/history'
    - Method: GET
    - Parameters: urlsafe_game_key
    - Returns: GameHistoryForm
    - Authorization: none
    - Description: Return a list of moves made for the requested game.

 - **make_move**
    - Path: 'make_move'
    - Method: PUT
    - Parameters: urlsafe_game_key, value
    - Returns: GameForm with new game state.
    - Authorization: oauth2 for user's gplus account.
    - Description: Accepts a value and - if valid - increments the current_int for
                   the given game and returns the updated state of the game.
                   If this causes a game to end, each player's rating will be updated
                   and a corresponding Score entity will be created. If the game has
                   already finished, the user is not part of the game, it is not the
                   user's turn, or the value is invalid, then the GameForm will be
                   returned with the unchanged game state with a message indicating
                   the error. If the move is valid, the GameForm will be return with
                   the new game state, with the message indicating the move was
                   successful.

##Models Included:
 - **User**
    - Stores unique user_name, user's gplus account email address, and user's
      rating (cumulative points earned in all games.)

 - **Game**
    - Stores unique game states. Associated with User model by storing a list of
      each participating user's unique username.

 - **MoveRecord**
    - Record of a single move made in a game. Stored as a repeated StructuredProperty
      in the GameHistory model.

 - **Score**
    - Records completed games. Child of the Users model it is associated with.

##Forms Included:
 - **UserForm**
    - Representation of a User with email redacted (name, rating).
 - **UserForms**
    - Multiple UserForm container.
 - **GameForm**
    - Representation of a Game's state (current_int, max_int, max_increment,
      game_over, users, created, last_update).
 - **GameForms**
    - Multiple GameForm container.
 - **NewGameForm**
    - Used to create a new game (other_players, starting_int, max_int, max_increment)
 - **MakeMoveForm**
    - Inbound make move form (value).
 - **MoveRecordForm**
    - Representation of a single Move in a game's history (username, move, datetime)
 - **GameHistoryForm**
    - Multiple MoveRecordForm container.
 - **ScoreForm**
    - Representation of a completed game's Score (created, points, game_key,
    guesses).
 - **ScoreForms**
    - Multiple ScoreForm container.
 - **StringMessage**
    - General purpose String container.
