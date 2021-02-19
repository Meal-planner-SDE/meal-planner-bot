from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, ReplyKeyboardMarkup
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    ConversationHandler,
    CallbackContext,
    CallbackQueryHandler,
)

def is_error(obj):
    return "error" in obj

def authenticate(meal_planner, update, context):
    print('Authenticating...')
    if not 'user' in context.user_data:
        print('User not in context...')

        user = meal_planner.get_user(update.message.chat.username)
        if is_error(user):
            print('User not registered...')

            update.message.reply_text(
                """Ups, it seems I do not know you yet. Please type /start to present yourself."""
            )
            return False
        else:
            print('User registered...')
            context.user_data['user'] = user
            return True
    print('User already in context')
    return True