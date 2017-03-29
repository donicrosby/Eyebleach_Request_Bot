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

reddit = praw.Reddit(client_id = bot_client_id,
                       client_secret = bot_client_secret,
                       password = bot_password,
                       user_agent = bot_user_agent,
                       username = "EyebleachRequest_Bot")

print "If this name:", reddit.user.me(), "is equal to the bot's username then the authentication was successful"

# Retreving subreddits for the bot to use
subreddits = reddit.subreddit('IrishJewTesting')

# getting the cute subreddits
aww = reddit.subreddit('aww')

for submission in subreddits.hot(limit = 5):
    

