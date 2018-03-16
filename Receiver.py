
import socket
import struct

# Variáveis
SCOPEID = 8 # scopeID in the end of the line where IPv6 address is
PORT = 5005
GROUP = 'ff02::0'


# Função para receber mensagens de qualquer nó da rede
def mainFunction():

	receiverSocket = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)

	groupBin = socket.inet_pton(socket.AF_INET6, 'ff02::0')
	mReq = groupBin + struct.pack('@I', SCOPEID)

	receiverSocket.bind(('', PORT))
	receiverSocket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_JOIN_GROUP, mReq)

	while True:
		message, payload = receiverSocket.recvfrom(1024)
		#print(receiverSocket.recvfrom(1024))
		print("\nReceived message [" + message.decode() + "] from " + payload[0][:payload[0].find("%")])



if __name__ == "__main__":
    mainFunction()


