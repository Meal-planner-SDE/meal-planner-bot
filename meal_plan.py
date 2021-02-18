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
    CHOOSE_MEAL_PLAN, CHOOSE_DAILY_PLAN = range(2)
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
        self.conv_handler_view = ConversationHandler(
            entry_points=[CommandHandler('viewmealplans', self.view_meal_plans)],
            states={
                MealPlanManager.CHOOSE_MEAL_PLAN: [
                    CallbackQueryHandler(self.choose_meal_plan),
                ],
                MealPlanManager.CHOOSE_DAILY_PLAN: [
                    CallbackQueryHandler(self.choose_daily_plan),
                ],
            },
            fallbacks=[MessageHandler(Filters.regex('^Done$'), self.done)],
        )

    def is_error(self, obj):
        return "error" in obj

    def authenticate(self, update, context):
        if not 'user' in context.user_data:
            user = self.meal_planner.get_user(update.message.chat.username)
            if self.is_error(user):
                update.message.reply_text(
                    """Ups, it seems I do not know you yet. Please type /start to present yourself."""
                )
                return False
            else:
                context.user_data['user'] = user
                return True
    def new_meal_plan(self, update, context):
        if not self.authenticate(update, context):
            return
        context.user_data['new_meal_plan'] = {}
        update.message.reply_text(
            """Wowie zowie, let's help you to create a new meal plan!
How many days would you plan?
            """,
            reply_markup=MealPlanManager.N_DAYS_MARKUP,
        )
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

        return MealPlanManager.N_MEALS

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
        del context.user_data['new_meal_plan']
        return ConversationHandler.END


    def view_meal_plans(self, update, context):
        if not self.authenticate(update, context):
            return
        meal_plans = self.meal_planner.get_meal_plans(context.user_data['user'])
        context.user_data['user_meal_plans'] = meal_plans
        keyboard = [
            [InlineKeyboardButton(f"#{i+1:2d}:{meal_plan['daily_calories']} calories - {meal_plan['diet_type']}", callback_data=i)] 
                for i, meal_plan in enumerate(meal_plans)
        ]
        markup = InlineKeyboardMarkup(keyboard)
        update.message.reply_text("Boo-ya, here are your meal plans:", reply_markup=markup)
        return MealPlanManager.CHOOSE_MEAL_PLAN
    def choose_meal_plan(self, update, context):
        return
    def choose_daily_plan(self, update, context):
        return

    def done(self, update, context):
        user_data = context.user_data
        if 'choice' in user_data:
            del user_data['choice']

        update.message.reply_text(
            f"I learned these facts about you: {(user_data)} Until next time!"
        )

        user_data.clear()
        return ConversationHandler.END

    