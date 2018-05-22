
import socket
import struct
import datetime, time
import _thread, threading
import sys
import hashlib
import json
from uuid import getnode
from math import sin, cos, sqrt, atan2, radians, degrees
import Crypto.Hash.MD5 as MD5
from Crypto.PublicKey import RSA

# Sender Variables
SCOPEID = 5															# scopeID in the end of the line where IPv6 address is
SOURCE_PORT = 5004
DESTINATION_PORT = 5005
DESTINATION_ADDRESS = 'ff02::0'
TIMOUT = 20

# Receiver Variables
COORDINATES = None
COORDINATES_INDEX = 0
INPUT_MESSAGE = None
ALARM = False
TIME_SENT_MESSAGES = 5												# Time between sent messages

messageHeader = {
	'protocolType': None,											# 0 = Beacon | 1 = DEN | 2 = CA
	'stationID': 0,													# Station ID
	# 'stationID': hex(getnode()),									# MAC Address
	'messageID': 0, 												# Message ID
}

beaconBody = {
	'stationPosition': None,										# Station Position
	'stationPositionTime': None,									# Sation Position Time
}

messageBodyDEN = {
	'actionID': [messageHeader['stationID'], 0], 					# Node source | nrº Repetitions
	'eventTime': None,												# Time at event was gathered
	'messageGenerationTime': None,									# Time of message generation
	'eventPosition': None,											# Motorcycle's Position
	'regionOfInterest': 1,											# 1 Km
	'expiryTime': 1,												# 1 second
	'stationType': 1,												# RSU = 0 | OBU = 1
	'eventType': 0,													# 0 = theft
	'eventSpeed': None,												# Motorcycle's Speed
	'eventPositionHeading': None, 									# Motorcycle's Direction
	'traces': [],													# Motorcycle Trace
}

security = {
	'signature': None
}


	
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

def sendFunction(alarmActive):

	global messageHeader
	global beaconBody
	global messageBodyDEN
	global security

	senderSocket = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)

	while COORDINATES_INDEX >= 0:

		if (alarmActive):

			messageHeader['protocolType'] = 1
			messageBodyDEN = updateNodeParameters(messageBodyDEN)
			messageBodyDEN['messageGenerationTime'] = time.time()

			nrRepetitions = messageBodyDEN['actionID'][1]

			if nrRepetitions == 255:
				messageBodyDEN['actionID'][1] = 0
			else:
				messageBodyDEN['actionID'][1] += 1

			security['signature'] = hash(messageBodyDEN)
			message = [messageHeader, messageBodyDEN, security]

		else:
			stationPosition, stationPositionTime = getCurrentPosition()

			messageHeader['protocolType'] = 0
			beaconBody['stationPosition'] = stationPosition
			beaconBody['stationPositionTime'] = stationPositionTime
			message = [messageHeader, beaconBody, None]

		messageEncoded = json.dumps(message).encode('utf-8')

		printMessages("\n++++++++++++++++++++")
		printMessages("Sending message [" + str(message) + "] to " + DESTINATION_ADDRESS)

		senderSocket.sendto(messageEncoded, (DESTINATION_ADDRESS, DESTINATION_PORT, 0, SCOPEID))

		messageHeader['messageID'] += 1
		time.sleep(5)
		#time.sleep(500 / 1000) 

	return



#################################################################################################
# Function for updating node data (position, speed and direction)								#
#################################################################################################

def updateNodeParameters(messageBodyDEN):

	newCoordinates, newDetectionTime = getCurrentPosition()

	messageBodyDEN['eventTime'] = newDetectionTime
	messageBodyDEN['eventPosition'] = newCoordinates

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

	return messageBodyDEN


def getCurrentPosition():

	global COORDINATES_INDEX
	
	line = COORDINATES[COORDINATES_INDEX].split(" ")
	
	coordinates = [ float(line[0]), float(line[1]) ]
	detectionTime = float(line[3].replace("\n", ""))
	
	COORDINATES_INDEX -= 1

	return coordinates, detectionTime


