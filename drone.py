#delivery drone by jack orton
#sorry i got bored commenting after a bit

import time
#from time import time
import sys
#import asyncio
import serial
import spidev
import RPi.GPIO as gpio
import random
from geopy import distance
import geopy

from pymavlink import mavutil
import dronekit
#from mavsdk import System
##would have preferred mavsdk but it wouldn't connect properly - probably my fault

#vehicle = System()

#SPI2UART connections
#uart1 = GSM
#uart2 = lora

ss1 = 22 #chip enable pin for spi2uart
gsmint = 18 #interupt pin from gsm to notify of sms
m0 = 16 #M0 pin on lora module
m1 = 15 #M1 pin on lora module

bufflen = [0, 0]
spi = spidev.SpiDev()

smsrec = 0
#vehicle = 0

def setup_pins():

	print("Initiate GPIO and SPI...")

	gpio.setmode(gpio.BOARD) #use real pin numbers for gpio pins

	gpio.setup(gsmint, gpio.IN, pull_up_down=gpio.PUD_UP)
	gpio.add_event_detect(gsmint, gpio.FALLING, callback = detect_sms, bouncetime = 90)

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

	
setup_pins()
time.sleep(!)
	
print("[DRONE] Connect to drone")
vehicle = dronekit.connect('/dev/serial0', wait_ready=True, baud=57600)
print ("[DRONE] Connected\n")	
	
	
	
	
	
	
	
	
	
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
			print("[GSM|SMS] Attempt SMS mode...")
			msg = "AT+CMGF=1\n"
			msg = list(bytearray(msg.encode()))

			buff_send(0x00, msg)
			stage = 1
			time.sleep(2)
			time1 = time.time()


		if stage == 1:
			bufflen = buff_check(0x00)
			if bufflen[0] > 0: #>9 should work
				print("[GSM|SMS] Response detected")
				stage = 2
				#time.sleep(0.2)
			else:
				time.sleep(1)

			if time.time()-time1 > 10:
				print ("[GSM|SMS] Response timeout, retry enter SMS mode")
				if bufflen[0] > 0:
					msg = buff_read(0x00, bufflen[0])
					msg2 = uart_decode(msg)
					print("[GSM|SMS] Timeout resp?: " + msg2)
					stage = 0

		if stage == 2:
			print ("[GSM|SMS] Get Response...")
			msg = buff_read(0x00, bufflen[0])
			msg2 = uart_decode(msg)
			
			tar = ['O','K']

			if set(tar).issubset(set(list(msg2))):
				print ("[GSM|SMS] SMS mode: OK")
				stage = 3
				#time.sleep(0.2)
			else:
				print("[GSM|SMS] SMS mode: FAIL: " + msg2)
				stage = 0
				#time.sleep(0.2)

		if stage == 3:
			print("[GSM|SMS] Input number")
			#sg = "AT+CMGS=\"+447459636932\"\n" #self
			#sg = list(bytearray(sg.encode()))
			#msg = "AT+CMGS=\"3232\"\n" #text STOP to stop promotions
			#msg = "AT+CMGS=\"+447*********\"\n" #ya boi j-dog
			msg = "AT+CMGS=\"" + mob + "\"\n"
			print("texting: " + msg)
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
				print ("[GSM|SMS] Response: number entry fail, retry SMS")
				print(msg2)
				stage = 0
				#time.sleep(0.2)

		if stage == 6:
			print ("[GSM|SMS] Send SMS text data...")
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
			print ("[GSM|SMS] Sent?: %s" % msg2)
			stage = 9
			#time.sleep(0.2)

