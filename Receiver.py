
import socket
import struct
import datetime
import time

# Variáveis
SCOPEID = 8 # scopeID in the end of the line where IPv6 address is
PORT = 5005
GROUP = 'ff02::0'

table = []



#####################################################################################
# Função para receber mensagens de qualquer nó da rede								#
#####################################################################################

def mainFunction():

	receiverSocket = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)

	groupBin = socket.inet_pton(socket.AF_INET6, 'ff02::0')
	mReq = groupBin + struct.pack('@I', SCOPEID)

	receiverSocket.bind(('', PORT))
	receiverSocket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_JOIN_GROUP, mReq)

	while True:
		message, payload = receiverSocket.recvfrom(1024)

		message = message.decode().split("|")

		nodeID = message[0]
		messageID = message[1]
		position = message[2]
		timeOfPosition = int(float(message[3]))
		timeOfPosition = datetime.datetime.fromtimestamp(timeOfPosition).strftime('%H:%M:%S')
		currentTime = datetime.datetime.fromtimestamp(time.time()).strftime('%H:%M:%S')

		updateTable(nodeID, messageID, position, timeOfPosition, currentTime)
		printTable()



#####################################################################################
# Função para fazer update da Neighbor table										#
#####################################################################################

def updateTable(nodeID, messageID, position, timeOfPosition, currentTime):

	global table

	# Table is empty
	if not table:
		appendTable(nodeID, messageID, position, timeOfPosition, currentTime)
		return

	i = findNode(nodeID, currentTime)
	if i == None:
		appendTable(nodeID, messageID, position, timeOfPosition, currentTime)
	else:
		table[i][1] = messageID
		table[i][2] = "newPosition"
		table[i][3] = timeOfPosition
		table[i][4] = currentTime



#####################################################################################
# Função para encontrar um nó na Neighbor table										#
#####################################################################################

def findNode(nodeID, currentTime):

	global table
	index = None

	i = 0
	for entry in table:
		if entry[0] == nodeID:
			index = i
		updateTimer(i, currentTime)
		i += 1
	return index



#####################################################################################
# Função para inserir um novo elemento na Neighbor table							#
#####################################################################################

def appendTable(nodeID, messageID, position, timeOfPosition, currentTime):

	global table

	table.append([nodeID, messageID, position, timeOfPosition, currentTime])



#####################################################################################
# Função para inserir um novo elemento na Neighbor table							#
#####################################################################################

def printTable():

	global table

	for entry in table:
		print(entry)
	print("\n")



#####################################################################################
# Função para fazer update do timer e remover a entrada caso o limite deste passe	#
#####################################################################################

def updateTimer(index, currentTime):

	global table

	previousTime = table[index][4]
	print(str(table[index][0]) + " - " + str(previousTime) + " - " + str(currentTime) + " - " + str(datetime.datetime.strptime(currentTime, '%H:%M:%S') - datetime.datetime.strptime(previousTime, '%H:%M:%S')))
	previousTime = datetime.datetime.strptime(previousTime, '%H:%M:%S')
	currentTime = datetime.datetime.strptime(currentTime, '%H:%M:%S')
	if (currentTime - previousTime).seconds >= 60:
		table.remove(table[index])



#####################################################################################
# Main																				#
#####################################################################################
if __name__ == "__main__":
 
    mainFunction()


