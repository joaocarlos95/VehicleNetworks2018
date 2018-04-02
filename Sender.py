
import socket
import sys
import time
import hashlib
from uuid import getnode as get_mac

# Variáveis
SCOPEID = 8 # scopeID in the end of the line where IPv6 address is
PORT = 5005
NODEID = hex(get_mac()).encode('utf-8')
MESSAGEID = 1


# Função para enviar uma mensagem para qualquer nó da rede
def sendFunction():

	global MESSAGEID
	global NODEID

	senderSocket = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)

	#destinationAddress = input("\nEnter destination IP Address: ")
	#message = input("Enter the message to send: ")
	
	destinationAddress = "ff02::0"
	message = str(NODEID) + "|" + str(MESSAGEID) + "|" + getCoordinates() + "|" + getTimeStamp()
	MESSAGEID += 1

	hashValue = hashlib.blake2s(digest_size=2)
	hashValue.update(NODEID)

	NODEID = int.from_bytes(hashValue.digest(), byteorder='big')

	print("\nSending message [" + message + "] to " + destinationAddress)

	senderSocket.sendto(message.encode(), (destinationAddress, PORT, 0, SCOPEID))
	print(".\n.\n.\n.\nMessage sent!")

	return


def getCoordinates():
	return "Coordinates"



def getTimeStamp():
	return str(time.time())



if __name__ == "__main__":

	while True:
		exit = input("Exit? Y or N: ")
		if exit == "Y":
			sys.exit()
		else:
			sendFunction()

