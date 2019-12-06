# coding:utf-8
import socket
import sys,time,random,os
import threading
import binascii,datetime
from iec104funPy3 import *
from tcpServerThrTest import *
import argparse,math

printFlag = [True]

class iec104server:
	recv_count = 0  # 当前接收的连接数，新连接加1，断开减1，默认1024条。

	def __init__(self, socket, addr, ycFrame,yxFrame):
		self.socket = socket
		self.addr = addr
		self.ycFrame = ycFrame
		self.yxFrame = yxFrame

		self.beginComf = '68040b000000'	#固定
		self.timeout = 0.4

		self.localSend = '0000'	#发送端发送序号
		self.localRecv = '0000'	#发送端接收序号

		print('Accept From:', self.addr)
		self.settimeout(1)
		self.myInit()

	def myInit(self):
		iec104server.recv_count = iec104server.recv_count + 1
		self.run()

	def settimeout(self, timeout=0.4):
		self.socket.settimeout(timeout)

	def get_connection_count(self):
		return iec104server.recv_count

	def closeSocket(self):
		try:
			self.socket.close()
		except Exception as e:
			pass

	#发送数据，参数类型为string
	def sendData(self,data):
		try:
			printData(['发#',binascii.b2a_hex(data)])
			self.socket.sendall(data)
			self.updateLocalSend(binascii.b2a_hex(data),2)	#这里加2，下次发送时要加2.
			return True
		except Exception as e:
			self.closeSocket()
			print('Error in send data(Break the connect.):', e)
			return False

	def recvData(self):
		try:
			temp_data = self.socket.recv(1024)
			tempDataAscii = binascii.b2a_hex(temp_data)  # 转成16进制
			if len(tempDataAscii) != 0:
				printData(['收#',tempDataAscii])
				self.updateLocalRecv(tempDataAscii,2)
				return tempDataAscii.decode()
			else:
				return ''
		except socket.timeout as e:
			return ''
		except Exception as e:
			print('Error in recvData:', e)
			self.closeSocket()
			return False

	#启动确认
	def sendBeginComf(self):
		return self.sendData(binascii.a2b_hex(self.beginComf))

	def sendInitEnd(self):
		#self.initEnd = '680e0000 0000 46010400010000000001'  # 初始化结束。
		curFrame = '680e'+self.localSend+self.localRecv+'46010400010000000001'
		return self.sendData(binascii.a2b_hex(curFrame))

	# 总召确认,返回确认帧的具体内容。以便后续的帧获取到发送序号。
	def sendZZaoComf(self):
		comf_str = '680e' + self.localSend+self.localRecv+'64010700010000000014'
		return self.sendData(binascii.a2b_hex(comf_str))

	# 发送总召激活终止。
	def sendEnd(self):
		# print('激活终止')
		###############################################总召，不连接，激活终止。
		curFrame = '680e'+self.localSend+self.localRecv+'6401'+'0a00'+'010000000014'
		return self.sendData(binascii.a2b_hex(curFrame))

	# 发送遥测数据
	def sendYcData(self):
		# my_print('发送遥测帧')
		yc_zheng = '68'
		for line in self.ycFrame:
			curFrame = yc_zheng+line[1]+self.localSend+self.localRecv+line[0]
			if not self.sendData(binascii.a2b_hex(curFrame)):
				return False
		return True

	def sendYXData(self):
		for line in self.yxFrame:
			curFrame = '68'+line[1]+self.localSend+self.localRecv+line[0]
			if not self.sendData(binascii.a2b_hex(curFrame)):
				return False
		return True


	#更新本地发送序号。
	#默认加0，则接收到的序号。在sendData中，自己每一次发，panding应该为2
	def updateLocalSend(self,resultData,panding=0):
		if len(resultData) > 12:
			self.localSend = createXuHao(getXuHao(resultData)+panding)

	#更新本地发送序号。
	#本地发送序号为最为接收I帧的发送序号+2
	def updateLocalRecv(self,resultData,panding=0):
		if len(resultData) > 12:
			self.localRecv = createXuHao(getXuHao(resultData)+panding)

	# 用户重写或者覆盖此方法
	def run(self):
		while True:
			resultData = self.recvData()
			if resultData == False:  # 接收错误
				break
			if resultData == '':  # 超时返回
				continue

			if checkIfBegin(resultData):  # 如果是启动传输。
				if not (self.sendBeginComf() and self.sendInitEnd()):
					break

			elif checkIfZZao(resultData):  # 如果是总召。
				if not (self.sendZZaoComf() and self.sendYcData() and self.sendYXData() and self.sendEnd()):
					break

			elif ifYaoKong(resultData):	#遥控
				ykPart = resultData[12:32]		#
				timeString = resultData[32:]	#时标
				if ykPart.find('0600') != -1:
					ykPartComf = ykPart.replace('0600','0700')
				elif ykPart.find('0800') != -1:
					ykPartComf = ykPart.replace('0800','0900')
				if len(timeString) == 0:
					frameLen = '0e'
				else:
					frameLen = '15'
				curFrame = '68'+frameLen+self.localSend+self.localRecv+ykPartComf+timeString
				if not self.sendData(binascii.a2b_hex(curFrame)):
					break

			elif ifGuiYi(resultData):	#归一化值。
				gyPart = resultData[12:20]	#从apdu类型到传输原因。
				gyActiveFlag = resultData[-2:]	#最后一字节
				frameLen = '10'
				if gyPart.find('0600') != -1 and gyActiveFlag == '80':
					gyPartComf = gyPart.replace('0600','0700')
				elif gyPart.find('0600') != -1 and gyActiveFlag == '00':
					gyPartComf = gyPart.replace('0600', '0a00')
				elif gyPart.find('0800') != 0:
					gyPartComf = gyPart.replace('0800', '0a00')
				curFrame = '68'+frameLen+self.localSend+self.localRecv+gyPartComf+resultData[20:]
				if not self.sendData(binascii.a2b_hex(curFrame)):
					break

			elif ifYaoTiao(resultData): #遥调
				ytPart = resultData[12:20]
				ytActiveFlag = resultData[-2:]
				frameLen = '0e'
				if ytPart.find('0600') != -1 and ytActiveFlag in ['82','81']:
					ytPartComf = ytPart.replace('0600','0700')
				elif ytPart.find('0600') != -1 and ytActiveFlag in ['02','01']:
					ytPartComf = ytPart.replace('0600', '0a00')
				elif ytPart.find('0800') != -1:
					ytPartComf = ytPart.replace('0800', '0a00')
				curFrame = '68'+frameLen+self.localSend+self.localRecv+ytPartComf+resultData[20:]
				if not self.sendData(binascii.a2b_hex(curFrame)):
					break

			else:
				pass

		self.closeSocket()
		iec104server.recv_count = iec104server.recv_count - 1


