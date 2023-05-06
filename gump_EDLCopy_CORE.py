# -*- coding: utf-8 -*-
#!/usr/bin/env python
# Author: Chen Pei Yu
# Date: 2023 Jan.

import os
import re


class CopyByEDL():
		
	
	copy_from_path = ''
	copy_to_path = ''
	chksum = 'Y'
	kpDir = 'Y'
	kpLevel = 0
	
	chkbox_only = 'N'
	input_only = ''
	chkbox_only_not = 'N'
	input_only_not = ''
	
	del_ext_of_clip_list = True #要把clip list中的副檔名去掉。最後一個.xxx
	
	file_inlist_count = 0
	has_copied = 0
	
	file_list = []
	copy_script = []	
	
	foundInDir = [] #在路径就有找到的，最后要找如果有路径在这个以下的script就取消，避免重复拷贝
	foundInDir_root = []
	foundInDir_name = []
	foundInFile = []  #在档案等级有找到的
	foundInFile_root = []
	foundInFile_name = []
	
	err_msg = []
	exec_log_path = 'exec_log.txt'
	info_log_path = 'info_log.txt'
		
	def __init__(self,**thePath):		
		# from path
		if not os.path.isdir(thePath['from_path']):
			print("Please Choose Copy From" + thePath['from_path'])
			return 
		else:
			self.copy_from_path = thePath['from_path']
		
        
        # to path
		if not os.path.isdir(thePath['to_path']):
			print("Please Choose Copy To")
			return 
		else:
			self.copy_to_path = thePath['to_path']
        
        # edl/txt path
		if os.path.isfile(thePath['clip_path']):						
			if thePath['clip_path'].find('.') >= 0:
				
				tmp = thePath['clip_path'].split('.')
				if tmp[1] == 'edl':
					self.a_getClipFromEDL(thePath['clip_path'])
				elif tmp[1] == 'txt':
					self.a1_getClipFromTXT(thePath['clip_path'])
				else:
					print('No Valid Clip File')				

		else:
			print("Please Choose EDL or TXT")
			return         
            
		# param
		self.chksum = thePath['rad_chksum']
		self.kpDir = thePath['rad_kpdir']
		self.kpLevel = thePath['spin_level']		
		self.chkbox_only = thePath['chkbox_only']
		self.input_only = thePath['input_only']
		self.chkbox_only_not = thePath['chkbox_only_not']
		self.input_only_not = thePath['input_only_not']

		return 

	def test_readLine(self,file_path):
		
		return file_path
	
	def a_getClipFromEDL(self,edl_path):
		'''
		type1 
		 008 B006_L003_0807PE V C 10:36:43:00 10:37:20:03 00:05:43:18 00:06:20:21
         * FROM CLIP NAME: B006_L003_0807PE.MOV
         
        type2
         001 B186_L010_0821WC V C 21:55:07:12 21:55:10:05 00:00:00:00 00:00:02:17
         002 B294_L013_0106UQ V C 10:02:12.03 10:02:27.15 00:00:00:00 00:00:15:12
		'''
		lines = open(edl_path)
		data = lines.readlines()
		
		isType1 = False
		for line in data:			
			if line.find('FROM CLIP NAME') >= 0: # type1				
				isType1 = True
				break		
							
		if isType1:			
			self.a2_edlType1(edl_path)
		else:			
			self.a3_edlType2(edl_path)
			
		return True
	
	def a1_getClipFromTXT(self,txt_path):
		
		with open(txt_path) as reader:
			while True:
				lines = reader.readline().strip()	
				#如果有副檔名，就刪掉。
				if self.del_ext_of_clip_list and lines.find('.') >= 0:					
					tmp = lines.rsplit(".",1) 
					lines = tmp[0]								

				if not lines:
	   				break
				else:    	
	   				self.file_list.append(lines)
	   				
	   	#去掉重複的	
		self.file_list = self.tool_removeRpt(self.file_list)	

		return True
	
	def a2_edlType1(self,edl_path):
		'''
		type1 
		 008 B006_L003_0807PE V C 10:36:43:00 10:37:20:03 00:05:43:18 00:06:20:21
         * FROM CLIP NAME: B006_L003_0807PE.MOV                
		'''
		lines = open(edl_path)
		data = lines.readlines()
		
		print('Type1 EDL')
		
		for line in data:
			if line.find('FROM CLIP NAME:') >= 0:
				ele = line.split('FROM CLIP NAME:')
				
				#如果有副檔名，就刪掉。
				if self.del_ext_of_clip_list and ele[1].strip().find('.') >= 0:					
					tmp = ele[1].strip().rsplit(".",1) #只做一次，從右邊			
					clip = tmp[0].strip()
					self.file_list.append(clip)
     
				else:					
					self.file_list.append(ele[1].strip())     
	
		print('EDL Has ' + str(len(self.file_list)) + ' Clips')	
		#去掉重複的	
		self.file_list = self.tool_removeRpt(self.file_list)	
		print('EDL Has ' + str(len(self.file_list)) + ' No Repeat Clips')
		return True
	
	def tool_removeRpt(self,list):
		new_list = []
		for data in list:
			if data not in new_list:				
				new_list.append(data)			
		return new_list
	
	def a3_edlType2(self,edl_path):
		print('Type 2 EDL')
		'''
		type2
         001 B186_L010_0821WC V C 21:55:07:12 21:55:10:05 00:00:00:00 00:00:02:17
         002 B294_L013_0106UQ V C 10:02:12.03 10:02:27.15 00:00:00:00 00:00:15:12
		'''
		lines = open(edl_path)
		data = lines.readlines()
		
		pattern_numb = '[0-9]'
		pattern_tc = '^(\d{2,})(\:|\.|\;)(\d{2})(\:|\.|\;)(\d{2})(\:|\.|\;)(\d{2})$'
						
		for line in data:						
			element = re.split(r"[ ]+", line)
			if re.match(pattern_numb,element[0]): #第一位是數字						
				for mat in element:	
					if mat!='':										
						if re.match(pattern_tc,mat.strip()): #且這一行裡面有符合tc的元素							
							self.file_list.append(element[1].strip())										
							break
  
		print('EDL Has ' + str(len(self.file_list)) + ' Clips')	
		#去掉重複的	
		self.file_list = self.tool_removeRpt(self.file_list)	
		print('EDL Has ' + str(len(self.file_list)) + ' No Repeat Clips')
		
		return True
	
	
	def b1_chkbox_onlycopy(self,name):
		flag_goon = False						
		
		if self.chkbox_only=='Y' and self.input_only!='' and name.find('.') >= 0:								
											
			tmp = name.rsplit(".",1) #只做一次，從右邊										
			find_ext = tmp[1]
			if self.input_only.find(',') >= 0: #逗號分格的副檔名	
				
				tmp = self.input_only.split(",") 
				for only_ext in tmp:
					if find_ext.lower() == only_ext.strip().lower(): #只要有一個符合就可以繼續下去
						flag_goon = True										
				
			else:				
				if find_ext.lower() == self.input_only.strip().lower():	#這樣才要繼續下去。									
					flag_goon = True
					
		else: #沒有這些條件檢查就直接進行
			flag_goon = True
			
		return flag_goon
	
	def b2_chkbox_onlyNOTcopy(self,name):
		flag_goon = True		
								
		if self.chkbox_only_not=='Y' and self.input_only_not!='' and name.find('.') >= 0:									
			tmp = name.rsplit(".",1) #只做一次，從右邊						
			ext = tmp[1]
			if self.input_only_not.find(',') >= 0:  # 逗號分格的副檔名
				tmp = input_only_not.split(",") 
				for only_ext in tmp:
					if ext.lower() == only_ext.strip().lower(): #只要有一個符合就不可以繼續下去
						flag_goon = False										
	      
			else:
				if ext.lower() == self.input_only_not.strip().lower():	#這樣才要繼續下去。	      
					flag_goon = False
      
		else: #沒有這些條件檢查就直接進行
			flag_goon = True				
			
		return flag_goon	
		
	def b1_genCopyScriptForFile(self,idx):		
		name = self.foundInFile_name[idx]
		root = self.foundInFile_root[idx]
		
		flag_goon = False
		if self.chkbox_only=='Y' and self.input_only!='' and name.find('.') >= 0:	
			flag_goon = self.b1_chkbox_onlycopy(name)
		elif self.chkbox_only_not=='Y' and self.input_only_not!='' and name.find('.') >= 0:
			flag_goon = self.b2_chkbox_onlyNOTcopy(name)																			
		else:
			flag_goon = True	
		
		if flag_goon:			
			to_path = self.copy_to_path	
			if self.kpDir=='Y':	# 要保留路徑
				to_path = self.copy_to_path + root.replace(self.copy_from_path,'') 
				
				if not os.path.exists(to_path):
					os.makedirs(to_path)		
					
				if to_path[-1] == '/':
					to_path = to_path + name
				else:
					to_path = to_path + '/' + name											
												
			if self.chksum=='Y': # 要校驗拷貝										
				script = "rsync -arvhcP " + os.path.join(root,name) + " " + to_path
			else:
				script = "rsync -arvhP " + os.path.join(root,name) + " " + to_path				

			self.copy_script.append(script)	
		
	def b1_genCopyScriptForDir(self,idx):
		name = self.foundInDir_name[idx]
		root = self.foundInDir_root[idx]
		
		to_path = self.copy_to_path			
		# 保留路徑
		if self.kpDir=='Y':	# 要保留路徑
			to_path = self.copy_to_path + root.replace(self.copy_from_path,'') 
			if not os.path.exists(to_path):
				os.makedirs(to_path)
			if to_path[-1] == '/':
				to_path = to_path + name + "/"
			else:
				to_path = to_path + "/" + name + "/"
		else:
			if to_path[-1] == '/':
				to_path = to_path + name + "/"
			else:
				to_path = to_path + "/" + name + "/"
												
		
		# 校驗拷貝
		if self.chksum=='Y': 										
			script = "rsync -arvhcP " + os.path.join(root,name)+"/" + " " + to_path
		else:			
			script = "rsync -arvhP " + os.path.join(root,name)+"/" + " " + to_path
			
		self.copy_script.append(script)
		
	
	def b_genCopyScript(self): 				
		store_from_path = []
		for clip in self.file_list:
			print('--------FIND:' + clip)
							
			for root, directories, files in os.walk(self.copy_from_path, topdown=True):	
				for name in directories:					
					
					if name.find('.') >= 0: #路徑中有點的，只要找尋的檔案在其中一個.之間的就可以，但是要完全符合
						namePart = name.split('.')
						for part in namePart:
							if part == clip:
								
								self.foundInDir.append(os.path.join(root,name)+'/')			
								self.foundInDir_root.append(root)					
								self.foundInDir_name.append(name)
								print("dir (has .)=>root:"+root +"<-name:"+ name + "<-")													
								
					else: #路徑沒有點的，完全符合才可以，也要管大小寫
						if name == clip:
							 
							self.foundInDir.append(os.path.join(root,name)+name+'/')	
							self.foundInDir_root.append(root)					
							self.foundInDir_name.append(name)							
							print("dir =>root:"+root +"<-name:"+ name + "<-")
			    					
				for name in files:						
					
					if name.find('.') >= 0: #檔案名有點的，只要找尋的檔案在其中一個.之間的就可以，但是要完全符合	
						namePart = name.split('.')
						for part in namePart:
							if part == clip:
								self.foundInFile.append(os.path.join(root,name))	
								self.foundInFile_root.append(root)					
								self.foundInFile_name.append(name)							
								print("file =>root:"+root +"<-name:"+ name + "<-")
								
					else:
						if name == clip:
							self.foundInFile.append(os.path.join(root,name))	
							self.foundInFile_root.append(root)					
							self.foundInFile_name.append(name)							
							print("file =>root:"+root +"<-name:"+ name + "<-")			
			
			print("-----Check Every Clip")
			self.b4_compareDirFile()

		return self.copy_script
	
	
	def b4_compareDirFile(self):
		if len(self.foundInDir) > 0: #才需要繞回圈			
			for index,f in enumerate(self.foundInFile):					
				for d in self.foundInDir:
					if f.find(d) >= 0 : #file有全包含 d的，就把file的刪掉
						self.foundInFile.pop(index)
						self.foundInFile_root.pop(index)
						self.foundInFile_name.pop(index)		
			
			for index,f in enumerate(self.foundInFile):
				print('file:' + f + ' index:' + str(index))
				self.b1_genCopyScriptForFile(index)
				
			for index,d in enumerate(self.foundInDir):
				print('dir :' + d + ' index:' + str(index))
				self.b1_genCopyScriptForDir(index)
										
		else:
									
			for index,f in enumerate(self.foundInFile):
				print('file:' + f + ' index:' + str(index))
				self.b1_genCopyScriptForFile(index)
				
			
		self.foundInDir.clear()
		self.foundInDir_root.clear()
		self.foundInDir_name.clear()
		
		self.foundInFile.clear()
		self.foundInFile_root.clear()
		self.foundInFile_name.clear()
		
		
	def c_exeScript(self):
		print('--------CMD:')
		for cmd in self.copy_script:
			print(cmd)
			try:
				os.system(cmd)
				self.has_copied += 1
			except:
				print("-----------Exec Exception Occurs in :" + cmd)
				self.err_msg.append("-----------Exec Exception Occurs in :" + cmd)
		print(str(self.has_copied) + 'Command Exec Complete')
		return True
		
	
	def d_wrtieMsgLog(self):
		# Write Exec Log
		writer = open(self.exec_log_path, 'w+')
		for line in self.copy_script:
			writer.write(line+"\n")
		writer.close()
		
		# Write Notice Log
		writer = open(self.info_log_path, 'w+')
		for line in self.err_msg:
			writer.write(line+"\n")
		writer.close()
		
		return True
	
	def e_clearVar(self):
		self.file_inlist_count = 0
		self.has_copied = 0
	
		self.file_list.clear()
		self.copy_script.clear()	
		self.err_msg.clear()
		
		return True
	

	

	