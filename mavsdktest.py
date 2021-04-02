import asyncio
from mavsdk import System

print ("hello 1")
#tester(1)

drone = System()

def tester(inpu):
	print ("test %d" % inpu)

tester(2)

async def drone_ctl():
	global drone
	print ("\nasync begin")
	print ("connect drone")
	tester(3)
	#drone = System()
	await drone.connect(system_address="serial:///dev/serial0:57600")

	print("connecting...")
	async for state in  drone.core.connection_state():
		if state.is_connected:
			print("fuk yah")
			break

tester(4)

if __name__ == "__main__":
	loop = asyncio.get_event_loop()
	loop.run_until_complete(drone_ctl())
	tester(5)

tester(6)
