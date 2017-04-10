import praw
from praw.models import Message
import json
import logging
import random
import threading
import time
import datetime

debugName = ("debug/info%s.log" %(datetime.datetime.isoformat(datetime.datetime.now())))

logging.basicConfig(filename= debugName, filemode='w',level=logging.INFO,
                    format='%(asctime)s [%(levelname)s] (%(threadName)-10s) %(message)s',
                    )

# flags to signal the program to end

ENDNOW = False
shutdownLock = threading.Lock()
MAILSTOP = False

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
        template = "*beep* *boop*\n\nIt looks like you could use some eyebleach!\n\n[This Post](%s) from /u/%s in /r/%s might help\n\nI'm a bot and still learning please be gentle!\n\n^If ^you ^are ^a ^moderator ^and ^would ^like ^your ^subreddit ^removed ^send \n\n^me ^a ^pm ^with ^subject ^Remove ^Subreddit ^and ^the ^subs ^you ^want ^removed\n\n^if ^you ^would ^like ^to ^make ^me ^better\n\n^please ^message ^me ^with ^your ^suggestions"

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
            with shutdownLock:
                global ENDNOW
                if(ENDNOW):
                    return 0
            title = submission.title.lower()
            
            if not hasattr(submission, 'body'):
                body = None
            if((not self.haveIResponded(self.instance, submission)) and (not self.tooManyResponses(self.instance, submission, 3))):
                if ((submission.link_flair_text != None) and (submission.link_flair_text == "NSFL")):
                    logging.info("Starting response thread")
                    responseWorker = postResponseWorkerThread(self.instance, self.bleach, submission)
                    responseWorker.start()
                else:
                    if(inText(title, self.keywords)):
                        logging.info("Starting response thread")
                        responseWorker = postResponseWorkerThread(self.instance, self.bleach, submission)
                        responseWorker.start()
                         
                    else:
                        if(body != None):
                            body = submission.body.lower()
                            if (inText(body, self.keywords)):
                                logging.info("Starting response thread")
                                responseWorker = postResponseWorkerThread(self.instance, self.bleach, submission)
                                responseWorker.start()
                            
    def haveIResponded(self, instance, submission):
        submission.comments.replace_more(limit=0)
        for reply in submission.comments.list():
            if(reply.author == instance.user.me()):
                return True
            elif(reply.parent() != submission):
                return False
            
    def tooManyResponses(self,instance, submission, limit):
        submission.comments.replace_more(limit=0)
        responses = 0
        for reply in submission.comments.list():
            if(responses >= limit):
                return True
            else:
                if(reply.author == instance.user.me()):
                    responses += 1
        return False    
                
class commentSearchWorkerThread(threading.Thread):
    def __init__ (self, instance, subreddits, bleach, keywords):
        threading.Thread.__init__(self, name = "commentSearchWorker")
        self.instance = instance
        self.subreddits = subreddits
        self.bleach = bleach
        self.keywords = keywords
        
    def run(self):
        for comment in self.subreddits.stream.comments():
            with shutdownLock:
                global ENDNOW
                if(ENDNOW):
                    return 0
            
            normalized = comment.body.lower()
            
            if(inText(normalized, self.keywords)):
                if((not (self.haveIResponded(self.instance, comment))) and (not self.tooManyResponses(self.instance, comment, 3))):
                    logging.info("Starting response thread")
                    responseWorker = postResponseWorkerThread(self.instance, self.bleach, comment)
                    responseWorker.start()
    
    def haveIResponded(self, instance, comment):
        comment.refresh()
        comment.replies.replace_more(limit=0)
        for reply in comment.replies.list():
            if(reply.author == instance.user.me()):
                return True
            elif(reply.parent() != comment):
                return False
            
    def tooManyResponses(self,instance, comment, limit):
        comment.refresh()
        parent = comment.parent()
        if (parent != comment.submission):
            parent.refresh()
            parent.replies.replace_more(limit=0)
            responses = 0
            for reply in parent.replies.list():
                if(responses >= limit):
                    return True
                else:
                    if(reply.author == instance.user.me()):
                        responses += 1
        else:
            parent.comments.replace_more(limit=0)
            responses = 0
            for reply in parent.comments.list():
                if(responses >= limit):
                    return True
                else:
                    if(reply.author == instance.user.me()):
                        responses += 1         
        return False
    
