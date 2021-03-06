from telegram import ReplyKeyboardMarkup, Update
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    ConversationHandler,
    CallbackContext,
)
from datetime import date
import utils

class ProfileManager:
    def __init__(self, meal_planner, logger):
        self.BIRTH, self.WEIGHT, self.HEIGHT, self.SEX, self.DIET, self.ACTIVITY_FACTOR, \
            self.CHOOSING, self.TYPING_REPLY, TYPING_CHOICE = range(9)
        self.meal_planner = meal_planner
        self.logger = logger
        self.sex_keyboard = [
            ['M', 'F', 'Other']
        ]
        self.sex_markup = ReplyKeyboardMarkup(self.sex_keyboard, one_time_keyboard=True,  resize_keyboard=True)

        self.diet_keyboard = [
            ['Omnivorous', 'Vegetarian'],
            ['Vegan', 'Gluten free']
        ]
        self.diet_markup = ReplyKeyboardMarkup(self.diet_keyboard, one_time_keyboard=True,  resize_keyboard=True)


        self.activity_keyboard = [
            ['Next?','A bit','Average'],
            ['Quite a lot', 'I\'m an athlete']
        ]
        self.activity_markup = ReplyKeyboardMarkup(self.activity_keyboard, one_time_keyboard=True,  resize_keyboard=True)

        self.conv_handler_edit = ConversationHandler(
            entry_points=[CommandHandler('start', self.edit_profile), CommandHandler('editprofile', self.edit_profile)],
            states={
                self.BIRTH: [
                    MessageHandler(
                        Filters.regex('^\d{4}$') & ~(Filters.command | Filters.regex('^Done$')),
                        self.birth_year,
                    ),
                    MessageHandler(
                        Filters.text & ~(Filters.command | Filters.regex('^Done$')),
                        self.error_invalid_birthyear,
                    )
                ],
                self.WEIGHT: [
                    MessageHandler(
                        Filters.regex('^\d+$') & ~(Filters.command | Filters.regex('^Done$')),
                        self.weight,
                    ),
                    MessageHandler(
                        Filters.text & ~(Filters.command | Filters.regex('^Done$')),
                        self.error_number_required,
                    )
                ],
                self.HEIGHT: [
                    MessageHandler(
                        Filters.regex('^\d+$') & ~(Filters.command | Filters.regex('^Done$')),
                        self.height,
                    ),
                    MessageHandler(
                        Filters.text & ~(Filters.command | Filters.regex('^Done$')),
                        self.error_number_required,
                    )
                ],
                self.SEX: [
                    MessageHandler(
                        Filters.regex('^(M|F|Other)$') & ~(Filters.command | Filters.regex('^Done$')),
                        self.sex,
                    ),
                    MessageHandler(
                        Filters.text & ~(Filters.command | Filters.regex('^Done$')),
                        self.error_invalid_sex,
                    )
                ],
                self.DIET: [
                    MessageHandler(
                        Filters.regex('^(Omnivorous|Vegan|Vegetarian|Gluten free)$') & ~(Filters.command | Filters.regex('^Done$')),
                        self.diet,
                    ),
                    MessageHandler(
                        Filters.text & ~(Filters.command | Filters.regex('^Done$')),
                        self.error_invalid_diet,
                    )
                ],
                self.ACTIVITY_FACTOR: [
                    MessageHandler(
                        Filters.regex('^(Next\?|A bit|Average|Quite a lot|I\'m an athlete)$') & ~(Filters.command | Filters.regex('^Done$')),
                        self.activity_factor,
                    ),
                    MessageHandler(
                        Filters.text & ~(Filters.command | Filters.regex('^Done$')),
                        self.error_invalid_activity_factor,
                    )
                ],
            },
            fallbacks=[MessageHandler(Filters.command | Filters.regex('^Done$'), self.done)],
        )
        self.conv_handler_show = CommandHandler('profile', self.profile)

    def identify_user(self, chat):
        user = {}
        user["id"] = chat.id
        user["username"] = chat.username
        user["name"] = chat.first_name
        return user 

    def error_number_required(self, update, context):
        update.message.reply_text(
            """Hey, apparently that's not a valid answer. You should answer with a number."""
        )

    def error_invalid_birthyear(self, update, context):
        update.message.reply_text(
            """Huh, that doesn't seem like the year you were born in. Tell me the truth."""
        )

    def error_invalid_sex(self, update, context):
        update.message.reply_text(
            """Uh-oh. I'm sorry, it seems I can't help you. You should choose a sex \
among 'M' (male), 'F' (female) or 'Other'.
            """
        )


    def error_invalid_diet(self, update, context):
        update.message.reply_text(
            """Yow, that's got to be a new diet type! 
Unfortunately I only know \
'Omnivorous', 'Vegetarian', 'Vegan' and  'Gluten free'. Please choose \
among these types, I'll make sure to lean more about that.
            """
        )

    def error_invalid_activity_factor(self, update, context):
        update.message.reply_text(
            """Ouch, I don't think understand what you mean. Could you be more precise? \
I only know how to behave to the following answers:
'Next?', 'A bit', 'Average', 'Quite a lot', 'I\'m an athlete'
            """
        )


    def edit_profile(self, update: Update, context: CallbackContext) -> int:
        update.message.reply_text(
            """Welcome to meal planner bot.
To help you to manage your meal plans, I need to know more about you.
What is your birth year?
            """,
            # reply_markup=markup,
        )
        context.user_data['tmp_user'] = {}
        return self.BIRTH


    def birth_year(self, update: Update, context: CallbackContext) -> int:
        text = update.message.text
        birth_year = int(text)
        
        current_year = date.today().year
        if birth_year > current_year:
            error_str = "I am not able to serve visitors from the future, I'm sorry."
            update.message.reply_text(error_str)
            return self.BIRTH

        context.user_data['tmp_user']['birth_year'] = birth_year
        update.message.reply_text(f'Wonderful! Tell me your weight (in kg), please.')
        return self.WEIGHT

    def weight(self, update: Update, context: CallbackContext) -> int:
        text = update.message.text
        weight = int(text)
        context.user_data['tmp_user']['weight'] = weight
        update.message.reply_text(f'Awesome! Tell me your height (in cm), please.')
        return self.HEIGHT

    def height(self, update: Update, context: CallbackContext) -> int:
        text = update.message.text
        height = int(text)
        context.user_data['tmp_user']['height'] = height
        update.message.reply_text(f'Fabulous! Tell me your sex, please.',
            reply_markup=self.sex_markup)
        return self.SEX

    def sex(self, update: Update, context: CallbackContext) -> int:
        text = update.message.text
        sex = text.lower() if text in ['M', 'F'] else 'm'
        context.user_data['tmp_user']['sex'] = sex
        update.message.reply_text(f'Brillant! What is your diet type?',
            reply_markup=self.diet_markup)
        return self.DIET
        

    def diet(self, update: Update, context: CallbackContext) -> int:
        diet_map = {
                'Omnivorous': 'omni',
                'Vegan': 'vegan',
                'Vegetarian': 'vegetarian',
                'Gluten free': 'glutenFree'
                }

        text = update.message.text
        diet = diet_map[text]
        context.user_data['tmp_user']['diet_type'] = diet
        update.message.reply_text(f'Stunning! How active would you define yourself?',
            reply_markup=self.activity_markup)
        return self.ACTIVITY_FACTOR
        
    def activity_factor(self, update: Update, context: CallbackContext) -> int:
        activity_map = {
                'Next?': 'none',
                'A bit': 'light',
                'Average': 'moderate',
                'Quite a lot': 'very',
                'I\'m an athlete': 'extra'
                }

        text = update.message.text
        activity = activity_map[text]
        context.user_data['tmp_user']['activity_factor'] = activity
        
        update.message.reply_text(f'I\'m updating your profile...')
        
        user = self.save_user(context.user_data['tmp_user'], update)
        if utils.is_error(user):
            update.message.reply('''
Ouch! It seems there's been an error, I'm so sorry! I suggest to try again in a few minutes.
            ''')
            return ConversationHandler.END
        context.user_data['user'] = user
        update.message.reply_text(f'''Magnificent! Your information have been saved correctly. You can type /profile to 
see your information.''')

        return ConversationHandler.END

    def save_user(self, user, update):
        chat_user = self.identify_user(update.message.chat)
        user['username'] = chat_user['username']

        self.logger.info(str(user))
        return self.meal_planner.update_user(user)

    def profile(self, update, context):
        if not utils.authenticate(self.meal_planner, update, context):
            return
        user = context.user_data['user']

        update.message.reply_text(f"""Cowabunga {user['username']}! This is what I know about you:
- Height: {user['height']} cm
- Weight: {user['weight']} kg
- Sex: {user['sex'].upper()}
- Birth year: {user['birth_year']}
- Diet: {utils.get_diet_type(user['diet_type'])}
- Activity factor: {utils.get_activity_factor(user['activity_factor'])}

If you wish to change something, just type /editprofile. 
        """
        )

    def done(self, update: Update, context: CallbackContext) -> int:
        user_data = context.user_data
        if 'tmp_user' in user_data:
            del user_data['tmp_user']

        update.message.reply_text(
            f"Uh-oh, it seems like you weren't able to complete the process. See you soon."
        )

        return ConversationHandler.END

