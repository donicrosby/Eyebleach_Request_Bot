# Eyebleach_Request_Bot
This is a reddit bot that looks for NSFL (Not Safe for Life) posts and other posts that might have disturbing content and returns Eyebleach, cute or nice pictures that can be used to bleach your eyes from looking at said disturbing content. Currently uses a private multireddit to get the bleach data (although that may change).

# Features
* Mutlithreaded (Not really that special)
  - Allows for both the comments and the submissions to be searched at once.
  - All replies have their own thread created to do all the work so the main threads can continue.

* Automatic Subreddit Removal
  - A mail monitor thread looks through the inbox looking for a specific subject line, then removes those subreddits
  - All subreddit removals must come from a Moderator of that subreddit to be valid

* Automatic Mail Forwarding
  - Mail montior also forwards all private messages to a user so that they may act appon it accordingly

* Refresh Timers
  - If there is an unexpected error and a thread goes down it will be restored on a regular interval
  - And removed subreddits that are found are updated with each refresh cycle.
