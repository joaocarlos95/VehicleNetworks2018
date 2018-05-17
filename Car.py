
import socket
import struct
import datetime, time
import _thread, threading
import sys
import hashlib
import json
import random
from uuid import getnode
from math import sin, cos, sqrt, atan2, radians

# Sender Variables
SCOPEID = 8 														# scopeID in the end of the line where IPv6 address is
SOURCE_PORT = 5005
DESTINATION_PORT = 5006
DESTINATION_ADDRESS = 'ff02::0'
TIMOUT_TABLE = 20
TIMOUT_BUFFER = 20

# Receiver Variables
COORDINATES = None
COORDINATES_INDEX = 0
INPUT_MESSAGE = None
TIME_SENT_MESSAGES = 5												# Time between sent messages

messageHeader = {
	'protocolType': None,											# 0 = Beacon | 1 = DEN | 2 = CA
	'stationID': 1,													# Station ID
	# 'stationID': hex(getnode()),									# MAC Address
	'messageID': 0, 												# Message ID
}

beaconBody = {
	'stationPosition': None,										# Station Position
	'stationPositionTime': None,									# Sation Position Time
}

table = []
nodeBuffer = []
tableMutex = threading.Lock()



class Station:

	def __init__(self, stationID, messageID, stationPosition, stationPositionTime, isNeighbour, timer):
		self.stationID = stationID
		self.messageID = messageID
		self.stationPosition = stationPosition
		self.stationPositionTime = stationPositionTime
		self.isNeighbour = isNeighbour
		self.timer = timer

class MessageBuffer:
	
	def __init__(protocolType, messageBodyDEN, timer):
		self.protocolType = protocolType
		self.messageBodyDEN = messageBodyDEN
		self.timer = timer
		


#################################################################################################
# Function to send messages to all nodes in range												#
#################################################################################################

def sendFunction():

	global messageHeader
	global beaconBody
	global messageBodyDEN

	senderSocket = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)

	while COORDINATES_INDEX >= 0:

		stationPosition, stationPositionTime = getCurrentPosition()

		messageHeader['protocolType'] = 0
		beaconBody['stationPosition'] = stationPosition
		beaconBody['stationPositionTime'] = stationPositionTime
		message = [messageHeader, beaconBody]

		messageEncoded = json.dumps(message).encode('utf-8')

		printMessages("\n++++++++++++++++++++")
		printMessages("Sending message [" + str(message) + "] to " + DESTINATION_ADDRESS)

		senderSocket.sendto(messageEncoded, (DESTINATION_ADDRESS, DESTINATION_PORT, 0, SCOPEID))

		messageHeader['messageID'] += 1
		time.sleep(5)
		#time.sleep(500 / 1000) 
		#time.sleep((500 + random.randint(0, 100)) / 1000) 
		
	return



#################################################################################################
# Function for forwarding messages 																#
#################################################################################################

def forwardMessage(message, destinationAddress):

	global messageHeader

	senderSocket = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)

	messageEncoded = json.dumps(message).encode('utf-8')

	printMessages("\n++++++++++++++++++++")
	printMessages("Forwarding message [" + str(message) + "] to " + destinationAddress)
	senderSocket.sendto(messageEncoded, (destinationAddress, DESTINATION_PORT, 0, SCOPEID))

	messageHeader['messageID'] += 1
	return


def timeExpired(expiryTime, positionTime):

	return expiryTime + positionTime > time.time()


