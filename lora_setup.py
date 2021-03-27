#This is in a separate file as the lora modules im using
#(E32-868T20D) needs its M1 and M0 pins pulled to 3v3
#to access settings, but pulled to 0v for nomral operation

#This file is for when M0 and M1 are 3v3, to change settings

import sys
import spidev
import RPi.GPIO as gpio
import time

#SPI2UART
#uart1 = GSM (uart 0x00 in code)
#uart2 = lora (uart 0x01 in code)

ss1 = 22
spi = spidev.SpiDev()

gpio.setmode(bpio.BOARD)
gpio.setup(ss1, gpio.OUT)
gpio.output(ss1, gpio.HIGH)

spi.open(0,0)
spi.max_speed_hz = 50000
spi.no_cs = True

gpio.output(ss1, gpio.LOW)
msg = [0x81]
spi.xfer(msg)
msg = [0x03]
spi.xfer(msg)
gpio.output(ss1, gpio.HIGH)

gpio.output(ss1, gpio.LOW)

msg = [0xC0] #save on shutdown
msg1 = [0x00, 0x00, 0x25, 0x06, 0xc4] #adr (00), adr(00), parit (def) & speed (19200), chan (0x06), opt

set = [0x41]
spi.xfer(set)
set = [len(msg+msg1)
spi.xfer(set)

spi.xfer(msg)
spi.xfer(msg1)