class mailMonitorWorkerThread(threading.Thread):
    def __init__ (self, instance, subreddits):
        threading.Thread.__init__(self, name = "mailMonitorWorker")
        self.instance = instance
        self.subreddits = subreddits
        
    def run(self):
        with open('filtersubreddits.txt', 'a') as sublist:
            for message in self.instance.inbox.unread(limit = None):
                if(isinstance(message, Message)):
                    normalized = message.subject.lower()
                    if(normalized == 'remove subreddit'):
                        author = message.author
                        toremove = message.body.splitlines()
                        for sub in toremove:
                            if (sub == '\n'):
                                continue
                            sub = sub.replace("/r/", "")
                            sub = sub.replace("r/", "")
                            try:
                                r = self.instance.subreddit(sub).subreddit_type
                                logging.info("The subreddit %s, is a %s subreddit" % (sub, r))
                            except:
                                logging.info("The subreddit %s, is a private subreddit" % (sub))
                                continue
                            
                            if(self.isMod(self.instance, author, sub)):
                                sublist.write("%s\n" %(sub))
                                message.mark_read()
                            else:
                                message.mark_read()
                else:
                    message.mark_read()
                    
                with shutdownLock:
                    global ENDNOW
                    if(ENDNOW or MAILSTOP):
                        break
                
        return 0
                
    def isMod(self,instance, user, sub):
        for mod in instance.subreddit(sub).moderator():
            if(mod == user):
                return True
        return False
                

    
def main():
    # Opening the keys json file to read in sensitive script data
    with open('keys/keys.json') as key_data:
        keys = json.load(key_data)
    
    filtered = open('filtersubreddits.txt', 'r')

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

    basicSubs = ['all']
    minus = '-'
    
    # getting the cute subreddits
    bleach = reddit.multireddit(reddit.user.me(), 'eyebleach')
    for line in filtered:
        sub = line.rstrip('\n')
        bleach.remove(line)
        basicSubs.append(sub)
    
    finalSubs = minus.join(basicSubs)
    print(finalSubs)
    filtered.close()
        
        
    # Retreving subreddits for the bot to use
    subreddits = reddit.subreddit(finalSubs)
    
    #keywords to search through in submissions
    keywords = ['i need some eyebleach', 'eyebleach please', 'nsfw/l', 'nsfl']
    
    #start = time.time()
    #end = start + 10 # making end time 30 seconds infront of start
    subSearchWorker = submissionSearchWorkerThread(reddit, subreddits, bleach, keywords)
    comSearchWorker = commentSearchWorkerThread(reddit, subreddits, bleach, keywords)
    mailMonitor = mailMonitorWorkerThread(reddit, subreddits)
    
    logging.info("Starting Bot at %s", time.asctime())
    subSearchWorker.start()
    comSearchWorker.start()
    mailMonitor.start()
    
    mailStart = time.time()
    mailEnd = mailStart + 900
    
    while(1):
        if(time.time() >= mailEnd):
            with shutdownLock:
                global MAILSTOP
                MAILSTOP = True
            while(mailMonitor.is_alive()):
                mailMonitor.join(1)
            mailStart = mailEnd  
            mailEnd = mailStart + 900
            logging.info("Restarting Mail Monitor Thread")
            mailMonitor = mailMonitorWorkerThread(reddit, subreddits)
            mailMonitor.start()
#         if(time.time() >= end):
#             with shutdownLock:
#                 global ENDNOW
#                 ENDNOW = True
#             print("%r" % (ENDNOW))
#             print("Ending")
#             while(subSearchWorker.is_alive()):
#                 subSearchWorker.join(1)
#             while(comSearchWorker.is_alive()):
#                 comSearchWorker.join(1)
#             mailMonitor.join(10)
    print("Returning")
    return 0

if __name__ == "__main__":
    main()


