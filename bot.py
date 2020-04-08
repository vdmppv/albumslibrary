import telebot
from telebot import types
import config
import lastfm
import sqlite3
import pymongo
from bson import ObjectId

bot = telebot.TeleBot(config.token)
user_out_dict = dict() # словарь, ставящий в соответствие каждому пользователю полученный массив исполнителей/треков для дальнейшей работы
user_inp_dict = dict() # словарь, ставящий в соответствие каждому пользователю исходный массив исполнителей/треков для дальнейшей работы
wait_flag = dict() # флаги ожидания добавления нового искомого
step_items = 6 # количество
error_text = "\nВозможно, неверный формат ввода. \n Для поиска похожих композиций необходимо вводить исходную композицию в формате исполнитель-трек. Для поиска похожих исполнителей возможен ввод только имени исполнителя. Введите /help для получения подробной справки."

client = pymongo.MongoClient("mongodb://localhost:27017/")
db = client["project_database"]
user_settings = db['user_settings']

def get_user_settings(chat_id, setting_name):
    if setting_name == "show_photo":
        setting_value = user_settings.find_one({'user_id': chat_id})['show_photo']
    else:
        setting_value = user_settings.find_one({'user_id': chat_id})['show_url']
    
    return setting_value

def set_user_settings(chat_id, setting_name, setting_value):
    st_val = {'user_id': chat_id}
    settings_value = user_settings.find_one(st_val)
    if setting_name == "show_photo":
        if settings_value:
            user_settings.update_one(st_val, {'$set':{'show_photo': setting_value}})
        else:
            st_val['show_photo'] = setting_value
            user_settings.insert(st_val)
    else:
        if settings_value:
            user_settings.update_one(st_val, {'$set':{'show_url': setting_value}})
        else:
            st_val['show_url'] = setting_value
            user_settings.insert(st_val)

def add_user(chat_id):
    user = db.user_settings.find_one({'user_id': chat_id})
    if not user:
        print("Создаём нового пользователя!")
        db.user_settings.insert_one({'user_id':chat_id, 'show_photo': True, 'show_url': True})

@bot.message_handler(commands=['photo_off'])
def handle_photo_off(message):
    set_user_settings(message.chat.id, "show_photo", False)

@bot.message_handler(commands=['photo_on'])
def handle_photo_on(message):
    set_user_settings(message.chat.id, "show_photo", True)

@bot.message_handler(commands=['url_off'])
def handle_url_off(message):
    set_user_settings(message.chat.id, "show_url", False)

@bot.message_handler(commands=['url_on'])
def handle_url_on(message):
    set_user_settings(message.chat.id, "show_url", True)

@bot.message_handler(commands=['start', 'help'])
def handle_start_help(message):
    add_user(message.chat.id)
    helpText = """
        Бот осуществляет поиск похожих исполнителей или треков используя ресурс LastFm.
        Для осуществления поиска необходимо ввести название композиции в формате:
        исполнитель - трек или же просто исполнитель

        Настройки:
        Для отключения вывода изображений введите команду:
        /photo_off
        Для включения введите:
        /photo_on

        Для отключения вывода ссылок введите команду:
        /url_off
        Для включения введите:
        /url_on
    """
    bot.send_message(message.chat.id, helpText)


@bot.message_handler(content_types=["text"])
def text_handler(message): # обработчик текстовых сообщений

    text_message = message.text
    chat_id = message.chat.id
    print("Получено сообщение = " + text_message)
    keyboard = types.InlineKeyboardMarkup()

    if len(user_inp_dict) == 0: #  проверяем новое ли это сообщение, или добавление в список на поиск.
        user_inp_dict[message.chat.id] = [text_message]
        add_user(chat_id)
    else:
        user_inp_dict[message.chat.id].append(text_message)

    top_button = types.InlineKeyboardButton(text="Самые популярные песни исполнителя", callback_data="top " + text_message)
    artists_button = types.InlineKeyboardButton(text="Найти похожих исполнителей", callback_data="show artist " + text_message)
    tracks_button = types.InlineKeyboardButton(text="Найти похожие треки", callback_data="show track " + text_message)
    add_button = types.InlineKeyboardButton(text="Добавить в поиск еще один трек/исполнителя", callback_data="add " + text_message)
    keyboard.add(top_button)
    keyboard.add(artists_button)
    keyboard.add(tracks_button)
    keyboard.add(add_button)
    bot.send_message(message.chat.id, "Выберите действие:", reply_markup=keyboard)


@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    text_message_array = call.data.split(' ')
    action= ""
    if len(text_message_array) >= 1:
        action = text_message_array[0]
    if action == "top":
        send_top(call)
    elif action == "show":
        show_action(call)
    elif action == "add":
        add_action(call)
    elif action == "next":
        send_next(call)


