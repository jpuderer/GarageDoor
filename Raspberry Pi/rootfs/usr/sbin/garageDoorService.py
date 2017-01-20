#!/usr/bin/python

# Code for much of this was taken from the example code the Google provided on
# their website.  It has since disappeared from their site.

import atexit
import json
import logging
import logging.handlers
import random
import RPi.GPIO as GPIO
import string
import sys
import time
import xmpp

from time import sleep
from yaml import load, dump

try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper

SERVER = 'gcm.googleapis.com'
PORT = 5235
USERNAME = "REDACTED_GCM_USER_ID"
PASSWORD = "REDACTED_GCM_PASSWORD"

AUTH_FILE = "/etc/garageDoorService/auth.yaml"

# Setup logging
DEFAULT_LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOGGER = logging.getLogger(__name__)
LOGGER.addHandler(logging.handlers.SysLogHandler(address = '/dev/log'))

unacked_messages_quota = 100
send_queue = []

class StreamToLogger(object):
   """
   Fake file-like stream object that redirects writes to a logger instance.
   """
   def __init__(self, logger, log_level=logging.INFO):
      self.logger = logger
      self.log_level = log_level
      self.linebuf = ''
 
   def write(self, buf):
      for line in buf.rstrip().splitlines():
         self.logger.log(self.log_level, line.rstrip())

   def flush(self):
       pass
 
def configure_logging():
    LOGGER.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    formatter = logging.Formatter(DEFAULT_LOG_FORMAT)
    ch.setFormatter(formatter)
    LOGGER.addHandler(ch)

# Redirect stdout and stderr to logger
#sys.stdout = StreamToLogger(LOGGER, logging.DEBUG)
#sys.stderr = StreamToLogger(LOGGER, logging.DEBUG)

def setup_gpio():
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(20, GPIO.OUT)
    GPIO.output(20, False)
    GPIO.setup(21, GPIO.OUT)
    GPIO.output(21, False)

def cleanup():
    GPIO.cleanup()

def isAuthorized(user, password):
    # Open the auth file and load it, we do this everytime so we don't have to
    # reload the service.  The file shouldn't be too large in most cases
    authFile = file(AUTH_FILE, 'r')
    authDict = load(authFile)
    if not authDict.has_key(user):
        return False
    if authDict[user] == password:
        return True
    else:
        return False

def openGarageDoor():
    GPIO.output(20, True)
    sleep(1)
    GPIO.output(20, False)
    sleep(1)

# Return a random alphanumerical id
def random_id():
    rid = ''
    for x in range(8): rid += random.choice(string.ascii_letters + string.digits)
    return rid

def message_callback(session, message):
    global unacked_messages_quota
    gcm = message.getTags('gcm')
    if not gcm:
        LOGGER.warning("Received message callback, but not a GCM message")
        return

    gcm_json = gcm[0].getData()
    msg = json.loads(gcm_json)
    if (msg.has_key('message_type') and 
            (msg['message_type'] == 'ack' or msg['message_type'] == 'nack')):
        unacked_messages_quota += 1
        return

    # Ignore control messages.  The only type of control message
    # at the moment is CONNECTION_DRAINING, which we can't really
    # do anything about, since we're not actively sending messages
    # anyway
    if (msg.has_key('message_type') and msg['message_type'] == 'control'):
        LOGGER.info("Control message received")
        return

    # Ignore any messages that do not have a 'from' or 'message_id'
    if not msg.has_key('from'):
        LOGGER.warning("Message does not have 'from' field.")
        return
    if not msg.has_key('message_id'):
        LOGGER.warning("Message does not have 'message_id' field.")
        return

    # Acknowledge the incoming message immediately.
    send({'to': msg['from'],
        'message_type': 'ack',
        'message_id': msg['message_id']})
    if not msg.has_key('data'):
        LOGGER.warning("Empty request.  No data.")
        return
    if not type(msg['data']) is dict:
        LOGGER.warning("Invalid data in request.")
        return
    data = msg['data']
    if not data.has_key('timestamp'):
        LOGGER.warning("No timestamp in request.")
        return
    try:
        timestamp = float(data['timestamp'])
    except ValueError:
        LOGGER.warning("Invalid timestamp in request.")
        return
    if ((time.time() - timestamp) > 5):
        LOGGER.warning("Timestamp in request is too old.  Discarding request.")
        return
    if not data.has_key('user') or not data.has_key('password'):
        LOGGER.warning("No auth data in request.")
        return
    if not isAuthorized(data['user'], data['password']):
        LOGGER.warning("Invalid auth (user, password) = (" + 
            data['user'] + ", " + data['password'] + ")")
        return

    # Open the garage door
    LOGGER.info("Opening garage door for: " + data['user'])
    openGarageDoor()
        
    # Send an empty response to acknowledge that command was successfully 
    # received and processed app that sent the upstream message.
    send_queue.append({'to': msg['from'],
        'message_id': random_id(),
        'data': {}})
    flush_queued_messages()

    # Sleep for ten seconds to avoid button mashing.  Any other
    # requests that get queued behind this one will expire before
    # they do anything
    sleep(10)

def disconnect_callback():
    LOGGER.warning("XMPP session disconnected. Reconnecting.")
    connect()

def send(json_dict):
    template = ("<message><gcm xmlns='google:mobile:data'>{1}</gcm></message>")
    client.send(xmpp.protocol.Message(
        node=template.format(client.Bind.bound[0], json.dumps(json_dict))))

def connect():
    global client
    while True:
        # I think there's a bug in the XMPP library where the client
        # object doesn't get properly recreated after a connection failure
        # so we recreated from scratch each time
        client = xmpp.Client(SERVER, debug=['always'])

        # Add a bit of delay here to prevent crazy fast retries
        sleep(10)

        LOGGER.info('Attempting to connect to GCM service.')
        client.connect(server=(SERVER, PORT), secure=1, use_srv=False)
        if not client.isConnected():
            continue
        auth = client.auth(USERNAME, PASSWORD)
        if not auth:
            LOGGER.error('GCM Server Authentication failed!')
        else:
            break
    client.RegisterHandler('message', message_callback)
    client.RegisterDisconnectHandler(disconnect_callback)
    LOGGER.info('Connected.')

def flush_queued_messages():
    global unacked_messages_quota
    while len(send_queue) and unacked_messages_quota > 0:
        send(send_queue.pop(0))
        unacked_messages_quota -= 1

def main():
    connect()
    count = 0
    while (True):
        count += 1
        # Send a space character once every 60 seconds to see if the 
        # connection is still alive
        if count >= 60:
            LOGGER.info("Sending keep-alive")
            try:
                client.send(' ')
            except IOError, e:
                LOGGER.info('Unabled to send: ' + str(e))
            count = 0
        try:
            client.Process(1)
            flush_queued_messages()
	except AttributeError, e:
	    # I seem to get an attribute error in some cases is the client dies 
            # unexpectedly
    	    LOGGER.error('Client error: '+ str(e))
            time.sleep(5)
            connect()

if __name__ == '__main__':
    atexit.register(cleanup)
    configure_logging()
    setup_gpio()
    main()

