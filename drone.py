
import time
import sys
from sys import getsizeof
import serial
import spidev
import RPi.GPIO as gpio


#SPI2UART
#uart1 = GSM
#uart2 = lora

ss1 = 22 #chip enable pin for spi2uart

spi = spidev.SpiDev()


def setup_pins():
	print("Setup GPIO and SPI")

	gpio.setmode(gpio.BOARD) #use real pin numbers for gpio pins
	gpio.setup(ss1, gpio.OUT) #set spi2uart chip select pin as output
	gpio.output(ss1, gpio.HIGH) #set spi2uart selector high to disable until needed

	spi.open(0,0) #(bus, device) - spi2uart
	spi.max_speed_hz = 1000000 #spi speed, make sure its > all of our spi2uart uarts speeds together
	spi.no_cs = True #we need custom chip select timings so we will use gpio pin control

	gpio.output(ss1, gpio.LOW) #set low to begin spi communication
	msg = [0x81] #0x80 = change baud rate, [0x80 | 0x00] = uart 1 baud rate, [0x80 | 0x01] = uart 2...
	spi.xfer(msg) #tell spi2uart we want to change baud
	msg = [0x03] #select baud rate (3 = 9600)
	spi.xfer(msg) #set
	gpio.output(ss1, gpio.HIGH) #end communication

def buff_check(uart): #check spi2uart module for received data in buffer on specific uart
	print("buffer check")
	send2 = [0x10 | uart] #0x10 = read number of bytes in receive buffer

	gpio.output(ss1, gpio.LOW) #begin spi communication
	spi.xfer(send2) #send request for byte count in buffer
	num = spi.readbytes(1) #read reply - 1 byte for up to 255 buffer size i think
	gpio.output(ss1, gpio.HIGH) # end communication

	return num #return buffer info

def setup_gsm():

	print("GSM check")
	msg = "AT\n"
	msg = list(bytearray(msg.encode()))
	#send = [0x41, len(msg)] + msg #tell spi2uart we want to write bytes to uart1
	#send = [0x41, 0x01, 0x01]
	#print(send)
	gpio.output(ss1, gpio.LOW)
	msgi = [0x40]
	spi.xfer(msgi)
#	time.sleep(0.01)
	msgl = [len(msg)]
	spi.xfer(msgl)
#	time.sleep(0.01)
	#msg = [0x70, 0x71, 0x6b]
	spi.xfer(msg)

#	spi.xfer(send)
	gpio.output(ss1, gpio.HIGH)
#	time.sleep(0.01)

def setup_lora():
	print("Hi")

def send_sms(mob, msg):
	print("Hi")

def read_sms():
	print("Hi")

def ctrl_drone():
	print("Hi")


setup_pins()

time.sleep(1)

print("attempting read")

result = buff_check(0x00)
print(result)
result = buff_check(0x01)
print(result)
result = buff_check(0x02)
print(result)
result = buff_check(0x03)
print(result)
setup_gsm()

gpio.cleanup()