def random_string(randomlength=1024):
	str = ''
	chars = 'AaBbCcDdEeFfGgHhIiJjKkLlMmNnOoPpQqRrSsTtUuVvWwXxYyZz0123456789'
	length = 61
	random = Random()
	for i in range(randomlength):
		str += chars[random.randint(0, length)]
	return str

#获取，单点，双点遥控选择与执行帧，客户端与服务端都可以调用。
#single为单双点，active为第3帧是否执行，comf是否回复帧，switch为分合，select为前两帧
def createYaoKong(point,single,active,comf,switch,select,timeMark):
	pubAddress = '0100'
	if single and not timeMark:
		ykType = '2d'	#单点，不带时标
	elif single and timeMark:
		ykType = '3a'	#单点，带时标
	elif not single and not timeMark:
		ykType = '2e'	#双点，不带时标
	elif not single and timeMark:
		ykType = '3b'	#双点，带时标

	if select:	#第一、二帧
		if not comf:	# 第一帧
			ykJiHuo = '0600'
		else:	#第二帧
			ykJiHuo = '0700'

		if single:	#单点
			if switch:	#合
				ykAction = '81'
			else:	#分
				ykAction = '80'
		else:	#双点
			if switch:	#合
				ykAction = '82'
			else:	#分
				ykAction = '81'

	elif not select: #第三、四帧
		if not comf: #第三帧，
			if active: #执行
				ykJiHuo = '0600'
			else:	#取消执行
				ykJiHuo = '0800'
		else: #第四帧
			if active: #执行
				ykJiHuo = '0700'
			else:	#取消执行
				ykJiHuo = '0900'

		if single:	#单点
			if switch:	#合
				ykAction = '01'
			else:	#分
				ykAction = '00'
		else:	#双点
			if switch:	#合
				ykAction = '02'
			else:	#分
				ykAction = '01'

	curAddress = createAddress(point,plus=24577-1)	#首个地址是24577
	return ykType+'01'+ykJiHuo+pubAddress+curAddress+ykAction

