#!/usr/bin/python

import sys
import spidev
import logging
import getpass
import sleekxmpp
from optparse import OptionParser
import Adafruit_DHT
import time
import RPi.GPIO as io
import thread
import serial

LEDState = '0;0;0;0'

io.setmode(io.BCM)

spi = spidev.SpiDev()
spi.open(0,0)

# Channel 6 is out Thermistor
# Since this is an SPI device, we initialize it here
Channel6_SPI = 1


# Channel 5 is our PhotoDiode
# Since this is an SPI device, we intialize it here
Channel5_SPI = 0

# Channel 4 is our LED Array
Channel4_GPIO = [24, 7, 22, 17]
io.setup(Channel4_GPIO, io.OUT)

# Channel 3 is our PIR
Channel3_GPIO = 18
io.setup(Channel3_GPIO, io.IN)

# Channel 2 is the DHT Humidity
Channel2_Sensor = Adafruit_DHT.DHT11
Channel2_GPIO = 23

# Channel 1 is the DHT Temperature
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

# UART function
def readlineCR(port):
        ch = port.read()
        rv = ''
        n = 0
        while (ch!='!') & (ch!='\r'): # & (ch!=''):

                rv += ch
                ch = port.read()
                n = n + 1
        print  'rv: %s',rv
        return rv




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



# This is the workhorse of all the read functions in this section. Thie method
# takes in a channelId, a timeout value, and what samplingmode is needed. This function
# is called upon when a '7211' message is recieved from the client. It returns back
# a single point of data. This function would be the only one you need to change in terms
# of your own design.

def ReadTransducerSampleDataFromAChannelOfATIM(timId, channelId, timeout, samplingMode):
	# Since we have the DHT11, we have one sensor responsible for both temperature and humidity.
	print 'I MADE IT TO THE FUNCTION'
	

	if timId == '1':
		if channelId == '1' or channelId == '2':
			# If you can spare the sampling time, .read_retry will attempt for 2 seconds to read the values
			humidity, temperature = Adafruit_DHT.read_retry(Channel1_Sensor, Channel1_GPIO)
			# Due to the nature of the one wire interface, occasionally a measurment in not obtained.
			# In this case, we respond back to the user with an empty data field and an error code.
			if humidity is not None and temperature is not None:
				print 'Temp={0:0.1f}*C  Humidity={1:0.1f}%'.format(temperature, humidity)
				if channelId == '1':
					data = str(temperature)
				elif channelId == '2':
					data = str(humidity)
				#data = str(humidity) + ":" + str(temperature)
				errorCode = 0
			else:
				print 'Failed to get a reading from the DHT11'
				data = ''
				# We are assuming that a non-zero errorCode means there is a problem
				errorCode = 1

		if channelId == '3':
			if io.input(Channel3_GPIO):
				print("Occupancy Detected")
				data = 1
			elif io.input(Channel3_GPIO) == 0:
				print("Empty")
				data = 0
			# There needs to be errorhandling incase a problem arises in the PIR
			errorCode = 0

		
		if channelId == '4':
			global LEDState
			data = LEDState
			errorCode = 0
		
		if channelId == '5' or channelId == '6':
			if channelId == '5':
				rawData = spi.xfer([1, (8+Channel5_SPI) << 4, 0])
			elif channelId == '6':
				rawData = spi.xfer([1, (8+Channel6_SPI) << 4, 0])
		
			data = str(((rawData[1]&3) << 8) + rawData[2])
		
			if data == '0':
				errorCode = 1
			elif data == '1023':
				errorCode = 2
			else:
				errorCode = 0

		return {'errorCode':errorCode, 'data':data}


	elif timId == '2':
		if channelId == '1':
			print 'Channel 1 Tim 2'
			UARTport.flushInput()
			print 'Flushed Input'
			UARTport.write('distance')
			print 'Wrote to the port'
			data = readlineCR(UARTport)
			print data
			errorCode = 0
			return {'errorCode':errorCode, 'data':data}
		if channelId == '2':
			UARTport.flushInput()
			UARTport.write('led')
			return {'errorCode':'0', 'data':'worked'}




# This is the function which is called by the '7213' message. Unlike the single channel read, the
# channelId is actually a string containing ";" seperated channels.

def ReadTransducerSampleDataFromMultipleChannelsOfATIM(timId, channelId, timeout, samplingMode):
	ChannelIDS = channelId.split(";")
	
	# Initializing the data list
	data = ""
	n = 1
	# We have a flag which allows us to track whether or not the value in question is the first value found.
	FirstValue = 0
	for ChannelID in ChannelIDS:
		DATA = ReadTransducerSampleDataFromAChannelOfATIM(timId, ChannelID, timeout, samplingMode)
		# This chunk of logic keeps the resulting data looking very pretty.
		if FirstValue == 0:
			data = data + str(DATA['data'])
			FirstValue = 1
		elif n==len(ChannelIDS):
			data = data + ";" + str(DATA['data'])
		else:
			data = data + ";" + str(DATA['data'])
		n = n+1
		print data
	errorCode = 0
	return{'channelId':channelId, 'data':data, 'errorCode':errorCode}


