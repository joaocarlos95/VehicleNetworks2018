
import sys, socket, struct
import datetime, time
import _thread, threading
import Crypto.Hash.MD5 as MD5
import json, serial

from uuid import getnode
from math import sin, cos, sqrt, atan2, radians, degrees
from Crypto.PublicKey import RSA


# Sender Variables
SCOPEID = 8															# scopeID in the end of the line where IPv6 address is
SOURCE_PORT = 5004
DESTINATION_PORT = 5005
DESTINATION_ADDRESS = 'ff02::0'
TIMOUT_TABLE = 20


# Receiver Variables
COORDINATES = None
COORDINATES_INDEX = 0
INPUT_MESSAGE = None
ALARM = False


messageHeader = {
	'protocolType': None,											# 0 = Beacon | 1 = DEN | 2 = CA | 3 = Unicast
	'stationID': 0,													# Station ID
	# 'stationID': hex(getnode()),									# MAC Address
	'messageID': 0, 												# Message ID
}
beaconBody = {
	'stationPosition': None,										# Station Position
	'stationPositionTime': None,									# Sation Position Time
}
messageBodyDEN = {
	'actionID': [messageHeader['stationID'], 0], 					# Node source | nr Repetitions
	'eventTime': None,												# Time at event was gathered
	'eventPosition': None,											# Motorcycle's Position
	'regionOfInterest': 1,											# 1 Km
	'expiryTime': 1,												# 1 second
	'stationType': 1,												# RSU = 0 | OBU = 1
	'eventType': 0,													# 0 = theft
	'eventSpeed': None,												# Motorcycle's Speed
	'eventPositionHeading': None, 									# Motorcycle's Direction
	'traces': [],													# Motorcycle Trace
}
messageBodyUnicast = {
	'nextDestinationMAC': None,
	'finalDestinationMAC': 4,
	'finalDestinationPosition': [1, 2],
	'eventPosition': None,											# Motorcycle's Position
	'eventTime': None,												# Time at event was gathered
}
security = { 'signature': None }


global serialPort 
serialPort = serial.Serial('/dev/tty.HOLUX_M-1200E-SPPslave')
table = []
tableMutex = threading.Lock()



class Station:

	def __init__(self, stationID, messageID, stationPosition, stationPositionTime, isNeighbour, timer):
		self.stationID = stationID
		self.messageID = messageID
		self.stationPosition = stationPosition
		self.stationPositionTime = stationPositionTime
		self.isNeighbour = isNeighbour
		self.timer = timer



#################################################################################################
# Function to send messages to all nodes in range												#
#################################################################################################

def sendMessages(alarmActive):

	global messageHeader
	global beaconBody
	global messageBodyDEN
	global messageBodyUnicast
	global security

	while COORDINATES_INDEX >= 0:

		# Alarm actived - Send message to owner and message to everyone
		if (alarmActive):
			updateNodeParameters()

			# Send message to someone (final destination or intermediarie)
			if messageBodyUnicast['nextDestinationMAC'] != messageHeader['stationID']:
				messageHeader['protocolType'] = 3
				setSecurity(messageBodyUnicast)
				message = [messageHeader, messageBodyUnicast, security]
				send(message, DESTINATION_ADDRESS)

			messageHeader['protocolType'] = 1
			setSecurity(messageBodyDEN)
			message = [messageHeader, messageBodyDEN, security]
			send(message, DESTINATION_ADDRESS)
		
		# Alarm desactivated - Send only beacon
		else:
			stationPosition, stationPositionTime = getCurrentPosition()

			messageHeader['protocolType'] = 0
			beaconBody['stationPosition'] = stationPosition
			beaconBody['stationPositionTime'] = stationPositionTime
			message = [messageHeader, beaconBody, None]
			send(message, DESTINATION_ADDRESS)

		time.sleep(500 / 100) 
	return

#################################################################################################
# Function to receive messages from all nodes in range											#
#################################################################################################