#遥调
def createYaoTiao(point,active,comf,switch,select):
	pubAddress = '0100'
	ytType = '2f' #遥调，与双点遥信类似。
	if select: #第一、二帧
		if not comf: #第一帧
			ytJiHuo = '0600'
		else: #第二帧
			ytJiHuo = '0700'

		if switch: #升
			ytAction = '82'
		else: #降
			ytAction = '81'

	else: #第三、四帧
		if not comf: #第三帧
			if active:
				ytJiHuo = '0600'
			else:
				ytJiHuo = '0800'
		else:
			ytJiHuo = '0a00'

		if active:
			if switch:
				ytAction = '02' #执行、升
			else:
				ytAction = '01' #执行、降
		else:
			if switch:
				ytAction = '82' #取消、升
			else:
				ytAction = '81' #取消、降

	curAddress = createAddress(point,plus=0) #网上没有查到首个地址，PMA显示首个地址为0
	return ytType+'01'+ytJiHuo+pubAddress+curAddress+ytAction

#select为前两帧，comf为回复帧，active为第3帧是否执行。
def createGuiYi(point,value,active,comf,select):
	pubAddress = '0100'
	gyType = '30'
	curAddress = createAddress(point,plus=0)
	curValue = createOneGy(value)

	if select: #第一、二帧
		gyAction = '80'
		if not comf: #第一帧
			gyJiHuo = '0600'
		else: #第二帧
			gyJiHuo = '0700'
	else: #第三、四帧
		if not comf: #第三帧
			if active: #执行
				gyJiHuo = '0600'
				gyAction = '00'
			else: #取消
				gyJiHuo = '0800'
				gyAction = '80' #不知道为什么PMA是返回这个值？，如果高位s/e执行时设为0，此值16进制应该是0
		else: #第四帧
			if active: #执行
				gyJiHuo = '0a00'
				gyAction = '00'
			else: #取消
				gyJiHuo = '0a00'
				gyAction = '80'

	return gyType+'01'+gyJiHuo+pubAddress+curAddress+curValue+gyAction

#更新遥测帧
def updateYCFrame(ycList,ycFrame,number):
	ycPart = ''
	yc_zhi = '0b'  # 当前帧为遥测帧（标度化值）
	zzao_zhen = '1400'  # 遥测帧，响应总召。传输原因
	pub_addr = '0100'  # 公共地址
	curAddress = ''
	first_address = True
	j = 0
	i = 0
	'''遥测帧长度：
	1、68:1	不计算在内
	2、长度:1 不计算内
	3、发送序号：2
	4、接收序号：2
	5、遥测值表示：1
	6、遥测值数量表示：1
	7、传输原因：2
	8、公共地址：2
	8、首个值地址：3
	9、遥测点个数x*3
	当x=76（2+2+1+1+2+2+3+76*3=13+228=241=f1）
	当x=52（2+2+1+1+2+2+3+52*3=13+156=169=a9）
	'''
	for z in range(number):
		if first_address == True:
			curAddress = createAddress(0)  # 当前帧遥测值首地址。
			first_address = False
		ycPart = ycPart + ycList[z]
		if j == 75:  # 最长一个遥测帧为76个值（前位置1，表示连接。16进制为（128+76=CC）。其实76为自己定义的一个值。
			j = 0
			this_z = yc_zhi + 'cc' + zzao_zhen + pub_addr + curAddress + ycPart
			ycFrame[i] = [this_z,'f1']
			i = i + 1
			curAddress = createAddress(z+1)  #下一个帧遥测值首地址。
			ycPart = ''
		else:
			j = j + 1
	###################128,最高位置1，连续
	last_z = yc_zhi+hex(j+128).replace('0x','')+zzao_zhen+pub_addr+curAddress+ycPart
	last_z_len = hex(int((len(last_z)+8)/2)).replace('0x', '')  #加8，因为这里少了发送序号和接收序号。
	ycFrame[i] = [last_z,last_z_len]
	# for line in ycList:
	# 	print('ycList:',line)
	# for line in ycFrame:
	# 	print('ycFrame:',line,len(line[0]))


