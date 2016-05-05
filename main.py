import logging

import webapp2
from google.appengine.api import mail, app_identity
from api import BaskinRobbins31Game

from datetime import datetime, timedelta
from models import User, Game

class SendReminderEmail(webapp2.RequestHandler):
    def get(self):
        """Send a reminder email to each User with an email about games.
        Called every hour using a cron job"""

        app_id = app_identity.get_application_id()

        onehourago = datetime.now() - timedelta(hours=1)

        old_games = Game.query(Game.last_update < onehourago).fetch()
        users_to_email = []
        for game in old_games:
            users_to_email.append(game.users[0])
        users_to_email = set(users_to_email)
        users_to_email = User.query(User.name.IN(users_to_email), User.email != None).fetch()
        for user in users_to_email:
            subject = 'This is a reminder!'
            body = 'Hello, a Baskin Robbins 31 game is waiting on your turn!'
            # This will send test emails, the arguments to send_mail are:
            # from, to, subject, body
            mail.send_mail('noreply@{}.appspotmail.com'.format(app_id),
                           user.email,
                           subject,
                           body)

app = webapp2.WSGIApplication([
    ('/crons/send_reminder', SendReminderEmail),
], debug=True)