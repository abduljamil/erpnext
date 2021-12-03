# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
from datetime import date
import frappe
from frappe.model.document import Document
import pdfplumber
from frappe.utils import get_site_path
import re
from fuzzywuzzy import fuzz
import pandas as pd

class SaleStockDetail(Document):
    pass

@frappe.whitelist(allow_guest=True)
def parse_pdf(pdf_file,dist_city,from_date,to_date):
    #print(pdf_file,dist_city,from_date,to_date)
    arr = re.split('/',pdf_file);
    path = frappe.get_site_path(arr[1],arr[2],arr[3]);
    #print(path)
    dates_data = frappe.db.get_list('Sale Stock Detail',
        filters={
            'from': from_date,
            'to': to_date
        },
        as_list=True)
    if(dates_data):
        frappe.throw(('Same dates record already exist'))       
    dates_fdata = frappe.db.get_list('Sale Stock Detail',
        filters={
            'from': from_date
        },
        as_list=True)
    dates_tdata = frappe.db.get_list('Sale Stock Detail',
        filters={
            'to': to_date
        },
        as_list=True)        
    if(dates_data ):
        frappe.throw(('Same dates record already exist'))
    elif(dates_fdata):
        frappe.throw(('Same From date record already exist')) 
    elif(dates_tdata):
        frappe.throw(('Same To date record already exist'))
