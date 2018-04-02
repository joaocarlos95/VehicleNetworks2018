
import socket
import struct
import datetime
import time
import _thread

# Variáveis
SCOPEID = 8 # scopeID in the end of the line where IPv6 address is
PORT = 5005
GROUP = 'ff02::0'
TIMOUT = 20

table = []
#tableThread = []



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



#####################################################################################
# Função para verificar se a mensagem que recebeu é nova							#
#####################################################################################

def differentMessageID(nodeID, messageID):

	index = findNode(nodeID)

	print(messageID )
	if index != None and int(table[index][1]) >= int(messageID):
		return False

	return True



#####################################################################################
# Função para fazer update da Neighbor table										#
#####################################################################################

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



#####################################################################################
# Função para encontrar um nó na Neighbor table										#
#####################################################################################

def findNode(nodeID):

	global table

	i = 0
	for entry in table:
		if entry[0] == nodeID:
			return i
		i += 1
	return None



#####################################################################################
# Função para inserir um novo elemento na Neighbor table							#
#####################################################################################

def appendTable(nodeID, messageID, position, timeOfPosition, timer):

	global table

	table.append([nodeID, messageID, position, timeOfPosition, timer])


#####################################################################################
# Função para inserir um novo elemento na Neighbor table							#
#####################################################################################

def printTable():

	global table

	print("\nTable:")
	for entry in table:
		print(entry)



#####################################################################################
# Função para fazer update do timer e remover a entrada caso o limite deste passe	#
#####################################################################################

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


#####################################################################################
# Main																				#
#####################################################################################
if __name__ == "__main__":
 
    mainFunction()


