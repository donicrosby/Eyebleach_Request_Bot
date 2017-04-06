import praw
import json
import logging
import time
import random
import threading

logging.basicConfig(level=logging.DEBUG,
                    format='[%(levelname)s] (%(threadName)-10s) %(message)s',
                    )

def inText(text, keywords):
    for word in keywords:
        if word in text:
            return True
    return False

def commentSearch(instance, subreddits, bleach, keywords):
    for comment in subreddits.stream.comments():
        normalized = comment.body.lower()
        
        if(inText(normalized, keywords)):
            try:
                _thread.start_new_thread(postResponce, (reddit,bleach,comment))
                
            except(praw.exceptions.ClientExceptions):
                logging.debug("ClientExeption")

            except(praw.exceptions.APIException):
                logging.debug("APIExeption")
        
            except(praw.exceptions.PRAWExceptions):
                logging.debug("PRAWExeption")

            finally:
                logging.debug("Responce Finsished")
            
def submissionSearch(instance, subreddits, bleach, keywords):
    for submission in subreddits.stream.submissions():
        title = submission.title.lower()
        body = submission.body.lower()
        
        if (submission.link_flair_text.upper() == "NSFL"):
            try:
                _thread.start_new_thread(postResponce, (reddit,bleach,submission))
            except(praw.exceptions.ClientExceptions):
                logging.debug("ClientExeption")

            except(praw.exceptions.APIException):
                logging.debug("APIExeption")
        
            except(praw.exceptions.PRAWExceptions):
                logging.debug("PRAWExeption")
            finally:
                logging.debug("Responce Finsished")
            
        elif(inText(title, keywords)):
            try:
                _thread.start_new_thread(postResponce, (reddit,bleach,submission))
            finally:
                logging.debug("Responce Finsished")
             
        elif(inText(body, keywords)):
            try:
                _thread.start_new_thread(postResponce, (reddit,bleach,submission))
            finally:
                logging.debug("Responce Finsished")
        
def postResponce(instance, bleach, submission):
    template = "*beep* *boop*\n\nIt looks like you could use some eyebleach!\n\n[This Post](%s) from /u/%s in /r/%s might help\n\nI'm a bot and still learning please be gentle!\n\n^If ^you ^would ^like ^your ^subreddit ^removed ^or ^would ^like ^to ^make ^me ^better\n\n^please ^message ^/u/Irish_Jew"

    randNumber = random.randint(1,100)
    subNumber = 1
    for subs in bleach.hot(limit=100):
        if (subNumber == randNumber):
            link = subs.shortlink
            user = subs.author
            sub = subs.subreddit
            break
    submission.reply(template %(link,user,sub))
    logging.debug("Posting Response")
    _thread.exit()
    
class submissionSearchWorkerThread(threading.Thread):
    def __init__ (self, instance, subreddits, bleach, keywords)
    
def main():
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

    logging.debug( "If this name: %s is equal to the bot's username then the authentication was successful", reddit.user.me())

    # Retreving subreddits for the bot to use
    subreddits = reddit.subreddit('testingground4bots')

    # getting the cute subreddits
    bleach = reddit.multireddit(reddit.user.me(), 'eyebleach')

    #keywords to search through in submissions
    keywords = ['i need some eyebleach', 'eyebleach please', 'nsfw/l', 'nsfl']
        
    

if __name__ == "__main__":
    main()