>>>>>>> 3717499cb07afc7c98f737044c5696bc2b0c8d28
    alldata = []
    require_data = []
    if(dist_city == "Abbotabad" or dist_city == "Bannu" or dist_city == "Jhelum" or dist_city == "Rawalpindi"):
        with pdfplumber.open(path) as pdf:
            for x in range(0, len(pdf.pages)):
                page = pdf.pages[x]
                data = page.extract_tables()
                alldata.append(data)
            for i in alldata[:]:
                #print(i)
                for j in i[:]:
                    #print(j)
                    for w in j[:]:
                        arr = list(filter(None, w))
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
        info = filter_data_bannu(require_data)
    elif(dist_city=="Islamabad" or dist_city == "Narowal"):
        with pdfplumber.open(path) as pdf:
            for x in range(0, len(pdf.pages)):
                page = pdf.pages[x]
                data = page.extract_tables()
                alldata.append(data)
            for i in alldata[:]:
                #print(i)
                for j in i[:]:
                    #print(j)
                    for w in j[:]:
                        arr = list(filter(None, w))
                        require_data.append(arr)
            for x in require_data[:]:
                if(len(x)<11):
                    require_data.remove(x)       
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
        info = filter_data_islamabad(require_data)
    elif(dist_city=="Peshawar" or dist_city =="RY Khan"):
        with pdfplumber.open(path) as pdf:
            for x in range(0, len(pdf.pages)):
                page = pdf.pages[x]
                data = page.extract_tables()
                alldata.append(data)
            for i in alldata[:]:
                #print(i)
                for j in i[:]:
                    #print(j)
                    for w in j[:]:
                        arr = list(filter(None, w))
                        require_data.append(arr)
            for x in require_data[:]:
                if(len(x)<11):
                    require_data.remove(x)       
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
        info = filter_data_peshawar(require_data)
    elif(dist_city == "Hyderabad" or dist_city=="Larkana" or dist_city=="Sukkur" or dist_city=="Thatta" or dist_city=="Mirpurkhas"):
        with pdfplumber.open(path) as pdf:
            for x in range(0, len(pdf.pages)):
                page = pdf.pages[x]
                data = page.extract_tables()
                alldata.append(data)
            for i in alldata[:]:
                #print(i)
                for j in i[:]:
                    #print(j)
                    for w in j[:]:
                        if(dist_city =="Larkana"):
                            for x in range(0,len(w)):
                                if(w[x]==''):
                                    w[x]="0"
                        w = list(filter(None, w))
                        require_data.append(w)         
            for x in require_data[:]:
                if(len(x)<13):
                    require_data.remove(x)       
        if(dist_city == "Hyderabad"):     
            info = filter_data_hyderabad(require_data)
        elif(dist_city == "Larkana" or dist_city=="Sukkur" or dist_city=="Thatta"):
            info = filter_data_larkana(require_data)
        elif(dist_city == "Mirpurkhas"):
            info = filter_data_mirpurkhas(require_data)    
    elif(dist_city=="Chakwal" or dist_city=="Kohat" or dist_city=="M.B Din" or dist_city=="Multan" or dist_city == "Sahiwal" or dist_city=="Quetta"): #chakwal,kohat,Mandibahudin,multan,sahiwal
        with pdfplumber.open(path) as pdf:
            for x in range(0, len(pdf.pages)):
                page = pdf.pages[x]
                data = page.extract_tables()
                alldata.append(data)
            for i in alldata[:]:
                #print(i)
                for j in i[:]:
                    #print(j)
                    for w in j[:]:
                        if dist_city == "Chakwal":
                            spl = re.split('  ',w[0])
                            for x in range(1,len(w)):
                                if(w[x]==''):
                                    w[x]="0"
                                spl.append(w[x])                    
                            arr = list(filter(None, spl))
                            require_data.append(arr)
                        elif dist_city == "Kohat":
                            w.pop(0)
                            for x in range(0,len(w)):
                                if(w[x]==''):
                                    w[x]="0"
                            w = list(filter(None, w))
                            require_data.append(w)
                        elif dist_city=="M.B Din":
                            for x in range(0,len(w)):
                                if(w[x]==''):
                                    w[x]="0"
                            require_data.append(w)
                        elif dist_city == "Multan":
                            w = list(filter(None, w))
                            require_data.append(w)
                        elif(dist_city == "Sahiwal" or dist_city == "Quetta"):
                            for x in range(0,len(w)):
                                if(w[x]==''):
                                    w[x]="0"
                            w = list(filter(None, w))        
                            require_data.append(w)                                                        
            for x in require_data[:]:
                if(dist_city=="Chakwal" or dist_city=="Kohat" ):
                    if(len(x)<9):
                        require_data.remove(x)
                elif(dist_city=="M.B Din"):
                    if(x[1]=="Rate" or x[0]=="Total of BLUE" or x[0]=="Total of"):
                        require_data.remove(x)
                elif(dist_city=="Multan"):
                    if(len(x)<9 or x[1]=="T.P."):
                        require_data.remove(x)
                elif(dist_city == "Sahiwal"):
                    if(len(x)<13):
                        require_data.remove(x)
                elif(dist_city == "Quetta"):
                    if(len(x)<11 or x[0]=="Product" or x[0]=="Total" or x[0]=="Grand Total"):
                        require_data.remove(x)                                     
        if(dist_city=="Chakwal"):
            info = filter_data_chakwal(require_data)
        elif(dist_city=="Kohat"):
            info = filter_data_kohat(require_data)
        elif(dist_city=="M.B Din"):
            info = filter_data_mandibahudin(require_data)
        elif(dist_city == "Multan"):
            info = filter_data_multan(require_data)
        elif(dist_city == "Sahiwal"):
            info = filter_data_hyderabad(require_data)
        elif(dist_city == "Quetta"):
            info = filter_data_quetta(require_data)                          
    elif(dist_city=="D.G. Khan" or dist_city=="Okara" or dist_city=="Vehari"): #deraghazi khan
        aligndata = []
        with pdfplumber.open(path) as pdf:
            for x in range(0, len(pdf.pages)):
                page = pdf.pages[x]
                data = page.extract_tables()
                alldata.append(data)
            for i in alldata[:]:
                #print(i)
                for j in i[:]:
                    #print(j)
                    for w in j[:]:
                        data = re.split('\n',w[0])
                        aligndata.append(data)                   
            for x in aligndata:
                for y in x[:]:
                    require_data.append(y)
            for x in range(0,len(require_data)):
                require_data[x] = re.split('\s\s+',require_data[x])
                require_data[x].reverse()
            for x in require_data[:]:
                if(len(x)<14):
                    require_data.remove(x)
                elif(x[0]=='Description'):
                    require_data.remove(x)
        if(dist_city=="Deraghazi"):                                               
            info = filter_data_deraghazi(require_data)
        elif(dist_city=="Okara" or dist_city =="Vehari"):
            info = filter_data_okara(require_data)
    elif(dist_city=="Bahawalnagar" or dist_city=="Bahawalpur"):
        with pdfplumber.open(path) as pdf:
            for x in range(0, len(pdf.pages)):
                data = pdf.pages[x].extract_text()
                data = re.sub("\n",",", data) 
                data = re.sub('Purchase.*',"", data)
                data = re.split(',',data)
                for y in range(0,len(data)):           
                    arr = re.split('\s+',data[y])
                    require_data.append(arr)
            for x in require_data[:]:
                if(len(x)<16):
                    require_data.remove(x)
            for x in range(0,len(require_data)):
                require_data[x].reverse()
                name = require_data[x][-1] +" "+ require_data[x][-2] +" "+ require_data[x][-3]
                require_data[x].append(name)
        info = filter_data_bahawalnagar(require_data)
    elif(dist_city=="Dadu" or dist_city=="Jacobabad" or dist_city=="Lahore" or dist_city=="Gujranwala" or dist_city=="Jhang" or dist_city=="Mardan" or dist_city=="Gujrat"):
        with pdfplumber.open(path) as pdf:
            for x in range(0, len(pdf.pages)):
                data = pdf.pages[x].extract_text()
                data = re.sub("\n",",", data) 
                data = re.split(',',data)
                for y in range(0,len(data)):           
                    arr = re.split('\s+',data[y])
                    arr = list(filter(None, arr))
                    require_data.append(arr)        
            for x in require_data[:]:
                if(dist_city=="Dadu" or dist_city=="Jacobabad" or dist_city=="Gujranwala"):
                    if(len(x)<14 or len(x)>20 or x[0]=="Gr"):
                        require_data.remove(x)
                if(dist_city=="Lahore"):
                    if(len(x)<12 or len(x)>15):
                        require_data.remove(x)
                if(dist_city=="Jhang"):
                    x.pop(0)
                    if(len(x)<14 or len(x)>20):
                        require_data.remove(x)
                if(dist_city=="Mardan"):
                    x.pop(0)
                    if(len(x)<20):
                        require_data.remove(x)
                if(dist_city=="Gujrat"):
                    x.pop(0)
                    if(len(x)<13 or x[1]=="PCW"):
                        require_data.remove(x)                
                            
            if(dist_city=="Jacobabad"):          
                require_data.pop(0)                     
            for x in range(0,len(require_data)):
                require_data[x].reverse()
                name = require_data[x][-1] +" "+ require_data[x][-2] +" "+ require_data[x][-3]
                require_data[x].append(name)
        if(dist_city=="Dadu" or dist_city=="Jacobabad"):
            info = filter_data_dadu(require_data)
        elif(dist_city=="Lahore"):
            info = filter_data_lahore(require_data)
        elif(dist_city=="Gujranwala" or dist_city=="Jhang"):
            info = filter_data_gujranwala(require_data)
        elif(dist_city=="Mardan"):
            info = filter_data_mardan(require_data)
        elif(dist_city=="Gujrat"):
            info = filter_data_gujrat(require_data)    
    elif(dist_city=="Timergrah" ):
        with pdfplumber.open(path) as pdf:
            for x in range(0, len(pdf.pages)):
                data = pdf.pages[x].extract_text()
                data = re.split('\n', data) 
                for y in range(0,len(data)):           
                    arr = re.split('\s+',data[y])
                    arr = list(filter(None, arr))
                    require_data.append(arr)                 
            for x in require_data[:]:
                if(dist_city=="Timergrah"):
                    x.pop(0)
                    if(len(x)<18 or x[0]=='Open' or x[0]=="Description" ):
                        require_data.remove(x) 
            for x in range(0,len(require_data)):
                require_data[x].reverse()
                name = require_data[x][-1] +" "+ require_data[x][-2] +" "+ require_data[x][-3]
                require_data[x].append(name)
        info = filter_data_timergrah(require_data)
    elif(dist_city=="Bhakkar" or dist_city=="Mainwali" or dist_city=="Sargodha"): 
        with pdfplumber.open(path) as pdf:
            for x in range(0, len(pdf.pages)):
                data = pdf.pages[x].extract_text()
                data = re.sub("\n",",", data) 
                data = re.split(',',data)
                for y in range(0,len(data)):           
                    arr = re.split('\s+',data[y])
                    arr = list(filter(None, arr))
                    require_data.append(arr) 
            for x in require_data[:]:
                if(dist_city=="Bhakkar"):
                    for y in range(0,len(x)):  
                        if(x[y]=='-'):
                            x[y]="0"
                    x[0] = re.sub(r'[0-9]',"",x[0])
                    if(len(x)<14 or x[0]=="PR.ID"):
                        require_data.remove(x)
                if(dist_city=="Mainwali" or dist_city=="Sargodha"):
                    if(len(x)<11 or x[0]=="Name"):
                        require_data.remove(x)               
            for x in range(0,len(require_data)):
                require_data[x].reverse()
                name = require_data[x][-1] +" "+ require_data[x][-2]
                require_data[x].append(name)
        if(dist_city=="Bhakkar"):            
            info = filter_data_bhakkar(require_data)
        elif(dist_city=="Mainwali" or dist_city=="Sargodha"):
            info = filter_data_mainwali(require_data)
    elif(dist_city=="Faisalabad" or dist_city=="Toba Tek Singh" or dist_city=="Sialkot" or dist_city=="Kasur"):
        with pdfplumber.open(path) as pdf:
            for x in range(0, len(pdf.pages)):
                data = pdf.pages[x].extract_text()
                data = re.split('\n', data)
                for y in range(0,len(data)):           
                    arr = re.sub('\s+',' ',data[y])
                    arr = re.split('\s',arr)
                    require_data.append(arr)  
            for x in require_data[:]:
                if(dist_city=="Faisalabad"):
                    if(len(x)<18):
                        require_data.remove(x)
                if(dist_city=="Toba Tek Singh"):
                    if(len(x)<12 or len(x)>14):
                        require_data.remove(x)
                if(dist_city=="Sialkot"):
                    if(len(x)<16):
                        require_data.remove(x)
                if(dist_city=="Kasur"):
                    for y in range(0,len(x)):
                        if(x[y]=='-'):
                            x[y]="0"
                    if(len(x)<11 or x[0]=="Product" or x[0]=="Group"):
                        require_data.remove(x)                 
            for x in range(0,len(require_data)):
                require_data[x].reverse()
                name = require_data[x][-1] +" "+ require_data[x][-2] +" "+ require_data[x][-3]
                require_data[x].append(name)   
        if(dist_city=="Faisalabad"):         
            info = filter_data_faisalabad(require_data)
        elif(dist_city=="Toba Tek Singh"):
            info = filter_data_tobateksingh(require_data)
        elif(dist_city=="Sialkot"):
            info = filter_data_sialkot(require_data)
        elif(dist_city=="Kasur"):
            info = filter_data_kasur(require_data)
    elif(dist_city=="Dera Ismail Khan"):
        data = pd.read_excel(path)
        require_data = data.values.tolist()
        for x in require_data[:]:
            x[0] = str(x[0])       
            if(x[0]=='nan' or x[0]=='CODE'):
                require_data.remove(x)
            x.pop(0)            
        info = filter_data_deraismailkhan(require_data)                                                           

    product_list = frappe.db.get_all('Item',fields=['item_code', 'item_name','item_type','item_power','trade_price'], as_list=True);
    
    for x in info:
        for y in product_list:
            Token_Set_Ratio = fuzz.token_set_ratio(x['item'],y[1])
            if Token_Set_Ratio >= 67:
                x['id'] = y[0]
                x['DB_trade_price'] = y[4]

    for z in info:
        key = 'DB_trade_price'
        if key not in z.keys():
            if z:
                for w in product_list:
                    Token_Set_Ratio = fuzz.token_set_ratio(z['item'],w[1])
                    if Token_Set_Ratio >= 60:
                        z['id'] = w[0]
                        z['DB_trade_price'] = w[4]    
    
    for a in info:
        key = 'DB_trade_price'
        if key not in a.keys():
            if a:
                for b in product_list:
                    Token_Set_Ratio = fuzz.token_set_ratio(a['item'],b[1]+" "+b[2])
                    if Token_Set_Ratio >= 59:
                        a['id'] = b[0]
                        a['DB_trade_price'] = b[4]
                        
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
    return final_data    

