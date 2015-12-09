#!/usr/bin/python

import sys
import logging
import getpass
from optparse import OptionParser
import Adafruit_DHT
import time
import RPi.GPIO as io


io.setmode(io.BCM)

Channel3_GPIO = 23

io.setup(Channel3_GPIO, io.OUT)

Channel2_GPIO = 18

io.setup(Channel2_GPIO, io.IN)

Channel1_Sensor = Adafruit_DHT.DHT11

Channel1_GPIO = 23



# - Python versions before 3.0 do not use UTF-8 encoding
# by default. To ensure that Unicode is handled properly
# throughout SleekXMPP, we will set the default encoding
# ourselves to UTF-8.
if sys.version_info < (3, 0):
    from sleekxmpp.util.misc_ops import setdefaultencoding
    setdefaultencoding('utf8')
else:
    raw_input = input

#######################################################

# xmpp send function
def xmpp_send(toAddr,myMsg,**key):
    type = 'Normal'
    if ('type' in key):
        type = key['type']
    if type == 'Normal':
        xmpp.send_message(
            mto=toAddr,mbody=myMsg,mtype='chat')
    elif type == 'All':
        toAddr = 'P21451'
        xmpp.send_message(
            mto=toAddr,mbody=myMsg,mtype='groupchat')
####################################################



def ReadTransducerSampleDataFromAChannelOfATIM(channelId, timeout, samplingMode):
	if channelId == '1':
		humidity, temperature = Adafruit_DHT.read_retry(Channel1_Sensor, Channel1_GPIO)
		if humidity is not None and temperature is not None:
			print 'Temp={0:0.1f}*C  Humidity={1:0.1f}%'.format(temperature, humidity)
			data = str(humidity, temperature)
			errorCode = 0
		else:
			print 'Failed to get a reading from the DHT11'
			errorCode = 1

	if channelId == '2':
		if io.input(Channel2_GPIO):
			print("Occupancy Detected")
			data = 1
		elif io.input(Channel2_GPIO) == 0:
			print("Empty")
			data = 0
		errorCode = 0


	return {'errorCode':errorCode, 'data':data}



#while sensor_choice!=0:
#
#	sensor_choice = input('Enter 1 for PIR or 2 for Temp/Humidity')
#	
#	if sensor_choice == 1:
#		if io.input(Channel2_GPIO):
#			print("Occupancy Detected")
#		
#	elif sensor_choice == 2:
#		humidity, temperature = Adafruit_DHT.read_retry(Channel1_Sensor, Channel1_GPIO)
#		if humidity is not None and temperature is not None:
#			print 'Temp={0:0.1f}*C  Humidity={1:0.1f}%'.format(temperature, humidity)
#		else:
#			print 'Failed to get a reading from the DHT11'




##############################################################

def parsing(msg):
	stringy = str( msg['body'])
	parse = stringy.split(",")
	functionId = parse[0]
	ncapId =  parse[1]
	timId =  parse[2]
	channelId =  parse[3]
	timeout =  parse[4]
	samplingMode = parse[5]
	#errorCode = 1
	return {'functionId':functionId, 'ncapId':ncapId, 'timId':timId, 'channelId':channelId, 'timeout':timeout, 'samplingMode':samplingMode} 

################################################################


class EchoBot(sleekxmpp.ClientXMPP):

    """
    A simple SleekXMPP bot that will echo messages it
    receives, along with a short thank you message.
    """

    def __init__(self, jid, password):
        sleekxmpp.ClientXMPP.__init__(self, jid, password)

        # The session_start event will be triggered when
        # the bot establishes its connection with the server
        # and the XML streams are ready for use. We want to
        # listen for this event so that we we can initialize
        # our roster.
        self.add_event_handler("session_start", self.start)

        # The message event is triggered whenever a message
        # stanza is received. Be aware that that includes
        # MUC messages and error messages.
        self.add_event_handler("message", self.message)

    def start(self, event):
        """
        Process the session_start event.
        Typical actions for the session_start event are
        requesting the roster and broadcasting an initial
        presence stanza.
        Arguments:
            event -- An empty dictionary. The session_start
                     event does not provide any additional
                     data.
        """
       
	self.send_presence()
        self.get_roster()

    def message(self, msg):
        """
        Process incoming message stanzas. Be aware that this also
        includes MUC messages and error messages. It is usually
        a good idea to check the messages's type before processing
        or sending replies.
        Arguments:
            msg -- The received message stanza. See the documentation
                   for stanza objects and the Message stanza to see
                   how it may be used.
        """
        if msg['type'] in ('chat', 'normal'):
	   MSG = parsing(msg)

	   if MSG['functionId'] == '7211':
	        SensorData = ReadTransducerSampleDataFromAChannelOfATIM(MSG['channelId'],MSG['timeout'],MSG['samplingMode'])
		response = MSG['functionID'] + ',' + SensorData['errorCode'] + ',' + MSG['ncapIds'] + ',' + MSG['timId'] + ',' + MSG['channelId'] + ',' + SensorData['data']
		xmpp_send(str(msg['from']), response)

if __name__ == '__main__':
    # Setup the command line arguments.
    optp = OptionParser()

    # Output verbosity options.
    optp.add_option('-q', '--quiet', help='set logging to ERROR',
                    action='store_const', dest='loglevel',
                    const=logging.ERROR, default=logging.INFO)
    optp.add_option('-d', '--debug', help='set logging to DEBUG',
                    action='store_const', dest='loglevel',
                    const=logging.DEBUG, default=logging.INFO)
    optp.add_option('-v', '--verbose', help='set logging to COMM',
                    action='store_const', dest='loglevel',
                    const=5, default=logging.INFO)

    # JID and password options.
    optp.add_option("-j", "--jid", dest="jid",
                    help="JID to use")
    optp.add_option("-p", "--password", dest="password",
                    help="password to use")
    opts, args = optp.parse_args()

    # Setup logging.
    logging.basicConfig(level=opts.loglevel,
                        format='%(levelname)-8s %(message)s')

    if opts.jid is None:
        opts.jid = 'client1@jahschwa.com'
    if opts.password is None:
        opts.password = 'Password1'

    # Setup the EchoBot and register plugins. Note that while plugins may
    # have interdependencies, the order in which you register them does
    # not matter.
    xmpp = EchoBot(opts.jid, opts.password)
    xmpp.register_plugin('xep_0030') # Service Discovery
    xmpp.register_plugin('xep_0004') # Data Forms
    xmpp.register_plugin('xep_0060') # PubSub
    xmpp.register_plugin('xep_0199') # XMPP Ping

     # Connect to the XMPP server and start processing XMPP stanzas.
    if xmpp.connect():
        # If you do not have the dnspython library installed, you will need
        # to manually specify the name of the server if it does not match
        # the one in the JID. For example, to use Google Talk you would
        # need to use:
        #
        # if xmpp.connect(('talk.google.com', 5222)):
        #     ...
        xmpp.process(block=True)
        print("Done")
    else:
        print("Unable to connect.")