# This function is called when a '7212' message is recieved.
def ReadTransducerBlockDataFromAChannelOfATIM(timId, channelId, timeout, numberOfSamples, sampleInterval, startTime):
	time.sleep(int(startTime))
	BlockData = ""
	samplingMode = '5'
	for num in range(0,int(numberOfSamples)):
		BlockData = BlockData + str(ReadTransducerSampleDataFromAChannelOfATIM(timId,channelId, timeout, samplingMode)['data']) + ';'
		time.sleep(int(sampleInterval))
	errorCode = 0
	return{'errorCode':errorCode, 'data':BlockData}


def ReadTransducerBlockDataFromMultipleChannelsOfATIM(timId, channelId, timeout, numberOfSamples, sampleInterval, startTime):
	channelIds = channelId.split(";")
	time.sleep(int(startTime))
	samplingMode = '5'
	BlockData = ['']*len(channelIds)
	for SampleNum in range(0,int(numberOfSamples)):
		for ChanNum in range(0,len(channelIds)):
		#	print ChanNum
			BlockData[ChanNum] = BlockData[ChanNum] + ";" + str(ReadTransducerSampleDataFromAChannelOfATIM(timId, channelIds[ChanNum], timeout, samplingMode)['data']) 
		
		time.sleep(int(sampleInterval))
	errorCode = 0
	data = ''
	for ChanNum in range(0,len(channelIds)):
		data = data + '{' + BlockData[ChanNum] + '}' 
	return{'errorCode':errorCode, 'data':data}





def WriteTransducerSampleDataToAChannelOfATIM(timId, channelId, timeout, samplingMode, dataValue):
        
        if channelId == '4':
                global LEDState
		LEDState = dataValue
		data = dataValue.split(";")
		for num in range(0,len(data)):
			if data[num] == '1':
				io.output(Channel4_GPIO[num], True)
			elif data[num] == '0':
				io.output(Channel4_GPIO[num], False)
		ErrorCode = '0'
			
		
		#if dataValue == '1':
                #        io.output(Channel4_GPIO, True)
                #        ErrorCode = 0
                #        print 'LED On'
                #elif dataValue == '0':
                #        io.output(Channel4_GPIO, False)
                #        ErrorCode = 0
                #        print 'LED OFF'
                #else:
                #        ErrorCode = 1
        return {'errorCode':ErrorCode}


def WriteTransducerBlockDataToAChannelOfATIM(timId, channelId, timeout, numberOfSamples, sampleInterval, startTime, dataValue):
	data = dataValue.split(":")
	time.sleep(int(startTime))
	samplingMode = '5'
	for num in range(0,int(numberOfSamples)):
		errorCode = str(WriteTransducerSampleDataToAChannelOfATIM(timId, channelId, timeout, samplingMode, data[num]))
		time.sleep(float(sampleInterval)/1000)
	print errorCode
	return{'errorCode':errorCode}






#############################################################
# Threading Functions
#############################################################

def Thread7211(MSG_Tuple, SenderInfo): 
        MSG = dict(map(None, MSG_Tuple))
	SensorData = ReadTransducerSampleDataFromAChannelOfATIM(MSG['timId'],MSG['channelId'],MSG['timeout'],MSG['samplingMode'])
	response = MSG['functionId'] + ',' + str(SensorData['errorCode']) + ',' +MSG['ncapId'] + ',' + MSG['timId'] + ',' + MSG['channelId'] + ',' + str(SensorData['data'])
	xmpp_send(str(SenderInfo[1]), response)

def Thread7212(MSG_Tuple, SenderInfo):
        MSG = dict(map(None, MSG_Tuple))
	SensorData = ReadTransducerBlockDataFromAChannelOfATIM(MSG['timId'],MSG['channelId'], MSG['timeout'], MSG['numberOfSamples'], MSG['sampleInterval'], MSG['startTime'])
        response = MSG['functionId'] + ',' + str(SensorData['errorCode']) + ',' + MSG['ncapId'] + ',' + MSG['timId'] + ',' + MSG['channelId'] + ',' + str(SensorData['data'])
	xmpp_send(str(SenderInfo[1]), response)

