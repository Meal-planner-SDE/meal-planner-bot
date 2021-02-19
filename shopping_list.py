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

class ShoppingListManager:
    MEAL_PLAN_ID = 0

    def __init__(self, meal_planner, logger):
        self.meal_planner = meal_planner
        self.logger = logger
        self.conv_handler_meal_plan_to_shopping_list = ConversationHandler(
            entry_points=[CommandHandler('mptosl', self.meal_plan_to_shopping_list)],
            states={
                ShoppingListManager.MEAL_PLAN_ID: [
                    MessageHandler(
                        Filters.regex('^\d+$') & ~(Filters.command | Filters.regex('^Done$')),
                        self.add_meal_plan_to_shopping_list,
                    ),
                ]
            },
            fallbacks=[MessageHandler(Filters.regex('^Done$'), self.done)],
        )

    def meal_plan_to_shopping_list(self, update, context):
        MEAL_PLAN_IDS_KEYBOARD = [
            # add ids of meal plans
        ]
        update.message.reply_text(
            """Someone told me that you'd like to get all the ingredients of your meal plan in a shopping list.
What's the ID of the meal plan?
            """,
            reply_markup=ReplyKeyboardMarkup(MEAL_PLAN_IDS_KEYBOARD, one_time_keyboard=True, resize_keyboard=True),
        )

        return ShoppingListManager.MEAL_PLAN_ID
    
    def add_meal_plan_to_shopping_list(self, update, context):
        meal_plan_id = int(update.message.text)
        update.message.reply_text(
            """Alright, this will take a while. Sit back and enjoy...
            """,
        )

        shopping_list = self.meal_planner.add_meal_plan_to_shopping_list(context.user_data['user'], meal_plan_id)

        update.message.reply_text(
            f"""We're finally done! Here is your shining shopping list:
{shopping_list}
            """
        )

        return ConversationHandler.END

    def done(self, update, context):
        user_data = context.user_data
        if 'choice' in user_data:
            del user_data['choice']

        update.message.reply_text(
            f"I learned these facts about you: {(user_data)} Until next time!"
        )

        user_data.clear()
        return ConversationHandler.END