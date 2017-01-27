'''
This function handles a Slack slash command and echoes the details back to the user.

Follow these steps to configure the slash command in Slack:

  1. Navigate to https://<your-team-domain>.slack.com/services/new

  2. Search for and select "Slash Commands".

  3. Enter a name for your command and click "Add Slash Command Integration".

  4. Copy the token string from the integration settings and use it in the next section.

  5. After you complete this blueprint, enter the provided API endpoint URL in the URL field.


To encrypt your secrets use the following steps:

  1. Create or use an existing KMS Key - http://docs.aws.amazon.com/kms/latest/developerguide/create-keys.html

  2. Click the "Enable Encryption Helpers" checkbox

  3. Paste <COMMAND_TOKEN> into the kmsEncryptedToken environment variable and click encrypt


Follow these steps to complete the configuration of your command API endpoint

  1. When completing the blueprint configuration select "Open" for security
     on the "Configure triggers" page.

  2. Enter a name for your execution role in the "Role name" field.
     Your function's execution role needs kms:Decrypt permissions. We have
     pre-selected the "KMS decryption permissions" policy template that will
     automatically add these permissions.

  3. Update the URL for your Slack slash command with the invocation URL for the
     created API resource in the prod stage.
'''

import boto3
import json
import logging
import os
import time

from base64 import b64decode
from urlparse import parse_qs

from slacker import Slacker
import requests
import datetime


ENCRYPTED_EXPECTED_TOKEN = os.environ['kmsEncryptedToken']

kms = boto3.client('kms')
expected_token = kms.decrypt(CiphertextBlob=b64decode(ENCRYPTED_EXPECTED_TOKEN))['Plaintext']

logger = logging.getLogger()
logger.setLevel(logging.INFO)

with open(os.path.join(os.path.dirname(__file__), 'SLACK_BOT_API_TOKEN')) as f:
    bot_api_token = f.read().strip()

with open(os.path.join(os.path.dirname(__file__), 'PAGERDUTY_API_KEY')) as f:
    pagerduty_api_token = f.read().strip()

slack = Slacker(bot_api_token)


def next_weekday(d, weekday):
    days_ahead = weekday - d.weekday()
    if days_ahead <= 0: # Target day already happened this week
        days_ahead += 7
    return d + datetime.timedelta(days_ahead)

def status(src):
  r = requests.get(src)
  return "Status for " + str(src) + ": " + str(r.status_code)


def on_call():
  #returns pager
  today = datetime.datetime.today()
  next_monday = next_weekday(today, 0) # 0 = Monday, 1=Tuesday, 2=Wednesday...

  day_filter = "since="+str(today)+"&"+"until="+str(next_monday)

  team_id = "PRM9TER"
  headers = {
              "Accept": "application/vnd.pagerduty+json;version=2",
              "Authorization": "Token token="+pagerduty_api_token
            }
  url = "https://api.pagerduty.com/schedules/"+team_id+"/users?"+day_filter

  r = requests.get(url, headers=headers)
  on = json.loads(r.text)

  users = on['users'][0]['name']

  return "On-Call: " + users + " for AM until " + str(next_monday.strftime("%A, %B %d, %Y.") + " :phone:")




def parse_command(command_text):
  split_command = command_text.split()
  if split_command[0] == "on-call":
    #on_call on-call
    return on_call()
  elif split_command[0] == "status":
    try:
      src = split_command[1]
      return status(src)
    except IndexError:
      return "That's not a valid source: " + src
  else:
    return "I don't recognize that command. Try /media [ on-call | status ]"



def slack_it(channel, text):
  slack.chat.post_message(channel=channel, text=text, as_user=True)
  #return {"response_type": "in_channel"}
  return {"body": "I got your message."}


def respond(err, res=None):
        return {
    'statusCode': '400' if err else '200',
        'body': err.message if err else json.dumps(res),
        'headers': {
            'Content-Type': 'application/json',
        },
    }


def lambda_handler(event, context):
    params = parse_qs(event['body'])
    token = params['token'][0]
    if token != expected_token:
        logger.error("Request token (%s) does not match expected", token)
        return respond(Exception('Invalid request token'))

    user = params['user_name'][0]
    command = params['command'][0]
    channel = params['channel_name'][0]
    command_text = params['text'][0]

    output = parse_command(command_text)

    return slack_it(channel, output)
