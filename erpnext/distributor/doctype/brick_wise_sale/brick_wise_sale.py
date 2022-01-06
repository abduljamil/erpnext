# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt
import re
import frappe
from frappe.utils import getdate
import pdfplumber
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