@frappe.whitelist(allow_guest=True)
def filter_data_hyderabad(require_data): #for hyderabad
    filter_data = {}
    final_data = []
    index_arr = [0,1,2,3,9,11,12] #[item,trade price, opening balance, purchase,bonus,return,sale]
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
            elif i == 9:
                filter_data['return'] = x[i]
            elif i == 11:
                filter_data['sale'] = x[i]
            elif i == 12:
                filter_data['bonus'] = x[i]        
        filter_data_copy = filter_data.copy()
        final_data.append(filter_data_copy)  
    return final_data                

@frappe.whitelist(allow_guest=True)
def filter_data_larkana(require_data): #for larkana,sukkur,Thatta
    filter_data = {}
    final_data = []
    index_arr = [0,1,2,3,10,12,13] #[item,trade price, opening balance, purchase,bonus,return,sale]
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
            elif i == 10:
                filter_data['return'] = x[i]
            elif i == 12:
                filter_data['sale'] = x[i]
            elif i == 13:
                filter_data['bonus'] = x[i]   
        filter_data_copy = filter_data.copy()
        final_data.append(filter_data_copy)    
    return final_data

@frappe.whitelist(allow_guest=True)
def filter_data_chakwal(require_data): #for chakwal
    filter_data = {}
    final_data = []
    index_arr = [0,1,2,4,8,9,10] #[item,trade price, opening balance, purchase,bonus,return,sale]
    #get data with specific index
    for x in require_data:
        for i in index_arr:
            if i == 0:
                filter_data['item'] = x[i]
            elif i == 1:
                filter_data['trade_price'] = x[i]
            elif i == 2:
                filter_data['opening_stock'] = x[i]
            elif i == 4:
                filter_data['purchase'] = x[i]
            elif i == 8:
                filter_data['return'] = x[i]
            elif i == 9:
                filter_data['sale'] = x[i]
            elif i == 10:
                filter_data['bonus'] = x[i]   
        filter_data_copy = filter_data.copy()
        final_data.append(filter_data_copy)    
    return final_data 

