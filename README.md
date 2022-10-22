# Chatbot Concierge #

## About ##

HW 2 of the Cloud Computing & Big Data class at Columbia University and New York University.

## Usage ##

1. Clone the repository.
2. Replace `/assets/js/sdk/apigClient.js` with your own SDK file from API
   Gateway.
3. Open `chat.html` in any browser.
4. Start sending messages to test the chatbot interaction.

## Implementation ##

1. Added lambda function (LF1) for implementing chatbot interactions. Majorly three types of intent were implemented
   GreetingIntent
   DiningSuggestions
   ThankYouIntent
2. Added lambda function (LF2) for handling recommendations. This function picks requests from SQS queue, finds the required recommendations and sends it via SES.
3. yelp-scraper.py is the file which scrapes data from Yelp database, stores it in DynamoDB and ElasticSearch.
4. CloudWatch triggers LF2 every minute to send requests from the SQS queue to SES.
5. Implemented the Extra Credit section as part of LF1 and LF2.
6. All searches are stored in a different DynamoDB table in LF2.
7. LF1 would be checking in the DynamoDB table before pushing the request to the queue.
8. If the search was implemented before, it immediately sends the mail to the user.
