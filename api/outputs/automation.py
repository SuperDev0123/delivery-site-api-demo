import sys, time
import os, base64
from datetime import datetime
from email.utils import COMMASPACE
from django.conf import settings
from api.models import *
from twilio.rest import Client
from django.conf import settings

ENV = 'production'

def send_sms(message, phone_number):
	print('send_sms', message, phone_number)

	if ENV == 'test':
		account_sid = "AC3476f2ed21f2d16213f1ba58614f7c51"
		auth_token  = "670ab2e82cd4a4701fedb36a82579e6d"
	else:
		account_sid = settings.TWILIO['APP_SID']
		auth_token = settings.TWILIO['TOKEN']

	client = Client(account_sid, auth_token)

	if ENV == 'test':
		phone_number = "+17634069539"
		msg = client.messages.create(
	    to="+17634069539", 
	    from_="+15005550006",
	    body=message)
	else:
		phone_number = "+8613022454673"
		msg = client.messages.create(
	    to=phone_number,
	    from_=settings.TWILIO['NUMBER'],
	    body=message)

	print('twilio sent msg id', msg.sid)

	
    
