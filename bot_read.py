# from pprint import pprint

import praw
import sqlite3
import os
import time
import datetime

import version
__version__ = version.VERSION

class Bot:
    def __init__(self):
        self.reddit = praw.Reddit('bot1') # bot1 maps to a section in praw.ini with the bot's credentials
        self.sub = "funny" # subreddit to monitor
        self.subreddit = self.reddit.subreddit(self.sub) # praw subreddit object
        self.replyFooter = '\n\n^^I ^^am ^^a ^^bot. ^^Keep ^^Your ^^Filthy ^^Meat ^^Husk ^^Away ^^From ^^Me.  ^^[[feedback](https://np.reddit.com/message/compose?to=th_dev_bot&subject=bot&message=)]'
        self.del_threshold = -2 # Number of downvotes before the comment is triggered for deletion
        self.pause_after = 5 # Number of seconds to wait before hitting the comment stream again
        self.comments = {} # dict to store processesed comments - syncs with DB
        self.historic_comment_limit = 500 # max number of comments to load from DB
        # phrase to summon the bot (underscores get escaped by reddit.) 
        # reddit user types: "th_dev_bot", script sees: "th\_dev\_bot"
        self.summon_phrase = "th\_dev\_bot" 

        print('Bot starting up...')
        print(f'Bot version: {__version__}')

        try:
            print('Connecting to DB...')
            """Local sqlite database to store info about processed comments"""
            self.db = sqlite3.connect(os.path.dirname(os.path.realpath(__file__)) + '/bot.db')
            #self.db.set_trace_callback(print)
            print("DB connection successful.")
        except sqlite3.Error as e:
            print(f'Error connecting to database: {e}')
            return None

        self.dbc = self.db.cursor()
        print("Creating comments table if it doesn't already exist.")
        self.dbc.execute('''CREATE TABLE IF NOT EXISTS comments (
                            comment_id text PRIMARY KEY,
                            sub text NOT NULL,
                            author text NOT NULL,
                            post text NOT NULL,
                            date text NOT NULL,
                            cmd text,
                            errors text,
                            reply text,
                            reply_text text,
                            removed integer,
                            score integer
                        );''')
        self.db.commit()


    def __del__(self):
        try:
            print('Closing DB connection.')
            self.db.close()
        except sqlite3.Error as e:
            print(f'Error closing database connection: {e}')


    def get_thread_comments(self, thread_url):
        """
        Get all comments in a thread.
        """
        print(f"Retrieving comments from {thread_url}")

        submission = self.reddit.submission(url=thread_url)
        # get rid of the 'show more comments' links in the tree and retrieve the actual comment data up to 'limit' times
        # limit 0 just removes them without getting the child comments
        # threshold determines how many child comments the sub-tree needs to have to be eligible for fetching
        # https://praw.readthedocs.io/en/stable/tutorials/comments.html
        submission.comments.replace_more(limit=3, threshold=0)

        # Calling .list() on submission.comments will return a breadth first queue of comments
        return submission.comments.list()


    def run(self, capture_text=False):
        print(f"Loading last (up to) {self.historic_comment_limit} comments from DB...")
        self.dbc.execute(f'SELECT comment_id,date,reply FROM comments ORDER BY date DESC LIMIT {self.historic_comment_limit};')
        comment_ids = self.dbc.fetchall()
        print(f"Loaded {len(comment_ids)} comments from DB.")

        for cid in comment_ids:
            self.comments.update({cid[0] : {'date' : cid[1], 'reply' : cid[2], 'historical' : True}})

        stream = self.subreddit.stream.comments(pause_after=self.pause_after)
        while True:
            print(f'Monitoring comments in the following subreddit: {self.sub}...')
            for comment in stream:
                if not comment:
                    break # opportunity to delete downvoted replies
                if comment.id in self.comments.keys():
                    print(f'Already processed comment {comment.id}')
                    continue
                
                # show attributes of the comment object
                # pprint(vars(comment))

                print(f'({comment.subreddit}) {comment.id} - {comment.author}: {comment.body} - {datetime.datetime.fromtimestamp(comment.created_utc)}')

                replyText = ''
                # detect comments summoning the bot
                # if self.summon_phrase in comment.body.lower() and comment.author != self.reddit.user.me():
                if self.summon_phrase in comment.body.lower():
                    print(f"I have been summoned by {comment.author}!")
                    self.comments.update({comment.id : {'sub' : comment.subreddit, 'author' : comment.author, 'post' : comment.submission, 'date' : time.time(), 'cmd' : [], 'errors' : []}})
                    # Comments only get added to the DB if they meet our selection criteria
                    self.dbc.execute("insert or ignore into comments (comment_id, sub, author, post, date) values (?, ?, ?, ?, ?);", (str(comment.id), str(comment.subreddit), str(comment.author), str(comment.submission), str(comment.created_utc)))
                    print(f'({comment.subreddit}) {comment.id} - {comment.author}: {comment.body}')
                    
                    self.comments[comment.id]['cmd'].append('default')
                    replyText += "Never summon me again, Peon.\n\n"

                    # Add options or flags for the commenters to use
                    if 'help' in comment.body.lower():
                        self.comments[comment.id]['cmd'].append('help')
                        replyText += f'Invoke me by including \"{self.summon_phrase}\" anywhere in your comment.\n\n'
                        replyText += f'I am currently monitoring the following subreddit: {self.sub}.' 

                    # # link_url is the parent thread, for example the string: "https://www.reddit.com/r/learnpython/comments/wcbewp/is_it_possible_to_hide_your_code_comments/"
                    # thread = comment.link_url
                    # # get all comments in the thread
                    # thread_comments = self.get_thread_comments(thread)
                    # # perform analysis on the comments
                    # # DoStuff(thread_comments) 
                    # # etc                   

                    if replyText != '':
                        try:
                            latest_reply = comment.reply(replyText + self.replyFooter)
                            self.comments[comment.id].update({'reply' : latest_reply})
                            latest_reply.disable_inbox_replies()
                            print(f'Replied with comment id {latest_reply} and disabled inbox replies.')
                            if capture_text:
                                # Persist the text content of your reply in the DB along with the comment id.
                                # Bad for the size of your DB, good for debugging 
                                self.dbc.execute("update comments set cmd=?,reply=?,reply_text=? where comment_id=?;", (str(self.comments[comment.id]['cmd']), str(latest_reply), replyText, str(comment.id)))
                            else:
                                self.dbc.execute("update comments set cmd=?,reply=? where comment_id=?;", (str(self.comments[comment.id]['cmd']), str(latest_reply), str(comment.id)))
                        except Exception as e:
                            print(f'Error replying to comment or disabling inbox replies: {e}')
                            self.comments[comment.id]['errors'].append(f'Error submitting comment or disabling inbox replies: {e}')

                    if len(self.comments[comment.id].get('errors')):
                        self.dbc.execute("update comments set errors=? where comment_id=?;", (str(self.comments[comment.id].get('errors')), str(comment.id)))
                    
                    self.db.commit()

            # Section to check for and delete downvoted comments
            # print('Checking for downvotes on {} replies...'.format(sum(1 for x in self.comments if self.comments[x].get('reply') and not self.comments[x].get('removed') and not self.comments[x].get('historical'))))
            # for x in (x for x in self.comments if self.comments[x].get('reply') and not self.comments[x].get('removed') and not self.comments[x].get('historical')):
            #     if self.comments[x]['reply'].score <= self.del_threshold:
            #         print('Deleting comment {} with score ({}) at or below threshold ({})...'.format(self.comments[x]['reply'], self.comments[x]['reply'].score, self.del_threshold))
            #         try:
            #             self.comments[x]['reply'].delete()
            #             self.comments[x].update({'removed':time.time()})
            #             self.dbc.execute("update comments set removed=? where comment_id=?;", (str(self.comments[x].get('removed')), str(x)))
            #         except Exception as e:
            #             print('Error deleting downvoted comment: {}'.format(e))
            #             self.comments[x]['errors'].append('Error deleting downvoted comment: {}'.format(e))
            # self.db.commit()

        return  


if __name__ == "__main__":
    bot = Bot()
    bot.run(capture_text=True)