@frappe.whitelist(allow_guest=True)
def filter_data_deraghazi(require_data): #for deraghazi
    filter_data = {}
    final_data = []
    index_arr = [-1,12,11,10,8,6] #[item,trade price, opening balance, purchase,sale,bonus]
    #get data with specific index
    for x in require_data:
        for i in index_arr:
            if i == -1:
                filter_data['item'] = x[i]
            elif i == 12:
                filter_data['trade_price'] = x[i]
            elif i == 11:
                filter_data['opening_stock'] = x[i]
            elif i == 10:
                filter_data['purchase'] = x[i]
            elif i == 8:
                filter_data['sale'] = x[i]
            elif i == 6:
                filter_data['bonus'] = x[i]   
        filter_data_copy = filter_data.copy()
        final_data.append(filter_data_copy)    
    return final_data

@frappe.whitelist(allow_guest=True)
def filter_data_kohat(require_data): #for kohat
    filter_data = {}
    final_data = []
    index_arr = [0,1,2,3,4,5] #[item,trade price, opening balance, purchase,sale,bonus]
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
                filter_data['sale'] = x[i]
            elif i == 5:
                filter_data['bonus'] = x[i]   
        filter_data_copy = filter_data.copy()
        final_data.append(filter_data_copy)   
    return final_data

