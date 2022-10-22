import math
import dateutil.parser
import datetime
import time
import os
import logging
import boto3
import json
import re

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
SQS = boto3.client("sqs")

def getQueueURL():
    """Retrieve the URL for the configured queue name"""
    q = SQS.get_queue_url(QueueName='DiningSQS').get('QueueUrl')
    return q
    
def record(event):
    """The lambda handler"""
    logger.debug("Recording with event %s", event)
    data = event.get('data')
    try:
        logger.debug("Recording %s", data)
        u = getQueueURL()
        logging.debug("Got queue URL %s", u)
        resp = SQS.send_message(
            QueueUrl=u, 
            MessageBody="Dining Concierge message from LF1 ",
            MessageAttributes={
                "location": {
                    "StringValue": str(get_slots(event)["location"]),
                    "DataType": "String"
                },
                "cuisine": {
                    "StringValue": str(get_slots(event)["cuisine"]),
                    "DataType": "String"
                },
                "time" : {
                    "StringValue": str(get_slots(event)["time"]),
                    "DataType": "String"
                },
                "people" : {
                    "StringValue": str(get_slots(event)["people"]),
                    "DataType": "String"
                },
                "phone" : {
                    "StringValue": str(get_slots(event)["phone"]),
                    "DataType": "String"
                },
                "emailid" : {
                    "StringValue": str(get_slots(event)["emailid"]),
                    "DataType": "String"
                }
            }
        )
        logger.debug("Send result: %s", resp)
    except Exception as e:
        raise Exception("Could not record link! %s" % e)

def get_slots(intent_request):
    return intent_request['currentIntent']['slots']


def elicit_slot(session_attributes, intent_name, slots, slot_to_elicit, message):
    return {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'ElicitSlot',
            'intentName': intent_name,
            'slots': slots,
            'slotToElicit': slot_to_elicit,
            'message': message
        }
    }


def close(session_attributes, fulfillment_state, message):
    response = {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'Close',
            'fulfillmentState': fulfillment_state,
            'message': message
        }
    }

    return response


def delegate(session_attributes, slots):
    return {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'Delegate',
            'slots': slots
        }
    }


""" --- Helper Functions --- """

def parse_int(n):
    try:
        return int(n)
    except ValueError:
        return float('nan')

def build_validation_result(is_valid, violated_slot, message_content):
    if message_content is None:
        return {
            "isValid": is_valid,
            "violatedSlot": violated_slot,
            'message': {'contentType': 'PlainText', 'content': message_content}
        }

    return {
        'isValid': is_valid,
        'violatedSlot': violated_slot,
        'message': {'contentType': 'PlainText', 'content': message_content}
    }

def validate_dining_suggestion(location, cuisine, time, people, phone, emailid):
    locations = ['manhattan', 'new york', 'nyc', 'new york city', 'ny']
    if location is not None and location.lower() not in locations:
        print('location')
        return build_validation_result(False,
                                       'location',
                                       'We do not have suggestions for "{}", try a different city'.format(location))
                                       
    cuisines = ['chinese', 'indian', 'italian', 'japanese', 'mexican', 'thai', 'korean', 'arab', 'american']
    if cuisine is not None and cuisine.lower() not in cuisines:
        return build_validation_result(False,
                                       'cuisine',
                                       'We do not have suggestions for {}, would you like suggestions for a differenet cuisine ?'.format(cuisine))

    
    if time is not None:
        if len(time) != 5:
            # Not a valid time; use a prompt defined on the build-time model.
            return build_validation_result(False, 'time', None)

        hour, minute = time.split(':')
        hour = int(hour)
        minute = int(minute)
        if math.isnan(hour) or math.isnan(minute):
            # Not a valid time; use a prompt defined on the build-time model.
            return build_validation_result(False, 'time', None)

        if hour < 10 or hour > 23:
            # Outside of business hours
            return build_validation_result(False, 'time', 'Our business hours are from 10 AM. to 11 PM. Can you specify a time during this range?')
    
    if people is not None:
        people = int(people)
        if people < 1 or people > 15:
            return build_validation_result(False, 'people', 'Sorry! We accept reservations only upto 15 people')
    
    if phone is not None:
        if len(phone) != 10:
            return build_validation_result(False, 'phone', 'You have entered an invalid phone number. Please enter a valid 10 digit phone number.')  
    
    if emailid is not None:
        regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        if(not re.fullmatch(regex, emailid)):
            return build_validation_result(False, 'emailid', 'You have entered an invalid email id. Please enter a valid one for reservation.')
            
    return build_validation_result(True, None, None)

