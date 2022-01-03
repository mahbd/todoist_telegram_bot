import base64
import hashlib
import hmac
from os import environ

import requests
from flask import Flask, request, redirect

from features import check_auth, send_message
from user import MongoDataBase, User

app = Flask(__name__)
db = MongoDataBase()


@app.route('/')
def index():
    return str(db.save(User(tg_id='45454445')))


@app.route('/bot/', methods=['POST'])
def webhook():
    update = request.get_json(force=True)
    sender_id = update['message']['from']['id']
    user = db.get_user(sender_id, mute=True)
    if not user:
        user = db.save(User(tg_id=sender_id))
    message = update['message'].get('text', '')
    check_auth(user, message)
    return {'ok': True}


@app.route('/auth/', methods=['GET'])
def auth():
    code = request.args.get('code', None)
    state = request.args.get('state', None)
    if not code or not state:
        return 'code or state is missing'
    user = db.get_user_by_state(state, mute=True)
    if not user:
        print('user was not found by state while authenticating')
        return 'user was not found'

    data = dict(
        client_id=environ.get('TODOIST_ID'),
        client_secret=environ.get('TODOIST_SECRET'),
        code=code,
    )
    response = requests.post('https://todoist.com/oauth/access_token', data=data)
    if response.status_code != 200:
        return 'error'
    result = response.json()
    if 'error' in result and result['error']:
        return result['error']
    user.auth = result['access_token']
    user.state = None
    user = db.save(user)
    text = 'You are authorized! Everything is good!\nNow you can create new task just by writing it to me...'
    send_message(user, text)
    return str(user)


@app.route('/callback/', methods=['POST'])
def callback():
    if 'X-Todoist-Hmac-SHA256' not in request.headers:
        return 'no signature'
    signature = request.headers['X-Todoist-Hmac-SHA256']
    salt = environ.get('TODOIST_SECRET').encode()
    my_signature = base64.b64encode(
        hmac.new(salt, request.data, hashlib.sha256).digest()).decode()
    if signature != my_signature:
        return 'wrong signature'
    data = request.get_json(force=True)
    if not data:
        return 'empty json'
    if data['event_name'] != 'reminder:fired':
        return 'wrong event_name'
    user = db.get_user_by_todo_id(data['user_id'], mute=True)
    if not user:
        # TODO: we should revoke authorization for user and delete all his data in Todoist's sync directory
        return 'user was not found'
    item = user.api.items.get_by_id(data['event_data']['item_id'])
    if not item:
        return 'item not found'
    send_message(user, item.data['content'])
    return 'Ok!'


if __name__ == '__main__':
    app.run()