@frappe.whitelist(allow_guest=True)
def filter_data_mandibahudin(require_data): #for Mandibahudin
    filter_data = {}
    final_data = []
    index_arr = [0,1,2,3,5,7] #[item,trade price, opening balance, purchase,sale,bonus]
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
            elif i == 5:
                filter_data['sale'] = x[i]
            elif i == 7:
                filter_data['bonus'] = x[i]   
        filter_data_copy = filter_data.copy()
        final_data.append(filter_data_copy)   
    return final_data

@frappe.whitelist(allow_guest=True)
def filter_data_mirpurkhas(require_data): #for mirpur
    filter_data = {}
    final_data = []
    index_arr = [0,1,2,3,5,9,10] #[item,trade price, opening balance, purchase,return,sale,bonus]
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
            elif i == 5:
                filter_data['return'] = x[i]
            elif i == 9:
                filter_data['sale'] = x[i]
            elif i == 10:
                filter_data['bonus'] = x[i]   
        filter_data_copy = filter_data.copy()
        final_data.append(filter_data_copy)  
    return final_data

@frappe.whitelist(allow_guest=True)
def filter_data_multan(require_data): #for multan
    filter_data = {}
    final_data = []
    index_arr = [0,1,2,3,4,6,7] #[item,trade price, opening balance, purchase,sale,bonus,return]
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
                filter_data['sale'] = x[i]
            elif i == 6:
                filter_data['bonus'] = x[i]
            elif i == 7:
                filter_data['return'] = x[i]       
        filter_data_copy = filter_data.copy()
        final_data.append(filter_data_copy)  
    return final_data