def updateYXFrame(yxList,yxFrame,yxSize):
	yxPart = ''

	s01 = '01'  # 单点信息
	sLen = 0  # 长度，多少个遥信量
	sReason = '1400'  # 传输原因，包括测试位，P/N位，传送原因，源发地址
	sPublish = '0100'  # 公共地址
	sFirstYxAddress = 0  # 第一个遥信地址
	firstAddress = True
	j = 0
	i = 0
	'''遥信帧长度：
	1、68:1	不计算在内
	2、长度:1 不计算内
	3、发送序号：2
	4、接收序号：2
	5、遥信值表示：1
	6、遥信值数量表示：1
	7、传输原因：2
	8、公共地址：2
	8、首个值地址：3
	9、遥测点个数x*1
	当x=76（2+2+1+1+2+2+3+76*1=13+76=89=59（Hex））
	当x=52（2+2+1+1+2+2+3+52*1=13+52=65=41（Hex））
	'''
	for z in range(yxSize):
		if firstAddress == True:
			firstAddress = False
			curAddress = createAddress(1,plus=0)
		yxPart = yxPart + yxList[z]
		if j == 75:	#最长一个遥信帧，即76个遥信（cc），也是随便定义的，跟遥测测试为相同。
			j = 0
			thisZ = s01+'cc'+sReason+sPublish+curAddress+yxPart
			yxFrame[i] = [thisZ,'59']
			i = i + 1
			curAddress = createAddress(z+1,plus=0)	#下一个遥信帧首地址。
			yxPart = ''
		else:
			j = j + 1
		#################128,则最高位置1，表示连续。
	thisZ = s01+hex(j+128).replace('0x','')+sReason+sPublish+curAddress+yxPart
	thisZLen = hex(int((len(thisZ)+8)/2)).replace('0x', '')  #加8，因为这里少了发送序号和接收序号。
	yxFrame[i] = [thisZ,thisZLen]
	# for line in yxFrame:
	# 	print(line,len(line[0]))

#定时更新ycList的值。不是具体报文。
def initYcList(ycList,ycFrame,number=200):
	random_yc(ycList, number)  # 初始化遥测值。

	ycFrameLen = math.ceil(number/76)	#向上取整
	#ycFrema = [[帧内容（不包括头，发送序号，接收序号），长度]]
	for i in range(ycFrameLen):	#初始化ycFrame长度
		ycFrame.append([])

	j = 0
	while True:
		for address in range(number):
			ycList[address] = createOneYc(address + j)
		updateYCFrame(ycList,ycFrame,number)
		time.sleep(10)
		j = j + 1
		if j >= 4:
			j = 0

def initYxList(yxList,yxFrame,yxSize):
	for i in range(yxSize):
		if i%2 == 0:
			yxList.append('00')	#'00分，01合'
		else:
			yxList.append('01')  # '00分，01合'

	yxFrameLen = math.ceil(yxSize/76)	#向上取整
	for i in range(yxFrameLen):
		yxFrame.append([])
	j = 0
	while True:
		for i in range(yxSize):
			if yxList[i] == '00':
				yxList[i] = '01'
			else:
				yxList[i] = '00'
		updateYXFrame(yxList,yxFrame,yxSize)
		time.sleep(2)

# 遥测值
def random_yc(ycList, number):
	for i in range(number):
		ycList.append(createOneYc(i))


# 每个遥测长度6位，共3个字节，前两个为具体数值，低位在前，高位在后，最后1个字节为品质。
def createOneYc(value):
	hex_yc = hex(value).replace('0x', '')
	if len(hex_yc) == 1:
		return '0' + hex_yc + '0000'
	elif len(hex_yc) == 2:
		return hex_yc + '0000'
	elif len(hex_yc) == 3:
		return hex_yc[1:3] + '0' + hex_yc[0] + '00'
	elif len(hex_yc) == 4:
		return hex_yc[2:4] + hex_yc[0:2] + '00'
	else:
		return '000000'

#返修归一值。
def createOneGy(value):
	hexString = hex(value)[2:].zfill(4)
	return hexString[2:]+hexString[0:2]

#以帧分割接收到的数据。
def splitData(varByte):
	dataList = []
	while True:
		if getBit(varByte,1) == '68':
			curLen = int(getBit(varByte,2),16)*2+4
			dataList.append(varByte[0:curLen])
			varByte = varByte[curLen:]
			if len(varByte) == 0:
				break
	return dataList

def countConnect():
	while True:
		print('Total:', iec104server.recv_count, '\r',end='')
		sys.stdout.flush()
		time.sleep(1)

def osSystem(cmd):
	try:
		return os.system(cmd)
	except Exception as e:
		print('Error in osSystem:', e)

def setTitle(theTitle):
	try:
		if os.name == 'nt':
			osSystem("title " + theTitle)
		if os.name == 'posix':
			sys.stdout.write("\x1b]2;" + theTitle + "\x07")
	except Exception as e:
		print('Error in setTitle:', e)

