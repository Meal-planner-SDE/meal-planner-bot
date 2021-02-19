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
    if not 'user' in context.user_data:
        user = meal_planner.get_user(update.message.chat.username)
        if is_error(user):
            update.message.reply_text(
                """Ups, it seems I do not know you yet. Please type /start to present yourself."""
            )
            return False
        else:
            context.user_data['user'] = user
            return True