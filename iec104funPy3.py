#coding:utf-8
import sys,time

#获取具体位值，返回str类型，大写。长2位。1个字节。
def getBit(varString,count):
	if len(varString) < 2*count:
		return ''
	if str(type(varString)).find('byte') != -1:
		return varString[2*count-2:2*count].decode().upper()
	else:
		return varString[2*count-2:2*count].upper()

#检测是否遥测报文，而且是响应总召的遥测。	
def checkIfYc(var):
	if len(var) >= 32 \
			and getBit(var,1) == '68' \
			and getBit(var,7) == '0B' \
			and getBit(var,9) == '14' \
			and getBit(var,10) == '00':
		return True
	else:
		return False

#检测是否遥信
def checkIfYx(var):
	if len(var) >= 32 \
			and getBit(var,1) == '68' \
			and getBit(var,7) == '01' \
			and getBit(var,9) == '14' \
			and getBit(var,10) == '00':
		return True
	else:
		return False
		
#检测是否总召终止。		
def checkIfEnd(var):
	#																	总召                       激活终止
	if len(var) >= 32 \
			and getBit(var,1) == '68' \
			and getBit(var,7) == '64' \
			and getBit(var,9) == '0A' \
			and getBit(var,10) == '00':
		return True
	#                                                              遥测数据少于80                总召响应
	# if len(var) >= 32 and getBit(var,1) == '68' and getBit(var,7) == '0b' and getBit(var,8) != 'd0' and getBit(var,9) == '14' and getBit(var,10) == '00':
		# print 'End 2'
		# return True
		
	return False

#检测是否遥控选择
def checkIfYaoKongSelect(var):
	if len(var) == 32 \
		and getBit(var,1) == '68' \
		and (getBit(var,7) == '2D' or getBit(var,7) == '2E') \
		and getBit(var,8) == '01' \
		and getBit(var,9) == '06' \
		and getBit(var,10) == '00' \
		and (getBit(var,16) == '81' or getBit(var,16) == '80'):	#80分，81合。
		return True
	else:
		return False

#获取发送序号,返回一个整数。		
def getXuHao(var):
	if len(var) < 8:
		return False
	# di_wei = getBit(var,3)	#低位
	# gao_wei = getBit(var,4)	#高位

	return int(getBit(var,4)+getBit(var,3),16)

#根据给出的数字，生成一个发送序号。返回类型：str，长度4位，两个字节。
def createXuHao(var_int):
	hex_num = hex(int(var_int)).replace('0x','')
	hex_num_len = len(hex_num)
	if hex_num_len%2 != 0:
		hex_num = '0' + hex_num
	if len(hex_num) == 2:
		return hex_num+'00'
	else:
		return hex_num[2]+hex_num[3]+hex_num[0]+hex_num[1]

#检测是否启动传输。		
def checkIfBegin(var):
	if len(var) == 12 \
			and getBit(var,1) == '68' \
			and getBit(var,3) == '07':
		return True
	else:
		return False
		
#检测是否总召		
def checkIfZZao(var):
	if len(var) == 32 \
			and getBit(var,7) == '64' \
			and getBit(var,9) == '06' \
			and getBit(var,10) == '00' \
			and getBit(var,16) == '14':
		return True
	else:
		return False
		
def checkIfSZhen(var):
	if len(var) == 12 and getBit(var,3) == '01':
		return True
	else:
		return False

#判断是否遥测帧。
def checkIfYC(var):
	if len(var) > 12 \
			and getBit(var,1) == '68' \
			and getBit(var,7) == '0B' \
			and int(getBit(var,2),16)*2 == len(var)-4:
		return True
	else:
		return False

#判断是否遥信帧。
def checkIfYX(var):
	if len(var) > 12 \
			and getBit(var,1) == '68' \
			and getBit(var,7) == '01' \
			and int(getBit(var,2),16)*2 == len(var)-4:
		return True
	else:
		return False

