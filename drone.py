
import time
#from time import time
import sys
import serial
import spidev
import RPi.GPIO as gpio
import random

#SPI2UART
#uart1 = GSM
#uart2 = lora

ss1 = 22 #chip enable pin for spi2uart
gsmint = 18 #interupt pin from gsm to notify of sms
spi = spidev.SpiDev()

smsrec = 0

def setup_pins():

	print("Initiate GPIO and SPI...")

	gpio.setmode(gpio.BOARD) #use real pin numbers for gpio pins
	gpio.setup(gsmint, gpio.IN, pull_up_down=gpio.PUD_UP)
	gpio.add_event_detect(gsmint, gpio.FALLING, callback = detect_sms, bouncetime = 50)
	gpio.setup(ss1, gpio.OUT) #set spi2uart chip select pin as output
	gpio.output(ss1, gpio.HIGH) #set spi2uart selector high to disable until needed

	spi.open(0,0) #(bus, device) - spi2uart
	spi.max_speed_hz = 50000 #spi speed, make sure its > all of our spi2uart uarts speeds together
	spi.no_cs = True #we need custom chip select timings so we will use gpio pin control

#	gpio.output(ss1, gpio.LOW) #set low to begin spi communication
#	msg = [0x81] #0x80 = change baud rate, [0x80 | 0x00] = uart 1 baud rate, [0x80 | 0x01] = uart 2...
#	spi.xfer(msg) #tell spi2uart we want to change baud
#	msg = [0x03] #select baud rate (3 = 9600)
#	spi.xfer(msg) #set
#	gpio.output(ss1, gpio.HIGH) #end communication

	print("done\n")

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

def buff_send_sms(uart, msg):
	end = [26]
	nl = "\n"
	nl = list(bytearray(nl.encode()))
	msg = msg + end + nl
#	print(msg)
	gpio.output(ss1, gpio.LOW)
	set = [0x40 | uart]
	spi.xfer(set)
	set = [len(msg)]
	spi.xfer(set)
	spi.xfer(msg)
	gpio.output(ss1, gpio.HIGH)

def detect_sms(channel):
	print("[GSM] SMS interrupt")
	#print(channel)
	global smsrec
	smsrec = 1


def uart_decode(msg):
	return bytearray(msg).decode()

