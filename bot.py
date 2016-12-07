import praw
import json

# Opening the keys json file to read in sensitive script data
with open('keys/keys.json') as key_data:
    keys = json.load(key_data)

# Assigning the bots secrets and client data
bot_user_agent = keys["user_agent"]
bot_client_id = keys["client_id"]
bot_client_secret = keys["client_secret"]
bot_password = keys["password"]

bot_info = praw.Reddit(client_id = bot_client_id,
                       client_secret = bot_client_secret,
                       password = bot_password,
                       user_agent = bot_user_agent,
                       username = "EyebleachRequest_Bot")

print(bot_info.user.me())
