# Reddit Bot

## What does this bot do?
This script allows you to monitor a subreddit of your choice for all incoming comments.
If a comment meets your criteria (for example, it contains the username of your bot), you can scrape other information, reply to the comment, etc, then persist the interaction in a local sqlite DB.

## How to use this bot
The first thing you will need to do is create an application on reddit. This will fall under the purview of your reddit account, so you will need to sign up if you haven't already.
Create an application here: https://ssl.reddit.com/prefs/apps/
<br/>

Select the 'script' option. <br/> 
Set the redirect uri to http://127.0.0.1
Create the app and note down your client_id (top left), and your client_secret (labelled).
<br/>

Modify praw.ini and add a section like this at the bottom:
```
[bot1]
client_id=YourClientId
client_secret=YourClientSecret
password=YourRedditPassword
username=YourRedditUsername
user_agent=YourBotNamevx.x.x
```

Labelling this section [bot1] allows us to reference it using ``` self.reddit = praw.Reddit('bot1') ```<br/>
Name it whatever you like.

If your bot gets snapped by reddit for whatever reason, increment your user_agent.

This script uses a sqlite database to store metadata about captured comments - comments in the stream that meet your criteria. For example, any comment that contains the name of your bot in the comment body. <br/>
This allows you to avoid processing a comment more than once.
</br>
The script will not work without an sqlite db file in the script directory. I have included an empty one.



## Dev Notes
- If you have the DB open in sqlitebrowser the script won't be able to write to the DB.
- You can toggle the 'capture_text' flag to store the text of your replies in the DB alongside their comment id

## Credits
- Massive thanks to https://github.com/toddrob99/MLB-StatBot