def receiveMessages():

	global messageHeader

	receiverSocket = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
	groupBin = socket.inet_pton(socket.AF_INET6, 'ff02::0')
	mReq = groupBin + struct.pack('@I', SCOPEID)
	receiverSocket.bind(('', SOURCE_PORT))
	receiverSocket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_JOIN_GROUP, mReq)

	while True:
		
		message, payload = receiverSocket.recvfrom(2048)
	
		messageReceivedHeader, messageReceivedBody, messageReceivedSecurity = json.loads(message.decode('utf-8'))

		protocolType = messageReceivedHeader['protocolType']
		stationID = messageReceivedHeader['stationID']
		messageID = messageReceivedHeader['messageID']

		if (isNewMessage(stationID, messageID) and messageHeader['stationID'] != stationID) and \
			protocolType != 1:
			
			printMessages("\n--------------------")
			printMessages("Message Received from " + str(payload[0].split("%")[0]))
			printMessages("Message: " + str(json.loads(message.decode('utf-8'))))
	
			if protocolType == 0:
				updateTable(stationID, messageID, messageReceivedBody, 1, 0)

			elif protocolType == 3:
				# Find nearest Node to destination
				messageReceivedBody['nextDestinationMAC'] = nearestNode(messageReceivedBody['finalDestinationPosition'])
				# Nearest Node is destination node or someone in between
				if messageReceivedBody['nextDestinationMAC'] != messageHeader['stationID']:
					setSecurity(messageReceivedBody)
					message = [protocolType, messageReceivedBody, security]
					send(message, DESTINATION_ADDRESS)
	return


#################################################################################################
# Function for sending messages 																#
#################################################################################################

def send(message, destination):

	global messageHeader

	senderSocket = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
	
	messageEncoded = json.dumps(message).encode('utf-8')
	
	printMessages("\n++++++++++++++++++++")
	printMessages("Sending message [" + str(message) + "] to " + destination)

	senderSocket.sendto(messageEncoded, (destination, DESTINATION_PORT, 0, SCOPEID))
	messageHeader['messageID'] += 1
	return


#################################################################################################
# Function for set security field in message													#
#################################################################################################

def setSecurity(payload):

	global security
	
	with open('moto.key') as f: key_text = f.read()
	key = RSA.importKey(key_text)
	f.close()
	hash = MD5.new(json.dumps(payload).encode('utf-8')).digest()

	security['signature'] = key.sign(hash, '')
	return


#################################################################################################
# Function for updating node data (position, speed and direction)								#
#################################################################################################

def updateNodeParameters():

	global messageBodyUnicast
	global messageBodyDEN

	newCoordinates, newDetectionTime = getCurrentPosition()

	messageBodyDEN['eventTime'] = newDetectionTime
	messageBodyDEN['eventPosition'] = newCoordinates

	messageBodyUnicast['nextDestinationMAC'] = nearestNode(messageBodyUnicast['finalDestinationPosition'])
	messageBodyUnicast['eventPosition'] = newCoordinates
	messageBodyUnicast['eventTime'] = newDetectionTime

	if not messageBodyDEN['traces']:
		messageBodyDEN['traces'].append([newCoordinates, newDetectionTime])

	elif len(messageBodyDEN['traces']) == 5:
		messageBodyDEN['traces'].pop(0)
		messageBodyDEN['traces'].append([newCoordinates, newDetectionTime])
		
		oldCoordinates = messageBodyDEN['traces'][3][0]
		oldDetectionTime = messageBodyDEN['traces'][3][1]
		messageBodyDEN['eventPositionHeading'] = getBearing(oldCoordinates, newCoordinates)
		messageBodyDEN['eventSpeed'] = getSpeed(oldCoordinates, oldDetectionTime, newCoordinates, newDetectionTime)

	else:
		messageBodyDEN['traces'].append([newCoordinates, newDetectionTime])

		previousCoordinates = len(messageBodyDEN['traces']) - 2
		oldCoordinates = messageBodyDEN['traces'][previousCoordinates][0]
		oldDetectionTime = messageBodyDEN['traces'][previousCoordinates][1]
		messageBodyDEN['eventPositionHeading'] = getBearing(oldCoordinates, newCoordinates)
		messageBodyDEN['eventSpeed'] = getSpeed(oldCoordinates, oldDetectionTime, newCoordinates, newDetectionTime)
	return


