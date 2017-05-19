import praw
from praw.models import Message
import json
import logging
import random
import threading
import time
import datetime
import re

debugName = ("debug/info%s.log" %(datetime.datetime.isoformat(datetime.datetime.now())))

logging.basicConfig(filename= debugName, filemode='w',level=logging.INFO,
                    format='%(asctime)s [%(levelname)s] (%(threadName)-10s) %(message)s',
                    )

# flags to signal the program to end

shutdownLock = threading.Lock()
banLock = threading.Lock()
ENDNOW = False
MAILSTOP = False
BANSTOP = False
SCANSTOP = False

def inText(text, keywords):
    re.IGNORECASE
    linkEx = "((http(s)?:\/\/.)?(www\.)?[-a-zA-Z0-9@:%._\+~#=]{2,256}\.[a-z]{2,6}\b([-a-zA-Z0-9@:%_\+.~#?&//=]*)"
    re.sub(linkEx, "LINK", text)
    matches = re.search(keywords, text)
    if(matches != None):
        return True
    return False
    
class postResponseWorkerThread(threading.Thread):
    def __init__ (self, instance, bleach, submission):
        threading.Thread.__init__(self, name = "responseWorker")
        self.instance = instance
        self.bleach = bleach
        self.submission = submission
        
    def run(self):
        # Add this when the other thread is going
        #  ^^| [^^Opt-out](https://www.reddit.com/r/EyebleachRequestBot/comments/6c1fn7/blacklist/)
        template = "It looks like you could use some eyebleach!\n\n[This Post](%s) in /r/%s might help\n\n----\n^^*Beep* ^^*boop* ^^I'm ^^a ^^bot, ^^please ^^be ^^gentle ^^| [^^Send ^^me ^^a ^^pm](https://www.reddit.com/message/compose/?to=EyebleachRequest_Bot) ^^| [^^About](https://np.reddit.com/r/eyebleachrequestbot/)"
        randNumber = random.randint(1,100)
        subNumber = 1
        for post in self.bleach.hot(limit=100):
            if (subNumber == randNumber):
                link = self.noParticipationLink(post)
                #user = post.author
                sub = post.subreddit
                self.submission.reply(template %(link,sub))
                break
            subNumber += 1
        
        return 0
    
    def noParticipationLink(self, submission):
        linkid = submission.id_from_url(submission.shortlink)
        npLink = ("np.reddit.com/%s" % (linkid))
        return npLink
    
class submissionSearchWorkerThread(threading.Thread):
    def __init__ (self, instance, subreddits, bleach, keywords):
        threading.Thread.__init__(self, name = "submissionSearchWorker")
        self.instance = instance
        self.subreddits = subreddits
        self.bleach = bleach
        self.keywords = keywords
        
    def run(self):
        logging.info("Submission Search Thread Starting")
        for submission in self.subreddits.stream.submissions():
            with shutdownLock:
                global ENDNOW, SCANSTOP
                if(ENDNOW or SCANSTOP):
                    logging.info("Submission Search Thread Returning")
                    return 0
            title = submission.title.lower()
            
            if not hasattr(submission, 'body'):
                body = None
            if((not self.haveIResponded(self.instance, submission)) and (not self.tooManyResponses(self.instance, submission, 3)) and (not self.isRestricted(self.instance, submission))):
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
    
    def isRestricted(self, instance, submission):
        if(submission.subreddit.subreddit_type == 'restricted'):
            logging.info("Subreddit %s, is restrictited ignoring" % (submission.subreddit))
            return True
        else:
            return False    
                
class commentSearchWorkerThread(threading.Thread):
    def __init__ (self, instance, subreddits, bleach, keywords):
        threading.Thread.__init__(self, name = "commentSearchWorker")
        self.instance = instance
        self.subreddits = subreddits
        self.bleach = bleach
        self.keywords = keywords
        
    def run(self):
        logging.info("Comment Search Thread Starting")
        for comment in self.subreddits.stream.comments():
            with shutdownLock:
                global ENDNOW, SCANSTOP
                if(ENDNOW or SCANSTOP):
                    logging.info("Comment Search Thread Returning")
                    return 0
                
            normalized = comment.body.lower()
            
            if(inText(normalized, self.keywords)):
                if((not (self.haveIResponded(self.instance, comment))) and (not self.tooManyResponses(self.instance, comment, 3)) and (not self.isAutoMod(self.instance, comment)) and (not self.isRestricted(self.instance, comment))):
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
    
    def isAutoMod(self, instance, comment):
        if(comment.author == 'AutoModerator'):
            logging.info("User is AutoModerator not replying")
            return True
        else:
            return False
        
    def isRestricted(self, instance, comment):
        if(comment.subreddit.subreddit_type == 'restricted'):
            logging.info("Subreddit %s, is restrictited ignoring" % (comment.subreddit))
            return True
        else:
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
                        
                    elif((message.author == None) and (self.isBan(message))):
                        sublist.write("%s\n" %(message.subreddit))
                        print("Banned from %s, restarting" % (message.subreddit))
                        logging.info("Banned from %s, Restarting" % (message.subreddit))
                        with banLock:
                            global BANSTOP
                            BANSTOP = True
                        message.mark_read()
                        
                    else:
                        logging.info("Forwarding Message from %s" % (message.author))
                        botsubject = ("EyeBleachBot Message: From-/u/%s Subj-%s" % (message.author, message.subject))
                        self.instance.redditor("Irish_Jew").message(botsubject, message.body)
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
    
    def isBan(self, message):
        sub = message.subreddit
        banmessage = ("You\'ve been banned from participating in r/%s" % (sub))
        if(message.subject.lower() == banmessage.lower()):
            return True
        else:
            return False
                
