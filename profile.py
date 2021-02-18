from telegram import ReplyKeyboardMarkup, Update
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    ConversationHandler,
    CallbackContext,
)
class ProfileManager:
    def __init__(self, db, logger):
        self.BIRTH, self.WEIGHT, self.HEIGHT, self.SEX, self.DIET, self.ACTIVITY_FACTOR, \
            self.CHOOSING, self.TYPING_REPLY, TYPING_CHOICE = range(9)
        self.db = db
        self.logger = logger
        self.sex_keyboard = [
            ['M', 'F', 'Other']
        ]
        self.sex_markup = ReplyKeyboardMarkup(self.sex_keyboard, one_time_keyboard=True)

        self.diet_keyboard = [
            ['Omnivorous', 'Vegetarian'],
            ['Vegan', 'Gluten free']
        ]
        self.diet_markup = ReplyKeyboardMarkup(self.diet_keyboard, one_time_keyboard=True)


        self.activity_keyboard = [
            ['Next?','A bit','Average'],
            ['Quite a lot', 'Athlete']
        ]
        self.activity_markup = ReplyKeyboardMarkup(self.activity_keyboard, one_time_keyboard=True)

        self.conv_handler = ConversationHandler(
            entry_points=[CommandHandler('start', self.start)],
            states={
                self.BIRTH: [
                    MessageHandler(
                        Filters.regex('^\d{4}$') & ~(Filters.command | Filters.regex('^Done$')),
                        self.birth_year,
                    )
                ],
                self.WEIGHT: [
                    MessageHandler(
                        Filters.regex('^\d+$') & ~(Filters.command | Filters.regex('^Done$')),
                        self.weight,
                    )
                ],
                self.HEIGHT: [
                    MessageHandler(
                        Filters.regex('^\d+$') & ~(Filters.command | Filters.regex('^Done$')),
                        self.height,
                    )
                ],
                self.SEX: [
                    MessageHandler(
                        Filters.regex('^(M|F|Other)$') & ~(Filters.command | Filters.regex('^Done$')),
                        self.sex,
                    )
                ],
                self.DIET: [
                    MessageHandler(
                        Filters.regex('^(Omnivorous|Vegan|Vegetarian|Gluten free)$') & ~(Filters.command | Filters.regex('^Done$')),
                        self.diet,
                    )
                ],
                self.ACTIVITY_FACTOR: [
                    MessageHandler(
                        Filters.regex('^(Next\?|A bit|Average|Quite a lot|Athlete)$') & ~(Filters.command | Filters.regex('^Done$')),
                        self.activity_factor,
                    )
                ],
                # self.CHOOSING: [
                #     MessageHandler(
                #         Filters.regex('^(Age|Favourite colour|Number of siblings)$'), regular_choice
                #     ),
                #     MessageHandler(Filters.regex('^Something else...$'), custom_choice),
                # ],
                # self.TYPING_CHOICE: [
                #     MessageHandler(
                #         Filters.text & ~(Filters.command | Filters.regex('^Done$')), regular_choice
                #     )
                # ],
                # self.TYPING_REPLY: [
                #     MessageHandler(
                #         Filters.text & ~(Filters.command | Filters.regex('^Done$')),
                #         received_information,
                #     )
                # ],
            },
            fallbacks=[MessageHandler(Filters.regex('^Done$'), self.done)],
        )

    def identify_user(self, chat):
        user = {}
        user["id"] = chat.id
        user["username"] = chat.username
        user["name"] = chat.first_name
        return user  

    def start(self, update: Update, context: CallbackContext) -> int:
        update.message.reply_text(
            "Welcome to meal planner bot."
            """Why don't you tell me something about yourself?
What is your birth year?
            """,
            # reply_markup=markup,
        )

        return self.BIRTH


    def birth_year(self, update: Update, context: CallbackContext) -> int:
        text = update.message.text
        birth_year = int(text)
        context.user_data['birth_year'] = birth_year
        update.message.reply_text(f'Wonderful! Tell me your weight (in kilos), please.')
        return self.WEIGHT


    def weight(self, update: Update, context: CallbackContext) -> int:
        text = update.message.text
        weight = int(text)
        context.user_data['weight'] = weight
        update.message.reply_text(f'Awesome! Tell me your height (in cm), please.')
        return self.HEIGHT

    def height(self, update: Update, context: CallbackContext) -> int:
        text = update.message.text
        height = int(text)
        context.user_data['height'] = height
        update.message.reply_text(f'Fabulous! Tell me your sex, please.',
            reply_markup=self.sex_markup)
        return self.SEX

    def sex(self, update: Update, context: CallbackContext) -> int:
        text = update.message.text
        sex = text.lower() if text in ['M', 'F'] else 'm'
        context.user_data['sex'] = sex
        update.message.reply_text(f'Brillant! Tell me your diet, please.',
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
        context.user_data['diet_type'] = diet
        update.message.reply_text(f'Stunning! How active are you?',
            reply_markup=self.activity_markup)
        return self.ACTIVITY_FACTOR
        
    def activity_factor(self, update: Update, context: CallbackContext) -> int:
        activity_map = {
                'Next?': 'none',
                'A bit': 'light',
                'Average': 'moderate',
                'Quite a lot': 'very',
                'Athlete': 'extra'
                }

        text = update.message.text
        activity = activity_map[text]
        context.user_data['activity_factor'] = activity
        
        update.message.reply_text(f'We are updating your profile...')
        
        user = self.save_user(context.user_data, update)
        
        update.message.reply_text(f'Magnificent! We saved your information correctly\n{user}')
        context.user_data.clear()
        return ConversationHandler.END

    def save_user(self, user_data, update):
        user = self.identify_user(update.message.chat)
        user_data['username'] = user['username']

        self.logger.info(str(user_data))
        return self.db.update_user(user_data)

    def done(self, update: Update, context: CallbackContext) -> int:
        user_data = context.user_data
        if 'choice' in user_data:
            del user_data['choice']

        update.message.reply_text(
            f"I learned these facts about you: {(user_data)} Until next time!"
        )

        user_data.clear()
        return ConversationHandler.END