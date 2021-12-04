# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt
import re
import frappe
import pdfplumber
from frappe.model.document import Document
from fuzzywuzzy import fuzz

class BrickWiseSale(Document):
	pass
@frappe.whitelist(allow_guest=True)
def parse_pdf(pdf_file,dist_city):
	tt_list = frappe.db.get_all('Territory',fields=['territory_name','parent_territory'],as_list=True)
	# print(tt_list)
	item_list = frappe.db.get_all('Item',fields=['name','item_name','trade_price','item_type','item_power'],as_list=True)
	# print(item_list)
	arr = re.split('/',pdf_file);
	path = frappe.get_site_path(arr[1],arr[2],arr[3]);
	with pdfplumber.open(path) as pdf:
		if dist_city == 'Lahore':
			full_array = []
			for x in range(0,len(pdf.pages)):
				data = pdf.pages[x].extract_text()
				data = re.sub("\n",",", data)
				data = data.split(',')
				for y in data:
					# first_data = re.sub("\n",",",y)
					aplha1 = 'PRODUCT NAME';
					aplha2 = 'AFLOXAN';
					aplha3 = 'JETEPAR';
					aplha4 = 'MAIORAD';
					aplha5 = 'MILID';
					if aplha1 in y or aplha2 in y or aplha3 in y or aplha4 in y or aplha5 in y:
						array = y.split('|')
						array.pop()
						array.pop(0)
						without_empty_string = []
						for string in array:
							if (string != '          '): ## 10 spaces in pdf
								without_empty_string.append(string)
							else:
								string = '0'
								without_empty_string.append(string)
						if(len(without_empty_string)>1):
							full_array.append(without_empty_string)
			#trim the first index  
			for a in full_array:
				a[0] = re.sub(r"\s\s+", " ", a[0])
			# trim the string
			for t in full_array:
				if t[0] == ' PRODUCT NAME PACK ':
					for i in range(len(t)):
						t[i] = t[i].strip()
			
			# print(full_array)
			# loop to correct the bricks name
			for b in full_array:
				if b[0] == 'PRODUCT NAME PACK':
					for c in range(len(b)):
						for t in tt_list:
							if b[c] == 'C.M.H':
								b[c] = 'COMBINED MILITARY HOSPITAL'
							elif b[c] == 'L.G.H':
								b[c] = 'LAHORE GENERAL HOSPITAL'
							elif b[c] in t[0]:
								b[c] = t[0]
							elif b[c]== 'S.Z.HOSPIT':
								b[c] = 'SHEIKH ZAID HOSPITAL'
							elif b[c] == 'G.T ROAD M':
								b[c]= 'GT ROAD MANAWA'
							elif b[c] == 'R.A.BAZAR':
								b[c] = 'R A BAZAR'
							elif b[c] == 'AL-FAISAL':
								b[c] =  'AL FAISAL TOWN'
							elif b[c] == 'GULSHAN-E-':
								b[c] = 'GULSHAN E RAVI'
							elif b[c] == 'BAIGAM KOT':
								b[c] = 'BAIGUM KOT'
			# print(full_array)
			# define the item code with array so  that we can replace the name of item with code which auto get item name#define item code
			item_code = ['008376','017230','002392','002188','004348','008999','012961','009072']
			#change item name with code 
			for c in full_array:
				if c[0]=='AFLOXAN Cap 2X10S ':
					c[0] = item_code[0]
				if c[0]=='AFLOXAN Tab 300MG 3X10S ':
					c[0] = item_code[1]
				if c[0]=='JETEPAR Cap. 20s ':
					c[0] = item_code[2]
				if c[0]=='JETEPAR syp.112ml 112ML ':
					c[0] = item_code[3]
				if c[0]=='JETEPAR Inj.2ml 10s ':
					c[0] = item_code[4]
				if c[0]=='JETEPAR INJ.10ml 5s ':
					c[0] = item_code[5]
				if c[0]=='MAIORAD TAB. 30S ':
					c[0] = item_code[6]
				if c[0]=='MAIORAD INJ.3ML 6S ':
					c[0] = item_code[7]
			## remove item row from array which not contain sale
			filter_array = full_array## remove zero with sale value which show bonus
			#only get integer without bonus
			for f in filter_array:
				for i in range(len(f)):
					if type(f[i])==str:
						f[i] = f[i].strip()
						f[i] = re.sub("\s+(0)","",f[i])
			for a in range(0,len(filter_array)):
				if  filter_array[a][0]=='PRODUCT NAME PACK' and filter_array[a][len(filter_array[a])-1]=='TOTAL':
					for i in range(0,11):
						filter_array[a+i].pop()
			# print(filter_array)
			# remove rows which not contain anny sale
			final_array = []
			for c in filter_array:
				arr=c[1:len(c)]
				if all(v == 0 for v in arr):
					pass
				else:
					final_array.append(c)
			
			
			result = []
			names = None
			for data in final_array:
				if data[0] == "PRODUCT NAME PACK":
					names = data[1:]
				else:
					index = data[0]
					for name, number in zip(names, data[1:]):
						result.append( [index, name, number] )
			
			## get parent territory of brick
			for element in result:
				for e in range(0,len(element)):
					for t in tt_list:
						if element[e] == t[0]:
							element.append(t[1])
			#get item name and price 
			for i in item_list:
				for b in result:
					for a in range(0,len(b)):
						if i[0]==b[a]:
							b.insert(a+1,i[1])
							b.append(i[2])
			
					
			# print(result)
			return result;
		##Sheikhupura 
		elif dist_city== 'Sheikhupura':
			products = []
			sales = []
			result = []
			for x in range(0,len(pdf.pages)):
				data = pdf.pages[x].extract_table()
				# print(data[x][0])
				if type(data)!=type(None) and data[x][0]== 'Product Name':
					for i in range(2,len(data)-2):
						products.append(data[i][0])
					# print(products)
					bricks = data[0][2:]
					# print(bricks)
					for p in range(0,len(products)):
						sales.append(data[2+p][2:])
					# print(sales)
			for s in sales:
				for i in range(0,len(s)):
					if s[i] =='':
						s[i] = '0'
			# print(products )
			# print(bricks)
			db_bricks = ['SHEIKHU PURA', 'FAROOQA ABAD','KHANQAH DOGRAN','SUKHE KE','PINDI BHATTIAN','SAFDARA ABAD','MANA WALA',
						'WARBUR TON','NANKANA SAHIB','BUCHEKI','MORE KHUNDA','FAIZA BAD','SHARIQ PUR','BEGUM KOT',
						'MURIDKEE','NARANG MANDI','JANDIALA SHER KHAN']
			bricks = db_bricks
			for i in range(0,len(products)):
				for j in range(0,len(bricks)):
					child = []
					product = products[i]
					child.append(product)
					brick = bricks[j]
					child.append(brick)
					sale = sales[i][j]
					child.append(sale)
					result.append(child)
			# print(len(result))
			## makes array according to data model
			for r in result:
				for i in item_list:
					if r[0] == 'MAIROAD INJ':
						r[0] = '009072'
					if r[0] == 'MAIROAD TAB':
						r[0] = '012961'
					percent = fuzz.token_set_ratio(r[0],i[1])
					if percent >= 80:
						r[0] = i[0]
			for r in result:
				for i in item_list:
					percent = fuzz.token_set_ratio(r[0],i[1])
					if percent >= 72:
						r[0] = i[0]
			# name and price
			for r in result:
				for i in item_list:
					if r[0] == i[0]:
						r.insert(1,i[1])
						r.append(i[2])
			# print(len(result))
			# for brick parent
			for r in result:
				for t in tt_list:
					if r[2] == t[0]:
						r.insert(4,t[1]) ## insert brick parent into index 4
			return result
		elif dist_city == 'Kasur':
			products = []
			sales = []
			bricks =[]
			for x in range(0,len(pdf.pages)):
				data = pdf.pages[x].extract_table()
				# print("1",data[0][-1])
				if data[0][-1] != 'Total':
					child_brick = data[0][2:]
					bricks.append(child_brick)
					for i in range(1,len(data)-2): ## for skipping total row
						products.append(data[i][1])
						sales.append(data[i][2:])
				else:
					child_brick = data[0][2:-1]
					bricks.append(child_brick)
					for j in range(1,len(data)-2):
						products.append(data[j][1]) 
						sales.append(data[j][2:-1])
			for b in bricks:
				for c in range(0,len(b)):
					if b[c] == 'BPH':
						b[c] = 'BHAI PHERU'
					if b[c] == 'CHM':
						b[c] = 'CHANGA MANGA'
					if b[c] == 'CHN':
						b[c] = 'CHUNIAN'
					if b[c] == 'HBA':
						b[c] = 'HABIB ABAD'
					if b[c] == 'KAH':
						b[c] = 'KAH NA'
					if b[c] == 'KHD':
						b[c] = 'KHUDIAN KHAS'
					if b[c] == 'KNP':
						b[c] = 'KANGAN PUR'
					if b[c] == 'KRK':
						b[c] = 'KOT RADHA KISHAN'
					if b[c] == 'KS2':
						b[c] = 'KASUR 2'
					if b[c] == 'KSR':
						b[c] = 'KASUR 1'
					if b[c] == 'MGM':
						b[c] = 'MANGA MANDI'
					if b[c] == 'MTA':
						b[c] = 'MUSTAFA ABAD'
					if b[c] == 'MUW':
						b[c] = "MANDI USMAN WALA"
					if b[c] == 'PTK':
						b[c] = 'PATTO KI'
					if b[c] == 'RWD':
						b[c] = 'RAI WIND'
					if b[c] =='THM':
						b[c] = 'THENG MORE'    # print(bricks)    
			## set sale value only
			for s in sales:
				for i in range(0,len(s)):
					index = s[i].index('\n')
					s[i] = s[i][:index]
					if s[i] == '-':
						s[i] = '0'    
			result=[]
			zipped_list=[]
			for s in sales:
				for b in bricks:
					if len(b)== len(s):
						zipped_values = zip(b, s)
						zipped_list.append(list(zipped_values))
			for z in range(0,len(zipped_list)):
				for l in range(0,len(zipped_list[z])):
					zipped_list[z][l]= list(zipped_list[z][l])
					zipped_list[z][l].insert(0,products[z])
					zipped_list[z][l] = tuple(zipped_list[z][l])
			# print(zipped_list)
			final_list = [item for z in zipped_list for item in z]
			# print(final_list) 
		## make array a/c  data model
			end_result = []
			for r in final_list:
				for i in item_list:
					if r[0] == 'MAIORAD 3ML INJ':
						r= list(r)
						r[0] = '009072'
						r = tuple(r)
						end_result.append(r)
					if r[0] == 'MAIORAD TAB':
						r= list(r)
						r[0] = '012961'
						r= tuple(r)
						end_result.append(r)
					percent = fuzz.token_set_ratio(r[0],i[1])
					if percent >= 80:
						r = list(r) 
						# print(r[0],i[1])
						r[0] = i[0]
						r = tuple(r)
						# print(r)
						end_result.append(r)
			# # name and price
			for r in range(0,len(end_result)):
				for i in item_list:
					if end_result[r][0] == i[0]:
						end_result[r]= list(end_result[r])
						end_result[r].insert(1,i[1])
						end_result[r].append(i[2])
			# print(end_result)
			# # for brick parent
			for r in range(0,len(end_result)):
				for t in tt_list:
					if end_result[r][2] == t[0]:
						end_result[r].insert(4,t[1]) ## insert brick parent into index 4
			return end_result