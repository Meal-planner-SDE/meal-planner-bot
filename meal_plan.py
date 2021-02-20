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
            fallbacks=[MessageHandler(Filters.command | Filters.regex('^Done$'), self.done)],
        )
        self.conv_handler_view = ConversationHandler(
            entry_points=[CommandHandler('viewmealplans', self.choose_meal_plan)],
            states={
                MealPlanManager.CHOOSE_DAILY_PLAN: [
                    CallbackQueryHandler(self.choose_daily_plan, pattern='^((?!exit|back_.*).)*$'),
                    CallbackQueryHandler(self.back_exit, pattern='^(exit|back_.*)$'),
                ],
                MealPlanManager.CHOOSE_RECIPE: [
                    CallbackQueryHandler(self.choose_recipe, pattern='^((?!exit|back_.*).)*$'),
                    CallbackQueryHandler(self.back_exit, pattern='^(exit|back_.*)$'),
                ],
                MealPlanManager.VIEW_RECIPE: [
                    CallbackQueryHandler(self.view_recipe, pattern='^((?!exit|back_.*).)*$'),
                    CallbackQueryHandler(self.back_exit, pattern='^(exit|back_.*)$'),
                ],
            },
            fallbacks=[MessageHandler(Filters.command | Filters.regex('^Done$'), self.done)],
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


    def choose_meal_plan(self, update, context):
        if not utils.authenticate(self.meal_planner, update, context):
            return
        
        if not 'user_meal_plans' in context.user_data:
            message_fn = update.message.reply_text
            message_fn("I'm collecting your meal plans, just a moment...")
            meal_plans = self.meal_planner.get_meal_plans(context.user_data['user'])
            context.user_data['user_meal_plans'] = meal_plans
        else:
            query = update.callback_query
            message_fn = query.edit_message_text
            message_fn("I'm collecting your meal plans, just a moment...")
            meal_plans = context.user_data['user_meal_plans']
        keyboard = [
            [InlineKeyboardButton(f"#{i+1:2d}:{meal_plan['daily_calories']} calories - {meal_plan['diet_type']}", callback_data=i)]
                for i, meal_plan in enumerate(meal_plans)
        ]
        keyboard.extend([
            [InlineKeyboardButton("Exit", callback_data="exit")]
        ])
        markup = InlineKeyboardMarkup(keyboard)
        
        message_fn("Boo-ya, here are your meal plans:", reply_markup=markup)
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
        keyboard.extend([
            [InlineKeyboardButton("Back", callback_data=f"back_mp_0")],
            [InlineKeyboardButton("Exit", callback_data="exit")]
        ])
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
        context.user_data['user_recipes'] = recipes_info
        # if not 'user_recipes' in context.user_data:
        # else:
        #     recipes_info = context.user_data['user_recipes']

        keyboard = [
            [InlineKeyboardButton(f"{recipes_info[recipe['recipe_id']]['title']}", callback_data=recipe['recipe_id'])] 
                for recipe in daily_plan['recipes']
        ]
        
        keyboard.extend([
            [InlineKeyboardButton("Back", callback_data=f"back_dp_{meal_plan_i}")],
            [InlineKeyboardButton("Exit", callback_data="exit")]
        ])
        markup = InlineKeyboardMarkup(keyboard)
        query.edit_message_text(
            text=f"These are the recipes of day #{daily_plan_i + 1} of meal plan #{meal_plan_i + 1}", reply_markup=markup
        )
        return MealPlanManager.VIEW_RECIPE

    def view_recipe(self, update, context):
        query = update.callback_query
        query.answer()
        recipes_info = context.user_data['user_recipes']
        daily_plan_i = context.user_data['user_daily_plan_chosen']
        recipe_id = int(query.data)
        keyboard = []
        keyboard.extend([
            [InlineKeyboardButton("Back", callback_data=f"back_rp_{daily_plan_i}")],
            [InlineKeyboardButton("Exit", callback_data="exit")]
        ])
        markup = InlineKeyboardMarkup(keyboard)
        # print((recipes_info[recipe_id]['instructions']))
        # print(markdownify(recipes_info[recipe_id]['instructions']))
        instructions = "I wasn't able to find any instructions for this recipe. You'll have to be creative I guess."
        recipe = recipes_info[recipe_id]
        image = ""
        if recipe['instructions']:
            instructions = recipe['instructions']
        if 'image' in recipe:
            if recipe['image']:
                image = f"[​​​​​​​​​​​]({recipe['image']})"
        query.edit_message_text(
            text=f"""Let's have a look at {recipe['title']}:
            {image}
{markdownify(instructions)}
            """, reply_markup=markup, parse_mode=ParseMode.MARKDOWN
        )
        return 

    def back_exit(self, update, context):
        query = update.callback_query
        query.answer()
        action = query.data
        if action == 'exit':
            return self.menu_exit(update, context)
        _, action, data = action.split('_')
        query.data = data
        if action == 'mp':
            return self.choose_meal_plan(update, context)
        if action == 'dp':
            return self.choose_daily_plan(update, context)
        if action == 'rp':
            return self.choose_recipe(update, context)

    def done(self, update: Update, context: CallbackContext) -> int:
        user_data = context.user_data
        attributes = ['new_meal_plan', 'user_meal_plans', 'user_meal_plan_chosen', 'user_daily_plan_chosen', 'user_recipes']
        for attribute in attributes:
            if attribute in user_data:
                del user_data[attribute]

        update.message.reply_text(
            f"Uh-oh, it seems like you weren't able to complete the process. See you soon."
        )

        return ConversationHandler.END

    def menu_exit(self, update, context):
        user_data = context.user_data
        attributes = ['new_meal_plan', 'user_meal_plans', 'user_meal_plan_chosen', 'user_daily_plan_chosen', 'user_recipes']
        for attribute in attributes:
            if attribute in user_data:
                del user_data[attribute]
        query = update.callback_query
        query.answer()
        query.edit_message_text("Whoopee, see you later!", reply_markup = None)
        return ConversationHandler.END