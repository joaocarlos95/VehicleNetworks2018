
import socket

# Variáveis
SCOPEID = 8 # scopeID in the end of the line where IPv6 address is
PORT = 5005
GROUP = 'ff02::0'



# Função para enviar uma mensagem para qualquer nó da rede
def sendFunction():

	senderSocket = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)

	destinationAddress = input("\nEnter destination IP Address: ")
	message = input("Enter the message to send: ")
	print("\nSending message [" + message + "] to " + destinationAddress)

	senderSocket.sendto(message.encode(), (destinationAddress, PORT, 0, SCOPEID))
	print(".\n.\n.\n.\nMessage sent!")



if __name__ == "__main__":
    sendFunction()