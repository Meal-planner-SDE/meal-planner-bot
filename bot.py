import hashlib
import logging
import os
import sys
import requests
import json

import tinydb
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import (Handler, CallbackQueryHandler, CommandHandler, Filters,
                          MessageHandler, Updater)


# Class that handle all the database functions
class Database:
    def __init__(self):
        self.database_url = "https://meal-plan-sde-db-adapter.herokuapp.com/"

    # Function to retrieve user by id from db
    def get_user(self, username):
        r = requests.get(f"{self.database_url}users/giovannasdasdi")
        print(r.json())

    # Function to insert and update user in db
    def update_user(self, username, user):
        r = requests.get(f"{self.database_url}users/{username}")
        if (is_error(user)):
            #post
            r = request.post(f"{self.database_url}users/", data=user)
        else:
            #patch
            r = request.patch(f"{self.database_url}users/{user.id}", data=user)

    def is_error(self, obj):
        return "error" in obj

# Class that handle all the bot requests
class Bot:

    # Array of characters used in the password creation
    chars = "abcdefghijklmnopqrstuvwxyz,;.:-_!£$%&/()=?ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890"

    def __init__(self):
        # Environment variables
        TOKEN = "1585535684:AAFj6jKfe6Nud4unaRZwS5HXi5VrzbHFSrs"
        PORT = int(os.environ.get("PORT", "8443"))
        updater = Updater(TOKEN, use_context=True)
        # Setting up logger
        logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                            level=logging.INFO)
        self.logger = logging.getLogger(__name__)

        # Setting up dispatcher
        self.log("Starting dispatcher")
        dp = updater.dispatcher
        dp.add_handler(CommandHandler("start", self.start))
        dp.add_handler(CommandHandler("profile", self.profile))
        dp.add_handler(CommandHandler("get_user", self.get_user))
        dp.add_handler(CommandHandler("help", self.help))
        dp.add_handler(CommandHandler("location", self.location))
        dp.add_handler(MessageHandler(Filters.location, self.location_callback))
        dp.add_handler(MessageHandler(Filters.contact, self.contact_callback))
        dp.add_handler(MessageHandler(Filters.text, self.hash))
        dp.add_error_handler(self.error)

        # Setting up database
        self.log("Starting database")
        self.db = Database()

        # Starting bot
        if len(sys.argv) == 2 and sys.argv[1] == "DEV":
            # Developer mode with local instance
            self.log("Start polling")
            updater.start_polling()
        else:
            # Deployed version with heroku instance
            self.log("Start webhook")
            updater.start_webhook(listen="0.0.0.0",
                                port=PORT,
                                url_path=TOKEN)
            updater.bot.set_webhook("https://hash-it-bot.herokuapp.com/" + TOKEN)
        updater.idle()

    # Function that given a message find a user by id
    # user name will be updated if exixts, insert otherwise
    def identify_user(self, chat):
        user = {}
        user["id"] = chat.id
        user["username"] = chat.username
        user["name"] = chat.first_name
        return user

    # Function called when bot is started
    def start(self, update, context):
        self.help(update, context)

    def profile(self, update, context):
        self.help(update, context)

    def get_user(self, update, context):
        user = self.identify_user(update.message.chat)
        a = self.db.get_user(user["username"])

    # Function that reply to help request (and start)
    def help(self, update, context):
        self.identify_user(update.message.chat)
        update.message.reply_text("Welcome to HashItBot!\n" + 
                                  "Write something which you want to hash\n" +
                                  "/location to share your location\n" +
                                  "/help to read this list\n") 


    # Function that returns a character given 2 hex numbers as strings
    def get_char_from_hex(self, n1, n2):
        return self.chars[int(n1 + n2, 16) % len(self.chars)]

    # Function that converts hash to string of characters
    def hash_to_chars(self, hash_string):
        self.log("Converting " + hash_string + " to string")
        result = ""
        for i in range(0, len(hash_string), 2):
            result += self.get_char_from_hex(hash_string[i], hash_string[i + 1])
        return result

    # Function that hashes every non-command message
    # It hashes concat + strings using the selected hash function
    def hash(self, update, context):
        user = self.identify_user(update.message.chat)
        text = user["concat"] + update.message.text
        self.log("Hashing " + text + " with " + user["hash"])
        hash_string = self.hash_type[user["hash"]](text.encode()).hexdigest()
        result = self.hash_to_chars(hash_string)
        update.message.reply_text(result)

    # Function that allows to change hash function with buttons
    def location(self, update, context):
        # Create a button foreach hash function available
        # keyboard = [[InlineKeyboardButton(s, callback_data=s)] for s in self.hash_type.keys()]
        # reply_markup = InlineKeyboardMarkup(keyboard)
        # update.message.reply_text("Please choose:", reply_markup=reply_markup)
        location_keyboard = KeyboardButton(text="Share location", request_location=True)
        reply_markup = ReplyKeyboardMarkup([[location_keyboard]], one_time_keyboard=True)
        user = self.identify_user(update.message.chat)
        print(user)
        update.message.reply_text("Do you want to send your location?", reply_markup=reply_markup)

    # Callback function called after a /function button is pressed
    def location_callback(self, update, context):
        print(update.message.location)
        query = update.callback_query

    def contact_callback(self, update, context):
        print(update.message.contact)
        query = update.callback_query
        # user = self.identify_user(query.message.chat)
        # user["hash"] = query.data
        # self.db.update_user(user)
        # query.edit_message_text(text="Hash function updated to {}".format(query.data))

    # Function that handle errors logging them
    def error(self, update, context):
        self.logger.warning("Update '%s' caused error '%s'", update, context.error)

    # Function used to log messages as info
    def log(self, message):
        self.logger.info(message)

if __name__ == '__main__':
    bot = Bot()
