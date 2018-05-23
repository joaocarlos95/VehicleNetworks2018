
import sys, socket, struct
import datetime, time, random
import _thread, threading
import Crypto.Hash.MD5 as MD5
import json, requests, serial

from uuid import getnode
from math import sin, cos, sqrt, atan2, radians, degrees
from Crypto.PublicKey import RSA


# Sender Variables
SCOPEID = 8 														# scopeID in the end of the line where IPv6 address is
SOURCE_PORT = 5006
DESTINATION_PORT = 5007
DESTINATION_ADDRESS = 'ff02::0'
TIMOUT_TABLE = 20
TIMOUT_BUFFER = 20
INTER_CONECTION = True

# Receiver Variables
COORDINATES = None
COORDINATES_INDEX = 0
INPUT_MESSAGE = None

messageHeader = {
	'protocolType': None,											# 0 = Beacon | 1 = DEN | 2 = CA | 3 = Unicast
	'stationID': 2,													# Station ID
	# 'stationID': hex(getnode()),									# MAC Address
	'messageID': 0, 												# Message ID
}
beaconBody = {
	'stationPosition': None,										# Station Position
	'stationPositionTime': None,									# Sation Position Time
}
security = { 'signature': None }


global serialPort 
serialPort = serial.Serial('/dev/tty.HOLUX_M-1200E-SPPslave')
table = []
nodeBuffer = []
tableMutex = threading.Lock()
bufferMutex = threading.Lock()



class Station:
	def __init__(self, stationID, messageID, stationPosition, stationPositionTime, isNeighbour, timer):
		self.stationID = stationID
		self.messageID = messageID
		self.stationPosition = stationPosition
		self.stationPositionTime = stationPositionTime
		self.isNeighbour = isNeighbour
		self.timer = timer


class MessageBuffer:	
	def __init__(self, stationID, eventTime, protocolType, messageBody, security, timer):
		self.protocolType = protocolType
		self.stationID = stationID
		self.eventTime = eventTime
		self.messageBody = messageBody
		self.security = security
		self.timer = timer



#################################################################################################
# Function to send messages to all nodes in range												#
#################################################################################################

def sendMessages():

	global messageHeader
	global beaconBody
	global messageBodyDEN
	global messageBodyUnicast
	global security

	while COORDINATES_INDEX >= 0:

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

		if (isNewMessage(stationID, messageID) and messageHeader['stationID'] != stationID):
			
			printMessages("\n--------------------")
			printMessages("Message Received from " + str(payload[0].split("%")[0]))
			printMessages("Message: " + str(json.loads(message.decode('utf-8'))))
	
			if protocolType == 0:
				updateTable(stationID, messageID, messageReceivedBody, 1, 0)

			elif protocolType == 1:
				
				if INTER_CONECTION and messageReceivedBody['eventType'] == 0:
					updateDatabase(messageReceivedBody, messageReceivedSecurity)

			elif protocolType == 3:
				# Find nearest Node to destination
				messageReceivedBody['nextDestinationMAC'] = nearestNode(messageReceivedBody['finalDestinationPosition'])
				# Nearest Node is someone between destination and actual node
				if messageReceivedBody['nextDestinationMAC'] != messageHeader['stationID'] and \
					messageReceivedBody['nextDestinationMAC'] != messageReceivedBody['finalDestinationPosition']:
					setSecurity(messageReceivedBody)
					message = [protocolType, messageReceivedBody, security]
					send(message, DESTINATION_ADDRESS)
				# Nearst Node is destination
				elif messageReceivedBody['nextDestinationMAC'] != messageHeader['stationID'] and \
					messageReceivedBody['nextDestinationMAC'] == messageReceivedBody['finalDestinationPosition']:
					setSecurity(messageReceivedBody)
					message = [protocolType, messageReceivedBody, security]
					send(message, DESTINATION_ADDRESS)
				# Nearst Node is the owner
				elif messageReceivedBody['nextDestinationMAC'] == messageHeader['stationID'] and \
					messageReceivedBody['nextDestinationMAC'] == messageReceivedBody['finalDestinationPosition']:
					print("Mota Roubada!!!!! Posição - " + str(messageReceivedBody['eventPosition']) + \
						" | Tempo - " + str(messageReceivedBody['eventTime']))
				# Nears Node is actual node
				else:
					appendBuffer(protocolType, messageReceivedBody, None)
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
# Function to verify if message's time is expired												#
#################################################################################################

def timeExpired(expiryTime, positionTime):
	return expiryTime + positionTime > time.time()


#################################################################################################
# Function to verify if message's limit distance has reached									#
#################################################################################################

def distancePassed(regionOfInterest, eventPosition, currentPosition):
	return regionOfInterest < getDistance(eventPosition, currentPosition)


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
		_thread.start_new_thread(updateTimerThread,(False,))
		tableMutex.release()
		dispatchBuffer()
		return		

	# Table has nodes - Find node or add new one
	i = findNode(stationID)
	if i == None:
		station = Station(stationID, messageID, stationPosition, stationPositionTime, isNeighbour, timer)
		table.append(station)
		dispatchBuffer()
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

