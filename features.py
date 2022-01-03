import random
from os import environ

from telegram import Bot, InlineKeyboardMarkup, InlineKeyboardButton

from user import User, MongoDataBase

bot = Bot(token=environ.get('BOT_TOKEN'))
db = MongoDataBase()


def send_message(user: User, message: str):
    bot.send_message(user.tg_id, message)


def send_buttons(user: User, message: str, buttons: list[list[InlineKeyboardButton]]):
    bot.send_message(user.tg_id, message, reply_markup=InlineKeyboardMarkup(buttons))


def add_todoist_task(user: User, message: str) -> [bool, str]:
    item = user.api.quick.add(message)
    if not item:
        send_message(user, 'Something went wrong...')
        return False
    labels = item['labels']
    if labels:
        labels = ['@' + label.data['name']
                  for label in user.api.labels.all() if label.data['id'] in labels]
    answer = 'Task added:\n{} {} {}'.format(
        item['content'], ' '.join(labels), item['due'] or '')
    send_message(user, answer)
    return True


def get_labels(user: User) -> bool:
    labels = user.api.labels.all()
    text = 'Labels:\n'
    for label in labels:
        text += f'{label.data["name"]}\n'
    send_message(user, text)
    return True


def get_projects(user: User) -> bool:
    projects = user.api.projects.all()
    text = 'Projects:\n'
    for project in projects:
        text += f'{project.data["name"]}\n'
    send_message(user, text)
    return True


def test_notification(user: User) -> bool:
    items = user.api.items.all()
    item = random.choice(items)
    text = f'{item.data["content"]}'
    send_message(user, text)
    return True


def process_command(user: User, message: str) -> [bool, str]:
    if message.startswith('/start'):
        text = 'You are authorized! Everything is good!\nNow you can create new task just by writing it to me...'
        send_message(user, text)
        return True, 'Working'
    elif message.startswith('/labels'):
        return get_labels(user), 'Labels'
    elif message.startswith('/projects'):
        return get_projects(user), 'Projects'
    elif message.startswith('/test_notification'):
        return test_notification(user), 'Test'
    else:
        return add_todoist_task(user, message)


def check_auth(user: User, message: str) -> [bool, str]:
    if not user.init_api():
        print("Resetting auth...")
        user = db.save(user)

    if not user.auth:
        user.state = ''.join([random.choice('abcdefghijklmnopqrstuvwxyz') for _ in range(10)])
        user = db.save(user)
        text = 'You are not authorized!\nPlease, authorize me by clicking on the button below...'
        scope = 'data:read_write,data:delete'
        url = f'https://todoist.com/oauth/authorize?client_id={environ.get("TODOIST_ID")}&scope={scope}&state={user.state}'
        send_buttons(user, text, [[InlineKeyboardButton(text='Authorize', url=url)]])
        return False, 'UnauthenticatedTodoist'
    return process_command(user, message)
