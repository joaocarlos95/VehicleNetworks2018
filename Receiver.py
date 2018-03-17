
import socket
import struct
import datetime

# Variáveis
SCOPEID = 8 # scopeID in the end of the line where IPv6 address is
PORT = 5005
GROUP = 'ff02::0'

table = []



#################################################################################
# Função para receber mensagens de qualquer nó da rede							#
#################################################################################

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

		updateTable(nodeID, messageID, position, timeOfPosition)
		printTable()
		#print("\nReceived message [" + message.decode() + "] from " + payload[0][:payload[0].find("%")])



#################################################################################
# Função para fazer update da Neighbor table									#
#################################################################################

def updateTable(nodeID, messageID, position, timeOfPosition):

	global table

	# Table is empty
	if not table:
		appendTable(nodeID, messageID, position, timeOfPosition)
		return

	i = findNode(nodeID)
	if i == None:
		appendTable(nodeID, messageID, position, timeOfPosition)
		return
	else:
		table[i][1] = messageID
		table[i][2] = "newPosition"
		table[i][3] = timeOfPosition



#################################################################################
# Função para encontrar um nó na Neighbor table									#
#################################################################################

def findNode(nodeID):

	global table

	i = 0
	for entry in table:
		if entry[0] == nodeID:
			return i
		i += 1
	return None



#################################################################################
# Função para inserir um novo elemento na Neighbor table						#
#################################################################################

def appendTable(nodeID, messageID, position, timeOfPosition):

	global table

	table.append([nodeID, messageID, position, timeOfPosition])



#################################################################################
# Função para inserir um novo elemento na Neighbor table						#
#################################################################################

def printTable():

	global table

	for entry in table:
		print(entry)
	print("\n")



#################################################################################
# Main																			#
#################################################################################
if __name__ == "__main__":
    mainFunction()


