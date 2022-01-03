from os import environ

from pymongo import MongoClient
from todoist import TodoistAPI


class User:
    def __init__(self, tg_id, todo_id=None, auth=None, state=None):
        self.tg_id = tg_id
        self.todo_id = todo_id
        self.auth = auth
        self.state = state
        self.api = None

    def __str__(self):
        return f"User: {self.tg_id}, {self.todo_id}, {self.auth}, {self.state}"

    def init_api(self) -> bool:
        if not self.auth:
            self.api = None
            return False
        api = TodoistAPI(self.auth)
        result = api.sync()
        if 'error' in result:
            self.auth = None
            self.todo_id = None
            return False
        self.api = api
        return True

    def to_dict(self):
        return {
            "tg_id": self.tg_id,
            "todo_id": self.todo_id,
            "auth": self.auth,
            "state": self.state
        }

    def from_dict(self, data):
        self.tg_id = data.get("tg_id")
        self.todo_id = data.get("todo_id")
        self.auth = data.get("auth")
        self.state = data.get("state")
        return self


class MongoDataBase:
    def __init__(self):
        self.client = MongoClient(environ.get("MONGO_URL"))
        self.db = self.client['todoist_bot_db']
        self.collection = self.db['users']

    def add_user(self, user: User) -> User:
        if not isinstance(user, User):
            raise TypeError("Must be instance of User")
        self.collection.insert_one(user.to_dict())
        return self.get_user(user.tg_id)

    def get_user(self, tg_id: str, mute=False) -> User:
        query = self.collection.find_one({"tg_id": tg_id})
        if query is None:
            if mute:
                return None
            raise ValueError("User not found")
        return User('').from_dict(query)

    def get_user_by_todo_id(self, todo_id: str, mute=False) -> User:
        query = self.collection.find_one({"todo_id": todo_id})
        if query is None:
            if mute:
                return None
            raise ValueError("User not found")
        return User('').from_dict(query)

    def get_user_by_state(self, state: str, mute=False) -> User:
        query = self.collection.find_one({"state": state})
        if query is None:
            if mute:
                return None
            raise ValueError("User not found")
        return User('').from_dict(query)

    def update_user(self, tg_id: str, user: User) -> User:
        if not isinstance(user, User):
            raise TypeError("Must be instance of User")
        self.collection.update_one({"tg_id": tg_id}, {"$set": user.to_dict()})
        return self.get_user(tg_id)

    def delete_user(self, tg_id) -> bool:
        return self.collection.delete_one({"tg_id": tg_id}).deleted_count > 0

    def save(self, user: User) -> User:
        # check if instance of User
        if not isinstance(user, User):
            raise TypeError("Must be instance of User")
        user_query = self.get_user(user.tg_id, mute=True)
        if user_query is not None:
            return self.update_user(user.tg_id, user)
        else:
            print("User not found, creating new one")
            return self.add_user(user)
