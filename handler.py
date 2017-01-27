import boto3
import os
import time
import urllib
from collections import defaultdict
from functools import wraps
from slacker import Slacker

with open(os.path.join(os.path.dirname(__file__), 'SLACK_BOT_API_TOKEN')) as f:
    bot_api_token = f.read().strip()

slack = Slacker(bot_api_token)

def
slack.chat.post_message(channel="#test", text="hello world", as_user=True)
