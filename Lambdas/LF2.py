import boto3
import json
import logging
from boto3.dynamodb.conditions import Key, Attr
from botocore.exceptions import ClientError
import requests
import random
import datetime

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
sqs = boto3.client("sqs")

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

def getSQSMsg():
    queueurl = sqs.get_queue_url(QueueName='DiningSQS').get('QueueUrl')
    response = sqs.receive_message(QueueUrl= queueurl, 
                AttributeNames=['SentTimestamp'],
                MessageAttributeNames=['All'],
                VisibilityTimeout=0,
                WaitTimeSeconds=0)
    logger.debug(response)
     
    try:
        message = response['Messages'][0]
        logger.debug('in try.....')
        if message is None:
            logger.debug("Empty message")
            return None
    except KeyError:
        logger.debug('in catch.....')
        logger.debug("No message in the queue")
        return None
    message = response['Messages'][0]
    sqs.delete_message(QueueUrl=queueurl,ReceiptHandle=message['ReceiptHandle'])
    logger.debug('Received and deleted message: %s' % response)
    return message

def lambda_handler(event, context):
    message = getSQSMsg() #data will be a json object

    if message is None:
        logger.debug("No cuisine or phoneNum key found in message")
        return
    print('Message : ', message)
    cuisine = message["MessageAttributes"]["cuisine"]["StringValue"]
    location = message["MessageAttributes"]["location"]["StringValue"]
    time = message["MessageAttributes"]["time"]["StringValue"]
    numOfPeople = message["MessageAttributes"]["people"]["StringValue"]
    phoneNumber = message["MessageAttributes"]["phone"]["StringValue"]
    emailid = message["MessageAttributes"]["emailid"]["StringValue"]
    phoneNumber = "+1" + phoneNumber
    if not cuisine or not phoneNumber:
        #logger.debug("No Cuisine or PhoneNumber key found in message")
        return
    
    ###
    query = {
        "size": 1000,
        "query": {
            "multi_match": {
                "query": cuisine,
                "fields": ["cuisine"]
            }
        }
    }
    headers = { "Content-Type": "application/json" }
    es_query = "https://search-restaurants-cbyh4tpkbi5k2x27arx725xx7y.us-east-1.es.amazonaws.com/restaurants/_search"
    esResponse = requests.get(es_query, headers=headers, auth=('admin', 'Admin@12345'), data=json.dumps(query))
    data = esResponse.json()
    try:
        esData = data["hits"]["hits"]
    except KeyError:
        logger.debug("Error extracting hits from ES response")
    
    # extract bID from AWS ES
    ids = []
    for restaurant in esData:
        ids.append(restaurant["_source"]["id"])
    
    messageToSend = 'Hello! Here are my {cuisine} restaurant suggestions in {location} for {numPeople} people at {diningTime}:<br/>'.format(
            cuisine=cuisine,
            location=location,
            numPeople=numOfPeople,
            diningTime=time,
        )

    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('yelp-restaurants')
    itr = 1
    for id in ids:
        if itr > 10:
            break
        response = table.get_item(Key={'restaurantId' : id})
        if response is None:
            continue
        item = response['Item']
        address = item["restaurantAddress"]
        if location.lower() in address.lower():
            restaurantMsg = '' + str(itr) + '. '
            name = item["restaurantName"]
            restaurantMsg += name +', located at ' + address +'. '
            messageToSend += restaurantMsg + "<br/>"
            itr += 1
        
    messageToSend += "Enjoy your meal!!"
    
    userstable = dynamodb.Table('recommended-users')
    userstable.put_item(
        Item={
            'cuisine' : cuisine,
            'location' : location, 
            'phonenumber' : phoneNumber,
            'emailid' : emailid, 
            'messagetosend' : messageToSend,
            'insertedAtTimestamp': str(datetime.datetime.now())
           }
        )
    
    sendMailToUser(messageToSend, emailid)
    logger.debug("Message = '%s' Phone Number = %s" % (messageToSend, phoneNumber))
    
    
    
    return {
        'statusCode': 200,
        'body': json.dumps("LF2 running succesfully")
    }