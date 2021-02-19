from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, ReplyKeyboardMarkup, ParseMode
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    ConversationHandler,
    CallbackContext,
    CallbackQueryHandler,
)
from markdownify import markdownify
import utils

class MealPlanManager:
    MAX_DAYS = 10
    MAX_MEALS = 10
    N_DAYS, N_MEALS = range(2)
    CHOOSE_MEAL_PLAN, CHOOSE_DAILY_PLAN, CHOOSE_RECIPE, VIEW_RECIPE = range(4)
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
                MealPlanManager.CHOOSE_DAILY_PLAN: [
                    CallbackQueryHandler(self.choose_daily_plan),
                ],
                MealPlanManager.CHOOSE_RECIPE: [
                    CallbackQueryHandler(self.choose_recipe),
                ],
                MealPlanManager.VIEW_RECIPE: [
                    CallbackQueryHandler(self.view_recipe),
                ],
            },
            fallbacks=[MessageHandler(Filters.regex('^Done$'), self.done)],
        )

    def new_meal_plan(self, update, context):
        if not utils.authenticate(self.meal_planner, update, context):
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
        if not utils.authenticate(self.meal_planner, update, context):
            return
        update.message.reply_text("I'm collecting your meal plans, just a moment...")
        meal_plans = self.meal_planner.get_meal_plans(context.user_data['user'])
        context.user_data['user_meal_plans'] = meal_plans
        keyboard = [
            [InlineKeyboardButton(f"#{i+1:2d}:{meal_plan['daily_calories']} calories - {meal_plan['diet_type']}", callback_data=i)]
                for i, meal_plan in enumerate(meal_plans)
        ]
        markup = InlineKeyboardMarkup(keyboard)
        update.message.reply_text("Boo-ya, here are your meal plans:", reply_markup=markup)
        return MealPlanManager.CHOOSE_DAILY_PLAN

    def choose_meal_plan(self, update, context):
        meal_plans = context.user_data['user_meal_plans']
        keyboard = [
            [InlineKeyboardButton(f"#{i+1:2d}:{meal_plan['daily_calories']} daily kcal - {meal_plan['diet_type']}", callback_data=i)] 
                for i, meal_plan in enumerate(meal_plans)
        ]
        markup = InlineKeyboardMarkup(keyboard)
        update.message.reply_text("Boo-ya, here are your meal plans:", reply_markup=markup)
        return MealPlanManager.CHOOSE_DAILY_PLAN

    def choose_daily_plan(self, update, context):
        query = update.callback_query
        query.answer()
        meal_plan_i = int(query.data)
        context.user_data['user_meal_plan_chosen'] = meal_plan_i
        meal_plan = context.user_data['user_meal_plans'][meal_plan_i]
        daily_plans = meal_plan['daily_plans']
        keyboard = [
            [InlineKeyboardButton(f"#{daily_plan['daily_plan_number'] + 1:2d}", callback_data=i)] 
                for i, daily_plan in enumerate(daily_plans)
        ]
        markup = InlineKeyboardMarkup(keyboard)

        query.edit_message_text(
            text=f"""These are the daily plans of the meal number #{meal_plan_i + 1}.
Daily calories: {meal_plan['daily_calories']} - Diet: {meal_plan['diet_type']}    
            """, reply_markup=markup
        )
        return MealPlanManager.CHOOSE_RECIPE

    def choose_recipe(self, update, context):
        query = update.callback_query
        query.answer()

        daily_plan_i = int(query.data)
        context.user_data['user_daily_plan_chosen'] = daily_plan_i

        meal_plan_i = context.user_data['user_meal_plan_chosen']
        daily_plan = context.user_data['user_meal_plans'][meal_plan_i]['daily_plans'][daily_plan_i]
        query.edit_message_text(
            text="I'm collecting the recipes of the day, just a moment..."
        )
        
        recipes_info = self.meal_planner.get_recipes_info(daily_plan['recipes'])
        context.user_data['recipes'] = recipes_info

        keyboard = [
            [InlineKeyboardButton(f"{recipes_info[recipe['recipe_id']]['title']}", callback_data=recipe['recipe_id'])] 
                for i, recipe in enumerate(daily_plan['recipes'])
        ]
        markup = InlineKeyboardMarkup(keyboard)
        query.edit_message_text(
            text=f"These are the recipes of day #{daily_plan_i + 1} of meal plan #{meal_plan_i + 1}", reply_markup=markup
        )
        return MealPlanManager.VIEW_RECIPE

    def view_recipe(self, update, context):
        query = update.callback_query
        query.answer()
        recipes_info = context.user_data['recipes']
        daily_plan_i = context.user_data['user_daily_plan_chosen']
        recipe_id = int(query.data)
        keyboard = [
            [InlineKeyboardButton(f"back", callback_data=1)]
        ]
        markup = InlineKeyboardMarkup(keyboard)
        print((recipes_info[recipe_id]['instructions']))
        print(markdownify(recipes_info[recipe_id]['instructions']))
        query.edit_message_text(
            text=f"""Let's have a look at {recipes_info[recipe_id]['title']}:
            [​​​​​​​​​​​]({recipes_info[recipe_id]['image']})
{markdownify(recipes_info[recipe_id]['instructions'])}
            """, reply_markup=markup, parse_mode=ParseMode.MARKDOWN
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

    