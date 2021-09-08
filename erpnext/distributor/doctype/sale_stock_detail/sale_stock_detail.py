# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

# import frappe
from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
import pdfplumber
from frappe.utils import get_site_path
import re
from fuzzywuzzy import fuzz

class SaleStockDetail(Document):
    pass

@frappe.whitelist(allow_guest=True)
def parse_pdf(pdf_file,dist_city):
    #print(pdf_file,dist_city)
    arr = re.split('/',pdf_file);
    path = frappe.get_site_path(arr[1],arr[2],arr[3]);
    #print(path)
    alldata = []
    require_data = []
    if(dist_city == "Abbotabad" or dist_city == "Bannu" or dist_city == "Jhelum" or dist_city == "Rawalpindi"):
        with pdfplumber.open(path) as pdf:
            for x in range(0, len(pdf.pages)):
                page = pdf.pages[x]
                data = page.extract_tables()
                #print(data)
                alldata.append(data)
            for i in alldata[:]:
                #print(i)
                for j in i[:]:
                    #print(j)
                    for w in j[:]:
                        arr = list(filter(None, w))
                        #print(arr)
                        require_data.append(arr)
            for x in require_data[:]:
                if(len(x)<11):
                    require_data.remove(x)
            for i in require_data[:]: #abbotabad,bannu,jhelum,rawalpindi
                i[0] = i[0].lstrip('0123456789 ')
                if(i[1]=='-'):    
                    i[1] = re.sub('-',"0", i[1])
                i[3] = re.sub(' -',"", i[3])
                if(i[3]=='-'):
                    i[3] = re.sub('-',"0", i[3])
                i[4] = re.sub(' -',"", i[4])
                if(i[4]=='-'):
                    i[4] = re.sub('-',"0", i[4])
                i[5] = re.sub(' -',"", i[5])
                if(i[5]=='-'):
                    i[5] = re.sub('-',"0", i[5])
                if(i[7]=='-'):    
                    i[7] = re.sub('-',"0", i[7])
                if(i[8]=='-'):    
                    i[8] = re.sub('-',"0", i[8])
                #print(i)
        #print(require_data)
        #print(len(require_data))    
        info = filter_data_bannu(require_data)
    elif(dist_city=="Islamabad" or dist_city == "Narowal"):
        with pdfplumber.open(path) as pdf:
            for x in range(0, len(pdf.pages)):
                page = pdf.pages[x]
                data = page.extract_tables()
                #print(data)
                alldata.append(data)
            for i in alldata[:]:
                #print(i)
                for j in i[:]:
                    #print(j)
                    for w in j[:]:
                        arr = list(filter(None, w))
                        #print(arr)
                        require_data.append(arr)
            for x in require_data[:]:
                if(len(x)<11):
                    require_data.remove(x)
            #print(require_data)        
            for i in require_data[:]: #islamabad,narowal
                i[0] = i[0].lstrip('0123456789 ')
                if(i[1]=='-'):    
                    i[1] = re.sub('-',"0", i[1])
                i[2] = re.sub(r' \d+$', '', i[2])
                i[2] = re.sub(' -',"", i[2])
                if(i[2]=='-'):
                    i[2] = re.sub('-',"0", i[2])
                i[3] = re.sub(r' \d+$', '', i[3])
                i[3] = re.sub(' -',"", i[3])
                if(i[3]=='-'):
                    i[3] = re.sub('-',"0", i[3])
                i[4] = re.sub(' -',"", i[4])
                if(i[4]=='-'):
                    i[4] = re.sub('-',"0", i[4])
                i[6] = re.sub(r' \d+$', '', i[6])
                i[6] = re.sub(' -',"", i[6])
                if(i[6]=='-'):    
                    i[6] = re.sub('-',"0", i[6])
                i[7] = re.sub(r' \d+$', '', i[7])
                i[7] = re.sub(' -',"", i[7])    
                if(i[7]=='-'):    
                    i[7] = re.sub('-',"0", i[7])
                #print(i)
        #print(require_data)
        #print(len(require_data))    
        info = filter_data_islamabad(require_data)
        #print(info)
    elif(dist_city=="Peshawar" or dist_city =="RY Khan"):
        with pdfplumber.open(path) as pdf:
            for x in range(0, len(pdf.pages)):
                page = pdf.pages[x]
                data = page.extract_tables()
                #print(data)
                alldata.append(data)
            for i in alldata[:]:
                #print(i)
                for j in i[:]:
                    #print(j)
                    for w in j[:]:
                        arr = list(filter(None, w))
                        #print(arr)
                        require_data.append(arr)
            for x in require_data[:]:
                if(len(x)<11):
                    require_data.remove(x)
                #print(require_data)        
            for i in require_data[:]: #peshawar, rahim yar khan
                i[0] = i[0].lstrip('0123456789 ')
                if(i[1]=='-'):    
                    i[1] = re.sub('-',"0", i[1])
                i[2] = re.sub(r' \d+$', '', i[2])
                i[2] = re.sub(' -',"", i[2])
                if(i[2]=='-'):
                    i[2] = re.sub('-',"0", i[2])
                i[3] = re.sub(r' \d+$', '', i[3])
                i[3] = re.sub(' -',"", i[3])
                if(i[3]=='-'):
                    i[3] = re.sub('-',"0", i[3])
                i[6] = re.sub(r' \d+$', '', i[6]) #sale
                i[6] = re.sub(' -',"", i[6])
                if(i[6]=='-'):    
                    i[6] = re.sub('-',"0", i[6])
                i[7] = re.sub(r' \d+$', '', i[7]) #return
                i[7] = re.sub(' -',"", i[7])    
                if(i[7]=='-'):    
                    i[7] = re.sub('-',"0", i[7])
        #print(require_data)
        #print(len(require_data))    
        info = filter_data_peshawar(require_data)
        #print(info) 
    product_list = frappe.db.get_all('Item',fields=['item_code', 'item_name','item_type','item_power'], as_list=True);
    
    for x in info:
        for y in product_list:
            Token_Set_Ratio = fuzz.token_set_ratio(x['item'],y[1])
            if Token_Set_Ratio >= 90:
                x['id'] = y[0]

    for z in info:
        key = 'id'
        if key not in z.keys():
            if z:
                for w in product_list:
                    Token_Set_Ratio = fuzz.token_set_ratio(z['item'],w[1])
                    if Token_Set_Ratio >= 80:
                        z['id'] = w[0]    
    
    for a in info:
        key = 'id'
        if key not in a.keys():
            if a:
                for b in product_list:
                    Token_Set_Ratio = fuzz.token_set_ratio(a['item'],b[1]+" "+b[2])
                    if Token_Set_Ratio >= 70:
                        a['id'] = b[0]

    return info;

