# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt
from dataclasses import fields
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
class BrickWiseSale(Document):
	pass
@frappe.whitelist(allow_guest=True)
def parse_pdf(pdf_file,parse_check,parent_detail):
	parent_details = json.loads(parent_detail)
	dist_city = parent_details["city"]
	if not parse_check:
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
	arr = re.split('/',pdf_file)
	path = frappe.get_site_path(arr[1],arr[2],arr[3])
	green_items = frappe.db.get_all('Item',fields=['name','belong_to'] ,filters={'belong_to': "Green"})
	def green_team_bricks(result):
		for k in result:
			for i in green_items:
				if k[0] == i['name']:
					k[2] = k[2] + ' ' + 'GT'
		return result

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
		result = green_team_bricks(result)
		return result
	elif dist_city == "Sukkur":
		bricks = []
		data = []
		# data1 = []
		result = []
		sales = []
		products = []
		start_data_var = 1000
		Second_sheet_var = False
		df = pd.read_excel(path)
		if df.iat[1,0][71:83] == 'ABDUL HALEEM':
			Second_sheet_var = True
		# will append line with item name to bricks till TTL QTY
		for i in range(0,len(df)):
			if df.iat[i,0] == 'ITEM':
				start_data_var = i
				for x in range(1,len(df.columns)):
					if df.iat[i,x] == 'TTL QTY':
						break
					bricks.append(df.iat[i,x])

			# break main for loop when reach TTL QTY row
			#strip will remove extra empty spaces
			if (df.iat[i,0]).strip() == 'TTL QTY BLUE TEAM':
				break

			if  i > start_data_var+1:
				data = []
				for k in range(0,len(bricks)+1):
					data.append(str(df.iat[i,k]))
					# print(data1)
				products.append(data[0])
				sales.append(data[1:])

		for i in range(0,len(products)):

			if 'JETEPAR SYR' in products[i]:
				products[i] = '002188'
			if 'JETEPAR CAPSULE' in products[i]:
				products[i] = '002392'
			if 'MAIORAD INJ' in products[i]:
				products[i] = '009072'
			if 'JETEPAR 2ML' in products[i]:
				products[i] = '004348'
			if 'JETEPAR 10ML' in products[i]:
				products[i] = '008999'
			if 'AFLOXAN CAPSULE' in products[i]:
				products[i] = '008376'
			# if '' in products[i]:
			# 	products[i] = ''
			# if '' in products[i]:
			# 	products[i] = ''


		# print(bricks)
		for i in range(0,len(bricks)):
			if bricks[i] == 'A.PUR':
				bricks[i] = 'ADIL PUR'
			if bricks[i] == 'AWAHN':
				bricks[i] = 'ALI WAHAN'
			if bricks[i] == 'CLKTR' and Second_sheet_var == True:
				bricks[i] = 'CLOCK TOWER SKR2'
			if bricks[i] == 'CTCOR' and Second_sheet_var == True:
				bricks[i] = 'CITY COURT'
			if bricks[i] == 'CVSUK' and Second_sheet_var == True:
				bricks[i] = 'CIVIL SUKKUR SKR2'
			if bricks[i] == 'DHRKI':
				bricks[i] = 'DAHARKI'
			if bricks[i] == 'GHTKI':
				bricks[i] = 'GHOTKI'
			if bricks[i] == 'GRIBA':
				bricks[i] = 'GARIBABAD'
			if bricks[i] == 'K.KOT' and Second_sheet_var == True:
				bricks[i] = 'KANDH KOT'
			if bricks[i] == 'KNDRA':
				bricks[i] = 'KANDHRA'
			if bricks[i] == 'KPMHR':
				bricks[i] = 'KHANPUR MEHAR'
			if bricks[i] == 'MPM':
				bricks[i] = 'MIRPUR MATHELO'
			if bricks[i] == 'OLDSK':
				bricks[i] = 'OLD SUKKUR'
			if bricks[i] == 'PAQIL':
				bricks[i] = 'PANO AKIL'
			if bricks[i] == 'ROHRI' and Second_sheet_var == True:
				bricks[i] = 'ROHRI'
			if bricks[i] == 'S.PAT' and Second_sheet_var == True:
				bricks[i] = 'SALEH PAT'
			if bricks[i] == 'SHLMR' and Second_sheet_var == True:
				bricks[i] = 'SHALIMAR ROAD SKR2'
			if bricks[i] == 'SRHAD' and Second_sheet_var == True:
				bricks[i] = 'SARHAD'
			if bricks[i] == 'SUKTW' and Second_sheet_var == True:
				bricks[i] = 'SUKKUR TOWNSHIP SKR2'
			if bricks[i] == 'SUKUR' and Second_sheet_var == True:
				bricks[i] = 'SUKKUR SKR2'
			if bricks[i] == 'UBARO' and Second_sheet_var == True:
				bricks[i] = 'UBARO'
			if bricks[i] == 'WORK' and Second_sheet_var == True:
				bricks[i] = 'WORK SHOP ROAD SKR2'
			if bricks[i] == 'WSALE' and Second_sheet_var == True:
				bricks[i] = 'WHOLE SALE SUKKUR SKR2'

			if bricks[i] == 'ABDU' and Second_sheet_var == False:
				bricks[i] = 'ABDU'
			if bricks[i] == 'AIRPT' and Second_sheet_var == False:
				bricks[i] = 'AIR PORT ROAD'
			if bricks[i] == 'BGRJI' and Second_sheet_var == False:
				bricks[i] = 'BAGARJI'
			if bricks[i] == 'BORDO' and Second_sheet_var == False:
				bricks[i] = 'BOARD OFFICE'
			if bricks[i] == 'BRROD' and Second_sheet_var == False:
				bricks[i] = 'BARRAGE ROAD'
			if bricks[i] == 'BUNDR' and Second_sheet_var == False:
				bricks[i] = 'BUNDER ROAD'
			if bricks[i] == 'CHAK' and Second_sheet_var == False:
				bricks[i] = 'CHAK'
			if bricks[i] == 'CHDKO' and Second_sheet_var == False:
				bricks[i] = 'CHUNDKO'
			if bricks[i] == 'CLKTR' and Second_sheet_var == False:
				bricks[i] = 'CLOCK TOWER SKR1'
			if bricks[i] == 'CVSUK' and Second_sheet_var == False:
				bricks[i] = 'CIVIL SUKKUR SKR1'
			if bricks[i] == 'EIDGH' and Second_sheet_var == False:
				bricks[i] = 'EID GAH ROAD'
			if bricks[i] == 'GAM B' and Second_sheet_var == False:
				bricks[i] = 'GAMBAT SIDE B'
			if bricks[i] == 'GARYA' and Second_sheet_var == False:
				bricks[i] = 'GARYA'
			if bricks[i] == 'GMBAT' and Second_sheet_var == False:
				bricks[i] = 'GAMBAT'
			if bricks[i] == 'HLANI' and Second_sheet_var == False:
				bricks[i] = 'HALANI'
			if bricks[i] == 'HNGOR' and Second_sheet_var == False:
				bricks[i] = 'HINGORJA'
			if bricks[i] == 'JCD' and Second_sheet_var == False:
				bricks[i] = 'JACOBABAD SUKKUR'
			if bricks[i] == 'JHANI' and Second_sheet_var == False:
				bricks[i] = 'JAHAN KHAN'
			if bricks[i] == 'JINAH' and Second_sheet_var == False:
				bricks[i] = 'JINNAH CHOWK'
			if bricks[i] == 'K.BNG' and Second_sheet_var == False:
				bricks[i] = 'KOT BANGLOW'
			if bricks[i] == 'KHAI' and Second_sheet_var == False:
				bricks[i] = 'KHAI SUKKUR'
			if bricks[i] == 'KHORA' and Second_sheet_var == False:
				bricks[i] = 'KHORA'
			if bricks[i] == 'KHP' and Second_sheet_var == False:
				bricks[i] = 'KHAIRPUR'
			if bricks[i] == 'KHPCV' and Second_sheet_var == False:
				bricks[i] = 'KHAIR PUR CIVIL'
			if bricks[i] == 'KNDYA' and Second_sheet_var == False:
				bricks[i] = 'KANDYARD'
			if bricks[i] == 'KPS' and Second_sheet_var == False:
				bricks[i] = 'KHANPUR'
			if bricks[i] == 'KUMB' and Second_sheet_var == False:
				bricks[i] = 'KUMB'
			if bricks[i] == 'LAKHI' and Second_sheet_var == False:
				bricks[i] = 'LAKKHI'
			if bricks[i] == 'LQMAN' and Second_sheet_var == False:
				bricks[i] = 'LUQMAN'
			if bricks[i] == 'MHPUR' and Second_sheet_var == False:
				bricks[i] = 'MEHRAB PUR'
			if bricks[i] == 'MIANI' and Second_sheet_var == False:
				bricks[i] = 'MIANI ROAD'
			if bricks[i] == 'MLTRY' and Second_sheet_var == False:
				bricks[i] = 'MILITARY ROAD'
			if bricks[i] == 'MOCHI' and Second_sheet_var == False:
				bricks[i] = 'MOCHI BAZAR'
			if bricks[i] == 'NEEMK' and Second_sheet_var == False:
				bricks[i] = 'NEEM KI CHARI'
			if bricks[i] == 'NGOTH' and Second_sheet_var == False:
				bricks[i] = 'NEW GOTH SUKKUR'
			if bricks[i] == 'NPIND' and Second_sheet_var == False:
				bricks[i] = 'NEW PIND SUKKUR'
			if bricks[i] == 'PJGOT' and Second_sheet_var == False:
				bricks[i] = 'PIR JO GOTH'
			if bricks[i] == 'PRYAL' and Second_sheet_var == False:
				bricks[i] = 'PIRYALO'
			if bricks[i] == 'R.PUR' and Second_sheet_var == False:
				bricks[i] = 'RANIPUR'
			if bricks[i] == 'S.GAS' and Second_sheet_var == False:
				bricks[i] = 'SUI GAS'
			if bricks[i] == 'SDERO' and Second_sheet_var == False:
				bricks[i] = 'SOBHO DERO'
			if bricks[i] == 'SHP' and Second_sheet_var == False:
				bricks[i] = 'SHIKARPUR'
			if bricks[i] == 'SHP B' and Second_sheet_var == False:
				bricks[i] = 'SHIKARPUR SIDE B'
			if bricks[i] == 'STRJA' and Second_sheet_var == False:
				bricks[i] = 'SETHARJA'
			if bricks[i] == 'SUK' and Second_sheet_var == False:
				bricks[i] = 'SUK'
			if bricks[i] == 'SUKTW' and Second_sheet_var == False:
				bricks[i] = 'SUKKUR TOWNSHIP SKR1'
			if bricks[i] == 'SUKUR' and Second_sheet_var == False:
				bricks[i] = 'SUKKUR SKR1'
			if bricks[i] == 'THERI' and Second_sheet_var == False:
				bricks[i] = 'THERI'
			if bricks[i] == 'TMW' and Second_sheet_var == False:
				bricks[i] = 'THARI MIRWAH'
			if bricks[i] == 'WORK' and Second_sheet_var == False:
				bricks[i] = 'WORK SHOP ROAD SKR1'
			if bricks[i] == 'WSALE' and Second_sheet_var == False:
				bricks[i] = 'WHOLE SALE SUKKUR SKR1'
		# print(bricks)
		# print(len(bricks))
		for i in range(len(sales)):
			for k in range(len(sales[i])):
				if sales[i][k] == 'nan':
					sales[i][k] = '0'

		for p in range(0,len(products)):
			for s in range(0,len(sales[p])):
				child = []
				child.append(products[p])
				child.append(bricks[s])
				child.append(sales[p][s])
				# child.append('DU')
				result.append(child)
		# print(len(result))
		for r in result:
			for i in item_list:
				if r[0] == i[0]:
					r.insert(1,i[1])
					r.append(i[2])
					# print(r)
		for r in result:
			# print(r)
			for t in tt_list:
				if r[2] == t[0]:
					r.insert(4,t[1])
					# print(r)
		# for r in result:
		#     if r[4] != 'SKR1':
		#         print(r[2])
		result = green_team_bricks(result)
		return result
	elif dist_city == "Hyderabad":
		bricks = []
		data = []
		new_result = []
		result = []
		sales = []
		products = []
		start_data_var = 1000
		Second_sheet_var = False
		df = pd.read_excel(path)
		for i in range(0,len(df)):
			if df.iat[i,0] == 'AREA':
				start_data_var = i
				for x in range(1,len(df.columns)):
					if df.iat[i,x] == 'TTL QTY':
						break
					products.append(df.iat[i,x])
	
			if (df.iat[i,0]) == 'TTL QTY':
				break

			if  i > start_data_var+1:
				data = []
				for k in range(0,len(products)+1):
					data.append(str(df.iat[i,k]))
					# print(data)
				bricks.append(data[0])
				sales.append(data[1:])

		for i in range(0,len(products)):
			if products[i]== 'A-CAP':
				products[i] = '008376'
			if products[i] == 'A-TAB':
				products[i] = '017230'
			if products[i] == 'J_10C':
				products[i] = '008999'
			if products[i] == 'J_2CC':
				products[i] = '004348'
			if products[i] == 'J_CAP':
				products[i] = '002392'
			if products[i] == 'J_SYP':
				products[i] = '002188'
			if products[i] == 'M_INJ':
				products[i] = '009072'
			if products[i] == 'M_TAB':
				products[i] = '012961'
		for i in range(0,len(bricks)):
			if bricks[i] == 'CHOTI GHITTI':
				bricks[i] = 'CHOTI GHITI'
			if bricks[i] == 'COUNTER SALE':
				bricks[i] = 'COUNTER SALE HYD'
			if bricks[i] == 'ISLAMABAD':
				bricks[i] = 'ISLAMABAD HYD'
			if bricks[i] == 'KARIO GHANWER':
				bricks[i] = 'KARIO'
			if bricks[i] == 'KHANOOT':
				bricks[i] = 'KHANOT'
			if bricks[i] == 'KALIMORI':
				bricks[i] = 'KALI MORI'
			if bricks[i] == 'L.M.C.H':
				bricks[i] = 'LMCH'
			if bricks[i] == 'LAJPAT RAOD':
				bricks[i] = 'LAJPAT ROAD'
			if bricks[i] == 'LATIFABAD NO.10':
				bricks[i] = 'LATIFABAD 10'
			if bricks[i] == 'LATIFABAD NO.11' or bricks[i] == 'LATFABAD NO,11':
				bricks[i] = 'LATIFABAD 11'
			if bricks[i] == 'LATIFABAD NO.6':
				bricks[i] = 'LATIFABAD 6'
			if bricks[i] == 'LATIFABAD NO.4' or bricks[i] == 'LATIFABAD NO .4':
				bricks[i] = 'LATIFABAD 4'
			if bricks[i] == 'LATIFABAD NO.7':
				bricks[i] = 'LATIFABAD 7'
			if bricks[i] == 'LATIFABAD NO.8':
				bricks[i] = 'LATIFABAD 8'
			if bricks[i] == 'LATIFABAD NO.5':
				bricks[i] = 'LATIFABAD 5'
			if bricks[i] == 'LATIFABAD NO.2':
				bricks[i] = 'LATIFABAD 2'
			if bricks[i] == 'LATIFABAD NO.12':
				bricks[i] = 'LATIFABAD 12'
			if bricks[i] == 'LIAQUAT COLONY':
				bricks[i] = 'LIAQAT COLONY'
			if bricks[i] == 'PHULEELI':
				bricks[i] = 'PHULELI'
			if bricks[i] == 'SADDAR':
				bricks[i] = 'SADDER HYD2'
			if bricks[i] == 'SARFARZ COLONY':
				bricks[i] = 'SARFRAZ COLONY'
			if bricks[i] == 'SHAHDAD PURE':
				bricks[i] = 'SHAHDADPUR'
			if bricks[i] == 'SHAHDILARGE':
				bricks[i] = 'SHADI LARGE'
			if bricks[i] == 'STATION ROAD':
				bricks[i] = 'STATION ROAD HYD'
			if bricks[i] == 'USMAN SHAH URI':
				bricks[i] = 'USMAN SHAH HURI'
			if bricks[i] == 'TALHAAR':
				bricks[i] = 'TALHAR'
			if bricks[i] == 'USMANSHAH':
				bricks[i] = 'USMAN SHAH HURI'
			if bricks[i] == 'TANDO BAAGO':
				bricks[i] = 'TANDO BAGO'
			if bricks[i] == 'TANDO MOHD. KHAN':
				bricks[i] = 'TANDO MUHAMMAD KHAN'
    
		for i in range(len(sales)):
			for k in range(len(sales[i])):
				if sales[i][k] == 'nan':
					sales[i][k] = '0'
		for s in range(0,len(sales)):
			for i in range(0,len(sales[s])):
				child = []
				child.append(products[i])
				child.append(bricks[s])
				child.append(sales[s][i])
				result.append(child)
		for r in  range(0,len(result)):
			for i in item_list:
				if result[r][0] == i[0]:
					if result[r][2] != '0':
						new_result.append(result[r])
					# print(r)
		for r in new_result:
			for i in item_list:
				if r[0] == i[0]:
					r.insert(1,i[1])
					r.append(i[2]) 
		for r in new_result:
				for t in tt_list:    
					if r[2] == t[0]:
						r.insert(4,t[1])
						# print(r)
		new_result = green_team_bricks(new_result)
		return new_result
	elif dist_city == "Thatta":
		bricks = []
		data = []
		result = []
		sales = []
		products = []
		start_data_var = 1000
		df = pd.read_excel(path)
		for i in range(0,len(df)):
			if df.iat[i,0] == 'ITEM':
				start_data_var = i
				for x in range(1,len(df.columns)):
					if df.iat[i,x] == 'TTL QTY':
						break
					bricks.append(df.iat[i,x])
			if (df.iat[i,0]).strip() == 'TTL QTY PCW TEAM-BLUE':
				break
    
			if  i > start_data_var+1:
				data = []
				for k in range(0,len(bricks)+1):
					data.append(str(df.iat[i,k]))
				products.append(data[0])
				sales.append(data[1:])
		for i in range(0,len(products)):
			if 'AFLOXON 150 CAP 20,S' in products[i]:
				products[i] = '008376'
			if 'AFLOXON 300MG TAB 30,S' in products[i]:
				products[i] = '017230'
			if 'JETEPAR 10ML INJ 5,S' in products[i]:
				products[i] = '008999'
			if 'JETEPAR 2ML AMPULES 10,S' in products[i]:
				products[i] = '004348'
			if 'JETEPAR CAP 20,S' in products[i]:
				products[i] = '002392'
			if 'JETEPAR SYP' in products[i]:
				products[i] = '002188'
			if 'MAIORAD INJ 3ML 6,S' in products[i]:
				products[i] = '009072'
			if 'MAIORAD TAB 30,S' in products[i]:
				products[i] = '012961'
			if 'JETEPAR SYRUP 112ML (TP: 244.22)' in products[i]:
				products[i] = '002188'
			

		for i in range(0,len(bricks)):
			if bricks[i] == 'BAGHN':
				bricks[i] = 'BAGHAN THT'
			if bricks[i] == 'BUHUR':
				bricks[i] = 'BUHURO'
			if bricks[i] == 'CHAJN':
				bricks[i] = 'CHACH JAHAN'
			if bricks[i] == 'DABHE':
				bricks[i] = 'DHABEEJI'
			if bricks[i] == 'JHARK':
				bricks[i] = 'JHIRK SIDE'
			if bricks[i] == 'JHIMP':
				bricks[i] = 'JHAMPIR'
			if bricks[i] == 'SUJAW':
				bricks[i] = 'SUJAWAL'
			if bricks[i] == 'THT':
				bricks[i] = 'THATTA THT'
			if bricks[i] == 'C.CND':
				bricks[i] = 'CHATO CHAND'
			if bricks[i] == 'CHOUH':
				bricks[i] = 'CHOUHAR JAMALI'
			if bricks[i] == 'GAGAR':
				bricks[i] = 'GHAGHAR'
			if bricks[i] == 'GHULM':
				bricks[i] = 'GHULLAMULLAH'
			if bricks[i] == 'KHORW':
				bricks[i] = 'KHORWA'
			if bricks[i] == 'NORAD':
				bricks[i] = 'NOORIABAD'
			if bricks[i] == 'S.KRM':
				bricks[i] = 'SHAH KARIM'
			if bricks[i] == 'BATHO':
				bricks[i] = 'BATHORO'
			if bricks[i] == 'GOHRA':
				bricks[i] = 'GHORA BARI'
			if bricks[i] == 'GULMD':
				bricks[i] = 'GULMANDA'
			if bricks[i] == 'J,CHK':
				bricks[i] = 'JATI CHOWK'
			if bricks[i] == 'JUNGS':
				bricks[i] = 'JUNGSHAI'
			if bricks[i] == 'N.B':
				bricks[i] = 'NOOHBHATI'
			if bricks[i] == 'P,T':
				bricks[i] = 'PATHAN COLONY'

		for i in range(len(sales)):
			for k in range(len(sales[i])):
				if sales[i][k] == 'nan':
					sales[i][k] = '0'
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
		result = green_team_bricks(result)
		return result
	elif dist_city =="Mir Pur Khas":
		bricks = []
		data = []
		result = []
		sales = []
		products = []
		start_data_var = 1000
		Second_sheet_var = False
		df = pd.read_excel(path)
		for i in range(0,len(df)):
			if df.iat[i,0] == 'AREA':
				start_data_var = i
				for x in range(1,len(df.columns)):
					if df.iat[i,x] == 'TOTAL':
						break
					products.append(df.iat[i,x])
			if (df.iat[i,0]) == 'TOTAL':
				break

			if  i > start_data_var:
				data = []
				for k in range(0,len(products)+1):
					data.append(str(df.iat[i,k]))
				bricks.append(data[0])
				sales.append(data[1:])
    
		for b in range(0,len(bricks)):
			if bricks[b] == "HIRABAD":
				bricks[b] = "HEERABAD"
			if bricks[b] == "CHHORE":
				bricks[b] = "CHOR"
			if bricks[b] == "DILSHAKH":
				bricks[b] = "DIL SHAKH"
			if bricks[b] == "JHUDO":
				bricks[b] = "JHUDDO"
			if bricks[b] == "KOT GHULAM MOHAMMAD":
				bricks[b] = "KOT GHULAM MUHAMMAD"
			if bricks[b] == "KOT MIRUS":
				bricks[b] = "KOT MIRS"
			if bricks[b] == "MISSON":
				bricks[b] = "MISSON"
			if bricks[b] == "NOUKOT":
				bricks[b] = "NAUKOT"
			if bricks[b] == "RAJA RASTY":
				bricks[b] = "RAJA RASTI"
			if bricks[b] == "SHAHI BAZAAR":
				bricks[b] = "SARAFA SHAHI BAZAR"
			if bricks[b] == "SOOFI FAQEER":
				bricks[b] = "SUFI FAQEER"
			if bricks[b] == "TANDO JAN MOHAMMAD":
				bricks[b] = "TANDO JAN MUHAMMAD"
			if bricks[b] == "SATELLITE TOWN":
				bricks[b] = "SATELLITE TOWN MPK"
			if bricks[b] == "WHOLESALE":
				bricks[b] = "WHOLESALE MPK"


		for i in range(0,len(products)):
			if products[i] == 'JT10C':
				products[i] = '008999'
			if products[i] == 'JT2CC':
				products[i] = '004348'
			if products[i] == 'JTCAP':
				products[i] = '002392'
			if products[i] == 'JTSYP':
				products[i] = '002188'
			if products[i] == 'MDINJ':
				products[i] = '009072'
			if products[i] == 'MRDTB':
				products[i] = '012961'

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
		for r in result:
			for t in tt_list:
				if r[2] == t[0]:
					r.insert(4,t[1])
		result = green_team_bricks(result)
		return result
	elif dist_city == "Nawab Shah":
		bricks = []
		data = []
		new_result = []
		result = []
		sales = []
		products = []
		start_data_var = 1000
		Second_sheet_var = False
		df = pd.read_excel(path)
		for i in range(0,len(df)):
				if df.iat[i,0] == 'town':
					start_data_var = i
					# print(df.iat[i,0])
				if not pd.isna(df.iat[i,0]) and not pd.isna(df.iat[i,1]) and not pd.isna(df.iat[i,2]) and i > start_data_var:
					data.append(df.iat[i,1])
					data.append(df.iat[i,0])
					repeating_bricks_var = df.iat[i,0]
					# print(repeating_bricks_var)
					data.append(str(df.iat[i,2]))
					result.append(data)
					data = []
					# print(result)
					# print(data)
						# var_for_products = i
				elif pd.isna(df.iat[i,0]) and not pd.isna(df.iat[i,1]) and not pd.isna(df.iat[i,2]) and i > start_data_var:
					# print(repeating_bricks_var)   
					data.append(df.iat[i,1]) 
					data.append(repeating_bricks_var)
					
					data.append(str(df.iat[i,2]))
					# print(data)
					result.append(data)
					data = []
				elif not pd.isna(df.iat[i,0]) and pd.isna(df.iat[i,1]) and pd.isna(df.iat[i,2]) and i > start_data_var:
					repeating_bricks_var = df.iat[i,0]
				
				if df.iat[i,0] == 'grand total. ':
					# print('hi')
					break
		# print(result)
		for i in range(0,len(result)):
			# for x in range(0,len(result[i])):
			if result[i][0].strip() == 'jetepar 10cc inj' or result[i][0].strip() == 'jetepar 10cc':
				result[i][0] = '008999'
			if result[i][0].strip() == 'jetepar 2cc inj':
				result[i][0] = '004348'
			if result[i][0] == 'jetepar syp':
				result[i][0] = '002188'
			if result[i][0] == 'jetepar cap':
				result[i][0] = '002392'


			if result[i][1] == 'kandiaro':
				result[i][1] = 'KANDIARO'
			if result[i][1] == 'n.feroz':
				result[i][1] = 'NAUSHAHRO FEROZ'
			if result[i][1] == 'phull':
				result[i][1] = 'PHULL'
			if result[i][1] == 'T.SHAH':
				result[i][1] = 'T SHAH'
			if result[i][1] == 'B.CITY':
				result[i][1] = 'BHIRIA CITY'
			if result[i][1] == 'B.ROAD':
				result[i][1] = 'BHIRIA ROAD'
			if result[i][1] == 'P.CHANG':
				result[i][1] = 'PACCA CHANG'
			if result[i][1] == 'AKRI':
				result[i][1] = 'AKRI'
			if result[i][1] == 'KARONDI':
				result[i][1] = 'KARONDI'
			if result[i][1] == 'moro ':
				result[i][1] = 'MORO'
			if result[i][1] == 'D.PUR':
				result[i][1] = 'DAULAT PUR'
			if result[i][1] == 'NAWABSHAH':
				result[i][1] = 'NAWABSHAH NWS'
			# print(result[i][2],result[i][3])
		# print(result)
		for r in  range(0,len(result)):
			for i in item_list:
				if result[r][0] == i[0]:
					if result[r][2] != '0':
						new_result.append(result[r])
					# print(r)
		for r in new_result:
			for i in item_list:
				if r[0] == i[0]:
					r.insert(1,i[1])
					r.append(i[2]) 
		for r in new_result:
				for t in tt_list:    
					if r[2] == t[0]:
						r.insert(4,t[1])
		new_result = green_team_bricks(new_result)
		return new_result


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
								elif b[c] ==  'TEZAB AAHA':
									b[c] = 'TEHZAB AAHATA'
								elif b[c] == "THOKAR NIA":
									b[c] = "THOKAR NAIZ BAIG"
         
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
				result = green_team_bricks(result)
				return result

			elif dist_city== 'Sheikhupura':
				products = []
				sales = []
				result = []
				for x in range(0,len(pdf.pages)):
					data = pdf.pages[x].extract_table()
					if type(data)!=type(None) and data[x][0]== 'Product Name':
						for i in range(2,len(data)-2):
							products.append(data[i][0])
						bricks = data[0][2:]
						for p in range(0,len(products)):
							sales.append(data[2+p][2:])
						
				for s in sales:
					for i in range(0,len(s)):
						if s[i] =='':
							s[i] = '0'
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
				# for brick parent
				for r in result:
					for t in tt_list:
						if r[2] == t[0]:
							r.insert(4,t[1]) ## insert brick parent into index 4
				result = green_team_bricks(result)
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
				end_result = green_team_bricks(end_result)
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
				bricks = data[0][2:-1]
				for b in range(0,len(bricks)):
					if 'D\nA\nO\nR\nR \nA\nB\nK\nA' in bricks[b]:
						bricks[b] = 'AKBAR ROAD'
					if 'D \nA\nB\nA\nR \nE\nT\nH\nK\nA' in bricks[b]:
						bricks[b] = 'AKHTER ABAD'
					if 'D\nA\nB\nA\nR \nE\nT\nH\nK\nA' in bricks[b]:
						bricks[b] = 'AKHTER ABAD'
					if 'R\nU\nP\nR \nSI\nA\nB' in bricks[b]:
						bricks[b] = 'BASIR PUR'
					if 'GP\n4U\n+M\nCHUCHAKD+BAMA+ALKA' in bricks[b]:
						bricks[b] = 'CHUCHAK'
					if 'R \nU\nP\nL \nA\nP\nE\nD' in bricks[b]:
						bricks[b] = 'DEPAL PUR'
					if 'R \nEPAL PUCHOWK\nD' in bricks[b]:
						bricks[b] = 'DEPAL PUR CHOWK'
					if '2\nQ \nH\nD' in bricks[b]:
						bricks[b] = 'DHQ 2'
					if 'D \nA\nSAL ABROAD\nAI\nF' in bricks[b]:
						bricks[b] = 'FAISLA ABAD ROAD'
					if 'N\nA\nC\n+\nBERTT\nM\nA\nG' in bricks[b]:
						bricks[b] = 'CANTT'
					if 'U\nO\nERA+YG PUR\nGN\nO\nG' in bricks[b]:
						bricks[b] = 'GOGERA'
					if 'D\nA\nB\nA\nB \nBI\nA\nH' in bricks[b]:
						bricks[b] = 'HABIB ABAD'
					if 'A\nH\nK\nA\nL\nLI \nE\nV\nA\nH' in bricks[b]:
						bricks[b] = 'HAVELI LAKHA'
					if 'L \nPITAZAR\nSA\nOB\nH' in bricks[b]:
						bricks[b] = 'HOSPITAL BAZAR'
					if 'Y\nT\nCI\nA \nR\nUJ\nH' in bricks[b]:
						bricks[b] = 'HUJRA CITY'
					if 'A\nK\nO\nB\nA\nJ' in bricks[b]:
						bricks[b] = 'JABOKA'
					if 'LALA ZAR COLONY' in bricks[b]:
						bricks[b] = 'LALA ZAR COLONY'
					if 'D \nE\nM\nHD\nAA\nDI AB\nN\nA\nM' in bricks[b]:
						bricks[b] = 'MANDI AHMED ABAD'
					if 'A\nL\nO\nOL KH\nNT+\nA\nL\nP' in bricks[b]:
						bricks[b] = 'KOHLA'
					if 'L\nA\nW\nO \nAJ\nR' in bricks[b]:
						bricks[b] = 'RAJO WAL'
					if 'Y\nRENALA HURD CIT\nK' in bricks[b]:
						bricks[b] = 'RENALA KHURD CITY'
					if 'L \nWAAD\nAHIRO\nS' in bricks[b]:
						bricks[b] = 'SAHIWAL ROAD'
					if 'H\nD\nR\nA\nG\nR \nAI\nH\nS' in bricks[b]:
						bricks[b] = 'SHER GARH'
					if 'D D\nAA\nSIRKI MOH+SMPURA RO' in bricks[b]:
						bricks[b] = 'SIRKI'
					if 'LA RA\nGE\nNG\nAO\nBG' in bricks[b]:
						bricks[b] = 'BANGLA GOGERA'
					if '1\nQ \nH\nD' in bricks[b]:
						bricks[b] = 'DHQ 1'
					if 'JABOKA+NOL PLOT+KOHLA+MUPLAKA+BAM' in bricks[b]:
						bricks[b] = 'JABOKA'
    
    
				for p in range(0,len(products)):
					if 'AFLOXAN CAP 20 S' in products[p]:
						products[p] = '008376'
					if 'AFLOXAN TAB 30 S' in products[p]:
						products[p] = '017230'
					if 'JETEPAR 10ml Amp 1' in products[p]:
						products[p] = '008999'
					if 'JETEPAR 2ml Amp 1' in products[p]:
						products[p] = '004348'
					if 'JETEPAR CAP 1' in products[p]:
						products[p] = '002392'
					if 'JETEPAR SYP 1' in products[p]:
						products[p] = '002188'
					if 'MAIORAD AMP 1' in products[p]:
						products[p] = '009072'
					if 'MAIORAD TAB' in products[p]:
						products[p] = '012961'
			
				for p in range(0,len(products)):
					for b in range(0,len(bricks)):
						child = []
						child.append(products[p])
						child.append(bricks[b])
						child.append(sales[p][b])
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
				result = green_team_bricks(result)
				return result
			elif dist_city == 'Karachi':
				result = []
				for x in range(0,len(pdf.pages)):
					products = []
					bricks = []
					sales = []
					new_result = []
					data = pdf.pages[x].extract_table()
					# print(data)
					product = data[0][1:]
					products.append(product)
					# print(products)
					for i in range(2,len(data)): ## for skipping total row
						bricks.append(data[i][0])
						# print(bricks)
						sale = data[i][1:]
						sales.append(sale)
						# print(sales)
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
					for b in range(len(bricks)):
						if "AL-ASIF SQUARE" in bricks[b]:
							bricks[b] = "AL ASIF SQUARE"
						if "AZAM-BASTI,MEHMOODABAD" in bricks[b]:
							bricks[b] = "AZAM-BASTI AND MEHMOODABAD"
						if "CIVIL HOSPITAL" in bricks[b]:
							bricks[b] = "CIVIL HOSPITAL KHI"
						if "CLIFTON,DEFENCE" in bricks[b]:
							bricks[b] = "CLIFTON AND DEFENCE"
						if "FEDERAL. B.AREA" in bricks[b]:
							bricks[b] = "FEDERAL B AREA"
						if "GULISTAN-E-JAUHAR" in bricks[b]:
							bricks[b] = "GULISTAN E JAUHAR"
						if "GULSHAN-E-IQBAL" in bricks[b]:
							bricks[b] = "GULSHAN E IQBAL KHI"
						if "J.P.M.C, CANTT STATION" in bricks[b]:
							bricks[b] = "J.P.M.C AND CANTT STATION"
						if "KAHTOOR,GADAP." in bricks[b]:
							bricks[b] = "KAHTOOR AND GADAP"
						if "LANDHI,QUAIDABAD,OLD MUZAFABAD" in bricks[b]:
							bricks[b] = "LANDHI AND QUAIDABAD AND OLD MUZAFABAD"
						if "LIAQATABAD" in bricks[b]:
							bricks[b] = "LIAQUATABAD"
						if "LYARI,CHAKIWARA" in bricks[b]:
							bricks[b] = "LYARI AND CHAKIWARA"
						if "P.I.B,NEW TOWN" in bricks[b]:
							bricks[b] = "PIR ILAHI BUKSH AND NEW TOWN"
						if "RANCHORE LINE, USMANABAD" in bricks[b]:
							bricks[b] = "RANCHORE LANE AND USMANABAD"
						if "SADDAR" in bricks[b]:
							bricks[b] = "SADDAR KHI"
						if "SHAH FAISAL COLONY" in bricks[b]:
							bricks[b] = "SHAH FAISAL COLONY KHI"
						if "SOILDER BAZAR,GARDEN WEST" in bricks[b]:
							bricks[b] = "SOILDER BAZAR AND GARDEN WEST"
						if "TOWER,BURNS ROAD" in bricks[b]:
							bricks[b] = "TOWER AND BURNS ROAD"
						if "WINDER,UTHAL,BELA,COASTLY BELT." in bricks[b]:
							bricks[b] = "WINDER AND UTHAL AND BELA AND COASTLY BELT"
					# print(products)

					for b in range(len(products[0])):
						if "CNORN-FRT-I" in products[0][b]:
							products[0][b] = "005425"
						if "DPROGSIC-P" in products[0][b]:
							products[0][b] = "081838"
						if "EBAST 10MG-" in products[0][b]:
							products[0][b] = "023906"
						if "HISFIX180MG" in products[0][b]:
							products[0][b] = "031038"
						if "HISFX-180MG" in products[0][b]:
							products[0][b] = "031038"
						if "HISTFX-120M" in products[0][b]:
							products[0][b] = "031037"
						if "GISRIP 2MG T" in products[0][b]:
							products[0][b] = "035295"
						if "ISRP-1MG T" in products[0][b]:
							products[0][b] = "035294"
						if "JETEPAR CAP" in products[0][b]:
							products[0][b] = "002392"
						if "JETEPAR SYR" in products[0][b]:
							products[0][b] = "002188"
						if "JTPAR-INJC- 2" in products[0][b]:
							products[0][b] = "004348"
						if "JTPR 10ML" in products[0][b]:
							products[0][b] = "008999"
						if "MAIORAD IN" in products[0][b]:
							products[0][b] = "009072"
						if "MAIORAD-IN" in products[0][b]:
							products[0][b] = "009072"


						if "MALTM  PLS" in products[0][b]:
							products[0][b] = "071560"
						if "DMAORAD-TAB" in products[0][b]:
							products[0][b] = "012961"
						if "METRONI 200" in products[0][b]:
							products[0][b] = "008909"
						if "MINGIR-10MG" in products[0][b]:
							products[0][b] = "038427"
						if "MNGAR TAB-" in products[0][b]:
							products[0][b] = "038426"

						if "MOXILIUM-D" in products[0][b]:
							products[0][b] = "006782"
						if "RMOXILM-125M" in products[0][b]:
							products[0][b] = "006783"
						if "MOXLIM 500-" in products[0][b]:
							products[0][b] = "008908"
						if "MOXLIM-500" in products[0][b]:
							products[0][b] = "008908"
						if "MOXLUM-250" in products[0][b]:
							products[0][b] = "006784"
						if "MTRNIDAZ T" in products[0][b]:
							products[0][b] = "081274"
						if "BMXLM- 250MG" in products[0][b]:
							products[0][b] = "006784"
						if "OBEXL-20MG" in products[0][b]:
							products[0][b] = "032259"
						if "PC-LC-SYRUP" in products[0][b]:
							products[0][b] = "019133"
						if "PROBTOR 20M" in products[0][b]:
							products[0][b] = "016654"
						if "PROBTOR-20M" in products[0][b]:
							products[0][b] = "016654"
						if "SAVELX 250M" in products[0][b]:
							products[0][b] = "032255"
						if "SAVLOX-500" in products[0][b]:
							products[0][b] = "029328"
						if "SPRCEF-DS SY" in products[0][b]:
							products[0][b] = "028727"
						if "SPRCEF-DS-SY" in products[0][b]:
							products[0][b] = "028727"
						if "SUPARCF-SUS" in products[0][b]:
							products[0][b] = "024819"
						if "SUPRCEF 400" in products[0][b]:
							products[0][b] = "024820"
						if "SUPRLOX SYR" in products[0][b]:
							products[0][b] = "028728"
						if "TRAMAGES 5" in products[0][b]:
							products[0][b] = "029327"
						if "0TRAMAGSIC" in products[0][b]:
							products[0][b] = "026920"
						if "VIGROL FORT" in products[0][b]:
							products[0][b] = "007018"
						if "VIKNN-FORT" in products[0][b]:
							products[0][b] = "006406"
					# print(products)
					for b in range(0,len(bricks)):
						for s in range(0,len(only_sale[b])): 
							child = []
							child.append(products[0][s])
							child.append(bricks[b])
							# print(bricks[b])
							child.append(only_sale[b][s])
							result.append(child) 
				for r in range(len(result)): # this script add the two sales in each box(e.g 5+6)
					if '+' in result[r][2]:
						temp_sale = result[r][2]
						temp_sale = temp_sale.split('+')
						temp_sale = int(temp_sale[0]) + int(temp_sale[1])
						temp_sale = str(temp_sale)
						result[r][2] = temp_sale
				for r in  range(0,len(result)):
					for i in item_list:
						if result[r][0] == i[0]:
							if result[r][2] != '0':
								new_result.append(result[r])
				for r in new_result:
					for i in item_list:
						if r[0] == i[0]:
							r.insert(1,i[1])
							r.append(i[2])
							# print(r)

				for r in new_result:
					for t in tt_list:    
						if r[2] == t[0]:
							r.insert(4,t[1])
							#print(r)
				new_result = green_team_bricks(new_result)
				return new_result
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
						for a in range(0,len(i)):
							if i[a] == '':
								i[a] = '0'
					for p in range(0,len(products)):
						for b in range(0,len(bricks)):
							child = []
							child.append(products[p])
							child.append(bricks[b])
							child.append(sales[p][b])
							result.append(child)
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
					result = green_team_bricks(result)
					return result
			elif dist_city == "Sialkot":
				bricks = []
				sales = []
				result = []
				products = []
				new_result = []
				for x in range(0,len(pdf.pages)):
					data = pdf.pages[x].extract_table()
					products = data[0][2:-1]
					
					for p in range(0,len(products)):
						if '046001' in products[p]:
							products[p] = '008999'
						if '046002' in products[p]:
							products[p] = '004348'
						if '046003' in products[p]:
							products[p] = '002188'
						if '046004' in products[p]:
							products[p] = '002392'
						if '046005' in products[p]:
							products[p] = '009072'
						if '046006' in products[p]:
							products[p] = '012961'
						# if '' in products[p]:
						#     product[p] = ''

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
					if '1010409' in bricks[b] :
						bricks[b] = 'NAWAN PIND'
					if '1010616' in bricks[b] :
						bricks[b] = 'PAKKA GARHA'
					if '1010804' in bricks[b] :
						bricks[b] = 'CHAKRALA MARALA'
					if '1010903' in bricks[b] :
						bricks[b] = 'BHOTH'
					if '1011004' in bricks[b] :
						bricks[b] = 'KUBAY CHAK'
					if '1011107' in bricks[b] :
						bricks[b] = '1011107 - CEO-KAY SKT-J'
					if '1020101' in bricks[b] :
						bricks[b] = 'JASSAR WALA'
					if '1031002' in bricks[b] :
						bricks[b] = 'BABU GHULAM NABI ROAD SAMBRIAL'
					if '1031007' in bricks[b] :
						bricks[b] = 'RANDHIR MOR SAMBRIAL'
					if '1040904' in bricks[b] :
						bricks[b] = 'DHQ ROAD NWL'
					if '1040909' in bricks[b] :
						bricks[b] = 'MANDI THROO'
					if '1050803' in bricks[b] :
						bricks[b] = 'LARI ADDA CHWND'
					if '1051004' in bricks[b] :
						bricks[b] = 'MAIN BAZAR PSR'
					if '1070806' in bricks[b] :
						bricks[b] = 'KHARDANA MOR'
					if '1070810' in bricks[b] :
						bricks[b] = 'WAGHA KNG'
					if '1070812' in bricks[b] :
						bricks[b] = 'GADGOR KNG'
					# if '' in bricks[b] :
					# 	bricks[b] = ''

				for s in range(0,len(sales)):
					for i in range(0,len(sales[s])):
						child = []
						child.append(products[i])
						child.append(bricks[s])
						child.append(sales[s][i])
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
				new_result = green_team_bricks(new_result)
				return new_result
			elif dist_city == "Narowal":
				products = []
				bricks = []
				sales = []
				result = []
				new_result = []
				for x in range(0,len(pdf.pages)):
					data = pdf.pages[x].extract_table()
					if data[0][0] == 'FOI Id :  /':
						products.append(data[1][1:-1])
						for i in range(2,len(data)-1):
							bricks.append(data[i][0])
							sales.append(data[i][1:-1])
					else:
						products.append(data[0][1:-1])
						for i in range(1,len(data)-1):
							bricks.append(data[i][0])
							sales.append(data[i][1:-1])

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
						if '006033' in products[p][i] :
							products[p][i] = '038427'
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
						if '006046' in products[p][i] :
							products[p][i] = '024819'
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
					if '1010204' in bricks[b] :
						bricks[b] = 'MANZOR PURA'
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

				for r in  range(0,len(result)):
					for i in item_list:
						if result[r][0] == i[0]:
							if result[r][2] != '0':
								new_result.append(result[r])  
				# print(len(new_result))    
				for r in  range(0,len(new_result)):
					for i in item_list:
						if new_result[r][0] == i[0]:
								new_result[r].insert(1,i[1])
								new_result[r].append(i[2]) 
				for r in new_result:
					for t in tt_list:
						if r[2] == t[0]:
							r.insert(4,t[1])
				new_result = green_team_bricks(new_result)
				return new_result


			elif dist_city == "Gujranwala":
				result = []
				new_result = []
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
							sale = re.findall('[-+]?\d+', data[x])
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
							sale = re.findall('[-+]?\d+', data[x])
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
					if bricks[b] == "EMAN ABAD  -":
						bricks[b] = "EMAN ABAD"
					if bricks[b] == "GAKHAR  -":
						bricks[b] = "GAKHAR"
					if bricks[b] == "SIALKOT":
						bricks[b] = "SIALKOT GUJRANWALA"
				# print(bricks)
				for b in range(0,len(bricks)):
					for p in range(0,len(products)):
						child = []
						child.append(products[p])
						child.append(bricks[b])
						child.append(sales[b][p])
						result.append(child)
				
				for r in  range(0,len(result)):
					for i in item_list:
						if result[r][0] == i[0]:
							if result[r][2] != '0':
								new_result.append(result[r])  
				# print(len(new_result))    
				for r in  range(0,len(new_result)):
					for i in item_list:
						if new_result[r][0] == i[0]:
								new_result[r].insert(1,i[1])
								new_result[r].append(i[2]) 
				for r in new_result:
					for t in tt_list:
						if r[2] == t[0]:
							r.insert(4,t[1])

				new_result = green_team_bricks(new_result)
				return new_result

			elif dist_city == "Mandi Bahauddin":
				result = []
				new_result = []
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
					if bricks[b] == 'BOSSAL':
						bricks[b] = 'BOSAL'
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
				new_result = green_team_bricks(new_result)
				return new_result

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
				result = green_team_bricks(result)
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
				result = green_team_bricks(result)
				return result

			elif dist_city == "Bannu":
				products = []
				sales = []
				bricks = []
				result = []
				for x in range(0,len(pdf.pages)):
					data = pdf.pages[x].extract_table()
					# print(data)
					#change the zero below to 1 if any error occurs in product
					products.append(data[0][1:-1])
					# print(data[0])
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
						if bricks[k] == '- LAKKI GATE':
							bricks[k] = 'LAKKI GATE'
						if bricks[k] == '- DHQ':
							bricks[k] = 'DHQ BNU'
						if bricks[k] == '- ZHQ':
							bricks[k] = 'ZHQ'
						if bricks[k] == '- RAILWAY ROAD':
							bricks[k] = 'RAILWAY ROAD'
						if bricks[k] == '- GHALA MANDI':
							bricks[k] = 'GHALA MANDI'
						if bricks[k] == '- DAS CHWOK':
							bricks[k] = 'DAS CHOWK'
						if bricks[k] == '- KGN':
							bricks[k] = 'KGN'
						if bricks[k] == '- MANGAL MELA':
							bricks[k] = 'MANGAL MELA'
						if bricks[k] == '- AMBERI KALA':
							bricks[k] = 'AMBERI KALA'
						if bricks[k] == '- DOMAIL':
							bricks[k] = 'DOMAIL'
						if bricks[k] == '- MIRANSHAH':
							bricks[k] = 'MIRANSHAH'
						if bricks[k] == '- MIR ALI':
							bricks[k] = 'MIR ALI'
						if bricks[k] == '- NAURANG':
							bricks[k] = 'NAURANG'
						if bricks[k] == '- GAMBILA':
							bricks[k] = 'GAMBILA'
						if bricks[k] == '- TAJORI':
							bricks[k] = 'TAJORI'
						if bricks[k] == '- LAKKI':
							bricks[k] = 'LAKKI MARWAT'
						if bricks[k] == '- KARAK':
							bricks[k] = 'KARAK'
						if bricks[k] == '- LATAMBER':
							bricks[k] = 'LATAMBER'
						if bricks[k] == '- TAKHT E NASRATI':
							bricks[k] = 'TAKHT E NASRATI'
						if bricks[k] == 'MIRANSHAH':
							bricks[k] = 'MIRAN SHAH'
						if bricks[k] == '- SURANI GT':
							bricks[k] = 'SURANI GT'
						if bricks[k] == '- SURANI':
							bricks[k] = 'SURANI'
				for p in range(0,len(products)):
					for i in range(0,len(products[p])):
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
						if '014015' in products[p][i]:
							products[p][i] ='031037'
						if '014018' in products[p][i]:
							products[p][i] ='035295'
						if '014026' in products[p][i]:
							products[p][i] ='012961'
						if '014034' in products[p][i]:
							products[p][i] ='038426'
						if '014051' in products[p][i]:
							products[p][i] ='007018'
						if '014005' in products[p][i]:
							products[p][i] ='007853'
						# print(products[p][i])

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
							# print(r)
				#print(result)
				for r in result:
					for t in tt_list:    
						if r[2] == t[0]:
							r.insert(4,t[1])
							#print(r)
				result = green_team_bricks(result)
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
					if bricks[b] == 'D.I.KHAN':
						bricks[b] = 'DIKHAN'
    
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
				result = green_team_bricks(result)
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
						if 'JETEPAR 10ML AMP' in products[i]:
							products[i] = '008999'
						if 'JETEPAR 2ML AMP' in products[i]:
							products[i] = '004348'
						if 'JETEPAR CAP' in products[i]:
							products[i] = '002392'
						if 'JETEPAR SYP' in products[i]:
							products[i] = '002188'
						if 'MAIORAD TAB' in products[i]:
							products[i] = '012961'
						if 'MAIORAD 3ML AMP' in products[i]:
							products[i] = '009072'
						if 'AFLOXAN TAB' in products[i]:
							products[i] = '017230'
						if 'AFLOXAN CAP' in products[i]:
							products[i] = '008376'
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
				result = green_team_bricks(result)
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
					for i in range(0,len(products)):
						if 'JETEPAR 10ML AMP' in products[i]:
							products[i] = '008999'
						if 'JETEPAR 2ML AMP' in products[i]:
							products[i] = '004348'
						if 'JETEPAR CAP' in products[i]:
							products[i] = '002392'
						if 'JETEPAR SYP' in products[i]:
							products[i] = '002188'
						if 'MAIORAD TAB' in products[i]:
							products[i] = '012961'
						if 'MAIORAD AMP' in products[i]:
							products[i] = '009072'
						if 'AFLOXAN TAB' in products[i]:
							products[i] = '017230'
						if 'AFLOXAN CAP' in products[i]:
							products[i] = '008376'
	
	
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
				result = green_team_bricks(result)
				return result
			elif dist_city == "Kohat":
				result = []
				new_result = []
				bricks = ['KOHAT 1','HANGU','DOABA','THALL','KOHAT 2','KOHAT 3','ALIZAI AND BAGHAN','PARACHINAR','BANDA DAUD SHAH','LACHI','GUMBAT','KOHAT DEVELOPMENT AUTHORITY']
				products = []
				sales = []
				for x in range(0,len(pdf.pages)):
					data = pdf.pages[x].extract_table()
					bricks=data[0][1:-1]
    
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
					products[i] = re.sub('973 JETEPAR CAP NEW','002392',products[i])
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

				for r in  range(0,len(result)):
					for i in item_list:
						if result[r][0] == i[0]:
							if result[r][2] != '0':
								new_result.append(result[r])  
				# print(len(new_result))    
				for r in  range(0,len(new_result)):
					for i in item_list:
						if new_result[r][0] == i[0]:
								new_result[r].insert(1,i[1])
								new_result[r].append(i[2]) 
				for r in new_result:
					for t in tt_list:
						if r[2] == t[0]:
							r.insert(4,t[1])

				new_result = green_team_bricks(new_result)
				return new_result    

				
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
						if 'JETEPAR SYP' in products[i]:
							products[i] = '002188'
						if 'JETEPAR 2ML INJ' in products[i]:
							products[i] = '004348'
						if 'JETEPAR 10ML INJ' in products[i]:
							products[i] = '008999'
						if 'MAIORAD INJ' in products[i]:
							products[i] = '009072'
						if 'JETEPAR CAP' in products[i]:
							products[i] = '002392'
						if 'MAIORAD TAB' in products[i]:
							products[i] = '012961'
						if 'AFLOXAN CAP' in products[i]:
							products[i] = '008376'
						if 'AFLOXAN TAB' in products[i]:
							products[i] = '017230'

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
				result = green_team_bricks(result)
				return result

			elif dist_city == "Rawalpindi":
				products = []
				sales = []
				bricks = []
				result = []
				new_result = []
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
							if bricks[k] == 'BUNNI CHOWK':
								bricks[k] = 'BANNI CHOWK'
							if bricks[k] == 'JAMIA MASJID ROAD':
								bricks[k] = 'JAMIA MASJID ROAD'
							if bricks[k] == 'KHAYABAN-E-SIR \nSYED':
								bricks[k] = 'KHAYABAN E SIR SYED'
							if bricks[k] == 'CHAKLALA SCHEME \nIII':
								bricks[k] = 'CHAKLALA SCHEME III'
							if bricks[k] == 'JAMIA MASJID \nROAD':
								bricks[k] = 'JAMIA MASJID ROAD'
        
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
						if '009005' in products[p][i]:
							products[p][i] = '008376'
						if 'AFLOXAN TAB' in products[p][i]:
							products[p][i]= '017230'
						if 'MAIORAD TAB' in products[p][i]:
							products[p][i]= '012961'
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
				new_result = green_team_bricks(new_result)
				return new_result

			elif dist_city == "Vehari":
				result = []
				new_result = []
				products = []                                    
				bricks = ['ADDA AREY WHEN','BUREWALA','CASH','CHAKRALA','DOKOTA','GARHA MORE','GAGGOO','KARAM PUR','LUDDAN',
				'MAILSI VIHARI','MITRO','NEW CHOWK VRI','PAKHY MORE MACHIWAL','THINGI','TIBBA SULTANPUR','VEHARI VRI','VIJHIANWALA']
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
					products[i] = re.sub('MAIORAD INJ 6s','009072',products[i])
				for p in range(0,len(products)):
					for s in range(0,len(sales[p])):
						child = []
						child.append(products[p])
						child.append(bricks[s])
						child.append(sales[p][s])
						# child.append('VRI')
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

				new_result = green_team_bricks(new_result)
				return new_result

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
					if 'MAIORAD INJ 6S' in products[i]:
						products[i] = '009072'
					if 'JETEPAR 10.ML INJ 5S' in products[i]:
						products[i] = '008999'
					if 'JETEPAR SYRUP 112.ML' in products[i]:
						products[i] = '002188'
					if 'JETEPAR INJ 2ML 10S' in products[i]:
						products[i] = '004348'
					if 'JETEPAR CAP 20S' in products[i]:
						products[i] = '002392'


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
				result = green_team_bricks(result)
				return result
			elif dist_city == "Peshawar":
				products = []
				bricks = []
				sales = []
				result = []
				brick = []
				new_result = []
				for x in range(0,len(pdf.pages)):
					data = pdf.pages[x].extract_table()
					products = data[0][1:]
					products.remove('Total Amount')
					for p in range(0,len(products)):
						if '006002' in products[p]:
							products[p] = '028729'
						if '006003' in products[p]:
							products[p] = '005425'
						if '006004' in products[p]:
							products[p] = '023906'
						if '006009' in products[p]:
							products[p] = '038426'
						if '006011' in products[p]:
							products[p] = '008908'
						if '006012' in products[p]:
							products[p] = '006782'
						if '006013' in products[p]:
							products[p] = '006783'
						if '006014' in products[p]:
							products[p] = '012649'
						if '006015' in products[p]:
							products[p] = '019133'
						if '006017' in products[p]:
							products[p] = '032255'
						if '006020' in products[p]:
							products[p] = '028727'
						if '006021' in products[p]:
							products[p] = '024819'
						if '006022' in products[p]:
							products[p] = '028728'
						if '006023' in products[p]:
							products[p] = '029327'
						if '006024' in products[p]:
							products[p] = '026920'
						if '006025' in products[p]:
							products[p] = '007018'
						if '006026' in products[p]:
							products[p] = '006406'
						if '006041' in products[p]:
							products[p] = '008376'
						if '006042' in products[p]:
							products[p] = '017230'
						if '006043' in products[p]:
							products[p] = '008999'
						if '006044' in products[p]:
							products[p] = '004348'
						if '006045' in products[p]:
							products[p] = '002392'
						if '006046' in products[p]:
							products[p] = '002188'
						if '006047' in products[p]:
							products[p] = '009072'
						if '006048' in products[p]:
							products[p] = '012961'
						if '006064' in products[p]:
							products[p] = '035294'
						if '006065' in products[p]:
							products[p] = '035295'
						if '006068' in products[p]:
							products[p] = '032259'
						if '006069' in products[p]:
							products[p] = '081838'
						if '006070' in products[p]:
							products[p] = '081274'
						if '006071' in products[p]:
							products[p] = '008909'
						if '006016' in products[p]:
							products[p] = '016654'
						if '006005' in products[p]:
							products[p] = '031037'
						# if '' in products[p]:
						#     product[p] = ''
					if x == len(pdf.pages)-1:
						for b in range(1,len(data)-1):
							brick.append(data[b][0])

						for s in range(1,len(data)-1):
							sales.append(data[s][1:-1])
					else:
						for b in range(1,len(data)):
							brick.append(data[b][0])

						for s in range(1,len(data)):
							sales.append(data[s][1:-1])
				# print(bricks)
				for s in sales:
					for i in range(0,len(s)):
						if s[i] =='-':
							s[i] = '0'
							# print(s[i])
				# print(sales)
				for i in range(0,len(brick)):
					bricks.append(brick[i][10:])
					bricks[i] = re.sub('\n','',bricks[i])
					bricks[i] = re.sub('QUDRAT ELAHI MARKET','QUDRAT ELAHI',bricks[i])
					bricks[i] = re.sub('AL HAYAT MRKET','AL HAYAT MARKET',bricks[i])
					bricks[i] = re.sub('GHULAM SAID PLAZA','GHULAM SAID',bricks[i])
					bricks[i] = re.sub('SOEKARNO SQAURE','SOEKARNO SQUARE',bricks[i])
					bricks[i] = re.sub('KHYBER MEDICAL CENTR','KHYBER MEDICAL CENTER',bricks[i])
					bricks[i] = re.sub('RAHEEM MEDICAL','RAHEEM MEDICAL CENTER',bricks[i])
					bricks[i] = re.sub('BAZAR-E-KALAN','BAZAR E KALAN',bricks[i])
					bricks[i] = re.sub('K.T.H','KHYBER TEACHING HOSPITAL',bricks[i])
					bricks[i] = re.sub('LRH','LADY READING HOSPITAL',bricks[i])
					bricks[i] = re.sub('H.A.M.C','HAYATABAD MEDICAL COMPLEX',bricks[i])
					bricks[i] = re.sub('BADA BAIR','BADABER',bricks[i])
					bricks[i] = re.sub('NOTHIA','NOTHIA QADEEM',bricks[i])
					bricks[i] = re.sub('KHATAK MEDICAL CENTR','KHATAK MEDICAL CENTER',bricks[i])
					bricks[i] = re.sub('AL SHIFA SURG CENTER','AL SHIFA SURGICAL CENTER',bricks[i])
					bricks[i] = re.sub('KHUSHAAL CENTER','KHUSHAL CENTER',bricks[i])
					bricks[i] = re.sub('MOHMAND MEDICAL CENT','MOHMAND MEDICAL CENTER',bricks[i])
					bricks[i] = re.sub('RAHEEM MEDICAL CENTER CENTR','RAHEEM MEDICAL CENTER',bricks[i])
					bricks[i] = re.sub('SIKANDAR PURA','SIKANDER PURA',bricks[i])
					bricks[i] = re.sub('NASEER TEACHING HOSP','NASEER TEACHING HOSPITAL',bricks[i])
					bricks[i] = re.sub('TARANGZAI','TAURANG ZAI',bricks[i])
					bricks[i] = re.sub('KOHAT RAOD','KOHAT ROAD',bricks[i])
				# print(products)
				for s in range(0,len(sales)):
					for i in range(0,len(sales[s])):
						# print(products[i],bricks[s],sales[s][i])
						child = []
						child.append(products[i])
						child.append(bricks[s])
						child.append(sales[s][i])
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
				new_result = green_team_bricks(new_result)
				return new_result
			elif dist_city == "Quetta":
				result = []
				new_result = []
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
						if products[i] == 'MAIORAD TAB':
							products[i] = '012961'
						if products[i] == 'AFLOXAN CAPS':
							products[i] = '008376'
						if products[i] == 'AFLOXAN TAB':
							products[i] = '017230'
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
				new_result = green_team_bricks(new_result)
				return new_result
			elif dist_city == "Jacobabad":
				result = []
				products = ['008376','017230','002392','008999','004348','002188','009072','012961','012961']
				bricks = []
				sales = []
				for x in range(0,len(pdf.pages)):
					data = pdf.pages[x].extract_text()
					data = re.sub('\n',',',data)
					data = data.split(',')
					bricks = data[5:6]
					data = data[8:-5]
					for i in range(0,len(data)):
						data[i] = re.sub('\s',',',data[i])
						data[i] = data[i].split(',')
						sales.append(data[i][-11:-1])
					for k in range(0,len(bricks)):
						bricks[k] = bricks[k].split('│') 
					bricks = bricks[0][3:-2]
					for k in range(0,len(bricks)):
						if bricks[k] == 'DERA A':
							bricks[k] = 'DERA ALLAH YAR'
						if bricks[k] == 'DERA M':
							bricks[k] = 'DERA MURAD JAMALI'
						if bricks[k] == 'JCD/OU':
							bricks[k] = 'JCD/OU'
						if bricks[k] == 'JCD/Q-':
							bricks[k] = 'JCD/Q'
						if bricks[k] == 'JCD/SH':
							bricks[k] = 'JCD/SH'
						if bricks[k] == 'JCD/WH':
							bricks[k] = 'JCD/WH'
						if bricks[k] == 'KANDH ':
							bricks[k] = 'KANDHKOT'
						if bricks[k] == 'KASHMO':
							bricks[k] = 'KASHMORE'
						if bricks[k] == 'THULL':
							bricks[k] = 'THUL'
						if bricks[k] == 'USTA M':
							bricks[k] = 'USTA MUHAMMAD'
				for p in range(0,len(products)):
					for s in range(0,len(sales[p])):
						child = []
						child.append(products[p])
						child.append(bricks[s])
						child.append(sales[p][s])
						# child.append('JCD')
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
				result = green_team_bricks(result)
				return result
			
			elif dist_city == "Layyah":
				result = []
				products = []
				bricks = ['LAYYAH LYH','CHOWK AZAM','KAROR LAL ESAN','FATEHPUR','CHOWK MUNDA','JAMAN SHAH',
				'KOT SULTAN','PAHARPUR','EHSAN PUR','DAIRA DIN PANAH','LADHANA','KOT ADDU','SANAWAN LYH','CHAUBARA LYH','MISC LYH',]
				sales = []
				first_table_end = 0
				for x in range(0,len(pdf.pages)):
					data = pdf.pages[x].extract_text()
					data = re.sub('\n','$',data)
					data = data.split('$')
					data = data[10:-15]
					for i in range(0,len(data)):   
						if data[i] == 'Group Name : GREEN':
							second_table_start = i
							first_table_end = i-8
				for k in range(0,len(data)):
					if k <= first_table_end or k > second_table_start:
						data[k] = re.sub('[(]','$',data[k])
						# print(data[k])
						data[k] = data[k].split('$')
						products.append(data[k][0][:-1])
						data[k] = re.sub('\s+','$',data[k][1])
						data[k] = data[k].split('$')
						sales.append(data[k][1:-2])
				for i in range(0,len(products)):
					if products[i] == 'JETEPAR  10ML  AMP':
						products[i] = '008999'
					if products[i] == 'JETEPAR  2ML  AMP':
						products[i] = '004348'
					if products[i] == 'JETEPAR  CAP':
						products[i] = '002392'
					if products[i] == 'JETEPAR  SYP':
						products[i] = '002188'
					if products[i] == 'MAIORAD  AMP':
						products[i] = '009072'
					if products[i] == 'METRONIDAZOLE 400MG TAB':
						products[i] = '081274'
					if products[i] == 'CYANORIN  FORTE  AMP':
						products[i] = '005425'
					if products[i] == 'MOXILIUM  SYP  125MG':
						products[i] = '006783'
					if products[i] == 'MOXILIUM  SYP  250MG':
						products[i] = '012649'
					if products[i] == 'MOXILIUM  DROPS':
						products[i] = '006782'
					if products[i] == 'VIGROL  FORTE  TAB':
						products[i] = '007018'
					if products[i] == 'PC-LAC  SYP':
						products[i] = '019133'
					if products[i] == 'VIKONON  FORTE  SYP':
						products[i] = '006406'
					if products[i] == 'SUPRACEF  SUSP  100MG':
						products[i] = '024819'
				for i in range(len(sales)):
					for k in range(len(sales[i])):
						if sales[i][k] == '-':
							sales[i][k] = '0' 
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
				result = green_team_bricks(result)
				return result

			elif dist_city == "Toba Tek Singh":
				result = []
				products = []
				sale_quantity = []
				sales_price = []
				sales = []
				bricks = []
				brick = []
				product = []
				flag_1 = False
				for x in range(0,len(pdf.pages)):
					data = pdf.pages[x].extract_text()
					bricks = pdf.pages[x].extract_table()
					bricks = bricks[0]
					bricks = bricks[1:-1]
					data = re.sub("\n","$", data)
					data = data.split('$')
					for i in range(len(bricks)):
						if bricks[i] != '':
							brick.append(bricks[i])
					for i in range(0,len(data)):
						find_Blue = re.search(r"BLUE", data[i-1])
						if find_Blue != None:
							flag_1 = True
						find_group = re.search(r"Group Total", data[i])
						if find_group != None:
							flag_1 = False
						if flag_1 == True:
							sales.append(data[i])
					for i in range(0,len(sales)):
						sales[i] = re.sub("\'S","$", sales[i])
						sales[i] = re.sub("ML","$", sales[i])
						sales[i] = sales[i].split('$')
						products.append(sales[i][0])
						sales[i] = sales[i][-1][1:]
						sales[i] = re.sub("\s+","$", sales[i])
						sales[i] = sales[i].split('$')
						sales[i] = sales[i][0:len(brick)]
					for i in range(0,len(products)):
						if products[i] == 'JETEPAR 10':
							products[i] = '008999'
						if products[i] == 'JETEPAR 2':
							products[i] = '004348'
						if products[i] == 'JETEPAR CAP 20':
							products[i] = '002392'
						if products[i] == 'JETEPAR SYP 112':
							products[i] = '002188'
						if products[i] == 'MAIORAD  3':
							products[i] = '009072'
						if products[i] == 'MAIORAD TAB 30':
							products[i] = '012961'
					for i in range(0,len(brick)):
						if brick[i] == 'GOJRA':
							brick[i] = 'GOJRA TTS'
						if brick[i] == 'KAMAL':
							brick[i] = 'KAMAL CHOWK'
						if brick[i] == 'PIR M':
							brick[i] = 'PIR MAHAL'
						if brick[i] == 'RAJAN':
							brick[i] = 'RAJANA'
						if brick[i] == 'S/WAL':
							brick[i] = 'SAHIWAL TTS'
						if brick[i] == 'TOBA':
							brick[i] = 'TOBA TEK SINGH TTS'
				for p in range(0,len(products)):
					for s in range(0,len(sales[p])):
						child = []
						child.append(products[p])
						child.append(brick[s])
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
							# print(r)
				result = green_team_bricks(result)
				return result
			elif dist_city == "Dera Ghazi Khan":
				result = []
				products = []
				bricks = []
				new_result = []
				sales = []
				for x in range(0,len(pdf.pages)):
					data = pdf.pages[x].extract_table()
					brick = data[0]
					data = data[1:7]

					for i in range(2,len(brick)):
						brick[i] = brick[i].replace("\n", "")
						brick[i] = brick[i][::-1]
						# print(brick[i])
						if 'BALAK HSARWAR' in brick[i]:
							bricks.append('BALAKH SARWAR')
						if 'CHOTIT' in brick[i]:
							bricks.append('CHOTI')
						if 'DJAAL' in brick[i]:
							bricks.append('DAJAL')
						if 'FAREED YBAZAR' in brick[i]:
							bricks.append('FAREEDY BAZAR')
						if 'FAIZ LPUR' in brick[i]:
							bricks.append('FAZIL PUR')
						if 'GADDIA' in brick[i]:
							bricks.append('GADDAI')
						if 'H IJAPUR' in brick[i]:
							bricks.append('HAJIPUR')
						if 'JAMPUR' in brick[i]:
							bricks.append('JAMPUR')
						if 'JHO KUTRAH' in brick[i]:
							bricks.append('JHOK UTRA')
						if 'KALA' in brick[i]:
							bricks.append('KALA')
						if 'KO TCHUTTA' in brick[i]:
							bricks.append('KOT CHUTTA')
						if 'KO TMETHAN' in brick[i]:
							bricks.append('KOT MITHAN')
						if 'KOTL AMUGHLAN' in brick[i]:
							bricks.append('KOTLA MUGHLAN')
						if 'MAN AAHMDAIN' in brick[i]:
							bricks.append('MANA AHMDANI')
						if 'MOHAMMA DPUR' in brick[i]:
							bricks.append('MOHAMMAD PUR')
						if 'NEDAORLLOC WEG E' in brick[i]:
							bricks.append('NEW COLLEGE ROAD')
						if 'PEE RAAIDL' in brick[i]:
							bricks.append('PIR ADIL')
						if 'IP RQATTAL' in brick[i]:
							bricks.append('PIR QATAL')
						if 'QUIAAOR-E-DDAZA M' in brick[i]:
							bricks.append('QUAID-E-AZAM ROAD')
						if 'RIALWA YROAD' in brick[i]:
							bricks.append('RAILWAY ROAD DGK')
						if 'RJAA NPUR' in brick[i]:
							bricks.append('RAJANPUR')
						if 'SADA RBAZAR' in brick[i]:
							bricks.append('SADAR BAZAR')
						if 'SAK IHSARWAR' in brick[i]:
							bricks.append('SAKHI SARWAR')
						if 'SHADA NLUND' in brick[i]:
							bricks.append('SHADAN LUND')
						if 'SHA HSADA RIDN' in brick[i]:
							bricks.append('SHAH SADAR DIN')
						if 'TAUNSA' in brick[i]:
							bricks.append('TAUNSA')
						if 'IT IBIKSSRAIN' in brick[i]:
							bricks.append('TIBBI QAISRANI')
						if 'WHOHWA' in brick[i]:
							bricks.append('WHOLESALE DGK')
						if brick[i] == 'latoT':
							break

					for i in range(0,len(data)-1):
						if x == len(pdf.pages)-1:
							
							if data[i][1] == sales[i][0]:
								for k in range(2,len(data[i])-1):
									sales[i].append(data[i][k])
						else:
							if x == 0:
								sales.append(data[i][1:])
							else:
								if data[i][1] == sales[i][0]:
									for k in range(2,len(data[i])):
										sales[i].append(data[i][k])
				for i in range(0,len(sales)):
					products.append(sales[i][0])
					sales[i] = sales[i][1:]
					for k in range(0,len(sales[i])):
						if sales[i][k] == '-':
							sales[i][k] = '0' 
					if products[i] == 'JETEPAR 10ML INJ 5 S':
						products[i] = '008999'
					if products[i] == 'JETEPAR 2ML INJ 10 S':
						products[i] = '004348'
					if products[i] == 'JETEPAR CAP 20 S':
						products[i] = '002392'
					if products[i] == 'JETEPAR SYP 112ML':
						products[i] = '002188'
					if products[i] == 'MAIORAD 3ML INJ 6 S':
						products[i] = '009072'
					if products[i] == 'MAIORAD TAB 30 S':
						products[i] = '012961'
				for p in range(0,len(products)):
					for s in range(0,len(sales[p])):
						child = []
						child.append(products[p])
						child.append(bricks[s])
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
				new_result = green_team_bricks(new_result)
				return new_result

			elif dist_city == "Jhang":
				result = []
				new_result = []
				products = []
				bricks = []
				sale_quantity = []
				sales_price = []
				sales = []
				# bricks = ['ATHARA HAZARI', 'AHMADPUR SIAL', 'BHOWA', 'GOJRA JNG', 'JHANG 1', 'JHANG 2', 'KOT SHAKIR JNG', 'SHAH JEEWNA', 'SHORKOT CANTT', 'SHORKOT JNG']
				product = []
				flag_1 = False
				for x in range(0,len(pdf.pages)):
					data = pdf.pages[x].extract_text()
					data = re.sub("\n","$", data)
					data = data.split('$')
					brick = re.sub(r"\s+","#",data[4])
					brick = brick.split('#')
					brick = brick[3:-2]
					for i in range(0,len(data)):
						find_Blue = re.search(r"BLUE", data[i-1])
						if find_Blue != None:
							flag_1 = True
						find_Green = re.search(r"GREEN", data[i-1])
						if find_Green != None:
							flag_1 = True
						find_group = re.search(r"Group Total", data[i])
						if find_group != None:
							flag_1 = False
						if flag_1 == True:
							sales.append(data[i])
					for i in range(0,len(sales)):
						sales[i] = re.sub("\'S","$", sales[i])
						sales[i] = re.sub("ML","$", sales[i])
						sales[i] = sales[i].split('$')
						products.append(sales[i][0])

					var_for_jhang_brick = True
					for i in range(0,len(brick)):
						if brick[i] == '18':
							bricks.append('ATHARA HAZARI')
						if brick[i] == 'AHMAD':
							bricks.append('AHMADPUR SIAL')
						if brick[i] == 'BHOW':
							bricks.append('BHOWA')
						if brick[i] == 'GOJRA':
							bricks.append('GOJRA JNG')
						if brick[i] == 'JHANG' and var_for_jhang_brick == True:
							bricks.append('JHANG 1')
							var_for_jhang_brick = False
						if brick[i] == 'JHANG' and var_for_jhang_brick == False:
							bricks.append('JHANG 2')
							var_for_jhang_brick = 'Please do not change or remove this statement it works'
						if brick[i] == 'KOT':
							bricks.append('KOT SHAKIR JNG')
						if brick[i] == 'SHAH':
							bricks.append('SHAH JEEWNA')
						if brick[i] == 'SHK.C':
							bricks.append('SHORKOT CANTT')
						if brick[i] == 'SHORK':
							bricks.append('SHORKOT JNG')

					for i in range(0,len(sales)):
						if products[i] == 'JETEPAR  2':
							products[i] = '004348'
						if products[i] == 'JETEPAR 10':
							products[i] = '008999'
						if products[i] == 'JETEPAR CAP 20':
							products[i] = '002392'
						if products[i] == 'JETEPAR SYP 112':
							products[i] = '002188'
						if products[i] == 'MAIORAD  3':
							products[i] = '009072'
						if products[i] == 'METRONIDAZOLE 400 MG 100':
							products[i] = '081274'
						if products[i] == 'METRONIDAZOLE TAB 200 100':
							products[i] = '008909'
						if products[i] == 'MOXILIUM DROP 10% 10':
							products[i] = '006782'
						if products[i] == 'MOXILIUM SYP 125MG 45':
							products[i] = '006783'
						if products[i] == 'MOXILIUM SYP 250MG 60':
							products[i] = '012649'
						if products[i] == 'P.C.LAC SYP 120':
							products[i] = '019133'
						if products[i] == 'VIKNON FORTE 120':
							products[i] = '006406'
						sales[i] = sales[i][-1]
						sales[i] = re.sub("\s+","$", sales[i])
						sales[i] = sales[i].split('$')
						sale_quantity.append(sales[i][-3:])
						sales[i] = sales[i][1:len(bricks)+1]
				for p in range(0,len(products)):
					for s in range(0,len(sales[p])):
						child = []
						child.append(products[p])
						child.append(bricks[s])
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
							# print(r)

				new_result = green_team_bricks(new_result)
				return new_result
			elif dist_city =="Sargodha":
				result = []
				products = []
				bricks = ['MALAKWAL SGD','AKT','JAUHARABAD ','KHUSHAB','MITHA LAK','NOWSHRA','NUR','QUAIDABAD'
				,'CHOWKI BHAGAT','BHALWAL','BHERA','FAROOKA','JAVERIA','KOT MOMIN','MARI LAK','PHL','SAHIWAL'
				,'SARGODHA 1','SHAHPUR']
				bricks2 = ['SILLANWALI','ADA46 49TAL','SARGODHA 2','WHOLESALE SGD']
				sales = []
				second_page = False
				for x in range(0,len(pdf.pages)):
					data = pdf.pages[x].extract_text()
					data = re.sub("\n","$", data)
					data = data.split('$')
					
					find_second_page = re.search(r"TOTAL", data[3])
					data1 = data[6:-2] # for sales
					data = data[6:-2] # for poduct
					for i in range(0,len(data)):
						data[i] = re.sub("\s\s\s+","$", data[i])
						data[i] = data[i].split('$')
						products.append(data[i][0])
						data1[i] = re.sub("\s+","$", data1[i])
						data1[i] = data1[i].split('$')
						if find_second_page != None:
							second_page = True
							# print(second_page)
						if second_page == True:
							sales.append(data1[i][-6:-2])
						else:
							sales.append(data[i][-19:])
				for i in range(len(products)):
					if products[i] == "AFLOXAN  CAPSUL":
						products[i] = "008376"
					if products[i] == "AFLOXAN TABLET":
							products[i] = "017230"
					if products[i] == "ALOPRA 20 MG TABLET":
							products[i] = "029986"
					if products[i] == "AVOR 1MG TABLET":
							products[i] = "006584"
					if products[i] == "AVOR 2 MG TABLET":
							products[i] = "007853"
					if products[i] == "BIGUANAIL 250 MG TABLET":
							products[i] = "003718"
					if products[i] == "BIGUANAIL 500 MG TABLET":
							products[i] = "005310"
					if products[i] == "CODAMIN-P TABLET 50'S":
							products[i] = "028729"
					if products[i] == "CYANORIN FORTE INJ":
							products[i] = "005425"
					if products[i] == "DEKOF TABLET":
							products[i] = "777777"
					if products[i] == "DEPROGESIC P TAB":
							products[i] = "081838"
					if products[i] == "DEPROGESIC TABLET":
							products[i] = "777777"
					if products[i] == "EBAST TABLET 10 MG":
							products[i] = "023906"
					if products[i] == "HISTAFEX 120 MG TABLET":
							products[i] = "031037"
					if products[i] == "HISTAFEX 180 MG TABLET":
							products[i] = "031038"
					if products[i] == "ISRIP 1 MG TABLET":
							products[i] = "035294"
					if products[i] == "ISRIP 2MG TABLET":
							products[i] = "035295"
					if products[i] == "ISRIP 3MG TABLET":
							products[i] = "035296"
					if products[i] == "ISRIP 4 MG TABLET":
							products[i] = "035297"
					if products[i] == "JETEPAR 10 ML INF":
							products[i] = "008999"
					if products[i] == "JETEPAR 2CC INJ":
							products[i] = "004348"
					if products[i] == "JETEPAR CAPSUL":
							products[i] = "002392"
					if products[i] == "JETEPAR SYRUP 112ML":
							products[i] = "002188"
					if products[i] == "MAIROAD INJ  3 ML":
							products[i] = "009072"
					if products[i] == "MAIROAD TABLET":
							products[i] = "012961"
					if products[i] == "MALTEM 40 MG TABLET":
							products[i] = "777777"
					if products[i] == "MALTEM PLUS DS":
							products[i] = "071560"
					if products[i] == "METRONIDAZOLE TAB 200":
							products[i] = "008909"
					if products[i] == "METRONIDAZOLE TAB 400":
							products[i] = "081274"
					if products[i] == "MILID 200 MG TABLET":
							products[i] = "777777"
					if products[i] == "MILID 400 MG TABLET":
							products[i] = "777777"
					if products[i] == "MINGAIR 10 MG TABLET":
							products[i] = "038427"
					if products[i] == "MINGAIR 5 MG TABLET":
							products[i] = "038426"
					if products[i] == "MOXILIUM 125 MG SUSPEN 45 ML  SUSPEN45 ML":
							products[i] = "006783"
					if products[i] == "MOXILIUM 250 MG CAP":
							products[i] = "006784"
					if products[i] == "MOXILIUM 250 MG SUSPEN 60 ML  SUSPEN60 ML":
							products[i] = "012649"
					if products[i] == "MOXILIUM 500 MG CAP":
							products[i] = "008908"
					if products[i] == "MOXILIUM DROPS 10 ML":
							products[i] = "006782"
					if products[i] == "Obexil 20 mg":
							products[i] = "032259"
					if products[i] == "PC-LAC SYRUP 120 ML":
							products[i] = "019133"
					if products[i] == "PROBITOR  20 MG CAPSUL":
							products[i] = "016654"
					if products[i] == "SAVELOX  250MG TABLET":
							products[i] = "032255"
					if products[i] == "SAVELOX 500MG TABLET":
							products[i] = "029328"
					if products[i] == "SUPRACEF CAPSUL":
							products[i] = "024820"
					if products[i] == "SUPRACEF SUSPEN 30 ML":
							products[i] = "024819"
					if products[i] == "SUPRACEF-DS SYRUP 30 ML":
							products[i] = "028727"
					if products[i] == "SUPRALOX SUSPEN 50 ML":
							products[i] = "028728"
					if products[i] == "SUPRALOX TABLET":
							products[i] = "777777"
					if products[i] == "TRAMAGESIC INJ 5 AMPS":
							products[i] = "026920"
					if products[i] == "TRAMGESIC CAPSUL":
							products[i] = "029327"
					if products[i] == "VIGROL FORTE TABLET":
							products[i] = "007018"
					if products[i] == "VIKONON FORTE SYRUP 120 ML":
							products[i] = "006406"
				for p in range(0,len(products)):
					for s in range(0,len(sales[p])):
						if products[p] != '777777':
							child = []
							child.append(products[p])
						if second_page == True:
							child.append(bricks2[s])
						else:
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
				result = green_team_bricks(result)
				return result
			elif dist_city == "Mianwali":
				result = []
				new_result = []
				products = []
				bricks = ['PIPLAN','ISA KHEL','KAMAR MASHANI','WAN BHACHRAN','LAWA','MAINWALI MWL','TRUG','MAKERWAL','HARNOLI','MUSAKHEL','HAFIZ WALA','SHADIA','QUAIDABAD MWL'
				,'DHQ MIANWALI','CHAKRALA MWL','KUNDIAN','DILLY WALI','ISKANDERABAD','KALABAGH']
				bricks2 = ['KOT CHANDNA']
				sales = []
				second_page = False
				for x in range(0,len(pdf.pages)):
					data = pdf.pages[x].extract_text()
					data = re.sub("\n","$", data)
					data = data.split('$')
					find_second_page = re.search(r"TOTAL", data[3])
					if find_second_page != None:
						second_page = True
						data = data[5:-1] # for poduct
					else:
						data = data[6:-2]
					for i in range(0,len(data)):
						data[i] = re.sub("\s\s+","$", data[i])
						data[i] = data[i].split('$')
						products.append(data[i][0])
						if second_page == True:
							sales.append(data[i][2])
						else:
							sales.append(data[i][-19:])
				for i in range(0,len(products)):
					if products[i] == "AFLOXAN CAP":
							products[i] = "008376"  
					if products[i] == "AFLOXAN TAB":
							products[i] = "017230"
					if products[i] == "JETEPAR 10ML AMPS":
							products[i] = "008999"
					if products[i] == "JETEPAR 2ML AMPS":
							products[i] = "004348"
					if products[i] == "JETEPAR CAP":
							products[i] = "002392"
					if products[i] == "JETEPAR SYP":
							products[i] = "002188"
					if products[i] == "MAIORAD 3ML AMPS":
							products[i] = "009072"
					if products[i] == "MAIORAD TAB":
							products[i] = "012961"
				for p in range(0,len(products)):
					for s in range(0,len(sales[p])):
						child = []
						child.append(products[p])
						if second_page == True:
							child.append(bricks2[s])
						else:
							child.append(bricks[s])
						child.append(sales[p][s])
						result.append(child)
				for r in  range(0,len(result)):
					for i in item_list:
						if result[r][0] == i[0]:
							if result[r][2] != '0':
								new_result.append(result[r])  
							
				for r in  range(0,len(new_result)):
					for i in item_list:
						if result[r][0] == i[0]:
								new_result[r].insert(1,i[1])
								new_result[r].append(i[2]) 
				for r in new_result:
					for t in tt_list:    
						if r[2] == t[0]:
							r.insert(4,t[1])
				new_result = green_team_bricks(new_result)			
				return new_result
			elif dist_city =="Bhakkar":
				result = []
				products = []
				bricks = []
				new_result = []
				# bricks = ['CHAK 214 AND 217','ALI KHAIL AND DELCRS','BASTI','BEHAL','BHAKKAR BKR','DHQ BKR','DARYA KHAN','DULLEWALA','HYDERABAD BKR','HAITO-14CK',
				# 'JAHAN KHAN BKR','JANDWALA','KALLURKOT','KHANSAR','MANKERA','NOTAK','PANJ GIRAIN','PCW. JAV','SARAI MAHAJIR','SHAH ALAM']
				sales = []
				for x in range(0,len(pdf.pages)):
					data = pdf.pages[x].extract_table()
					brick = (data[1])
					for i in range(len(data)):
						if "Group Name" in data[i][0]:
							start_var = i+1
							# print(start_var)
						if "Group Total" in data[i][0]:
							stop_var = i
					data = data[start_var:stop_var]
					for i in range(2,len(brick)):
						brick[i] = brick[i].replace("\n", "")
						brick[i] = brick[i][::-1]
						# print(brick[i])
						if '21-4217' in brick[i]:
							bricks.append('CHAK 214 AND 217')
						if 'AILKHIAL+DELCRS' in brick[i]:
							bricks.append('ALI KHAIL AND DELCRS')
						if 'BAS IT' in brick[i]:
							bricks.append('BASTI')
						if 'BEHAL' in brick[i]:
							bricks.append('BEHAL')
						if 'BHKR' in brick[i]:
							bricks.append('BHAKKAR BKR')
						if 'DHQ' in brick[i]:
							bricks.append('DHQ BKR')
						if 'DRYA' in brick[i]:
							bricks.append('DARYA KHAN')
						if 'DULEWALA' in brick[i]:
							bricks.append('DULLEWALA')
						if 'HIADRABAD' in brick[i]:
							bricks.append('HYDERABAD BKR')
						if 'HIAT-O14CK' in brick[i]:
							bricks.append('HAITO 14CK')
						if 'IJAZ' in brick[i]:
							bricks.append('IJAZ')
						if 'JAH NKHAN' in brick[i]:
							bricks.append('JAHAN KHAN BKR')
						if 'JANDWALA' in brick[i]:
							bricks.append('JANDWALA')
						if 'KALUR' in brick[i]:
							bricks.append('KALLURKOT')
						if 'KHANSAR' in brick[i]:
							bricks.append('KHANSAR')
						if 'MANKERA' in brick[i]:
							bricks.append('MANKERA')
						if 'NM C' in brick[i]:
							bricks.append('NMC')
						if 'NOTAK' in brick[i]:
							bricks.append('NOTAK')
						if 'PANJGRIAN' in brick[i]:
							bricks.append('PANJ GIRAIN')
						if 'PC .WJAV' in brick[i]:
							bricks.append('PCW JAV')
						if 'SARIA' in brick[i]:
							bricks.append('SARAI MAHAJIR')
						if 'SHAHALA M' in brick[i]:
							bricks.append('SHAH ALAM')

						if brick[i] == 'ƒ':
							break

					for i in range(len(data)):
						products.append(data[i][0])
						sales.append(data[i][2:-2])
						if products[i] == 'JETIPAR 10ML':
							products[i] = '008999'
						if products[i] == 'JETIPAR 2ML':
							products[i] = '004348'
						if products[i] == 'JETIPAR CAP':
							products[i] = '002392'
						if products[i] == 'JETIPAR SYP':
							products[i] = '002188'
						if products[i] == 'MAIORAD TAB':
							products[i] = '012961'
						if products[i] == 'MAIORAD INJ':
							products[i] = '009072'
				
					for i in range(len(sales)):
						for k in range(len(sales[i])):
							if sales[i][k] == '-':
								sales[i][k] = '0' 

				for p in range(0,len(products)):
					for s in range(0,len(sales[p])):
						child = []
						child.append(products[p])
						child.append(bricks[s])
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
				new_result = green_team_bricks(new_result)
				return new_result

			elif dist_city =="Mingora":
				result = []
				new_result = []
				products = []
				bricks = []
				bricks1 = []
				bricks3 = []
				sales = []
				final_sale = []
				sales5 = []
				mingora1 = True	
				mingora3 = False
				temp_var = 1
				for x in range(0,len(pdf.pages)):
					data = pdf.pages[x].extract_text()
					data = re.sub('\n','$',data)
					data = data.split('$')
					if x == 0 or x == 1 :
						bricks1 = data[8]
						bricks1 = re.sub('\s+','$',bricks1)
						bricks1 = bricks1.split('$')
						if x == 1:
							bricks3 = bricks3 + bricks1[4:-2]
						else:
							bricks3 = bricks1[4:]
					if data[8][-10:]== 'Total Sale':
						sales3 = data[10:-2]
						for i in range(len(sales1)):
							sales4 = re.sub('\s','$',sales3[i])
							sales4 = sales4.split('$')
							sales5.append(sales4)
					else:
						sales1 = data[10:-2]
						for i in range(len(sales1)):
							sales2 = re.sub('\s','$',sales1[i])
							sales2 = sales2.split('$')
							sales.append(sales2)
				for i in range(len(sales)):
					if sales[i][0] == sales5[i][0]:
						sales[i] = sales[i] + sales5[i][-14:-2]
						products.append(sales[i][0])
						sales[i] = sales[i][-32:]
						# print(sales[i])
				for i in range(len(sales)):
					sales[i] = [int(x) for x in sales[i]]
					temp_sale = []
					for k in range(0,len(sales[i]),2):
						temp_sale.append(sales[i][k]+sales[i][k+1])
					final_sale.append(temp_sale)
					final_sale[i] = [str(x) for x in final_sale[i]]
				for i in range(0,len(products)):
					if products[i] == '2700':
						products[i] = '008999'
					if products[i] == '2701':
						products[i] = '004348'
					if products[i] == '2702':
						products[i] = '002392'
					if products[i] == '2703':
						products[i] = '002188'
					if products[i] == '2727':
						products[i] = '008376'
					if products[i] == '2728':
						products[i] = '017230'
					if products[i] == '2737':
						products[i] = '009072'
					if products[i] == '2738':
						products[i] = '012961'
					if products[i] == '2705':
						products[i] = '024819'
					if products[i] == '2706':
						products[i] = '028727'
					if products[i] == '2707':
						products[i] = '024820'
					if products[i] == '2708':
						products[i] = '006406'
					if products[i] == '2709':
						products[i] = '007018'
					if products[i] == '2710':
						products[i] = '005425'
					if products[i] == '2713':
						products[i] = '028729'
					if products[i] == '2714':
						products[i] = '016654'
					if products[i] == '2730':
						products[i] = '006783'
					if products[i] == '2731':
						products[i] = '012649'
					if products[i] == '2732':
						products[i] = '008908'
					if products[i] == '2733':
						products[i] = '006784'
					if products[i] == '2734':
						products[i] = '006782'
					if products[i] == '2739':
						products[i] = '026920'
					if products[i] == '2740':
						products[i] = '029327'
					if products[i] == '2741':
						products[i] = '028728'
					if products[i] == '2754':
						products[i] = '019133'
					if products[i] == '2756':
						products[i] = '038426'
					if products[i] == '2757':
						products[i] = '038426'
					if products[i] == '2759':
						products[i] = '032259'
					if products[i] == '2760':
						products[i] = '032255'
					if products[i] == '2761':
						products[i] = '029328'
					if products[i] == '7153':
						products[i] = '081838'
					if products[i] == '7154':
						products[i] = '081274'
				for i in range(0,len(bricks3)):
					if 'MINGORA' in bricks3[i] and mingora1 == True:
						bricks3[i] = 'MINGORA 1'
						bricks.append(bricks3[i])
						mingora1 = False

					if 'MINGORA' in bricks3[i] and mingora3 == True:
						bricks3[i] = 'MINGORA 3'
						bricks.append(bricks3[i])

					if 'BARIKOT' in bricks3[i]:
						bricks3[i] = 'BARIKOT'
						bricks.append(bricks3[i])
					if 'BUTKHELA' in bricks3[i]:
						bricks3[i] = 'BATKHELA'
						bricks.append(bricks3[i])
					if 'BUNIR' in bricks3[i]:
						bricks3[i] = 'BUNER'
						bricks.append(bricks3[i])
					if 'BESHAM' in bricks3[i]:
						bricks3[i] = 'BISHAM'
						bricks.append(bricks3[i])
					if 'MATTA' in bricks3[i]:
						bricks3[i] = 'MATTA SWAT'
						bricks.append(bricks3[i])
					if 'K.KHELA-4BAG' in bricks3[i]:
						bricks3[i] = 'KHWAZA KHELA'
						bricks.append(bricks3[i])
					if 'MINGORA-' in bricks3[i]:
						bricks3[i] = 'MINGORA 2'
						bricks.append(bricks3[i])
					if 'MAD.BAH.FATH' in bricks3[i]:
						bricks3[i] = 'MADYAN AND BAHRAIN AND FATEHPUR'
						bricks.append(bricks3[i])
					if 'PURAN' in bricks3[i]:
						bricks3[i] = 'PURAN'
						bricks.append(bricks3[i])
					if 'SAIDU+CENTER' in bricks3[i]:
						bricks3[i] = 'SAIDU AND CENTER'
						bricks.append(bricks3[i])
					if 'COUNTER' in bricks3[i]:
						bricks3[i] = 'COUNTER SALE'
						bricks.append(bricks3[i])
					if 'TIMARGARA' in bricks3[i]:
						bricks3[i] = 'TIMARGARA MGR'
						bricksnew_result = green_team_bricks(new_result).append(bricks3[i])
						mingora3 = True
					if 'SOLD' in bricks3[i]:
						bricks3[i] = 'SOLD AREA'
						bricks.append(bricks3[i])

					if 'KABAL' in bricks3[i]:
						bricks3[i] = 'KABAL'
						bricks.append(bricks3[i])

				for p in range(0,len(products)):
					for s in range(0,len(final_sale[p])):
						child = []
						child.append(products[p])
						child.append(bricks[s])
						child.append(final_sale[p][s])
						result.append(child)
				for r in  range(0,len(result)):
					for i in item_list:
						if result[r][0] == i[0]:
							if result[r][2] != '0':
								new_result.append(result[r])  
				for r in new_result:
					for i in item_list:
						if r[0] == i[0]:
							r.insert(1,i[1])
							r.append(i[2]) 
							# print(r)
				for r in new_result:
						for t in tt_list:    
							if r[2] == t[0]:
								r.insert(4,t[1])
				# print(new_result)
				new_result = green_team_bricks(new_result)
				return new_result
			elif dist_city =="MULTAN":
				result = []
				products = []
				new_result = []
				brick = []
				bricks = []
				sales = []
				sales2 = []
				last_page = False
				for x in range(0,len(pdf.pages)):
					data = pdf.pages[x].extract_table()
					for i in range(1,len(data[0])):
					#   # for k in range(0,len(brick[i])):
						data[0][i] = str(data[0][i]).replace('\n','')
						brick.append(data[0][i])
					# print(products)
					for i in range(0,len(brick)):
						if 'D AORR NEATTHLSUNIM' in brick[i]:
							brick[i] = 'NISHTER ROAD MULTAN'
						if 'TTNACN ATLUM' in brick[i]:
							brick[i] = 'MULTAN CANTT'
						if 'D ABAUJHDSAD OLR' in brick[i] or 'D ABAUJHDSALD ROO' in brick[i]:
							brick[i] = 'OLD SUJABAD ROAD'
						if 'D AORY NAAWTAILMULR' in brick[i]:
							brick[i] = 'RAILWAY ROAD'
						if 'H AHSK SWACHOABB' in brick[i] or 'H AHSK SWAHOABBC' in brick[i]:
							brick[i] = 'CHOWK SHAH ABBAS'
						if 'D ABAZNAATTMLUUMM' in brick[i]:
							brick[i] = 'MUMTAZABAD MULTAN'
						if 'K WOHNCAC.G. ULTB.M' in brick[i]:
							brick[i] = 'BGC CHOWK'
						if 'E TK GATANALPU' in brick[i]:
							brick[i] = 'PAK GATE'
						if 'E TAGM ANATRLAUHM' in brick[i]:
							brick[i] = 'HARAM GATE'
						if 'L AMAHAFIZ JROAD' in brick[i]:
							brick[i] = 'HAFIZ JAMAL ROAD'
						if 'E TAGT NAALTULAUDM' in brick[i]:
							brick[i] = 'DAULAT GATE MULTAN'
						if 'H AHSM ODOASOARM' in brick[i]:
							brick[i] = 'MASOOM SHAH ROAD'
						if '1 O. NGI ANNTULHUCM' in brick[i]:
							brick[i] = 'CHUNGI NO 1'
						if 'D AONRAT.B. ULT' in brick[i]:
							brick[i] = 'T.B ROAD MULTAN'
						if 'NATLUMW EN' in brick[i]:
							brick[i] = 'NEW MULTAN'
						if 'FI AZAQNK AWTLOUHMC' in brick[i]:
							brick[i] = 'CHOWK QAZAFI'
						if 'D ABANMIJTA2) SAMUL' in brick[i] or 'D ABANMIJTAAUL2) SM' in brick[i]:
							brick[i] = 'SAMIJABAD'
						if 'L LRAEHLN ALWSOE TL' in brick[i] or 'L LRAEN HALLWSOE' in brick[i]:
							brick[i] = 'TOWN HALL WHOLE SALLER'
						if '9 O.NUNGI LTANHUCM' in brick[i]:
							brick[i] = 'CHUNGI NO 9'
						if 'T HSANGALTULGU' in brick[i]:
							brick[i] = 'GULGASHT'
						if 'D, AON RAN.ATSLOUBM' in brick[i]:
							brick[i] = 'BOSAN ROAD'
						if 'R UPB ADWAAONR' in brick[i]:
							brick[i] = 'NAWAB PUR ROAD'
						if 'A. D.M.K ANWTOLHUCM5) 31(' in brick[i]:
							brick[i] = 'MDA CHOWK'
						if 'NI AMIAJ DRAUOORS' in brick[i]:
							brick[i] = 'SURAJ MIANI ROAD'
						if 'L ANWAHANEMULTKD' in brick[i]:
							brick[i] = 'KHANEWAL'
						if 'H AHSR DEAHOSR' in brick[i]:
							brick[i] = 'SHER SHAH ROAD'
						if 'KWOHCRI AHEV' in brick[i]:
							brick[i] = 'VEHARI CHOWK'
						if 'E RALCAEDIPITMS0)HO51(' in brick[i]:
							brick[i] = 'MEDICARE HOSPITAL'
						if 'Y ADNSALISAAWW' in brick[i]:
							brick[i] = 'WASSANDAY WALI'
						if 'LIAWNALHIOR' in brick[i]:
							brick[i] = 'ROHILLAN WALI'
						if 'NATLUSR EHAHS' in brick[i] or 'SHAHER SULTAN' in brick[i]:
							brick[i] = 'SHAHER SULTAN'
						if 'RUPLI A' in brick[i]:
							brick[i] = 'ALI PUR'
						if 'RUPLALA1' in brick[i]:
							brick[i] = 'JALAL PUR'
						if 'DABAUJHS' in brick[i]:
							brick[i] = 'SHUJABAD'
						if 'M OODKHLIMAAL' in brick[i] or 'M OODAKHALLIM' in brick[i]:
							brick[i] = 'MAKHDOOM ALI'
						if 'ZAIF5- K CAHC' in brick[i]:
							brick[i] = 'CHACK 5 FAIZ'
						if 'RALA DDA' in brick[i]:
							brick[i] = 'ADDA LAR MULTAN'
						if 'R AFFAHUZRAMG' in brick[i] or 'R AFFAHZAURMG' in brick[i]:
							brick[i] = 'MUZAFFAR GARH'
						if 'AREESAB' in brick[i]:
							brick[i] = 'BASEERA'
						if 'LAMAH JAHS' in brick[i]:
							brick[i] = 'SHAH JAMAL MULTAN'
						if 'EROMHI SERUQ' in brick[i]:
							brick[i] = 'QURESHI MORE'
						if 'NAWANAS' in brick[i]:
							brick[i] = 'SANAWAN'
						if 'TARUJG' in brick[i]:
							brick[i] = 'GUJRAT MLT'
						if 'UNNAHCN AMI' in brick[i]:
							brick[i] = 'MIAN CHANNU'
						if 'MKIAHL UDBA' in brick[i]:
							brick[i] = 'ABDUL HAKIM'
						if 'ABMALUT' in brick[i]:
							brick[i] = 'TULAMBA'
						if 'HOHKA HCAK' in brick[i]:
							brick[i] = 'KACHA KHOH'
						if 'N SIHOMLA LDADWA' in brick[i]:
							brick[i] = 'ADDA MOHSIN WALL'
						if 'LEEM2 - 1L LUP' in brick[i]:
							brick[i] = 'PULL 12 MEEL'
						if 'RUPM ONOADRHAKHAOMP8' in brick[i]:
							brick[i] = 'MAKHDOOM PUR PAHORAN'
						if 'argabul p' in brick[i]:
							brick[i] = 'PULL BAGAR MULTAN'
						if 'ALAWRBIAK' in brick[i]:
							brick[i] = 'KABIR WALA'
						if 'LAWENAHK' in brick[i]:
							brick[i] = 'KHANEWAL'
						if '41L - LUP' in brick[i]:
							brick[i] = 'PULL 14'
						if 'M OODDKHHIMARAS' in brick[i]:
							brick[i] = 'MAKHDOOM RASHEED'
						if 'ATTAHT' in brick[i]:
							brick[i] = 'THATTA MULTAN'
						if 'SILAIM' in brick[i]:
							brick[i] = 'MAILSI'
						if 'ATOKOD4' in brick[i]:
							brick[i] = 'DOKOTA MULTAN'
						if 'ANIAHA' in brick[i]:
							brick[i] = 'JAHANIAN'
						if 'D AORI RANATVEHMUL9) 01(' in brick[i]:
							brick[i] = 'VEHARI ROAD'
						if 'E- N-NKAH RUMULTHAM SA' in brick[i] or 'E- N-NKARUULTH MHAM SA' in brick[i]:
							brick[i] = 'SHAH RUKN E ALAM'
						if 'NATLUMH AGD E' in brick[i]:
							brick[i] = 'EID GAH MULTAN'
						if 'NARARABL LUP' in brick[i]:
							brick[i] = 'PULL BARARAN'
						if 'D AORHARI MJ)E(V1) 61(' in brick[i]:
							brick[i] = 'VEHARI ROAD'
						if 'N ERLDALTHIPI2) CHOS61(' in brick[i]:
							brick[i] = 'CHILDREN HOSPITAL MULTAN'
						if 'A NELE-STAN-PI6) IBHOS' in brick[i]:
							brick[i] = 'IBN E SENA HOSPITAL'
						if 'C M.A RHSNHTE' in brick[i]:
							brick[i] = 'AHSAN MEDICINE COMPANY NISHTER'
						if 'HRAGN AHK' in brick[i]:
							brick[i] = 'KHAN GARH'
						if 'KOOLAMTI SAB' in brick[i]:
							brick[i] = 'BASTI MALOOK'
						if 'RUPA YNUD' in brick[i]:
							brick[i] = 'DUNYA PUR'
						if 'NWOTN EDRAG' in brick[i]:
							brick[i] = 'GARDEN TOWN'
						if 'DABAR AFFAZUM' in brick[i]:
							brick[i] = 'MUZAFFAR ABAD'
						if 'NHIAWR ALAS' in brick[i]:
							brick[i] = 'SALAR WAHIN'
						if 'D NAA BANDSDOAB' in brick[i]:
							brick[i] = 'ADDA BAND BOSAN'
						if 'N WOTSEL ASMODBYP' in brick[i]:
							brick[i] = 'MODEL TOWN BYPASS'
						if 'NAWNAR' in brick[i]:
							brick[i] = 'RANWAN'
						if 'OGNARL LUP' in brick[i]:
							brick[i] = 'PULL RANGO'
						if 'SALLVIH CUB' in brick[i]:
							brick[i] = 'BUCH VILLAS'
						if 'L EDOMDL AAOZRAF' in brick[i]:
							brick[i] = 'FAZAL MODEL ROAD'
						if 'RUPY ATAT' in brick[i]:
							brick[i] = 'TATAY PUR'
						if 'TNASA LHDOB' in brick[i]:
							brick[i] = 'BUDHLA SANT'
						if 'DAORH ANNA JIM' in brick[i]:
							brick[i] = 'M A JINNAH ROAD'
					bricks = brick[:-1]
					# for p in data:
					if x == len(pdf.pages)-1:
						last_page = True
					if x == 0:
						sales = data[1:-1]
					else:
						sales2 = (data[1:-1])
						for i in range(0,len(sales2)):
							if sales[i][0] == sales2[i][0] and last_page == True:
								sales[i] = sales[i][:] + sales2[i][1:-1]
								products.append(sales[i][0])
							# print(sales[i])
							elif sales[i][0] == sales2[i][0]:
								sales[i] = sales[i][:] + sales2[i][1:]
				
				for i in range(0,len(products)):
					sales[i] = sales[i][1:]
					if 'JETEPAR 2ML INJ' in products[i]:
						products[i] = '004348'
					if 'JETEPAR CAP' in products[i]:
						products[i] = '002392'
					if 'JETEPAR INJ' in  products[i]:
						products[i] = '008999'
					if products[i] == 'JETEPAR 10ML 5S' or products[i] == 'JETEPAR 10ML INJ  5S':
						products[i] = '008999'
					if 'JETEPAR SYP' in products[i]:
						products[i] = '002188'
					# if products[i] == 'JETEPAR SYP. 112ML':
					#   products[i] = '002188'
					if 'MAIORAD INJ' in products[i] or 'MAIORAD 3ML-INJ 6,S' in products[i]:
						products[i] = '009072'
				for p in range(0,len(products)):
					for s in range(0,len(sales[p])):
						child = []
						child.append(products[p])
						child.append(bricks[s])
						child.append(sales[p][s])
						result.append(child)
				for r in  range(0,len(result)):
					for i in item_list:
						if result[r][0] == i[0]:
							if result[r][2] != '0':
								new_result.append(result[r])  
				# print(len(new_result))    
				for r in  range(0,len(new_result)):
					for i in item_list:
						if new_result[r][0] == i[0]:
								new_result[r].insert(1,i[1])
								new_result[r].append(i[2])
								# print(new_result[r]) 
				for r in new_result:
					for t in tt_list:
						if r[2] == t[0]:
							r.insert(4,t[1])
				new_result = green_team_bricks(new_result)
				return new_result
			elif dist_city == "Rahim Yar Khan":
				products = []
				products1 = []
				get_only_once_1 = True
				get_only_once_2 = True
				sales = []
				bricks = []
				bricks1 = []
				result = []
				for x in range(0,len(pdf.pages)):
					data = pdf.pages[x].extract_table()
					if data[0][-1] == 'Total Amount' and get_only_once_1 == True:
						products.append(data[0][1:-1])
						get_only_once_1 = False
					else :
						if get_only_once_2 == False:
							products.append(data[0][1:])
							get_only_once_2 = False
					for i in range(1,len(data)):
						if data[i][0] == 'Total':
							break
						else:
							sales.append(data[i][1:-1])
							bricks.append(data[i][0])     
				products1 = [b for b in products[0][:]]
				for i in range(0,len(products1)):
					products1[i] = re.sub('006011','004348',products1[i][0:6])
					products1[i] = re.sub('006012','002392',products1[i])
					products1[i] = re.sub('006013','002188',products1[i])
					products1[i] = re.sub('006014','008999',products1[i])
					products1[i] = re.sub('006015','012961',products1[i])
					products1[i] = re.sub('006016','009072',products1[i])


					products1[i] = re.sub('031001','002188',products1[i])
					products1[i] = re.sub('031002','009072',products1[i])
					products1[i] = re.sub('031003','012961',products1[i])
					products1[i] = re.sub('031004','002392',products1[i])
					products1[i] = re.sub('006016','009072',products1[i])
    



				for i in range(0,len(bricks)):
					bricks1.append(bricks[i][10:])
					bricks1[i] = re.sub('\n','',bricks1[i])

				for s in range(0,len(sales)):
					for i in range(0,len(sales[s])):
						if sales[s][i] == '-':
							sales[s][i] = '0'  
				for i in range(0,len(bricks1)):
					if bricks1[i] == 'HOSPITAL ROAD-1':
						bricks1[i] = 'HOSPITAL ROAD 1'
					if bricks1[i] == 'HOSPITAL ROAD-2':
						bricks1[i] = 'HOSPITAL ROAD 2'
					if bricks1[i] == 'ABBASIA TWON':
						bricks1[i] = 'ABBASIA TOWN'
					if bricks1[i] == 'KHAN PUR ROAD RYK':
						bricks1[i] = 'KHANPUR ROAD'
					if bricks1[i] == 'GULSHAN iQBAL':
						bricks1[i] = 'GULSHAN E IQBAL'
					if bricks1[i] == 'GULSHAN USMAN':
						bricks1[i] = 'GULSHAN E USMAN'
					if bricks1[i] == 'AIR PORT ROAD RYK':
						bricks1[i] = 'AIRPORT ROAD RYK'
					if bricks1[i] == 'ABU DAHBI ROAD Ryk':
						bricks1[i] = 'ABU DHABI ROAD RYK'
					if bricks1[i] == 'Wireless Pull Ryk':
						bricks1[i] = 'WIRELESS PULL RYK'
					if bricks1[i] == 'NOOR-E-WALI':
						bricks1[i] = 'NOOR E WALI'
					if bricks1[i] == 'IQBAL NAGAR':
						bricks1[i] = 'IQBAL NAGAR RYK'
					if bricks1[i] == 'HOSPITAL ROAD-SDK':
						bricks1[i] = 'HOSPITAL ROAD SDK'
					if bricks1[i] == 'KACHA SADIQA BAD ROAD sdk':
						bricks1[i] = 'KACHA SADIQABAD ROAD'
					if bricks1[i] == 'QAID AZAM ROAD SDK':
						bricks1[i] = 'QUAID AZAM ROAD SDK'
					if bricks1[i] == 'SATTAR SHAHEED ROAD sdk':
						bricks1[i] = 'SATTAR SHAHEED ROAD SDK'
					if bricks1[i] == 'FFC':
						bricks1[i] = 'FAUJI FERTILIZER COMPANY'
					if bricks1[i] == 'HOSPITAL ROAD KHAN PUR':
						bricks1[i] = 'HOSPITAL ROAD KHANPUR'
					if bricks1[i] == 'MODAL TWON kpr':
						bricks1[i] = 'MODEL TOWN KPR'
					if bricks1[i] == 'NAWAKOT ROAD kpr':
						bricks1[i] = 'NAWAKOT ROAD KPR'
					if bricks1[i] == 'BAG-O-BAHAR ROAD KPR':
						bricks1[i] = 'BAG O BAHAR ROAD KPR'
					if bricks1[i] == 'NAWAKOT CHOWK kpr':
						bricks1[i] = 'NAWAKOT CHOWK KPR'
					if bricks1[i] == 'SHUGAR MILL':
						bricks1[i] = 'SUGAR MILL'
					if bricks1[i] == 'NAZ CINEMA ROAD KHAN PUR':
						bricks1[i] = 'NAZ CINEMA ROAD KHANPUR'
					if bricks1[i] == 'BAG-O-BHAR+ BHHISHTI':
						bricks1[i] = 'BAG O BHAR AND BAHISHTI'
					if bricks1[i] == 'PULL SUNNY':
						bricks1[i] = 'SUNNY PULL'
					if bricks1[i] == 'ALLAH BAD':
						bricks1[i] = 'ALLAH ABAD'
					if bricks1[i] == 'AMINA BAD':
						bricks1[i] = 'AMINABAD'
					if bricks1[i] == 'MIAN WALI QURESHI':
						bricks1[i] = 'MIAN WALI QURESHIAN'
					if bricks1[i] == 'KAHI KAIR SHAH':
						bricks1[i] = 'KAHI KHAIR SHAH'
					if bricks1[i] == 'JETHA BUHTA BAZAR kpr':
						bricks1[i] = 'JETHA BHUTA BAZAR'
					if bricks1[i] == 'KACHERY ROAD KHANPUR':
						bricks1[i] = 'KUTCHERY ROAD KHANPUR'
					if bricks1[i] == 'MOR BHUTTA WAAN':
						bricks1[i] = 'MOR BHUTTA WAHAN'
					if bricks1[i] == 'ZAFRA BAD':
						bricks1[i] = 'ZAFARABAD'

				for p in range(0,len(bricks1)):
					for s in range(0,len(sales[p])):
						child = []
						child.append(products1[s])
						child.append(bricks1[p])
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
				result = green_team_bricks(result)
				return result

			elif dist_city == "Bahawalnagar" or "Bahawalpur":
				sales =[]
				bricks = ['BAHAWALNAGAR CITY','DUNGA BUNGA','HAROONABAD','FAQIR WALA','KHICHI WALA','FORT ABBAS','MAROT','MADRASA','CHISHTIAN','DAHRANWALA','MINCHINABAD','MCLEOD GANJ','MANDI SADQ GANJ']
				bahaawalpur_bricks = ['BAHAWALPUR A','BAHAWALPUR B','BAHAWALPUR C','BAHAWALPUR D','KHAIRPUR','HASILPUR','LODHRAN','KAHROR PAKKA','YAZMAN CITY','TAILWALA','AHMEDPUR','UCH SHARIF','MUBARAKPUR']
				# products = ['008376','017230','008999','004348','002392','002188','009072','012961']
				result = []
				products = []
				new_result = []
				info = []
				for x in range(0,len(pdf.pages)):
					data = pdf.pages[x].extract_text()
					data = re.sub("\n","$", data)
					data = data.split('$')
					bahawalpur_Area = re.search(r"Bahawalpur", data[1])
					for d in range(0,len(data)):
						last_row_remove_len = len(data)-5
						if 'Product Pack Rate' in data[d]:
							info = data[d:last_row_remove_len]
					for i in range(0,len(info)):
						if info[i] == 'BLUE TEAM':
							product_sales = info[i+1:]
					for ps in product_sales:
						if 'JETEPAR 10ML INJ. 5S' in ps:
							products.append('008999')
						if 'JETEPAR 2ML INJ. 10S' in ps:
							products.append('004348')
						if 'JETEPAR CAP. 20S' in ps:
							products.append('002392')
						if 'JETEPAR SYRUP 112ML' in ps:
							products.append('002188')
						if 'MAIORAD 3ML INJ. 6S' in ps:
							products.append('009072')
						if 'MAIORAD TAB. 30S' in ps:
							products.append('012961')
						if 'AFLOXON 150MG CAP. 20S' in ps:
							products.append('008376')
						if 'AFLOXON 300MG TAB. 30S' in ps:
							products.append('017230')
						ps = re.sub('\s+','$',ps)
						ps = ps.split('$')
						ps = ps[-15:-2]
						sales.append(ps)
				for p in range(0,len(products)):
					for b in range(0,len(bricks)):
						child_result = []
						child_result.append(products[p])
						if bahawalpur_Area != None:
							child_result.append(bahaawalpur_bricks[b])

						else:
							child_result.append(bricks[b])
						child_result.append(sales[p][b])
						result.append(child_result)
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
			# elif dist_city == "Bahawalpur":
			# 	products = []
			# 	bricks = []
			# 	sales = []
			# 	result = []
			# 	new_result = []
			# 	for x in range(0,len(pdf.pages)):
			# 		data = pdf.pages[x].extract_table()
			# 		bricks = data[0][2:-1]
			# 		for b in range(0,len(bricks)):
			# 			if '13-Soling' in bricks[b]:
			# 				bricks[b] = '13-SOLING'
			# 			if 'Adda 42 \nDB' in bricks[b]:
			# 				bricks[b] = 'ADDA 42 DB'
			# 			if 'ADDA \nSHAHNAL' in bricks[b]:
			# 				bricks[b] = 'ADDA SHAHNAL'
			# 			if 'Ahmed pur \n(City)' in bricks[b]:
			# 				bricks[b] = 'AHMEDPUR'
			# 			if 'Bahawalpu\nr (A)' in bricks[b]:
			# 				bricks[b] = 'BAHAWALPUR A'
			# 			if 'Bahawalpu\nr (B)' in bricks[b]:
			# 				bricks[b] = 'BAHAWALPUR B'
			# 			if 'Bahawalpu\nr (C)' in bricks[b]:
			# 				bricks[b] = 'BAHAWALPUR C'
			# 			if 'Bahawalpu\nr (D)' in bricks[b]:
			# 				bricks[b] = 'BAHAWALPUR D'
			# 			if 'Chandi \nChowk' in bricks[b]:
			# 				bricks[b] = 'CHANDI CHOWK'
			# 			if 'CHANNI \nGOTH' in bricks[b]:
			# 				bricks[b] = 'CHANNI GOTH'
			# 			if 'Chowk \nBhatta' in bricks[b]:
			# 				bricks[b] = 'CHOWK BHATTA'
			# 			if 'Chuna \nWala' in bricks[b]:
			# 				bricks[b] = 'CHUNA WALA'
			# 			if 'Dera \nBakha' in bricks[b]:
			# 				bricks[b] = 'DERA BAKHA'
			# 			if 'Hasilpur \nCity' in bricks[b]:
			# 				bricks[b] = 'HASILPUR'
			# 			if 'Hataji' in bricks[b]:
			# 				bricks[b] = 'HATAJI'
			# 			if 'Head Raj \nkan' in bricks[b]:
			# 				bricks[b] = 'HEAD RAJ KAN'
			# 			if 'Kahror \nPacca City' in bricks[b]:
			# 				bricks[b] = 'KAHROR PAKKA'
			# 			if 'Khan Qah \nSharif' in bricks[b]:
			# 				bricks[b] = 'KHAN QAH SHARIF'
			# 			if 'Kotla Musa \nKhan' in bricks[b]:
			# 				bricks[b] = 'KOTLA MUSA KHAN'
			# 			if 'Lal \nSohanra' in bricks[b]:
			# 				bricks[b] = 'LAL SOHANRA'
			# 			if 'Lodhran \nCity' in bricks[b]:
			# 				bricks[b] = 'LODHRAN'
			# 			if 'Mubarak \npur (City)' in bricks[b]:
			# 				bricks[b] = 'MUBARAKPUR'
			# 			if 'Musafir \nKhana' in bricks[b]:
			# 				bricks[b] = 'MUSAFIR KHANA'
			# 			if 'Noor Pur \nNouranga' in bricks[b]:
			# 				bricks[b] = 'NOOR PUR NOURANGA'
			# 			if 'Pull Farooq \nAbad' in bricks[b]:
			# 				bricks[b] = 'PULL FAROOQ ABAD'
			# 			if 'Qaim pur' in bricks[b]:
			# 				bricks[b] = 'QAIM PUR'
			# 			if 'Shahi Wala \nBungla' in bricks[b]:
			# 				bricks[b] = 'SHAHI WALA BUNGLA'
			# 			if 'Tailwala' in bricks[b]:
			# 				bricks[b] = 'TAILWALA'
			# 			if 'Uch Sharif \n(City)' in bricks[b]:
			# 				bricks[b] = 'UCH SHARIF'
			# 			if 'Yazman \nCity' in bricks[b]:
			# 				bricks[b] = 'YAZMAN CITY'
			# 			if 'ADDA \nPARMET' in bricks[b]:
			# 				bricks[b] = 'ADDA PARMET'
							
							
			# 		# print(data[3:])
			# 		product = data[3:]
			# 		product1 = product[::2]
			# 		products = []
			# 		for p in range(0,len(product1)):
			# 			products.append(product1[p][0:][1])
			# 		for p in range(0,len(products)):
			# 			if 'JETEPAR 10ML' in products[p]:
			# 				products[p] = '008999'
			# 			if 'JETEPAR 2ML' in products[p]:
			# 				products[p] = '004348'
			# 			if 'JETEPAR CAP' in products[p]:
			# 				products[p] = '002392'
			# 			if 'JETEPAR SYRUP' in products[p]:
			# 				products[p] = '002188'
			# 			if 'MAIORAD 3ML' in products[p]:
			# 				products[p] = '009072'
			# 			if 'MAIORAD TAB' in products[p]:
			# 				products[p] = '012961'
			# 			if 'AFLOXAN CAP' in products[p]:
			# 				products[p] = '008376'
			# 			if 'AFLOXAN TAB' in products[p]:
			# 				products[p] = '017230'
						
			# 		sale = data[3:]
			# 		sale1 = sale[::2]
			# 		sales = []
			# 		for s in range(0,len(sale1)):
			# 			sales.append(sale1[s][0:][2:])
			# 			for s in range(0,len(sales)):
			# 				for i in range(0,len(sales[s])):
			# 					if sales[s][i] == '':
			# 						sales[s][i] = '0'
						
			# 		for p in range(0,len(products)):
			# 			for s in range(0,len(sales)):
			# 				for i in range(0,len(sales[s])):
			# 					# print(products[p],bricks[b],sales[s][i])
			# 					child = []
			# 					child.append(products[p])
			# 					child.append(bricks[b])
			# 					child.append(sales[s][i])
			# 					result.append(child)
			# 		for r in  range(0,len(result)):
			# 			for i in item_list:
			# 				if result[r][0] == i[0]:
			# 					if result[r][2] != '0':
			# 						new_result.append(result[r])  
			# 		# print(len(new_result))    
			# 		for r in  range(0,len(new_result)):
			# 			for i in item_list:
			# 				if new_result[r][0] == i[0]:
			# 						new_result[r].insert(1,i[1])
			# 						new_result[r].append(i[2])
			# 						# print(new_result[r]) 
			# 		for r in new_result:
			# 			for t in tt_list:
			# 				if r[2] == t[0]:
			# 					r.insert(4,t[1])
			# 		new_result = green_team_bricks(new_result)
			# 	# return new_result
			# 	print(new_result)