#################################################################################################
# Function for getting the current position of the node 										#
#################################################################################################

def getCurrentPositionList():

	global COORDINATES_INDEX
	
	line = COORDINATES[COORDINATES_INDEX].split(" ")
	
	coordinates = [ float(line[0]), float(line[1]) ]
	detectionTime = float(line[3].replace("\n", ""))
	
	COORDINATES_INDEX -= 1

	return coordinates, detectionTime

def getCurrentPosition():

	serialLine = serialPort.readline().decode('utf-8').split(",")

	if(serialLine[0] == "$GPGGA" ):
		latitude, longitude = convertDMStoDD(serialLine[2], serialLine[3], serialLine[4], serialLine[5])
		coordinates = [latitude, longitude]
		detectionTime = time.time()	
		return coordinates, detectionTime
	
	else:
		return getCurrentPosition()


#################################################################################################
# Function for getting the direction of the node 												#
#################################################################################################

def getBearing(oldCoordinates, newCoordinates):

	oldLatitude = radians(oldCoordinates[0])
	oldLongitude = radians(oldCoordinates[1])
	newLatitude = radians(newCoordinates[0])
	newLongitude = radians(newCoordinates[1])

	differenceLongitude = newLongitude - oldLongitude

	x = sin(differenceLongitude) * cos(newLatitude)
	y = cos(oldLatitude) * sin(newLatitude) - (sin(oldLatitude) * cos(newLatitude) * cos(differenceLongitude))

	return round(((degrees(atan2(x, y)) + 360) % 360), 2)


#################################################################################################
# Function for getting the speed of the node 													#
#################################################################################################

def getSpeed(oldCoordinates, oldDetectionTime, newCoordinates, newDetectionTime):

	oldLatitude = radians(oldCoordinates[0])
	oldLongitude = radians(oldCoordinates[1])
	newLatitude = radians(newCoordinates[0])
	newLongitude = radians(newCoordinates[1])

	distance = getDistance(oldCoordinates, newCoordinates)
	differenceTime = newDetectionTime - oldDetectionTime 

	return round((distance * 3600 / differenceTime), 3)


#################################################################################################
# Function for getting the direction of two nodes 												#
#################################################################################################

def getDistance(oldCoordinates, newCoordinates):

	radius = 6373.0

	oldLatitude = radians(oldCoordinates[0])
	oldLongitude = radians(oldCoordinates[1])
	newLatitude = radians(newCoordinates[0])
	newLongitude = radians(newCoordinates[1])

	differenceLatitude = newLatitude - oldLatitude
	differenceLongitude = newLongitude - oldLongitude

	x = sin(differenceLatitude / 2)**2 + cos(oldLatitude) * cos(oldLatitude) * sin(differenceLongitude / 2)**2
	y = 2 * atan2(sqrt(x), sqrt(1 - x))

	return abs(radius * y)


#################################################################################################
# Function for finding the nearest node to destination											#
#################################################################################################

def nearestNode(destinationPosition):

	node = messageHeader['stationID']
	distanceToDestination = getDistance(getCurrentPosition()[0], destinationPosition)
	
	for entry in table:
		distance = getDistance(entry.stationPosition, destinationPosition)
		if distanceToDestination == None:
			node = entry.stationID
			distanceToDestination = distance
		elif distanceToDestination > distance:
			node = entry.stationID
			distanceToDestination = distance
	
	return node


#################################################################################################
# Function to verify if new message is new 														#
#################################################################################################

def isNewMessage(stationID, messageID):

	index = findNode(stationID)
	if index != None and table[index].messageID >= messageID:
		return False
	return True


#################################################################################################
# Function to find a node in table 																#
#################################################################################################

def findNode(stationID):

	global table

	index = 0
	for entry in table:
		if entry.stationID == stationID:
			return index
		index += 1
	return None


#################################################################################################
# Function to update Neighbor table																#
#################################################################################################

