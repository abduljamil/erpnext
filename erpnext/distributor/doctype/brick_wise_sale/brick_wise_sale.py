# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt
from dis import distb
import re
import frappe
from frappe.utils import getdate
import pdfplumber
import fitz
import pandas as pd 
from frappe.model.document import Document
from frappe import publish_progress
from fuzzywuzzy import fuzz
import json
scope_obj = "" 
class BrickWiseSale(Document):
	pass

@frappe.whitelist(allow_guest=True)
def parse_pdf(pdf_file,parent_detail):
	parent_details = json.loads(parent_detail)
	dist_city = parent_details["city"]
	# print(doc)
	try:
		doc = frappe.get_last_doc('Brick Wise Sale',filters={"city":dist_city})
		first_date = doc.get("from")
		second_date = parent_details["fromDate"]
		new_record = getdate(second_date)
		if first_date == new_record:
			name = doc.get("name")
			frappe.delete_doc("Brick Wise Sale",name)
	except:
		pass
	tt_list = frappe.db.get_all('Territory',fields=['territory_name','parent_territory'],as_list=True)
	# print(tt_list)
	item_list = frappe.db.get_all('Item',fields=['name','item_name','trade_price','item_type','item_power'],as_list=True)
	# print(item_list)
	arr = re.split('/',pdf_file)
	path = frappe.get_site_path(arr[1],arr[2],arr[3])
	if dist_city =='Gujrat':
		result = []
		products = ['008376','017230','008999','004348','002392','002188','009072','012961']
		bricks = []
		sales = []
		sales1 = []
		b_condition = True
		p_condition = False
		b_s_index  = 36
		b_e_index  = 0
		s_s_index = 0

		doc = fitz.open(path)
		page1 = doc[0]
		words = page1.get_text("words")
