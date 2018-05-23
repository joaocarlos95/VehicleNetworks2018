import serial, time

def convertDMStoDD(lat,N,lng,W):
	mylist=[lat,N,lng,W]
	lat = degreesToDecimal(float(mylist[0]))
	if mylist[1] == 'S':
		lat *= -1
	lon = degreesToDecimal(float(mylist[2]))
	if mylist[3] == 'W':
		lon *= -1
	return lat, lon

def degreesToDecimal(value):
	d = int(value/100)
	m = int(str(value).split(".")[0][-2:])
	s = float(str(value).split(".")[1])/100
	dd = dms_to_dd(d, m, s)
	return dd

def dms_to_dd(d, m, s):
	dd = d + float(m)/60 + float(s)/3600
	return dd

#ser = serial.Serial('/dev/ttyACM0', 9600)
ser= serial.Serial('/dev/tty.HOLUX_M-1200E-SPPslave')


while 1:
	serial_line = ser.readline()
	A=serial_line.split(",")
	if(A[0] == "$GPGGA" ):
		#print(serial_line)
		print(convertDMStoDD(A[2],A[3],A[4],A[5]))
		print()

ser.close()





