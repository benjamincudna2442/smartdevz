from typing import Dict, List
from flask import Flask, request, jsonify
from pyrogram import Client
from pyrogram.errors import FloodWait, RPCError
from uuid import uuid4
import time
import os

# Flask app setup
app = Flask(__name__)

# Data models
class BotInfo:
    def __init__(self, first_name: str, id: int, username: str):
        self.first_name = first_name
        self.id = id
        self.username = username

class Chat:
    def __init__(self, id: int, members_count: int | None, title: str, type: str, username: str | None):
        self.id = id
        self.members_count = members_count
        self.title = title
        self.type = type
        self.username = username

class User:
    def __init__(self, id: int, first_name: str | None, last_name: str | None, username: str | None, is_premium: bool):
        self.id = id
        self.first_name = first_name
        self.last_name = last_name
        self.username = username
        self.is_premium = is_premium

class BotDataResponse:
    def __init__(self, bot_info: BotInfo, chats: List[Chat], users: List[User]):
        self.bot_info = bot_info
        self.chats = chats
        self.users = users

    def to_dict(self) -> Dict:
        return {
            "bot_info": {
                "first_name": self.bot_info.first_name,
                "id": self.bot_info.id,
                "username": self.bot_info.username
            },
            "chats": [
                {
                    "id": chat.id,
                    "members_count": chat.members_count,
                    "title": chat.title,
                    "type": chat.type,
                    "username": chat.username
                } for chat in self.chats
            ],
            "users": [
                {
                    "id": user.id,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "username": user.username,
                    "is_premium": user.is_premium
                } for user in self.users
            ]
        }

# Helper function to initialize Pyrogram client
def create_client(bot_token: str, api_id: int, api_hash: str) -> Client:
    try:
        session_name = f"bot_{uuid4().hex}"
        client = Client(
            name=session_name,
            bot_token=bot_token,
            api_id=api_id,
            api_hash=api_hash,
            in_memory=True
        )
        client.start()
        return client
    except Exception as e:
        raise Exception(f"Failed to initialize client: {str(e)}")

# Helper function to normalize chat type
def normalize_chat_type(raw_type: str) -> str:
    type_map = {
        "private": "private",
        "group": "group",
        "supergroup": "supergroup",
        "channel": "channel"
    }
    return type_map.get(raw_type.lower(), "unknown")

# Helper function to get chats and users
def get_chats_and_users(client: Client) -> tuple[List[Chat], List[User]]:
    chats: Dict[int, Chat] = {}
    users: Dict[int, User] = {}

    try:
        # Fetch chats using get_chats
        for dialog in client.get_dialogs():
            chat = dialog.chat
            if hasattr(chat, "id") and chat.id not in chats:
                chat_type = normalize_chat_type(chat.type.name if hasattr(chat, "type") else "unknown")
                chats[chat.id] = Chat(
                    id=chat.id,
                    members_count=chat.members_count if hasattr(chat, "members_count") else None,
                    title=chat.title or chat.first_name or "Unknown",
                    type=chat_type,
                    username=chat.username if hasattr(chat, "username") else None
                )

                # Fetch users from chat (if applicable)
                if chat_type in ["group", "supergroup", "channel"]:
                    try:
                        for member in client.get_chat_members(chat.id):
                            user = member.user
                            if user and user.id not in users:
                                users[user.id] = User(
                                    id=user.id,
                                    first_name=user.first_name,
                                    last_name=user.last_name,
                                    username=user.username,
                                    is_premium=user.is_premium if hasattr(user, "is_premium") else False
                                )
                    except (FloodWait, RPCError):
                        continue  # Skip inaccessible chats

    except FloodWait as fw:
        time.sleep(fw.value)
        return get_chats_and_users(client)
    except Exception as e:
        raise Exception(f"Error fetching chats and users: {str(e)}")

    return list(chats.values()), list(users.values())

# API endpoint for root/info
@app.route('/', methods=['GET'])
def get_api_info():
    return jsonify({
        "api_name": "Telegram Users API",
        "version": "1.0.0",
        "description": "API for retrieving Telegram bot data including chats and users",
        "owners": [
            {"username": "@ISmartCoder"},
            {"username": "@theSmartDev"}
        ],
        "endpoints": [
            {
                "path": "/tgusers",
                "method": "GET",
                "description": "Fetch bot data including bot info, chats, and users",
                "parameters": [
                    {
                        "name": "token",
                        "type": "string",
                        "required": True,
                        "description": "Telegram Bot Token"
                    }
                ]
            },
            {
                "path": "/docs",
                "method": "GET",
                "description": "Get API documentation and basic tutorial",
                "parameters": []
            }
        ],
        "contact": "Contact @ISmartCoder or @theSmartDev for support"
    })

# API endpoint for documentation
@app.route('/docs', methods=['GET'])
def get_docs():
    return jsonify({
        "title": "Telegram Users API Tutorial",
        "version": "1.0.0",
        "overview": "This API allows you to retrieve information about a Telegram bot's chats and users using a valid bot token.",
        "getting_started": {
            "step_1": {
                "title": "Obtain a Bot Token",
                "description": "Create a bot using @BotFather on Telegram to get a bot token."
            },
            "step_2": {
                "title": "Make a Request",
                "description": "Use the /tgusers endpoint with your bot token as a query parameter.",
                "example": "GET /tgusers?token=your_bot_token_here"
            },
            "step_3": {
                "title": "Handle Response",
                "description": "The API returns a JSON object containing bot_info, chats, and users."
            }
        },
        "example_request": {
            "curl": "curl -X GET 'http://your-api-domain/tgusers?token=your_bot_token_here'",
            "python": """
import requests

url = "http://your-api-domain/tgusers"
params = {"token": "your_bot_token_here"}
response = requests.get(url, params=params)
data = response.json()
print(data)
"""
        },
        "response_format": {
            "bot_info": {
                "first_name": "string",
                "id": "integer",
                "username": "string"
            },
            "chats": [
                {
                    "id": "integer",
                    "members_count": "integer or null",
                    "title": "string",
                    "type": "string",
                    "username": "string or null"
                }
            ],
            "users": [
                {
                    "id": "integer",
                    "first_name": "string or null",
                    "last_name": "string or null",
                    "username": "string or null",
                    "is_premium": "boolean"
                }
            ]
        },
        "notes": [
            "Ensure your bot token is kept secure",
            "Rate limits may apply due to Telegram API restrictions",
            "Contact @ISmartCoder or @theSmartDev for support"
        ]
    })

# API endpoint to fetch bot data
@app.route('/tgusers', methods=['GET'])
def get_bot_data():
    try:
        bot_token = request.args.get('token')
        if not bot_token:
            return jsonify({"error": "Bot token is required"}), 400

        # Use environment variables for sensitive data
        api_id = int(os.environ.get("API_ID", "26512884"))
        api_hash = os.environ.get("API_HASH", "c3f491cd59af263cfc249d3f93342ef8")

        client = create_client(bot_token, api_id, api_hash)
        me = client.get_me()
        bot_info = BotInfo(
            first_name=me.first_name,
            id=me.id,
            username=me.username
        )

        chats, users = get_chats_and_users(client)
        client.stop()

        response = BotDataResponse(
            bot_info=bot_info,
            chats=chats,
            users=users
        )
        return jsonify(response.to_dict())

    except RPCError as e:
        return jsonify({"error": f"Telegram API error: {str(e)}"}), 400
    except Exception as e:
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