# print(words[i][4])
		for i in range(0,len(words)):
			# print(words[i][4])
			if words[i][4] == 'Product':
				b_s_index  = i+1
			if '------' in words[i][4] and b_condition == True and i > b_s_index   :
					b_e_index  = i
					s_s_index = i+1
					b_condition = False
					p_condition = True
					
			if '-------' in words[i][4] and p_condition == True and i > b_e_index :
					s_e_index  = i
					p_condition = False
					# print(s_s_index)
		for k in range(b_s_index ,b_e_index ):
			bricks.append(words[k][4])
		# print(bricks)

		for b in range(0,len(bricks)):
			bricks[b] = re.sub('LALAM','LALAMUSA',bricks[b])
			bricks[b] = re.sub('KHARI','KHARIAN',bricks[b])
			bricks[b] = re.sub('DINGA','DINGA GUJRAT',bricks[b])
			bricks[b] = re.sub('FATEP','FATEH PUR',bricks[b])
			bricks[b] = re.sub('PHALI','PHALIA GRT',bricks[b])
			bricks[b] = re.sub('KING[+]','KING ROAD',bricks[b])
			bricks[b] = re.sub('S.ALA','ALA',bricks[b])
			bricks[b] = re.sub('M.B.D','MBD GUJRAT',bricks[b])
			bricks[b] = re.sub('MANGO','MANGOWAL',bricks[b])
			bricks[b] = re.sub('KUNJA','KUNJAH',bricks[b])
			bricks[b] = re.sub('J.P.J','JALAL PUR JATTAN',bricks[b])
			bricks[b] = re.sub('PAHRI','PAHRIANWALI',bricks[b])
			

		# print(bricks)

		for i in range(s_s_index,s_e_index):
			if words[i][0] > 100:
				# sales1 = []
				sales1.append(words[i][4])
				difference_ = words[i+1][0]-words[i][0]
				if difference_ > 42.76:
					num_zeros = int(difference_/40)
					for k in range(1,num_zeros+1):
						sales1.insert(i+k,'0')
			else:
				if words[i][0]  == 6.75:
					sales.append(sales1)
					sales1 = []

		sales=sales[1:-1]
		# print(difference_)
		for i in range(0,len(sales)):
			add_zeros = 14 - len(sales[i])
			# print((sales[i]))
			# print(add_zeros)
			for k in range(0,add_zeros):
				sales[i].append('0')
			# print((sales[i]))

		for p in range(0,len(products)):
			for s in range(0,len(sales[p])):
				child = []
				child.append(products[p])
				child.append(bricks[s])
				child.append(sales[p][s])
				result.append(child)
		# print(len(result))

		for r in result:
			for i in item_list:
				if r[0] == i[0]:
					r.insert(1,i[1])
					r.append(i[2]) 
					# print(r)
		for r in result:
			for t in tt_list:
				if r[2] == t[0]:
					r.insert(4,t[1])
					# print(r)
		# print(result)
		return result
		 
	else:
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
								elif b[c] == 'SANDA':
									b[c] = 'SANDA LAHORE'
								elif b[c] == 'SHAHNOOR':
									b[c] = 'SHAH NOOR'
								elif b[c] == 'SHADMAN':
									b[c] = 'SHAD MAN'
								elif b[c] ==  'SAMANABAD':
									b[c] = 'SAMANA BAD'
								elif b[c] ==  'SAMANAABD':
									b[c] = 'SAMANA ABAD'
								elif b[c] ==  'BAIGAM KOT':
									b[c] = 'BAIGUM KOT'
								elif b[c] ==  'TEZAB AAHATA':
									b[c] = 'TEHZAB AAHATA'
								elif b[c] ==  'JALLO PIND':
									b[c] = 'JALLO PARK'
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
					if c[0] =='MILID TAB.400MG 30S':
						pass
					elif c[0] == 'MILID TAB.200MG 30S':
						pass
					elif all(v == 0 for v in arr):
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
				

				# # print(x)
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
					# size = 10
					# progress = x / size * 100
					# publish_progress(percent=progress, title="Reading the file")
				
				for s in sales:
					for i in range(0,len(s)):
						if s[i] =='':
							s[i] = '0'
				# print(products )
				# print(bricks)
				db_bricks = ['SHEIKHU PURA', 'FAROOQA ABAD','KHANQAH DOGRAN','SUKHE KE','PINDI BHATTIAN','SAFDARA ABAD','MANA WALA',
							'WARBUR TON','NANKANA SAHIB','BUCHEKI','MORE KHUNDA','FAIZA BAD','SHARAK PUR','BEGUM KOT',
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
			elif dist_city == 'Okara':
				products = []
				bricks = []
				sales = []
				result = []
				for x in range(0,len(pdf.pages)):
					data = pdf.pages[x].extract_table()
					# print(data)
					for p in range(1,len(data)-2):
						products.append(data[p][1])
					for q in range(0,len(products)):
						index = products[q].index('{')
						products[q] = products[q][:index]
					for s in range(1,len(data)-2):
						sale = data[s][2:-1]
						sales.append(sale)
					# print(sales)        bricks = data[0][2:-1]
				new_bricks = ['AKHTER ABAD','BANGLA GOGERA','BASIR PUR','DEPAL PUR','DEPAL PUR CHOWK','DHA 1', 'DHA 2','FAISLA ABAD ROAD','CANTT','HABIB ABAD','HAVELI LAKHA','HOSPITAL BAZAR','HUJRA CITY','JABOKA','MANDI AHMED ABAD','RAJO WAL','RENALA KHURD CITY','SAHIWAL ROAD','SIRKI']
				bricks = new_bricks
				for p in range(0,len(products)):
					for b in range(0,len(bricks)):
						child = []
						child.append(products[p])
						child.append(bricks[b])
						child.append(sales[p][b])
						result.append(child)
			# print(result)
				for r in result:
					for i in item_list:
						final_result = fuzz.token_set_ratio(r[0],i[1])
						if final_result >= 80:
							r[0] = i[0]
				for r in result:
					for i in item_list:
						final_result = fuzz.token_set_ratio(r[0],i[1])
						if final_result >= 75:
							r[0] = i[0]    
							# print(r)    
				for r in result:
					for i in item_list:
						final_result = fuzz.token_set_ratio(r[0],i[1])
						if final_result >= 70:
							r[0] = i[0]    
							# print(r)
				for r in result:
					for i in item_list:
						if r[0] == i[0]:
							r.insert(1,i[1])
							r.append(i[2])
				for r in result:
					for t in tt_list:
						if r[2] == t[0]:
							r.insert(4,t[1])
				return result
			elif dist_city == 'Karachi':
				result = []
				for x in range(0,len(pdf.pages)):
					products = []
					bricks = []
					sales = []
					data = pdf.pages[x].extract_table()
					product = data[0][1:]
					products.append(product)
					# print(products)
					for i in range(2,len(data)): ## for skipping total row
						bricks.append(data[i][0])
						sale = data[i][1:]
						sales.append(sale)
				for p in range(0,len(products)):
					products[p] = list(filter(None,products[p])) ##remove none value
				bricks = list(filter(None,bricks))
				for s in range(0,len(sales)):
					sales[s] = ['0' if x == '' else x for x in sales[s]] ## change '' with '0'
				only_sale = [sales[s] for s in range(0,len(sales)) if '\n' not in sales[s][0]]
				## remove the total of territory wise
				for p in products:
					for s in range(0,len(only_sale)):
						if len(only_sale[s])-len(p) == 1:
							only_sale[s] = only_sale[s][:-1]
				for b in range(0,len(bricks)):
					for s in range(0,len(only_sale[b])): 
						child = []
						child.append(products[0][s])
						child.append(bricks[b])
						# print(products[0][s])
						child.append(only_sale[b][s])
						result.append(child)
				print(result)
			elif dist_city=='Sahiwal':
				products = []
				bricks = []
				sales = []
				result = []
				for x in range(0,len(pdf.pages)):
					data = pdf.pages[x].extract_table()
					bricks =data[0][1:-2]
					for b in range(0,len(bricks)):
						if bricks[b] =='SWLCN':
							bricks[b] = 'SAHIWAL CENTER'
						if bricks[b] =='DHQ':
							bricks[b] = 'DISTRICT HEAD QUARTER HOSPITAL'
						if bricks[b] =='PAKPN':
							bricks[b] = 'PAK PATTAN'
						if bricks[b] =='ARIFW':
							bricks[b] = 'ARIFWALA'
						if bricks[b] =='IQNGR':
							bricks[b] = 'IQBAL NAGAR'
						if bricks[b] =='KASWL':
							bricks[b] = 'KASSOWAL'
						if bricks[b] =='QBLA':
							bricks[b] = 'QABOOLA'
						if bricks[b] =='CCI':
							bricks[b] = 'CHICHAWATNI'
						if bricks[b] =='GHABD':
							bricks[b] = 'GHAZIA ABAD'
						if bricks[b] =='HARPA':
							bricks[b] = 'HARAPPA'
							# print(b[l])
					# print(bricks)
					for p in range(2,len(data)-4):
						products.append(data[p][0]) 
						sales.append(data[p][1:-2])
					for i in sales:
						# print(i)
						for a in range(0,len(i)):
							# print(i[a])
							if i[a] == '':
								i[a] = '0'
					# print(bricks)
					for p in range(0,len(products)):
						for b in range(0,len(bricks)):
								# print(products[p],bricks[b],sales[p][b]
								child = []
								child.append(products[p])
								child.append(bricks[b])
								child.append(sales[p][b])
								result.append(child)
					# print(result)
					# for jetepar syrup and 2ml inj
					for r in result:
						if r[0] ==  'JETEPAR 2ML INJ 10S':
							r[0] = 'Jetepar Injection 2ml'
						if r[0] ==  'AFLOXAN 300MG TAB 30S':
							r[0] = 'Afloxan Tablet'
						if r[0] ==  "AFLOXAN CAP 20'S":
							r[0] = 'Afloxan Capsule'
						if r[0] ==  'JETEPAR 10ML INJ 5S':
							r[0] = 'Jetepar Injection 10ml'
						if r[0] ==  'JETEPAR CAP 20S':
							r[0] = 'Jetepar Capsule'
						if r[0] ==  'JETEPAR SYRUP 112ML':
							r[0] = 'Jetepar Syrup'
						if r[0] ==  'MAIORAD 3ML INJ 6S':
							r[0] = 'Maiorad Injection'
						if r[0] ==  'MAIORAD TAB 30S':
							r[0] = 'Maiorad Tablet'
						for i in item_list:
							final_result = fuzz.token_set_ratio(r[0],i[1])
							if final_result >= 100:
								r[0] = i[0]    
								# print(r)
					for r in result:
						for i in item_list:
							if r[0] == i[0]:
								r.insert(1,i[1])
								r.append(i[2])
					for r in result:
						for t in tt_list:
							if r[2] == t[0]:
								r.insert(4,t[1])
					return result
			elif dist_city == "Sialkot":
				bricks = []
				sales = []
				result = []
				products = ['008999','004348','002188','009072']
				for x in range(0,len(pdf.pages)):
					data = pdf.pages[x].extract_table()
					if x == len(pdf.pages)-1:
						for b in range(1,len(data)-3):
							bricks.append(data[b][1])
						
						for s in range(1,len(data)-3):
							sales.append(data[s][2:-1])
					else:
						for b in range(1,len(data)):
							bricks.append(data[b][1])
						for s in range(1,len(data)):
							sales.append(data[s][2:-1])
		# print(sales)
				for s in sales:
					for i in range(0,len(s)):
						if s[i] =='-':
							s[i] = '0'
							# print(s[i])
				# print(sales)

				for b in range(0,len(bricks)):
					if '1010101' in bricks[b] :
						bricks[b] = 'COMMISSIONER ROAD'
					if '1010105' in bricks[b] :
						bricks[b] = 'MURRAY COLLEGE ROAD'
					if '1010203' in bricks[b] :
						bricks[b] = 'DEFENCE ROAD SIALKOT'
					if '1010204' in bricks[b] :
						bricks[b] = 'SHAHAB PURA'
					if '1010208' in bricks[b] :
						bricks[b] = 'RODAS ROAD'
					if '1010219' in bricks[b] :
						bricks[b] = 'SARDAR BEGUM CHOWK'
					if '1010220' in bricks[b] :
						bricks[b] = 'ALAM CHOWK SHAHAB PURA ROAD'
					if '1010301' in bricks[b] :
						bricks[b] = 'ABBOTT ROAD'
					if '1010302' in bricks[b] :
						bricks[b] = 'PARIS ROAD'
					if '1010304' in bricks[b] :
						bricks[b] = 'GREEN WOOD STREET'
					if '1010305' in bricks[b] :
						bricks[b] = 'RAILWAY ROAD SIALKOT'
					if '1020104' in bricks[b] :
						bricks[b] = 'PASRUR ROAD 2'
					if '1010322' in bricks[b] :
						bricks[b] = 'KHADIM ALI ROAD'
					if '1010402' in bricks[b] :
						bricks[b] = 'PULL AIK'
					if '1010403' in bricks[b] :
						bricks[b] = 'PASRUR ROAD SIALKOT'
					if '1010404' in bricks[b] :
						bricks[b] = 'ZAFARWAL ROAD'
					if '1010406' in bricks[b] :
						bricks[b] = 'AIMNA ABAD ROAD'
					if '1010416' in bricks[b] :
						bricks[b] = 'ISLAMABAD MOHALLA'
					if '1010601' in bricks[b] :
						bricks[b] = 'GOHAD PUR / MURAD PUR ROAD'
					if '1010603' in bricks[b] :
						bricks[b] = 'KASHMIR ROAD SIALKOT'
					if '1010605' in bricks[b] :
						bricks[b] = 'CHRISTIAN TOWN / HUNTER PURA'
					if '1010701' in bricks[b] :
						bricks[b] = 'SADAR BAZAR CANTT SIALKOT'
					if '1010702' in bricks[b] :
						bricks[b] = 'JINNAH ISLAMIA COLLEGE ROAD'
					if '1010801' in bricks[b] :
						bricks[b] = 'KOTLI LOHARAN EAST'
					if '1010803' in bricks[b] :
						bricks[b] = 'DHALLE WALI'
					if '1010805' in bricks[b] :
						bricks[b] = 'KULLU WAL'
					if '1010806' in bricks[b] :
						bricks[b] = 'KAPUROWALI'
					if '1010810' in bricks[b] :
						bricks[b] = 'KOTLI LOHARAN WEST'
					if '1010901' in bricks[b] :
						bricks[b] = 'PULI TOP KHANA'
					if '1010902' in bricks[b] :
						bricks[b] = 'BHARTH'
					if '1010904' in bricks[b] :
						bricks[b] = 'MARAKI WAL'
					if '1010905' in bricks[b] :
						bricks[b] = 'KHAROTA SYEDAN'
					if '1010906' in bricks[b] :
						bricks[b] = 'SHADIWAL'
					if '1011001' in bricks[b] :
						bricks[b] = 'DALUWALI'
					if '1011002' in bricks[b] :
						bricks[b] = 'JHAI'
					if '1011003' in bricks[b] :
						bricks[b] = 'JUNG MORE'
					if '1011006' in bricks[b] :
						bricks[b] = 'SAID PUR'
					if '1011007' in bricks[b] :
						bricks[b] = 'GONDAL'
					if '1011009' in bricks[b] :
						bricks[b] = 'BAJ WAT'
					if '1011101' in bricks[b] :
						bricks[b] = 'DUBURJI MALIAN'
					if '1011103' in bricks[b] :
						bricks[b] = 'MIANI ADDA'
					if '1011104' in bricks[b] :
						bricks[b] = 'GHOYAN KI'
					if '1011105' in bricks[b] :
						bricks[b] = 'ADDA KAMAL PUR'
					if '1011106' in bricks[b] :
						bricks[b] = 'BHALLOWALI SIALKOT'
					if '1011205' in bricks[b] :
						bricks[b] = 'HAJI PURA'
					if '1011206' in bricks[b] :
						bricks[b] = 'RANGPURA'
					if '1011207' in bricks[b] :
						bricks[b] = 'CIRCULAR ROAD SIALKOT'
					if '1011208' in bricks[b] :
						bricks[b] = 'IMAM SAB'
					if '1020103' in bricks[b] :
						bricks[b] = 'NISBAT ROAD'
					if '1020105' in bricks[b] :
						bricks[b] = 'PULL NAHAR'
					if '1020106' in bricks[b] :
						bricks[b] = 'DASKA SIAL KOT'
					if '1020107' in bricks[b] :
						bricks[b] = 'SOHAWA STOP'
					if '1020108' in bricks[b] :
						bricks[b] = 'CIVIL HOSPITAL ROAD SIALKOT'
					if '1020202' in bricks[b] :
						bricks[b] = 'CHUNGI # 8'
					if '1020203' in bricks[b] :
						bricks[b] = 'COLLEGE ROAD SIAL KOT'
					if '1020207' in bricks[b] :
						bricks[b] = 'SAMBRIAL ROAD'
					if '1020301' in bricks[b] :
						bricks[b] = 'MOTRA'
					if '1020302' in bricks[b] :
						bricks[b] = 'ADAMKAY'
					if '1020303' in bricks[b] :
						bricks[b] = 'JAMKE CHEEMA'
					if '1020305' in bricks[b] :
						bricks[b] = 'BHOPAL WALA VILLAGE'
					if '1020402' in bricks[b] :
						bricks[b] = 'MUNDEKE GORAYA'
					if '1020403' in bricks[b] :
						bricks[b] = 'KOTLI BAWA'
					if '1030701' in bricks[b] :
						bricks[b] = 'MODEL TOWN UGOKI'
					if '1030702' in bricks[b] :
						bricks[b] = 'MAIN BAZAR UGOKI'
					if '1030705' in bricks[b] :
						bricks[b] = 'SHAHAB PURA CHOWK'
					if '1030706' in bricks[b] :
						bricks[b] = 'SUBLIME CHOWK'
					if '1030707' in bricks[b] :
						bricks[b] = 'FATEH GARH SIALKOT'
					if '1030708' in bricks[b] :
						bricks[b] = 'ADALAT GARH'
					if '1031001' in bricks[b] :
						bricks[b] = 'SAMBRIAL MORE'
					if '1031004' in bricks[b] :
						bricks[b] = 'LARI ADDA SIALKOT'
					if '1031005' in bricks[b] :
						bricks[b] = 'JETHI KAY ROAD'
					if '1031006' in bricks[b] :
						bricks[b] = 'BAIGO WALA SIALKOT'
					if '1040902' in bricks[b] :
						bricks[b] = 'MURIDKE ROAD'
					if '1040905' in bricks[b] :
						bricks[b] = 'QILA AHMED ABAD'
					if '1040907' in bricks[b] :
						bricks[b] = 'DHAMTHAL SIALKOT'
					if '1050801' in bricks[b] :
						bricks[b] = 'GALI ABSHAR WALI CHWND'
					if '1050804' in bricks[b] :
						bricks[b] = 'MAIN ROAD CHWND'
					if '1050901' in bricks[b] :
						bricks[b] = 'HAIDRI CHOWK'
					if '1050902' in bricks[b] :
						bricks[b] = 'MAIN ROAD BDN'
					if '1050903' in bricks[b] :
						bricks[b] = 'MAIN BAZAR BDN'
					if '1050904' in bricks[b] :
						bricks[b] = 'GUNNA BDN'
					if '1051001' in bricks[b] :
						bricks[b] = 'KACHEHRI ROAD'
					if '1051003' in bricks[b] :
						bricks[b] = 'KALAS WALA ROAD'
					if '1051006' in bricks[b] :
						bricks[b] = 'PURANA BAZAR'
					if '1051007' in bricks[b] :
						bricks[b] = 'CHAWINDA PHATAK'
					if '1060703' in bricks[b] :
						bricks[b] = 'RAIL WAY ROAD SKG'
					if '1060705' in bricks[b] :
						bricks[b] = 'NOOR KOT ROAD'
					if '1060706' in bricks[b] :
						bricks[b] = 'DARMAN ROAD'
					if '1070803' in bricks[b] :
						bricks[b] = 'LANGRE WALI'
					if '1070807' in bricks[b] :
						bricks[b] = 'ADDA MAHAL'
					if '1070808' in bricks[b] :
						bricks[b] = 'SALAN KAY'
					if '1070809' in bricks[b] :
						bricks[b] = 'MEH RAJKE'
					if '1070811' in bricks[b] :
						bricks[b] = 'CHAUBARA'
					if '1070813' in bricks[b] :
						bricks[b] = 'PHALORA'
					if '1070814' in bricks[b] :
						bricks[b] = 'SIALKOT BHAGOWAL'
					if '1070815' in bricks[b] :
						bricks[b] = 'GOPAL PUR'

				for s in range(0,len(sales)):
					for i in range(0,len(sales[s])):
						# print(products[i],bricks[s],sales[s][i])
					

						child = []
						child.append(products[i])
						child.append(bricks[s])
						child.append(sales[s][i])
						result.append(child)

				for r in result:
					for i in item_list:
						if r[0] == i[0]:
							r.insert(1,i[1])
							r.append(i[2])
							# print(r)
				for r in result:
					for t in tt_list:
						if r[2] == t[0]:
							r.insert(4,t[1])
							# print(r)

				# print(len(bricks))
				return result
			elif dist_city == "Narowal":
				products = []
				bricks = []
				sales = []
				result = []
				for x in range(0,len(pdf.pages)):
					data = pdf.pages[x].extract_table()
					products.append(data[0][1:-1])
					for i in range(1,len(data)-1):
						bricks.append(data[i][0])
						sales.append(data[i][1:-1])
			# print(products)
				for p in range(0,len(products)):
					for i in range(0,len(products[p])):
						if '006003' in products[p][i] :
							products[p][i] = '002392'
						if '006004' in products[p][i] :
							products[p][i] = '008999'
						if '006005' in products[p][i] :
							products[p][i] = '004348'
						if '006006' in products[p][i] :
							products[p][i] = '002188'
						if '006022' in products[p][i] :
							products[p][i] = '005425'
						if '006025' in products[p][i] :
							products[p][i] = '081838'
						if '006026' in products[p][i] :
							products[p][i] = '023906'
						if '006027' in products[p][i] :
							products[p][i] = '031037'
						if '006031' in products[p][i] :
							products[p][i] = '008909'
						if '006032' in products[p][i] :
							products[p][i] = '081274'
						if '006034' in products[p][i] :
							products[p][i] = '038426'
						if '006035' in products[p][i] :
							products[p][i] = '006784'
						if '006036' in products[p][i] :
							products[p][i] = '008908'
						if '006037' in products[p][i] :
							products[p][i] = '006782'
						if '006038' in products[p][i] :
							products[p][i] = '006783'
						if '006039' in products[p][i] :
							products[p][i] = '012649'
						if '006040' in products[p][i] :
							products[p][i] = '019133'
						if '006041' in products[p][i] :
							products[p][i] = '016654'
						if '006042' in products[p][i] :
							products[p][i] = '032255'
						if '006043' in products[p][i] :
							products[p][i] = '029328'
						if '006044' in products[p][i] :
							products[p][i] = '024820'
						if '006047' in products[p][i] :
							products[p][i] = '028728'
						if '006050' in products[p][i] :
							products[p][i] = '026920'
						if '006052' in products[p][i] :
							products[p][i] = '006406'
				# print(products)
		
		
				for b in range(0,len(bricks)):
					if '1010101' in bricks[b] :
						bricks[b] = 'DHA NAROWAL'
					if '1010102' in bricks[b] :
						bricks[b] = 'KUTCHERY ROAD'
					if '1010103' in bricks[b] :
						bricks[b] = 'RAILWAY ROAD NAROWAL'
					if '1010104' in bricks[b] :
						bricks[b] = 'ZAFARWAL ROAD NAROWAL'
					if '1010105' in bricks[b] :
						bricks[b] = 'MURIDKE ROAD'
					if '1010201' in bricks[b] :
						bricks[b] = 'NURKOT'
					if '1010202' in bricks[b] :
						bricks[b] = 'JASSAR'
					if '1010203' in bricks[b] :
						bricks[b] = 'BUSTAN'
					if '1010205' in bricks[b] :
						bricks[b] = 'KANJRUR'
					if '1010207' in bricks[b] :
						bricks[b] = 'SHAKARGHAR CITY'
					if '1010208' in bricks[b] :
						bricks[b] = 'ZAFAR WAL'
					if '1010301' in bricks[b] :
						bricks[b] = 'DHAM THAL'
					if '1010302' in bricks[b] :
						bricks[b] = 'SANKHATRA'
					if '1010303' in bricks[b] :
						bricks[b] = 'PINDI BORI'
					if '1010304' in bricks[b] :
						bricks[b] = 'DERMAN'
					if '1010305' in bricks[b] :
						bricks[b] = 'ZAFARWAL CITY'
					if '1010307' in bricks[b] :
						bricks[b] = 'NONAR NAROWAL'
					if '1010308' in bricks[b] :
						bricks[b] = 'NONAR NAROWAL'
					if '1010309' in bricks[b] :
						bricks[b] = 'SHAH GREEB'
					if '1010311' in bricks[b] :
						bricks[b] = 'DHABLI WALA'
					if '1010401' in bricks[b] :
						bricks[b] = 'DOMALA VILLAGE'
					if '1010402' in bricks[b] :
						bricks[b] = 'QILA AHMEDABAD NAROWAL'
					if '1010404' in bricks[b] :
						bricks[b] = 'PASRUR NAROWAL'
					if '1010405' in bricks[b] :
						bricks[b] = 'CHAWINDA'
					if '1010501' in bricks[b] :
						bricks[b] = 'TALWANDI'
					if '1010502' in bricks[b] :
						bricks[b] = 'ADA SIRAJ'
					if '1010503' in bricks[b] :
						bricks[b] = 'QILA KALLAR WALA'
					if '1010504' in bricks[b] :
						bricks[b] = 'BADDO MALHI'
				# print(bricks)

				for s in range(0,len(sales)):
					for i in range(0,len(sales[s])):
						if sales[s][i] == '-':
							sales[s][i] = '0'
				products= [item for sublist in products for item in sublist]

				for s in range(0,len(sales)):
					for i in range(0,len(sales[s])):
						child = []
						child.append(products[i])
						child.append(bricks[s])
						child.append(sales[s][i])
						result.append(child)

				for r in result:
					for i in item_list:
						if r[0] == i[0]:
							r.insert(1,i[1])
							r.append(i[2])
				#              # print(r)
				for r in result:
					for t in tt_list:
						if r[2] == t[0]:
							r.insert(4,t[1])
				# print(result)
				return result
			elif dist_city == "Gujranwala":
				result = []
				products = ['008999','004348','002392','002188','009072','012961']
				brick = []
				sale = []
				sales = []
				bricks = []
				for x in range(0,len(pdf.pages)):
					# print(pdf.pages[0].lines)
					data = pdf.pages[x].extract_text()
					# print(data)
					data = re.sub("\n","$", data)
					# print(data)
					# data = re.sub(r"\s\s+","",data)
					data = data.split('$')
					# print(data)
					if x == len(pdf.pages)-1: # condition for lat page
						# print("page 2")
						for x in range(6,len(data)-5):
							data[x] = re.sub(r"\s\s+","#",data[x]) # search for double sapce and put # after it
							data[x] = data[x].split('#')  # split line after # and convert into different element in an array
							data[x] = data[x].pop(0) # remove the second element from array
							# print(data[x]) 
							brick = re.sub('[0-9]+','',data[x])
							# data = data.split(',')
							bricks.append(brick)
							sale = re.findall('[0-9]+', data[x])
							sales.append(sale)
							# print(sales)
					else:
						# print('page 1')
						for x in range(8,len(data)-1):
							data[x] = re.sub(r"\s\s\s+","#",data[x])
							data[x] = data[x].split('#')
							data[x] = data[x].pop(0)
							# print(data[x])  
							brick = re.sub('[0-9]+','',data[x])
							bricks.append(brick)        
							sale = re.findall('[0-9]+', data[x])
							sales.append(sale)
							# print(sales)
				for b in range(0,len(bricks)):
					bricks[b] = re.sub(r"\s\s\s+","#",bricks[b])
					bricks[b] = bricks[b].split("#")
					bricks[b] = bricks[b].pop(0)
					if bricks[b] == "HOSPITAL  ROAD":
						bricks[b] = "HOSPITAL ROAD"
					if bricks[b] == "SIALKOT RAOD":
						bricks[b] = "SIALKOT ROAD GUJRANWALA"
					if bricks[b] == "SHAHEEN ABAD  -":
						bricks[b] = "SHAHEEN ABAD"
					if bricks[b] == "SIALKOT RAOD":
						bricks[b] = "SIALKOT ROAD"
					if bricks[b] == "EMAN ABAD -":
						bricks[b] = "EMAN ABAD"
					if bricks[b] == "GAKHAR -":
						bricks[b] = "GAKHAR"
					if bricks[b] == "Sialkot":
						bricks[b] = "SIALKOT ROAD GUJRANWALA"
				# print(bricks)
				for b in range(0,len(bricks)):
					for p in range(0,len(products)):
						child = []
						child.append(products[p])
						child.append(bricks[b])
						child.append(sales[b][p])
						result.append(child)
				
				for r in result:
					for i in item_list:
						if r[0] == i[0]:
							r.insert(1,i[1])
							r.append(i[2])
							# print(r)
				for r in result:
						for t in tt_list:    
							if r[2] == t[0]:
								r.insert(4,t[1])
								# print(r)
				# print(result)
				return result
			elif dist_city == "Mandi Bahauddin":
				result = []
				products = []
				bricks = []
				sales = []
				for x in range(0,len(pdf.pages)):
					data = pdf.pages[x].extract_table()
					bricks = data[0][1:14]
					if x == len(pdf.pages)-1:
						for d in range(1,len(data)-2):
							sales.append(data[d][1:14])
							if d == len(data)-3:
								products.append('081274')
							elif d == len(data)-4:
								products.append('008909')  
							else:
								products.append(data[d][0])

					else:
						for d in range(1,len(data)):
							if data[d][0] != 'BLUE':
								sales.append(data[d][1:14])
								products.append(data[d][0])
				# print(len(products))

				for b in range(0,len(bricks)):
					if bricks[b] == 'KUT.SH':
						bricks[b] = 'KUTHYALA SYEDAN'
					if bricks[b] == 'MALIK.':
						bricks[b] = 'MALAKWAL'
					if bricks[b] == 'QADIF':
						bricks[b] = 'QADIRABAD'
				# print(bricks)

				for s in range(0,len(sales)):
					for i in range(0,len(sales[s])):
						if sales[s][i] == '':
							sales[s][i] = '0'

				for p in range(0,len(products)):
					for s in range(0,len(sales[p])):
						if bricks[s] == '':
							continue
						child = []
						child.append(products[p])
						child.append(bricks[s])
						child.append(sales[p][s])
						result.append(child)
				# print(result)
    
				for r in range(0,len(result)):
					if 'MAIORAD INJ 6AMP' in result[r][0]:
						result[r][0] = '009072'
					if 'JETEPAR 2ML INJ 10AMP' in result[r][0]:
						result[r][0] = '004348'
					if 'JETEPAR CAP 20CAP' in result[r][0]:
						result[r][0] = '002392'
					if 'JETEPAR 10ML/INJ 5AMP' in result[r][0]:
						result[r][0] = '008999'
					if 'MAIORAD 100MG TAB 30TAB' in result[r][0]:
						result[r][0] = '012961'
					if 'AFLOXAN 150MG CAP 20CAP' in result[r][0]:
						result[r][0] = '008376'
					if 'AFLOXAN 300MG TAB 30TAB' in result[r][0]:
						result[r][0] = '017230'
					if 'MOXILIUM 250GM 60ML' in result[r][0]:
						result[r][0] = '012649'
					if 'MOXILIUM 250CAP 20CAP' in result[r][0]:
						result[r][0] = '006784'
					if 'EBAST 10MG TAB 10TAB' in result[r][0]:
						result[r][0] = '023906'
					if 'MINQAIR 5MG TAB 14TAB' in result[r][0]:
						result[r][0] = '038426'
					if 'MINQAIR 10MG TAB 14TAB' in result[r][0]:
						result[r][0] = '038427'
					if 'SUPRACEF 100MG SYRP 30ML' in result[r][0]:
						result[r][0] = '024819'
					if 'PROBITOR 20MGCAP 14CAP' in result[r][0]:
						result[r][0] = '016654'
					if 'TRAMAGESIC INJ 5AMP' in result[r][0]:
						result[r][0] = '026920'
					if 'JETEPAR SYRUP 112ML' in result[r][0]:
						result[r][0] = '002188'
					if 'MOXILIUM 125SUSPEN 45ML' in result[r][0]:
						result[r][0] = '006783'
					if 'VIKONON FORTE SYRUP 120ML' in result[r][0]:
						result[r][0] = '006406'
					if 'MOXILIUM 500MG CAP 20CAP' in result[r][0]:
						result[r][0] = '008908'
					if 'MOXILIUM DROPES 10ML' in result[r][0]:
						result[r][0] = '006782'
					if 'PC-LAC SYRUP 120ML' in result[r][0]:
						result[r][0] = '019133'
					if 'VIGROL FORTE 50TAB' in result[r][0]:
						result[r][0] = '007018'
					if 'CYANORIN FORTE 25AMP' in result[r][0]:
						result[r][0] = '005425'
					if 'HISTAFEX 120MG TAB 10TAB' in result[r][0]:
						result[r][0] = '031037'
					if 'SAVELOX 250MG TAB 10TAB' in result[r][0]:
						result[r][0] = '032255'
					if 'SAVELOX 500MG TAB 10TAB' in result[r][0]:
						result[r][0] = '029328'
					if 'SUPRALOX 50ML' in result[r][0]:
						result[r][0] = '028728'
					if 'SUPRACEF 400MG CAP 5CAP' in result[r][0]:
						result[r][0] = '024820'
					if 'TRAMAGESIC 50MG 20CAP' in result[r][0]:
						result[r][0] = '029327'
					if 'DEPROGESIC -P 10TAB' in result[r][0]:
						result[r][0] = '081838'
					if 'AVOR 2MG TAB 100TAB' in result[r][0]:
						result[r][0] = '007853'
				# print(result)
    
				for r in result:
					for i in item_list:
						if r[0] == i[0]:
							r.insert(1,i[1])
							r.append(i[2])
							# print(r)
				for r in result:
					for t in tt_list:    
						if r[2] == t[0]:
							r.insert(4,t[1])
							# print(r)
				# print(result)
				return result
			elif dist_city =="Mardan":
				result = []
				products = [] 
				products1 = []
				bricks = []
				sales = []
				n_sales = []
				for x in range(0,len(pdf.pages)):
					
					data = pdf.pages[x].extract_tables()
					# print(data)
					bricks = data[0]
					# print(bricks)
					index1 = bricks[0].index('')
					# print(index1)
					if index1 == 8:
						products1 = ['008999','002188','004348','002392']
					if index1 == 14:
						products1 = ['008999','002188','004348','002392','009072']
					if index1 == 15:
						products1 = ['008376','008999','002188','004348','002392','009072']

					bricks = [b for b in bricks[0][1:index1]]
					# print(bricks)
					for c in range(0,len(bricks)):
						bricks[c] = re.sub('\n','',bricks[c])
						bricks[c] = re.sub('SHAWAADDA[+]N','SHEWA ADDA',bricks[c])
						bricks[c] = re.sub('SHAHMANSOO','SHAHMANSOOR',bricks[c])
						bricks[c] = re.sub('M.CPLAZA','MC PLAZA',bricks[c])
						bricks[c] = re.sub('MIRAFZALKHA','MIR AFZAL KHAN',bricks[c])
						bricks[c] = re.sub('HOSPITALROA','HOSPITAL ROAD MDN',bricks[c])
						bricks[c] = re.sub('PARHOTI','PAR HOTI',bricks[c])
						bricks[c] = re.sub('RASHAKI','RASHAKAI',bricks[c])
						bricks[c] = re.sub('M.M.C','MARDAN MEDICAL COMPLEX',bricks[c])
						bricks[c] = re.sub('COLLAGECHO','COLLEGE CHOWK',bricks[c])
						bricks[c] = re.sub('GHARIKAPOOR','GHARI KAPURA',bricks[c])
						bricks[c] = re.sub('NEWADDARET','NEW ADDA RETAIL',bricks[c])
						bricks[c] = re.sub('NEWADDAWHO','NEW ADDA WHOLESALE',bricks[c])
						bricks[c] = re.sub('B-R-WS','BANK ROAD WHOLESALE',bricks[c])
						bricks[c] = re.sub('SHEDANOBAR','SHEDAN BAZAR',bricks[c])
						bricks[c] = re.sub('T.BAI','TAKHT BHAI',bricks[c])
						bricks[c] = re.sub('LUNDKHUR','LUND KHWAR',bricks[c])
						bricks[c] = re.sub('DAKI[+]SHAKNO','DAKI AND SHAKNO',bricks[c])
					data1 = pdf.pages[x].extract_text()
					# split the data at new line
					data1 = re.sub("\n","$", data1)
					data1 = data1.split('$')
					# print(data1)
					# extracting only first sale from table because tabl doesn't get it
					for i in range(16,len(data1)-3):
						data1[i] = re.sub(r"\s\s+","#",data1[i])
						data1[i] = data1[i].split('#')
						products.append(data1[i][0])
						# print(n_sales)
					sal = []
					sales2=[]
					sal = data[1]
					# print(sal[0])
					for c in range(0,len(sal)-2):
						sales2 = sal[c][0:index1-1]
						sales.append(sales2)
				data1 = data1[16][1:index1]
				sales.insert(0,data1) 
    
				for p in range(0,len(products1)):
					for s in range(0,len(sales[p])):
						child = []
						child.append(products1[p])
						child.append(bricks[s])
						child.append(sales[p][s])
						result.append(child)
				for r in result:
					for i in item_list:
						if r[0] == i[0]:
							r.insert(1,i[1])
							r.append(i[2])
				#             # print(r)
				for r in result:
						for t in tt_list:    
							if r[2] == t[0]:
								r.insert(4,t[1])
								# print(r)
				return result
			elif dist_city =="Timergara":
				result = []
				products = []
				bricks = []
				sales = []
				data = pdf.pages[0].extract_table()
				for i in range(0,len(data)):
					bricks = data[0][3:-1]
					
					if data[i][1] == None:
						pass
					else:
						products.append(data[i][1])
						sales.append(data[i][3:-1])
				for i in range(0,len(products)):
					bricks[i] = re.sub('TIMERGARA','TIMERGARA TMG',bricks[i])
				for i in range(0,len(products)):
					# products2[i] = re.sub('\n','',products2[i])
					products[i] = re.sub('AFLOXAN CAP','008376',products[i])
					products[i] = re.sub('AFLOXAN TAB 300MG','017230',products[i])
					products[i] = re.sub('JETEPAR 10ML AMP','008999',products[i])
					products[i] = re.sub('JETEPAR 2ML AMP:','004348',products[i])
					products[i] = re.sub('JETEPAR CAPS','002392',products[i])
					products[i] = re.sub('JETEPAR SYP','002188',products[i])
					products[i] = re.sub('MAIORAD 3ML AMP','009072',products[i])
					products[i] = re.sub('MAIORAD TAB','012961',products[i])
				for s in range(0,len(sales)):
					for i in range(0,len(sales[s])):
						if sales[s][i] == '':
							sales[s][i] = '0' 
				# print(bricks)
				# print(products)
				# print(sales)	
				for p in range(0,len(products)):
					for s in range(0,len(sales[p])):
						child = []
						child.append(products[p])
						child.append(bricks[s])
						child.append(sales[p][s])
						result.append(child)
				for r in result:
					for i in item_list:
						if r[0] == i[0]:
							r.insert(1,i[1])
							r.append(i[2]) 
				for r in result:
					for t in tt_list:
						if r[2] == t[0]:
							r.insert(4,t[1])
				return result
			elif dist_city == "Bannu":
				products = []
				sales = []
				bricks = []
				result = []
				for x in range(0,len(pdf.pages)):
					data = pdf.pages[x].extract_table()
					# print(data)
					products.append(data[1][1:-1])
					# print(products)
					for i in range(2,len(data)-1):
						sales.append(data[i][1:-1])
				# print(sales)
						bricks.append(data[i][0])
				# print(bricks)
					for k in range(0,len(bricks)):
						bricks[k] = bricks[k][8:]
						if bricks[k] == 'BANNU':
							bricks[k] = 'BANNU MAIN'
						if bricks[k] == 'MIRANSHAH':
							bricks[k] = 'MIRAN SHAH'
						if bricks[k] == 'LAKKI':
							bricks[k] = 'LAKKI MARWAT'
				# print(bricks)
    
				for p in range(0,len(products)):
					for i in range(0,len(products[p])):
						# print(products[p][i])
						# if '' in products[p][i]:
						if '014010' in products[p][i]:
							products[p][i] = '005425'
						if '014011' in products[p][i]:
							products[p][i] = '081838'
						if '014013' in products[p][i]:
							products[p][i] = '023906'
						if '014021' in products[p][i]:
							products[p][i] = '008999'
						if '014022' in products[p][i]:
							products[p][i] = '004348'
						if '014023' in products[p][i]:
							products[p][i] = '002188'
						if '014024' in products[p][i]:
							products[p][i] = '002392'
						if '014025' in products[p][i]:
							products[p][i] = '009072'
						if '014027' in products[p][i]:
							products[p][i] = '071560'
						if '014030' in products[p][i]:
							products[p][i] = '081274'
						if '014033' in products[p][i]:
							products[p][i] = '038427'
						if '014035' in products[p][i]:
							products[p][i] = '006783'
						if '014036' in products[p][i]:
							products[p][i] = '012649'
						if '014037' in products[p][i]:
							products[p][i] = '012649'
						if '014038' in products[p][i]:
							products[p][i] = '008908'
						if '014039' in products[p][i]:
							products[p][i] = '006782'
						if '014040' in products[p][i]:
							products[p][i] = '032259'
						if '014041' in products[p][i]:
							products[p][i] = '019133'
						if '014042' in products[p][i]:
							products[p][i] = '016654'
						if '014043' in products[p][i]:
							products[p][i] = '032255'
						if '014044' in products[p][i]:
							products[p][i] = '029328'
						if '014045' in products[p][i]:
							products[p][i] = '024819'
						if '014046' in products[p][i]:
							products[p][i] = '028727'
						if '014048' in products[p][i]:
							products[p][i] = '028728'
						if '014049' in products[p][i]:
							products[p][i] = '026920'
						if '014052' in products[p][i]:
							products[p][i] = '006406'
				# print(products)
				for s in range(0,len(sales)):
					for i in range(0,len(sales[s])):
						if sales[s][i] == '-':
							sales[s][i] = '0'
			# print(sales)
				for s in range(0,len(sales)):
					for i in range(0,len(sales[s])):
						# print(products[i][p],bricks[s],sales[s][i])
						# print(products[p][i],bricks[s],sales[s][i])
						child = []
						child.append(products[p][i])
						child.append(bricks[s])
						child.append(sales[s][i])
						result.append(child)
				# print(result)
				# print(bricks)
				for r in result:
					for i in item_list:
						if r[0] == i[0]:
							r.insert(1,i[1])
							r.append(i[2])
							# print(r)
				#print(result)
				for r in result:
					for t in tt_list:    
						if r[2] == t[0]:
							r.insert(4,t[1])
							#print(r)
				return result
			elif dist_city == "Dera Ismail Khan":
				result = []
				products = ['008999','004348','002392','002188','009072','012961']
				
				bricks = ['D.I.KHAN','TANK','WANA','PAHAR','DRABAN/CHOD','PROVA/RAMAK','JANDOLA','ZAFAR','PEZU/PANYALA',
				'NEW DERA','MAKEEN',]

				sales = []

				data = pdf.pages[0].extract_table()
				for x in range(0,len(data)):
					# print(data[x][0:11])
					sales.append(data[x][0:11])
				# print(sales)
				for b in range(0,len(bricks)):
					if bricks[b] == 'PAHAR':
						bricks[b] = 'PAHAR PUR'
					if bricks[b] == 'DRABAN/CHOD':
						bricks[b] = 'DRABAN'
					if bricks[b] == 'PROVA/RAMAK':
						bricks[b] = 'PROVA'
					if bricks[b] == 'PEZU/PANYALA':
						bricks[b] = 'PANI ALA'
    
				for s in range(0,len(sales)):
					for i in range(0,len(sales[s])):
						if sales[s][i] == '':
							sales[s][i] = '0'
				for p in range(0,len(products)):
					for s in range(0,len(sales[p])):
						child = []
						child.append(products[p])
						child.append(bricks[s])
						child.append(sales[p][s])
						result.append(child)
      
				for r in result:
					for i in item_list:
						if r[0] == i[0]:
							r.insert(1,i[1])
							r.append(i[2])
						# print(r)

				for r in result:
					for t in tt_list:    
						if r[2] == t[0]:
							r.insert(4,t[1])
							# print(r)
				# print(result)
				return result
			elif dist_city == "Abbotabad":
				result = []
				products = []
				bricks = []
				sales = []
				sales1 = []
				for x in range(0,len(pdf.pages)):
					data = pdf.pages[x].extract_table()
					products = data[0][1:-1]
					sales = data[1:-1]
					for i in range(0,len(products)):
						products[i] = re.sub('\n','',products[i])
						if products[i] == '001001 JETEPAR SYP':
							products[i] = '002188'
						if products[i] == '001003 JETEPAR 2ML AMP':
							products[i] = '004348'
						if products[i] == '001004 JETEPAR 10ML AMP':
							products[i] = '008999'
						if products[i] == '001008 MAIORAD 3ML AMP':
							products[i] = '009072'
						if products[i] == '001002 JETEPAR CAP':
							products[i] = '002392'
				for i in range(0,len(sales)):
					bricks.append(sales[i][0])
					bricks[i]=bricks[i][10:]
					sales[i] = sales[i][1:-1]
				for i in range(0,len(bricks)):
					if bricks[i] == 'BUTTGRAM':
						bricks[i] = 'BATTAGRAM'
					if bricks[i] == 'SHINKIARI/BUFFA':
						bricks[i] = 'SHINKIARI'
					if bricks[i] == 'GARI/BALLAKOT':
						bricks[i] = 'GARI BALLAKOT'
					if bricks[i] == 'DERBAND':
						bricks[i] = 'DARBAND'
					if bricks[i] == 'BATTAL/CHATTAR':
						bricks[i] = 'BATTAL AND CHATTAR'
				for s in range(0,len(sales)):
					for i in range(0,len(sales[s])):
						if sales[s][i] == '-':
							sales[s][i] = '0' 
				for s in range(0,len(sales)):
					for i in range(0,len(sales[s])):
						# print(products[i][p],bricks[s],sales[s][i])
						# print(products[p][i],bricks[s],sales[s][i])
						child = []
						child.append(products[i])
						child.append(bricks[s])
						child.append(sales[s][i])
						child.append('ABD')
						result.append(child)
				for r in result:
					for i in item_list:
						if r[0] == i[0]:
							r.insert(1,i[1])
							r.append(i[2])
							# print(r)
				return result
			elif dist_city =="Chakwal":
				result = []
				products = []
				bricks = []
				sales = []
				for x in range(0,len(pdf.pages)):
					data = pdf.pages[x].extract_table()
					bricks=data[0][1:-1]
					for i in range(0,len(bricks)):
						bricks[i] = re.sub('\n','',bricks[i])
						bricks[i] = re.sub('CHOA SHAYDIAYN BELT','CHOA SAIDANSHAH',bricks[i])
						bricks[i] = re.sub('DHUDIAL BELT','DHUDYAL',bricks[i])
						bricks[i] = re.sub('KALAR KAHAR TOWN','KALAR KAHAR',bricks[i])
						bricks[i] = re.sub('TALAGANG BELT','TALAGANG',bricks[i])
					for i in range(1,len(data)-5):
						# print(data[i])
						if data[i][0] != None:
							# print('hi')
							products.append(data[i][0])
							sales.append(data[i][1:-1])
							# print(data[i])
					# print(products)
					for i in range(0,len(sales)):
						products[i] = re.sub('JETEPAR 10ML AMP','008999',products[i])
						products[i] = re.sub('JETEPAR 2ML AMP','004348',products[i])
						products[i] = re.sub('JETEPAR CAP','002392',products[i])
						products[i] = re.sub('JETEPAR SYP','002188',products[i])
						for k in range(0,len(sales[i])):
								x = re.split("\n", sales[i][k], 1)
								sales[i][k] = x[0]
								if sales[i][k] == '':
									sales[i][k] = '0'
					# print(sales)
					# print(products)
     
				for s in range(0,len(sales)):
					for i in range(0,len(sales[s])):
						child = []
						child.append(products[s])
						child.append(bricks[i])
						child.append(sales[s][i])
						child.append('CWL')
						result.append(child)
				for r in result:
					for i in item_list:
						if r[0] == i[0]:
							r.insert(1,i[1])
							r.append(i[2])
							# print(r)
				return result
			elif dist_city == "Kohat":
				result = []
				bricks = ['KOHAT 1','HANGU','DOABA','THALL','KOHAT 2','KOHAT 3','ALIZAI AND BAGHAN','PARACHINAR','BANDA DAUD SHAH','LACHI','GUMBAT','KOHAT DEVELOPMENT AUTHORITY']
				products = []
				sales = []
				for x in range(0,len(pdf.pages)):
					data = pdf.pages[x].extract_text()
					data = re.sub('\n',',',data)
					data = data.split(',')
					
					data = data[9:-3]
					# print(data)
					for i in range(0,len(data)):
						data[i] = re.sub('\s\s+',',',data[i])
						data[i] = data[i].split(',')
						products.append(data[i][0][1:]) 
						sales.append(data[i][1:-2])
				
				for i in range(0,len(products)):
					products[i] = re.sub('987 AFLOXAN CAP','008376',products[i])
					products[i] = re.sub('983 JETEPAR 10ML INJ','008999',products[i])
					products[i] = re.sub('986 JETEPAR 120ML SYP','002188',products[i])
					products[i] = re.sub('984 JETEPAR 2ML INJ','004348',products[i])
					products[i] = re.sub('052 JETEPAR 2ML INJ NEW','004348',products[i])
					products[i] = re.sub('985 JETEPAR CAP','002392',products[i])
					products[i] = re.sub('973 JETEPAR SYP NEW','002188',products[i])
					products[i] = re.sub('989 MAIORAD AMPS','009072',products[i])
					products[i] = re.sub('990 MAIORAD TAB','012961',products[i])
				for p in range(0,len(products)):
					for s in range(0,len(sales[p])):
						child = []
						child.append(products[p])
						child.append(bricks[s])
						child.append(sales[p][s])
						result.append(child)

				for r in result:
					for i in item_list:
						if r[0] == i[0]:
							r.insert(1,i[1])
							r.append(i[2])

				for r in result:
					for t in tt_list:
						if r[2] == t[0]:
							r.insert(4,t[1])
				return result    
			elif dist_city == "Jhelum":
				result = []
				products = []
				bricks = []
				sales = []
				sales1 = []
				for x in range(0,len(pdf.pages)):
					data = pdf.pages[x].extract_table()
					products=data[0][1:-1]
					sales=data[1:-1]
					for i in range(0,len(products)):
						products[i] = re.sub('\n','',products[i])
						if products[i] == '004041 JETEPAR SYP':
							products[i] = '002188'
						if products[i] == '004039 JETEPAR 2ML INJ':
							products[i] = '004348'
						if products[i] == '004038 JETEPAR 10ML INJ':
							products[i] = '008999'
						if products[i] == '004045 MAIORAD INJ':
							products[i] = '009072'
						if products[i] == '004040 JETEPAR CAP':
							products[i] = '002392'      
					for i in range(0,len(sales)):
						bricks.append(sales[i][0][4:])
						if bricks[i][0]==' ':
							bricks[i] = bricks[i][1:]
						if bricks[i]=='JHELUM':
							bricks[i] = 'JHELUM JHL'
						if bricks[i]=='DADYAL & CHAKSWARI':
							bricks[i] = 'DADYAL AND CHAKSWARI'
						sales[i] = sales[i][1:-1]
				for s in range(0,len(sales)):
					for i in range(0,len(sales[s])):
						if sales[s][i] == '-':
							sales[s][i] = '0' 
				for p in range(0,len(bricks)):
					for s in range(0,len(sales[p])):
						child = []
						child.append(products[s])
						child.append(bricks[p])
						child.append(sales[p][s])
						child.append('JHL')
						result.append(child)   

				for r in result:
					for i in item_list:
						if r[0] == i[0]:
							r.insert(1,i[1])
							r.append(i[2])
				return result
			elif dist_city == "Rawalpindi":
				products = []
				sales = []
				bricks = []
				result = []
				for x in range(0,len(pdf.pages)):
					data = pdf.pages[x].extract_table()
					products.append(data[0][1:-1])
					if x == len(pdf.pages)-1:
						for i in range(1,len(data)-1):
							sales.append(data[i][1:-1])
							bricks.append(data[i][0])
					else:
						for i in range(1,len(data)):
							sales.append(data[i][1:-1])
							bricks.append(data[i][0])
					if x == 1:
						for k in range(0,len(bricks)):
							bricks[k] = bricks[k][10:]
							if bricks[k] == 'MALL ROAD':
								bricks[k] = 'MALL ROAD RWL'
							if bricks[k] == 'CHAKWAL':
								bricks[k] = 'CHAKWAL RWL'
							if bricks[k] == 'ALI PURE FARASH':
								bricks[k] = 'ALI PUR FARASH'
				for p in range(0,len(products)):
					for i in range(0,len(products[p])):
						if '009001' in products[p][i]:
							products[p][i] = '002188'
						if '009002' in products[p][i]:
							products[p][i] = '002392'
						if '009003' in products[p][i]:
							products[p][i] = '004348'
						if '009004' in products[p][i]:
							products[p][i] = '008999'
						if '009008' in products[p][i]:
							products[p][i] = '009072'
					for s in range(0,len(sales)):
						for i in range(0,len(sales[s])):
							if sales[s][i] == '-':
								sales[s][i] = '0'
				for s in range(0,len(sales)):
					for i in range(0,len(sales[s])):
						child = []
						child.append(products[p][i])
						child.append(bricks[s])
						child.append(sales[s][i])
						result.append(child)
				for r in result:
					for i in item_list:
						if r[0] == i[0]:
							r.insert(1,i[1])
							r.append(i[2])
				for r in result:
					for t in tt_list:    
						if r[2] == t[0]:
							r.insert(4,t[1])
				return result
			elif dist_city == "Vehari":
				result = []
				products = []
				bricks = ['ADDA AREY WHEN','BUREWALA','CASH','CHAKRALA','DOKOTA','G.MORE','GAGGOO','KARAM PUR','LUDDAN',
				'MAILSI VIHARI','MITRO','NEW CHOWK','PAKHY MORE MACHIWAL','THINGI','TIBBA SULTANPUR','VEHARI','VIJHIANWALA']
				sales = []
				sales1 = []
				for x in range(0,len(pdf.pages)):
					data = pdf.pages[x].extract_table()
					data1 = data
					data = data[1:-2]
					if x == 0:
						for i in range(0,len(data)):
							products.append(data[i][1])
							sales.append(data[i][1:])
					else:
						if data1[0][-1] == "Total":
							for i in range(0,len(sales)):
								if sales[i][0] == data[i][1]:
									sales[i] = sales[i][1:] + data[i][2:-1]
						else:
							sales.append(data[i][1:])
				for s in range(0,len(sales)):
					for i in range(0,len(sales[s])):
						if sales[s][i] == '-':
							sales[s][i] = '0' 
				for i in range(0,len(products)):
					products[i] = re.sub('JETEPAR CAP 20s','002392',products[i])
					products[i] = re.sub('JETEPAR.10ML ING 5s','008999',products[i])
					products[i] = re.sub('JETEPAR SYP 120ml','002188',products[i])
					products[i] = re.sub('JETEPAR.2ML INJ 10s','004348',products[i])
				for p in range(0,len(products)):
					for s in range(0,len(sales[p])):
						child = []
						child.append(products[p])
						child.append(bricks[s])
						child.append(sales[p][s])
						child.append('VRI')
						result.append(child)
				for r in result:
					for i in item_list:
						if r[0] == i[0]:
							r.insert(1,i[1])
							r.append(i[2])
				return result
			elif dist_city == "Larkana":
				result = []
				bricks = []
				bricks3 = []
				products = []
				sales = []
				sales2 = []
				for x in range(0,len(pdf.pages)):
					data = pdf.pages[x].extract_tables()
					bricks = data[0]
					bricks = bricks[0]
					if x== 0:
						bricks1 = bricks[1:]
						products2 =data[1][0:-4]
						for i in range(0,len(products2)):
							products.append(products2[i][0])
							sales.append(products2[i])
					if x == 1:
						bricks3 = bricks[1:-2]
						for i in range(0,len(data)):
							for k in range(2,len(data[i])-4):
								sales2.append(data[i][k]) 
				bricks = bricks1 + bricks3
				for i in range(0,len(sales)):
					if sales[i][0] == sales2[i][0]:
						sales[i] = sales[i] + sales2[i][1:-2]
						sales[i] = sales[i][1:]
				for s in range(0,len(sales)):
					for i in range(0,len(sales[s])):
						if sales[s][i] == '':
							sales[s][i] = '0' 
				for i in range(0,len(products)):
					products[i] = re.sub('MAIORAD INJ 6S [(]TP: 83.53[)]','009072',products[i])
					products[i] = re.sub('JETEPAR 10.ML INJ 5S [(]TP: 224.26[)]','008999',products[i])
					products[i] = re.sub('JETEPAR SYRUP 112.ML [(]TP: 177.65[)]','002188',products[i])
					products[i] = re.sub('JETEPAR INJ 2ML 10S [(]TP: 142.21[)]','004348',products[i])
				for i in range(0,len(bricks)):
					bricks[i] = re.sub('BAHRM','BAHRAM',bricks[i])
					bricks[i] = re.sub('CIVIL','CIVIL HOSPITAL LARKANA',bricks[i])
					bricks[i] = re.sub('DAKHN','DAKHAN',bricks[i])
					bricks[i] = re.sub('KAMBR','QAMBAR',bricks[i])
					bricks[i] = re.sub('NAUDR','NAUDERO',bricks[i])
					bricks[i] = re.sub('RATOD','RATO DERO',bricks[i])
					bricks[i] = re.sub('S.Z.H','SHAIKH ZAYED HOSPITAL',bricks[i])
					bricks[i] = re.sub('B-ROD','BAKRANI ROAD',bricks[i])
					bricks[i] = re.sub('CATLE','CATTLE COLONY',bricks[i])
					bricks[i] = re.sub('POLIC','POLICE SHOPING CENTRE',bricks[i])
					bricks[i] = re.sub('MURAD','MUHALLA MURAD WAHAN',bricks[i])
					bricks[i] = re.sub('SHDKT','SHAHDADKOT',bricks[i])
					bricks[i] = re.sub('DAKHN','DAKHAN',bricks[i])
					bricks[i] = re.sub('NAUDR','NAUDERO',bricks[i])
					bricks[i] = re.sub('NASIR','NASIRABAD',bricks[i])
					bricks[i] = re.sub('EM-RO','EMPIRE ROAD',bricks[i])
					bricks[i] = re.sub('LAHOR','LAHORI MUHALLA',bricks[i])
					bricks[i] = re.sub('GAR-Y','GARI YASEEN',bricks[i])
					bricks[i] = re.sub('ARIJA','ARIJA VILLAGE',bricks[i])
					bricks[i] = re.sub('ARZ-B','ARZI BHUTTO',bricks[i])
					bricks[i] = re.sub('BKRNI','BAKRANI',bricks[i])
					bricks[i] = re.sub('BANGU','BANGULDERO',bricks[i])
					bricks[i] = re.sub('BRO-C','BERO CHANDIO',bricks[i])
					bricks[i] = re.sub('BHANS','BHAN SYEDABAD',bricks[i])
					bricks[i] = re.sub('DHAMR','DHAMRAH',bricks[i])
					bricks[i] = re.sub('GAJIK','GAJI KHUHAWAR',bricks[i])
					bricks[i] = re.sub('GRELO','GARELO',bricks[i])
					bricks[i] = re.sub('GAR-K','GARI KHUDA BUX',bricks[i])
					bricks[i] = re.sub('DADU','DADU LARKANA',bricks[i])
					bricks[i] = re.sub('HAKIM','HAKIM SHAH',bricks[i])
					bricks[i] = re.sub('HATI','HATTI',bricks[i])
					bricks[i] = re.sub('KN-SH','KHAIRPUR NATHAN SHAH',bricks[i])
					bricks[i] = re.sub('KAMBR','KAMBER',bricks[i])
					bricks[i] = re.sub('KHARO','KHAIRO DERO',bricks[i])
					bricks[i] = re.sub('KHANP','KHANPUR',bricks[i])
					bricks[i] = re.sub('ALLAH','ALLAH ABAD',bricks[i])
					bricks[i] = re.sub('GAJAN','GAJAN PUR CHOWK',bricks[i])
					bricks[i] = re.sub('JALIS','JAILES BAZAR',bricks[i])
					bricks[i] = re.sub('LADIE','LADIES JAIL',bricks[i])
					bricks[i] = re.sub('M-CHK','MIROKHAN CHOWK',bricks[i])
					bricks[i] = re.sub('NA-CH','NAUDERO CHOWK',bricks[i])
					bricks[i] = re.sub('NA-RO','NAUDERO ROAD',bricks[i])
					bricks[i] = re.sub('NAZAR','NAZAR MUHALLA',bricks[i])
					bricks[i] = re.sub('NISHT','NISHTAR ROAD',bricks[i])
					bricks[i] = re.sub('OLD-B','OLD BUS STAND',bricks[i])
					bricks[i] = re.sub('PK-CH','PAKISTANI CHOWK',bricks[i])
					bricks[i] = re.sub('PHUL','PHULL ROAD',bricks[i])
					bricks[i] = re.sub('RAMAT','RAHMAT PUR',bricks[i])
					bricks[i] = re.sub('SACHA','SACHAL COLONY',bricks[i])
					bricks[i] = re.sub('STATO','STATION ROAD',bricks[i])
					bricks[i] = re.sub('MADJI','MADEJI',bricks[i])
					bricks[i] = re.sub('MAHOT','MAHOTA',bricks[i])
					bricks[i] = re.sub('MROKN','MIROKHAN',bricks[i])
					bricks[i] = re.sub('PHULJ','PHULJI',bricks[i])
					bricks[i] = re.sub('PIARO','PIAROGOTH',bricks[i])
					bricks[i] = re.sub('QUBO','QUBO SAEED KHAN',bricks[i])
					bricks[i] = re.sub('RADHN','RADHAN',bricks[i])
					bricks[i] = re.sub('SAJWL','SAJAWAL',bricks[i])
					bricks[i] = re.sub('SEWHN','SEWHAN',bricks[i])
				for p in range(0,len(products)):
					for s in range(0,len(sales[p])):
						child = []
						child.append(products[p])
						child.append(bricks[s])
						child.append(sales[p][s])
						child.append('LRK')
						result.append(child)
				for r in result:
					for i in item_list:
						if r[0] == i[0]:
							r.insert(1,i[1])
							r.append(i[2])
				return result
			elif dist_city == "Peshawar":
				products = []
				products1 = []
				p_sales = []
				d_sales = []
				sales = []
				bricks = []
				bricks1 = []
				result = []
				new_result = []
				for x in range(0,len(pdf.pages)):
					data = pdf.pages[x].extract_table()
					if data[0][-1] == 'Total Amount':
						products.append(data[0][1:-1])
					else:
						products.append(data[0][1:])
					for i in range(0,len(data)):
						if data[0][-1] == 'Total Amount' and data[-1][0] == 'Total':
							if i == 0 or i == len(data)-1:
								pass
							else:
								
								if data[i][0] not in bricks:
									p_sales.append(data[i][:])
									bricks.append(data[i][0])
								else:
									d_sales.append(data[i][:-1])
						elif data[0][-1] == 'Total Amount':
							if i == 0:
								pass
							else:
								
								if data[i][0] not in bricks:
									p_sales.append(data[i][:])
									bricks.append(data[i][0])
								else:
									d_sales.append(data[i][:-1])
						elif data[-1][0] == 'Total':
							if i == 0 or i == len(data)-1:
								pass
							else:
								
								if data[i][0] not in bricks:
									p_sales.append(data[i][:])
									bricks.append(data[i][0])
								else:
									d_sales.append(data[i][:-1])
						else:
							if i == 0:
								pass
							else:
								
								if data[i][0] not in bricks:
									bricks.append(data[i][0])
									p_sales.append(data[i][:])
								else:
									d_sales.append(data[i][:-1])
				for i in range(0,len(p_sales)):
					if p_sales[i][0] == d_sales[i][0]:
						p_sales[i] = p_sales[i]+d_sales[i][1:]
					sales.append(p_sales[i][1:])
     
				for i in range(0,len(bricks)):
					bricks1.append(bricks[i][10:])
					bricks1[i] = re.sub('\n','',bricks1[i])
					bricks1[i] = re.sub('QUDRAT ELAHI MARKET','QUDRAT ELAHI',bricks1[i])
					bricks1[i] = re.sub('AL HAYAT MRKET','AL HAYAT MARKET',bricks1[i])
					bricks1[i] = re.sub('GHULAM SAID PLAZA','GHULAM SAID',bricks1[i])
					bricks1[i] = re.sub('SOEKARNO SQAURE','SOEKARNO SQUARE',bricks1[i])
					bricks1[i] = re.sub('KHYBER MEDICAL CENTR','KHYBER MEDICAL CENTER',bricks1[i])
					bricks1[i] = re.sub('RAHEEM MEDICAL','RAHEEM MEDICAL CENTER',bricks1[i])
					bricks1[i] = re.sub('BAZAR-E-KALAN','BAZAR E KALAN',bricks1[i])
					bricks1[i] = re.sub('K.T.H','KHYBER TEACHING HOSPITAL',bricks1[i])
					bricks1[i] = re.sub('LRH','LADY READING HOSPITAL',bricks1[i])
					bricks1[i] = re.sub('H.A.M.C','HAYATABAD MEDICAL COMPLEX',bricks1[i])
					bricks1[i] = re.sub('BADA BAIR','BADABER',bricks1[i])
					bricks1[i] = re.sub('NOTHIA','NOTHIA QADEEM',bricks1[i])
					bricks1[i] = re.sub('KHATAK MEDICAL CENTR','KHATAK MEDICAL CENTER',bricks1[i])
					bricks1[i] = re.sub('AL SHIFA SURG CENTER','AL SHIFA SURGICAL CENTER',bricks1[i])
					bricks1[i] = re.sub('KHUSHAAL CENTER','KHUSHAL CENTER',bricks1[i])
					bricks1[i] = re.sub('MOHMAND MEDICAL CENT','MOHMAND MEDICAL CENTER',bricks1[i])
					bricks1[i] = re.sub('RAHEEM MEDICAL CENTER CENTR','RAHEEM MEDICAL CENTER',bricks1[i])
					bricks1[i] = re.sub('SIKANDAR PURA','SIKANDER PURA',bricks1[i])
					bricks1[i] = re.sub('NASEER TEACHING HOSP','NASEER TEACHING HOSPITAL',bricks1[i])
					bricks1[i] = re.sub('TARANGZAI','TAURANG ZAI',bricks1[i])
					bricks1[i] = re.sub('KOHAT RAOD','KOHAT ROAD',bricks1[i])
					# bricks1[i] = re.sub('','',bricks1[i])
     
				products1.insert(1,products[0:int(len(products)/2)])
				products1 = [b for b in products1[0][:]]
    
				for i in range(1,len(products1)):
					products2 = products1[0]+products1[i]

				for i in range(0,len(products2)):
					products2[i] = re.sub('006002','028729',products2[i][0:6])
					products2[i] = re.sub('006003','005425',products2[i])
					products2[i] = re.sub('006004','023906',products2[i])
					products2[i] = re.sub('006009','038426',products2[i])
					products2[i] = re.sub('006011','008908',products2[i])
					products2[i] = re.sub('006012','006782',products2[i])
					products2[i] = re.sub('006013','006783',products2[i])
					products2[i] = re.sub('006014','012649',products2[i])
					products2[i] = re.sub('006015','019133',products2[i])
					products2[i] = re.sub('006017','032255',products2[i])
					products2[i] = re.sub('006020','028727',products2[i])
					products2[i] = re.sub('006021','024819',products2[i])
					products2[i] = re.sub('006022','028728',products2[i])
					products2[i] = re.sub('006023','029327',products2[i])
					products2[i] = re.sub('006024','026920',products2[i])
					products2[i] = re.sub('006025','007018',products2[i])
					products2[i] = re.sub('006026','006406',products2[i])
					products2[i] = re.sub('006041','008376',products2[i])
					products2[i] = re.sub('006042','017230',products2[i])
					products2[i] = re.sub('006043','008999',products2[i])
					products2[i] = re.sub('006044','004348',products2[i])
					products2[i] = re.sub('006045','002392',products2[i])
					products2[i] = re.sub('006046','002188',products2[i])
					products2[i] = re.sub('006047','009072',products2[i])
					products2[i] = re.sub('006048','012961',products2[i])
					products2[i] = re.sub('006064','035294',products2[i])
					products2[i] = re.sub('006065','035295',products2[i])
					products2[i] = re.sub('006068','032259',products2[i])
					products2[i] = re.sub('006069','081838',products2[i])
					products2[i] = re.sub('006070','081274',products2[i])
					products2[i] = re.sub('006071','008909',products2[i])
				for s in range(0,len(sales)):
					for i in range(0,len(sales[s])):
						if sales[s][i] == '-':
							sales[s][i] = '0'  

				for p in range(0,len(bricks1)):
					for s in range(0,len(sales[p])):
						child = []
						child.append(products2[s])
						child.append(bricks1[p])
						child.append(sales[p][s])
						result.append(child)
      
				for r in  range(0,len(result)):
					for i in item_list:
						if result[r][0] == i[0]:
							if result[r][2] != '0':
								new_result.append(result[r])  
							
				for r in  range(0,len(new_result)):
					for i in item_list:
						if new_result[r][0] == i[0]:
								new_result[r].insert(1,i[1])
								new_result[r].append(i[2]) 
				for r in new_result:
					for t in tt_list:
						if r[2] == t[0]:
							r.insert(4,t[1])
				return new_result
			elif dist_city == "Quetta":
				result = []
				products = []
				bricks = ['ALAM KHAN CHOWK','ALAMDAR ROAD','BARORI','QUETTA CANTONMENT','INSTITUTION','JINNAH ROAD KANDHARI BAZAR','HUDA SPINI ROAD','SABZAL ROAD','SIRKI ROAD GAWALMANDI CHOWK'
				,'LIAQAT BAZAR ARCHAR_FJ ROAD','MEKANGI ROAD','MISSION ROAD','OFF JINNAH ROAD','PASHTUN ABAD','PRINCE ROAD','SARIAB ROAD','SATELLITE TOWN QTA','ZARGON ROAD',
				'WHOLESALE QTA','CHAMAN','DALBANDIN','DUKKI','QILLA SIAFULLAH','KALAT','KHANOZAI','KHARAN','KHUZDAR','KUCHLACK','LORALAI','M_BAG','MASTUNG',
				'MACHH','NOSHKI','PISHIN','SANJAWI','SARANAN','SIBI','ZHOB','ZIARAT']
				sales = []
				sales1 = []
				sales2 = []
				sales3 = []
				for x in range(0,len(pdf.pages)):
					data = pdf.pages[x].extract_table()
					sales=data[2:-1]
					for i in range(0,len(sales)):
						products.append(sales[i][0])
						sales1.append(sales[i][2:-2])
						if products[i] == 'JETEPAR  SYP':
							products[i] = '002188'
						if products[i] == 'JETEPAR INJ. 2CC':
							products[i] = '004348'
						if products[i] == 'JETEPAR INJ. 10CC':
							products[i] = '008999'
						if products[i] == 'MAIORAD INJ':
							products[i] = '009072'
						if products[i] == 'JETEPAR CAPS':
							products[i] = '002392'
				for i in range(0,len(sales1)):
					sales2 = []
					for k in range(0,len(sales1[i])):
						if sales1[i][k]!=None:
							sales2.append(sales1[i][k])
					sales3.append(sales2)
					sales3[i].pop(19)
				for s in range(0,len(sales3)):
					for i in range(0,len(sales3[s])):
						if sales3[s][i] == '':
							sales3[s][i] = '0'
				for p in range(0,len(products)):
					for s in range(0,len(sales3[p])):
						child = []
						child.append(products[p])
						child.append(bricks[s])
						child.append(sales3[p][s])
						result.append(child)
				for r in result:
					for i in item_list:
						if r[0] == i[0]:
							r.insert(1,i[1])
							r.append(i[2])
							# print(r)
				for r in result:
					for t in tt_list:
						if r[2] == t[0]:
							r.insert(4,t[1])
							# print(r)
				return result

