
import socket
import sys
import time
import hashlib
import _thread
from uuid import getnode as get_mac

# Variáveis
SCOPEID = 8 # scopeID in the end of the line where IPv6 address is
PORT = 5005
NODEID = 0
MESSAGEID = 1
COORDINATES = None
COORDINATES_INDEX = 0
EXIT = None

# Função para enviar uma mensagem para qualquer nó da rede
def sendFunction():

	global MESSAGEID
	global NODEID

	senderSocket = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)

	#destinationAddress = input("\nEnter destination IP Address: ")
	#message = input("Enter the message to send: ")
	
	hashValue = hashlib.blake2s(digest_size=2)
	hashValue.update(hex(get_mac()).encode('utf-8'))
	NODEID = int.from_bytes(hashValue.digest(), byteorder='big')

	destinationAddress = "ff02::0"
	message = str(NODEID) + "|" + str(MESSAGEID) + "|" + getCoordinates()
	MESSAGEID += 1

	print("\nSending message [" + message + "] to " + destinationAddress)

	senderSocket.sendto(message.encode(), (destinationAddress, PORT, 0, SCOPEID))
	print(".\n.\n.\n.\nMessage sent!")

	return


def getCoordinates():

	global COORDINATES_INDEX

	line = COORDINATES[COORDINATES_INDEX].split(" ")

	latitude = line[0]
	longitude = line[1]
	timestamp = line[3]

	COORDINATES_INDEX -= 1

	return "(" + latitude + "," + longitude + ")|" + timestamp


def exitProgram():

	global EXIT

	EXIT = input("\nIf you want to exit, press Enter\n")



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

	_thread.start_new_thread(exitProgram,())

	COORDINATES = fileCoordinates.readlines()
	COORDINATES_INDEX = len(COORDINATES) - 1

	while EXIT is None:
		sendFunction()
		time.sleep(3)