def getBearing(oldCoordinates, newCoordinates):

	oldLatitude = radians(oldCoordinates[0])
	oldLongitude = radians(oldCoordinates[1])
	newLatitude = radians(newCoordinates[0])
	newLongitude = radians(newCoordinates[1])

	differenceLongitude = newLongitude - oldLongitude

	x = sin(differenceLongitude) * cos(newLatitude)
	y = cos(oldLatitude) * sin(newLatitude) - (sin(oldLatitude) * cos(newLatitude) * cos(differenceLongitude))

	return round(((degrees(atan2(x, y)) + 360) % 360), 2)


def getSpeed(oldCoordinates, oldDetectionTime, newCoordinates, newDetectionTime):

	oldLatitude = radians(oldCoordinates[0])
	oldLongitude = radians(oldCoordinates[1])
	newLatitude = radians(newCoordinates[0])
	newLongitude = radians(newCoordinates[1])

	distance = getDistance(oldCoordinates, newCoordinates)
	differenceTime = newDetectionTime - oldDetectionTime 

	return round((distance * 3600 / differenceTime), 3)


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
# Função para receber mensagens de qualquer nó da rede (Receiver)								#
#################################################################################################

def receiveFunction():

	global messageHeader

	receiverSocket = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)

	groupBin = socket.inet_pton(socket.AF_INET6, 'ff02::0')
	mReq = groupBin + struct.pack('@I', SCOPEID)

	receiverSocket.bind(('', SOURCE_PORT))
	receiverSocket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_JOIN_GROUP, mReq)

	while True:
		message, payload = receiverSocket.recvfrom(1024)

		messageDecoded = json.loads(message.decode('utf-8'))
		messageReceivedHeader = messageDecoded[0]
		messageReceivedBody = messageDecoded[1]

		printMessages("\n--------------------")
		printMessages("Message Received from " + str(payload[0].split("%")[0]))
		printMessages("Message: " + str(messageDecoded))

		receivedStationID = messageReceivedHeader['stationID']
		receivedMessageID = messageReceivedHeader['messageID']
		receivedStationPosition = messageReceivedHeader['stationPosition']
		receivedStationPositionTime = messageReceivedHeader['stationPositionTime']

		if (isNewMessage(receivedStationID, receivedMessageID) and (messageHeader['stationID'] != receivedStationID)):
			updateTable(receivedStationID, receivedMessageID, receivedStationPosition, receivedStationPositionTime, 0)
		

def isNewMessage(stationID, messageID):

	index = findNode(stationID)

	if index != None and table[index].messageID >= messageID:
		return False

	return True


def findNode(stationID):

	global table

	i = 0
	for entry in table:
		if entry.stationID == stationID:
			return i
		i += 1
	return None



#################################################################################################
# Function to update Neighbor table																#
#################################################################################################

def updateTable(stationID, messageID, stationPosition, stationPositionTime, isNeighbour, timer):

	global table
	global tableMutex

	tableMutex.acquire()

	if not table:
		station = Station(stationID, messageID, stationPosition, stationPositionTime, isNeighbour, timer)
		table.append(station)
		_thread.start_new_thread(updateTimerThread,())
		return		

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



#################################################################################################
# Function to update the timer and remove the entry if the limit passes 						#
#################################################################################################

def updateTimerThread():

	global table

	while len(table) != 0:
		index = 0
		for entry in table:
			if entry.timer == TIMOUT:
				del table[index]				
				printTable()
			else:
				entry.timer += 1
				printTable()
			index += 1
		time.sleep(1)



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
			_thread.start_new_thread(sendFunction,(True,))
		else:
			INPUT_MESSAGE = userInput


#################################################################################################
# Função para fazer imprimir conteúdo quando o Test Mode está activo							#
#################################################################################################

def printMessages(message):

	if INPUT_MESSAGE == "Test":
		print(message)



#################################################################################################
# Função para fazer imprimir conteúdo quando o Test Mode está activo							#
#################################################################################################

def hash(payload):

	with open('moto.key') as f: key_text = f.read()
	key = RSA.importKey(key_text)
	f.close()

	hash = MD5.new(json.dumps(payload).encode('utf-8')).digest()
	print(hash)

	return key.sign(hash, '')


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

	_thread.start_new_thread(sendFunction,(False,))
	_thread.start_new_thread(receiveFunction,())
	
	while INPUT_MESSAGE != "Exit":
		pass

	sys.exit()