@frappe.whitelist(allow_guest=True)
def filter_data_okara(require_data): #for okara, vehari
    filter_data = {}
    final_data = []
    index_arr = [-1,12,11,10,8,7] #[item,trade price, opening balance, purchase,sale,bonus]
    #get data with specific index
    for x in require_data:
        for i in index_arr:
            if i == -1:
                filter_data['item'] = x[i]
            elif i == 12:
                filter_data['trade_price'] = x[i]
            elif i == 11:
                filter_data['opening_stock'] = x[i]
            elif i == 10:
                filter_data['purchase'] = x[i]
            elif i == 8:
                filter_data['sale'] = x[i]
            elif i == 7:
                filter_data['bonus'] = x[i]   
        filter_data_copy = filter_data.copy()
        final_data.append(filter_data_copy)    
    return final_data

@frappe.whitelist(allow_guest=True)
def filter_data_bahawalnagar(require_data): #for bahawalnagar,bahawalpur
    filter_data = {}
    final_data = []
    index_arr = [-1,2,12,11,10,6,7] #[item, return ,trade price, opening balance, purchase,sale,bonus]
    #get data with specific index
    for x in require_data:
        for i in index_arr:
            if i == -1:
                filter_data['item'] = x[i]
            elif i == 2:
                filter_data['return'] = x[i]   
            elif i == 12:
                filter_data['trade_price'] = x[i]
            elif i == 11:
                filter_data['opening_stock'] = x[i]
            elif i == 10:
                filter_data['purchase'] = x[i]
            elif i == 6:
                filter_data['sale'] = x[i]
            elif i == 7:
                filter_data['bonus'] = x[i]   
        filter_data_copy = filter_data.copy()
        final_data.append(filter_data_copy)    
    return final_data

@frappe.whitelist(allow_guest=True)
def filter_data_dadu(require_data): #for dadu,jacobabad
    filter_data = {}
    final_data = []
    index_arr = [-1,11,10,8,6,5,4] #[item,trade price, opening balance, purchase,return,sale,bonus]
    #get data with specific index
    for x in require_data:
        for i in index_arr:
            if i == -1:
                filter_data['item'] = x[i]   
            elif i == 11:
                filter_data['trade_price'] = x[i]
            elif i == 10:
                filter_data['opening_stock'] = x[i]
            elif i == 8:
                filter_data['purchase'] = x[i]
            elif i == 6:
                filter_data['return'] = x[i]     
            elif i == 5:
                filter_data['sale'] = x[i]
            elif i == 4:
                filter_data['bonus'] = x[i]   
        filter_data_copy = filter_data.copy()
        final_data.append(filter_data_copy)    
    return final_data

@frappe.whitelist(allow_guest=True)
def filter_data_lahore(require_data): #for lahore
    filter_data = {}
    final_data = []
    index_arr = [-1,8,7,6,4,3,1] #[item,trade price, opening balance, purchase,return,sale,bonus]
    #get data with specific index
    for x in require_data:
        for i in index_arr:
            if i == -1:
                filter_data['item'] = x[i]   
            elif i == 8:
                filter_data['trade_price'] = x[i]
            elif i == 7:
                filter_data['opening_stock'] = x[i]
            elif i == 6:
                filter_data['purchase'] = x[i]
            elif i == 4:
                filter_data['return'] = x[i]     
            elif i == 3:
                filter_data['sale'] = x[i]
            elif i == 1:
                filter_data['bonus'] = x[i]   
        filter_data_copy = filter_data.copy()
        final_data.append(filter_data_copy)    
    return final_data

@frappe.whitelist(allow_guest=True)
def filter_data_gujranwala(require_data): #for gujranwala, jhang
    filter_data = {}
    final_data = []
    index_arr = [-1,12,11,9,3,7,5] #[item,trade price, opening balance, purchase,return,sale,bonus]
    #get data with specific index
    for x in require_data:
        for i in index_arr:
            if i == -1:
                filter_data['item'] = x[i]   
            elif i == 12:
                filter_data['trade_price'] = x[i]
            elif i == 11:
                filter_data['opening_stock'] = x[i]
            elif i == 9:
                filter_data['purchase'] = x[i]
            elif i == 3:
                filter_data['return'] = x[i]     
            elif i == 7:
                filter_data['sale'] = x[i]
            elif i == 5:
                filter_data['bonus'] = x[i]   
        filter_data_copy = filter_data.copy()
        final_data.append(filter_data_copy)    
    return final_data