def read_sms():
	global smsrec
	stage = 0
	recmsg = ""
	while stage < 9:
		if stage == 0:
			#msg = "AT\n"
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
				time.sleep(1)
			else:
				print("[GSM|SMS] SMS mode: FAIL")
				print(msg2)
				stage = 0
				time.sleep(1)
		
		
		if stage == 3:
				print("[GSM] Read SMS...")
				msg = "AT+CMGL=\"REC UNREAD\"\n"
				msg = list(bytearray(msg.encode()))
				
				#print(msg)
				
				buff_send(0x00, msg)

				stage = 4
				time.sleep(2)
				time1 = time.time()

		if stage == 4:
			bufflen = buff_check(0x00)
			if bufflen[0] > 0:
				print ("[GSM] SMS data received")
				stage = 5
				#time.sleep(1)
			else:
				time.sleep(1)

			if time.time() - time1 > 10:
				print ("[GSM] SMS read timout, retry read")
				stage = 0

		if stage == 5:
			recmsg = buff_read(0x00, bufflen[0])
			recmsg = uart_decode(recmsg)
			smsrec = 0
			#print(recmsg)
			
			stage = 6
			time.sleep(1)
		
		if stage == 6:
			print("[GSM|SMS] Wipe SMS")
			msg = "AT+CMGD=4\n"
			msg = list(bytearray(msg.encode()))
			#print(msg)
			buff_send(0x00, msg)
			
			stage = 7
			time.sleep(1)
		
		if stage == 7:
			bufflen = buff_check(0x00)
			if bufflen[0] > 0:
				print ("[GSM|SMS] Response received")
				stage = 8
				#time.sleep(1)
			else:
				time.sleep(1)

			if time.time() - time1 > 10:
				print ("[GSMSMS] SMS delete timout, retry read")
				stage = 6

		if stage == 8:
			msg = buff_read(0x00, bufflen[0])
			#msg = uart_decode(recmsg)
			
			#print(msg)
			
			stage = 9
		
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

	#stage = 20 #########################################################################
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
			
			#send_sms("+447*********", testsms)
			send_sms("+447459636932", testsms)
			
			stage = 15
			time1 = time.time()
			time.sleep(2)
			

		if stage == 15: #wait for text from self
			global smsrec
			if smsrec == 1:
				print("[GSM] SMS received")
				stage = 16
				smsrec = 0
				time.sleep(1)
			else:
				print ("[GSM] Wait SMS...")
				time.sleep(1)


			if time.time() - time1 > 15:
				print ("[GSM] SMS Timout, retry\n")
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

#voltage = 89

#async def batt_check(vehicle):
#	global voltage
#	async for data in vehicle.telemetry.battery():
#		print(f"Batt: {data.remaining_percent}")
#		voltage = data.remaining_percent
		
#async def setup_drone():
	#global vehicle
	#vehicle = System()
def setup_drone():
	print("Setup drone")
	#print("[DRONE] Connect to drone")
	global vehicle
	
	#vehicle = dronekit.connect('/dev/serial0', wait_ready=True, baud=57600)
	#print ("[DRONE] Connected\n")
	#await vehicle.connect(system_address="serial:///dev/serial0:57600")

	#print("[DRONE] Connecting...")
	#async for state in vehicle.core.connection_state():
		#if state.is_connected:
		#	print ("[DRONE] Connected\n")
			#break
	
	#print("wait 20 seconds for data transfer?")
	#time.sleep(20)
	print("[DRONE] pull data")
		
	stage = 0
	connected = 0
	while stage < 10:
		if stage == 0:
			#print("[DRONE] pull batt")
			
			#asyncio.ensure_future(batt_check(vehicle))
			#print(voltage)
			#async for data in vehicle.telemetry.battery():
				#print(f"Batt: {data.voltage_v}")
			#async for data in vehicle.telemetry.health():
			#	print(f"Gyro: {data.is_gyrometer_calibration_ok}")
			#	print(f"Accel: {data.is_accelerometer_calibration_ok}")
			#	print(f"mag: {data.is_magnetomoter_calibration_ok}")
			#async for data in vehicle.telemetry.battery():
				#print(f"Batt: {data.voltage_v}")
				
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
			currgps = [vehicle.location.global_relative_frame.lat, vehicle.location.global_relative_frame.lon]
			satcount = vehicle.gps_0.satellites_visible
			mode = vehicle.mode.name
			print(currgps)
			
			#if vehicle.is_armable: #for some reason vehicle.is_armable always returned False, even if i could arm.
			if currgps[0] != 0 and satcount > 6 and mode == "GUIDED":
				print("[DRONE] Ready to arm\n")
				stage = 10
				connected = 1
			else:
				print("[DRONE] Waiting for gps and GUIDED mode")
				print("[DRONE] Sats: %d" % satcount)
				print("[DRONE] Mode: %s" % mode)
				
				
				#currgps = vehicle.location.global_relative_frame.lat
				#currgps = currgps.split("=")
				#currgps = [float(currgps[1].split(","))[0], float(currgps[2].split(","))[0]]
				#print(currgps)
				#print(type(currgps))
					   
				time.sleep(2)
				
			if time.time() - time1 > 20:
				print("[DRONE] Timout\n")
				connected = 1 ##0
				stage = 10 ##0
	
	#return connected