def updateTable(stationID, messageID, messageReceivedBody, isNeighbour, timer):

	global table
	global tableMutex

	stationPosition = messageReceivedBody['stationPosition']
	stationPositionTime = messageReceivedBody['stationPositionTime']

	tableMutex.acquire()

	# Table is empty - Add node
	if not table:
		station = Station(stationID, messageID, stationPosition, stationPositionTime, isNeighbour, timer)
		table.append(station)
		_thread.start_new_thread(updateTimerThread,())
		tableMutex.release()
		return		

	# Table has nodes - Find node or add new one
	i = findNode(stationID)
	if i == None:
		station = Station(stationID, messageID, stationPosition, stationPositionTime, isNeighbour, timer)
		table.append(station)
	else:
		table[i].messageID = messageID
		table[i].stationPosition = stationPosition
		table[i].stationPositionTime = stationPositionTime
		table[i].isNeighbour = isNeighbour
		table[i].timer = timer

	tableMutex.release()
	return


#################################################################################################
# Function to update the timer and remove the entry if the limit passes 						#
#################################################################################################

def updateTimerThread():

	global table

	while len(table) != 0:
		index = 0
		for entry in table:
			if entry.timer == TIMOUT_TABLE:
				del table[index]				
				printTable()
			else:
				entry.timer += 1
				printTable()
			index += 1
		time.sleep(1)
	return


#################################################################################################
# Function to print the table																	#
#################################################################################################

def printTable():

	global table

	if INPUT_MESSAGE == "Test":
		print("\nTable:")
		for entry in table:
			stationPositionTime = datetime.datetime.fromtimestamp(entry.stationPositionTime).strftime('%H:%M:%S')
			print("[ " + str(entry.stationID) + " | " + str(entry.messageID) + " | " + 
				str(entry.stationPosition) + " | " + str(stationPositionTime) + " | " +
				str(entry.timer) + " ]\n")
	return


#################################################################################################
# Function to check the input entered by the user 												#
#################################################################################################

def inputMessages():

	global INPUT_MESSAGE
	global ALARM

	print("\nFor exit, type \"Exit\".")
	print("For test mode type \"Test\".")
	print("For normal mode type \"Normal\".\n")
	print("For alarm mode type \"Alarm\".\n")
	
	while True:
		userInput = input()
		if userInput == "Alarm":
			ALARM = True
			_thread.start_new_thread(sendMessages,(True,))
		else:
			INPUT_MESSAGE = userInput
	return


#################################################################################################
# Funcao para fazer imprimir conteudo quando o Test Mode está activo							#
#################################################################################################

def printMessages(message):

	if INPUT_MESSAGE == "Test":
		print(message)
	return


#################################################################################################
# GPS converter from DMS format to DD format													#
#################################################################################################

def convertDMStoDD(latitude, YY, longitude, XX):
	
	print(latitude, YY, longitude, XX)
	latitude = degreesToDecimal(float(latitude))
	if YY == 'S':
		latitude *= -1
	
	longitude = degreesToDecimal(float(longitude))
	if XX == 'W':
		longitude *= -1
	
	return latitude, longitude


#################################################################################################
# Converte degrees to decimal 																	#
#################################################################################################

def degreesToDecimal(value):
	
	D = int(value/100)
	M = int(str(value).split(".")[0][-2:])
	S = float(str(value).split(".")[1])/100
	
	return D + float(M)/60 + float(S)/3600
	

#####################################################################################
# Main																				#
#####################################################################################
if __name__ == "__main__":

	while True:

		number = input("Choose a number for coordinate file (between 1 and 5) or \"Exit\" to exit the program: ")
		if number == "Exit":
			sys.exit()

		try:
		    fileCoordinates = open("./Coordinates/Coordinate" + number + ".txt")
		    break
		except (OSError, IOError) as e:
			print("\nYou must choose a number between 1 and 5")

	_thread.start_new_thread(inputMessages,())

	COORDINATES = fileCoordinates.readlines()
	COORDINATES_INDEX = len(COORDINATES) - 1

	_thread.start_new_thread(sendMessages,(False,))
	_thread.start_new_thread(receiveMessages,())
	
	while INPUT_MESSAGE != "Exit":
		pass

	sys.exit()
