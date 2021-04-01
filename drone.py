
import time
#from time import time
import sys
import serial
import spidev
import RPi.GPIO as gpio
import random

import dronekit

#SPI2UART
#uart1 = GSM
#uart2 = lora

ss1 = 22 #chip enable pin for spi2uart
gsmint = 18 #interupt pin from gsm to notify of sms
m0 = 16 #M0 pin on lora module
m1 = 15 #M1 pin on lora module

bufflen = [0, 0]
spi = spidev.SpiDev()

smsrec = 0
vehicle = 0

def setup_pins():

	print("Initiate GPIO and SPI...")

	gpio.setmode(gpio.BOARD) #use real pin numbers for gpio pins

	gpio.setup(gsmint, gpio.IN, pull_up_down=gpio.PUD_UP)
	gpio.add_event_detect(gsmint, gpio.FALLING, callback = detect_sms, bouncetime = 50)

	gpio.setup(ss1, gpio.OUT) #set spi2uart chip select pin as output
	gpio.output(ss1, gpio.HIGH) #set spi2uart selector high to disable until needed

	gpio.setup(m0, gpio.OUT)
	gpio.setup(m1, gpio.OUT)
	gpio.output(m0, gpio.HIGH) #enter setup
	gpio.output(m1, gpio.HIGH) #enter setup

	spi.open(0,0) #(bus, device) - spi2uart
	spi.max_speed_hz = 50000 #spi speed, make sure its > all of our spi2uart uarts speeds together
	spi.no_cs = True #we need custom chip select timings so we will use gpio pin control

#	gpio.output(ss1, gpio.LOW) #set low to begin spi communication
#	msg = [0x81] #0x80 = change baud rate, [0x80 | 0x00] = uart 1 baud rate, [0x80 | 0x01] = uart 2...
#	spi.xfer(msg) #tell spi2uart we want to set baud
#	msg = [0x07] #select baud rate (3 = 9600)
#	spi.xfer(msg) #set
#	gpio.output(ss1, gpio.HIGH) #end communication

	bufflen = buff_check(0x00)
	if bufflen[0] > 0:
		print("[SPI2UART] Unexpected buffer content in 0x00, empty...")
		msg = buff_read(0x00, bufflen[0])
		
	bufflen = buff_check(0x01)
	if bufflen[0] > 0:
		print("[SPI2UART] Unexpected buffer content in 0x01, empty...")
		msg = buff_read(0x01, bufflen[0])
		



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
	print("[INTERRUPT] SMS interrupt")
	#print(channel)
	global smsrec
	smsrec = 1

def uart_decode(msg):
	return bytearray(msg).decode()

def send_sms(mob, msgtxt):
	print ("[GSM|SMS] Send SMS")

	stage = 0
	while stage < 9:
		if stage == 0:
			msg = "AT+CMGF=1\n"
			msg = list(bytearray(msg.encode()))

			buff_send(0x00, msg)
			stage = 1
			time1 = time.time()


		if stage == 1:
			bufflen = buff_check(0x00)
			if bufflen[0] > 0:
				print("[GSM|SMS] Response detected")
				stage = 2
				#time.sleep(0.2)
			else:
				time.sleep(1)

			if time.time()-time1 > 10:
				print ("[GSM|SMS] Response timeout, retry enter SMS mode")
				stage = 0

		if stage == 2:
			print ("[GSM|SMS] Get Response...")
			msg = buff_read(0x00, bufflen[0])
			msg2 = uart_decode(msg)

			if msg2.strip("\n\r\0") == "OK":
				print ("[GSM|SMS] SMS mode: OK")
				stage = 3
				#time.sleep(0.2)
			else:
				print("[GSM|SMS] SMS mode: FAIL")
				stage = 0
				#time.sleep(0.2)

		if stage == 3:
			print("[GSM|SMS] Input number")
			sg = "AT+CMGS=\"+447459636932\"\n" #self
			sg = list(bytearray(sg.encode()))
			#msg = "AT+CMGS=\"3232\"\n" #text STOP to stop promotions
			#msg = "AT+CMGS=\"+447914157048\"\n" #j-dog
			msg = "AT+CMGS=\"" + mob + "\"\n"
			msg = list(bytearray(msg.encode()))
			#print("OG:")
			#print(sg)
			#print("New:")
			#print(msg)

			buff_send(0x00, msg)

			time1 = time.time()
			stage = 4

		if stage == 4:
			bufflen = buff_check(0x00)

			if bufflen[0] > 0:
				print ("[GSM|SMS] Response detected")
				stage = 5
				#time.sleep(0.2)
			else:
				time.sleep(1)

			if time.time() - time1 > 10:
				print ("[GSM|SMS] Response timeout, retry SMS")
				stage = 0
				#time.sleep(0.2)

		if stage == 5:
			print ("[GSM|SMS] Get response...")
			msg = buff_read(0x00, bufflen[0])
			msg2 = uart_decode(msg)

			if msg2.strip(" \n\r\0") == ">":
				print ("[GSM|SMS] SMS ready")
				stage = 6
				#time.sleep(0.2)
			else:
				print ("[GSM|SMS] Response: FAIL, retry SMS")
				#print(msg2)
				stage = 0
				#time.sleep(0.2)

		if stage == 6:
			print ("[GSM|SMS] Send SMS...")
			msg = msgtxt
			msg = list(bytearray(msg.encode()))

			buff_send_sms(0x00, msg)
			#time.sleep(1)
			time1 = time.time()
			stage = 7

		if stage == 7:
			bufflen = buff_check(0x00)
			if bufflen[0] > 0:
				print ("[GSM|SMS] Response detected")
				stage = 8
				#time.sleep(0.2)
			else:
				time.sleep(1)

		if stage == 8:
			msg = buff_read(0x00, bufflen[0])
			msg2 = uart_decode(msg)
			#print ("[GSM|SMS] Received: %s" % msg2)
			stage = 9
			#time.sleep(0.2)