def condition_yaw(heading, relative=False):
	if relative:
		is_relative=1 #yaw relative to direction of travel
	else:
		is_relative=0 #yaw is an absolute angle
	# create the CONDITION_YAW command using command_long_encode()
	msg = vehicle.message_factory.command_long_encode(
		0, 0,    # target system, target component
		mavutil.mavlink.MAV_CMD_CONDITION_YAW, #command
		0, #confirmation
		heading,    # param 1, yaw in degrees
		0,          # param 2, yaw speed deg/s
		1,          # param 3, direction -1 ccw, 1 cw
		is_relative, # param 4, relative offset 1, absolute angle 0
		0, 0, 0)    # param 5 ~ 7 not used
	# send command to vehicle
	vehicle.send_mavlink(msg)
	
def goto(head, gotoFunction=vehicle.simple_goto):
	currentLocation = (vehicle.location.global_relative_frame.lat, vehicle.location.global_relative_frame.lon)
	move = distance.distance(0.0005)
	new = move.destination(currentLocation, head)
	targps = (new[0], new[1])
	tar_loc = dronekit.LocationGlobalRelative(targps, 3.5)
	#targetLocation=get_location_metres(currentLocation, dNorth, dEast)
	# targetDistance=get_distance_metres(currentLocation, targetLocation)
	gotoFunction(targetLocation)
	