def refreshSubs(instance):
    basicSubs = ['all']
    minus = '-'
    
    # getting the cute subreddits
    filtered = open('filtersubreddits.txt', 'r')
    bleach = instance.multireddit(instance.user.me(), 'eyebleach')
    for line in filtered:
        sub = line.rstrip('\n')
        bleach.remove(line)
        basicSubs.append(sub)
    
    finalSubs = minus.join(basicSubs)
    print(finalSubs)
    filtered.close()
    return finalSubs, bleach
    
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
        
    finalSubs, bleach = refreshSubs(reddit)
    # Retreving subreddits for the bot to use
    subreddits = reddit.subreddit(finalSubs)
    
    #keywords to search through in submissions
    keywords = ['\bi need some eyebleach', '\beyebleach please', '\bnsfw/l', '\bnsfl']
    
    global MAILSTOP
    global ENDNOW
    global BANSTOP
    global SCANSTOP
    
    
    subSearchWorker = submissionSearchWorkerThread(reddit, subreddits, bleach, keywords)
    comSearchWorker = commentSearchWorkerThread(reddit, subreddits, bleach, keywords)
    mailMonitor = mailMonitorWorkerThread(reddit, subreddits)
    
    logging.info("Starting Bot at %s", time.asctime())
    subSearchWorker.start()
    comSearchWorker.start()
    mailMonitor.start()
    
    mailStart = time.time()
    mailEnd = mailStart + 900
    
    refreshStart = time.time()
    refreshEnd = refreshStart + 1800
    
    while(1):
        if(time.time() >= mailEnd):
            with shutdownLock:
                MAILSTOP = True
            while(mailMonitor.is_alive()):
                mailMonitor.join(1)
    
            if(MAILSTOP):
                MAILSTOP = False
                
            logging.info("Restarting Mail Monitor Thread")
            mailStart = mailEnd
            mailEnd = mailStart + 900
            
            mailMonitor = mailMonitorWorkerThread(reddit, subreddits)
            mailMonitor.start()
            
        if(time.time() >= refreshEnd):
            with shutdownLock:
                ENDNOW = True
                logging.info("Shutting Down Submission and Comment Threads")
            
            #waiting for threads to terminate
            while(subSearchWorker.is_alive()):
                subSearchWorker.join(1)
            while(comSearchWorker.is_alive()):
                comSearchWorker.join(1)
                
            finalSubs, bleach = refreshSubs(reddit)
            # Retreving subreddits for the bot to use
            subreddits = reddit.subreddit(finalSubs)
            
            subSearchWorker = submissionSearchWorkerThread(reddit, subreddits, bleach, keywords)
            comSearchWorker = commentSearchWorkerThread(reddit, subreddits, bleach, keywords)
            
            refreshStart = refreshEnd
            refreshEnd = refreshStart + 1800
            
            if(ENDNOW):
                ENDNOW = False
            
            logging.info("Restarting Submission and Comment Threads")
            subSearchWorker.start()
            comSearchWorker.start()
            
        with banLock:       
            if(BANSTOP):
                banStopTime = time.time()
                banEndTime = banStopTime + 30
                with shutdownLock:
                    SCANSTOP = True
                    
                while(subSearchWorker.is_alive()):
                    subSearchWorker.join(1)
                while(comSearchWorker.is_alive()):
                    comSearchWorker.join(1)
                
                BANSTOP = False
                SCANSTOP = False
                
                while(time.time() < banEndTime):
                    pass
                
                finalSubs, bleach = refreshSubs(reddit)
                # Retreving subreddits for the bot to use
                subreddits = reddit.subreddit(finalSubs)
                
                subSearchWorker = submissionSearchWorkerThread(reddit, subreddits, bleach, keywords)
                comSearchWorker = commentSearchWorkerThread(reddit, subreddits, bleach, keywords)
                
                logging.info("Restarting Submission and Comment Threads after ban")
                subSearchWorker.start()
                comSearchWorker.start()
            
    print("Returning")
    return 0

if __name__ == "__main__":
    main()