def read_sms():
	stage = 0
	recmsg = ""
	while stage < 4:
		if stage == 0:
				print("[GSM] Read SMS...")
				msg = "AT+CMGL=\"REC UNREAD\"\n"
				msg = list(bytearray(msg.encode()))

				buff_send(0x00, msg)

				stage = 2
				time.sleep(3)
				time1 = time.time()

		if stage == 2:
			bufflen = buff_check(0x00)
			if bufflen[0] > 0:
				print ("[GSM] SMS data received")
				stage = 3
				#time.sleep(1)
			else:
				time.sleep(1)

			if time.time() - time1 > 10:
				print ("[GSM] SMS read timout, retry read")
				stage = 0

		if stage == 3:
			recmsg = buff_read(0x00, bufflen[0])
			recmsg = uart_decode(recmsg)
			stage = 4
		
	return recmsg

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

	time.sleep(1)

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
				#time.sleep(1)
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
				#time.sleep(1)
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
				#time.sleep(1)
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
				#time.sleep(1)
			else:
				print ("[GSM] Response: FAIL: %s" % msg2)
				stage = 3
				#time.sleep(1)

		if stage == 6: #send text to self
			print("[GSM] Send test SMS to self...")
			
			send_sms("+447459636932", testsms)
			
			stage = 15
			time.sleep(2)
			

		if stage == 15: #wait for text from self
			global smsrec
			if smsrec == 1:
				print("[GSM] SMS received")
				stage = 16
				smsrec = 0
				#time.sleep(1)
			else:
				print ("[GSM] Wait SMS...")
				time.sleep(1)


			if time.time() - time1 > 15:
				print ("[GSM] SMS Timout, exit")
				stage = 6
				#time.sleep(1)

		if stage == 16:

			#rint ("SMSREC %d" % smsrec)

			msg1 = read_sms()
			
			msg2 = list(msg1)
			tar = list(testsms)

			if set(tar).issubset(set(msg2)):
				print ("[GSM] SMS: OK")
				stage = 19
				#time.sleep(1)
			else:
				print ("[GSM] Message mismatch: %s" % msg1)
				print ("[GSM] Tar SMS: %s" % testsms)
				stage = 6
				#time.sleep(1)

		if stage == 19:
			print ("[GSM] GSM setup complete!\n")


def setup_lora():
	print("Setting up LORA module...")

	stage = 0
	time1 = 0

	gpio.output(m0, gpio.LOW)
	gpio.output(m1, gpio.LOW)

	print("[LORA|SPI2UART] Switch UART 0x01 to 9600")

	gpio.output(ss1, gpio.LOW) #set uart 0x01 to 9600 for lora setup
	msg = [0x81]
	spi.xfer(msg)
	msg = [0x03]
	spi.xfer(msg)
	gpio.output(ss1, gpio.HIGH)

	time.sleep(.2)

	print("[LORA] Enter setup mode")
	gpio.output(m0, gpio.HIGH) #lora set-up mode
	gpio.output(m1, gpio.HIGH)

	time.sleep(.2)

	time1 = time.time()
	while stage < 6:
		if stage == 0:
			print ("[LORA] Send check")
			#m = "\n"
			#n = list(bytearray(m.encode()))
			msg = [0xc3, 0xc3, 0xc3]
			buff_send(0x01, msg)

			stage = 1
			time.sleep(1)
			time1 = time.time()

		if stage == 1:
			bufflen = buff_check(0x01)
			if bufflen[0] > 0:
				print ("[LORA] Response detected")
				stage = 2
				#time.sleep(1)
			else:
				time.sleep(1)

			if time.time() - time1 > 10:
				print ("[LORA] Response timeout, retry")
				stage = 0
				#time.sleep(1)

		if stage == 2:
			print ("[LORA] Get response...")
			msg = buff_read(0x01, bufflen[0])
