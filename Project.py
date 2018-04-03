
import socket
import struct
import datetime
import time
import _thread
import sys
import hashlib
from uuid import getnode as get_mac

# Variáveis Sender
SCOPEID = 8 # scopeID in the end of the line where IPv6 address is
PORT = 5005
GROUP = 'ff02::0'
TIMOUT = 20

# Variáveis Receiver
PORT = 5005
NODEID = 0
MESSAGEID = 1
COORDINATES = None
COORDINATES_INDEX = 0
INPUTMESSAGE = None

table = []



#################################################################################################
# Função para enviar mensagens para todos os nós da rede (Sender)								#
#################################################################################################

def sendFunction():

	global MESSAGEID
	global NODEID

	senderSocket = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)

	hashValue = hashlib.blake2s(digest_size=2)
	hashValue.update(hex(get_mac()).encode('utf-8'))
	NODEID = int.from_bytes(hashValue.digest(), byteorder='big')

	destinationAddress = "ff02::0"

	while COORDINATES_INDEX >= 0:
	
		message = str(NODEID) + "|" + str(MESSAGEID) + "|" + getCoordinates()

		printMessages("Sending message [" + message + "] to " + destinationAddress)

		senderSocket.sendto(message.encode(), (destinationAddress, PORT, 0, SCOPEID))
		printMessages(".\n.\n.\n.\nMessage sent!\n")

		MESSAGEID += 1
		time.sleep(3)

	return



#################################################################################################
# Função para receber mensagens de qualquer nó da rede (Receiver)								#
#################################################################################################

def receiveFunction():

	receiverSocket = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)

	groupBin = socket.inet_pton(socket.AF_INET6, 'ff02::0')
	mReq = groupBin + struct.pack('@I', SCOPEID)

	receiverSocket.bind(('', PORT))
	receiverSocket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_JOIN_GROUP, mReq)

	while True:
		message, payload = receiverSocket.recvfrom(1024)

		message = message.decode().split("|")

		print("\nMessage Received from " + str(payload[0].split("%")[0]))
		print("Message: " + str(message))

		nodeID = message[0]
		messageID = message[1]
		position = message[2]
		timeOfPosition = int(float(message[3]))
		timeOfPosition = datetime.datetime.fromtimestamp(timeOfPosition).strftime('%H:%M:%S')

		if (differentMessageID(nodeID, messageID)):
			updateTable(nodeID, messageID, position, timeOfPosition, 0)
			printTable()



#################################################################################################
# Função para verificar se a mensagem que recebeu é nova (Receiver)								#
#################################################################################################

def differentMessageID(nodeID, messageID):

	index = findNode(nodeID)

	if index != None and int(table[index][1]) >= int(messageID):
		return False

	return True



#################################################################################################
# Função para fazer update da Neighbor table (Receiver)											#
#################################################################################################

def updateTable(nodeID, messageID, position, timeOfPosition, timer):

	global table

	# Table is empty
	if not table:
		appendTable(nodeID, messageID, position, timeOfPosition, timer)
		_thread.start_new_thread(updateTimerThread,())
		return		

	i = findNode(nodeID)
	if i == None:
		appendTable(nodeID, messageID, position, timeOfPosition, timer)
	else:
		table[i][1] = messageID
		table[i][2] = position
		table[i][3] = timeOfPosition
		table[i][4] = 0



#################################################################################################
# Função para encontrar um nó na Neighbor table	(Receiver)										#
#################################################################################################

def findNode(nodeID):

	global table

	i = 0
	for entry in table:
		if entry[0] == nodeID:
			return i
		i += 1
	return None



#################################################################################################
# Função para inserir um novo elemento na Neighbor table (Receiver)								#
#################################################################################################

def appendTable(nodeID, messageID, position, timeOfPosition, timer):

	global table

	table.append([nodeID, messageID, position, timeOfPosition, timer])


#################################################################################################
# Função para inserir um novo elemento na Neighbor table (Receiver)								#
#################################################################################################

def printTable():

	global table

	print("\nTable:")
	for entry in table:
		print(entry)



#################################################################################################
# Função para fazer update do timer e remover a entrada caso o limite deste passe (Receiver)	#
#################################################################################################

def updateTimerThread():

	global table

	while len(table) != 0:
		index = 0
		for entry in table:
			if entry[4] == TIMOUT:
				table.remove(table[index])
				printTable()
			else:
				table[index][4] += 1
			index += 1
		time.sleep(1)



#################################################################################################
# Função para obter as coordenadas provenientes de um ficheiro de texto	(Sender)				#
#################################################################################################

def getCoordinates():

	global COORDINATES_INDEX

	line = COORDINATES[COORDINATES_INDEX].split(" ")

	latitude = line[0]
	longitude = line[1]
	timestamp = line[3].replace("\n", "")

	COORDINATES_INDEX -= 1

	return "(" + latitude + "," + longitude + ")|" + timestamp



#################################################################################################
# Função para verificar o input introduzido pelo utilizador - Test/Normal Mode; Exit (Sender)	#
#################################################################################################

def inputMessages():

	global INPUTMESSAGE

	print("\nFor exit, type \"Exit\".")
	print("For test mode type \"Test\".")
	print("For normal mode type \"Normal\".\n")
	
	while True:
		INPUTMESSAGE = input()


#################################################################################################
# Função para fazer imprimir conteúdo quando o Test Mode está activo							#
#################################################################################################

def printMessages(message):

	if INPUTMESSAGE == "Test":
		print(message)



#####################################################################################
# Main																				#
#####################################################################################
if __name__ == "__main__":

	while True:

		number = input("Choose a number for coordinate file (between 1 and 5) or 0 to exit: ")
		if number == "0":
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
	
	while INPUTMESSAGE != "Exit":
		pass

	sys.exit()