def distancePassed(regionOfInterest, eventPosition, currentPosition):

	return regionOfInterest < getDistance(eventPosition, currentPosition)


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

		stationID = messageReceivedHeader['stationID']
		messageID = messageReceivedHeader['messageID']

		printMessages("\n--------------------")
		printMessages("Message Received from " + str(payload[0].split("%")[0]))
		printMessages("Message: " + str(messageDecoded))

		if (isNewMessage(stationID, messageID) and messageHeader['stationID'] != stationID):
			
			if messageReceivedHeader['protocolType'] == 0:
				stationPosition = messageReceivedBody['stationPosition']
				stationPositionTime = messageReceivedBody['stationPositionTime']
				updateTable(stationID, messageID, stationPosition, stationPositionTime, 1, 0)
		
			elif messageReceivedHeader['protocolType'] == 1:

				expiryTime = messageReceivedBody['expiryTime']
				eventTime = messageReceivedBody['eventTime']
				regionOfInterest = messageReceivedBody['regionOfInterest']
				eventPosition = messageReceivedBody['eventPosition']

				if True:
					messageHeader['protocolType'] = 1
					message = [messageHeader, messageReceivedBody]
					forwardMessage(message, 'ff02::0')

				#currentPosition, newDetectionTime = getCurrentPosition()
			
				#if !(timeExpired(expiryTime, eventTime) and 
				#	distancePassed(regionOfInterest, eventPosition, currentPosition)):
				#	toTransmit = retransmitProbability(regionOfInterest, eventPosition, currentPosition)
				#	if toTransmit != None and toTransmit <= random.randint(0,100):
				#
				#		messageHeader['protocolType'] = 1
				#		message = [messageHeader, messageReceivedBody]
				#		forwardMessage(message, 'ff02::0')


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


def retransmitProbability(regionOfInterest, eventPosition, currentPosition, protocolType, messageBody):

	sizeTable = len(table)

	if sizeTable == 0:
		appendBuffer(protocolType, messageBody)
		return None
	else:
		x = 100 / sizeTable
		distanceEvent = getDistance(eventPosition, currentPosition)
		return (distanceEvent / regionOfInterest) * x

def appendBuffer(protocolType, messageBody):

	global nodeBuffer

	messageBuffer = MessageBuffer(protocolType, messageBodyDEN, 0)
	nodeBuffer.append(messageBuffer)
	_thread.start_new_thread(updateTimerThread,(True,))

def dispatchBuffer():

	global nodeBuffer
	global messageHeader

	while len(nodeBuffer) != 0:
		for entry in nodeBuffer:
			messageHeader['protocolType'] = entry.protocolType
			messageBody = entry.messageBody
			message = [messageHeader, messageBody]
			forwardMessage(message, 'ff02::0')



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
		_thread.start_new_thread(updateTimerThread,(False,))
		tableMutex.release()
		dispatchBuffer()
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

def updateTimerThread(isBuffer):

	global table
	global nodeBuffer

	if isBuffer:
		while len(nodeBuffer) != 0:
			index = 0
			for entry in nodeBuffer:
				if entry.timer == TIMOUT_BUFFER:
					del nodeBuffer[index]				
				else:
					entry.timer += 1
				index += 1
			time.sleep(1)

	else:
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



#################################################################################################
# Function to print the table																	#
#################################################################################################

def printTable():

	global table

	if INPUT_MESSAGE == "Test":

		print("\nTable:")
		for entry in table:
			stationPositionTime = datetime.datetime.fromtimestamp(entry.stationPositionTime).strftime('%H:%M:%S')
			print("[ " + str(entry.stationID) + " | " + str(entry.messageID) + " | " + str(entry.stationPosition) + " | " + 
				str(stationPositionTime) + " | " + str(entry.timer) + " ]\n")



#################################################################################################
# Function to get the coordinates 																#
#################################################################################################

def getCurrentPosition():

	global COORDINATES_INDEX
	
	line = COORDINATES[COORDINATES_INDEX].split(" ")
	
	coordinates = [ float(line[0]), float(line[1]) ]
	detectionTime = float(line[3].replace("\n", ""))
	
	COORDINATES_INDEX -= 1

	return coordinates, detectionTime



#################################################################################################
# Function to check the input entered by the user 												#
#################################################################################################

def inputMessages():

	global INPUT_MESSAGE

	print("\nFor exit, type \"Exit\".")
	print("For test mode type \"Test\".")
	print("For normal mode type \"Normal\".\n")
	
	while True:
		INPUT_MESSAGE = input()



#################################################################################################
# Função para fazer imprimir conteúdo quando o Test Mode está activo							#
#################################################################################################

def printMessages(message):

	if INPUT_MESSAGE == "Test":
		print(message)



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

	_thread.start_new_thread(sendFunction,())
	_thread.start_new_thread(receiveFunction,())
	
	while INPUT_MESSAGE != "Exit":
		pass

	sys.exit()

