
import socket
import sys
import time

# Variáveis
SCOPEID = 8 # scopeID in the end of the line where IPv6 address is (what defines the interface)
PORT = 5005
NODEID = 2
MESSAGEID = 1


# Função para enviar uma mensagem para qualquer nó da rede
def sendFunction():

	global MESSAGEID

	senderSocket = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)

	#destinationAddress = input("\nEnter destination IP Address: ")
	#message = input("Enter the message to send: ")
	
	destinationAddress = "ff02::0"
	message = str(NODEID) + "|" + str(MESSAGEID) + "|" + getCoordinates() + "|" + getTimeStamp()
	MESSAGEID += 1
	
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