def sendMailToUser(resultData, emailid):

    SENDER = "namrathaupadhyaforaws@gmail.com"
    RECIPIENT = emailid
    AWS_REGION = "us-east-1"

    SUBJECT = "Your Dining recommendations"

    BODY_TEXT = ("AWS project in (Python)")

    # The HTML body of the email.
    BODY_HTML = """<html>
    <head></head>
    <body>
      <h1>Restaurant Suggestions</h1>
      <p>""" + resultData + """</p>
    </body>
    </html>
                """

    # The character encoding for the email.
    CHARSET = "UTF-8"

    # Create a new SES resource and specify a region.
    client = boto3.client('ses',region_name=AWS_REGION)

    # return true
    # Try to send the email.
    try:
        #Provide the contents of the email.
        response = client.send_email(
            Destination={
                'ToAddresses': [
                    RECIPIENT,
                ],
            },
            Message={
                'Body': {
                    'Html': {
                        'Charset': CHARSET,
                        'Data': BODY_HTML,
                    },
                    'Text': {
                        'Charset': CHARSET,
                        'Data': BODY_TEXT,
                    },
                },
                'Subject': {
                    # 'Charset': CHARSET,
                    'Data': SUBJECT,
                },
            },
            Source=SENDER,
            # # If you are not using a configuration set, comment or delete the
            # # following line
            # ConfigurationSetName=CONFIGURATION_SET,
        )
    # Display an error if something goes wrong.
    except ClientError as e:
        logger.debug(e.response['Error']['Message'])
    else:
        logger.debug("Email sent! Message ID:"),
        logger.debug(response['MessageId'])
        
def checkInDynamodb(intent_request):
    
    cuisine = str(get_slots(intent_request)["cuisine"])
    location = str(get_slots(intent_request)["location"])
    emailid = str(get_slots(intent_request)["emailid"])
    phone = str(get_slots(intent_request)["phone"])
    dynamodb = boto3.resource('dynamodb')
    usertable = dynamodb.Table('recommended-users')
    response = usertable.get_item(Key={'cuisine' : cuisine, 'location' : location})
    if 'Item' in response.keys():
        messageToSend = response['Item']['messagetosend']
        sendMailToUser(messageToSend, emailid)
        return close(intent_request['sessionAttributes'],
                 'Fulfilled',
                 {'contentType': 'PlainText',
                  'content': 'Hey you\'ve searched this before!! Sending you the same reccommendations!!'})
    else:    
        record(intent_request)
        return close(intent_request['sessionAttributes'],
                 'Fulfilled',
                 {'contentType': 'PlainText',
                  'content': 'Thank you for providing the information. Expect restaurant suggestions on your phone number {} shortly'.format(phone)})

""" --- Functions that control the bot's behavior --- """


def diningSuggestions(intent_request):
    
    location = get_slots(intent_request)["location"]
    cuisine = get_slots(intent_request)["cuisine"]
    time = get_slots(intent_request)["time"]
    people = get_slots(intent_request)["people"]
    phone = get_slots(intent_request)["phone"]
    emailid = get_slots(intent_request)["emailid"]
    
    source = intent_request['invocationSource']

    if source == 'DialogCodeHook':
        # Perform basic validation on the supplied input slots.
        # Use the elicitSlot dialog action to re-prompt for the first violation detected.
        slots = get_slots(intent_request)

        validation_result = validate_dining_suggestion(location, cuisine, time, people, phone, emailid)
        if not validation_result['isValid']:
            slots[validation_result['violatedSlot']] = None
            return elicit_slot(intent_request['sessionAttributes'],
                               intent_request['currentIntent']['name'],
                               slots,
                               validation_result['violatedSlot'],
                               validation_result['message'])

    
        output_session_attributes = intent_request['sessionAttributes'] if intent_request['sessionAttributes'] is not None else {}
        return delegate(output_session_attributes, get_slots(intent_request))
    
    return checkInDynamodb(intent_request)

""" --- Intents --- """

def welcome(intent_request):
    return {
        "dialogAction": {
            "type": "Close",
            "fulfillmentState": "Fulfilled",
            "message": {
                "contentType": "SSML",
                "content": "Hi There! How can I help ?"
            },
        }
    }

def thankYou(intent_request):
    return {
        "dialogAction": {
            "type": "Close",
            "fulfillmentState": "Fulfilled",
            "message": {
                "contentType": "SSML",
                "content": "Thank you and visit again!"
            },
        }
    }


def dispatch(intent_request):
    logger.debug('dispatch userId={}, intentName={}'.format(intent_request['userId'], intent_request['currentIntent']['name']))

    intent_name = intent_request['currentIntent']['name']

    # Dispatch to your bot's intent handlers
    if intent_name == 'DiningSuggestionsIntent':
        return diningSuggestions(intent_request)
    elif intent_name == 'ThankYouIntent':
        return thankYou(intent_request)
    elif intent_name == 'GreetingIntent':
        return welcome(intent_request)

    raise Exception('Intent with name ' + intent_name + ' not supported')


def lambda_handler(event, context):
    print(event)
    os.environ['TZ'] = 'America/New_York'
    time.tzset()
    logger.debug('event.bot.name={}'.format(event['bot']['name']))
    return dispatch(event)