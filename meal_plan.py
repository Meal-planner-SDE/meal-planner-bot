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
class MealPlanManager:
    MAX_DAYS = 10
    MAX_MEALS = 10
    N_DAYS, N_MEALS = range(2)
    N_DAYS_KEYBOARD = [
        list(range(1, MAX_DAYS + 1))
    ]
    N_DAYS_MARKUP = ReplyKeyboardMarkup(N_DAYS_KEYBOARD, one_time_keyboard=True, resize_keyboard=True)

    N_MEALS_KEYBOARD = [
        list(range(1, MAX_DAYS + 1))
    ]
    N_MEALS_MARKUP = ReplyKeyboardMarkup(N_MEALS_KEYBOARD, one_time_keyboard=True, resize_keyboard=True)

    def __init__(self, meal_planner, logger):
        self.meal_planner = meal_planner
        self.logger = logger
        self.conv_handler_create = ConversationHandler(
            entry_points=[CommandHandler('newmealplan', self.new_meal_plan)],
            states={
                MealPlanManager.N_DAYS: [
                    MessageHandler(
                        Filters.regex('^\d$') & ~(Filters.command | Filters.regex('^Done$')),
                        self.n_days,
                    ),
                ],
                MealPlanManager.N_MEALS: [
                    MessageHandler(
                        Filters.regex('^\d$') & ~(Filters.command | Filters.regex('^Done$')),
                        self.n_meals,
                    ),
                ],
            },
            fallbacks=[MessageHandler(Filters.regex('^Done$'), self.done)],
        )

    def new_meal_plan(self, update, context):
        
        update.message.reply_text(
            """Wowie zowie, let's help you to create a new meal plan!
How many days would you plan?
            """,
            reply_markup=MealPlanManager.N_DAYS_MARKUP,
        )
        context.user_data['new_meal_plan'] = {}

        return MealPlanManager.N_DAYS

    def n_days(self, update, context):
        text = update.message.text
        days = int(text)
        
        if not (0 < days < MealPlanManager.MAX_DAYS):
            error_str = "Wooopsie."
            update.message.reply_text(error_str)
            return MealPlanManager.N_DAYS

        context.user_data['new_meal_plan']['n_days'] = days
        update.message.reply_text(
            """Stupendous! What about the number of meals per day you desire?
            """,
            reply_markup=MealPlanManager.N_MEALS_MARKUP,
        )

        return self.N_MEALS

    def n_meals(self, update, context):
        text = update.message.text
        meals = int(text)
        
        if not (0 < meals < MealPlanManager.MAX_MEALS):
            error_str = "Wooopsie."
            update.message.reply_text(error_str)
            return MealPlanManager.N_MEALS

        context.user_data['new_meal_plan']['n_meals'] = meals
        update.message.reply_text(
            """Marvellous! 
I'm working to make the meal plan of your dreams, it might take some time...
            """
        )
        new_meal_plan = context.user_data['new_meal_plan']
        meal_plan = self.meal_planner.create_meal_plan(context.user_data['user'], new_meal_plan['n_days'], new_meal_plan['n_meals'])
        update.message.reply_text(
            f"""Here it is:
{meal_plan}
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