@frappe.whitelist(allow_guest=True)
def filter_data_mardan(require_data): #for mardan
    filter_data = {}
    final_data = []
    index_arr = [-1,18,17,15,9,7,4] #[item,trade price, opening balance, purchase,return,sale,bonus]
    #get data with specific index
    for x in require_data:
        for i in index_arr:
            if i == -1:
                filter_data['item'] = x[i]   
            elif i == 18:
                filter_data['trade_price'] = x[i]
            elif i == 17:
                filter_data['opening_stock'] = x[i]
            elif i == 15:
                filter_data['purchase'] = x[i]
            elif i == 9:
                filter_data['return'] = x[i]     
            elif i == 7:
                filter_data['sale'] = x[i]
            elif i == 4:
                filter_data['bonus'] = x[i]   
        filter_data_copy = filter_data.copy()
        final_data.append(filter_data_copy)    
    return final_data

@frappe.whitelist(allow_guest=True)
def filter_data_timergrah(require_data): #for timergrah
    filter_data = {}
    final_data = []
    index_arr = [-1,15,14,13,8,6,5] #[item,trade price, opening balance, purchase,return,sale,bonus]
    #get data with specific index
    for x in require_data:
        for i in index_arr:
            if i == -1:
                filter_data['item'] = x[i]   
            elif i == 15:
                filter_data['trade_price'] = x[i]
            elif i == 14:
                filter_data['opening_stock'] = x[i]
            elif i == 13:
                filter_data['purchase'] = x[i]
            elif i == 8:
                filter_data['return'] = x[i]    
            elif i == 6:
                filter_data['sale'] = x[i]
            elif i == 5:
                filter_data['bonus'] = x[i]   
        filter_data_copy = filter_data.copy()
        final_data.append(filter_data_copy)    
    return final_data

@frappe.whitelist(allow_guest=True)
def filter_data_bhakkar(require_data): #for timergrah
    filter_data = {}
    final_data = []
    index_arr = [-1,12,11,5,4,3] #[item, opening balance, purchase,return,sale,bonus]
    #get data with specific index
    for x in require_data:
        for i in index_arr:
            if i == -1:
                filter_data['item'] = x[i]   
            elif i == 12:
                filter_data['opening_stock'] = x[i]
            elif i == 11:
                filter_data['purchase'] = x[i]
            elif i == 5:
                filter_data['return'] = x[i]     
            elif i == 4:
                filter_data['sale'] = x[i]
            elif i == 3:
                filter_data['bonus'] = x[i]   
        filter_data_copy = filter_data.copy()
        final_data.append(filter_data_copy)    
    return final_data

@frappe.whitelist(allow_guest=True)
def filter_data_faisalabad(require_data): #for faisalabad
    filter_data = {}
    final_data = []
    index_arr = [-1,15,13,5,4] #[item, opening balance, purchase,return,sale]
    #get data with specific index
    for x in require_data:
        for i in index_arr:
            if i == -1:
                filter_data['item'] = x[i]   
            elif i == 15:
                filter_data['opening_stock'] = x[i]
            elif i == 13:
                filter_data['purchase'] = x[i]
            elif i == 5:
                filter_data['return'] = x[i]     
            elif i == 4:
                filter_data['sale'] = x[i]  
        filter_data_copy = filter_data.copy()
        final_data.append(filter_data_copy)    
    return final_data

@frappe.whitelist(allow_guest=True)
def filter_data_gujrat(require_data): #for gujrat
    filter_data = {}
    final_data = []
    index_arr = [-1,9,8,2,5,4] #[item, opening balance, purchase,return,sale,bonus]
    #get data with specific index
    for x in require_data:
        for i in index_arr:
            if i == -1:
                filter_data['item'] = x[i]   
            elif i == 9:
                filter_data['opening_stock'] = x[i]
            elif i == 8:
                filter_data['purchase'] = x[i]
            elif i == 2:
                filter_data['return'] = x[i]     
            elif i == 5:
                filter_data['sale'] = x[i]
            elif i == 4:
                filter_data['bonus'] = x[i]      
        filter_data_copy = filter_data.copy()
        final_data.append(filter_data_copy)    
    return final_data

@frappe.whitelist(allow_guest=True)
def filter_data_mainwali(require_data): #for mainwali
    filter_data = {}
    final_data = []
    index_arr = [-1,7,6,5,3,2] #[item, opening balance, purchase,return,sale,bonus]
    #get data with specific index
    for x in require_data:
        for i in index_arr:
            if i == -1:
                filter_data['item'] = x[i]   
            elif i == 7:
                filter_data['opening_stock'] = x[i]
            elif i == 6:
                filter_data['purchase'] = x[i]
            elif i == 5:
                filter_data['return'] = x[i]     
            elif i == 3:
                filter_data['sale'] = x[i]
            elif i == 2:
                filter_data['bonus'] = x[i]      
        filter_data_copy = filter_data.copy()
        final_data.append(filter_data_copy)    
    return final_data   