def printData(info):
	if printFlag[0] == False:
		return False
	sys.stdout.write(datetime.datetime.now().strftime('%H:%M:%S.%f '))
	sys.stdout.write(info[0])
	sys.stdout.write(' ')
	data = info[1]
	if type(data) == type(b'asdf'):
		data = data.decode()

	while True:
		sys.stdout.write(data[0:2])
		sys.stdout.write(' ')
		data = data[2:]
		if len(data) == 0:
			print('')
			break


'''
104规约的报文帧分为三类：I帧、S帧和U帧。
I帧称为信息帧，长度一定大于6个字节，被称作长帧，用于传输数据；
S帧称为确认帧，长度只有6个字节，被称作短帧，用于确认接收的I帧；
U帧称为控制帧，长度只有6个字节，也被称作短帧，用于控制启动/停止/测试。
长帧报文分为APCI和ASDU两个部分，统称为APDU，而短帧报文只有APCI部分。
APCI的6个字节是这样构成的： 起动字符68H，1个字节； 后面的报文长度，1个字节(最大253)； 控制域位组，4个字节。
I帧的4字节控制域位组规定为：字节1和字节2为发送序号，字节3和字节4为接收序号。
需注意两点：
1、由于字节1和字节3的最低位固定为0，不用于构成序号，所以在计算序号时，要先转换为十进制数值，再除以2；
2、由于低位字节在前、高位字节在后，所以计算时要先做颠倒。
S帧的字节1固定为01H，字节2固定为00H，字节3和字节4为接收序号。计算时仍要注意以上两点。
U帧的字节2、3、4均固定为00H，字节1包含TESTFR，STARTDT和STOPDT三种功能，同时只能激活其中的一种功能。
启动(STARTDT)和停止(STOPDT)都是由主站（104的M端，也就是104的客户端）发起的，先由主站发送生效报文，子站随后确认。
而主站和子站都可发送测试(TESTFR)报文，由另一方确认。
STARTDT：68 04 07 00 00 00(生效)； 68 04 0B 00 00 00(确认)			客户端发起
STOPDT：68 04 13 00 00 00(生效)； 68 04 23 00 00 00(确认)			  客户端发起
TESTFR：68 04 43 00 00 00(生效)； 68 04 83 00 00 00(确认)			  客户端和服务端对发

发送序号与接收序号
各端：
1、发送序号与接收序号初始值都为0
2、发送序号为自身加1，
3、接收序号为最后接收的I帧加1，16进制表现为加2
s帧，没有发送序号，接收序号同上。

I，长度大于6的帧（即I帧）。
'''
#========================================
class iec104client:
	def __init__(self,ip,port):
		self.ip = ip
		self.port = port
		self.qidong 	= '680407000000'	#启动
		self.qidongComf	= '68040B000000'	#启动确认，固定格式。
		self.sZheng		= '680401001000'	#s帧，固定格式。
		self.zZhao		= '680e0200080064010600010000000014'	#总召
		self.countIFrame = 0	#计算I帧的个数（长度大于12，6个字字），以备发送S帧或总召的发送序号。
		self.countZZao = 0		#统计当前发送总召的个数。
		#
		self.localSend = '0000'	#发送端发送序号
		self.localRecv = '0000'	#发送端接收序号

		self.endYcYxFlag = False	#遥测、遥信帧接收完成。
		self.startFlag = False
		self.recvDataFalg = False
		self.timeout = 4	#时间间隔。
		self.recvList = []	#接收到的数据。

	def connect(self):
		try:
			self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			self.s.connect((self.ip, self.port))
			return True
		except Exception as e:
			print('Error in connect:',self.ip,self.port,e)
			return False

	def closeSocket(self):
		self.s.close()
		self.startFlag = False

	def updateLocalSend(self,tempDataAscii):
		if len(tempDataAscii) > 12:
			self.localSend = createXuHao(getXuHao(tempDataAscii)+2)

	#更新发送端的接收序号。
	#为最后已接收到的I帧的发送序号加2。
	def updateLocalRecv(self,tempDataAscii):
		self.localRecv = createXuHao(getXuHao(tempDataAscii)+2)

	#保留特定帧：单、双点遥控，初始化结束（46），启动确认，归一化值（30）
	def ifKeep(self,tempDataAscii):
		if tempDataAscii.upper() == '68040B000000':	#启动确认
			self.recvList.append(tempDataAscii)
			return True
		frameType = getBit(tempDataAscii,7)
		if frameType in ['2D','2E','46','3A','3B','30','2F']:
			self.recvList.append(tempDataAscii)
		elif frameType == '64':	#总召激活终止。
			if getBit(tempDataAscii,9) == '0A' and getBit(tempDataAscii,10) == '00':
				self.endYcYxFlag = True

	def recvData(self):
		self.recvDataFalg = True
		self.s.settimeout(4)
		while self.recvDataFalg == True:
			try:
				tempData = self.s.recv(1024)
				tempDataAscii = binascii.b2a_hex(tempData)	#转成16进制
				for line in splitData(tempDataAscii):
					if len(line) != 0:
						if len(line) > 12:	#从I帧更新本地的接收序号，必须先更新。
							self.updateLocalRecv(line)
						self.ifKeep(line.decode())
						printData(['收：',line.decode()])
			except socket.timeout as e:
				pass
			except Exception as e:
				print('Error in recvData:',e)
				self.closeSocket()
				self.recvDataFalg = False
				return False,''

	def sendData(self,varString):
		try:
			self.s.sendall(binascii.a2b_hex(varString))
			self.updateLocalSend(varString)
			printData(['发：',varString])
			return True
		except Exception as e:
			print('Error in sendData:',e)
			return False

	#发送总召，接收遥测、遥测超时为3秒。
	def sendZZao(self,timeout=3):
		###########启动+长度  发送序号      接收序号         固定
		if printFlag[0]: print('发送总召')
		curZZao = '680e'+self.localSend+self.localRecv+'64010600010000000014'
		self.endYcYxFlag = False
		if self.sendData(curZZao):
			startTime = time.time()
			while time.time() - startTime < timeout:
				if self.endYcYxFlag:
					self.endYcYxFlag = False
					return True
		print('False in sendZZao.....')
		return False

	#发送s帧
	def sendSFrame(self):
		if printFlag[0]: print('发送S帧')
		curSZheng = '68040100'+self.localRecv
		return self.sendData(curSZheng)


	#获取第一帧，删除后返回。
	def lastRecv(self,timeout=4):
		startTime = time.time()
		while time.time() - startTime < timeout:
			if len(self.recvList) != 0:
				headLine = self.recvList[0]
				del self.recvList[0]
				return headLine
		return ''

	#发送遥控
	def sendYaoKongActive(self,point,single,switch,active,timeMark):
		ykPartSelect       = createYaoKong(point=point,single=single,active=True,comf=False,switch=switch,select=True,timeMark=timeMark)
		ykPartSelectComf   = createYaoKong(point=point,single=single,active=True,comf=True,switch=switch,select=True,timeMark=timeMark)
		ykPartActive       = createYaoKong(point=point,single=single,active=active,comf=False,switch=switch,select=False,timeMark=timeMark)
		ykPartActiveComf   = createYaoKong(point=point,single=single,active=active,comf=True,switch=switch,select=False,timeMark=timeMark)
		ykPartActiveComfHG   = createYaoKong(point=point,single=single,active=True,comf=True,switch=switch,select=False,timeMark=timeMark)	#汉哥软件返回。
		#正确应该是0600、0700、0600、0700，###、0600、0700、0800、0900（公司软件返回0700）
		ykPartActiveComfPMA = ykPartActiveComf[0:4]+'0a'+ykPartActiveComf[6:]

		if timeMark:
			curTimeMark = getTimeMark()
			ykPartSelect       = ykPartSelect+curTimeMark
			ykPartSelectComf   = ykPartSelectComf+curTimeMark
			ykPartActive       = ykPartActive+curTimeMark
			ykPartActiveComf   = ykPartActiveComf+curTimeMark
			ykPartActiveComfHG = ykPartActiveComfHG+curTimeMark

		frameLen = ''
		if timeMark:
			frameLen = '15'
		else:
			frameLen = '0e'

		if printFlag[0]: print('开始遥控：点：',point,'单点：',single,'合：',switch,'执行：',active,'时标：',timeMark)
		ykSelect = '68'+frameLen+self.localSend+self.localRecv+ykPartSelect
		if self.sendData(ykSelect) and self.lastRecv()[12:] == ykPartSelectComf:
			ykActive = '68'+frameLen+self.localSend + self.localRecv + ykPartActive
			if self.sendData(ykActive) and (self.lastRecv()[12:] in [ykPartActiveComf,ykPartActiveComfHG,ykPartActiveComfPMA]):
				if printFlag[0]: print('遥控成功。')
				return True
		if printFlag[0]: print('遥控失败。')
		return False

	#遥调
	def sendYaoTiao(self,point,active,switch):
		ytPartSelect     = createYaoTiao(point=point,active=True,comf=False,switch=switch,select=True)
		ytPartSelectComf = createYaoTiao(point=point,active=True,comf=True,switch=switch,select=True)
		ytPartActive     = createYaoTiao(point=point,active=active,comf=False,switch=switch,select=False)
		ytPartActiveComf = createYaoTiao(point=point,active=active,comf=True,switch=switch,select=False)

		frameLen = '0e'
		ytSelect = '68'+frameLen+self.localSend+self.localRecv+ytPartSelect
		if printFlag[0]: print('开始遥调：点：', point, '升：', switch, '执行：', active)
		if self.sendData(ytSelect) and self.lastRecv()[12:] == ytPartSelectComf:
			ytActive = '68'+frameLen+self.localSend+self.localRecv+ytPartActive
			if self.sendData(ytActive) and self.lastRecv()[12:] == ytPartActiveComf:
				if printFlag[0]: print('遥调成功。')
				return True

		if printFlag[0]: print('遥调失败。')
		return False

	#发送归一化值。
	def sendGuiYi(self,point,value,active):
		gyPartSelect     = createGuiYi(point=point, value=value, active=True, comf=False, select=True)
		gyPartSelectComf = createGuiYi(point=point, value=value, active=True, comf=True, select=True)
		gyPartActive     = createGuiYi(point=point, value=value, active=active, comf=False, select=False)
		gyPartActiveComf = createGuiYi(point=point, value=value, active=active, comf=True, select=False)

		frameLen = '10'
		gySelect = '68'+frameLen+self.localSend+self.localRecv+gyPartSelect
		if printFlag[0]: print('开始归一化值：点：', point, '值：', value, '执行：', active)
		if self.sendData(gySelect) and self.lastRecv()[12:] == gyPartSelectComf:
			gyActive = '68'+frameLen+self.localSend+self.localRecv+gyPartActive
			if self.sendData(gyActive) and self.lastRecv()[12:] == gyPartActiveComf:
				if printFlag[0]: print('归一化值设定成功。')
				return True
		if printFlag[0]: print('归一化值设定失败。')
		return False

	def start(self):
		while True:
			if not self.connect():
				time.sleep(1)
				continue
			else:
				self.run()

	def run(self):
		self.startFlag = True
		threading.Thread(target=self.recvData,args=()).start()

		if not self.sendData(self.qidong):
			return False

		time.sleep(0.1)

		if checkIf0B(self.lastRecv()):
			if checkIf46(self.lastRecv()):	#PMA不回这一帧
				pass
		else:
			return False

		while self.startFlag:
			self.sendZZao()

			time.sleep(0.1)
			if not self.sendSFrame(): break
			#time.sleep(self.timeout)
			time.sleep(0.1)

			single = True	#单双点。
			switch = True	#分、合闸
			active = True
			#点号、单、双，分、合，执行、取消、时标
			# print('startYK#################################')
			point = random.randint(1,10)
			for single in [True,False]:
				for switch in [True,False]:
					for active in [True,False]:
						for timeMark in [True,False]:
							if not self.sendYaoKongActive(point=point,single=single,switch=switch,active=active,timeMark=timeMark):
								time.sleep(0.5)
							else:
								time.sleep(0.01)

				#time.sleep(100000)

			point = random.randint(1,10)
			for active in [True,False]:
				for switch in [True,False]:
					if not self.sendYaoTiao(point=point,active=active,switch=switch):
						time.sleep(0.5)
					else:
						time.sleep(1)

			#time.sleep(10000)
			point = random.randint(1,10)
			value = random.randint(10,19)
			for active in [True,False]:
				if not self.sendGuiYi(point=point,value=value,active=active):
					time.sleep(0.5)
				else:
					time.sleep(1)
				#time.sleep(10000)

			time.sleep(1)

		print('End of client.')

	def close(self):
		self.startFlag = False