def ctrl_drone(): #main function
	stage = 0 ######0
	pausestage = 0
	running = 1
	custname = ""
	custmob = ""
	targps = (0, 0)
	currgps = (0, 0)
	print("\n[SYSTEM] System Ready... Run main script")
	print("[SYSTEM] Wait for SMS")
	while running == 1:
		
		if vehicle.mode.name != "GUIDED":
			#print("[SYSTEM] NOT IN GUIDED - PAUSE")
			#print(vehicle.mode.name)
			pausestage = stage
			#stage = -1
		if stage == -1 and vehicle.mode.name == "GUIDED":
			print("[SYSTEM] Resume")
			stage = oldstage
		
		if stage == 0:
			if smsrec == 1:
				stage = 1
				time.sleep(1.5)
			else:
				time.sleep(1)
		
		if stage == 1:
			print("[SYSTEM] SMS Received")
			
			msg = list(read_sms())
			msglen = len(msg)
			#print(msg)
			ncount = 0
			ccount = 0
			msgstart = 0
			msgend = 0
			nostart = 0
			noend = 0

			for i in range(msglen):
				if msg[(msglen-1)-i] == '\n':
					ncount = ncount + 1
			
					if ncount == 3:
						msgend = (msglen-1)-i-1
						#print(msgend)

					if ncount == 4:
						msgstart = (msglen-1)-i+1
						#print(msgstart)
			
						
				
				if msg[(msglen-1)-i] == ',':
					ccount = ccount + 1
					
					if ccount == 3:
						noend = (msglen-1)-i-1
						#print(noend)
					
					if ccount == 4:
						nostart = (msglen-1)-i+2
						#print(nostart)
						
			
			custname = ''.join(str(e) for e in msg[msgstart:msgend])
			#custmob = ''.join(str(e) for e in (["\""] + msg[nostart:noend] + ["\""]))
			custmob = ''.join(str(e) for e in (msg[nostart:noend]))
			#custname = str(msg[msgstart:msgend])
			#custmob = str(msg[nostart:noend])
			
			if len(custname) == 0 or len(custmob) == 0:
				print("[SYSTEM] Failed to grab cust details")
				stage = 0
				time.sleep(1)
			else:
				stage = 2
			
			print(custname)
			print(custmob)

		if stage == 2:
			#msg = "Hi, " + custname ". We currently have: USB Cable. Would you like one? (Yes)"
			msg = "".join(str(e) for e in ["Hi ", custname, ". We currently have: USB Cable. Would you like one? (Yes)"])
			send_sms(custmob, msg)
			print(msg)
			print("[SYSTEM] Wait reply...")
			
			stage = 3
			#running = 0
			
			
		if stage == 3:
			if smsrec == 1:
				stage = 4
				time.sleep(1.5)
			else:
				time.sleep(1)
		
		if stage == 4:
			print("[SYSTEM] SMS Received")
			
			msg = list(read_sms())
			msglen = len(msg)
			#print(msg)
			ncount = 0
			ccount = 0
			msgstart = 0
			msgend = 0
			nostart = 0
			noend = 0
			
			

			for i in range(msglen):
				if msg[(msglen-1)-i] == '\n':
					ncount = ncount + 1
			
					if ncount == 3:
						msgend = (msglen-1)-i-1
						#print(msgend)

					if ncount == 4:
						msgstart = (msglen-1)-i+1
						#print(msgstart)
			
						
				
				if msg[(msglen-1)-i] == ',':
					ccount = ccount + 1
					
					if ccount == 3:
						noend = (msglen-1)-i-1
						#print(noend)
					
					if ccount == 4:
						nostart = (msglen-1)-i+2
						#print(nostart)
						
			
			custmsg = ''.join(str(e) for e in msg[msgstart:msgend])
			reccustmob = ''.join(str(e) for e in (msg[nostart:noend]))
			
			print(custmsg)
			print(reccustmob)
			
			if not reccustmob == custmob:
				print("uh oh")

			if len(custmsg) == 0 or len(reccustmob) == 0:
				print("[SYSTEM] Failed to grab cust details")
				stage = 2 
				time.sleep(1)
			else:
				if custmsg == "Yes" or custmsg == "yes":
					stage = 5
					time.sleep(1)
				else:
					stage = 3
					
		if stage == 5:
			msg = "Send gps lat&lon coords (with space between)" #lazy but im already using commas to separate message out
			send_sms(custmob, msg)
			print(msg)
			print("[SYSTEM] Wait reply...")
			
			stage = 6
		
		if stage == 6:
			if smsrec == 1:
				stage = 7
				time.sleep(1.5)
			else:
				time.sleep(1)
				
		if stage == 7:
			print("[SYSTEM] SMS Received")
			
			msg = list(read_sms())
			msglen = len(msg)
			
			ncount = 0
			ccount = 0
			msgstart = 0
			msgend = 0
			nostart = 0
			noend = 0

			for i in range(msglen):
				if msg[(msglen-1)-i] == '\n':
					ncount = ncount + 1
			
					if ncount == 3:
						msgend = (msglen-1)-i-1
						#print(msgend)

					if ncount == 4:
						msgstart = (msglen-1)-i+1
						#print(msgstart)
			
						
				
				if msg[(msglen-1)-i] == ',':
					ccount = ccount + 1
					
					if ccount == 3:
						noend = (msglen-1)-i-1
						#print(noend)
					
					if ccount == 4:
						nostart = (msglen-1)-i+2
						#print(nostart)
						
			
			gps = ''.join(str(e) for e in msg[msgstart:msgend])
			reccustmob = ''.join(str(e) for e in (msg[nostart:noend]))
			
			print(gps)
			print(reccustmob)
			
			if not reccustmob == custmob:
				print("uh oh")

			if len(gps) == 0 or len(reccustmob) == 0:
				print("[SYSTEM] Failed to grab cust details")
				stage = 2 
				time.sleep(1)
			
			
			targps = (float(gps.split()[0]), float(gps.split()[1]))
			currgps = (vehicle.location.global_relative_frame.lat, vehicle.location.global_relative_frame.lon)

			print(targps)
			print(currgps)
			
					
			dis = distance.distance(currgps,targps).km
			print(dis)
					
			if dis < 0.5:
				print("[SYSTEM] Good target")
				stage = 8
				time.sleep(1)
			else:
				print("[SYSTEM] Big Distance")
				running = 0
				
		if stage == 8:
			alt = 3.5
			print("[DRONE] Arm and takeoff...")
			vehicle.armed = True
			while not vehicle.armed:
       				print ("[DRONE] Arming...")
        			time.sleep(1)
			print ("[DRONE] Armed")
			print ("[DRONE] Takeoff to %fm" % alt)
			vehicle.simple_takeoff(alt) #take off to 3.5m height
			
			while True:
				print ("[DRONE] Altitude: ", vehicle.location.global_relative_frame.alt)
				#Break and return from function just below target altitude.
				if vehicle.location.global_relative_frame.alt>=alt*0.95:
				    print ("[DRONE] Reached target altitude")
				    break
				time.sleep(1)
				
			stage = 9
			
		if stage == 9:
			print("[DRONE] Go to customer GPS:")
			print(targps)
			tar_loc = dronekit.LocationGlobalRelative(targps, 3.5)
			
			condition_yaw(0, False)
			
			vehicle.simple_goto(tar_loc, groundspeed=3)
			remainingDistance = distance.distance((vehicle.location.global_frame.lat, vehicle.location.global_frame.lon),(tar_loc.lat, tar_loc.lon)).m
			
			while remainingDistance>1: 
				remainingDistance = distance.distance((vehicle.location.global_frame.lat, vehicle.location.global_frame.lon),(tar_loc.lat, tar_loc.lon)).m
				print ("Distance to target: %f" % remainingDistance)
				time.sleep(2)
				
			stage = 10
			
		if stage == 10:
			
			
			custmob = "+447914157048"
			
			
			print("[DRONE] At customer GPS")
			print("[SYSTEM] Call Customer")
			print("[GSM] Dial")
			
			msg = "ATD+ " + custmob + ";\n"
			msg = list(bytearray(msg.encode())) #convert message into sendable data
			print(msg)
			buff_send(0x00, msg)

			time1 = time.time() #record time AT sent for timeout
			stage = 11 #move onto next stage
			
			
		if stage == 11: #listen for response from gsm module (we expect 'OK')
			bufflen = buff_check(0x00) #check if data is received on uart0 buffer of spi2uart
			if bufflen[0] > 0: #if buffer has bytes
				print("[GSM] Response detected")
				stage = 12 #move to read buffer
				#time.sleep(1)
			else:
				time.sleep(1) #else wait for response

			if time.time()-time1 > 10: #if no response in 10 seconds, return to stage 0 and resend AT
				print("[GSM] Response timeout, retrying call...")
				stage = 10

		if stage == 12: #read response from module, ensure it is 'OK', otherwise retry
			print("[GSM] Get Reponse...")
			msg = buff_read(0x00, bufflen[0]) #read uart0 received bytes
			msg2 = uart_decode(msg) #decode into text

			if(msg2.strip("\n\r\0") == "OK"): #if expected response from GSM module
				print("[GSM] Response: OK\n[GSM] Call underway")
				stage = 13
				time.sleep(1)
			else: #if response not as expected, then return to stage 0
				print("[GSM] Respone: Call FAIL: %s" % msg2.strip("\n\r\0"))
				print(msg)
				running = 0
		
		if stage == 13:
			print("[GSM] Enable DTMF")
			
			msg = "AT+DDET=1\n"
			msg = list(bytearray(msg.encode())) #convert message into sendable data
			print(msg)
			buff_send(0x00, msg)

			time1 = time.time() #record time AT sent for timeout
			stage = 14 #move onto next stage
			
			
		if stage == 14: #listen for response from gsm module (we expect 'OK')
			bufflen = buff_check(0x00) #check if data is received on uart0 buffer of spi2uart
			if bufflen[0] > 0: #if buffer has bytes
				print("[GSM] Response detected")
				stage = 15 #move to read buffer
				#time.sleep(1)
			else:
				time.sleep(1) #else wait for response

			if time.time()-time1 > 10: #if no response in 10 seconds, return to stage 0 and resend AT
				print("[GSM] Response timeout, retrying DTMF enable...")
				stage = 13

		if stage == 15: #read response from module, ensure it is 'OK', otherwise retry
			print("[GSM] Get Reponse...")
			msg = buff_read(0x00, bufflen[0]) #read uart0 received bytes
			msg2 = uart_decode(msg) #decode into text

			if(msg2.strip("\n\r\0") == "OK"): #if expected response from GSM module
				print("[GSM] Response: OK\n[GSM] DTMF Listening...")
				stage = 16
				time.sleep(1)
			else: #if response not as expected, then return to stage 0
				print("[GSM] Respone: FAIL: %s" % msg2.strip("\n\r\0"))
				print(msg)
				running = 13
				
		if stage == 16:
			dtmf = "100"
			newdtmf = 0
			lastin = time.time()
			while True:
				bufflen = buff_check(0x00) #check if data is received on uart0 buffer of spi2uart
				if bufflen[0] > 0: #if buffer has bytes
					print("[GSM] Response detected")
					msg = buff_read(0x00, bufflen[0]) #read uart0 received bytes
					msg2 = uart_decode(msg) #decode into text
					print(msg2)
					tar = list("+DTMF:")
					if set(tar).issubset(set(list(msg2))):
						print("[GSM] DTMF Input detected")
						msg2 = msg2.split("+DTMF:")
						dtmf = list(msg2[1])[1]
						print("[GSM] PARSED: " + dtmf)
						newdtmf = 1
						lastin = time.time()
					#time.sleep(1)
				else:
					time.sleep(1) #else wait for response
					
				if newdtmf == 1:
					newdtmf = 0
					if dtmf == "2":
						print("Forwards")
						goto(0.5, 0)
						time.sleep(0.5)
					if dtmf == "4":
						print("left")
						goto(0, -0.5)
						time.sleep(0.5)
					if dtmf == "6":
						print("right")
						goto(0, 0.5)
						time.sleep(0.5)
					if dtmf == "8":
						print("back")
						goto(-0.5, 0)
						time.sleep(0.5)
					if dtmf == "#":
						print("DROP TIME BABY")
						stage = 17
						break
				
				if time.time() - lastin > 30:
					print("input timeout")
					stage = 17
					break
					
		if stage == 17:
			print("[GSM] Hangup Call")
			
			msg = "ATH\n"
			msg = list(bytearray(msg.encode())) #convert message into sendable data
			print(msg)
			buff_send(0x00, msg)

			time1 = time.time() #record time AT sent for timeout
			stage = 18 #move onto next stage
			
			
		if stage == 18: #listen for response from gsm module (we expect 'OK')
			bufflen = buff_check(0x00) #check if data is received on uart0 buffer of spi2uart
			if bufflen[0] > 0: #if buffer has bytes
				print("[GSM] Response detected")
				stage = 19 #move to read buffer
				#time.sleep(1)
			else:
				time.sleep(1) #else wait for response

			if time.time()-time1 > 10: #if no response in 10 seconds, return to stage 0 and resend AT
				print("[GSM] Response timeout, retrying Hangup...")
				stage = 17

		if stage == 19: #read response from module, ensure it is 'OK', otherwise retry
			print("[GSM] Get Reponse...")
			msg = buff_read(0x00, bufflen[0]) #read uart0 received bytes
			msg2 = uart_decode(msg) #decode into text

			if(msg2.strip("\n\r\0") == "OK"): #if expected response from GSM module
				print("[GSM] Response: OK")
				stage = 20
				vehicle.mode = "LAND"
				running = 0
				
				
				#time.sleep(1)
			else: #if response not as expected, then return to stage 0
				print("[GSM] Respone: FAIL: %s" % msg2.strip("\n\r\0"))
				print(msg)
				stage = 17
				
			






print("\n----------------\nDelivery Drone\n----------------\nby Jack Orton\n\n")

#setup_pins()
time.sleep(1)


#send_sms("+447*********", "sahh dude - love from ur drone")


setup_gsm()
#setup_lora()
setup_drone()


#drone_ready = 0
#while drone_ready == 0:
#if __name__ == "__main__":
#	asyncio.ensure_future(setup_drone())
#	asyncio.get_event_loop().run_forever()
	
ctrl_drone()

#send_sms("+447*********", "sahh dude - love from ur drone")

spi.close()
gpio.cleanup()