def setup_gsm(): #check connection to and set up the gsm module

	print("Setting up GSM module...")
	stage = 0 #track setup stage
	time1 = time.time() #timers for time out / retrying
	time2 = time.time()
	bufflen = 0

	testsms = str(random.randrange(10000))

	print ("[GSM] Disable echo")
	msg = "ATE0\n" #command to turn off gsm echo
	msg = list(bytearray(msg.encode())) #convert message to sendable data

	buff_send(0x00, msg)

	time.sleep(2)

	bufflen = buff_check(0x00)
	if bufflen[0] > 0:
		dat = buff_read(0x00, bufflen[0])
		dat = uart_decode(dat).strip("\n\r\0")
		print ("[GSM] Response: " + dat)

	time.sleep(0.5)


	while stage < 19: #while stages left to go

		if stage == 0: #Check module is connected (AT should reply with 'OK')
			print("[GSM] Send AT, await 'OK'...")
			msg = "AT\n"
			msg = list(bytearray(msg.encode())) #convert message into sendable data

			buff_send(0x00, msg)

			time1 = time.time() #record time AT sent for timeout
			stage = 1 #move onto next stage

		if stage == 1: #listen for response from gsm module (we expect 'OK')
			bufflen = buff_check(0x00) #check if data is received on uart0 buffer of spi2uart
			if bufflen[0] > 0: #if buffer has bytes
				print("[GSM] Response detected")
				stage = 2 #move to read buffer
				time.sleep(1)
			else:
				time.sleep(1) #else wait for response

			if time.time()-time1 > 10: #if no response in 10 seconds, return to stage 0 and resend AT
				print("[GSM] Response timeout, retrying AT...")
				stage = 0

		if stage == 2: #read response from module, ensure it is 'OK', otherwise retry
			print("[GSM] Get Reponse...")
			msg = buff_read(0x00, bufflen[0]) #read uart0 received bytes
			msg2 = uart_decode(msg) #decode into text

			if(msg2.strip("\n\r\0") == "OK"): #if expected response from GSM module
				print("[GSM] Response: OK\n")
				stage = 3
				time.sleep(1)
			else: #if response not as expected, then return to stage 0
				print("[GSM] Respone: FAIL: %s" % msg2.strip("\n\r\0"))
				print(msg)
				stage = 0

		if stage == 3: #check cops / creg?
			print("[GSM] Check cellular connection...")
			msg = "AT+COPS?\n"
			msg = list(bytearray(msg.encode()))

			buff_send(0x00, msg)

			stage = 4
			time1 = time.time()

		if stage == 4:
			bufflen = buff_check(0x00)
			if bufflen[0] > 0:
				print ("[GSM] Response detected")
				stage = 5
				time.sleep(1)
			else:
				time.sleep(1)

			if time.time() - time1 > 10:
				print ("[GSM] Response timeout, retry connection check")
				stage = 3

		if stage == 5:
			print ("[GSM] Get Response...")
			msg = buff_read(0x00, bufflen[0])
			msg2 = uart_decode(msg)
			msg3 = list(msg2)

			tar = ["O", "2"]
			if set(tar).issubset(set(msg3)):
				print ("[GSM] Response: OK\n")
				stage = 6
				time.sleep(1)
			else:
				print ("[GSM] Response: FAIL: %s" % msg2)
				stage = 3
				time.sleep(1)

		if stage == 6: #send text to self
			print("[GSM] Send test SMS to self...")
			msg = "AT+CMGF=1\n"
			msg = list(bytearray(msg.encode()))

			buff_send(0x00, msg)

			stage = 7
			time1 = time.time()

		if stage == 7:
			bufflen = buff_check(0x00)
			if bufflen[0] > 0:
				print("[GSM] Response detected")
				stage = 8
				time.sleep(1)
			else:
				time.sleep(1)

			if time.time()-time1 > 10:
				print ("[GSM] Response timeout, retry enter SMS mode")
				stage = 6

		if stage == 8:
			print ("[GSM] Get Response...")
			msg = buff_read(0x00, bufflen[0])
			msg2 = uart_decode(msg)

			if msg2.strip("\n\r\0") == "OK":
				print ("[GSM] SMS mode: OK")
				stage = 9
				time.sleep(1)
			else:
				print("[GSM] SMS mode: FAIL")
				stage = 6
				time.sleep(1)

		if stage == 9:
			print("[GSM] Input number")
			msg = "AT+CMGS=\"+447459636932\"\n" #self
			#msg = "AT+CMGS=\"+447914157048\"\n" #j-dog
			msg = list(bytearray(msg.encode()))

			buff_send(0x00, msg)

			time1 = time.time()
			stage = 10

		if stage == 10:
			bufflen = buff_check(0x00)

			if bufflen[0] > 0:
				print ("[GSM] Response detected")
				stage = 11
				time.sleep(1)
			else:
				time.sleep(1)

			if time.time() - time1 > 10:
				print ("[GSM] Response timeout, retry SMS")
				stage = 6
				time.sleep(1)

		if stage == 11:
			print ("[GSM] Get response...")
			msg = buff_read(0x00, bufflen[0])
			msg2 = uart_decode(msg)

			if msg2.strip(" \n\r\0") == ">":
				print ("[GSM] SMS ready")
				stage = 12
				time.sleep(1)
			else:
				print ("[GSM] Response: FAIL, retry SMS")
				stage = 6
				time.sleep(1)

		if stage == 12:
			print ("[GSM] Send SMS...")
			msg = testsms
			msg = list(bytearray(msg.encode()))

			buff_send_sms(0x00, msg)
			time.sleep(2)
			time1 = time.time()
			stage = 13

		if stage == 13:
			bufflen = buff_check(0x00)
			if bufflen[0] > 0:
				print ("[GSM] Response detected")
				stage = 14
				time.sleep(1)
			else:
				time.sleep(1)

		if stage == 14:
			msg = buff_read(0x00, bufflen[0])
			msg2 = uart_decode(msg)
			#print ("[GSM] Received: %s" % msg2)
			stage = 15
			time.sleep(1)
			time1 = time.time()

		if stage == 15: #wait for text from self
			global smsrec
			if smsrec == 1:
				print("[GSM] SMS received")
				stage = 16
				smsrec = 0
				time.sleep(1)
			else:
				print ("[GSM] Wait SMS...")
				time.sleep(2)


			if time.time() - time1 > 25:
				print ("[GSM] SMS Timout, exit")
				stage = 16
				time.sleep(1)

		if stage == 16:

			print ("SMSREC %d" % smsrec)

			print("[GSM] Read SMS...")
			msg = "AT+CMGL=\"REC UNREAD\"\n"
			msg = list(bytearray(msg.encode()))

			buff_send(0x00, msg)

			stage = 17
			time.sleep(1)
			time1 = time.time()

		if stage == 17:
			bufflen = buff_check(0x00)
			if bufflen[0] > 0:
				print ("[GSM] SMS data received")
				stage = 18
				time.sleep(1)
			else:
				time.sleep(1)

			if time.time() - time1 > 10:
				print ("[GSM] SMS read timout, retry read")
				stage = 16

		if stage == 18:
			msg = buff_read(0x00, bufflen[0])
			msg1 = uart_decode(msg)
			msg2 = list(msg1)
			tar = list(testsms)

			if set(tar).issubset(set(msg2)):
				print ("[GSM] SMS: OK")
				stage = 19
				time.sleep(1)
			else:
				print ("[GSM] Message mismatch: %s" % msg1)
				stage = 6
				time.sleep(1)

		if stage == 19:
			print ("[GSM] GSM setup complete!\n"


def setup_lora():
	print("Hi")

def send_sms(mob, msg):
	print("Hi")

def read_sms():
	print("Hi")

def ctrl_drone():
	print("Hi")







print("\n----------------\nDelivery Drone\n----------------\nby Jack Orton\n\n")

setup_pins()

time.sleep(1)

#result = buff_check(0x00)
#print(result)
#result = buff_check(0x01)
#print(result)
#result = buff_check(0x02)
#print(result)
#result = buff_check(0x03)
#print(result)

setup_gsm()

spi.close()
gpio.cleanup()
