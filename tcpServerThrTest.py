#coding:utf-8
import socket
from time import ctime
import threading
import time

#监听
#最开始用在重写南网配网测试，串口圆环监听程序。		
class TcpSer:
	def __init__(self,HOST='0.0.0.0',PORT=1234):
		self.HOST = HOST
		self.PORT = PORT
		self.ADDR = (self.HOST,self.PORT)
		self.connectCount = 10
		self.countSock = 0
		self.exitFlag = False
		self.tcpSerSock = False
		self.socketList = []
		self.start()

	def start(self):
		if self.listen() == False:
			self.exitFlag = True
			return False

		self.exitFlag = False
		t = threading.Thread(target=self.accept,args=())
		t.start()
		return True
	
	def listen(self):
		print('Listening:',self.HOST,self.PORT)
		try:
			self.tcpSerSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			self.tcpSerSock.bind(self.ADDR)
			self.tcpSerSock.listen(self.connectCount)
			return True
		except Exception as e:
			print('Error in listen:',e)
			return False
	
	def accept(self):
		self.tcpSerSock.settimeout(0.1)
		while self.exitFlag == False:
			try:
				clientSock, addr = self.tcpSerSock.accept()
				clientSock.setblocking(0)
				self.socketList.append([clientSock,addr])
				self.countSock = self.countSock + 1
			except socket.timeout as e:
				continue
			except Exception as e:
				return False

	def setExitFlag(self):
		self.exitFlag = True

	def getExitFlag(self):
		return self.exitFlag

	def getSocket(self):
		if len(self.socketList) != 0:
			theFirstSocket = self.socketList[0]
			del self.socketList[0]
			return theFirstSocket
		else:
			return False

	def close(self):
		#print('Stop Listen:',self.HOST,self.PORT)
		self.tcpSerSock.close()
		self.setExitFlag()

class baseSR:
	def __init__(self,socket):
		self.socket = socket
		self.bufsize = 1024
	
	def settimeout(self,timeout):
		try:
			self.socket.settimeout(timeout)
			return True
		except Exception as e:
			return False
	
	def rr(self):
		try:
			recvData = self.socket.recv(self.bufsize)
			if recvData:
				return recvData
			return False
		except socket.timeout as e:
			return ''
		except Exception as e:
			return False
	
	def ss(self,data):
		try:
			self.socket.send(data)
			return True
		except Exception as e:
			#print('Error baseSR ss:',e)
			return False	
			
	def close(self):
		try:
			self.socket.close()
			return True
		except Exception as e:
			print('Error in baseSR close:',e)
			return False
			
#=======================================================================			
class tcpServer(baseSR):
	def __init__(self,socket,addr,recvList,sendList):
		self.socket = socket
		self.addr = addr
		self.recvList = recvList
		self.sendList = sendList
		self.bufsize = 1024
		self.sendCount = 0
		self.exitFlag = False
		threading.Thread(target=self.mainLoop,args=()).start()
	
	def recv(self):
		self.settimeout(0.1)
		while self.exitFlag == False:
			recvData = self.rr()
			if recvData == False:
				self.close()
				self.exitFlag = True
				break
			if recvData == '':
				continue
			self.recvList.append(recvData)
			
	def mainLoop(self):
		print('Accept from:',self.addr)
		threading.Thread(target=self.recv,args=()).start()
		while self.exitFlag == False:
			if len(self.recvList) == 0:
				time.sleep(0.1)
				continue
			if self.ss(b"\xff") == False:
				self.close()
				break
			else:
				self.sendCount = self.sendCount + len(self.recvList[0])
				del self.recvList[0]
				print('sendCount:'+str(self.sendCount)+'\r',end='')
				#print('#')
		print('End of the connection.',self.socket)
		
if __name__ == '__main__':
	socketHand = TcpSer('0.0.0.0',1234)
	while True:
		tcpSock = socketHand.getSocket()
		if tcpSock == False:
			time.sleep(0.1)
			continue
		print('One connection.')
		tcpServer(tcpSock[0],tcpSock[1],[],[])
		time.sleep(4)
		socketHand.close()
		time.sleep(14)
		socketHand.start()

		