@frappe.whitelist(allow_guest=True)
def filter_data_bannu(require_data): #for abbotabad,bannu, jhelum,rawalpindi
    filter_data = {}
    final_data = []
    index_arr = [0,1,3,4,5,7,8] #[item,trade price, opening balance, purchase,return, sale,bonus,]
    #get data with specific index
    for x in require_data:
        for i in index_arr:
            if i == 0:
                filter_data['item'] = x[i]
            elif i == 1:
                filter_data['trade_price'] = x[i]
            elif i == 3:
                filter_data['opening_stock'] = x[i]
            elif i == 4:
                filter_data['purchase'] = x[i]
            elif i == 5:
                filter_data['return'] = x[i]
            elif i == 7:
                filter_data['sale'] = x[i]
            elif i == 8:
                filter_data['bonus'] = x[i]
        filter_data_copy = filter_data.copy()
        final_data.append(filter_data_copy)
    #print(final_data)
    #print(len(final_data))    
    return final_data

@frappe.whitelist(allow_guest=True)
def filter_data_islamabad(require_data): #for islamabad,narowal
    filter_data = {}
    final_data = []
    index_arr = [0,1,2,3,4,6,7] #[item,trade price, opening balance, purchase,return, sale,bonus,]
    #get data with specific index
    for x in require_data:
        for i in index_arr:
            if i == 0:
                filter_data['item'] = x[i]
            elif i == 1:
                filter_data['trade_price'] = x[i]
            elif i == 2:
                filter_data['opening_stock'] = x[i]
            elif i == 3:
                filter_data['purchase'] = x[i]
            elif i == 4:
                filter_data['return'] = x[i]
            elif i == 6:
                filter_data['sale'] = x[i]
            elif i == 7:
                filter_data['bonus'] = x[i]
        filter_data_copy = filter_data.copy()
        final_data.append(filter_data_copy)
    #print(final_data)
    #print(len(final_data))    
    return final_data

@frappe.whitelist(allow_guest=True)
def filter_data_peshawar(require_data): #for peshawar, rahim yar khan
    filter_data = {}
    final_data = []
    index_arr = [0,1,2,3,6,7] #[item,trade price, opening balance, purchase,sale, return,]
    #get data with specific index
    for x in require_data:
        for i in index_arr:
            if i == 0:
                filter_data['item'] = x[i]
            elif i == 1:
                filter_data['trade_price'] = x[i]
            elif i == 2:
                filter_data['opening_stock'] = x[i]
            elif i == 3:
                filter_data['purchase'] = x[i]
            elif i == 6:
                filter_data['sale'] = x[i]
            elif i == 7:
                filter_data['return'] = x[i]
        filter_data_copy = filter_data.copy()
        final_data.append(filter_data_copy)
    #print(final_data)
    #print(len(final_data))    
    return final_data    

                