def updateTimerThread(isBuffer):

	global table
	global nodeBuffer

	if isBuffer:
		while len(nodeBuffer) != 0:
			index = 0
			for message in nodeBuffer:
				if message.protocolType == 3:
					if message.timer == TIMOUT_BUFFER:
						del nodeBuffer[index]				
					else:
						message.timer += 1
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
			print("[ " + str(entry.stationID) + " | " + str(entry.messageID) + " | " + str(entry.stationPosition) + " | " + 
				str(stationPositionTime) + " | " + str(entry.timer) + " ]\n")
	return


#################################################################################################
# Function to get the coordinates 																#
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
	return


#################################################################################################
# Function to update database 																	#
#################################################################################################

def updateDatabase(messageReceivedBody, messageSecurity):

	databaseSocket = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)

	with open('moto.key') as f1: key_text2 = f1.read()
	key2 = RSA.importKey(key_text2)
	f1.close()

	pubkey = key2.publickey()
	hash = MD5.new(json.dumps(messageReceivedBody).encode('utf-8')).digest()
	
	if pubkey.verify(hash, messageSecurity.get("signature")):
		stolenVehicle = {
			'stationID': messageReceivedBody['actionID'][0],
			'eventPositionLatitude': messageReceivedBody['eventPosition'][0],
			'eventPositionLongitude': messageReceivedBody['eventPosition'][1],
			'eventTime': messageReceivedBody['eventTime'],
			'eventSpeed': messageReceivedBody['eventSpeed'],
			'eventPositionHeading': messageReceivedBody['eventPositionHeading'],
		}
		messageEncoded = json.dumps(stolenVehicle).encode('utf-8')

		printMessages("\n++++++++++++++++++++")
		printMessages("Sending message [" + str(stolenVehicle) + "] to " + str("MotoAlarm"))

		requests.post("http://motoalarm.cf/v1/Api.php?apicall=updateposition", data=stolenVehicle)
	return


#################################################################################################
# Function to append a message in the buffer													#
#################################################################################################

def appendBuffer(protocolType, messageBody, security):

	global nodeBuffer
	global bufferMutex
	
	bufferMutex.acquire()

	eventTime = messageBody['eventTime']
	if protocolType == 3:
		stationID = messageBody['finalDestinationMAC']
	
	# Buffer empty
	if not nodeBuffer:
		messageBuffer = MessageBuffer(stationID, eventTime, protocolType, messageBody, security, 0)
		nodeBuffer.append(messageBuffer)
		_thread.start_new_thread(updateTimerThread,(True,))
		bufferMutex.release()
		return
	# Buffer has something
	else:
		index = findInBuffer(protocolType, eventTime)
		# Message isn't in buffer
		if index == None:
			messageBuffer = MessageBuffer(stationID, eventTime, protocolType, messageBody, security, 0)
			nodeBuffer.append(messageBuffer)
		# Message is in buffer and new message is newer
		elif eventTime > nodeBuffer[index].eventTime:
			del nodeBuffer[index]
			messageBuffer = MessageBuffer(stationID, eventTime, protocolType, messageBody, security, 0)
			nodeBuffer.append(messageBuffer)
	
	bufferMutex.release()
	return


#################################################################################################
# Function to find message by station ID in buffer												#
#################################################################################################

def findInBuffer(protocolType, stationID):

	index = 0
	for message in nodeBuffer:
		if message.stationID == stationID and message.protocolType == protocolType:
			return index
		index += 1
	return None


#################################################################################################
# Function to dispatch all messages in buffer													#
#################################################################################################

def dispatchBuffer():

	global nodeBuffer
	global messageHeader

	while len(nodeBuffer) != 0:
		for message in nodeBuffer:
			if message.protocolType == 3:
				# Find nearest Node to destination
				message.messageBody['nextDestinationMAC'] = nearestNode(message.messageBody['finalDestinationPosition'])
				# Nearest Node is someone between destination and actual node
				if message.messageBody['nextDestinationMAC'] != messageHeader['stationID'] and \
					message.messageBody['nextDestinationMAC'] != message.messageBody['finalDestinationPosition']:
					setSecurity(message.messageBody)
					message = [message.protocolType, message.messageBody, security]
					send(message, DESTINATION_ADDRESS)
				# Nearst Node is destination
				elif message.messageBody['nextDestinationMAC'] != messageHeader['stationID'] and \
					message.messageBody['nextDestinationMAC'] == message.messageBody['finalDestinationPosition']:
					setSecurity(message.messageBody)
					message = [message.protocolType, message.messageBody, security]
					send(message, DESTINATION_ADDRESS)
	return


#################################################################################################
# GPS converter from DMS format to DD format													#
#################################################################################################

def convertDMStoDD(latitude, YY, longitude, XX):
	
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

	_thread.start_new_thread(sendMessages,())
	_thread.start_new_thread(receiveMessages,())
	
	while INPUT_MESSAGE != "Exit":
		pass

	sys.exit()


