import time
#from time import time
import sys
import spidev
import RPi.GPIO as gpio

ss1 = 22 #chip enable pin for spi2uart

bufflen = [0, 0]
spi = spidev.SpiDev()

print("Initiate GPIO and SPI...")

gpio.setmode(gpio.BOARD) #use real pin numbers for gpio pins

gpio.setup(ss1, gpio.OUT) #set spi2uart chip select pin as output
gpio.output(ss1, gpio.HIGH) #set spi2uart selector high to disable until needed

spi.open(0,0) #(bus, device) - spi2uart
spi.max_speed_hz = 50000 #spi speed, make sure its > all of our spi2uart uarts speeds together
spi.no_cs = True #we need custom chip select timings so we will use gpio pin control


def buff_check(uart): #check spi2uart module for received data in buffer on specific uart

	set = [0x10 | uart] #0x10 = read number of bytes in receive buffer

	gpio.output(ss1, gpio.LOW) #begin spi communication
	spi.xfer(set) #send request for byte count in buffer
	num = spi.readbytes(1) #read reply - 1 byte for up to 255 buffer size i think
	gpio.output(ss1, gpio.HIGH) # end communication

	return num #return buffer info

def buff_read(uart, amt):

	set = [0x20 | uart] #0x20 = read buffer bytes

	gpio.output(ss1, gpio.LOW) #begin spi communication
	spi.xfer(set) #send request for buffer bytes
	set = [amt] #request amount of bytes
	spi.xfer(set)
	read = spi.readbytes(amt)

	return read

def buff_send(uart, msg):
	gpio.output(ss1, gpio.LOW)
	set = [0x40 | uart]
	spi.xfer(set)
	set = [len(msg)]
	spi.xfer(set)
	spi.xfer(msg)
	gpio.output(ss1, gpio.HIGH)

def uart_decode(msg):
	return bytearray(msg).decode()
	
while True:
	msg = input(":")
	msg = list(bytearray(msg.encode()))

	buff_send(0x00, msg)
	time.sleep(2)

	bufflen = buff_check(0x00)
	if bufflen[0] > 0:
		rec = buff_read(0x00, bufflen[0])
		rec = uart_decode(rec)
  
  
