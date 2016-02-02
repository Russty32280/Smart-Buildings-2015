import serial
import time

def readlineCR(port):
        ch = port.read()
        rv = ''
        n = 0
        while (ch!='!') & (ch!='\r'): # & (ch!=''):

                rv += ch
                ch = port.read()
                n = n + 1
        print  rv
        print  ch
        print n
        print len(rv)

global UARTPort
UARTPort = serial.Serial(
    "/dev/ttyAMA0", baudrate=19200, timeout= 0.25)

UARTPort.flushInput()
UARTPort.flushOutput()

UARTPort.write('distance')
UARTPort.close()