#检测是否初始化结束帧46
def checkIf46(var):
	if len(var) > 12 \
			and getBit(var,1) == '68' \
			and getBit(var,7) == '46' \
			and int(getBit(var,2),16)*2+4 == len(var):
		return True
	return False

#判断是否启动确认。
def checkIf0B(var):
	if var.upper() == '68040B000000':
		return True
	return False

#判断是否I帧，长度大于12，6个字节的，都是I帧。
def ifIFrame(var):
	if len(var) > 12 \
			and getBit(var,1) == '68' \
			and int(getBit(var,2),16) == len(var)-4:
		return True
	else:
		return False

#判断是否遥控帧，长度为16字节，不判断带时标的帧。
def ifYaoKong(var):
	if len(var) >= 32:
		bit7 = getBit(var,7)
		# bit13 = getBit(var,13)
		# bit14 = getBit(var,14)
		# bit15 = getBit(var,15)
		# bit16 = getBit(var,16)
		if bit7 in ['2D','2E','3A','3B']:
			return True
	else:
		return False

#简单判断是否遥调
def ifYaoTiao(var):
	if len(var) >= 32:
		bit7 = getBit(var,7)
		if bit7 in ['2F']:
			return True
	return False

#简单判断是否归一化帧
def ifGuiYi(var):
	if len(var) == 36:
		bit7 = getBit(var,7)
		if bit7 in ['30']:
			return True
	return False

#获取当前时标
def getTimeMark():
	curTime = time.localtime()
	year = hex(curTime[0]-2000).replace('0x','').zfill(2)
	mon  = hex(curTime[1]).replace('0x','').zfill(2)
	wday = int(time.strftime('%w', curTime))
	date = hex(curTime[2]+wday*32).replace('0x','').zfill(2)
	hour = hex(curTime[3]).replace('0x','').zfill(2)
	min  = hex(curTime[4]).replace('0x','').zfill(2)
	#microSecond = int(str(time.time()).split('.')[1][:3])
	miSe = hex(curTime[6]+curTime[5]*256).replace('0x','').zfill(4)
	return miSe[2:]+miSe[0:2]+min+hour+date+mon+year

#根据时标，获取时间。
def getTime(timeString):
	year = int(getBit(timeString,7),16)
	mon  = int(getBit(timeString,6),16)
	date = int(bin(int(getBit(timeString,5),16))[-5:],2)
	hour = int(getBit(timeString,4),16)
	min  = int(getBit(timeString,3),16)
	miSe = int(getBit(timeString,2)+getBit(timeString,1),16)
	if len(bin(miSe))>=4:
		micro = int(bin(miSe)[-8:],2)
	else:
		micro = 0

	if miSe > 256:
		second = int(bin(miSe).replace('0b','')[:-8],2)
	else:
		second = 0

	return str(year)+'-'+str(mon)+'-'+str(date)+' '+str(hour)+':'+str(min)+':'+str(second)+'.'+str(micro)

'''
2002版：
遥信：1H-4000H
遥测：4001H-5000H，首地址：16385
遥控：6001H-6100H，首地址：24577
设点：6201H-6400H
电度：6401H-6600H
'''
#生成一个3字节的遥测地址。接受一个整数，返回长度6，3个字节的地址位。返回数据类型：str
#遥测帧，起始地址为16385，而遥信帧，起始地址为0
def createAddress(i,plus=16385):
	hex_str = hex(plus + int(i)).replace('0x','').zfill(4)
	return hex_str[2]+hex_str[3]+hex_str[0]+hex_str[1]+'00'


if __name__ == '__main__':
	tmp = b'680e0000000046010400010000000001'
	curXuHao = getXuHao(tmp[4:])
	print(curXuHao)
	print(createXuHao(curXuHao+2))
	timeMark = getTimeMark()
	print(timeMark)
	print(getTime(timeMark))