def send_top(call):
    print("Top songs: ")
    print(user_inp_dict)

    user_out_dict[call.message.chat.id] = lastfm.get_top_tracks(config.lastFmKey, user_inp_dict[call.message.chat.id])

    user_inp_dict.clear()
    num_items = min(len(user_out_dict[call.message.chat.id]), step_items)

    print ("num_items " + str(num_items))
    
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="Самые популярные песни: ")

    for i in range (0, num_items):
        print(user_out_dict[call.message.chat.id][i].name)
        print(user_out_dict[call.message.chat.id][i].url)
        print()
        mess_to_send = user_out_dict[call.message.chat.id][i].name + " \n"
        mess_to_send += user_out_dict[call.message.chat.id][i].url
        bot.send_message(call.message.chat.id, mess_to_send, disable_web_page_preview=True)
        
    
    user_out_dict[call.message.chat.id] = user_out_dict[call.message.chat.id][num_items:]


def add_action(call):
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="Введите еще одну композицию или исполнителя.")
    wait_flag[call.message.chat.id] = True


def show_action(call):
    print("user_inp_dict")
    print(user_inp_dict)
    text_message_array = call.data.split(' ')
    method = ""

    if len(text_message_array) >= 2:
        method = text_message_array[1]

    if call.message.chat.id in user_inp_dict:
        user_out_dict[call.message.chat.id] = lastfm.get_similar_from_array(config.lastFmKey, user_inp_dict[call.message.chat.id], method) 

    user_inp_dict.clear()
    call.data = "next " + method
    send_next(call)


def send_next(call):

    photo_flag = int(get_user_settings(call.message.chat.id, 'show_photo'))
    url_flag = int(get_user_settings(call.message.chat.id, 'show_url'))

    print("photo_flag = " + str(get_user_settings(call.message.chat.id, 'show_photo')))
    print("url_flag = " + str(get_user_settings(call.message.chat.id, 'show_url')))

    print("photo_flag = " + str(photo_flag))
    print("url_flag = " + str(url_flag))

    text_message_array = call.data.split(' ')
    method = ""
    if len(text_message_array) >= 2:
        method = text_message_array[1]

    if not call.message.chat.id in user_out_dict:
        return

    num_items = min(len(user_out_dict[call.message.chat.id]), step_items)

    print("num_items = " + str(num_items))

    if method == "artist":
        if not num_items:
            text = "Похожих исполнитей не найдено! " + error_text
        else:
            text = "Похожие исполнители:"
    else:
        if not num_items:
            text = "Похожих треков не найдено! " + error_text
        else:
            text = "Похожие треки:"

    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=text)

    if method == "artist":
        for i in range(0, num_items):
            print(user_out_dict[call.message.chat.id][i].name)
            print(user_out_dict[call.message.chat.id][i].image)
            print(user_out_dict[call.message.chat.id][i].url)
            print()
            mess_to_send = user_out_dict[call.message.chat.id][i].name + " \n"
            if url_flag:
                mess_to_send += user_out_dict[call.message.chat.id][i].url
            bot.send_message(call.message.chat.id, mess_to_send, disable_web_page_preview=True)

            if photo_flag:
                bot.send_photo(call.message.chat.id, user_out_dict[call.message.chat.id][i].image)
    elif method == "track":
        for i in range(0, num_items):
            print(user_out_dict[call.message.chat.id][i].artist)
            print(user_out_dict[call.message.chat.id][i].name)
            print(user_out_dict[call.message.chat.id][i].image)
            print(user_out_dict[call.message.chat.id][i].url)
            print()
            mess_to_send = user_out_dict[call.message.chat.id][i].artist + " - " + user_out_dict[call.message.chat.id][i].name + " \n"
            if url_flag:
                mess_to_send += user_out_dict[call.message.chat.id][i].url
            bot.send_message(call.message.chat.id, mess_to_send, disable_web_page_preview=True)

            if photo_flag:
                bot.send_photo(call.message.chat.id, user_out_dict[call.message.chat.id][i].image)
    else:
        return

    user_out_dict[call.message.chat.id] = user_out_dict[call.message.chat.id][num_items:]

    if len(user_out_dict[call.message.chat.id]) > 0:
        keyboard = types.InlineKeyboardMarkup()
        next_button = types.InlineKeyboardButton(text="Показать еще " + str(step_items),
                                                 callback_data="next " + method)
        keyboard.add(next_button)
        bot.send_message(call.message.chat.id, "...", reply_markup=keyboard)


if __name__ == '__main__':
    bot.polling(none_stop=True)