def Thread7213(MSG_Tuple, SenderInfo):
	MSG = dict(map(None, MSG_Tuple))
        SensorData = ReadTransducerSampleDataFromMultipleChannelsOfATIM(MSG['timId'], MSG['channelId'], MSG['timeout'], MSG['samplingMode'])
        response =  MSG['functionId'] + ',' + str(SensorData['errorCode']) + ',' + MSG['ncapId'] + ',' + MSG['timId'] + ',' + MSG['channelId'] + ',' + str(SensorData['data'])
        xmpp_send(str(SenderInfo[1]), response)

def Thread7214(MSG_Tuple, SenderInfo):
	MSG = dict(map(None, MSG_Tuple))
        SensorData = ReadTransducerBlockDataFromMultipleChannelsOfATIM(MSG['timId'], MSG['channelId'], MSG['timeout'], MSG['numberOfSamples'], MSG['sampleInterval'], MSG['startTime'])
        response =  MSG['functionId'] +  ',' + MSG['ncapId'] + ',' + MSG['timId'] + ',' + MSG['channelId'] + ',' +  str(SensorData['data'])
        xmpp_send(str(SenderInfo[1]), response)

def Thread7217(MSG_Tuple, SenderInfo):
	MSG = dict(map(None, MSG_Tuple))
        ErrorCode = WriteTransducerSampleDataToAChannelOfATIM(MSG['timId'], MSG['channelId'], MSG['timeout'], MSG['samplingMode'], MSG['dataValue'])
        response = MSG['functionId']+ ',' + str(ErrorCode['errorCode']) + ',' + MSG['ncapId'] + ',' + MSG['timId'] + ',' + MSG['channelId']
        xmpp_send(str(SenderInfo[1]), response)
	
def Thread7218(MSG_Tuple, SenderInfo):
	MSG = dict(map(None, MSG_Tuple))
        ErrorCode = WriteTransducerBlockDataToAChannelOfATIM(MSG['timId'], MSG['channelId'], MSG['timeout'], MSG['numberOfSamples'], MSG['sampleInterval'], MSG['startTime'], MSG['dataValue'])
        response = MSG['functionId']+ ',' + str(ErrorCode['errorCode']) + ',' + MSG['ncapId'] + ',' + MSG['timId'] + ',' + MSG['channelId']
        xmpp_send(str(SenderInfo[1]), response)


##############################################################

def MessageParse(msg):
	stringy = str(msg['body'])
	parse = stringy.split(",")
	functionId = parse[0]
	print functionId
	ncapId =  parse[1]
	timId =  parse[2]
	channelId =  parse[3]
	timeout =  parse[4]
	if functionId == '7212' or functionId == '7214' or functionId == '7218':
		print 'I am in the nested if statement'
		numberOfSamples = parse[5]
		sampleInterval = parse[6]
		startTime = parse[7]
		if functionId == '7218':
			dataValue = parse[8]
			return {'functionId':functionId, 'ncapId':ncapId, 'timId':timId, 'channelId':channelId, 'timeout':timeout, 'numberOfSamples':numberOfSamples, 'sampleInterval':sampleInterval, 'startTime':startTime, 'dataValue':dataValue}
		return {'functionId':functionId, 'ncapId':ncapId, 'timId':timId, 'channelId':channelId, 'timeout':timeout, 'numberOfSamples':numberOfSamples, 'sampleInterval':sampleInterval, 'startTime':startTime}
	samplingMode = parse[5]
	if functionId == '7217':
		dataValue = parse[6]
		return {'functionId':functionId, 'ncapId':ncapId, 'timId':timId, 'channelId':channelId, 'timeout':timeout, 'samplingMode':samplingMode, 'dataValue':dataValue}
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

	global UARTport
	UARTport = serial.Serial("/dev/ttyAMA0", baudrate=9600, timeout=0.25)


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
	   print 'Recieved Message'
	   MSG = MessageParse(msg)

	   if MSG['functionId'] == '7211':
		print 'Recieved a 7211 Message'
	        thread.start_new_thread(Thread7211, (tuple(MSG.items()), ('from', msg['from'])))

	   if MSG['functionId'] == '7212':
		thread.start_new_thread(Thread7212, (tuple(MSG.items()), ('from', msg['from'])))

	   if MSG['functionId'] == '7213':
		thread.start_new_thread(Thread7213, (tuple(MSG.items()), ('from', msg['from'])))

	   if MSG['functionId'] == '7214':
		thread.start_new_thread(Thread7214, (tuple(MSG.items()), ('from', msg['from'])))


           if MSG['functionId'] == '7217':
                thread.start_new_thread(Thread7217, (tuple(MSG.items()), ('from', msg['from'])))

	   if MSG['functionId'] == '7218':
		thread.start_new_thread(Thread7218, (tuple(MSG.items()), ('from', msg['from'])))


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
        opts.jid = 'ncap@jahschwa.com'
    if opts.password is None:
        opts.password = 'password'

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