#			msg1 = uart_decode(msg)
#			hexmsg = [hex(x) for x in msg]
			tar = [195, 69]
			if set(tar).issubset(set(msg)):
				print("[LORA] Response: OK")
				stage = 3
				#time.sleep(1)
			else:
				print("[LORA] Response: FAIL, retry")
				print (msg)
				stage = 0
				#time.sleep(1)

		if stage == 3:
			print ("[LORA] Send settings")

			msg = [0xc0, 0x00, 0x00, 0x25, 0x06, 0xc4]
			buff_send(0x01, msg)

			stage = 4
			time1 = time.time()

			time.sleep(1)

		if stage == 4:
			bufflen = buff_check(0x01)
			if bufflen[0] > 0:
				print("[LORA] Response detected")
				stage = 5
				#time.sleep(1)
			else:
				time.sleep(1)

			if time.time() - time1 > 10:
				print("[LORA] Settings timeout, retry")
				stage = 10
				#time.sleep(1)

		if stage == 5:
			print ("[LORA] Get response...")
			msg = buff_read(0x01, bufflen[0])
			tar = [0xc0, 0x00, 0x00, 0x25, 0x06, 0xc4]
#			print(msg)
#			hx = [hex(x) for x in msg]
#			print(hx)
			if msg == tar:
				print("[LORA] Settings OK")
				stage = 6
			else:
				print("LORA] Settings FAIL, retry")
				stage = 3

		#time.sleep(.2)
		print("[LORA] Exit setup")
		gpio.output(m0, gpio.LOW)
		gpio.output(m1, gpio.LOW)

		print("[LORA|SPI2UART] Switch UART 0x01 to 19200")
		gpio.output(ss1, gpio.LOW)
		msg = [0x81]
		spi.xfer(msg)
		msg = [0x04]
		spi.xfer(msg)
		gpio.output(ss1, gpio.HIGH)
		time.sleep(.2)
		
		print("[LORA] LORA Ssetup complete!\n")


def setup_drone():
	global vehicle
	print("Setup drone")
	print("[DRONE] Connect to drone")
	vehicle = dronekit.connect('/dev/serial0', wait_ready=True, baud=57600)
	print ("[DRONE] Connected\n")
	stage = 0
	connected = 0
	while stage < 10:
		if stage == 0:
			print( "Autopilot Firmware version: %s" % vehicle.version)
			#print( "Autopilot capabilities (supports ftp): %s" % vehicle.capabilities.ftp)
			#print( "Global Location: %s" % vehicle.location.global_frame)
			print( vehicle.location.global_relative_frame)
			#print( "Local Location: %s" % vehicle.location.local_frame)    #NED
			print( vehicle.attitude)
			print( "Velocity: %s" % vehicle.velocity)
			print( vehicle.gps_0)
			print( "Groundspeed: %s" % vehicle.groundspeed)
			#print( "Airspeed: %s" % vehicle.airspeed)
			#print( "Gimbal status: %s" % vehicle.gimbal)
			print( vehicle.battery)
			print( "EKF OK?: %s" % vehicle.ekf_ok)
			print( "Last Heartbeat: %s" % vehicle.last_heartbeat)
			#print( "Rangefinder: %s" % vehicle.rangefinder)
			#print( "Rangefinder distance: %s" % vehicle.rangefinder.distance)
			#print( "Rangefinder voltage: %s" % vehicle.rangefinder.voltage)
			print( "Heading: %s" % vehicle.heading)
			print( "Is Armable?: %s" % vehicle.is_armable)
			print( "System status: %s" % vehicle.system_status.state)
			print( "Mode: %s" % vehicle.mode.name)    # settable
			print( "Armed: %s" % vehicle.armed)    # settable
			
			print("\n[DRONE] Wait until arming ready")
			stage = 1
			time1 = time.time()
		
		if stage == 1:
			if vehicle.is_armable:
				print("[DRONE] Ready to arm\n")
				stage = 10
				connected = 1
			else:
				print("[DRONE] Waiting for armable")
				time.sleep(2)
				
			if time.time() - time1 > 20:
				print("[DRONE] Timout\n")
				connected = 1 ##0
				stage = 10 ##0
	
	return connected

def ctrl_drone(): #main function
	stage = 0
	running = 1
	
	print("\n[SYSTEM] System Ready... Run main script")
	print("[SYSTEM] Wait for SMS")
	while running == 1:
		if stage == 0:
			if smsrec == 1:
				stage = 1
			else:
				time.sleep(1)
		
		if stage == 1:
			print("[SYSTEM] SMS Received")
			
			msg = list(read_sms())

			print(msg)
			running = 0







print("\n----------------\nDelivery Drone\n----------------\nby Jack Orton\n\n")

setup_pins()
time.sleep(1)

setup_gsm()
#setup_lora()

#drone_ready = 0
#while drone_ready == 0:
#	drone_ready = setup_drone()
	
ctrl_drone()

#send_sms("+447914157048", "sahh dude - love from ur drone")

spi.close()
gpio.cleanup()