@frappe.whitelist(allow_guest=True)
def filter_data_tobateksingh(require_data): #for Toba Tek singh
    filter_data = {}
    final_data = []
    index_arr = [-1,8,7,3,2,1] #[item, opening balance, purchase,return,sale,bonus]
    #get data with specific index
    for x in require_data:
        for i in index_arr:
            if i == -1:
                filter_data['item'] = x[i]   
            elif i == 8:
                filter_data['opening_stock'] = x[i]
            elif i == 7:
                filter_data['purchase'] = x[i]
            elif i == 3:
                filter_data['return'] = x[i]     
            elif i == 2:
                filter_data['sale'] = x[i]
            elif i == 1:
                filter_data['bonus'] = x[i]      
        filter_data_copy = filter_data.copy()
        final_data.append(filter_data_copy)    
    return final_data

@frappe.whitelist(allow_guest=True)
def filter_data_sialkot(require_data): #for sialkot
    filter_data = {}
    final_data = []
    index_arr = [-1,11,10,5,4,3] #[item, opening balance, purchase,return,sale,bonus]
    #get data with specific index
    for x in require_data:
        for i in index_arr:
            if i == -1:
                filter_data['item'] = x[i]   
            elif i == 11:
                filter_data['opening_stock'] = x[i]
            elif i == 10:
                filter_data['purchase'] = x[i]
            elif i == 5:
                filter_data['return'] = x[i]     
            elif i == 4:
                filter_data['sale'] = x[i]
            elif i == 3:
                filter_data['bonus'] = x[i]      
        filter_data_copy = filter_data.copy()
        final_data.append(filter_data_copy)    
    return final_data

@frappe.whitelist(allow_guest=True)
def filter_data_kasur(require_data): #for kasur
    filter_data = {}
    final_data = []
    index_arr = [-1,7,6,3,4] #[item, opening balance, purchase,return,sale]
    #get data with specific index
    for x in require_data:
        for i in index_arr:
            if i == -1:
                filter_data['item'] = x[i]   
            elif i == 7:
                filter_data['opening_stock'] = x[i]
            elif i == 6:
                filter_data['purchase'] = x[i]
            elif i == 3:
                filter_data['return'] = x[i]     
            elif i == 4:
                filter_data['sale'] = x[i]      
        filter_data_copy = filter_data.copy()
        final_data.append(filter_data_copy)    
    return final_data

@frappe.whitelist(allow_guest=True)
def filter_data_quetta(require_data): #for quetta
    filter_data = {}
    final_data = []
    index_arr = [0,1,2,7,8,9] #[item,opening stock, purchase, return , sale, bonus]
    #get data with specific index
    for x in require_data:
        for i in index_arr:
            if i == 0:
                filter_data['item'] = x[i]
            elif i == 1:
                filter_data['opening_stock'] = x[i]
            elif i == 2:
                filter_data['purchase'] = x[i]
            elif i == 8:
                filter_data['sale'] = x[i]
            elif i == 9:
                filter_data['bonus'] = x[i]
            elif i == 7:
                filter_data['return'] = x[i]       
        filter_data_copy = filter_data.copy()
        final_data.append(filter_data_copy)  
    return final_data

@frappe.whitelist(allow_guest=True)
def filter_data_deraismailkhan(require_data): #for dera ismail khan
    filter_data = {}
    final_data = []
    index_arr = [0,1,2,3,6,7,9] #[item,trade price,opening stock, purchase, sale, bonus, return ]
    #get data with specific index
    for x in require_data:
        for i in index_arr:
            if i == 0:
                filter_data['item'] = x[i]
            elif i==1:
                filter_data['trade_price'] = x[i]   
            elif i == 2:
                filter_data['opening_stock'] = x[i]
            elif i == 3:
                filter_data['purchase'] = x[i]
            elif i == 6:
                filter_data['sale'] = x[i]
            elif i == 7:
                filter_data['bonus'] = x[i]
            elif i == 9:
                filter_data['return'] = x[i]       
        filter_data_copy = filter_data.copy()
        final_data.append(filter_data_copy)  
    return final_data
