import praw
import json
import logging
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
    
class postResponseWorkerThread(threading.Thread):
    def __init__ (self, instance, bleach, submission):
        threading.Thread.__init__(self, name = "responseWorker")
        self.instance = instance
        self.bleach = bleach
        self.submission = submission
        
    def run(self):
        template = "*beep* *boop*\n\nIt looks like you could use some eyebleach!\n\n[This Post](%s) from /u/%s in /r/%s might help\n\nI'm a bot and still learning please be gentle!\n\n^If ^you ^would ^like ^your ^subreddit ^removed ^or ^would ^like ^to ^make ^me ^better\n\n^please ^message ^/u/Irish_Jew"

        randNumber = random.randint(1,100)
        subNumber = 1
        for subs in self.bleach.hot(limit=100):
            if (subNumber == randNumber):
                link = subs.shortlink
                user = subs.author
                sub = subs.subreddit
                self.submission.reply(template %(link,user,sub))
                break
            subNumber += 1
        
        return 0
    
class submissionSearchWorkerThread(threading.Thread):
    def __init__ (self, instance, subreddits, bleach, keywords):
        threading.Thread.__init__(self, name = "submissionSearchWorker")
        self.instance = instance
        self.subreddits = subreddits
        self.bleach = bleach
        self.keywords = keywords
        
    def run(self):
        for submission in self.subreddits.stream.submissions():
            
            title = submission.title.lower()
            if not hasattr(submission, 'body'):
                body = None
            if ((submission.link_flair_text != None) and (submission.link_flair_text == "NSFL")):
                logging.debug("Starting response thread")
                responseWorker = postResponseWorkerThread(self.instance, self.bleach, submission)
                responseWorker.start()
            else:
                if(inText(title, self.keywords)):
                    logging.debug("Starting response thread")
                    responseWorker = postResponseWorkerThread(self.instance, self.bleach, submission)
                    responseWorker.start()
                     
                else:
                    if(body != None):
                        body = submission.body.lower()
                        if (inText(body, self.keywords)):
                            logging.debug("Starting response thread")
                            responseWorker = postResponseWorkerThread(self.instance, self.bleach, submission)
                            responseWorker.start()
                
class commentSearchWorkerThread(threading.Thread):
    def __init__ (self, instance, subreddits, bleach, keywords):
        threading.Thread.__init__(self, name = "commentSearchWorker")
        self.instance = instance
        self.subreddits = subreddits
        self.bleach = bleach
        self.keywords = keywords
        
    def run(self):
        for comment in self.subreddits.stream.comments():
            normalized = comment.body.lower()
            
            if(inText(normalized, self.keywords)):
                logging.debug("Starting response thread")
                responseWorker = postResponseWorkerThread(self.instance, self.bleach, comment)
                responseWorker.start()
    
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
    subreddits = reddit.subreddit('IrishJewTesting')

    # getting the cute subreddits
    bleach = reddit.multireddit(reddit.user.me(), 'eyebleach')

    #keywords to search through in submissions
    keywords = ['i need some eyebleach', 'eyebleach please', 'nsfw/l', 'nsfl']
    
    subSearchWorker = submissionSearchWorkerThread(reddit, subreddits, bleach, keywords)
    comSearchWorker = commentSearchWorkerThread(reddit, subreddits, bleach, keywords)
    
    subSearchWorker.start()
    comSearchWorker.start()
        
    

if __name__ == "__main__":
    main()