def mainServer(port,ycSize=64,yxSize=32):
	ycList = []
	ycFrame = []
	yxList = []
	yxFrame = []
	ycSize = ycSize
	yxSize = yxSize
	threading.Thread(target=initYcList, args=(ycList,ycFrame,ycSize)).start()
	threading.Thread(target=initYxList, args=(yxList,yxFrame,yxSize)).start()
	threading.Thread(target=countConnect, args=()).start()

	socketHand = TcpSer('0.0.0.0', 2404)
	while True:
		tcpSock = socketHand.getSocket()
		if tcpSock == False:
			time.sleep(0.05)
			continue
		threading.Thread(target=iec104server, args=(tcpSock[0], tcpSock[1], ycFrame,yxFrame)).start()

def mainClient(ip,port,thrCount=1):
	for i in range(thrCount):
		threading.Thread(target=iec104client(ip,port).start,args=()).start()

def main_loop():
	curRole = 's'
	ip = '127.0.0.1'
	port = 2404
	thrCount = 1
	ycSize = 128
	yxSize = 128
	p = argparse.ArgumentParser(description="")
	p.add_argument("-c", "--client", action='store_true', help="set client")
	p.add_argument("-s", "--server", action='store_true', help="set server,default.")
	p.add_argument("-i", "--ip", help="set remove ip,default 127.0.0.1", default='127.0.0.1')
	p.add_argument("-p", "--port", help="set port,xxx or xxx-yyy,default 2404", default=2404)
	p.add_argument("-z", "--ycsize", help="set yc count,default 64", default=64)
	p.add_argument("-x", "--yxsize", help="set yx ciybt,default 32", default=32)
	p.add_argument("-o", "--printEnable",action='store_true', help="if print enable")
	p.add_argument("-r", "--thrCount",help="client Thread.default 1",default=1)
	args = p.parse_args()
	if args.client:
		curRole = 'c'
	if args.server:
		curRole = 's'
	if args.printEnable:
		printFlag[0] = False
	if args.ip:
		ip = args.ip
	if args.port:
		port = int(args.port)
	if args.thrCount:
		thrCount = int(args.thrCount)
	if args.ycsize:
		ycSize = int(args.ycsize)
	if args.yxsize:
		yxSize = int(args.yxsize)

	if curRole == 's':
		setTitle('Server#'+str(port)+' yc:'+str(ycSize)+' yx:'+str(yxSize))
		mainServer(port,ycSize,yxSize)
	if curRole == 'c':
		setTitle('Client#'+ip+':'+str(port)+' thr:'+str(thrCount))
		mainClient(ip,port,thrCount)

