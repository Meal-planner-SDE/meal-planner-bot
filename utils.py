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

NOT_EMPTY = '^.+$'

def is_error(obj):
    return "error" in obj

def authenticate(meal_planner, update, context):
    print('Authenticating...')
    if not 'user' in context.user_data:
        print('User not in context...')
        update.message.reply_text("""I'm so sorry, I was sleeping. Just a moment that I need to settle down...""")
        user = meal_planner.get_user(update.message.chat.username)
        if is_error(user):
            print('User not registered...')

            update.message.reply_text(
                """Ups, it seems I do not know you yet. Please type /start to present yourself."""
            )
            return False
        else:
            update.message.reply_text("""Perfect! Let's start.""")
            context.user_data['user'] = user
            return True
    print('User already in context')
    return True

def get_diet_type(diet_type):
    diet_map = {
        'omni' : 'Omnivorous',
        'vegan' : 'Vegan',
        'vegetarian' : 'Vegetarian',
        'glutenFree' : 'Gluten free'
    }
    return diet_map[diet_type]


def get_activity_factor(activity_factor):
    activity_factor_map = {
        'none' : 'Better not to talk about that',
        'light' : 'A bit',
        'moderate' : 'Average',
        'very' : 'Quite a lot',
        'extra' : 'You\'re an athlete',    }
    
    return activity_factor_map[activity_factor]