if __name__ == '__main__':
	main_loop()
	# print(createGuiYi(point=1,value=10,active=True,comf=False,select=True))
	# print(createGuiYi(point=1,value=10,active=True,comf=True,select=True))
	# print(createGuiYi(point=1,value=10,active=True,comf=False,select=False))
	# print(createGuiYi(point=1,value=10,active=True,comf=True,select=False))
	# print('')
	# print(createGuiYi(point=11,value=11,active=True,comf=False,select=True))
	# print(createGuiYi(point=11,value=11,active=True,comf=True,select=True))
	# print(createGuiYi(point=11,value=11,active=False,comf=False,select=False))
	# print(createGuiYi(point=11,value=11,active=False,comf=True,select=False))

	# print(createYaoTiao(point=1,active=True,comf=False,switch=True,select=True))
	# print(createYaoTiao(point=1,active=True,comf=True,switch=True,select=True))
	# print(createYaoTiao(point=1,active=True,comf=False,switch=True,select=False))
	# print(createYaoTiao(point=1,active=True,comf=True,switch=True,select=False))
	# print ()
	# print(createYaoTiao(point=1,active=True,comf=False,switch=False,select=True))
	# print(createYaoTiao(point=1,active=True,comf=True,switch=False,select=True))
	# print(createYaoTiao(point=1,active=True,comf=False,switch=False,select=False))
	# print(createYaoTiao(point=1,active=True,comf=True,switch=False,select=False))
	# print ()
	# print(createYaoTiao(point=1,active=True,comf=False,switch=True,select=True))
	# print(createYaoTiao(point=1,active=True,comf=True,switch=True,select=True))
	# print(createYaoTiao(point=1,active=False,comf=False,switch=True,select=False))
	# print(createYaoTiao(point=1,active=False,comf=True,switch=True,select=False))
	# print ()
	# print(createYaoTiao(point=1,active=True,comf=False,switch=False,select=True))
	# print(createYaoTiao(point=1,active=True,comf=True,switch=False,select=True))
	# print(createYaoTiao(point=1,active=False,comf=False,switch=False,select=False))
	# print(createYaoTiao(point=1,active=False,comf=True,switch=False,select=False))
	# print ()
