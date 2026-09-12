# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt
from dataclasses import fields
from dis import distb
import re
from collections import Counter
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
def parse_pdf(pdf_file, parse_check, parent_detail):
    parent_details = json.loads(parent_detail)
    dist_city = parent_details["city"]
    if not parse_check:
        try:
            doc = frappe.get_last_doc("Brick Wise Sale", filters={"city": dist_city})
            first_date = doc.get("from")
            second_date = parent_details["fromDate"]
            new_record = getdate(second_date)
            if first_date == new_record:
                name = doc.get("name")
                frappe.delete_doc("Brick Wise Sale", name)
        except:
            pass
    tt_list = frappe.db.get_all(
        "Territory", fields=["territory_name", "parent_territory"], as_list=True
    )
    # print(tt_list)
    item_list = frappe.db.get_all(
        "Item",
        fields=["name", "item_name", "trade_price", "item_type", "item_power"],
        as_list=True,
    )
    arr = re.split("/", pdf_file)
    path = frappe.get_site_path(arr[1], arr[2], arr[3])
    green_items = frappe.db.get_all(
        "Item", fields=["name", "belong_to"], filters={"belong_to": "Green"}
    )

    def green_team_bricks(result):
        for k in result:
            for i in green_items:
                if k[0] == i["name"]:
                    k[2] = k[2] + " " + "GT"
        return result

    if dist_city == "Gujrat":
        result = []
        products = [
            "008376",
            "017230",
            "008999",
            "004348",
            "002392",
            "002188",
            "009072",
            "012961",
        ]
        bricks = []
        sales = []
        sales1 = []
        b_condition = True
        p_condition = False
        b_s_index = 36
        b_e_index = 0
        s_s_index = 0

        doc = fitz.open(path)
        page1 = doc[0]
        words = page1.get_text("words")
        # print(words[i][4])
        for i in range(0, len(words)):
            # print(words[i][4])
            if words[i][4] == "Product":
                b_s_index = i + 1
            if "------" in words[i][4] and b_condition == True and i > b_s_index:
                b_e_index = i
                s_s_index = i + 1
                b_condition = False
                p_condition = True

            if "-------" in words[i][4] and p_condition == True and i > b_e_index:
                s_e_index = i
                p_condition = False
                # print(s_s_index)
        for k in range(b_s_index, b_e_index):
            bricks.append(words[k][4])
        # print(bricks)

        for b in range(0, len(bricks)):
            bricks[b] = re.sub("LALAM", "LALAMUSA", bricks[b])
            bricks[b] = re.sub("KHARI", "KHARIAN", bricks[b])
            bricks[b] = re.sub("DINGA", "DINGA GUJRAT", bricks[b])
            bricks[b] = re.sub("FATEP", "FATEH PUR", bricks[b])
            bricks[b] = re.sub("PHALI", "PHALIA GRT", bricks[b])
            bricks[b] = re.sub("KING[+]", "KING ROAD", bricks[b])
            bricks[b] = re.sub("S.ALA", "ALA", bricks[b])
            bricks[b] = re.sub("M.B.D", "MBD GUJRAT", bricks[b])
            bricks[b] = re.sub("MANGO", "MANGOWAL", bricks[b])
            bricks[b] = re.sub("KUNJA", "KUNJAH", bricks[b])
            bricks[b] = re.sub("J.P.J", "JALAL PUR JATTAN", bricks[b])
            bricks[b] = re.sub("PAHRI", "PAHRIANWALI", bricks[b])

        # print(bricks)

        for i in range(s_s_index, s_e_index):
            if words[i][0] > 100:
                # sales1 = []
                sales1.append(words[i][4])
                difference_ = words[i + 1][0] - words[i][0]
                if difference_ > 42.76:
                    num_zeros = int(difference_ / 40)
                    for k in range(1, num_zeros + 1):
                        sales1.insert(i + k, "0")
            else:
                if words[i][0] == 6.75:
                    sales.append(sales1)
                    sales1 = []

        sales = sales[1:-1]
        # print(difference_)
        for i in range(0, len(sales)):
            add_zeros = 14 - len(sales[i])
            # print((sales[i]))
            # print(add_zeros)
            for k in range(0, add_zeros):
                sales[i].append("0")
            # print((sales[i]))

        for p in range(0, len(products)):
            for s in range(0, len(sales[p])):
                child = []
                child.append(products[p])
                child.append(bricks[s])
                child.append(sales[p][s])
                result.append(child)
        # print(len(result))

        for r in result:
            for i in item_list:
                if r[0] == i[0]:
                    r.insert(1, i[1])
                    r.append(i[2])
                    # print(r)
        for r in result:
            for t in tt_list:
                if r[2] == t[0]:
                    r.insert(4, t[1])
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
        if df.iat[1, 0][71:83] == "ABDUL HALEEM":
            Second_sheet_var = True
        # will append line with item name to bricks till TTL QTY
        for i in range(0, len(df)):
            if df.iat[i, 0] == "ITEM":
                start_data_var = i
                for x in range(1, len(df.columns)):
                    if df.iat[i, x] == "TTL QTY":
                        break
                    bricks.append(df.iat[i, x])

            # break main for loop when reach TTL QTY row
            # strip will remove extra empty spaces
            if (df.iat[i, 0]).strip() == "TTL QTY BLUE TEAM":
                break

            if i > start_data_var + 1:
                data = []
                for k in range(0, len(bricks) + 1):
                    data.append(str(df.iat[i, k]))
                    # print(data1)
                products.append(data[0])
                sales.append(data[1:])

        for i in range(0, len(products)):
            if "AFLOXAN CAPS" in products[i]:
                products[i] = "008376"
            if "JETEPAR 10ML INJ" in products[i]:
                products[i] = "008999"
            if "JETEPAR 2ML INJ" in products[i]:
                products[i] = "004348"
            if "JETEPAR SYR" in products[i]:
                products[i] = "002188"
            if "MAIORAD INJ" in products[i]:
                products[i] = "009072"
            if "JETEPAR CAPS" in products[i]:
                products[i] = "002392"
            if "MAIORAD TABLET" in products[i]:
                products[i] = "012961"

        # print(bricks)
        for i in range(0, len(bricks)):
            if bricks[i] == "A.PUR":
                bricks[i] = "ADIL PUR"
            if bricks[i] == "AWAHN":
                bricks[i] = "ALI WAHAN"
            if bricks[i] == "CLKTR" and Second_sheet_var == True:
                bricks[i] = "CLOCK TOWER SKR2"
            if bricks[i] == "CTCOR" and Second_sheet_var == True:
                bricks[i] = "CITY COURT"
            if bricks[i] == "CVSUK" and Second_sheet_var == True:
                bricks[i] = "CIVIL SUKKUR SKR2"
            if bricks[i] == "DHRKI":
                bricks[i] = "DAHARKI"
            if bricks[i] == "GHTKI":
                bricks[i] = "GHOTKI"
            if bricks[i] == "GRIBA":
                bricks[i] = "GARIBABAD"
            if bricks[i] == "K.KOT" and Second_sheet_var == True:
                bricks[i] = "KANDH KOT"
            if bricks[i] == "KNDRA":
                bricks[i] = "KANDHRA"
            if bricks[i] == "KPMHR":
                bricks[i] = "KHANPUR MEHAR"
            if bricks[i] == "MPM":
                bricks[i] = "MIRPUR MATHELO"
            if bricks[i] == "OLDSK":
                bricks[i] = "OLD SUKKUR"
            if bricks[i] == "PAQIL":
                bricks[i] = "PANO AKIL"
            if bricks[i] == "ROHRI" and Second_sheet_var == True:
                bricks[i] = "ROHRI"
            if bricks[i] == "S.PAT" and Second_sheet_var == True:
                bricks[i] = "SALEH PAT"
            if bricks[i] == "SHLMR" and Second_sheet_var == True:
                bricks[i] = "SHALIMAR ROAD SKR2"
            if bricks[i] == "SRHAD" and Second_sheet_var == True:
                bricks[i] = "SARHAD"
            if bricks[i] == "SUKTW" and Second_sheet_var == True:
                bricks[i] = "SUKKUR TOWNSHIP SKR2"
            if bricks[i] == "SUKUR" and Second_sheet_var == True:
                bricks[i] = "SUKKUR SKR2"
            if bricks[i] == "UBARO" and Second_sheet_var == True:
                bricks[i] = "UBARO"
            if bricks[i] == "WORK" and Second_sheet_var == True:
                bricks[i] = "WORK SHOP ROAD SKR2"
            if bricks[i] == "WSALE" and Second_sheet_var == True:
                bricks[i] = "WHOLE SALE SUKKUR SKR2"
            if bricks[i] == "AYUBG" and Second_sheet_var == True:
                bricks[i] = "AYUB GAT SUKKUR"
            if bricks[i] == "SBMND":
                bricks[i] = "SABZI MANDI"

            if bricks[i] == "ABDU" and Second_sheet_var == False:
                bricks[i] = "ABDU"
            if bricks[i] == "AIRPT" and Second_sheet_var == False:
                bricks[i] = "AIR PORT ROAD"
            if bricks[i] == "BGRJI" and Second_sheet_var == False:
                bricks[i] = "BAGARJI"
            if bricks[i] == "BORDO" and Second_sheet_var == False:
                bricks[i] = "BOARD OFFICE"
            if bricks[i] == "BRROD" and Second_sheet_var == False:
                bricks[i] = "BARRAGE ROAD"
            if bricks[i] == "BUNDR" and Second_sheet_var == False:
                bricks[i] = "BUNDER ROAD"
            if bricks[i] == "CHAK" and Second_sheet_var == False:
                bricks[i] = "CHAK"
            if bricks[i] == "CHDKO" and Second_sheet_var == False:
                bricks[i] = "CHUNDKO"
            if bricks[i] == "CLKTR" and Second_sheet_var == False:
                bricks[i] = "CLOCK TOWER SKR1"
            if bricks[i] == "CVSUK" and Second_sheet_var == False:
                bricks[i] = "CIVIL SUKKUR SKR1"
            if bricks[i] == "EIDGH" and Second_sheet_var == False:
                bricks[i] = "EID GAH ROAD"
            if bricks[i] == "GAM B" and Second_sheet_var == False:
                bricks[i] = "GAMBAT SIDE B"
            if bricks[i] == "GARYA" and Second_sheet_var == False:
                bricks[i] = "GARYA"
            if bricks[i] == "GMBAT" and Second_sheet_var == False:
                bricks[i] = "GAMBAT"
            if bricks[i] == "HLANI" and Second_sheet_var == False:
                bricks[i] = "HALANI"
            if bricks[i] == "HNGOR" and Second_sheet_var == False:
                bricks[i] = "HINGORJA"
            if bricks[i] == "JCD" and Second_sheet_var == False:
                bricks[i] = "JACOBABAD SUKKUR"
            if bricks[i] == "JHANI" and Second_sheet_var == False:
                bricks[i] = "JAHAN KHAN"
            if bricks[i] == "JINAH" and Second_sheet_var == False:
                bricks[i] = "JINNAH CHOWK"
            if bricks[i] == "K.BNG" and Second_sheet_var == False:
                bricks[i] = "KOT BANGLOW"
            if bricks[i] == "KHAI" and Second_sheet_var == False:
                bricks[i] = "KHAI SUKKUR"
            if bricks[i] == "KHORA" and Second_sheet_var == False:
                bricks[i] = "KHORA"
            if bricks[i] == "KHP" and Second_sheet_var == False:
                bricks[i] = "KHAIRPUR"
            if bricks[i] == "KHPCV" and Second_sheet_var == False:
                bricks[i] = "KHAIR PUR CIVIL"
            if bricks[i] == "KNDYA" and Second_sheet_var == False:
                bricks[i] = "KANDYARD"
            if bricks[i] == "KPS" and Second_sheet_var == False:
                bricks[i] = "KHANPUR"
            if bricks[i] == "KUMB" and Second_sheet_var == False:
                bricks[i] = "KUMB"
            if bricks[i] == "LAKHI" and Second_sheet_var == False:
                bricks[i] = "LAKKHI"
            if bricks[i] == "LQMAN" and Second_sheet_var == False:
                bricks[i] = "LUQMAN"
            if bricks[i] == "MHPUR" and Second_sheet_var == False:
                bricks[i] = "MEHRAB PUR"
            if bricks[i] == "MIANI" and Second_sheet_var == False:
                bricks[i] = "MIANI ROAD"
            if bricks[i] == "MLTRY" and Second_sheet_var == False:
                bricks[i] = "MILITARY ROAD"
            if bricks[i] == "MOCHI" and Second_sheet_var == False:
                bricks[i] = "MOCHI BAZAR"
            if bricks[i] == "NEEMK" and Second_sheet_var == False:
                bricks[i] = "NEEM KI CHARI"
            if bricks[i] == "NGOTH" and Second_sheet_var == False:
                bricks[i] = "NEW GOTH SUKKUR"
            if bricks[i] == "NPIND" and Second_sheet_var == False:
                bricks[i] = "NEW PIND SUKKUR"
            if bricks[i] == "PJGOT" and Second_sheet_var == False:
                bricks[i] = "PIR JO GOTH"
            if bricks[i] == "PRYAL" and Second_sheet_var == False:
                bricks[i] = "PIRYALO"
            if bricks[i] == "R.PUR" and Second_sheet_var == False:
                bricks[i] = "RANIPUR"
            if bricks[i] == "S.GAS" and Second_sheet_var == False:
                bricks[i] = "SUI GAS"
            if bricks[i] == "SDERO" and Second_sheet_var == False:
                bricks[i] = "SOBHO DERO"
            if bricks[i] == "SHP" and Second_sheet_var == False:
                bricks[i] = "SHIKARPUR"
            if bricks[i] == "SHP B" and Second_sheet_var == False:
                bricks[i] = "SHIKARPUR SIDE B"
            if bricks[i] == "STRJA" and Second_sheet_var == False:
                bricks[i] = "SETHARJA"
            if bricks[i] == "SUK" and Second_sheet_var == False:
                bricks[i] = "SUK"
            if bricks[i] == "SUKTW" and Second_sheet_var == False:
                bricks[i] = "SUKKUR TOWNSHIP SKR1"
            if bricks[i] == "SUKUR" and Second_sheet_var == False:
                bricks[i] = "SUKKUR SKR1"
            if bricks[i] == "THERI" and Second_sheet_var == False:
                bricks[i] = "THERI"
            if bricks[i] == "TMW" and Second_sheet_var == False:
                bricks[i] = "THARI MIRWAH"
            if bricks[i] == "WORK" and Second_sheet_var == False:
                bricks[i] = "WORK SHOP ROAD SKR1"
            if bricks[i] == "WSALE" and Second_sheet_var == False:
                bricks[i] = "WHOLE SALE SUKKUR SKR1"
            if bricks[i] == "STDUM" and Second_sheet_var == False:
                bricks[i] = "STADIUM ROAD"
            if bricks[i] == "SKBYP" and Second_sheet_var == False:
                bricks[i] = "SUKKUR BY PASS"
            if bricks[i] == "S.PAT":
                bricks[i] = "SALEH PAT"
        # print(bricks)
        # print(len(bricks))
        for i in range(len(sales)):
            for k in range(len(sales[i])):
                if sales[i][k] == "nan":
                    sales[i][k] = "0"

        for p in range(0, len(products)):
            for s in range(0, len(sales[p])):
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
                    r.insert(1, i[1])
                    r.append(i[2])
                    # print(r)
        for r in result:
            # print(r)
            for t in tt_list:
                if r[2] == t[0]:
                    r.insert(4, t[1])
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
        for i in range(0, len(df)):
            if df.iat[i, 0] == "AREA":
                start_data_var = i
                for x in range(1, len(df.columns)):
                    if df.iat[i, x] == "TTL QTY":
                        break
                    products.append(df.iat[i, x])

            if (df.iat[i, 0]) == "TTL QTY":
                break

            if i > start_data_var + 1:
                data = []
                for k in range(0, len(products) + 1):
                    data.append(str(df.iat[i, k]))
                    # print(data)
                bricks.append(data[0])
                sales.append(data[1:])

        for i in range(0, len(products)):
            if products[i] == "A-CAP":
                products[i] = "008376"
            if products[i] == "A-TAB":
                products[i] = "017230"
            if products[i] == "J_10C":
                products[i] = "008999"
            if products[i] == "J_2CC":
                products[i] = "004348"
            if products[i] == "J_CAP":
                products[i] = "002392"
            if products[i] == "J_SYP":
                products[i] = "002188"
            if products[i] == "M_INJ":
                products[i] = "009072"
            if products[i] == "M_TAB":
                products[i] = "012961"
        for i in range(0, len(bricks)):
            if bricks[i] == "CHOTI GHITTI":
                bricks[i] = "CHOTI GHITI"
            if bricks[i] == "COUNTER SALE":
                bricks[i] = "COUNTER SALE HYD"
            if bricks[i] == "ISLAMABAD":
                bricks[i] = "ISLAMABAD HYD"
            if bricks[i] == "KARIO GHANWER":
                bricks[i] = "KARIO"
            if bricks[i] == "KHANOOT":
                bricks[i] = "KHANOT"
            if bricks[i] == "KALIMORI":
                bricks[i] = "KALI MORI"
            if bricks[i] == "L.M.C.H":
                bricks[i] = "LMCH"
            if bricks[i] == "LAJPAT RAOD":
                bricks[i] = "LAJPAT ROAD"
            if bricks[i] == "LATIFABAD NO.10":
                bricks[i] = "LATIFABAD 10"
            if bricks[i] == "LATIFABAD NO.11" or bricks[i] == "LATFABAD NO,11":
                bricks[i] = "LATIFABAD 11"
            if bricks[i] == "LATIFABAD NO.6":
                bricks[i] = "LATIFABAD 6"
            if bricks[i] == "LATIFABAD NO.4" or bricks[i] == "LATIFABAD NO .4":
                bricks[i] = "LATIFABAD 4"
            if bricks[i] == "LATIFABAD NO.7":
                bricks[i] = "LATIFABAD 7"
            if bricks[i] == "LATIFABAD NO.8":
                bricks[i] = "LATIFABAD 8"
            if bricks[i] == "LATIFABAD NO.5":
                bricks[i] = "LATIFABAD 5"
            if bricks[i] == "LATIFABAD NO.2":
                bricks[i] = "LATIFABAD 2"
            if bricks[i] == "LATIFABAD NO.12":
                bricks[i] = "LATIFABAD 12"
            if bricks[i] == "LIAQUAT COLONY":
                bricks[i] = "LIAQAT COLONY"
            if bricks[i] == "PHULEELI":
                bricks[i] = "PHULELI"
            if bricks[i] == "SADDAR":
                bricks[i] = "SADDER HYD2"
            if bricks[i] == "SARFARZ COLONY":
                bricks[i] = "SARFRAZ COLONY"
            if bricks[i] == "SHAHDAD PURE":
                bricks[i] = "SHAHDADPUR"
            if bricks[i] == "SHAHDILARGE":
                bricks[i] = "SHADI LARGE"
            if bricks[i] == "STATION ROAD":
                bricks[i] = "STATION ROAD HYD"
            if bricks[i] == "USMAN SHAH URI":
                bricks[i] = "USMAN SHAH HURI"
            if bricks[i] == "TALHAAR":
                bricks[i] = "TALHAR"
            if bricks[i] == "USMANSHAH":
                bricks[i] = "USMAN SHAH HURI"
            if bricks[i] == "TANDO BAAGO":
                bricks[i] = "TANDO BAGO"
            if bricks[i] == "TANDO MOHD. KHAN":
                bricks[i] = "TANDO MUHAMMAD KHAN"
            if bricks[i] == "KADHAN":
                bricks[i] = "KADAN"
            if bricks[i] == "LATIFABAD NO 8":
                bricks[i] = "LATIFABAD 8"
            if bricks[i] == "LATIFABAD NO 8":
                bricks[i] = "LATIFABAD 8"
            if bricks[i] == " AUTO BHAN ROAD":
                bricks[i] = "AUTO BAHN ROAD"
            if bricks[i] == "RUKKAN BURIRA":
                bricks[i] = "RUKAN BURIRA"
            if bricks[i] == "JAMSHORRO":
                bricks[i] = "JAMSHORO"

        for i in range(len(sales)):
            for k in range(len(sales[i])):
                if sales[i][k] == "nan":
                    sales[i][k] = "0"
        for s in range(0, len(sales)):
            for i in range(0, len(sales[s])):
                child = []
                child.append(products[i])
                child.append(bricks[s])
                child.append(sales[s][i])
                result.append(child)
        for r in range(0, len(result)):
            for i in item_list:
                if result[r][0] == i[0]:
                    if result[r][2] != "0":
                        new_result.append(result[r])
                    # print(r)
        for r in new_result:
            for i in item_list:
                if r[0] == i[0]:
                    r.insert(1, i[1])
                    r.append(i[2])
        for r in new_result:
            for t in tt_list:
                if r[2] == t[0]:
                    r.insert(4, t[1])
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
        for i in range(0, len(df)):
            if df.iat[i, 0] == "ITEM":
                start_data_var = i
                for x in range(1, len(df.columns)):
                    if df.iat[i, x] == "TTL QTY":
                        break
                    bricks.append(df.iat[i, x])
            if (df.iat[i, 0]).strip() == "TTL QTY PCW TEAM-BLUE":
                break

            if i > start_data_var + 1:
                data = []
                for k in range(0, len(bricks) + 1):
                    data.append(str(df.iat[i, k]))
                products.append(data[0])
                sales.append(data[1:])
        for i in range(0, len(products)):
            if "AFLOXON 150 CAP 20,S" in products[i]:
                products[i] = "008376"
            if "AFLOXON 300MG TAB 30,S" in products[i]:
                products[i] = "017230"
            if "JETEPAR 10ML INJ 5,S" in products[i]:
                products[i] = "008999"
            if "JETEPAR 2ML AMPULES 10,S" in products[i]:
                products[i] = "004348"
            if "JETEPAR CAP" in products[i]:
                products[i] = "002392"
            if "JETEPAR SYP" or "JETEPAR SYR" in products[i]:
                products[i] = "002188"
            if "MAIORAD INJ 3ML 6,S" in products[i]:
                products[i] = "009072"
            if "MAIORAD TAB 30,S" in products[i]:
                products[i] = "012961"
            if "JETEPAR SYRUP 112ML (TP: 244.22)" in products[i]:
                products[i] = "002188"

        for i in range(0, len(bricks)):
            if bricks[i] == "BAGHN":
                bricks[i] = "BAGHAN THT"
            if bricks[i] == "BUHUR":
                bricks[i] = "BUHURO"
            if bricks[i] == "CHAJN":
                bricks[i] = "CHACH JAHAN"
            if bricks[i] == "DABHE":
                bricks[i] = "DHABEEJI"
            if bricks[i] == "JHARK":
                bricks[i] = "JHIRK SIDE"
            if bricks[i] == "JHIMP":
                bricks[i] = "JHAMPIR"
            if bricks[i] == "SUJAW":
                bricks[i] = "SUJAWAL"
            if bricks[i] == "THT":
                bricks[i] = "THATTA THT"
            if bricks[i] == "C.CND":
                bricks[i] = "CHATO CHAND"
            if bricks[i] == "CHOUH":
                bricks[i] = "CHOUHAR JAMALI"
            if bricks[i] == "GAGAR":
                bricks[i] = "GHAGHAR"
            if bricks[i] == "GHULM":
                bricks[i] = "GHULLAMULLAH"
            if bricks[i] == "KHORW":
                bricks[i] = "KHORWA"
            if bricks[i] == "NORAD":
                bricks[i] = "NOORIABAD"
            if bricks[i] == "S.KRM":
                bricks[i] = "SHAH KARIM"
            if bricks[i] == "BATHO":
                bricks[i] = "BATHORO"
            if bricks[i] == "GOHRA":
                bricks[i] = "GHORA BARI"
            if bricks[i] == "GULMD":
                bricks[i] = "GULMANDA"
            if bricks[i] == "J,CHK":
                bricks[i] = "JATI CHOWK"
            if bricks[i] == "JUNGS":
                bricks[i] = "JUNGSHAI"
            if bricks[i] == "N.B":
                bricks[i] = "NOOHBHATI"
            if bricks[i] == "P,T":
                bricks[i] = "PATHAN COLONY"
            if bricks[i] == "GULMANDA":
                bricks[i] = "GUL MANDA"
            if bricks[i] == "DABHEEJI":
                bricks[i] = "DHABEEJI"

        for i in range(len(sales)):
            for k in range(len(sales[i])):
                if sales[i][k] == "nan":
                    sales[i][k] = "0"
        for p in range(0, len(products)):
            for s in range(0, len(sales[p])):
                child = []
                child.append(products[p])
                child.append(bricks[s])
                child.append(sales[p][s])
                result.append(child)
        for r in result:
            for i in item_list:
                if r[0] == i[0]:
                    r.insert(1, i[1])
                    r.append(i[2])
        for r in result:
            for t in tt_list:
                if r[2] == t[0]:
                    r.insert(4, t[1])
        result = green_team_bricks(result)
        return result
    elif dist_city == "Mir Pur Khas":
        bricks = []
        data = []
        result = []
        sales = []
        products = []
        start_data_var = 1000
        Second_sheet_var = False
        df = pd.read_excel(path)
        for i in range(0, len(df)):
            if df.iat[i, 0] == "AREA":
                start_data_var = i
                for x in range(1, len(df.columns)):
                    if df.iat[i, x] == "TOTAL":
                        break
                    products.append(df.iat[i, x])
            if (df.iat[i, 0]) == "TOTAL":
                break

            if i > start_data_var:
                data = []
                for k in range(0, len(products) + 1):
                    data.append(str(df.iat[i, k]))
                bricks.append(data[0])
                sales.append(data[1:])

        for b in range(0, len(bricks)):
            if bricks[b] == "HIRABAD":
                bricks[b] = "HEERABAD"
            if bricks[b] == "CHHORE ":
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
            if bricks[b] == "CHHACHRO":
                bricks[b] = "CHACHRO"
            if bricks[b] == "DIPLO ":
                bricks[b] = "DIPLO"
            if bricks[b] == "ISLAMKOT ":
                bricks[b] = "ISLAMKOT"
            if bricks[b] == "JHILORI":
                bricks[b] = "JHULURI"

        # print(bricks)

        for i in range(0, len(products)):
            if products[i] == "JT10C":
                products[i] = "008999"
            if products[i] == "JT2CC":
                products[i] = "004348"
            if products[i] == "JTCAP":
                products[i] = "002392"
            if products[i] == "JTSYP":
                products[i] = "002188"
            if products[i] == "MDINJ":
                products[i] = "009072"
            if products[i] == "MRDTB":
                products[i] = "012961"

        for s in range(0, len(sales)):
            for i in range(0, len(sales[s])):
                child = []
                child.append(products[i])
                child.append(bricks[s])
                child.append(sales[s][i])
                result.append(child)

        for r in result:
            for i in item_list:
                if r[0] == i[0]:
                    r.insert(1, i[1])
                    r.append(i[2])
        for r in result:
            for t in tt_list:
                if r[2] == t[0]:
                    r.insert(4, t[1])
        result = green_team_bricks(result)
        return result
    elif dist_city == "Nawab Shah":
        products = []
        bricks = []
        sales = []
        result = []
        df = pd.read_excel(path, header=None)

        # ---- 1. header row dhoondein jahan col 0 == "ITEM" ho ----
        header_row_idx = None
        for i in range(len(df)):
            if str(df.iat[i, 0]).strip().upper() == "ITEM":
                header_row_idx = i
                break

        if header_row_idx is None:
            print("DEBUG: 'ITEM' header row nahi mila")
            # return []

        header_row = df.iloc[header_row_idx]

        # ---- 2. "TTL QTY" column dhoondein ----
        ttl_qty_col = None
        for c in range(2, len(header_row)):
            if str(header_row[c]).strip().upper() == "TTL QTY":
                ttl_qty_col = c
                break
        if ttl_qty_col is None:
            ttl_qty_col = len(header_row) - 2

        brick_cols = list(range(2, ttl_qty_col))

        # ---- 3. bricks list banayein aur normalize karein ----
        bricks = [str(header_row[c]).strip().upper() for c in brick_cols]
        for b in range(0, len(bricks)):
            if bricks[b] == "KANDIARO":
                bricks[b] = "KANDIARO"
            if bricks[b] == "N.FEROZ":
                bricks[b] = "NAUSHAHRO FEROZ"
            if bricks[b] == "PHULL":
                bricks[b] = "PHULL"
            if bricks[b] == "T.SHAH":
                bricks[b] = "T SHAH"
            if bricks[b] == "B.CITY":
                bricks[b] = "BHIRIA CITY"
            if bricks[b] == "B.ROAD":
                bricks[b] = "BHIRIA ROAD"
            if bricks[b] == "P.CHANG":
                bricks[b] = "PACCA CHANG"
            if bricks[b] == "AKRI":
                bricks[b] = "AKRI"
            if bricks[b] == "KARONDI":
                bricks[b] = "KARONDI"
            if bricks[b] == "MORO":
                bricks[b] = "MORO"
            if bricks[b] == "D.PUR":
                bricks[b] = "DAULAT PUR"
            if bricks[b] == "NAWABSHAH":
                bricks[b] = "NAWABSHAH NWS"
            if bricks[b] == "THARUSHAH":
                bricks[b] = "THARU SHAH"

        # print("DEBUG: bricks =", bricks)

        # ---- 4. products + sales nikalein ----
        for i in range(header_row_idx + 1, len(df)):
            raw_name = str(df.iat[i, 0]).strip()

            if raw_name.upper().startswith("G TTL"):
                break

            if "(TP:" not in raw_name.upper():
                continue

            product_name = raw_name.split("(TP:")[0].strip()
            products.append(product_name)

            row_sales = []
            for col in brick_cols:
                val = df.iat[i, col]
                if pd.isna(val):
                    row_sales.append("0")
                else:
                    row_sales.append(str(val))
            sales.append(row_sales)

        # print("DEBUG: products =", products)
        # print("DEBUG: sales =", sales)

        # ---- 5. empty ko "0" bana dein (safety) ----
        for i in sales:
            for a in range(0, len(i)):
                if i[a] == "":
                    i[a] = "0"

        # ---- 6. products x bricks nested loop, zero sale skip ----
        for p in range(0, len(products)):
            for b in range(0, len(bricks)):
                if sales[p][b] == "0":
                    continue
                child = []
                child.append(products[p])
                child.append(bricks[b])
                child.append(sales[p][b])
                result.append(child)

        print(
            "DEBUG: result BEFORE matching (total rows =",
            len(result),
            ") sample:",
            result[:5],
        )

        # ---- 7. product name replacement (readable names ke liye) ----
        for r in result:
            if r[0] == "JETEPAR 10ML AMP. 5 AMP":
                r[0] = "Jetepar Injection 10ml"
            if r[0] == "JETEPAR 2ML AMP. 10 AMP":
                r[0] = "Jetepar Injection 2ml"
            if r[0] == "JETEPAR CAP. 10S":
                r[0] = "Jetepar Capsule"
            if r[0] == "JETEPAR SYP. 112ML":
                r[0] = "Jetepar Syrup"
            if r[0] == "MAIORAD 100MG TAB 30S":
                r[0] = "Maiorad Tablet"
            if r[0] == "MAIORAD 3ML AMPS 6S":
                r[0] = "Maiorad Injection"

            # ---- fuzzy match: pehle exact (100), agar na mile to best available match ----
            best_ratio = 0
            best_code = None
            for i in item_list:
                final_result = fuzz.token_set_ratio(r[0], i[1])
                if final_result > best_ratio:
                    best_ratio = final_result
                    best_code = i[0]
            if best_ratio >= 100:
                r[0] = best_code
            else:
                print(
                    f"DEBUG: NO EXACT MATCH for '{r[0]}' -> best guess was '{best_code}' with ratio {best_ratio}"
                )

        # print("DEBUG: result AFTER matching sample:", result[:5])

        # ---- 8. item_list se naam/rate insert ----
        for r in result:
            for i in item_list:
                if r[0] == i[0]:
                    r.insert(1, i[1])
                    r.append(i[2])

        # print("DEBUG: result AFTER item_list insert sample:", result[:5])

        # ---- 9. tt_list se extra field insert ----
        for r in result:
            for t in tt_list:
                if r[2] == t[0]:
                    r.insert(4, t[1])

        # print("DEBUG: result FINAL (total rows =", len(result), ") sample:", result[:5])

        # result = green_team_bricks(result)
        # print("DEBUG: result AFTER green_team_bricks (total rows =", len(result), ")")

        # return result
        result = green_team_bricks(result)
        return result
        # print(result)

    else:
        with pdfplumber.open(path) as pdf:
            if dist_city == "Lahore":
                # This report software changed at some point. The OLD format
                # is a pipe ("|") delimited pseudo-table. The NEW format
                # ("4M Technologies" invoice-style report) has no "|" at all
                # -- that's exactly why the old code crashed on it
                # (`y.split("|")` returns a 1-item list, then the two
                # `.pop()` calls empty it out and the second one raises
                # "IndexError: pop from empty list"). Detect which one this
                # PDF is and route to the matching parser.
                first_page_text = pdf.pages[0].extract_text() or ""

                if "|" in first_page_text:
                    # ================= OLD FORMAT (unchanged) =================
                    full_array = []
                    for x in range(0, len(pdf.pages)):
                        data = pdf.pages[x].extract_text()
                        data = re.sub("\n", ",", data)
                        data = data.split(",")
                        for y in data:
                            aplha1 = "PRODUCT NAME"
                            aplha2 = "AFLOXAN"
                            aplha3 = "JETEPAR"
                            aplha4 = "MAIORAD"
                            aplha5 = "MILID"
                            if (
                                aplha1 in y
                                or aplha2 in y
                                or aplha3 in y
                                or aplha4 in y
                                or aplha5 in y
                            ):
                                array = y.split("|")
                                array.pop()
                                array.pop(0)
                                without_empty_string = []
                                for string in array:
                                    if string != "          ":  ## 10 spaces in pdf
                                        without_empty_string.append(string)
                                    else:
                                        string = "0"
                                        without_empty_string.append(string)
                                if len(without_empty_string) > 1:
                                    full_array.append(without_empty_string)
                    for a in full_array:
                        a[0] = re.sub(r"\s\s+", " ", a[0])
                    for t in full_array:
                        if t[0] == " PRODUCT NAME PACK ":
                            for i in range(len(t)):
                                t[i] = t[i].strip()

                    for b in full_array:
                        if b[0] == "PRODUCT NAME PACK":
                            for c in range(len(b)):
                                for t in tt_list:
                                    if b[c] == "C.M.H":
                                        b[c] = "COMBINED MILITARY HOSPITAL"
                                    elif b[c] == "L.G.H":
                                        b[c] = "LAHORE GENERAL HOSPITAL"
                                    elif b[c] in t[0]:
                                        b[c] = t[0]
                                    elif b[c] == "S.Z.HOSPIT":
                                        b[c] = "SHEIKH ZAID HOSPITAL"
                                    elif b[c] == "G.T ROAD M":
                                        b[c] = "GT ROAD MANAWA"
                                    elif b[c] == "R.A.BAZAR":
                                        b[c] = "R A BAZAR"
                                    elif b[c] == "AL-FAISAL":
                                        b[c] = "AL FAISAL TOWN"
                                    elif b[c] == "GULSHAN-E-":
                                        b[c] = "GULSHAN E RAVI"
                                    elif b[c] == "BAIGAM KOT":
                                        b[c] = "BAIGUM KOT"
                                    elif b[c] == "SANDA":
                                        b[c] = "SANDA LAHORE"
                                    elif b[c] == "SHAHNOOR":
                                        b[c] = "SHAH NOOR"
                                    elif b[c] == "SHADMAN":
                                        b[c] = "SHAD MAN"
                                    elif b[c] == "SAMANABAD":
                                        b[c] = "SAMANA BAD"
                                    elif b[c] == "SAMANAABD":
                                        b[c] = "SAMANA ABAD"
                                    elif b[c] == "BAIGAM KOT":
                                        b[c] = "BAIGUM KOT"
                                    elif b[c] == "TEZAB AAHATA":
                                        b[c] = "TEHZAB AAHATA"
                                    elif b[c] == "JALLO PIND":
                                        b[c] = "JALLO PARK"
                                    elif b[c] == "TEZAB AAHA":
                                        b[c] = "TEHZAB AAHATA"
                                    elif b[c] == "THOKAR NIA":
                                        b[c] = "THOKAR NAIZ BAIG"
                                    elif b[c] == "BAIGAM KOT":
                                        b[c] = "BAIGUM KOT"
                                    elif b[c] == "BUND ROAD":
                                        b[c] = "BAND ROAD"
                                    elif b[c] == "AL-FAISAL TOWN":
                                        b[c] = "AL FAISAL TOWN"
                                    elif b[c] == "G.T ROAD MANAWA":
                                        b[c] = "GT ROAD MANAWA"
                                    elif b[c] == "GARHI SHAHU":
                                        b[c] = "GARHI SHAHU BAZAR"
                                    elif b[c] == "GULSHAN-E-RAVI":
                                        b[c] = "GULSHAN E RAVI"
                                    elif b[c] == "L.G.H":
                                        b[c] = "LAHORE GENERAL HOSPITAL"
                                    elif b[c] == "R.A.BAZAR":
                                        b[c] = "R A BAZAR"
                                    elif b[c] == "SABZAZAR":
                                        b[c] = "SABZADAR ROAD"
                                    elif b[c] == "SAMANAABD":
                                        b[c] = "SAMANA ABAD"
                                    elif b[c] == "SANDA":
                                        b[c] = "SANDA LAHORE"
                                    elif b[c] == "SHADMAN":
                                        b[c] = "SHAD MAN"
                                    elif b[c] == "SHAHNOOR":
                                        b[c] = "SHAH NOOR"
                                    elif b[c] == "THOKAR NIAZ BAIG":
                                        b[c] = "THOKAR NAIZ BAIG"
                                    elif b[c] == "SHAHDARA TOWN":
                                        b[c] = "SHAHDRA TOWN"
                                    elif b[c] == "SHAHDARA G.T ROAD":
                                        b[c] = "SHAHDARA G.T ROAD"
                                    elif b[c] == "TAJ BAGH LHR.":
                                        b[c] = "TAJ BAGH LHR"
                                    elif b[c] == "SHEIKHUPURA":
                                        b[c] = "SHEIKHUPURA LHR"
                                    elif b[c] == "KOT ABDUL MALIK GT":
                                        print("Hello")
                                        b[c] = "KOT ABDUL MALIK LHR1 GT"

                    item_code = [
                        "008376",
                        "017230",
                        "002392",
                        "002188",
                        "004348",
                        "008999",
                        "012961",
                        "009072",
                    ]
                    for c in full_array:
                        if c[0] == "AFLOXAN Cap 2X10S ":
                            c[0] = item_code[0]
                        if c[0] == "AFLOXAN Tab 300MG 3X10S ":
                            c[0] = item_code[1]
                        if c[0] == "JETEPAR Cap. 20s ":
                            c[0] = item_code[2]
                        if c[0] == "JETEPAR syp.112ml 112ML ":
                            c[0] = item_code[3]
                        if c[0] == "JETEPAR Inj.2ml 10s ":
                            c[0] = item_code[4]
                        if c[0] == "JETEPAR INJ.10ml 5s ":
                            c[0] = item_code[5]
                        if c[0] == "MAIORAD TAB. 30S ":
                            c[0] = item_code[6]
                        if c[0] == "MAIORAD INJ.3ML 6S ":
                            c[0] = item_code[7]
                    filter_array = full_array
                    for f in filter_array:
                        for i in range(len(f)):
                            if type(f[i]) == str:
                                f[i] = f[i].strip()
                                f[i] = re.sub("\s+(0)", "", f[i])
                    for a in range(0, len(filter_array)):
                        if (
                            filter_array[a][0] == "PRODUCT NAME PACK"
                            and filter_array[a][len(filter_array[a]) - 1] == "TOTAL"
                        ):
                            for i in range(0, 11):
                                filter_array[a + i].pop()
                    final_array = []
                    for c in filter_array:
                        arr = c[1 : len(c)]
                        if c[0] == "MILID TAB.400MG 30S":
                            pass
                        elif c[0] == "MILID TAB.200MG 30S":
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
                                result.append([index, name, number])

                    for element in result:
                        for e in range(0, len(element)):
                            for t in tt_list:
                                if element[e] == t[0]:
                                    element.append(t[1])
                    for i in item_list:
                        for b in result:
                            for a in range(0, len(b)):
                                if i[0] == b[a]:
                                    b.insert(a + 1, i[1])
                                    b.append(i[2])
                    result = green_team_bricks(result)
                    return result

                else:
                    # ================= NEW FORMAT (4M Technologies invoice) =================
                    # Layout: "<region_code> - <region name> <val1> <val2> <val3>
                    # <val4> <total_qty>" then, on the next line, the Amount
                    # value -- and sometimes the region name wraps onto that
                    # next line too (e.g. "ALLAMA IQBAL" / "TOWN"). We read
                    # words by their x/y position instead of relying on "|"
                    # since this report has no table delimiters at all.
                    # Column order is fixed: JETEPAR Cap, syp, Inj.2ml, INJ.10ml.
                    PRODUCT_CODES = ["002392", "002188", "004348", "008999"]
                    NAME_X0_CUTOFF = 105  # anything left of this is region-name text

                    def cluster_rows(words, tol=2.0):
                        words = sorted(words, key=lambda w: w["top"])
                        rows, cur, cur_top = [], [], None
                        for w in words:
                            if cur_top is None or abs(w["top"] - cur_top) <= tol:
                                cur.append(w)
                                cur_top = w["top"] if cur_top is None else cur_top
                            else:
                                rows.append(cur)
                                cur, cur_top = [w], w["top"]
                        if cur:
                            rows.append(cur)
                        for r in rows:
                            r.sort(key=lambda w: w["x0"])
                        return rows

                    result = []
                    for page in pdf.pages:
                        rows = cluster_rows(page.extract_words())
                        i = 0
                        while i < len(rows):
                            row = rows[i]
                            texts = [w["text"] for w in row]
                            if not re.match(r"^\d{7}$", texts[0]):
                                i += 1
                                continue

                            name_words, value_words = [], []
                            for w in row[2:]:  # skip region code + "-"
                                if w["x0"] < NAME_X0_CUTOFF:
                                    name_words.append(w["text"])
                                else:
                                    value_words.append(w["text"])

                            # region name can wrap to the next visual row,
                            # which also carries the Amount value -- pull any
                            # left-hand-side leftover words from it, then
                            # consume that row so it isn't scanned again
                            if i + 1 < len(rows):
                                next_row = rows[i + 1]
                                next_texts = [w["text"] for w in next_row]
                                if not re.match(r"^\d{7}$", next_texts[0]):
                                    for w in next_row:
                                        if w["x0"] < NAME_X0_CUTOFF:
                                            name_words.append(w["text"])
                                    i += 1

                            region_name = " ".join(name_words)
                            if len(value_words) >= 4:
                                for code, val in zip(PRODUCT_CODES, value_words[:4]):
                                    qty = "0" if val == "-" else val.replace(",", "")
                                    result.append([code, region_name, qty])
                            i += 1

                    for r in result:
                        for i in item_list:
                            if r[0] == i[0]:
                                r.insert(1, i[1])
                                r.append(i[2])
                    for r in result:
                        for t in tt_list:
                            if r[2] == t[0]:
                                r.insert(4, t[1])
                    result = green_team_bricks(result)
                    return result
            elif dist_city == "Sheikhupura":
                products = []
                sales = []
                result = []
                for x in range(0, len(pdf.pages)):
                    data = pdf.pages[x].extract_table()
                    if type(data) != type(None) and data[x][0] == "Product Name":
                        for i in range(2, len(data) - 2):
                            products.append(data[i][0])
                        bricks = data[0][2:]
                        for p in range(0, len(products)):
                            sales.append(data[2 + p][2:])

                for s in sales:
                    for i in range(0, len(s)):
                        if s[i] == "":
                            s[i] = "0"
                db_bricks = [
                    "SHEIKHU PURA",
                    "FAROOQA ABAD",
                    "KHANQAH DOGRAN",
                    "SUKHE KE",
                    "PINDI BHATTIAN",
                    "SAFDARA ABAD",
                    "MANA WALA",
                    "WARBUR TON",
                    "NANKANA SAHIB",
                    "BUCHEKI",
                    "MORE KHUNDA",
                    "FAIZA BAD",
                    "SHARAK PUR",
                    "BEGUM KOT",
                    "MURIDKEE",
                    "NARANG MANDI",
                    "JANDIALA SHER KHAN",
                ]
                bricks = db_bricks
                for i in range(0, len(products)):
                    for j in range(0, len(bricks)):
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
                        if r[0] == "MAIROAD INJ":
                            r[0] = "009072"
                        if r[0] == "MAIROAD TAB":
                            r[0] = "012961"
                        if r[0] == "AVOR TAB 2MG":
                            r[0] = "007853"
                        if r[0] == "METRONIDAZOLE 200MG":
                            r[0] = "008909"
                        if r[0] == "METRONIDAZOLE TAB 400MG":
                            r[0] = "081274"
                        if r[0] == "OBEXIL TAB 20MG":
                            r[0] = "032259"
                        if r[0] == "PC-LAC SUP 120ML":
                            r[0] = "019133"
                        if r[0] == "AFLOXAN CAP":
                            r[0] = "008376"
                        if r[0] == "CYRIN INJ":
                            r[0] = "005425"

                        percent = fuzz.token_set_ratio(r[0], i[1])
                        if percent >= 80:
                            r[0] = i[0]
                for r in result:
                    for i in item_list:
                        percent = fuzz.token_set_ratio(r[0], i[1])
                        if percent >= 72:
                            r[0] = i[0]
                # name and price
                for r in result:
                    for i in item_list:
                        if r[0] == i[0]:
                            r.insert(1, i[1])
                            r.append(i[2])
                # for brick parent
                for r in result:
                    for t in tt_list:
                        if r[2] == t[0]:
                            r.insert(4, t[1])  ## insert brick parent into index 4
                result = green_team_bricks(result)
                return result
            elif dist_city == "Kasur":
                products = []
                sales = []
                bricks = []
                for x in range(0, len(pdf.pages)):
                    data = pdf.pages[x].extract_table()
                    # print("1",data[0][-1])
                    if data[0][-1] != "Total":
                        child_brick = data[0][2:]
                        bricks.append(child_brick)
                        for i in range(1, len(data) - 2):  ## for skipping total row
                            products.append(data[i][1])
                            sales.append(data[i][2:])
                    else:
                        child_brick = data[0][2:-1]
                        bricks.append(child_brick)
                        for j in range(1, len(data) - 2):
                            products.append(data[j][1])
                            sales.append(data[j][2:-1])
                for b in bricks:
                    for c in range(0, len(b)):
                        if b[c] == "BPH":
                            b[c] = "BHAI PHERU"
                        if b[c] == "CHM":
                            b[c] = "CHANGA MANGA"
                        if b[c] == "CHN":
                            b[c] = "CHUNIAN"
                        if b[c] == "HBA":
                            b[c] = "HABIB ABAD"
                        if b[c] == "KAH":
                            b[c] = "KAH NA"
                        if b[c] == "KHD":
                            b[c] = "KHUDIAN KHAS"
                        if b[c] == "KNP":
                            b[c] = "KANGAN PUR"
                        if b[c] == "KRK":
                            b[c] = "KOT RADHA KISHAN"
                        if b[c] == "KS2":
                            b[c] = "KASUR 2"
                        if b[c] == "KSR":
                            b[c] = "KASUR 1"
                        if b[c] == "MGM":
                            b[c] = "MANGA MANDI"
                        if b[c] == "MTA":
                            b[c] = "MUSTAFA ABAD"
                        if b[c] == "MUW":
                            b[c] = "MANDI USMAN WALA"
                        if b[c] == "PTK":
                            b[c] = "PATTO KI"
                        if b[c] == "RWD":
                            b[c] = "RAI WIND"
                        if b[c] == "THM":
                            b[c] = "THENG MORE"  # print(bricks)
                        if b[c] == "KS3":
                            b[c] = "KASUR 3"  # print(bricks)
                ## set sale value only
                for s in sales:
                    for i in range(0, len(s)):
                        index = s[i].index("\n")
                        s[i] = s[i][:index]
                        if s[i] == "-":
                            s[i] = "0"
                result = []
                zipped_list = []
                for s in sales:
                    for b in bricks:
                        if len(b) == len(s):
                            zipped_values = zip(b, s)
                            zipped_list.append(list(zipped_values))
                for z in range(0, len(zipped_list)):
                    for l in range(0, len(zipped_list[z])):
                        zipped_list[z][l] = list(zipped_list[z][l])
                        zipped_list[z][l].insert(0, products[z])
                        zipped_list[z][l] = tuple(zipped_list[z][l])
                # print(zipped_list)
                final_list = [item for z in zipped_list for item in z]
                # print(final_list)
                ## make array a/c  data model
                end_result = []
                for r in final_list:
                    for i in item_list:
                        if r[0] == "MAIORAD 3ML INJ":
                            r = list(r)
                            r[0] = "009072"
                            r = tuple(r)
                            end_result.append(r)
                        if r[0] == "MAIORAD TAB":
                            r = list(r)
                            r[0] = "012961"
                            r = tuple(r)
                            end_result.append(r)
                        percent = fuzz.token_set_ratio(r[0], i[1])
                        if percent >= 80:
                            r = list(r)
                            # print(r[0],i[1])
                            r[0] = i[0]
                            r = tuple(r)
                            # print(r)
                            end_result.append(r)
                # # name and price
                for r in range(0, len(end_result)):
                    for i in item_list:
                        if end_result[r][0] == i[0]:
                            end_result[r] = list(end_result[r])
                            end_result[r].insert(1, i[1])
                            end_result[r].append(i[2])
                # print(end_result)
                # # for brick parent
                for r in range(0, len(end_result)):
                    for t in tt_list:
                        if end_result[r][2] == t[0]:
                            end_result[r].insert(
                                4, t[1]
                            )  ## insert brick parent into index 4
                end_result = green_team_bricks(end_result)
                return end_result
            elif dist_city == "Okara":
                products = []
                bricks = []
                sales = []
                result = []
                for x in range(0, len(pdf.pages)):
                    data = pdf.pages[x].extract_table()
                    # print(data)
                    for p in range(1, len(data) - 2):
                        products.append(data[p][1])
                        for q in range(0, len(products)):
                            if "{" in products[q]:
                                index = products[q].index("{")
                                products[q] = products[q][:index]
                            products[q] = products[q].strip()
                    for s in range(1, len(data) - 2):
                        sale = data[s][2:-1]
                        sales.append(sale)
                    # print(sales)        bricks = data[0][2:-1]
                new_bricks = [
                    "AKHTER ABAD",
                    "BANGLA GOGERA",
                    "BASIR PUR",
                    "DEPAL PUR",
                    "DEPAL PUR CHOWK",
                    "DHA 1",
                    "DHA 2",
                    "FAISLA ABAD ROAD",
                    "CANTT",
                    "HABIB ABAD",
                    "HAVELI LAKHA",
                    "HOSPITAL BAZAR",
                    "HUJRA CITY",
                    "JABOKA",
                    "MANDI AHMED ABAD",
                    "RAJO WAL",
                    "RENALA KHURD CITY",
                    "SAHIWAL ROAD",
                    "SIRKI",
                ]
                bricks = new_bricks
                bricks = data[0][2:-1]
                for b in range(0, len(bricks)):
                    if "D\nA\nO\nR\nR \nA\nB\nK\nA" in bricks[b]:
                        bricks[b] = "AKBAR ROAD"
                    if "D \nA\nB\nA\nR \nE\nT\nH\nK\nA" in bricks[b]:
                        bricks[b] = "AKHTER ABAD"
                    if "D\nA\nB\nA\nR \nE\nT\nH\nK\nA" in bricks[b]:
                        bricks[b] = "AKHTER ABAD"
                    if "R\nU\nP\nR \nSI\nA\nB" in bricks[b]:
                        bricks[b] = "BASIR PUR"
                    if "GP\n4U\n+M\nCHUCHAKD+BAMA+ALKA" in bricks[b]:
                        bricks[b] = "CHUCHAK"
                    if "R \nU\nP\nL \nA\nP\nE\nD" in bricks[b]:
                        bricks[b] = "DEPAL PUR"
                    if "R \nEPAL PUCHOWK\nD" in bricks[b]:
                        bricks[b] = "DEPAL PUR CHOWK"
                    if "2\nQ \nH\nD" in bricks[b]:
                        bricks[b] = "DHQ 2"
                    if "D \nA\nSAL ABROAD\nAI\nF" in bricks[b]:
                        bricks[b] = "FAISLA ABAD ROAD"
                    if "N\nA\nC\n+\nBERTT\nM\nA\nG" in bricks[b]:
                        bricks[b] = "CANTT"
                    if "U\nO\nERA+YG PUR\nGN\nO\nG" in bricks[b]:
                        bricks[b] = "GOGERA"
                    if "D\nA\nB\nA\nB \nBI\nA\nH" in bricks[b]:
                        bricks[b] = "HABIB ABAD"
                    if "A\nH\nK\nA\nL\nLI \nE\nV\nA\nH" in bricks[b]:
                        bricks[b] = "HAVELI LAKHA"
                    if "L \nPITAZAR\nSA\nOB\nH" in bricks[b]:
                        bricks[b] = "HOSPITAL BAZAR"
                    if "Y\nT\nCI\nA \nR\nUJ\nH" in bricks[b]:
                        bricks[b] = "HUJRA CITY"
                    if "A\nK\nO\nB\nA\nJ" in bricks[b]:
                        bricks[b] = "JABOKA"
                    if "LALA ZAR COLONY" in bricks[b]:
                        bricks[b] = "LALA ZAR COLONY"
                    if "D \nE\nM\nHD\nAA\nDI AB\nN\nA\nM" in bricks[b]:
                        bricks[b] = "MANDI AHMED ABAD"
                    if "A\nL\nO\nOL KH\nNT+\nA\nL\nP" in bricks[b]:
                        bricks[b] = "KOHLA"
                    if "L\nA\nW\nO \nAJ\nR" in bricks[b]:
                        bricks[b] = "RAJO WAL"
                    if "Y\nRENALA HURD CIT\nK" in bricks[b]:
                        bricks[b] = "RENALA KHURD CITY"
                    if "L \nWAAD\nAHIRO\nS" in bricks[b]:
                        bricks[b] = "SAHIWAL ROAD"
                    if "H\nD\nR\nA\nG\nR \nAI\nH\nS" in bricks[b]:
                        bricks[b] = "SHER GARH"
                    if "D D\nAA\nSIRKI MOH+SMPURA RO" in bricks[b]:
                        bricks[b] = "SIRKI"
                    if "LA RA\nGE\nNG\nAO\nBG" in bricks[b]:
                        bricks[b] = "BANGLA GOGERA"
                    if "1\nQ \nH\nD" in bricks[b]:
                        bricks[b] = "DHQ 1"
                    if "JABOKA+NOL PLOT+KOHLA+MUPLAKA+BAM" in bricks[b]:
                        bricks[b] = "JABOKA"
                    if "D\nA\nO\nR\nT \nG" in bricks[b]:
                        bricks[b] = "GT ROAD"

                for p in range(0, len(products)):
                    name = products[p]
                    if name.startswith("AFLOXAN CAP"):
                        products[p] = "008376"
                    elif name.startswith("AFLOXAN TAB"):
                        products[p] = "017230"
                    elif name.startswith("JETEPAR 10ml Amp"):
                        products[p] = "008999"
                    elif name.startswith("JETEPAR 2ml Amp"):
                        products[p] = "004348"
                    elif name.startswith("JETEPAR CAP"):
                        products[p] = "002392"
                    elif name.startswith("JETEPAR SYP"):
                        products[p] = "002188"
                    elif name.startswith("MAIORAD AMP"):
                        products[p] = "009072"
                    elif name.startswith("MAIORAD TAB"):
                        products[p] = "012961"

                for p in range(0, len(products)):
                    for b in range(0, len(bricks)):
                        child = []
                        child.append(products[p])
                        child.append(bricks[b])
                        child.append(sales[p][b])
                        result.append(child)

                for r in result:
                    for i in item_list:
                        if r[0] == i[0]:
                            r.insert(1, i[1])
                            r.append(i[2])
                for r in result:
                    for t in tt_list:
                        if r[2] == t[0]:
                            r.insert(4, t[1])
                result = green_team_bricks(result)
                return result
            elif dist_city == "Karachi":
                result = []
                for x in range(0, len(pdf.pages)):
                    products = []
                    bricks = []
                    sales = []
                    new_result = []
                    data = pdf.pages[x].extract_table()
                    # print(data)
                    product = data[0][1:]
                    products.append(product)
                    # print(products)
                    for i in range(2, len(data)):  ## for skipping total row
                        bricks.append(data[i][0])
                        # print(bricks)
                        sale = data[i][1:]
                        sales.append(sale)
                        # print(sales)
                    for p in range(0, len(products)):
                        products[p] = list(
                            filter(None, products[p])
                        )  ##remove none value
                    bricks = list(filter(None, bricks))
                    for s in range(0, len(sales)):
                        sales[s] = [
                            "0" if x == "" else x for x in sales[s]
                        ]  ## change '' with '0'

                    only_sale = [
                        sales[s]
                        for s in range(0, len(sales))
                        if "\n" not in sales[s][0]
                    ]
                    ## remove the total of territory wise
                    for p in products:
                        for s in range(0, len(only_sale)):
                            if len(only_sale[s]) - len(p) == 1:
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
                        if "ANKELASRIA HOSPITAL" in bricks[b]:
                            bricks[b] = "ANKLESARIA HOSPITAL"
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
                    for b in range(0, len(bricks)):
                        for s in range(0, len(only_sale[b])):
                            child = []
                            child.append(products[0][s])
                            child.append(bricks[b])
                            # print(bricks[b])
                            child.append(only_sale[b][s])
                            result.append(child)
                for r in range(
                    len(result)
                ):  # this script add the two sales in each box(e.g 5+6)
                    if "+" in result[r][2]:
                        temp_sale = result[r][2]
                        temp_sale = temp_sale.split("+")
                        temp_sale = int(temp_sale[0]) + int(temp_sale[1])
                        temp_sale = str(temp_sale)
                        result[r][2] = temp_sale
                for r in range(0, len(result)):
                    for i in item_list:
                        if result[r][0] == i[0]:
                            if result[r][2] != "0":
                                new_result.append(result[r])
                for r in new_result:
                    for i in item_list:
                        if r[0] == i[0]:
                            r.insert(1, i[1])
                            r.append(i[2])
                            # print(r)

                for r in new_result:
                    for t in tt_list:
                        if r[2] == t[0]:
                            r.insert(4, t[1])
                            # print(r)
                new_result = green_team_bricks(new_result)
                return new_result
            elif dist_city == "Sahiwal":
                products = []
                bricks = []
                sales = []
                result = []
                for x in range(0, len(pdf.pages)):
                    data = pdf.pages[x].extract_table()
                    bricks = data[0][1:-2]
                    for b in range(0, len(bricks)):
                        if bricks[b] == "SWLCN":
                            bricks[b] = "SAHIWAL CENTER"
                        if bricks[b] == "DHQ":
                            bricks[b] = "DISTRICT HEAD QUARTER HOSPITAL"
                        if bricks[b] == "PAKPN":
                            bricks[b] = "PAK PATTAN"
                        if bricks[b] == "ARIFW":
                            bricks[b] = "ARIFWALA"
                        if bricks[b] == "IQNGR":
                            bricks[b] = "IQBAL NAGAR"
                        if bricks[b] == "KASWL":
                            bricks[b] = "KASSOWAL"
                        if bricks[b] == "QBLA":
                            bricks[b] = "QABOOLA"
                        if bricks[b] == "CCI":
                            bricks[b] = "CHICHAWATNI"
                        if bricks[b] == "GHABD":
                            bricks[b] = "GHAZIA ABAD"
                        if bricks[b] == "HARPA":
                            bricks[b] = "HARAPPA"

                    for p in range(2, len(data) - 4):
                        products.append(data[p][0])
                        sales.append(data[p][1:-2])

                    for i in sales:
                        for a in range(0, len(i)):
                            if i[a] == "":
                                i[a] = "0"

                    for p in range(0, len(products)):
                        for b in range(0, len(bricks)):
                            if sales[p][b] == "0":
                                continue
                            child = []
                            child.append(products[p])
                            child.append(bricks[b])
                            child.append(sales[p][b])
                            result.append(child)

                    # for jetepar syrup and 2ml inj
                    for r in result:
                        if r[0] == "JETEPAR 2ML INJ 10S":
                            r[0] = "Jetepar Injection 2ml"
                        if r[0] == "AFLOXAN 300MG TAB 30S":
                            r[0] = "Afloxan Tablet"
                        if r[0] == "AFLOXAN CAP 20'S":
                            r[0] = "Afloxan Capsule"
                        if r[0] == "JETEPAR 10ML INJ 5S":
                            r[0] = "Jetepar Injection 10ml"
                        if r[0] == "JETEPAR CAP 20S":
                            r[0] = "Jetepar Capsule"
                        if r[0] == "JETEPAR SYRUP 112ML":
                            r[0] = "Jetepar Syrup"
                        if r[0] == "MAIORAD 3ML INJ 6S":
                            r[0] = "Maiorad Injection"
                        if r[0] == "MAIORAD TAB 30S":
                            r[0] = "Maiorad Tablet"
                        for i in item_list:
                            final_result = fuzz.token_set_ratio(r[0], i[1])
                            if final_result >= 100:
                                r[0] = i[0]

                    for r in result:
                        for i in item_list:
                            if r[0] == i[0]:
                                r.insert(1, i[1])
                                r.append(i[2])

                    for r in result:
                        for t in tt_list:
                            if r[2] == t[0]:
                                r.insert(4, t[1])

                    result = green_team_bricks(result)
                    return result
            elif dist_city == "Sialkot":
                bricks = []
                sales = []
                result = []
                products = []
                new_result = []
                for x in range(0, len(pdf.pages)):
                    data = pdf.pages[x].extract_table()
                    products = data[0][2:-1]

                    for p in range(0, len(products)):
                        if "046001" in products[p]:
                            products[p] = "008999"
                        if "046002" in products[p]:
                            products[p] = "004348"
                        if "046003" in products[p]:
                            products[p] = "002188"
                        if "046004" in products[p]:
                            products[p] = "002392"
                        if "046005" in products[p]:
                            products[p] = "009072"
                        if "046006" in products[p]:
                            products[p] = "012961"
                        # if '' in products[p]:
                        #     product[p] = ''

                    if x == len(pdf.pages) - 1:
                        for b in range(1, len(data) - 3):
                            bricks.append(data[b][1])

                        for s in range(1, len(data) - 3):
                            sales.append(data[s][2:-1])
                    else:
                        for b in range(1, len(data)):
                            bricks.append(data[b][1])
                        for s in range(1, len(data)):
                            sales.append(data[s][2:-1])
                # print(sales)
                for s in sales:
                    for i in range(0, len(s)):
                        if s[i] == "-":
                            s[i] = "0"
                            # print(s[i])
                # print(sales)

                for b in range(0, len(bricks)):
                    if "1010101" in bricks[b]:
                        bricks[b] = "COMMISSIONER ROAD"
                    if "1010105" in bricks[b]:
                        bricks[b] = "MURRAY COLLEGE ROAD"
                    if "1010203" in bricks[b]:
                        bricks[b] = "DEFENCE ROAD SIALKOT"
                    if "1010204" in bricks[b]:
                        bricks[b] = "SHAHAB PURA"
                    if "1010208" in bricks[b]:
                        bricks[b] = "RODAS ROAD"
                    if "1010219" in bricks[b]:
                        bricks[b] = "SARDAR BEGUM CHOWK"
                    if "1010220" in bricks[b]:
                        bricks[b] = "ALAM CHOWK SHAHAB PURA ROAD"
                    if "1010301" in bricks[b]:
                        bricks[b] = "ABBOTT ROAD"
                    if "1010302" in bricks[b]:
                        bricks[b] = "PARIS ROAD"
                    if "1010304" in bricks[b]:
                        bricks[b] = "GREEN WOOD STREET"
                    if "1010305" in bricks[b]:
                        bricks[b] = "RAILWAY ROAD SIALKOT"
                    if "1020104" in bricks[b]:
                        bricks[b] = "PASRUR ROAD 2"
                    if "1010322" in bricks[b]:
                        bricks[b] = "KHADIM ALI ROAD"
                    if "1010402" in bricks[b]:
                        bricks[b] = "PULL AIK"
                    if "1010403" in bricks[b]:
                        bricks[b] = "PASRUR ROAD SIALKOT"
                    if "1010404" in bricks[b]:
                        bricks[b] = "ZAFARWAL ROAD"
                    if "1010406" in bricks[b]:
                        bricks[b] = "AIMNA ABAD ROAD"
                    if "1010416" in bricks[b]:
                        bricks[b] = "ISLAMABAD MOHALLA"
                    if "1010601" in bricks[b]:
                        bricks[b] = "GOHAD PUR / MURAD PUR ROAD"
                    if "1010603" in bricks[b]:
                        bricks[b] = "KASHMIR ROAD SIALKOT"
                    if "1010605" in bricks[b]:
                        bricks[b] = "CHRISTIAN TOWN / HUNTER PURA"
                    if "1010701" in bricks[b]:
                        bricks[b] = "SADAR BAZAR CANTT SIALKOT"
                    if "1010702" in bricks[b]:
                        bricks[b] = "JINNAH ISLAMIA COLLEGE ROAD"
                    if "1010801" in bricks[b]:
                        bricks[b] = "KOTLI LOHARAN EAST"
                    if "1010803" in bricks[b]:
                        bricks[b] = "DHALLE WALI"
                    if "1010805" in bricks[b]:
                        bricks[b] = "KULLU WAL"
                    if "1010806" in bricks[b]:
                        bricks[b] = "KAPUROWALI"
                    if "1010810" in bricks[b]:
                        bricks[b] = "KOTLI LOHARAN WEST"
                    if "1010901" in bricks[b]:
                        bricks[b] = "PULI TOP KHANA"
                    if "1010902" in bricks[b]:
                        bricks[b] = "BHARTH"
                    if "1010904" in bricks[b]:
                        bricks[b] = "MARAKI WAL"
                    if "1010905" in bricks[b]:
                        bricks[b] = "KHAROTA SYEDAN"
                    if "1010906" in bricks[b]:
                        bricks[b] = "SHADIWAL"
                    if "1011001" in bricks[b]:
                        bricks[b] = "DALUWALI"
                    if "1011002" in bricks[b]:
                        bricks[b] = "JHAI"
                    if "1011003" in bricks[b]:
                        bricks[b] = "JUNG MORE"
                    if "1011006" in bricks[b]:
                        bricks[b] = "SAID PUR"
                    if "1011007" in bricks[b]:
                        bricks[b] = "GONDAL"
                    if "1011009" in bricks[b]:
                        bricks[b] = "BAJ WAT"
                    if "1011101" in bricks[b]:
                        bricks[b] = "DUBURJI MALIAN"
                    if "1011103" in bricks[b]:
                        bricks[b] = "MIANI ADDA"
                    if "1011104" in bricks[b]:
                        bricks[b] = "GHOYAN KI"
                    if "1011105" in bricks[b]:
                        bricks[b] = "ADDA KAMAL PUR"
                    if "1011106" in bricks[b]:
                        bricks[b] = "BHALLOWALI SIALKOT"
                    if "1011205" in bricks[b]:
                        bricks[b] = "HAJI PURA"
                    if "1011206" in bricks[b]:
                        bricks[b] = "RANGPURA"
                    if "1011207" in bricks[b]:
                        bricks[b] = "CIRCULAR ROAD SIALKOT"
                    if "1011208" in bricks[b]:
                        bricks[b] = "IMAM SAB"
                    if "1020103" in bricks[b]:
                        bricks[b] = "NISBAT ROAD"
                    if "1020105" in bricks[b]:
                        bricks[b] = "PULL NAHAR"
                    if "1020106" in bricks[b]:
                        bricks[b] = "DASKA SIAL KOT"
                    if "1020107" in bricks[b]:
                        bricks[b] = "SOHAWA STOP"
                    if "1020108" in bricks[b]:
                        bricks[b] = "CIVIL HOSPITAL ROAD SIALKOT"
                    if "1020202" in bricks[b]:
                        bricks[b] = "CHUNGI # 8"
                    if "1020203" in bricks[b]:
                        bricks[b] = "COLLEGE ROAD SIAL KOT"
                    if "1020207" in bricks[b]:
                        bricks[b] = "SAMBRIAL ROAD"
                    if "1020301" in bricks[b]:
                        bricks[b] = "MOTRA"
                    if "1020302" in bricks[b]:
                        bricks[b] = "ADAMKAY"
                    if "1020303" in bricks[b]:
                        bricks[b] = "JAMKE CHEEMA"
                    if "1020305" in bricks[b]:
                        bricks[b] = "BHOPAL WALA VILLAGE"
                    if "1020402" in bricks[b]:
                        bricks[b] = "MUNDEKE GORAYA"
                    if "1020403" in bricks[b]:
                        bricks[b] = "KOTLI BAWA"
                    if "1030701" in bricks[b]:
                        bricks[b] = "MODEL TOWN UGOKI"
                    if "1030702" in bricks[b]:
                        bricks[b] = "MAIN BAZAR UGOKI"
                    if "1030705" in bricks[b]:
                        bricks[b] = "SHAHAB PURA CHOWK"
                    if "1030706" in bricks[b]:
                        bricks[b] = "SUBLIME CHOWK"
                    if "1030707" in bricks[b]:
                        bricks[b] = "FATEH GARH SIALKOT"
                    if "1030708" in bricks[b]:
                        bricks[b] = "ADALAT GARH"
                    if "1031001" in bricks[b]:
                        bricks[b] = "SAMBRIAL MORE"
                    if "1031004" in bricks[b]:
                        bricks[b] = "LARI ADDA SIALKOT"
                    if "1031005" in bricks[b]:
                        bricks[b] = "JETHI KAY ROAD"
                    if "1031006" in bricks[b]:
                        bricks[b] = "BAIGO WALA SIALKOT"
                    if "1040902" in bricks[b]:
                        bricks[b] = "MURIDKE ROAD"
                    if "1040905" in bricks[b]:
                        bricks[b] = "QILA AHMED ABAD"
                    if "1040907" in bricks[b]:
                        bricks[b] = "DHAMTHAL SIALKOT"
                    if "1050801" in bricks[b]:
                        bricks[b] = "GALI ABSHAR WALI CHWND"
                    if "1050804" in bricks[b]:
                        bricks[b] = "MAIN ROAD CHWND"
                    if "1050901" in bricks[b]:
                        bricks[b] = "HAIDRI CHOWK"
                    if "1050902" in bricks[b]:
                        bricks[b] = "MAIN ROAD BDN"
                    if "1050903" in bricks[b]:
                        bricks[b] = "MAIN BAZAR BDN"
                    if "1050904" in bricks[b]:
                        bricks[b] = "GUNNA BDN"
                    if "1051001" in bricks[b]:
                        bricks[b] = "KACHEHRI ROAD"
                    if "1051003" in bricks[b]:
                        bricks[b] = "KALAS WALA ROAD"
                    if "1051006" in bricks[b]:
                        bricks[b] = "PURANA BAZAR"
                    if "1051007" in bricks[b]:
                        bricks[b] = "CHAWINDA PHATAK"
                    if "1060703" in bricks[b]:
                        bricks[b] = "RAIL WAY ROAD SKG"
                    if "1060705" in bricks[b]:
                        bricks[b] = "NOOR KOT ROAD"
                    if "1060706" in bricks[b]:
                        bricks[b] = "DARMAN ROAD"
                    if "1070803" in bricks[b]:
                        bricks[b] = "LANGRE WALI"
                    if "1070807" in bricks[b]:
                        bricks[b] = "ADDA MAHAL"
                    if "1070808" in bricks[b]:
                        bricks[b] = "SALAN KAY"
                    if "1070809" in bricks[b]:
                        bricks[b] = "MEH RAJKE"
                    if "1070811" in bricks[b]:
                        bricks[b] = "CHAUBARA"
                    if "1070813" in bricks[b]:
                        bricks[b] = "PHALORA"
                    if "1070814" in bricks[b]:
                        bricks[b] = "SIALKOT BHAGOWAL"
                    if "1070815" in bricks[b]:
                        bricks[b] = "GOPAL PUR"
                    if "1010409" in bricks[b]:
                        bricks[b] = "NAWAN PIND"
                    if "1010616" in bricks[b]:
                        bricks[b] = "PAKKA GARHA"
                    if "1010804" in bricks[b]:
                        bricks[b] = "CHAKRALA MARALA"
                    if "1010903" in bricks[b]:
                        bricks[b] = "BHOTH"
                    if "1011004" in bricks[b]:
                        bricks[b] = "KUBAY CHAK"
                    if "1011107" in bricks[b]:
                        bricks[b] = "1011107 - CEO-KAY SKT-J"
                    if "1020101" in bricks[b]:
                        bricks[b] = "JASSAR WALA"
                    if "1031002" in bricks[b]:
                        bricks[b] = "BABU GHULAM NABI ROAD SAMBRIAL"
                    if "1031007" in bricks[b]:
                        bricks[b] = "RANDHIR MOR SAMBRIAL"
                    if "1040904" in bricks[b]:
                        bricks[b] = "DHQ ROAD NWL"
                    if "1040909" in bricks[b]:
                        bricks[b] = "MANDI THROO"
                    if "1050803" in bricks[b]:
                        bricks[b] = "LARI ADDA CHWND"
                    if "1051004" in bricks[b]:
                        bricks[b] = "MAIN BAZAR PSR"
                    if "1070806" in bricks[b]:
                        bricks[b] = "KHARDANA MOR"
                    if "1070810" in bricks[b]:
                        bricks[b] = "WAGHA KNG"
                    if "1070812" in bricks[b]:
                        bricks[b] = "GADGOR KNG"
                    if "1070804" in bricks[b]:
                        bricks[b] = "ORA CHOWK KNG"
                    if "1010608" in bricks[b]:
                        bricks[b] = "MUBARAK PURA KHADIM ALI ROAD"

                    # bricks code changed
                    if "2010101" in bricks[b]:
                        bricks[b] = "COMMISSIONER ROAD"
                    if "2010504" in bricks[b]:
                        bricks[b] = "ABBOTT ROAD"
                    if "2010501" in bricks[b]:
                        bricks[b] = "PARIS ROAD"
                    if "2010502" in bricks[b]:
                        bricks[b] = "RAILWAY ROAD SIALKOT"
                    if "2010806" in bricks[b]:
                        bricks[b] = "KHADIM ALI ROAD"
                    if "2010401" in bricks[b]:
                        bricks[b] = "PULL AIK"
                    if "2010402" in bricks[b]:
                        bricks[b] = "ZAFARWAL ROAD"
                    if "2010703" in bricks[b]:
                        bricks[b] = "KASHMIR ROAD SIALKOT"
                    if "2010805" in bricks[b]:
                        bricks[b] = "CHRISTIAN TOWN / HUNTER PURA"
                    if "2010202" in bricks[b]:
                        bricks[b] = "SADAR BAZAR CANTT SIALKOT"
                    if "2020107" in bricks[b]:
                        bricks[b] = "KOTLI LOHARAN EAST"
                    if "2020105" in bricks[b]:
                        bricks[b] = "DHALLE WALI"
                    if "2020103" in bricks[b]:
                        bricks[b] = "KULLU WAL"
                    if "2020102" in bricks[b]:
                        bricks[b] = "KAPUROWALI"
                    if "2020108" in bricks[b]:
                        bricks[b] = "KOTLI LOHARAN WEST"
                    if "2020201" in bricks[b]:
                        bricks[b] = "PULI TOP KHANA"
                    if "2020205" in bricks[b]:
                        bricks[b] = "MARAKI WAL"
                    if "2020202" in bricks[b]:
                        bricks[b] = "KHAROTA SYEDAN"
                    if "2010207" in bricks[b]:
                        bricks[b] = "DALUWALI"
                    if "2020406" in bricks[b]:
                        bricks[b] = "JHAI"
                    if "2020305" in bricks[b]:
                        bricks[b] = "SAID PUR"
                    if "2020207" in bricks[b]:
                        bricks[b] = "GONDAL"
                    if "2020306" in bricks[b]:
                        bricks[b] = "BAJ WAT"
                    if "3020103" in bricks[b]:
                        bricks[b] = "MIANI ADDA"
                    if "3020104" in bricks[b]:
                        bricks[b] = "GHOYAN KI"
                    if "3020106" in bricks[b]:
                        bricks[b] = "ADDA KAMAL PUR"
                    if "2010604" in bricks[b]:
                        bricks[b] = "HAJI PURA"
                    if "2010303" in bricks[b]:
                        bricks[b] = "RANGPURA"
                    if "2010304" in bricks[b]:
                        bricks[b] = "CIRCULAR ROAD SIALKOT"
                    if "3010103" in bricks[b]:
                        bricks[b] = "NISBAT ROAD"
                    if "3010202" in bricks[b]:
                        bricks[b] = "CHUNGI # 8"
                    if "3010101" in bricks[b]:
                        bricks[b] = "COLLEGE ROAD SIAL KOT"
                    if "3010204" in bricks[b]:
                        bricks[b] = "SAMBRIAL ROAD"
                    if "3020202" in bricks[b]:
                        bricks[b] = "JAMKE CHEEMA"
                    if "3020109" in bricks[b]:
                        bricks[b] = "MUNDEKE GORAYA"
                    if "3020111" in bricks[b]:
                        bricks[b] = "KOTLI BAWA"
                    if "2010709" in bricks[b]:
                        bricks[b] = "MODEL TOWN UGOKI"
                    if "2010706" in bricks[b]:
                        bricks[b] = "SHAHAB PURA CHOWK"
                    if "2010704" in bricks[b]:
                        bricks[b] = "SUBLIME CHOWK"
                    if "2010707" in bricks[b]:
                        bricks[b] = "ADALAT GARH"
                    if "3020302" in bricks[b]:
                        bricks[b] = "SAMBRIAL MORE"
                    if "2010701" in bricks[b]:
                        bricks[b] = "LARI ADDA SIALKOT"
                    if "4020101" in bricks[b]:
                        bricks[b] = "QILA AHMED ABAD"
                    if "2020605" in bricks[b]:
                        bricks[b] = "GALI ABSHAR WALI CHWND"
                    if "2020608" in bricks[b]:
                        bricks[b] = "KACHEHRI ROAD"
                    if "2020609" in bricks[b]:
                        bricks[b] = "KALAS WALA ROAD"
                    if "2010502" in bricks[b]:
                        bricks[b] = "RAIL WAY ROAD SKG"
                    if "2020402" in bricks[b]:
                        bricks[b] = "LANGRE WALI"
                    if "2020502" in bricks[b]:
                        bricks[b] = "ADDA MAHAL"
                    if "2020508" in bricks[b]:
                        bricks[b] = "CHAUBARA"
                    if "2020511" in bricks[b]:
                        bricks[b] = "SIALKOT BHAGOWAL"
                    if "2020301" in bricks[b]:
                        bricks[b] = "KUBAY CHAK"
                    if "2020603" in bricks[b]:
                        bricks[b] = "LARI ADDA CHWND"
                    if "2020607" in bricks[b]:
                        bricks[b] = "MAIN BAZAR PSR"
                    if "2010204" in bricks[b]:
                        bricks[b] = "CHOWK GANTA GHUR"
                    if "2010404" in bricks[b]:
                        bricks[b] = "AIMAN ABAD ROAD"
                    if "2010406" in bricks[b]:
                        bricks[b] = "NAWAN PIND"
                    if "2010405" in bricks[b]:
                        bricks[b] = "AKBAR ABAD"
                    if "2010506" in bricks[b]:
                        bricks[b] = "MUBARAK PURA"
                    if "2010602" in bricks[b]:
                        bricks[b] = "RORAS ROAD"
                    if "2010603" in bricks[b]:
                        bricks[b] = "SHAHAB PURA ROAD"
                    if "2010702" in bricks[b]:
                        bricks[b] = "KOTLI BEHRAM CHOWK"
                    if "2010708" in bricks[b]:
                        bricks[b] = "UGGOKI MAIN ROAD"
                    if "2010801" in bricks[b]:
                        bricks[b] = "GHOHAD PUR CHOWK"
                    if "2010802" in bricks[b]:
                        bricks[b] = "HEAD MARALA ROAD GOHAD PUR"
                    if "2010803" in bricks[b]:
                        bricks[b] = "AIR PORT ROAD GOHAD PUR"
                    if "2020106" in bricks[b]:
                        bricks[b] = "SHAIR PUR"
                    if "2020601" in bricks[b]:
                        bricks[b] = "ADDA GUNNA"
                    if "2020602" in bricks[b]:
                        bricks[b] = "ADDA BADIYANA"
                    if "3010105" in bricks[b]:
                        bricks[b] = "PULL NAHAR"
                    if "3020305" in bricks[b]:
                        bricks[b] = "MAJRA KALAN"
                    if "3020303" in bricks[b]:
                        bricks[b] = "ADDA BEGOWALA"
                    if "3020301" in bricks[b]:
                        bricks[b] = "MAIN ROAD SAMBRIAL"
                    if "3020206" in bricks[b]:
                        bricks[b] = "BOPAL WALA"
                    if "3020203" in bricks[b]:
                        bricks[b] = "ADAMKAY CHEEMA"
                    if "3020201" in bricks[b]:
                        bricks[b] = "ADDA MOTRA"
                    if "3020101" in bricks[b]:
                        bricks[b] = "DOBURJI CHOWK"
                    if "3010206" in bricks[b]:
                        bricks[b] = "ADDA JAISAR WALA"
                    if "3010205" in bricks[b]:
                        bricks[b] = "CIVIL CHOWK"
                    if "2010201" in bricks[b]:
                        bricks[b] = "IDREES HOSPITAL CHOWK CANTT"
                    if "2010208" in bricks[b]:
                        bricks[b] = "ISLAMIA COLLEGE ROAD"
                    if "2010302" in bricks[b]:
                        bricks[b] = "RUNG PURA CHOWK"
                    if "2010306" in bricks[b]:
                        bricks[b] = "IMAM SAB CHOWK"
                    if "2010403" in bricks[b]:
                        bricks[b] = "PASRUR ROAD SIALKOT"
                    if "2010507" in bricks[b]:
                        bricks[b] = "GREEN WOOD STREET"
                    if "2010508" in bricks[b]:
                        bricks[b] = "SARDAR BEGUM CHOWK"
                    if "2010601" in bricks[b]:
                        bricks[b] = "DEFENCE ROAD EAST SIDE"
                    if "2010605" in bricks[b]:
                        bricks[b] = "FATEH GARH SIALKOT"
                    if "2020403" in bricks[b]:
                        bricks[b] = "ORA CHOWK JHAI"
                    if "2020405" in bricks[b]:
                        bricks[b] = "DALUWALI"
                    if "2020501" in bricks[b]:
                        bricks[b] = "ADDA KHARANA"
                    if "2020504" in bricks[b]:
                        bricks[b] = "MIRAJKAY"
                    if "2020509" in bricks[b]:
                        bricks[b] = "GADGOR KNG"
                    if "2020606" in bricks[b]:
                        bricks[b] = "CHAWINDA PHATAK"
                    if "3010203" in bricks[b]:
                        bricks[b] = "SOHAWA STOP"
                    if "3020105" in bricks[b]:
                        bricks[b] = "HAPPO GARHA"
                    if "3020107" in bricks[b]:
                        bricks[b] = "BHALLOWALI SIALKOT"
                    if "3020304" in bricks[b]:
                        bricks[b] = "JETHI KAY ROAD"
                    if "4020104" in bricks[b]:
                        bricks[b] = "MANDI THROO"
                    if "3020306" in bricks[b]:
                        bricks[b] = "SAHO WALA"
                    if "2010301" in bricks[b]:
                        bricks[b] = "BAIRY WALA CHOWK"
                    if "2010407" in bricks[b]:
                        bricks[b] = "PASRUR ROAD AHEAD CHINA CHOWK"
                    if "2010104" in bricks[b]:
                        bricks[b] = "CHAKRALA MARALA"
                    if "2020109" in bricks[b]:
                        bricks[b] = "HASSAN WAL"
                    if "2020204" in bricks[b]:
                        bricks[b] = "BHARTH"
                    if "2020206" in bricks[b]:
                        bricks[b] = "SHADIWAL"
                    if "2020302" in bricks[b]:
                        bricks[b] = "JUNG MORE"
                    if "2020304" in bricks[b]:
                        bricks[b] = "ADDA RUM"
                    if "2020510" in bricks[b]:
                        bricks[b] = "PHALORA"
                    if "2020512" in bricks[b]:
                        bricks[b] = "ADDA GOPAL PUR"
                    if "4010101" in bricks[b]:
                        bricks[b] = "DHQ ROAD NWL"
                    if "4010103" in bricks[b]:
                        bricks[b] = "ZAFAR WAL ROAD NWL"
                    if "2020104" in bricks[b]:
                        bricks[b] = "CHAKRALA MARALA"
                    if "2010305" in bricks[b]:
                        bricks[b] = "ADDA PASRURIAN"
                    if "2010710" in bricks[b]:
                        bricks[b] = "NOUL MORH / HARRAR"
                    if "4020201" in bricks[b]:
                        bricks[b] = "MAIN BAZAR ZAFARWAL"
                    if "4020206" in bricks[b]:
                        bricks[b] = "THQ ROAD"
                    if "2020404" in bricks[b]:
                        bricks[b] = "RANGERS ROAD"

                for s in range(0, len(sales)):
                    for i in range(0, len(sales[s])):
                        child = []
                        child.append(products[i])
                        child.append(bricks[s])
                        child.append(sales[s][i])
                        result.append(child)
                for r in range(0, len(result)):
                    for i in item_list:
                        if result[r][0] == i[0]:
                            if result[r][2] != "0":
                                new_result.append(result[r])

                for r in range(0, len(new_result)):
                    for i in item_list:
                        if new_result[r][0] == i[0]:
                            new_result[r].insert(1, i[1])
                            new_result[r].append(i[2])
                for r in new_result:
                    for t in tt_list:
                        if r[2] == t[0]:
                            r.insert(4, t[1])
                new_result = green_team_bricks(new_result)
                return new_result
            elif dist_city == "Narowal":
                products = []
                bricks = []
                sales = []
                result = []
                new_result = []
                for x in range(0, len(pdf.pages)):
                    data = pdf.pages[x].extract_table()
                    if data[0][0] == "FOI Id :  /":
                        products.append(data[1][1:-1])
                        for i in range(2, len(data) - 1):
                            bricks.append(data[i][0])
                            sales.append(data[i][1:-1])
                    else:
                        products.append(data[0][1:-1])
                        for i in range(1, len(data) - 1):
                            bricks.append(data[i][0])
                            sales.append(data[i][1:-1])

                for p in range(0, len(products)):
                    for i in range(0, len(products[p])):
                        if "006003" in products[p][i]:
                            products[p][i] = "002392"
                        if "006004" in products[p][i]:
                            products[p][i] = "008999"
                        if "006005" in products[p][i]:
                            products[p][i] = "004348"
                        if "006006" in products[p][i]:
                            products[p][i] = "002188"
                        if "006022" in products[p][i]:
                            products[p][i] = "005425"
                        if "006025" in products[p][i]:
                            products[p][i] = "081838"
                        if "006026" in products[p][i]:
                            products[p][i] = "023906"
                        if "006027" in products[p][i]:
                            products[p][i] = "031037"
                        if "006031" in products[p][i]:
                            products[p][i] = "008909"
                        if "006032" in products[p][i]:
                            products[p][i] = "081274"
                        if "006033" in products[p][i]:
                            products[p][i] = "038427"
                        if "006034" in products[p][i]:
                            products[p][i] = "038426"
                        if "006035" in products[p][i]:
                            products[p][i] = "006784"
                        if "006036" in products[p][i]:
                            products[p][i] = "008908"
                        if "006037" in products[p][i]:
                            products[p][i] = "006782"
                        if "006038" in products[p][i]:
                            products[p][i] = "006783"
                        if "006039" in products[p][i]:
                            products[p][i] = "012649"
                        if "006040" in products[p][i]:
                            products[p][i] = "019133"
                        if "006041" in products[p][i]:
                            products[p][i] = "016654"
                        if "006042" in products[p][i]:
                            products[p][i] = "032255"
                        if "006043" in products[p][i]:
                            products[p][i] = "029328"
                        if "006044" in products[p][i]:
                            products[p][i] = "024820"
                        if "006046" in products[p][i]:
                            products[p][i] = "024819"
                        if "006047" in products[p][i]:
                            products[p][i] = "028728"
                        if "006050" in products[p][i]:
                            products[p][i] = "026920"
                        if "006052" in products[p][i]:
                            products[p][i] = "006406"
                # print(products)

                for b in range(0, len(bricks)):
                    if "1010101" in bricks[b]:
                        bricks[b] = "DHA NAROWAL"
                    if "1010102" in bricks[b]:
                        bricks[b] = "KUTCHERY ROAD"
                    if "1010103" in bricks[b]:
                        bricks[b] = "RAILWAY ROAD NAROWAL"
                    if "1010104" in bricks[b]:
                        bricks[b] = "ZAFARWAL ROAD NAROWAL"
                    if "1010105" in bricks[b]:
                        bricks[b] = "MURIDKE ROAD"
                    if "1010201" in bricks[b]:
                        bricks[b] = "NURKOT"
                    if "1010202" in bricks[b]:
                        bricks[b] = "JASSAR"
                    if "1010203" in bricks[b]:
                        bricks[b] = "BUSTAN"
                    if "1010205" in bricks[b]:
                        bricks[b] = "KANJRUR"
                    if "1010207" in bricks[b]:
                        bricks[b] = "SHAKARGHAR CITY"
                    if "1010208" in bricks[b]:
                        bricks[b] = "ZAFAR WAL"
                    if "1010209" in bricks[b]:
                        bricks[b] = "DHOBIWALA"
                    if "1010301" in bricks[b]:
                        bricks[b] = "DHAM THAL"
                    if "1010302" in bricks[b]:
                        bricks[b] = "SANKHATRA"
                    if "1010303" in bricks[b]:
                        bricks[b] = "PINDI BORI"
                    if "1010304" in bricks[b]:
                        bricks[b] = "DERMAN"
                    if "1010305" in bricks[b]:
                        bricks[b] = "ZAFARWAL CITY"
                    if "1010307" in bricks[b]:
                        bricks[b] = "NONAR NAROWAL"
                    if "1010308" in bricks[b]:
                        bricks[b] = "NONAR NAROWAL"
                    if "1010309" in bricks[b]:
                        bricks[b] = "SHAH GREEB"
                    if "1010311" in bricks[b]:
                        bricks[b] = "DHABLI WALA"
                    if "1010401" in bricks[b]:
                        bricks[b] = "DOMALA VILLAGE"
                    if "1010402" in bricks[b]:
                        bricks[b] = "QILA AHMEDABAD NAROWAL"
                    if "1010404" in bricks[b]:
                        bricks[b] = "PASRUR NAROWAL"
                    if "1010405" in bricks[b]:
                        bricks[b] = "CHAWINDA"
                    if "1010501" in bricks[b]:
                        bricks[b] = "TALWANDI"
                    if "1010502" in bricks[b]:
                        bricks[b] = "ADA SIRAJ"
                    if "1010503" in bricks[b]:
                        bricks[b] = "QILA KALLAR WALA"
                    if "1010504" in bricks[b]:
                        bricks[b] = "BADDO MALHI"
                    if "1010204" in bricks[b]:
                        bricks[b] = "MANZOR PURA"
                # print(bricks)

                for s in range(0, len(sales)):
                    for i in range(0, len(sales[s])):
                        if sales[s][i] == "-":
                            sales[s][i] = "0"
                products = [item for sublist in products for item in sublist]

                for s in range(0, len(sales)):
                    for i in range(0, len(sales[s])):
                        child = []
                        child.append(products[i])
                        child.append(bricks[s])
                        child.append(sales[s][i])
                        result.append(child)

                for r in range(0, len(result)):
                    for i in item_list:
                        if result[r][0] == i[0]:
                            if result[r][2] != "0":
                                new_result.append(result[r])
                # print(len(new_result))
                for r in range(0, len(new_result)):
                    for i in item_list:
                        if new_result[r][0] == i[0]:
                            new_result[r].insert(1, i[1])
                            new_result[r].append(i[2])
                for r in new_result:
                    for t in tt_list:
                        if r[2] == t[0]:
                            r.insert(4, t[1])
                new_result = green_team_bricks(new_result)
                return new_result

            elif dist_city == "Gujranwala":
                result = []
                new_result = []
                bricks = []
                sales = []

                for page in pdf.pages:
                    text = page.extract_text()
                    lines = text.split("\n")

                    # ---- header aur footer ke darmiyan asal data ka range dhoondein ----
                    start_idx = None
                    end_idx = len(lines)
                    for i, line in enumerate(lines):
                        if "City/Sub City Name" in line:
                            start_idx = i + 1
                        if "Unit Totals" in line or "<<SoftWave>>" in line:
                            end_idx = min(end_idx, i)

                    i = start_idx
                    while i < end_idx:
                        line = lines[i].strip()
                        i += 1
                        if not line or line == "AMP":
                            continue

                        tokens = line.split()

                        # ---- pehla "pure number" token dhoondein; yahin se values shuru hoti hain ----
                        idx = None
                        for j in range(1, len(tokens)):
                            if re.fullmatch(r"-?\d+", tokens[j]):
                                idx = j
                                break
                        if idx is None:
                            continue  # yeh brick line nahi hai

                        name = " ".join(tokens[0:idx])
                        values = tokens[
                            idx:-1
                        ]  # aakhri token total value hai, hata dein

                        # ---- agli line ek chhota "serial number" column hai (product value NAHI hai) ----
                        # ---- ise sirf skip/consume karein, values mein add na karein ----
                        if i < end_idx and re.fullmatch(r"-?\d+", lines[i].strip()):
                            i += 1

                        bricks.append(name)
                        sales.append(values)

                # ---- brick names normalize karein ----
                for b in range(0, len(bricks)):
                    if bricks[b] == "HOSPITAL  ROAD":
                        bricks[b] = "HOSPITAL ROAD"
                    if bricks[b] == "SIALKOT RAOD":
                        bricks[b] = "SIALKOT ROAD GUJRANWALA"
                    if bricks[b] == "SHAHEEN ABAD  -":
                        bricks[b] = "SHAHEEN ABAD"
                    if bricks[b] == "EMAN ABAD  -":
                        bricks[b] = "EMAN ABAD"
                    if bricks[b] == "GAKHAR  -":
                        bricks[b] = "GAKHAR"
                    if bricks[b] == "SIALKOT":
                        bricks[b] = "SIALKOT GUJRANWALA"

                # ---- column order (confirm ki gayi): ----
                # col0 = A-JETEPAR10ML  -> 008999 (Jetepar Injection 10ml)
                # col1 = JETEPAR2MLAMP  -> 004348 (Jetepar Injection 2ml)
                # col2 = JETEPARCAPS    -> 002392 (Jetepar Capsule)
                # col3 = JETEPARINJ10m  -> 008999 (SAME product jaisa col0, add karein)
                # col4 = JETEPARSYRUP   -> 002188 (Jetepar Syrup)
                # col5 = MAIORADTAB     -> 012961 (Maiorad Tablet)
                # (Maiorad Injection is report mein nahi hai)

                for b in range(0, len(bricks)):
                    vals = sales[b]

                    jetepar_10ml = int(vals[0]) + int(
                        vals[3]
                    )  # col0 + col3, same product
                    jetepar_2ml = int(vals[1])
                    jetepar_cap = int(vals[2])
                    jetepar_syrup = int(vals[4])
                    maiorad_tab = int(vals[5])

                    row_map = [
                        ("008999", jetepar_10ml),
                        ("004348", jetepar_2ml),
                        ("002392", jetepar_cap),
                        ("002188", jetepar_syrup),
                        ("012961", maiorad_tab),
                    ]

                    for code, val in row_map:
                        child = []
                        child.append(code)
                        child.append(bricks[b])
                        child.append(str(val))
                        result.append(child)

                for r in range(0, len(result)):
                    for i in item_list:
                        if result[r][0] == i[0]:
                            if result[r][2] != "0":
                                new_result.append(result[r])

                for r in range(0, len(new_result)):
                    for i in item_list:
                        if new_result[r][0] == i[0]:
                            new_result[r].insert(1, i[1])
                            new_result[r].append(i[2])

                for r in new_result:
                    for t in tt_list:
                        if r[2] == t[0]:
                            r.insert(4, t[1])

                new_result = green_team_bricks(new_result)
                return new_result
            elif dist_city == "Mandi Bahauddin":
                result = []
                new_result = []
                products = []
                bricks = []
                sales = []
                for x in range(0, len(pdf.pages)):
                    data = pdf.pages[x].extract_table()
                    bricks = data[0][1:15]
                    if x == len(pdf.pages) - 1:
                        for d in range(1, len(data) - 2):
                            sales.append(data[d][1:15])
                            if d == len(data) - 3:
                                products.append("081274")
                            elif d == len(data) - 4:
                                products.append("008909")
                            else:
                                products.append(data[d][0])

                    else:
                        for d in range(1, len(data)):
                            if data[d][0] != "BLUE":
                                sales.append(data[d][1:15])
                                products.append(data[d][0])
                # print(len(products))

                for b in range(0, len(bricks)):
                    if bricks[b] == "KUT.SHK":
                        bricks[b] = "KUTHYALA SYEDAN"
                    if bricks[b] == "MALIK.\nW":
                        bricks[b] = "MALAKWAL"
                    if bricks[b] == "QADIF":
                        bricks[b] = "QADIRABAD"
                    if bricks[b] == "BOSSAL":
                        bricks[b] = "BOSAL"
                    if bricks[b] == "JOKALIO":
                        bricks[b] = "JOKALI"
                    if bricks[b] == "PHARN\nWA":
                        bricks[b] = "PHARN"
                    if bricks[b] == "HEAD FA":
                        bricks[b] = "HEAD"

                # print(bricks)

                for s in range(0, len(sales)):
                    for i in range(0, len(sales[s])):
                        if sales[s][i] == "":
                            sales[s][i] = "0"

                for p in range(0, len(products)):
                    for s in range(0, len(sales[p])):
                        if bricks[s] == "":
                            continue
                        child = []
                        child.append(products[p])
                        child.append(bricks[s])
                        child.append(sales[p][s])
                        result.append(child)
                # print(result)

                for r in range(0, len(result)):
                    if "MAIORAD INJ 6AMP" in result[r][0]:
                        result[r][0] = "009072"
                    if "JETEPAR 2ML INJ 10AMP" in result[r][0]:
                        result[r][0] = "004348"
                    if "JETEPAR CAP 20CAP" in result[r][0]:
                        result[r][0] = "002392"
                    if "JETEPAR 10ML/INJ 5AMP" in result[r][0]:
                        result[r][0] = "008999"
                    if "MAIORAD 100MG TAB 30TAB" in result[r][0]:
                        result[r][0] = "012961"
                    if "AFLOXAN 150MG CAP 20CAP" in result[r][0]:
                        result[r][0] = "008376"
                    if "AFLOXAN 300MG TAB 30TAB" in result[r][0]:
                        result[r][0] = "017230"
                    if "MOXILIUM 250GM 60ML" in result[r][0]:
                        result[r][0] = "012649"
                    if "MOXILIUM 250CAP 20CAP" in result[r][0]:
                        result[r][0] = "006784"
                    if "EBAST 10MG TAB 10TAB" in result[r][0]:
                        result[r][0] = "023906"
                    if "MINQAIR 5MG TAB 14TAB" in result[r][0]:
                        result[r][0] = "038426"
                    if "MINQAIR 10MG TAB 14TAB" in result[r][0]:
                        result[r][0] = "038427"
                    if "SUPRACEF 100MG SYRP 30ML" in result[r][0]:
                        result[r][0] = "024819"
                    if "PROBITOR 20MGCAP 14CAP" in result[r][0]:
                        result[r][0] = "016654"
                    if "TRAMAGESIC INJ 5AMP" in result[r][0]:
                        result[r][0] = "026920"
                    if "JETEPAR SYRUP 112ML" in result[r][0]:
                        result[r][0] = "002188"
                    if "MOXILIUM 125SUSPEN 45ML" in result[r][0]:
                        result[r][0] = "006783"
                    if "VIKONON FORTE SYRUP 120ML" in result[r][0]:
                        result[r][0] = "006406"
                    if "MOXILIUM 500MG CAP 20CAP" in result[r][0]:
                        result[r][0] = "008908"
                    if "MOXILIUM DROPES 10ML" in result[r][0]:
                        result[r][0] = "006782"
                    if "PC-LAC SYRUP 120ML" in result[r][0]:
                        result[r][0] = "019133"
                    if "VIGROL FORTE 50TAB" in result[r][0]:
                        result[r][0] = "007018"
                    if "CYANORIN FORTE 25AMP" in result[r][0]:
                        result[r][0] = "005425"
                    if "HISTAFEX 120MG TAB 10TAB" in result[r][0]:
                        result[r][0] = "031037"
                    if "SAVELOX 250MG TAB 10TAB" in result[r][0]:
                        result[r][0] = "032255"
                    if "SAVELOX 500MG TAB 10TAB" in result[r][0]:
                        result[r][0] = "029328"
                    if "SUPRALOX 50ML" in result[r][0]:
                        result[r][0] = "028728"
                    if "SUPRACEF 400MG CAP 5CAP" in result[r][0]:
                        result[r][0] = "024820"
                    if "TRAMAGESIC 50MG 20CAP" in result[r][0]:
                        result[r][0] = "029327"
                    if "DEPROGESIC -P 10TAB" in result[r][0]:
                        result[r][0] = "081838"
                    if "AVOR 2MG TAB 100TAB" in result[r][0]:
                        result[r][0] = "007853"
                # print(result)

                for r in range(0, len(result)):
                    for i in item_list:
                        if result[r][0] == i[0]:
                            if result[r][2] != "0":
                                new_result.append(result[r])

                for r in range(0, len(new_result)):
                    for i in item_list:
                        if new_result[r][0] == i[0]:
                            new_result[r].insert(1, i[1])
                            new_result[r].append(i[2])
                for r in new_result:
                    for t in tt_list:
                        if r[2] == t[0]:
                            r.insert(4, t[1])
                new_result = green_team_bricks(new_result)
                return new_result

            elif dist_city == "Mardan":
                result = []
                products = []
                products1 = []
                bricks = []
                sales = []
                n_sales = []
                for x in range(0, len(pdf.pages)):
                    data = pdf.pages[x].extract_tables()
                    # print(data)
                    bricks = data[0]
                    # print(bricks)
                    index1 = bricks[0].index("")
                    # print(index1)
                    if index1 == 8:
                        products1 = ["008999", "002188", "004348", "002392"]
                    if index1 == 14:
                        products1 = ["008999", "002188", "004348", "002392", "009072"]
                    if index1 == 15:
                        products1 = [
                            "008376",
                            "008999",
                            "002188",
                            "004348",
                            "002392",
                            "009072",
                        ]

                    bricks = [b for b in bricks[0][1:index1]]
                    # print(bricks)
                    for c in range(0, len(bricks)):
                        bricks[c] = re.sub("\n", "", bricks[c])
                        bricks[c] = re.sub("SHAWAADDA[+]N", "SHEWA ADDA", bricks[c])
                        bricks[c] = re.sub("SHAHMANSOO", "SHAHMANSOOR", bricks[c])
                        bricks[c] = re.sub("M.CPLAZA", "MC PLAZA", bricks[c])
                        bricks[c] = re.sub("MIRAFZALKHA", "MIR AFZAL KHAN", bricks[c])
                        bricks[c] = re.sub(
                            "HOSPITALROA", "HOSPITAL ROAD MDN", bricks[c]
                        )
                        bricks[c] = re.sub("PARHOTI", "PAR HOTI", bricks[c])
                        bricks[c] = re.sub("RASHAKI", "RASHAKAI", bricks[c])
                        bricks[c] = re.sub("M.M.C", "MARDAN MEDICAL COMPLEX", bricks[c])
                        bricks[c] = re.sub("COLLAGECHO", "COLLEGE CHOWK", bricks[c])
                        bricks[c] = re.sub("GHARIKAPOOR", "GHARI KAPURA", bricks[c])
                        bricks[c] = re.sub("NEWADDARET", "NEW ADDA RETAIL", bricks[c])
                        bricks[c] = re.sub(
                            "NEWADDAWHO", "NEW ADDA WHOLESALE", bricks[c]
                        )
                        bricks[c] = re.sub("B-R-WS", "BANK ROAD WHOLESALE", bricks[c])
                        bricks[c] = re.sub("SHEDANOBAR", "SHEDAN BAZAR", bricks[c])
                        bricks[c] = re.sub("T.BAI", "TAKHT BHAI", bricks[c])
                        bricks[c] = re.sub("LUNDKHUR", "LUND KHWAR", bricks[c])
                        bricks[c] = re.sub(
                            "DAKI[+]SHAKNO", "DAKI AND SHAKNO", bricks[c]
                        )
                    data1 = pdf.pages[x].extract_text()
                    # split the data at new line
                    data1 = re.sub("\n", "$", data1)
                    data1 = data1.split("$")
                    for i in range(16, len(data1) - 3):
                        data1[i] = re.sub(r"\s\s+", "#", data1[i])
                        data1[i] = data1[i].split("#")
                        products.append(data1[i][0])
                        # print(n_sales)
                    sal = []
                    sales2 = []
                    sal = data[1]
                    # print(sal[0])
                    for c in range(0, len(sal) - 2):
                        sales2 = sal[c][0 : index1 - 1]
                        sales.append(sales2)
                data1 = data1[16][1:index1]
                sales.insert(0, data1)

                for p in range(0, len(products1)):
                    for s in range(0, len(sales[p])):
                        child = []
                        child.append(products1[p])
                        child.append(bricks[s])
                        child.append(sales[p][s])
                        result.append(child)
                for r in result:
                    for i in item_list:
                        if r[0] == i[0]:
                            r.insert(1, i[1])
                            r.append(i[2])
                #             # print(r)
                for r in result:
                    for t in tt_list:
                        if r[2] == t[0]:
                            r.insert(4, t[1])
                            # print(r)
                result = green_team_bricks(result)
                return result

            elif dist_city == "Timergara":
                result = []
                products = []
                bricks = []
                sales = []
                data = pdf.pages[0].extract_table()
                for i in range(0, len(data)):
                    bricks = data[0][3:-1]

                    if data[i][1] == None:
                        pass
                    else:
                        products.append(data[i][1])
                        sales.append(data[i][3:-1])
                for i in range(0, len(products)):
                    bricks[i] = re.sub("TIMERGARA", "TIMERGARA TMG", bricks[i])
                for i in range(0, len(products)):
                    # products2[i] = re.sub('\n','',products2[i])
                    products[i] = re.sub("AFLOXAN CAP", "008376", products[i])
                    products[i] = re.sub("AFLOXAN TAB 300MG", "017230", products[i])
                    products[i] = re.sub("JETEPAR 10ML AMP", "008999", products[i])
                    products[i] = re.sub("JETEPAR 2ML AMP:", "004348", products[i])
                    products[i] = re.sub("JETEPAR CAPS", "002392", products[i])
                    products[i] = re.sub("JETEPAR SYP", "002188", products[i])
                    products[i] = re.sub("MAIORAD 3ML AMP", "009072", products[i])
                    products[i] = re.sub("MAIORAD TAB", "012961", products[i])
                for s in range(0, len(sales)):
                    for i in range(0, len(sales[s])):
                        if sales[s][i] == "":
                            sales[s][i] = "0"
                # print(bricks)
                # print(products)
                # print(sales)
                for p in range(0, len(products)):
                    for s in range(0, len(sales[p])):
                        child = []
                        child.append(products[p])
                        child.append(bricks[s])
                        child.append(sales[p][s])
                        result.append(child)
                for r in result:
                    for i in item_list:
                        if r[0] == i[0]:
                            r.insert(1, i[1])
                            r.append(i[2])
                for r in result:
                    for t in tt_list:
                        if r[2] == t[0]:
                            r.insert(4, t[1])
                result = green_team_bricks(result)
                return result

            elif dist_city == "Bannu":
                products = []
                sales = []
                bricks = []
                result = []
                for x in range(0, len(pdf.pages)):
                    data = pdf.pages[x].extract_table()
                    # print(data)
                    # change the zero below to 1 if any error occurs in product
                    products.append(data[0][1:-1])
                    # print(data[0])
                    for i in range(2, len(data) - 1):
                        sales.append(data[i][1:-1])
                        # print(sales)
                        bricks.append(data[i][0])
                    # print(bricks)
                    for k in range(0, len(bricks)):
                        bricks[k] = bricks[k][8:]
                        if bricks[k] == "BANNU":
                            bricks[k] = "BANNU MAIN"
                        if bricks[k] == "MIRANSHAH":
                            bricks[k] = "MIRAN SHAH"
                        if bricks[k] == "LAKKI":
                            bricks[k] = "LAKKI MARWAT"
                        if bricks[k] == "- LAKKI GATE":
                            bricks[k] = "LAKKI GATE"
                        if bricks[k] == "- DHQ":
                            bricks[k] = "DHQ BNU"
                        if bricks[k] == "- ZHQ":
                            bricks[k] = "ZHQ"
                        if bricks[k] == "- RAILWAY ROAD":
                            bricks[k] = "RAILWAY ROAD"
                        if bricks[k] == "- GHALA MANDI":
                            bricks[k] = "GHALA MANDI"
                        if bricks[k] == "- DAS CHWOK":
                            bricks[k] = "DAS CHOWK"
                        if bricks[k] == "- KGN":
                            bricks[k] = "KGN"
                        if bricks[k] == "- MANGAL MELA":
                            bricks[k] = "MANGAL MELA"
                        if bricks[k] == "- AMBERI KALA":
                            bricks[k] = "AMBERI KALA"
                        if bricks[k] == "- DOMAIL":
                            bricks[k] = "DOMAIL"
                        if bricks[k] == "- MIRANSHAH":
                            bricks[k] = "MIRANSHAH"
                        if bricks[k] == "- MIR ALI":
                            bricks[k] = "MIR ALI"
                        if bricks[k] == "- NAURANG":
                            bricks[k] = "NAURANG"
                        if bricks[k] == "- GAMBILA":
                            bricks[k] = "GAMBILA"
                        if bricks[k] == "- TAJORI":
                            bricks[k] = "TAJORI"
                        if bricks[k] == "- LAKKI":
                            bricks[k] = "LAKKI MARWAT"
                        if bricks[k] == "- KARAK":
                            bricks[k] = "KARAK"
                        if bricks[k] == "- LATAMBER":
                            bricks[k] = "LATAMBER"
                        if bricks[k] == "- TAKHT E NASRATI":
                            bricks[k] = "TAKHT E NASRATI"
                        if bricks[k] == "MIRANSHAH":
                            bricks[k] = "MIRAN SHAH"
                        if bricks[k] == "- SURANI GT":
                            bricks[k] = "SURANI GT"
                        if bricks[k] == "- SURANI":
                            bricks[k] = "SURANI"
                        if bricks[k] == "- TAJI KALA":
                            bricks[k] = "TAJI KALA"
                        if bricks[k] == "- TAJI KALA GT":
                            bricks[k] = "TAJI KALA GT"
                        if bricks[k] == "- SABIR ABAD":
                            bricks[k] = "SABIR ABAD"
                        if bricks[k] == "- SABIR ABAD GT":
                            bricks[k] = "SABIR ABAD GT"

                        # if '- TAJI KALA' in bricks:
                        # 	bricks[k]='TAJI KALA'

                for p in range(0, len(products)):
                    for i in range(0, len(products[p])):
                        if "014010" in products[p][i]:
                            products[p][i] = "005425"
                        if "014011" in products[p][i]:
                            products[p][i] = "081838"
                        if "014013" in products[p][i]:
                            products[p][i] = "023906"
                        if "014021" in products[p][i]:
                            products[p][i] = "008999"
                        if "014022" in products[p][i]:
                            products[p][i] = "004348"
                        if "014023" in products[p][i]:
                            products[p][i] = "002188"
                        if "014024" in products[p][i]:
                            products[p][i] = "002392"
                        if "014025" in products[p][i]:
                            products[p][i] = "009072"
                        if "014027" in products[p][i]:
                            products[p][i] = "071560"
                        if "014030" in products[p][i]:
                            products[p][i] = "081274"
                        if "014033" in products[p][i]:
                            products[p][i] = "038427"
                        if "014035" in products[p][i]:
                            products[p][i] = "006783"
                        if "014036" in products[p][i]:
                            products[p][i] = "012649"
                        if "014037" in products[p][i]:
                            products[p][i] = "012649"
                        if "014038" in products[p][i]:
                            products[p][i] = "008908"
                        if "014039" in products[p][i]:
                            products[p][i] = "006782"
                        if "014040" in products[p][i]:
                            products[p][i] = "032259"
                        if "014041" in products[p][i]:
                            products[p][i] = "019133"
                        if "014042" in products[p][i]:
                            products[p][i] = "016654"
                        if "014043" in products[p][i]:
                            products[p][i] = "032255"
                        if "014044" in products[p][i]:
                            products[p][i] = "029328"
                        if "014045" in products[p][i]:
                            products[p][i] = "024819"
                        if "014046" in products[p][i]:
                            products[p][i] = "028727"
                        if "014048" in products[p][i]:
                            products[p][i] = "028728"
                        if "014049" in products[p][i]:
                            products[p][i] = "026920"
                        if "014052" in products[p][i]:
                            products[p][i] = "006406"
                        if "014015" in products[p][i]:
                            products[p][i] = "031037"
                        if "014018" in products[p][i]:
                            products[p][i] = "035295"
                        if "014026" in products[p][i]:
                            products[p][i] = "012961"
                        if "014034" in products[p][i]:
                            products[p][i] = "038426"
                        if "014051" in products[p][i]:
                            products[p][i] = "007018"
                        if "014005" in products[p][i]:
                            products[p][i] = "007853"
                        # print(products[p][i])

                for s in range(0, len(sales)):
                    for i in range(0, len(sales[s])):
                        if sales[s][i] == "-":
                            sales[s][i] = "0"
                for s in range(0, len(sales)):
                    for i in range(0, len(sales[s])):
                        child = []
                        child.append(products[p][i])
                        child.append(bricks[s])
                        child.append(sales[s][i])
                        result.append(child)
                for r in result:
                    for i in item_list:
                        if r[0] == i[0]:
                            r.insert(1, i[1])
                            r.append(i[2])
                            # print(r)
                # print(result)
                for r in result:
                    for t in tt_list:
                        if r[2] == t[0]:
                            r.insert(4, t[1])
                            # print(r)
                result = green_team_bricks(result)
                return result

            elif dist_city == "Dera Ismail Khan":
                result = []
                products = ["008999", "004348", "002392", "002188", "009072", "012961"]

                bricks = [
                    "D.I.KHAN",
                    "TANK",
                    "WANA",
                    "PAHAR",
                    "DRABAN/CHOD",
                    "PROVA/RAMAK",
                    "JANDOLA",
                    "ZAFAR",
                    "PEZU/PANYALA",
                    "NEW DERA",
                    "MAKEEN",
                ]

                sales = []

                data = pdf.pages[0].extract_table()
                for x in range(0, len(data)):
                    # print(data[x][0:11])
                    sales.append(data[x][0:11])
                # print(sales)
                for b in range(0, len(bricks)):
                    if bricks[b] == "PAHAR":
                        bricks[b] = "PAHAR PUR"
                    if bricks[b] == "DRABAN/CHOD":
                        bricks[b] = "DRABAN"
                    if bricks[b] == "PROVA/RAMAK":
                        bricks[b] = "PROVA"
                    if bricks[b] == "PEZU/PANYALA":
                        bricks[b] = "PANI ALA"
                    if bricks[b] == "D.I.KHAN":
                        bricks[b] = "DIKHAN"

                for s in range(0, len(sales)):
                    for i in range(0, len(sales[s])):
                        if sales[s][i] == "":
                            sales[s][i] = "0"
                for p in range(0, len(products)):
                    for s in range(0, len(sales[p])):
                        child = []
                        child.append(products[p])
                        child.append(bricks[s])
                        child.append(sales[p][s])
                        result.append(child)

                for r in result:
                    for i in item_list:
                        if r[0] == i[0]:
                            r.insert(1, i[1])
                            r.append(i[2])
                        # print(r)

                for r in result:
                    for t in tt_list:
                        if r[2] == t[0]:
                            r.insert(4, t[1])
                            # print(r)
                result = green_team_bricks(result)
                return result
            elif dist_city == "Abbotabad":
                result = []
                products = []
                bricks = []
                sales = []
                sales1 = []
                for x in range(0, len(pdf.pages)):
                    data = pdf.pages[x].extract_table()
                    products = data[0][1:-1]
                    sales = data[1:-1]
                    for i in range(0, len(products)):
                        products[i] = re.sub("\n", "", products[i])
                        if "JETEPAR 10ML AMP" in products[i]:
                            products[i] = "008999"
                        if "JETEPAR 2ML AMP" in products[i]:
                            products[i] = "004348"
                        if "JETEPAR CAP" in products[i]:
                            products[i] = "002392"
                        if "JETEPAR SYP" in products[i]:
                            products[i] = "002188"
                        if "MAIORAD TAB" in products[i]:
                            products[i] = "012961"
                        if "MAIORAD 3ML AMP" in products[i]:
                            products[i] = "009072"
                        if "AFLOXAN TAB" in products[i]:
                            products[i] = "017230"
                        if "AFLOXAN CAP" in products[i]:
                            products[i] = "008376"
                for i in range(0, len(sales)):
                    bricks.append(sales[i][0])
                    bricks[i] = bricks[i][10:]
                    sales[i] = sales[i][1:-1]
                for i in range(0, len(bricks)):
                    if bricks[i] == "BUTTGRAM":
                        bricks[i] = "BATTAGRAM"
                    if bricks[i] == "SHINKIARI/BUFFA":
                        bricks[i] = "SHINKIARI"
                    if bricks[i] == "GARI/BALLAKOT":
                        bricks[i] = "GARI BALLAKOT"
                    if bricks[i] == "DERBAND":
                        bricks[i] = "DARBAND"
                    if bricks[i] == "BATTAL/CHATTAR":
                        bricks[i] = "BATTAL AND CHATTAR"
                for s in range(0, len(sales)):
                    for i in range(0, len(sales[s])):
                        if sales[s][i] == "-":
                            sales[s][i] = "0"
                for s in range(0, len(sales)):
                    for i in range(0, len(sales[s])):
                        # print(products[i][p],bricks[s],sales[s][i])
                        # print(products[p][i],bricks[s],sales[s][i])
                        child = []
                        child.append(products[i])
                        child.append(bricks[s])
                        child.append(sales[s][i])
                        child.append("ABD")
                        result.append(child)
                for r in result:
                    for i in item_list:
                        if r[0] == i[0]:
                            r.insert(1, i[1])
                            r.append(i[2])
                            # print(r)
                result = green_team_bricks(result)
                return result
            elif dist_city == "Chakwal":
                result = []
                products = []
                bricks = []
                sales = []
                for x in range(0, len(pdf.pages)):
                    data = pdf.pages[x].extract_table()
                    bricks = data[0][1:-1]
                    for i in range(0, len(bricks)):
                        bricks[i] = re.sub("\n", "", bricks[i])
                        bricks[i] = re.sub(
                            "CHOA SHAYDIAYN BELT", "CHOA SAIDANSHAH", bricks[i]
                        )
                        bricks[i] = re.sub("DHUDIAL BELT", "DHUDYAL", bricks[i])
                        bricks[i] = re.sub("KALAR KAHAR TOWN", "KALAR KAHAR", bricks[i])
                        bricks[i] = re.sub("TALAGANG BELT", "TALAGANG", bricks[i])
                    for i in range(1, len(data) - 5):
                        # print(data[i])
                        if data[i][0] != None:
                            # print('hi')
                            products.append(data[i][0])
                            sales.append(data[i][1:-1])
                            # print(data[i])
                    # print(products)
                    for i in range(0, len(products)):
                        if "JETEPAR 10ML AMP" in products[i]:
                            products[i] = "008999"
                        if "JETEPAR 2ML AMP" in products[i]:
                            products[i] = "004348"
                        if "JETEPAR CAP" in products[i]:
                            products[i] = "002392"
                        if "JETEPAR SYP" in products[i]:
                            products[i] = "002188"
                        if "MAIORAD TAB" in products[i]:
                            products[i] = "012961"
                        if "MAIORAD AMP" in products[i]:
                            products[i] = "009072"
                        if "AFLOXAN TAB" in products[i]:
                            products[i] = "017230"
                        if "AFLOXAN CAP" in products[i]:
                            products[i] = "008376"

                        for k in range(0, len(sales[i])):
                            x = re.split("\n", sales[i][k], 1)
                            sales[i][k] = x[0]
                            if sales[i][k] == "":
                                sales[i][k] = "0"
                    # print(sales)
                    # print(products)

                for s in range(0, len(sales)):
                    for i in range(0, len(sales[s])):
                        child = []
                        child.append(products[s])
                        child.append(bricks[i])
                        child.append(sales[s][i])
                        child.append("CWL")
                        result.append(child)
                for r in result:
                    for i in item_list:
                        if r[0] == i[0]:
                            r.insert(1, i[1])
                            r.append(i[2])
                            # print(r)
                result = green_team_bricks(result)
                return result
            elif dist_city == "Kohat":
                result = []
                new_result = []
                bricks = [
                    "KOHAT 1",
                    "HANGU",
                    "DOABA",
                    "THALL",
                    "KOHAT 2",
                    "KOHAT 3",
                    "ALIZAI AND BAGHAN",
                    "PARACHINAR",
                    "BANDA DAUD SHAH",
                    "LACHI",
                    "GUMBAT",
                    "KOHAT DEVELOPMENT AUTHORITY",
                ]
                products = []
                sales = []

                # ---- extract_table() is unreliable for this PDF, so we don't use it for bricks ----

                for x in range(0, len(pdf.pages)):
                    data = pdf.pages[x].extract_text()
                    data = re.sub("\n", ",", data)
                    data = data.split(",")
                    data = data[9:-3]  # sirf product rows

                    for line in data:
                        tokens = (
                            line.split()
                        )  # koi bhi tadaad ke spaces handle karta hai
                        code = tokens[0]

                        # ---- pehla "pure number" token dhoondein; yahin se values shuru hoti hain ----
                        idx = None
                        for j in range(1, len(tokens)):
                            if re.fullmatch(r"-?\d+(\.\d+)?", tokens[j]):
                                idx = j
                                break

                        name = code + " " + " ".join(tokens[1:idx])
                        values = tokens[idx:]
                        row_sales = values[:-2]  # total qty aur total amount hata dein

                        products.append(name)
                        sales.append(row_sales)

                # ---- product name -> code replacement ----
                for i in range(0, len(products)):
                    if products[i] == "987 AFLOXAN CAP":
                        products[i] = "008376"
                    if products[i] == "983 JETEPAR 10ML INJ":
                        products[i] = "008999"
                    if products[i] == "986 JETEPAR 120ML SYP":
                        products[i] = "002188"
                    if products[i] == "984 JETEPAR 2ML INJ":
                        products[i] = "004348"
                    if products[i] == "052 JETEPAR 2ML INJ NEW":
                        products[i] = "004348"
                    if products[i] == "985 JETEPAR CAP":
                        products[i] = "002392"
                    if products[i] == "973 JETEPAR CAP NEW":
                        products[i] = "002392"
                    if products[i] == "973 JETEPAR SYP NEW":
                        products[i] = "002188"
                    if products[i] == "993 JETEPAR SYP NEW":
                        products[i] = "002188"
                    if products[i] == "989 MAIORAD AMPS":
                        products[i] = "009072"
                    if products[i] == "990 MAIORAD TAB":
                        products[i] = "012961"

                # ---- product x brick nested loop, zero sale skip ----
                for p in range(0, len(products)):
                    for s in range(0, len(sales[p])):
                        if sales[p][s] == "0":
                            continue
                        child = []
                        child.append(products[p])
                        child.append(bricks[s])
                        child.append(sales[p][s])
                        result.append(child)

                # ---- item_list match ----
                for r in range(0, len(result)):
                    for i in item_list:
                        if result[r][0] == i[0]:
                            if result[r][2] != "0":
                                new_result.append(result[r])

                for r in range(0, len(new_result)):
                    for i in item_list:
                        if new_result[r][0] == i[0]:
                            new_result[r].insert(1, i[1])
                            new_result[r].append(i[2])

                for r in new_result:
                    for t in tt_list:
                        if r[2] == t[0]:
                            r.insert(4, t[1])

                new_result = green_team_bricks(new_result)
                return new_result
            elif dist_city == "Jhelum":
                result = []
                products = []
                bricks = []
                sales = []
                sales1 = []
                for x in range(0, len(pdf.pages)):
                    data = pdf.pages[x].extract_table()
                    products = data[0][1:-1]
                    sales = data[1:-1]
                    for i in range(0, len(products)):
                        products[i] = re.sub("\n", "", products[i])
                        if "JETEPAR SYP" in products[i]:
                            products[i] = "002188"
                        if "JETEPAR 2ML INJ" in products[i]:
                            products[i] = "004348"
                        if "JETEPAR 10ML INJ" in products[i]:
                            products[i] = "008999"
                        if "MAIORAD INJ" in products[i]:
                            products[i] = "009072"
                        if "JETEPAR CAP" in products[i]:
                            products[i] = "002392"
                        if "MAIORAD TAB" in products[i]:
                            products[i] = "012961"
                        if "AFLOXAN CAP" in products[i]:
                            products[i] = "008376"
                        if "AFLOXAN TAB" in products[i]:
                            products[i] = "017230"

                    for i in range(0, len(sales)):
                        bricks.append(sales[i][0][4:])
                        if bricks[i][0] == " ":
                            bricks[i] = bricks[i][1:]
                        if bricks[i] == "JHELUM":
                            bricks[i] = "JHELUM JHL"
                        if bricks[i] == "DADYAL & CHAKSWARI":
                            bricks[i] = "DADYAL AND CHAKSWARI"
                        sales[i] = sales[i][1:-1]
                for s in range(0, len(sales)):
                    for i in range(0, len(sales[s])):
                        if sales[s][i] == "-":
                            sales[s][i] = "0"
                for p in range(0, len(bricks)):
                    for s in range(0, len(sales[p])):
                        child = []
                        child.append(products[s])
                        child.append(bricks[p])
                        child.append(sales[p][s])
                        child.append("JHL")
                        result.append(child)

                for r in result:
                    for i in item_list:
                        if r[0] == i[0]:
                            r.insert(1, i[1])
                            r.append(i[2])
                result = green_team_bricks(result)
                return result

            elif dist_city == "Rawalpindi":
                products = []
                sales = []
                bricks = []
                result = []
                new_result = []
                for x in range(0, len(pdf.pages)):
                    data = pdf.pages[x].extract_table()
                    products.append(data[0][1:-1])
                    if x == len(pdf.pages) - 1:
                        for i in range(1, len(data) - 1):
                            sales.append(data[i][1:-1])
                            bricks.append(data[i][0])
                    else:
                        for i in range(1, len(data)):
                            sales.append(data[i][1:-1])
                            bricks.append(data[i][0])
                    if x == 1:
                        for k in range(0, len(bricks)):
                            # bricks[k] = bricks[k][10:]
                            # if bricks[k] == 'MALL ROAD':
                            # 	bricks[k] = 'MALL ROAD RWL'
                            # if bricks[k] == 'CHAKWAL':
                            # 	bricks[k] = 'CHAKWAL RWL'
                            # if bricks[k] == 'ALI PURE FARASH':
                            # 	bricks[k] = 'ALI PUR FARASH'
                            # if bricks[k] == 'BUNNI CHOWK':
                            # 	bricks[k] = 'BANNI CHOWK'
                            # if bricks[k] == 'JAMIA MASJID ROAD':
                            # 	bricks[k] = 'JAMIA MASJID ROAD'
                            # if bricks[k] == 'KHAYABAN-E-SIR \nSYED':
                            # 	bricks[k] = 'KHAYABAN E SIR SYED'
                            # if bricks[k] == 'CHAKLALA SCHEME \nIII':
                            # 	bricks[k] = 'CHAKLALA SCHEME III'
                            # if bricks[k] == 'JAMIA MASJID \nROAD':
                            # 	bricks[k] = 'JAMIA MASJID ROAD'

                            if "1010104" in bricks[k]:
                                bricks[k] = "G-10"
                            if "1010105" in bricks[k]:
                                bricks[k] = "G-11"
                            if "1010112" in bricks[k]:
                                bricks[k] = "I-8"
                            if "1010206" in bricks[k]:
                                bricks[k] = "BARA KAHU"
                            if "1010209" in bricks[k]:
                                bricks[k] = "ALI PUR FARASH"
                            if "1020101" in bricks[k]:
                                bricks[k] = "CHANDNI CHOWK"
                            if "1020102" in bricks[k]:
                                bricks[k] = "SAID PURE ROAD"
                            if "1020103" in bricks[k]:
                                bricks[k] = "BOHAR BAZAR"
                            if "1020111" in bricks[k]:
                                bricks[k] = "SADIQABAD"
                            if "1020201" in bricks[k]:
                                bricks[k] = "SADDAR"
                            if "1020206" in bricks[k]:
                                bricks[k] = "KAMALABAD"
                            if "1020211" in bricks[k]:
                                bricks[k] = "CHAKLALA SCHEME III"
                            if "1020212" in bricks[k]:
                                bricks[k] = "BAHRIA"
                            if "1020216" in bricks[k]:
                                bricks[k] = "MALL ROAD RWL"
                            if "1030201" in bricks[k]:
                                bricks[k] = "WAH CANTT"
                            if "1040101" in bricks[k]:
                                bricks[k] = "ATTOCK"
                            if "1040501" in bricks[k]:
                                bricks[k] = "KAMRA"
                            if "1050101" in bricks[k]:
                                bricks[k] = "GUJAR KHAN"
                            if "1050301" in bricks[k]:
                                bricks[k] = "KAHUTA"
                            if "1010101" in bricks[k]:
                                bricks[k] = "G-8 MARKAZ"
                            if "1010102" in bricks[k]:
                                bricks[k] = "G-9 MARKAZ"
                            if "1010103" in bricks[k]:
                                bricks[k] = "PESHAWAR MORE"
                            if "1010106" in bricks[k]:
                                bricks[k] = "F-10"
                            if "1010107" in bricks[k]:
                                bricks[k] = "F-11"
                            if "1010110" in bricks[k]:
                                bricks[k] = "F-8"
                            if "1010111" in bricks[k]:
                                bricks[k] = "E SECTORS"
                            if "1010113" in bricks[k]:
                                bricks[k] = "I-9"
                            if "1010114" in bricks[k]:
                                bricks[k] = "I-10"
                            if "1010115" in bricks[k]:
                                bricks[k] = "PWD"
                            if "1010116" in bricks[k]:
                                bricks[k] = "HUMMAK"
                            if "1010117" in bricks[k]:
                                bricks[k] = "MANDRA"
                            if "1010118" in bricks[k]:
                                bricks[k] = "B-17"
                            if "1010119" in bricks[k]:
                                bricks[k] = "D-17"
                            if "1010122" in bricks[k]:
                                bricks[k] = "D-12 MARKAZ"
                            if "1010201" in bricks[k]:
                                bricks[k] = "F-6 SUPER MARKET"
                            if "1010202" in bricks[k]:
                                bricks[k] = "F-7 JINNAH SUPER"
                            if "1010203" in bricks[k]:
                                bricks[k] = "MELODY MARKET"
                            if "1010204" in bricks[k]:
                                bricks[k] = "ABPARA MARKET"
                            if "1010207" in bricks[k]:
                                bricks[k] = "BLUE AREA"
                            if "1010301" in bricks[k]:
                                bricks[k] = "CHAK SHAHZAD"
                            if "1020107" in bricks[k]:
                                bricks[k] = "KHAYABAN E SIR SYED"
                            if "1020108" in bricks[k]:
                                bricks[k] = "PIRWADHAI"
                            if "1020109" in bricks[k]:
                                bricks[k] = "DHOKE HASSOO"
                            if "1020110" in bricks[k]:
                                bricks[k] = "DHQ MOHAN PURA"
                            if "1020114" in bricks[k]:
                                bricks[k] = "MURREE ROAD"
                            if "1020116" in bricks[k]:
                                bricks[k] = "SATELLITE TOWN RWL"
                            if "1020203" in bricks[k]:
                                bricks[k] = "PESHAWAR ROAD"
                            if "1020204" in bricks[k]:
                                bricks[k] = "TENCH BHATA"
                            if "1020205" in bricks[k]:
                                bricks[k] = "DHERI"
                            if "1020209" in bricks[k]:
                                bricks[k] = "MORGAH"
                            if "1020213" in bricks[k]:
                                bricks[k] = "NASEERABAD"
                            if "1020214" in bricks[k]:
                                bricks[k] = "MISRIAL ROAD"
                            if "1020215" in bricks[k]:
                                bricks[k] = "LALKURTI"
                            if "1020401" in bricks[k]:
                                bricks[k] = "GULBERG GREEN"
                            if "1030101" in bricks[k]:
                                bricks[k] = "TAXILLA"
                            if "1030301" in bricks[k]:
                                bricks[k] = "HASSAN ABDAL"
                            if "1030401" in bricks[k]:
                                bricks[k] = "TARNOL"
                            if "1040201" in bricks[k]:
                                bricks[k] = "HAZRO"
                            if "1050201" in bricks[k]:
                                bricks[k] = "KALLAR SAYYADAN"
                            if "1050401" in bricks[k]:
                                bricks[k] = "MANDRA"
                            if "1050402" in bricks[k]:
                                bricks[k] = "RAWAT"
                            if "1050403" in bricks[k]:
                                bricks[k] = "DHA"
                            if "1060101" in bricks[k]:
                                bricks[k] = "FATEH JANG"
                            if "1080301" in bricks[k]:
                                bricks[k] = "KOTLI"
                            if "1010401" in bricks[k]:
                                bricks[k] = "GHOURI TOWN"
                            if "1030402" in bricks[k]:
                                bricks[k] = "G-15"
                            if "1010120" in bricks[k]:
                                bricks[k] = "F-17"
                            if "1010121" in bricks[k]:
                                bricks[k] = "F-18"
                            if "1020105" in bricks[k]:
                                bricks[k] = "JAMIA MASJID ROAD"
                            if "1020106" in bricks[k]:
                                bricks[k] = "OPP HFH"
                            if "1020210" in bricks[k]:
                                bricks[k] = "ADYALA ROAD"
                            if "1060301" in bricks[k]:
                                bricks[k] = "PINDI GHEB"
                            if "1020208" in bricks[k]:
                                bricks[k] = "DHAMIAL CHAKRI"
                            if "1020113" in bricks[k]:
                                bricks[k] = "DHOKE KALA KHAN"
                            if "1020119" in bricks[k]:
                                bricks[k] = "MARIR HASSAN"

                for p in range(0, len(products)):
                    for i in range(0, len(products[p])):
                        if "009001" in products[p][i]:
                            products[p][i] = "002188"
                        if "009002" in products[p][i]:
                            products[p][i] = "002392"
                        if "009003" in products[p][i]:
                            products[p][i] = "004348"
                        if "009004" in products[p][i]:
                            products[p][i] = "008999"
                        if "009008" in products[p][i]:
                            products[p][i] = "009072"
                        if "009005" in products[p][i]:
                            products[p][i] = "008376"
                        if "AFLOXAN TAB" in products[p][i]:
                            products[p][i] = "017230"
                        if "MAIORAD TAB" in products[p][i]:
                            products[p][i] = "012961"
                    for s in range(0, len(sales)):
                        for i in range(0, len(sales[s])):
                            if sales[s][i] == "-":
                                sales[s][i] = "0"
                for s in range(0, len(sales)):
                    for i in range(0, len(sales[s])):
                        child = []
                        child.append(products[p][i])
                        child.append(bricks[s])
                        child.append(sales[s][i])
                        result.append(child)
                for r in range(0, len(result)):
                    for i in item_list:
                        if result[r][0] == i[0]:
                            if result[r][2] != "0":
                                new_result.append(result[r])

                for r in range(0, len(new_result)):
                    for i in item_list:
                        if new_result[r][0] == i[0]:
                            new_result[r].insert(1, i[1])
                            new_result[r].append(i[2])
                for r in new_result:
                    for t in tt_list:
                        if r[2] == t[0]:
                            r.insert(4, t[1])
                new_result = green_team_bricks(new_result)
                return new_result

            elif dist_city == "Vehari":
                result = []
                new_result = []

                # -------------------------------------------------------
                # Bricks are read dynamically from each page's header row
                # instead of a hardcoded list (see earlier note), then
                # matched to the correct name via a letter-fingerprint --
                # not a plain reverse -- because some environments extract
                # these header cells with a newline between almost every
                # character (rather than between whole words like in the
                # sample PDF this was built against), which can also
                # transpose adjacent letters (e.g. "THINGI" -> "TIHNIG").
                # Sorting the letters ignores both the extra spaces and
                # any such transposition, so it matches reliably either way.
                # -------------------------------------------------------
                from collections import OrderedDict

                KNOWN_BRICKS = [
                    "48 PUL",
                    "7WAN MEEL",
                    "90 MOR",
                    "ADDA AREY WHEN",
                    "BUREWALA",
                    "CASH",
                    "CHAKRALA",
                    "DALLAN/KAMAND",
                    "DEWAN SAHAB",
                    "DOKOTA",
                    "G.MORE",
                    "GAGOO",
                    "JAMLERA",
                    "KARMPUR",
                    "LUD(VHR)",
                    "LUDDON",
                    "MAILSI",
                    "MANAMORE",
                    "MITROO",
                    "NEW CHOWK",
                    "PAKHI MACHIWAL",
                    "R.TIBA",
                    "SAHUKA",
                    "SHEIKH FAZAL",
                    "THINGI",
                    "TIBA",
                    "VEHARI",
                    "VEH-B",
                    "VIJHIANWALA",
                ]

                def _fingerprint(s):
                    letters = re.sub(r"[^A-Z0-9]", "", s.upper())
                    return "".join(sorted(letters))

                BRICK_FINGERPRINTS = {_fingerprint(b): b for b in KNOWN_BRICKS}

                # If any of the names above don't exactly match your
                # Territory Tree spelling, put the correction here:
                #   "name as it comes out above": "correct Territory Tree name"
                # Example: "90 MOR": "90 MORE",
                BRICK_RENAME = {
                    # "CURRENT NAME": "TERRITORY TREE NAME",
                    "90 MOR": "90 MORR",
                    "DALLAN/KAMAND": "DALLAN / KAMAND",
                    "DEWAN SAHAB": "DEEWAN SAHAB",
                    "GAGOO": "GAGGOO",
                    "KARMPUR": "KARAM PUR",
                    "LUD(VHR)": "LUD VHR",
                    "LUDDON": "LUDDAN",
                    "MAILSI": "MAILSI VIHARI",
                    "MANAMORE": "MANA MORE",
                    "MITROO": "MITRO",
                    "NEW CHOWK": "NEW CHOWK VRI",
                    "PAKHI MACHIWAL": "PAKHY MORE MACHIWAL",
                    "R.TIBA": "RATTA TIBBA",
                    "TIBA": "TIBBA SULTANPUR",
                    "VEHARI": "VEHARI VRI",
                    "G.MORE": "GARHA MORE",
                    "VEHARI GT": "VEHARI VRI GT",
                }

                def decode_brick(raw):
                    if raw is None:
                        return ""
                    raw = str(raw)
                    # best-effort literal decode (used only as a fallback
                    # label if no known brick's fingerprint matches)
                    literal = " ".join(raw.split("\n")).strip()[::-1].strip()
                    fp = _fingerprint(literal)
                    name = BRICK_FINGERPRINTS.get(fp, literal)
                    return BRICK_RENAME.get(name, name)

                all_bricks = []
                sales_by_product = (
                    OrderedDict()
                )  # product name -> accumulated sale values across pages

                for x in range(0, len(pdf.pages)):
                    data = pdf.pages[x].extract_table()
                    if not data:
                        continue
                    header = data[0]

                    # The row-total ("Total" qty/amt) column only appears
                    # on the LAST page of a multi-page report -- earlier
                    # pages have no such trailing column at all. Detect it
                    # instead of assuming a fixed position (this was the
                    # actual cause of the IndexError on the new PDF).
                    has_total_col = (
                        header[-1] is not None and str(header[-1]).strip() == "Total"
                    )
                    end_idx = len(header) - 1 if has_total_col else len(header)

                    page_bricks = [decode_brick(h) for h in header[2:end_idx]]
                    all_bricks.extend(page_bricks)
                    n = len(page_bricks)

                    for row in data[1:]:
                        if not row:
                            continue
                        # skip sub-group Total row (e.g. [None, "Total", ...])
                        # and the grand Total row (e.g. ["Total", None, ...])
                        if row[0] == "Total" or row[1] == "Total" or row[1] is None:
                            continue
                        product_name = str(row[1]).strip()
                        row_vals = list(row[2:end_idx])
                        while len(row_vals) < n:
                            row_vals.append("0")
                        row_vals = row_vals[:n]
                        # products repeat with the SAME name on every page
                        # (unlike Bhakkar's new format) so sales just
                        # accumulate onto the same product key here.
                        sales_by_product.setdefault(product_name, []).extend(row_vals)

                products = list(sales_by_product.keys())
                sales = [sales_by_product[p] for p in products]
                bricks = all_bricks

                for s in range(0, len(sales)):
                    for i in range(0, len(sales[s])):
                        if sales[s][i] in ("-", None, ""):
                            sales[s][i] = "0"

                # Matched with "in" (substring) instead of re.sub, because
                # the new report appends a price suffix to the product name
                # (e.g. "JETEPAR CAP 20s {TP 199.10") -- re.sub would only
                # replace the matched part and leave "002392 {TP 199.10"
                # behind, which would then never match item_list.
                NAME_TO_CODE = {
                    "JETEPAR CAP 20s": "002392",
                    "JETEPAR.10ML ING 5s": "008999",
                    "JETEPAR SYP 120ml": "002188",
                    "JETEPAR.2ML INJ 10s": "004348",
                    "MAIORAD INJ 6s": "009072",
                    "MOXILIUM SUS 125MG": "006783",  # new product on this report, wasn't handled before
                }
                for i in range(0, len(products)):
                    for name, code in NAME_TO_CODE.items():
                        if name in products[i]:
                            products[i] = code
                            break

                for p in range(0, len(products)):
                    for s in range(0, len(sales[p])):
                        if bricks[s] == "":
                            continue
                        child = []
                        child.append(products[p])
                        child.append(bricks[s])
                        child.append(sales[p][s])
                        result.append(child)

                for r in range(0, len(result)):
                    for i in item_list:
                        if result[r][0] == i[0]:
                            if result[r][2] != "0":
                                new_result.append(result[r])

                for r in range(0, len(new_result)):
                    for i in item_list:
                        if new_result[r][0] == i[0]:
                            new_result[r].insert(1, i[1])
                            new_result[r].append(i[2])
                for r in new_result:
                    for t in tt_list:
                        if r[2] == t[0]:
                            r.insert(4, t[1])

                new_result = green_team_bricks(new_result)
                return new_result
            elif dist_city == "Larkana":
                result = []
                bricks = []
                bricks3 = []
                products = []
                sales = []
                sales2 = []

                for x in range(len(pdf.pages)):
                    data = pdf.pages[x].extract_tables()
                    page_bricks = data[0][0]  # bricks from the first table

                    if x == 0:
                        bricks1 = page_bricks[1:]  # skip headers
                        products2 = data[1][0:-4]
                        for row in products2:
                            products.append(row[0])
                            sales.append(row)
                    if x == 1:
                        bricks3 = page_bricks[1:-2]  # remove last 2 if unnecessary
                        for table in data:
                            for k in range(2, len(table) - 4):
                                sales2.append(table[k])

                # Combine all bricks
                bricks = bricks1 + bricks3

                # Merge sales1 and sales2
                for i in range(len(sales)):
                    if i < len(sales2) and sales[i][0] == sales2[i][0]:
                        sales[i] = sales[i] + sales2[i][1:-2]  # merge with exclusion
                        sales[i] = sales[i][1:]  # remove duplicate product name

                # Replace empty values with '0'
                for s_row in sales:
                    for i in range(len(s_row)):
                        if not s_row[i]:
                            s_row[i] = "0"

                # Map product names to codes
                for i in range(len(products)):
                    if "MAIORAD INJ 6S" in products[i]:
                        products[i] = "009072"
                    elif "JETEPAR 10.ML INJ 5S" in products[i]:
                        products[i] = "008999"
                    elif "JETEPAR SYRUP 112.ML" in products[i]:
                        products[i] = "002188"
                    elif "JETEPAR INJ 2ML 10S" in products[i]:
                        products[i] = "004348"
                    elif "JETEPAR CAP 20S" in products[i]:
                        products[i] = "002392"

                # Clean up bricks names
                for i in range(len(bricks)):
                    brick = bricks[i]
                    brick = re.sub("BAHRM", "BAHRAM", brick)
                    brick = re.sub("CIVIL", "CIVIL HOSPITAL LARKANA", brick)
                    brick = re.sub("DAKHN", "DAKAN", brick)
                    brick = re.sub("KAMBR", "QAMBAR", brick)
                    brick = re.sub("NAUDR", "NAUDERO", brick)
                    brick = re.sub("RATOD", "RATO DERO", brick)
                    brick = re.sub("S.Z.H", "SHAIKH ZAYED HOSPITAL", brick)
                    brick = re.sub("B-ROD", "BAKRANI ROAD", brick)
                    brick = re.sub("CATLE", "CATTLE COLONY", brick)
                    brick = re.sub("POLIC", "POLICE SHOPING CENTRE", brick)
                    brick = re.sub("SHDKT", "SHAHDADKOT", brick)
                    brick = re.sub("NASIR", "NASIRABAD", brick)
                    brick = re.sub("EM-RO", "EMPIRE ROAD", brick)
                    brick = re.sub("LAHOR", "LAHORI MUHALLA", brick)
                    brick = re.sub("GAR-Y", "GARI YASEEN", brick)
                    brick = re.sub("ARIJA", "ARIJA", brick)
                    brick = re.sub("ARZ-B", "ARZI BHUTTO", brick)
                    brick = re.sub("BKRNI", "BAKRANI ROAD", brick)
                    brick = re.sub("BANGU", "BANGULDERO", brick)
                    brick = re.sub("BRO-C", "BERO CHANDIO", brick)
                    brick = re.sub("BHANS", "BHAN SYEDABAD", brick)
                    brick = re.sub("DHAMR", "DHAMRAH", brick)
                    brick = re.sub("GAJIK", "GAJI KHUHAWAR", brick)
                    brick = re.sub("GRELO", "GARELO", brick)
                    brick = re.sub("GAR-K", "GARI KHUDA BUX", brick)
                    brick = re.sub("DADU", "DADU LARKANA", brick)
                    brick = re.sub("HAKIM", "HAKIM SHAH", brick)
                    brick = re.sub("HATI", "HATTI", brick)
                    brick = re.sub("KN-SH", "KHAIRPUR NATHAN SHAH", brick)
                    brick = re.sub("KAMBR", "KAMBER", brick)
                    brick = re.sub("KHARO", "KHAIRO DERO", brick)
                    brick = re.sub("KHANP", "KHANPUR", brick)
                    brick = re.sub("ALLAH", "ALLAH ABAD", brick)
                    brick = re.sub("GAJAN", "GAJAN PUR CHOWK", brick)
                    brick = re.sub("JALIS", "JAILES BAZAR", brick)
                    brick = re.sub("LADIE", "LADIES JAIL", brick)
                    brick = re.sub("M-CHK", "MIROKHAN CHOWK", brick)
                    brick = re.sub("NA-CH", "NAUDERO CHOWK", brick)
                    brick = re.sub("NA-RO", "NAUDERO ROAD", brick)
                    brick = re.sub("NAZAR", "NAZAR MUHALLA", brick)
                    brick = re.sub("NISHT", "NISHTAR ROAD", brick)
                    brick = re.sub("OLD-B", "OLD.BUS.S", brick)
                    brick = re.sub("PK-CH", "PAKISTANI CHOWK", brick)
                    brick = re.sub("PHUL", "PHULL ROAD", brick)
                    brick = re.sub("RAMAT", "RAHMAT PUR", brick)
                    brick = re.sub("SACHA", "SACHAL COLONY", brick)
                    brick = re.sub("STATO", "STATION ROAD", brick)
                    brick = re.sub("MADJI", "MADEJI", brick)
                    brick = re.sub("MAHOT", "MAHOTA", brick)
                    brick = re.sub("MROKN", "MIROKHAN", brick)
                    brick = re.sub("PHULJ", "PHULJI", brick)
                    brick = re.sub("PIARO", "PIAROGOTH", brick)
                    brick = re.sub("QUBO", "QUBO SAEED KHAN", brick)
                    brick = re.sub("RADHN", "RADHAN", brick)
                    brick = re.sub("SAJWL", "SAJAWAL", brick)
                    brick = re.sub("SEWHN", "SEWHAN", brick)
                    bricks[i] = brick

                # Final assembly
                for p in range(len(products)):
                    for s in range(len(sales[p])):
                        child = []
                        child.append(products[p])
                        # Use brick if available, else default to 'LKA'
                        brick_name = (
                            bricks[s] if s < len(bricks) and bricks[s] else "LKA"
                        )
                        child.append(brick_name)
                        child.append(sales[p][s])
                        child.append("LRK")
                        result.append(child)

                # Add item info from item_list
                for r in result:
                    for i in item_list:
                        if r[0] == i[0]:
                            r.insert(1, i[1])
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

                for x in range(0, len(pdf.pages)):
                    data = pdf.pages[x].extract_table()
                    products = data[0][1:]
                    products.remove("Total Amount")
                    for p in range(0, len(products)):
                        if "006002" in products[p]:
                            products[p] = "028729"
                        if "006003" in products[p]:
                            products[p] = "005425"
                        if "006004" in products[p]:
                            products[p] = "023906"
                        if "006009" in products[p]:
                            products[p] = "038426"
                        if "006011" in products[p]:
                            products[p] = "008908"
                        if "006012" in products[p]:
                            products[p] = "006782"
                        if "006013" in products[p]:
                            products[p] = "006783"
                        if "006014" in products[p]:
                            products[p] = "012649"
                        if "006015" in products[p]:
                            products[p] = "019133"
                        if "006017" in products[p]:
                            products[p] = "032255"
                        if "006020" in products[p]:
                            products[p] = "028727"
                        if "006021" in products[p]:
                            products[p] = "024819"
                        if "006022" in products[p]:
                            products[p] = "028728"
                        if "006023" in products[p]:
                            products[p] = "029327"
                        if "006024" in products[p]:
                            products[p] = "026920"
                        if "006025" in products[p]:
                            products[p] = "007018"
                        if "006026" in products[p]:
                            products[p] = "006406"
                        if "006041" in products[p]:
                            products[p] = "008376"
                        if "006042" in products[p]:
                            products[p] = "017230"
                        if "006043" in products[p]:
                            products[p] = "008999"
                        if "006044" in products[p]:
                            products[p] = "004348"
                        if "006045" in products[p]:
                            products[p] = "002392"
                        if "006046" in products[p]:
                            products[p] = "002188"
                        if "006047" in products[p]:
                            products[p] = "009072"
                        if "006048" in products[p]:
                            products[p] = "012961"
                        if "006064" in products[p]:
                            products[p] = "035294"
                        if "006065" in products[p]:
                            products[p] = "035295"
                        if "006068" in products[p]:
                            products[p] = "032259"
                        if "006069" in products[p]:
                            products[p] = "081838"
                        if "006070" in products[p]:
                            products[p] = "081274"
                        if "006071" in products[p]:
                            products[p] = "008909"
                        if "006016" in products[p]:
                            products[p] = "016654"
                        if "006005" in products[p]:
                            products[p] = "031037"
                        # if '' in products[p]:
                        #     product[p] = ''
                    if x == len(pdf.pages) - 1:
                        for b in range(1, len(data) - 1):
                            brick.append(data[b][0])

                        for s in range(1, len(data) - 1):
                            sales.append(data[s][1:-1])
                    else:
                        for b in range(1, len(data)):
                            brick.append(data[b][0])

                        for s in range(1, len(data)):
                            sales.append(data[s][1:-1])
                # print(bricks)
                for s in sales:
                    for i in range(0, len(s)):
                        if s[i] == "-":
                            s[i] = "0"
                            # print(s[i])
                # print(sales)
                for i in range(0, len(brick)):
                    bricks.append(brick[i][10:])
                    bricks[i] = re.sub("\n", "", bricks[i])
                    bricks[i] = re.sub("QUDRAT ELAHI MARKET", "QUDRAT ELAHI", bricks[i])
                    bricks[i] = re.sub("AL HAYAT MRKET", "AL HAYAT MARKET", bricks[i])
                    bricks[i] = re.sub("GHULAM SAID PLAZA", "GHULAM SAID", bricks[i])
                    bricks[i] = re.sub("SOEKARNO SQAURE", "SOEKARNO SQUARE", bricks[i])
                    bricks[i] = re.sub(
                        "KHYBER MEDICAL CENTR", "KHYBER MEDICAL CENTER", bricks[i]
                    )
                    bricks[i] = re.sub(
                        "RAHEEM MEDICAL", "RAHEEM MEDICAL CENTER", bricks[i]
                    )
                    bricks[i] = re.sub("BAZAR-E-KALAN", "BAZAR E KALAN", bricks[i])
                    bricks[i] = re.sub("K.T.H", "KHYBER TEACHING HOSPITAL", bricks[i])
                    bricks[i] = re.sub("LRH", "LADY READING HOSPITAL", bricks[i])
                    bricks[i] = re.sub(
                        "H.A.M.C", "HAYATABAD MEDICAL COMPLEX", bricks[i]
                    )
                    bricks[i] = re.sub("BADA BAIR", "BADABER", bricks[i])
                    bricks[i] = re.sub("NOTHIA", "NOTHIA QADEEM", bricks[i])
                    bricks[i] = re.sub(
                        "KHATAK MEDICAL CENTR", "KHATAK MEDICAL CENTER", bricks[i]
                    )
                    bricks[i] = re.sub(
                        "AL SHIFA SURG CENTER", "AL SHIFA SURGICAL CENTER", bricks[i]
                    )
                    bricks[i] = re.sub("KHUSHAAL CENTER", "KHUSHAL CENTER", bricks[i])
                    bricks[i] = re.sub(
                        "MOHMAND MEDICAL CENT", "MOHMAND MEDICAL CENTER", bricks[i]
                    )
                    bricks[i] = re.sub(
                        "RAHEEM MEDICAL CENTER CENTR",
                        "RAHEEM MEDICAL CENTER",
                        bricks[i],
                    )
                    bricks[i] = re.sub("SIKANDAR PURA", "SIKANDER PURA", bricks[i])
                    bricks[i] = re.sub(
                        "NASEER TEACHING HOSP", "NASEER TEACHING HOSPITAL", bricks[i]
                    )
                    bricks[i] = re.sub("TARANGZAI", "TAURANG ZAI", bricks[i])
                    bricks[i] = re.sub("FAQIR ABAD", "FAQIRABAD", bricks[i])
                    bricks[i] = re.sub(
                        "HILAL-E-AHMER BUILDI", "HILAL-E-AHMAR BUILDING", bricks[i]
                    )
                    bricks[i] = re.sub("KOHAT RAOD", "KOHAT ROAD", bricks[i])
                    bricks[i] = re.sub("SHANAGLA MARKET", "SHANGLA MARKET", bricks[i])
                    bricks[i] = re.sub(
                        "SHANAGLA MARKET GT", "SHANGLA MARKET GT", bricks[i]
                    )
                    bricks[i] = re.sub("AL MANSOOR MARKET", "AL MANSOOR", bricks[i])
                    bricks[i] = re.sub("NISHTER ABAD GT", "NISHTERABAD GT", bricks[i])
                    bricks[i] = re.sub("NISHTER ABAD", "NISHTERABAD", bricks[i])
                    bricks[i] = re.sub("PAJJAGI ROAD", "PAJAGI ROAD", bricks[i])
                    bricks[i] = re.sub(
                        "CHARSADDA ROAD GT", "CHARSADDA ROAD GT", bricks[i]
                    )
                    bricks[i] = re.sub("CHARSADDA ROAD", "CHARSADA ROAD", bricks[i])
                    bricks[i] = re.sub("D A O R T G", "DAORT G", bricks[i])
                    bricks[i] = re.sub(
                        "ABASEEN MEDICAL CENT", "ABASEEN MEDICAL CENTER", bricks[i]
                    )
                    bricks[i] = re.sub(
                        "MOLVI GEE HOSPITAL", "MOLVI JEE HOSPITAL", bricks[i]
                    )

                # print(products)
                for s in range(0, len(sales)):
                    for i in range(0, len(sales[s])):
                        try:
                            child = []
                            child.append(products[i])  # Product code
                            child.append(bricks[s])  # Brick name
                            child.append(sales[s][i])  # Sale qty or price
                            result.append(child)
                        except IndexError:
                            print(
                                f"⚠️ IndexError at s={s}, i={i}, len(products)={len(products)}, len(sales[{s}])={len(sales[s])}, len(bricks)={len(bricks)}"
                            )
                        continue

                for r in range(0, len(result)):
                    for i in item_list:
                        if result[r][0] == i[0]:
                            if result[r][2] != "0":
                                new_result.append(result[r])

                for r in range(0, len(new_result)):
                    for i in item_list:
                        if new_result[r][0] == i[0]:
                            new_result[r].insert(1, i[1])
                            new_result[r].append(i[2])

                for r in new_result:
                    for t in tt_list:
                        if r[2] == t[0]:
                            r.insert(4, t[1])

                new_result = green_team_bricks(new_result)
                return new_result
            elif dist_city == "Quetta":
                result = []
                new_result = []
                products = []

                bricks = [
                    "ALAM KHAN CHOWK",
                    "ALAMDAR ROAD",
                    "BARORI",
                    "QUETTA CANTONMENT",
                    "INSTITUTION",
                    "JINNAH ROAD KANDHARI BAZAR",
                    "HUDA SPINI ROAD",
                    "SABZAL ROAD",
                    "SIRKI ROAD GAWALMANDI CHOWK",
                    "LIAQAT BAZAR ARCHAR_FJ ROAD",
                    "MEKANGI ROAD",
                    "MISSION ROAD",
                    "OFF JINNAH ROAD",
                    "PASHTUN ABAD",
                    "PRINCE ROAD",
                    "SARIAB ROAD",
                    "SATELLITE TOWN QTA",
                    "ZARGON ROAD",
                    "WHOLESALE QTA",
                    "CHAMAN",
                    "DALBANDIN",
                    "DUKKI",
                    "QILLA SIAFULLAH",
                    "KALAT",
                    "KHANOZAI",
                    "KHARAN",
                    "KHUZDAR",
                    "KUCHLACK",
                    "LORALAI",
                    "M_BAG",
                    "MASTUNG",
                    "MACHH",
                    "NOSHKI",
                    "PISHIN",
                    "SANJAWI",
                    "SARANAN",
                    "SIBI",
                    "ZHOB",
                    "ZIARAT",
                ]
                sales = []
                sales1 = []
                sales2 = []
                sales3 = []
                for x in range(0, len(pdf.pages)):
                    data = pdf.pages[x].extract_table()
                    sales = data[2:-1]
                    for i in range(0, len(sales)):
                        products.append(sales[i][0])
                        sales1.append(sales[i][2:-2])
                        if products[i] == "JETEPAR  SYP":
                            products[i] = "002188"
                        if products[i] == "JETEPAR INJ. 2CC":
                            products[i] = "004348"
                        if products[i] == "JETEPAR INJ. 10CC":
                            products[i] = "008999"
                        if products[i] == "MAIORAD INJ":
                            products[i] = "009072"
                        if products[i] == "JETEPAR CAPS":
                            products[i] = "002392"
                        if products[i] == "MAIORAD TAB":
                            products[i] = "012961"
                        if products[i] == "AFLOXAN CAPS":
                            products[i] = "008376"
                        if products[i] == "AFLOXAN TAB":
                            products[i] = "017230"
                for i in range(0, len(sales1)):
                    sales2 = []
                    for k in range(0, len(sales1[i])):
                        if sales1[i][k] != None:
                            sales2.append(sales1[i][k])
                    sales3.append(sales2)
                    sales3[i].pop(19)
                for s in range(0, len(sales3)):
                    for i in range(0, len(sales3[s])):
                        if sales3[s][i] == "":
                            sales3[s][i] = "0"
                for p in range(0, len(products)):
                    for s in range(0, len(sales3[p])):
                        child = []
                        child.append(products[p])
                        child.append(bricks[s])
                        child.append(sales3[p][s])
                        result.append(child)
                for r in range(0, len(result)):
                    for i in item_list:
                        if result[r][0] == i[0]:
                            if result[r][2] != "0":
                                new_result.append(result[r])

                for r in range(0, len(new_result)):
                    for i in item_list:
                        if new_result[r][0] == i[0]:
                            new_result[r].insert(1, i[1])
                            new_result[r].append(i[2])
                for r in new_result:
                    for t in tt_list:
                        if r[2] == t[0]:
                            r.insert(4, t[1])
                new_result = green_team_bricks(new_result)
                return new_result
            elif dist_city == "Jacobabad":
                result = []
                products = []
                sales = []

                page = pdf.pages[0]
                table = page.extract_table()

                # ----- Bricks: read from the header TEXT line, not from the table -----
                # (extract_table() sometimes fails to detect the "ITEM <bricks...>
                # TTL QTY TTL AMT" header as its own row -- on some report
                # layouts that header line gets skipped by pdfplumber's table
                # detection entirely, and table[0] silently becomes the FIRST
                # PRODUCT ROW instead. That's exactly what was happening with
                # the old-format PDF: bricks were being built from a random
                # product's sale numbers instead of the real brick names.
                # Reading the header straight from the page text is
                # layout-independent and works on both old and new formats.)
                header_line = None
                for line in page.extract_text().split("\n"):
                    parts = line.strip().split()
                    if parts and parts[0] == "ITEM" and parts[-1] in ("QTY", "AMT"):
                        header_line = line.strip()
                        break
                if header_line is None:
                    return []  # couldn't find a header on this page

                header_tokens = header_line.split()[1:]  # drop leading "ITEM"
                bricks = []
                i = 0
                while i < len(header_tokens):
                    tok = header_tokens[i]
                    if (
                        tok == "TTL"
                        and i + 1 < len(header_tokens)
                        and header_tokens[i + 1] in ("QTY", "AMT")
                    ):
                        i += 2  # skip "TTL QTY" / "TTL AMT" -- not a brick column
                        continue
                    bricks.append(tok)
                    i += 1

                BRICK_RENAME = {
                    "DERA A": "DERA ALLAH YAR",
                    "DERA M": "DERA MURAD JAMALI",
                    "KANDH": "KANDHKOT",
                    "KASHMO": "KASHMORE",
                    "USTA M": "USTA MUHAMMAD",
                    "CINEM": "CINEMA ROAD",
                    "DAY": "DERA ALLAH YAR",
                    "DMJ": "DERA MURAD JAMALI",
                    "GPUR": "GHOUS PUR",
                    "KKOT": "KANDHKOT",
                    "KSM": "KASHMORE",
                    "MNQUA": "MUNICIPAL/QUAID E AZAM ROAD",
                    "MUNCP": "MUNICIPAL",
                    "QTA": "QUETTA ROAD",
                    "TWANI": "TANDO WANI",
                    "UTM": "USTA MUHAMMAD",
                    "W/S": "WHOLE SALE",
                    "GWAH": "GANDA WAH",
                    "JCD/Q": "QUAID E AZAM ROAD",
                    "JCD/WH": "WHOLE SALE",
                    "CIVL": "CIVIL HOSPITAL JCD",
                    "KPUR": "KHAIRPUR JCD",
                }
                bricks = [BRICK_RENAME.get(b, b) for b in bricks]
                # NOTE: "THULL" has no rename rule above and passes through
                # as-is. If it doesn't exactly match your Territory Tree
                # name, tell me the correct name and I'll add it.

                # ----- Products & Sales: skip header + any non-product row -----
                for row in table:
                    if not row or not row[0]:
                        continue

                    first_col = row[0].strip().upper()
                    if (
                        first_col == "ITEM"
                        or first_col.startswith("TTL")
                        or first_col.startswith("G TTL")
                    ):
                        continue

                    if all(v is None or str(v).strip() == "" for v in row[1:]):
                        continue

                    product = row[0].strip()
                    row_sales = row[1:-1]  # drop the trailing totals column
                    # (if a report has BOTH a "TTL QTY" and a "TTL AMT" column
                    # per row, this only drops the last one -- but the loop
                    # below only ever reads the first len(bricks) values, so
                    # any extra leftover totals value is simply never used)
                    products.append(product)
                    sales.append(row_sales)

                for p in range(0, len(products)):
                    if "JETEPAR CAP" in products[p]:
                        products[p] = "002392"
                    if "JETEPAR INJ 10" in products[p]:
                        products[p] = "008999"
                    if "JETEPAR INJ 2" in products[p]:
                        products[p] = "004348"
                    if "JETEPAR SYP" in products[p]:
                        products[p] = "002188"
                    if "MAIORAD INJ" in products[p]:
                        products[p] = "009072"

                for s in range(0, len(sales)):
                    for i in range(0, len(sales[s])):
                        if sales[s][i] in ("", None):
                            sales[s][i] = "0"

                # products aur sales same length ke hain
                for p_index, product in enumerate(products):
                    row_sales = sales[p_index]  # sales row of current product

                    for b_index, brick in enumerate(bricks):
                        sale_value = (
                            row_sales[b_index] if b_index < len(row_sales) else "0"
                        )
                        result.append([product, brick, sale_value])

                for r in result:
                    for i in item_list:
                        if r[0] == i[0]:
                            r.insert(1, i[1])
                            r.append(i[2])
                for r in result:
                    for t in tt_list:
                        if r[2] == t[0]:
                            r.insert(4, t[1])
                result = green_team_bricks(result)
                return result
            elif dist_city == "Layyah":
                result = []
                products = []
                bricks = [
                    "LAYYAH LYH",
                    "CHOWK AZAM",
                    "KAROR LAL ESAN",
                    "FATEHPUR",
                    "CHOWK MUNDA",
                    "JAMAN SHAH",
                    "KOT SULTAN",
                    "PAHARPUR",
                    "EHSAN PUR",
                    "DAIRA DIN PANAH",
                    "LADHANA",
                    "KOT ADDU",
                    "SANAWAN LYH",
                    "CHAUBARA LYH",
                    "MISC LYH",
                ]
                sales = []
                first_table_end = 0
                for x in range(0, len(pdf.pages)):
                    data = pdf.pages[x].extract_text()
                    data = re.sub("\n", "$", data)
                    data = data.split("$")
                    data = data[10:-15]
                    for i in range(0, len(data)):
                        if data[i] == "Group Name : GREEN":
                            second_table_start = i
                            first_table_end = i - 8
                for k in range(0, len(data)):
                    if k <= first_table_end or k > second_table_start:
                        data[k] = re.sub("[(]", "$", data[k])
                        # print(data[k])
                        data[k] = data[k].split("$")
                        products.append(data[k][0][:-1])
                        data[k] = re.sub("\s+", "$", data[k][1])
                        data[k] = data[k].split("$")
                        sales.append(data[k][1:-2])
                for i in range(0, len(products)):
                    if products[i] == "JETEPAR  10ML  AMP":
                        products[i] = "008999"
                    if products[i] == "JETEPAR  2ML  AMP":
                        products[i] = "004348"
                    if products[i] == "JETEPAR  CAP":
                        products[i] = "002392"
                    if products[i] == "JETEPAR  SYP":
                        products[i] = "002188"
                    if products[i] == "MAIORAD  AMP":
                        products[i] = "009072"
                    if products[i] == "METRONIDAZOLE 400MG TAB":
                        products[i] = "081274"
                    if products[i] == "CYANORIN  FORTE  AMP":
                        products[i] = "005425"
                    if products[i] == "MOXILIUM  SYP  125MG":
                        products[i] = "006783"
                    if products[i] == "MOXILIUM  SYP  250MG":
                        products[i] = "012649"
                    if products[i] == "MOXILIUM  DROPS":
                        products[i] = "006782"
                    if products[i] == "VIGROL  FORTE  TAB":
                        products[i] = "007018"
                    if products[i] == "PC-LAC  SYP":
                        products[i] = "019133"
                    if products[i] == "VIKONON  FORTE  SYP":
                        products[i] = "006406"
                    if products[i] == "SUPRACEF  SUSP  100MG":
                        products[i] = "024819"
                for i in range(len(sales)):
                    for k in range(len(sales[i])):
                        if sales[i][k] == "-":
                            sales[i][k] = "0"
                for p in range(0, len(products)):
                    for s in range(0, len(sales[p])):
                        child = []
                        child.append(products[p])
                        child.append(bricks[s])
                        child.append(sales[p][s])
                        result.append(child)
                for r in result:
                    for i in item_list:
                        if r[0] == i[0]:
                            r.insert(1, i[1])
                            r.append(i[2])
                for r in result:
                    for t in tt_list:
                        if r[2] == t[0]:
                            r.insert(4, t[1])
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
                is_team_section = False  # Renamed for clarity

                for x in range(len(pdf.pages)):
                    data = pdf.pages[x].extract_text()
                    bricks = pdf.pages[x].extract_table()
                    if not bricks or not bricks[0]:
                        continue
                    bricks = bricks[0]
                    bricks = bricks[1:-1]  # skip first (Packing) and last (T.Qty.)

                    # Replace all empty or blank strings with default value
                    bricks = [
                        "TOBA TEK SINGH TTS" if not b or not b.strip() else b.strip()
                        for b in bricks
                    ]
                    brick = bricks  # assign cleaned bricks list

                    data = re.sub("\n", "$", data)
                    data = data.split("$")

                    for i in range(len(data)):
                        # Detect start of Blue or Green team section
                        if re.search(r"(BLUE TEAM|GREEN TEAM)", data[i - 1]):
                            is_team_section = True
                        # Detect end of product block
                        if re.search(r"Group Total", data[i]):
                            is_team_section = False
                        if is_team_section:
                            sales.append(data[i])

                for i in range(len(sales)):
                    sales[i] = re.sub("'S", "$", sales[i])
                    sales[i] = re.sub("ML", "$", sales[i])
                    sales[i] = re.sub("AMP", "$", sales[i])
                    sales[i] = sales[i].split("$")
                    products.append(sales[i][0])
                    sales[i] = sales[i][-1][1:]
                    sales[i] = re.sub(r"\s+", "$", sales[i])
                    sales[i] = sales[i].split("$")
                    # Remove unwanted data before brick-wise quantities
                    s_index = next(
                        (idx for idx, val in enumerate(sales[i]) if val.endswith("S")),
                        -1,
                    )
                    if s_index != -1:
                        sales[i] = sales[i][s_index + 1 :]

                    # Now ensure exactly 15 values
                    if len(sales[i]) < len(brick):
                        # Pad with "0" if missing values
                        sales[i] += ["0"] * (len(brick) - len(sales[i]))
                    elif len(sales[i]) > len(brick):
                        # Trim extra values
                        sales[i] = sales[i][: len(brick)]

                    print(sales[i])

                # Map product names to item codes
                for i in range(len(products)):
                    if "JETEPAR CAP" in products[i]:
                        products[i] = "002392"
                    if "JETEPAR 10" in products[i]:
                        products[i] = "008999"
                    if "JETEPAR 2" in products[i]:
                        products[i] = "004348"
                    if "JETEPAR SYP" in products[i]:
                        products[i] = "002188"
                    if "MAIORAD  3" in products[i]:
                        products[i] = "009072"
                    if "MAIORAD TAB" in products[i]:
                        products[i] = "012961"
                    if "MOXILIUM  CAP" in products[i]:
                        products[i] = "006784"  # Add correct codes if needed
                    if "MOXILIUM SYP 125MG" in products[i]:
                        products[i] = "006783"
                    if "MOXILIUM SYP 250MG" in products[i]:
                        products[i] = "012649"
                    if "P.C.LAC SYP" in products[i]:
                        products[i] = "019133"
                    if "TRAMAGESIC" in products[i]:
                        products[i] = "026920"
                    if "METRONIDAZOLE" in products[i]:
                        products[i] = "081274"

                # Fix brick names
                for i in range(len(brick)):
                    if brick[i] == "GOJRA":
                        brick[i] = "GOJRA TTS"
                    if brick[i] == "KAMAL":
                        brick[i] = "KAMAL CHOWK"
                    if brick[i] == "PIR M":
                        brick[i] = "PIR MAHAL"
                    if brick[i] == "RAJAN":
                        brick[i] = "RAJANA"
                    if brick[i] == "S/WAL":
                        brick[i] = "SAHIWAL TTS"
                    if brick[i] == "TOBA":
                        brick[i] = "TOBA TEK SINGH TTS"

                # Build result
                for p in range(len(products)):
                    for s in range(len(sales[p])):
                        child = []
                        child.append(products[p])  # item code
                        child.append(brick[s])  # brick name
                        child.append(sales[p][s])  # quantity
                        result.append(child)

                # Enrich result with item_list info
                for r in result:
                    for i in item_list:
                        if r[0] == i[0]:
                            r.insert(1, i[1])  # item name
                            r.append(i[2])  # item group

                # Enrich result with team info
                for r in result:
                    for t in tt_list:
                        if r[2] == t[0]:  # match on quantity or brick code if needed
                            r.insert(4, t[1])

                result = green_team_bricks(result)  # Apply final custom filtering
                return result
            elif dist_city == "Dera Ghazi Khan":
                result = []
                products = []
                bricks = []
                new_result = []
                sales = []
                for x in range(0, len(pdf.pages)):
                    data = pdf.pages[x].extract_table()
                    brick = data[0]
                    data = data[1:7]

                    for i in range(2, len(brick)):
                        brick[i] = brick[i].replace("\n", "")
                        brick[i] = brick[i][::-1]
                        # print(brick[i])
                        if "BALAK HSARWAR" in brick[i]:
                            bricks.append("BALAKH SARWAR")
                        if "CHOTIT" in brick[i]:
                            bricks.append("CHOTI")
                        if "DJAAL" in brick[i]:
                            bricks.append("DAJAL")
                        if "FAREED YBAZAR" in brick[i]:
                            bricks.append("FAREEDY BAZAR")
                        if "FAIZ LPUR" in brick[i]:
                            bricks.append("FAZIL PUR")
                        if "GADDIA" in brick[i]:
                            bricks.append("GADDAI")
                        if "H IJAPUR" in brick[i]:
                            bricks.append("HAJIPUR")
                        if "JAMPUR" in brick[i]:
                            bricks.append("JAMPUR")
                        if "JHO KUTRAH" in brick[i]:
                            bricks.append("JHOK UTRA")
                        if "KALA" in brick[i]:
                            bricks.append("KALA")
                        if "KO TCHUTTA" in brick[i]:
                            bricks.append("KOT CHUTTA")
                        if "KO TMETHAN" in brick[i]:
                            bricks.append("KOT MITHAN")
                        if "KOTL AMUGHLAN" in brick[i]:
                            bricks.append("KOTLA MUGHLAN")
                        if "MAN AAHMDAIN" in brick[i]:
                            bricks.append("MANA AHMDANI")
                        if "MOHAMMA DPUR" in brick[i]:
                            bricks.append("MOHAMMAD PUR")
                        if "NEDAORLLOC WEG E" in brick[i]:
                            bricks.append("NEW COLLEGE ROAD")
                        if "PEE RAAIDL" in brick[i]:
                            bricks.append("PIR ADIL")
                        if "IP RQATTAL" in brick[i]:
                            bricks.append("PIR QATAL")
                        if "QUIAAOR-E-DDAZA M" in brick[i]:
                            bricks.append("QUAID-E-AZAM ROAD")
                        if "RIALWA YROAD" in brick[i]:
                            bricks.append("RAILWAY ROAD DGK")
                        if "RJAA NPUR" in brick[i]:
                            bricks.append("RAJANPUR")
                        if "SADA RBAZAR" in brick[i]:
                            bricks.append("SADAR BAZAR")
                        if "SAK IHSARWAR" in brick[i]:
                            bricks.append("SAKHI SARWAR")
                        if "SHADA NLUND" in brick[i]:
                            bricks.append("SHADAN LUND")
                        if "SHA HSADA RIDN" in brick[i]:
                            bricks.append("SHAH SADAR DIN")
                        if "TAUNSA" in brick[i]:
                            bricks.append("TAUNSA")
                        if "IT IBIKSSRAIN" in brick[i]:
                            bricks.append("TIBBI QAISRANI")
                        if "WHOHWA" in brick[i]:
                            bricks.append("WHOLESALE DGK")
                        if brick[i] == "latoT":
                            break

                    for i in range(0, len(data) - 1):
                        if x == len(pdf.pages) - 1:
                            if data[i][1] == sales[i][0]:
                                for k in range(2, len(data[i]) - 1):
                                    sales[i].append(data[i][k])
                        else:
                            if x == 0:
                                sales.append(data[i][1:])
                            else:
                                if data[i][1] == sales[i][0]:
                                    for k in range(2, len(data[i])):
                                        sales[i].append(data[i][k])
                for i in range(0, len(sales)):
                    products.append(sales[i][0])
                    sales[i] = sales[i][1:]
                    for k in range(0, len(sales[i])):
                        if sales[i][k] == "-":
                            sales[i][k] = "0"
                    if products[i] == "JETEPAR 10ML INJ 5 S":
                        products[i] = "008999"
                    if products[i] == "JETEPAR 2ML INJ 10 S":
                        products[i] = "004348"
                    if products[i] == "JETEPAR CAP 20 S":
                        products[i] = "002392"
                    if products[i] == "JETEPAR SYP 112ML":
                        products[i] = "002188"
                    if products[i] == "MAIORAD 3ML INJ 6 S":
                        products[i] = "009072"
                    if products[i] == "MAIORAD TAB 30 S":
                        products[i] = "012961"
                for p in range(0, len(products)):
                    for s in range(0, len(sales[p])):
                        child = []
                        child.append(products[p])
                        child.append(bricks[s])
                        child.append(sales[p][s])
                        result.append(child)
                for r in range(0, len(result)):
                    for i in item_list:
                        if result[r][0] == i[0]:
                            if result[r][2] != "0":
                                new_result.append(result[r])

                for r in range(0, len(new_result)):
                    for i in item_list:
                        if new_result[r][0] == i[0]:
                            new_result[r].insert(1, i[1])
                            new_result[r].append(i[2])
                for r in new_result:
                    for t in tt_list:
                        if r[2] == t[0]:
                            r.insert(4, t[1])
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
                for x in range(0, len(pdf.pages)):
                    data = pdf.pages[x].extract_text()
                    data = re.sub("\n", "$", data)
                    data = data.split("$")
                    brick = re.sub(r"\s+", "#", data[4])
                    brick = brick.split("#")
                    brick = brick[3:-2]
                    for i in range(0, len(data)):
                        find_Blue = re.search(r"BLUE", data[i - 1])
                        if find_Blue != None:
                            flag_1 = True
                        find_Green = re.search(r"GREEN", data[i - 1])
                        if find_Green != None:
                            flag_1 = True
                        find_group = re.search(r"Group Total", data[i])
                        if find_group != None:
                            flag_1 = False
                        if flag_1 == True:
                            sales.append(data[i])
                    for i in range(0, len(sales)):
                        sales[i] = re.sub("'S", "$", sales[i])
                        sales[i] = re.sub("ML", "$", sales[i])
                        sales[i] = sales[i].split("$")
                        products.append(sales[i][0])

                    var_for_jhang_brick = True
                    for i in range(0, len(brick)):
                        if brick[i] == "18":
                            bricks.append("ATHARA HAZARI")
                        if brick[i] == "AHMAD":
                            bricks.append("AHMADPUR SIAL")
                        if brick[i] == "BHOW":
                            bricks.append("BHOWA")
                        if brick[i] == "GOJRA":
                            bricks.append("GOJRA JNG")
                        if brick[i] == "JHANG" and var_for_jhang_brick == True:
                            bricks.append("JHANG 1")
                            var_for_jhang_brick = False
                        if brick[i] == "JHANG" and var_for_jhang_brick == False:
                            bricks.append("JHANG 2")
                            var_for_jhang_brick = (
                                "Please do not change or remove this statement it works"
                            )
                        if brick[i] == "KOT":
                            bricks.append("KOT SHAKIR JNG")
                        if brick[i] == "SHAH":
                            bricks.append("SHAH JEEWNA")
                        if brick[i] == "SHK.C":
                            bricks.append("SHORKOT CANTT")
                        if brick[i] == "SHORK":
                            bricks.append("SHORKOT JNG")

                    for i in range(0, len(sales)):
                        if products[i] == "JETEPAR  2":
                            products[i] = "004348"
                        if products[i] == "JETEPAR 10":
                            products[i] = "008999"
                        if products[i] == "JETEPAR CAP 20":
                            products[i] = "002392"
                        if products[i] == "JETEPAR SYP 112":
                            products[i] = "002188"
                        if products[i] == "MAIORAD  3":
                            products[i] = "009072"
                        if products[i] == "METRONIDAZOLE 400 MG 100":
                            products[i] = "081274"
                        if products[i] == "METRONIDAZOLE TAB 200 100":
                            products[i] = "008909"
                        if products[i] == "MOXILIUM DROP 10% 10":
                            products[i] = "006782"
                        if products[i] == "MOXILIUM SYP 125MG 45":
                            products[i] = "006783"
                        if products[i] == "MOXILIUM SYP 250MG 60":
                            products[i] = "012649"
                        if products[i] == "P.C.LAC SYP 120":
                            products[i] = "019133"
                        if products[i] == "VIKNON FORTE 120":
                            products[i] = "006406"
                        sales[i] = sales[i][-1]
                        sales[i] = re.sub("\s+", "$", sales[i])
                        sales[i] = sales[i].split("$")
                        sale_quantity.append(sales[i][-3:])
                        sales[i] = sales[i][1 : len(bricks) + 1]
                for p in range(0, len(products)):
                    for s in range(0, len(sales[p])):
                        child = []
                        child.append(products[p])
                        child.append(bricks[s])
                        child.append(sales[p][s])
                        result.append(child)

                for r in range(0, len(result)):
                    for i in item_list:
                        if result[r][0] == i[0]:
                            if result[r][2] != "0":
                                new_result.append(result[r])

                for r in range(0, len(new_result)):
                    for i in item_list:
                        if new_result[r][0] == i[0]:
                            new_result[r].insert(1, i[1])
                            new_result[r].append(i[2])
                for r in new_result:
                    for t in tt_list:
                        if r[2] == t[0]:
                            r.insert(4, t[1])
                            # print(r)

                new_result = green_team_bricks(new_result)
                return new_result
            elif dist_city == "Sargodha":
                result = []
                products = []
                bricks = [
                    "MALAKWAL SGD",
                    "AKT",
                    "JAUHARABAD ",
                    "KHUSHAB",
                    "MITHA LAK",
                    "NOWSHRA",
                    "NUR",
                    "QUAIDABAD",
                    "CHOWKI BHAGAT",
                    "BHALWAL",
                    "BHERA",
                    "FAROOKA",
                    "JAVERIA",
                    "KOT MOMIN",
                    "MARI LAK",
                    "PHL",
                    "SAHIWAL",
                    "SARGODHA 1",
                    "SHAHPUR",
                ]
                bricks2 = ["SILLANWALI", "ADA46 49TAL", "SARGODHA 2", "WHOLESALE SGD"]
                sales = []
                second_page = False
                for x in range(0, len(pdf.pages)):
                    data = pdf.pages[x].extract_text()
                    data = re.sub("\n", "$", data)
                    data = data.split("$")

                    find_second_page = re.search(r"TOTAL", data[3])
                    data1 = data[6:-2]  # for sales
                    data = data[6:-2]  # for poduct
                    for i in range(0, len(data)):
                        data[i] = re.sub("\s\s\s+", "$", data[i])
                        data[i] = data[i].split("$")
                        products.append(data[i][0])
                        data1[i] = re.sub("\s+", "$", data1[i])
                        data1[i] = data1[i].split("$")
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
                for p in range(0, len(products)):
                    for s in range(0, len(sales[p])):
                        if products[p] != "777777":
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
                            r.insert(1, i[1])
                            r.append(i[2])
                for r in result:
                    for t in tt_list:
                        if r[2] == t[0]:
                            r.insert(4, t[1])
                result = green_team_bricks(result)
                return result
            elif dist_city == "Mianwali":
                result = []
                new_result = []
                products = []
                bricks = [
                    "PIPLAN",
                    "ISA KHEL",
                    "KAMAR MASHANI",
                    "WAN BHACHRAN",
                    "LAWA",
                    "MAINWALI MWL",
                    "TRUG",
                    "MAKERWAL",
                    "HARNOLI",
                    "MUSAKHEL",
                    "HAFIZ WALA",
                    "SHADIA",
                    "QUAIDABAD MWL",
                    "DHQ MIANWALI",
                    "CHAKRALA MWL",
                    "KUNDIAN",
                    "DILLY WALI",
                    "ISKANDERABAD",
                    "KALABAGH",
                ]
                bricks2 = ["KOT CHANDNA"]
                sales = []
                second_page = False
                for x in range(0, len(pdf.pages)):
                    data = pdf.pages[x].extract_text()
                    data = re.sub("\n", "$", data)
                    data = data.split("$")
                    find_second_page = re.search(r"TOTAL", data[3])
                    if find_second_page != None:
                        second_page = True
                        data = data[5:-1]  # for poduct
                    else:
                        data = data[6:-2]
                    for i in range(0, len(data)):
                        data[i] = re.sub("\s\s+", "$", data[i])
                        data[i] = data[i].split("$")
                        products.append(data[i][0])
                        if second_page == True:
                            sales.append(data[i][2])
                        else:
                            sales.append(data[i][-19:])
                for i in range(0, len(products)):
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
                for p in range(0, len(products)):
                    for s in range(0, len(sales[p])):
                        child = []
                        child.append(products[p])
                        if second_page == True:
                            child.append(bricks2[s])
                        else:
                            child.append(bricks[s])
                        child.append(sales[p][s])
                        result.append(child)
                for r in range(0, len(result)):
                    for i in item_list:
                        if result[r][0] == i[0]:
                            if result[r][2] != "0":
                                new_result.append(result[r])

                for r in range(0, len(new_result)):
                    for i in item_list:
                        if result[r][0] == i[0]:
                            new_result[r].insert(1, i[1])
                            new_result[r].append(i[2])
                for r in new_result:
                    for t in tt_list:
                        if r[2] == t[0]:
                            r.insert(4, t[1])
                new_result = green_team_bricks(new_result)
                return new_result
            elif dist_city == "Bhakkar":
                result = []
                new_result = []

                # ---------------------------------------------------------------
                # STEP 1: detect which report format this PDF is
                # (old format has a "Group Name"/"Group Total" marker row,
                #  new format e.g. "NOOR MEDICINE COMPANY" layout does not)
                # ---------------------------------------------------------------
                first_page_data = pdf.pages[0].extract_table()
                is_old_format = any(
                    row[0] is not None and "Group Name" in row[0]
                    for row in first_page_data
                )

                # code lookup used by BOTH formats
                NAME_TO_CODE = {
                    "JETIPAR 10ML": "008999",
                    "JETIPAR 2ML": "004348",
                    "JETIPAR CAP": "002392",
                    "JETIPAR SYP": "002188",
                    "MAIORAD TAB": "012961",
                    "MAIORAD INJ": "009072",
                }

                def old_brick_name(t):
                    """Same keyword matching as the original working code."""
                    if "21-4217" in t or "214-217" in t:
                        return "CHAK 214 AND 217"
                    if "AILKHIAL+DELCRS" in t or "ALIKHAIL+DELCRS" in t:
                        return "ALI KHAIL AND DELCRS"
                    if "BAS IT" in t:
                        return "BASTI"
                    if "BEHAL" in t:
                        return "BEHAL"
                    if "BHKR" in t:
                        return "BHAKKAR BKR"
                    if "DHQ" in t:
                        return "DHQ BKR"
                    if "DRYA" in t:
                        return "DARYA KHAN"
                    if "DULEWALA" in t:
                        return "DULLEWALA"
                    if "HIADRABAD" in t or "HAIDRABAD" in t:
                        return "HYDERABAD BKR"
                    if "HIAT-O14CK" in t:
                        return "HAITO 14CK"
                    if "IJAZ" in t:
                        return "IJAZ"
                    if "JAH NKHAN" in t or "JAHNKHAN" in t:
                        return "JAHAN KHAN BKR"
                    if "JANDWALA" in t:
                        return "JANDWALA"
                    if "KALUR" in t:
                        return "KALLURKOT"
                    if "KHANSAR" in t:
                        return "KHANSAR"
                    if "MANKERA" in t:
                        return "MANKERA"
                    if "NM C" in t or "NMC" in t:
                        return "NMC"
                    if "NOTAK" in t:
                        return "NOTAK"
                    if "PANJGRIAN" in t or "PANJGRAIN" in t:
                        return "PANJ GIRAIN"
                    if "PC .WJAV" in t:
                        return "PCW JAV"
                    if "SARAI" in t or "SARIA" in t:
                        return "SARAI MAHAJIR"
                    if "SHAHALAM" in t or "SHAHALA M" in t:
                        return "SHAH ALAM"
                    if "FAROOQ" in t:
                        return "FAROOQ"
                    return None

                # Fingerprint-based brick matching for the NEW format.
                # We match on the SORTED SET OF LETTERS rather than a plain
                # substring, because different pdfplumber/environment
                # versions can split a 2-line cell at a slightly different
                # point, which after removing the newline can leave two
                # adjacent letters swapped (e.g. "ALIKHEL" -> "AILKHEL",
                # "DAILYCROSS" -> "DIALYCROSS"). A plain "in" substring
                # check breaks on that swap; a sorted-letters fingerprint
                # does not, since it ignores order entirely.
                BRICK_FINGERPRINTS = {}

                def _register_brick(canonical_no_space, label):
                    fp = "".join(sorted(canonical_no_space.upper()))
                    BRICK_FINGERPRINTS[fp] = label

                _register_brick("214PUL", "214 PUL")
                _register_brick("217PUL", "217 PUL")
                _register_brick("36TDA", "36 TDA")
                _register_brick("ALIKHEL", "ALI KHAIL AND DELCRS")
                _register_brick("BEHAL", "BEHAL")
                _register_brick("BHAKKARCITY", "BHAKKAR BKR")
                _register_brick("DAILYCROSS", "DAILY CROSS")
                _register_brick("DARYAKHAN", "DARYA KHAN")
                _register_brick("DULLEYWALA", "DULLEWALA")
                _register_brick("HAIDERABAD", "HYDERABAD BKR")
                _register_brick("HAITO", "HAITO 14CK")
                _register_brick("JAHANKHAN", "JAHAN KHAN")
                _register_brick("JANDANWALA", "JANDWALA")
                _register_brick("KALOORKOT", "KALLURKOT")
                _register_brick("KHANSAR", "KHANSAR")
                _register_brick("KOHAWARKALAN", "KHAWAR KALAN")
                _register_brick("KOTLAJAM", "KOTLA JAM")
                _register_brick("MABALSHARIF", "MABAL SHARIF")
                _register_brick("MANKERA", "MANKERA")
                _register_brick("NOTAK", "NOTAK")
                _register_brick("PANJGRAIN", "PANJ GIRAIN")
                _register_brick("RODI", "RODI")
                _register_brick("SARAI", "SARAI MAHAJIR")
                _register_brick("SHAHALM", "SHAH ALAM")
                _register_brick("ZAMAYWALA", "ZAMAY WALA")

                # "Total"/"Grand Total" columns can also come through with
                # transposed letters in some environments (e.g. "TTOLA"),
                # so this is matched by letter-fingerprint too, not just
                # an exact string check.
                TOTAL_FINGERPRINTS = {
                    "".join(sorted("TOTAL")),
                    "".join(sorted("GRANDTOTAL")),
                }

                def new_brick_name(brick_text):
                    """Returns None for the 'Total'/'Grand Total' column
                    (so it's never treated as a brick, even if its letters
                    come through reordered). Unrecognised codes fall back
                    to the whitespace-stripped raw text instead of
                    crashing or silently vanishing, so any new/unmapped
                    brick is still visible in the output and a rule can
                    be added above for it."""
                    t = re.sub(r"\s+", "", brick_text).upper()
                    t = re.sub(r"[^A-Z0-9]", "", t)  # drop stray marker
                    # characters (e.g. the "\u0192" column-end marker used
                    # in the old format) that could otherwise contaminate
                    # the letter-fingerprint and cause a real match to miss
                    if t == "":
                        return None
                    fp = "".join(sorted(t))
                    if fp in TOTAL_FINGERPRINTS:
                        return None
                    return BRICK_FINGERPRINTS.get(fp, t)

                if is_old_format:
                    # =========================================================
                    # OLD FORMAT — logic untouched (this is exactly what
                    # already works for you, only guarded against None so a
                    # stray None cell can never crash it)
                    # =========================================================
                    products = []
                    bricks = []
                    sales = []
                    for x in range(0, len(pdf.pages)):
                        data = pdf.pages[x].extract_table()
                        brick = data[1]
                        start_var = None
                        stop_var = None
                        for i in range(len(data)):
                            if data[i][0] is not None and "Group Name" in data[i][0]:
                                start_var = i + 1
                            if data[i][0] is not None and "Group Total" in data[i][0]:
                                stop_var = i
                        data = data[start_var:stop_var]
                        for i in range(2, len(brick)):
                            if brick[i] is None:
                                continue
                            brick[i] = brick[i].replace("\n", "")
                            brick[i] = brick[i][::-1]
                            name = old_brick_name(brick[i])
                            if name:
                                bricks.append(name)
                            if brick[i] == "\u0192":  # 'ƒ'
                                break
                        for i in range(len(data)):
                            products.append(data[i][0])
                            sales.append(data[i][2:-3])
                            if products[i] in NAME_TO_CODE:
                                products[i] = NAME_TO_CODE[products[i]]
                        for i in range(len(sales)):
                            for k in range(len(sales[i])):
                                if sales[i][k] == "-":
                                    sales[i][k] = "0"

                    for p in range(0, len(products)):
                        for s in range(0, len(sales[p])):
                            child = [products[p], bricks[s], sales[p][s]]
                            result.append(child)

                else:
                    # =========================================================
                    # NEW FORMAT (e.g. "NOOR MEDICINE COMPANY" style report)
                    #  - no "Group Name"/"Group Total" markers
                    #  - bricks may be split across multiple pages
                    #  - a product's sales can be split across 2 rows
                    #    (2nd row has no product name in column 0) -> merged
                    #    into the product above it, as its sales
                    # =========================================================
                    all_bricks = []
                    per_row_sales = None
                    row_product_names = None

                    for x in range(0, len(pdf.pages)):
                        data = pdf.pages[x].extract_table()
                        header = data[0]

                        brick_cols = []
                        for idx, cell in enumerate(header):
                            if cell is None:
                                continue
                            clean = cell.replace("\n", " ").strip()
                            if clean == "":
                                continue
                            clean_rev = clean[::-1].strip()
                            name = new_brick_name(clean_rev)
                            if name is None:
                                continue  # "Total" / empty column -> not a brick
                            all_bricks.append(name)
                            brick_cols.append(idx)

                        data_rows = data[1:-1]  # drop header row + trailing Total row

                        if row_product_names is None:
                            # product names only appear on the first page
                            row_product_names = [r[0] for r in data_rows]

                        page_sales = [[r[i] for i in brick_cols] for r in data_rows]

                        if per_row_sales is None:
                            per_row_sales = page_sales
                        else:
                            for i in range(len(per_row_sales)):
                                per_row_sales[i].extend(page_sales[i])

                    # merge any unnamed continuation row into the product above it
                    merged_products = []
                    merged_sales = []
                    for i in range(len(row_product_names)):
                        name = row_product_names[i]
                        row_vals = per_row_sales[i]
                        if name is None and merged_products:
                            prev = merged_sales[-1]
                            for k in range(len(prev)):
                                pv = (
                                    0
                                    if prev[k] in (None, "-", "")
                                    else float(str(prev[k]).replace(",", ""))
                                )
                                cv = (
                                    0
                                    if row_vals[k] in (None, "-", "")
                                    else float(str(row_vals[k]).replace(",", ""))
                                )
                                total = pv + cv
                                prev[k] = (
                                    str(int(total))
                                    if total == int(total)
                                    else str(total)
                                )
                        else:
                            merged_products.append(name)
                            merged_sales.append(list(row_vals))

                    products = [
                        NAME_TO_CODE.get(name, name) for name in merged_products
                    ]
                    bricks = all_bricks
                    sales = merged_sales
                    for i in range(len(sales)):
                        for k in range(len(sales[i])):
                            if sales[i][k] in ("-", None, ""):
                                sales[i][k] = "0"

                    for p in range(0, len(products)):
                        for s in range(0, len(sales[p])):
                            child = [products[p], bricks[s], sales[p][s]]
                            result.append(child)

                # -------------------------------------------------------------
                # everything below is UNCHANGED for both formats
                # -------------------------------------------------------------
                for r in range(0, len(result)):
                    for i in item_list:
                        if result[r][0] == i[0]:
                            if result[r][2] != "0":
                                new_result.append(result[r])

                for r in range(0, len(new_result)):
                    for i in item_list:
                        if new_result[r][0] == i[0]:
                            new_result[r].insert(1, i[1])
                            new_result[r].append(i[2])
                for r in new_result:
                    for t in tt_list:
                        if r[2] == t[0]:
                            r.insert(4, t[1])
                new_result = green_team_bricks(new_result)
                return new_result
            elif dist_city == "Mingora":
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
                for x in range(0, len(pdf.pages)):
                    data = pdf.pages[x].extract_text()
                    data = re.sub("\n", "$", data)
                    data = data.split("$")
                    if x == 0 or x == 1:
                        bricks1 = data[8]
                        bricks1 = re.sub("\s+", "$", bricks1)
                        bricks1 = bricks1.split("$")
                        if x == 1:
                            bricks3 = bricks3 + bricks1[4:-2]
                        else:
                            bricks3 = bricks1[4:]
                    if data[8][-10:] == "Total Sale":
                        sales3 = data[10:-2]
                        for i in range(len(sales1)):
                            sales4 = re.sub("\s", "$", sales3[i])
                            sales4 = sales4.split("$")
                            sales5.append(sales4)
                    else:
                        sales1 = data[10:-2]
                        for i in range(len(sales1)):
                            sales2 = re.sub("\s", "$", sales1[i])
                            sales2 = sales2.split("$")
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
                    for k in range(0, len(sales[i]), 2):
                        temp_sale.append(sales[i][k] + sales[i][k + 1])
                    final_sale.append(temp_sale)
                    final_sale[i] = [str(x) for x in final_sale[i]]
                for i in range(0, len(products)):
                    if products[i] == "2700":
                        products[i] = "008999"
                    if products[i] == "2701":
                        products[i] = "004348"
                    if products[i] == "2702":
                        products[i] = "002392"
                    if products[i] == "2703":
                        products[i] = "002188"
                    if products[i] == "2727":
                        products[i] = "008376"
                    if products[i] == "2728":
                        products[i] = "017230"
                    if products[i] == "2737":
                        products[i] = "009072"
                    if products[i] == "2738":
                        products[i] = "012961"
                    if products[i] == "2705":
                        products[i] = "024819"
                    if products[i] == "2706":
                        products[i] = "028727"
                    if products[i] == "2707":
                        products[i] = "024820"
                    if products[i] == "2708":
                        products[i] = "006406"
                    if products[i] == "2709":
                        products[i] = "007018"
                    if products[i] == "2710":
                        products[i] = "005425"
                    if products[i] == "2713":
                        products[i] = "028729"
                    if products[i] == "2714":
                        products[i] = "016654"
                    if products[i] == "2730":
                        products[i] = "006783"
                    if products[i] == "2731":
                        products[i] = "012649"
                    if products[i] == "2732":
                        products[i] = "008908"
                    if products[i] == "2733":
                        products[i] = "006784"
                    if products[i] == "2734":
                        products[i] = "006782"
                    if products[i] == "2739":
                        products[i] = "026920"
                    if products[i] == "2740":
                        products[i] = "029327"
                    if products[i] == "2741":
                        products[i] = "028728"
                    if products[i] == "2754":
                        products[i] = "019133"
                    if products[i] == "2756":
                        products[i] = "038426"
                    if products[i] == "2757":
                        products[i] = "038426"
                    if products[i] == "2759":
                        products[i] = "032259"
                    if products[i] == "2760":
                        products[i] = "032255"
                    if products[i] == "2761":
                        products[i] = "029328"
                    if products[i] == "7153":
                        products[i] = "081838"
                    if products[i] == "7154":
                        products[i] = "081274"
                for i in range(0, len(bricks3)):
                    if "MINGORA" in bricks3[i] and mingora1 == True:
                        bricks3[i] = "MINGORA 1"
                        bricks.append(bricks3[i])
                        mingora1 = False

                    if "MINGORA" in bricks3[i] and mingora3 == True:
                        bricks3[i] = "MINGORA 3"
                        bricks.append(bricks3[i])

                    if "BARIKOT" in bricks3[i]:
                        bricks3[i] = "BARIKOT"
                        bricks.append(bricks3[i])
                    if "BUTKHELA" in bricks3[i]:
                        bricks3[i] = "BATKHELA"
                        bricks.append(bricks3[i])
                    if "BUNIR" in bricks3[i]:
                        bricks3[i] = "BUNER"
                        bricks.append(bricks3[i])
                    if "BESHAM" in bricks3[i]:
                        bricks3[i] = "BISHAM"
                        bricks.append(bricks3[i])
                    if "MATTA" in bricks3[i]:
                        bricks3[i] = "MATTA SWAT"
                        bricks.append(bricks3[i])
                    if "K.KHELA-4BAG" in bricks3[i]:
                        bricks3[i] = "KHWAZA KHELA"
                        bricks.append(bricks3[i])
                    if "MINGORA-" in bricks3[i]:
                        bricks3[i] = "MINGORA 2"
                        bricks.append(bricks3[i])
                    if "MAD.BAH.FATH" in bricks3[i]:
                        bricks3[i] = "MADYAN AND BAHRAIN AND FATEHPUR"
                        bricks.append(bricks3[i])
                    if "PURAN" in bricks3[i]:
                        bricks3[i] = "PURAN"
                        bricks.append(bricks3[i])
                    if "SAIDU+CENTER" in bricks3[i]:
                        bricks3[i] = "SAIDU AND CENTER"
                        bricks.append(bricks3[i])
                    if "COUNTER" in bricks3[i]:
                        bricks3[i] = "COUNTER SALE"
                        bricks.append(bricks3[i])
                    if "TIMARGARA" in bricks3[i]:
                        bricks3[i] = "TIMARGARA MGR"
                        bricksnew_result = green_team_bricks(new_result).append(
                            bricks3[i]
                        )
                        mingora3 = True
                    if "SOLD" in bricks3[i]:
                        bricks3[i] = "SOLD AREA"
                        bricks.append(bricks3[i])

                    if "KABAL" in bricks3[i]:
                        bricks3[i] = "KABAL"
                        bricks.append(bricks3[i])

                for p in range(0, len(products)):
                    for s in range(0, len(final_sale[p])):
                        child = []
                        child.append(products[p])
                        child.append(bricks[s])
                        child.append(final_sale[p][s])
                        result.append(child)
                for r in range(0, len(result)):
                    for i in item_list:
                        if result[r][0] == i[0]:
                            if result[r][2] != "0":
                                new_result.append(result[r])
                for r in new_result:
                    for i in item_list:
                        if r[0] == i[0]:
                            r.insert(1, i[1])
                            r.append(i[2])
                            # print(r)
                for r in new_result:
                    for t in tt_list:
                        if r[2] == t[0]:
                            r.insert(4, t[1])
                # print(new_result)
                new_result = green_team_bricks(new_result)
                return new_result
            # elif dist_city == "MULTAN":
            #     result = []
            #     products = []
            #     new_result = []
            #     brick = []
            #     bricks = []
            #     sales = []
            #     sales2 = []
            #     last_page = False
            #     for x in range(0, len(pdf.pages)):
            #         data = pdf.pages[x].extract_table()
            #         for i in range(1, len(data[0])):
            #             #   # for k in range(0,len(brick[i])):
            #             data[0][i] = str(data[0][i]).replace("\n", "")
            #             brick.append(data[0][i])
            #         # print(products)
            #         for i in range(0, len(brick)):
            #             if "D AORR NEATTHLSUNIM" in brick[i]:
            #                 brick[i] = "NISHTER ROAD MULTAN"
            #             if "TTNACN ATLUM" in brick[i]:
            #                 brick[i] = "MULTAN CANTT"
            #             if (
            #                 "D ABAUJHDSAD OLR" in brick[i]
            #                 or "D ABAUJHDSALD ROO" in brick[i]
            #             ):
            #                 brick[i] = "OLD SUJABAD ROAD"
            #             if "D AORY NAAWTAILMULR" in brick[i]:
            #                 brick[i] = "RAILWAY ROAD"
            #             if (
            #                 "H AHSK SWACHOABB" in brick[i]
            #                 or "H AHSK SWAHOABBC" in brick[i]
            #             ):
            #                 brick[i] = "CHOWK SHAH ABBAS"
            #             if "D ABAZNAATTMLUUMM" in brick[i]:
            #                 brick[i] = "MUMTAZABAD MULTAN"
            #             if "K WOHNCAC.G. ULTB.M" in brick[i]:
            #                 brick[i] = "BGC CHOWK"
            #             if "E TK GATANALPU" in brick[i]:
            #                 brick[i] = "PAK GATE"
            #             if "E TAGM ANATRLAUHM" in brick[i]:
            #                 brick[i] = "HARAM GATE"
            #             if "L AMAHAFIZ JROAD" in brick[i]:
            #                 brick[i] = "HAFIZ JAMAL ROAD"
            #             if "E TAGT NAALTULAUDM" in brick[i]:
            #                 brick[i] = "DAULAT GATE MULTAN"
            #             if "H AHSM ODOASOARM" in brick[i]:
            #                 brick[i] = "MASOOM SHAH ROAD"
            #             if "1 O. NGI ANNTULHUCM" in brick[i]:
            #                 brick[i] = "CHUNGI NO 1"
            #             if "D AONRAT.B. ULT" in brick[i]:
            #                 brick[i] = "T.B ROAD MULTAN"
            #             if "NATLUMW EN" in brick[i]:
            #                 brick[i] = "NEW MULTAN"
            #             if "FI AZAQNK AWTLOUHMC" in brick[i]:
            #                 brick[i] = "CHOWK QAZAFI"
            #             if (
            #                 "D ABANMIJTA2) SAMUL" in brick[i]
            #                 or "D ABANMIJTAAUL2) SM" in brick[i]
            #             ):
            #                 brick[i] = "SAMIJABAD"
            #             if (
            #                 "L LRAEHLN ALWSOE TL" in brick[i]
            #                 or "L LRAEN HALLWSOE" in brick[i]
            #             ):
            #                 brick[i] = "TOWN HALL WHOLE SALLER"
            #             if "9 O.NUNGI LTANHUCM" in brick[i]:
            #                 brick[i] = "CHUNGI NO 9"
            #             if "T HSANGALTULGU" in brick[i]:
            #                 brick[i] = "GULGASHT"
            #             if "D, AON RAN.ATSLOUBM" in brick[i]:
            #                 brick[i] = "BOSAN ROAD"
            #             if "R UPB ADWAAONR" in brick[i]:
            #                 brick[i] = "NAWAB PUR ROAD"
            #             if "A. D.M.K ANWTOLHUCM5) 31(" in brick[i]:
            #                 brick[i] = "MDA CHOWK"
            #             if "NI AMIAJ DRAUOORS" in brick[i]:
            #                 brick[i] = "SURAJ MIANI ROAD"
            #             if "L ANWAHANEMULTKD" in brick[i]:
            #                 brick[i] = "KHANEWAL"
            #             if "H AHSR DEAHOSR" in brick[i]:
            #                 brick[i] = "SHER SHAH ROAD"
            #             if "KWOHCRI AHEV" in brick[i]:
            #                 brick[i] = "VEHARI CHOWK"
            #             if "E RALCAEDIPITMS0)HO51(" in brick[i]:
            #                 brick[i] = "MEDICARE HOSPITAL"
            #             if "Y ADNSALISAAWW" in brick[i]:
            #                 brick[i] = "WASSANDAY WALI"
            #             if "LIAWNALHIOR" in brick[i]:
            #                 brick[i] = "ROHILLAN WALI"
            #             if "NATLUSR EHAHS" in brick[i] or "SHAHER SULTAN" in brick[i]:
            #                 brick[i] = "SHAHER SULTAN"
            #             if "RUPLI A" in brick[i]:
            #                 brick[i] = "ALI PUR"
            #             if "RUPLALA1" in brick[i]:
            #                 brick[i] = "JALAL PUR"
            #             if "DABAUJHS" in brick[i]:
            #                 brick[i] = "SHUJABAD"
            #             if "M OODKHLIMAAL" in brick[i] or "M OODAKHALLIM" in brick[i]:
            #                 brick[i] = "MAKHDOOM ALI"
            #             if "ZAIF5- K CAHC" in brick[i]:
            #                 brick[i] = "CHACK 5 FAIZ"
            #             if "RALA DDA" in brick[i]:
            #                 brick[i] = "ADDA LAR MULTAN"
            #             if "R AFFAHUZRAMG" in brick[i] or "R AFFAHZAURMG" in brick[i]:
            #                 brick[i] = "MUZAFFAR GARH"
            #             if "AREESAB" in brick[i]:
            #                 brick[i] = "BASEERA"
            #             if "LAMAH JAHS" in brick[i]:
            #                 brick[i] = "SHAH JAMAL MULTAN"
            #             if "EROMHI SERUQ" in brick[i]:
            #                 brick[i] = "QURESHI MORE"
            #             if "NAWANAS" in brick[i]:
            #                 brick[i] = "SANAWAN"
            #             if "TARUJG" in brick[i]:
            #                 brick[i] = "GUJRAT MLT"
            #             if "UNNAHCN AMI" in brick[i]:
            #                 brick[i] = "MIAN CHANNU"
            #             if "MKIAHL UDBA" in brick[i]:
            #                 brick[i] = "ABDUL HAKIM"
            #             if "ABMALUT" in brick[i]:
            #                 brick[i] = "TULAMBA"
            #             if "HOHKA HCAK" in brick[i]:
            #                 brick[i] = "KACHA KHOH"
            #             if "N SIHOMLA LDADWA" in brick[i]:
            #                 brick[i] = "ADDA MOHSIN WALL"
            #             if "LEEM2 - 1L LUP" in brick[i]:
            #                 brick[i] = "PULL 12 MEEL"
            #             if "RUPM ONOADRHAKHAOMP8" in brick[i]:
            #                 brick[i] = "MAKHDOOM PUR PAHORAN"
            #             if "argabul p" in brick[i]:
            #                 brick[i] = "PULL BAGAR MULTAN"
            #             if "ALAWRBIAK" in brick[i]:
            #                 brick[i] = "KABIR WALA"
            #             if "LAWENAHK" in brick[i]:
            #                 brick[i] = "KHANEWAL"
            #             if "41L - LUP" in brick[i]:
            #                 brick[i] = "PULL 14"
            #             if "M OODDKHHIMARAS" in brick[i]:
            #                 brick[i] = "MAKHDOOM RASHEED"
            #             if "ATTAHT" in brick[i]:
            #                 brick[i] = "THATTA MULTAN"
            #             if "SILAIM" in brick[i]:
            #                 brick[i] = "MAILSI"
            #             if "ATOKOD4" in brick[i]:
            #                 brick[i] = "DOKOTA MULTAN"
            #             if "ANIAHA" in brick[i]:
            #                 brick[i] = "JAHANIAN"
            #             if "D AORI RANATVEHMUL9) 01(" in brick[i]:
            #                 brick[i] = "VEHARI ROAD"
            #             if (
            #                 "E- N-NKAH RUMULTHAM SA" in brick[i]
            #                 or "E- N-NKARUULTH MHAM SA" in brick[i]
            #             ):
            #                 brick[i] = "SHAH RUKN E ALAM"
            #             if "NATLUMH AGD E" in brick[i]:
            #                 brick[i] = "EID GAH MULTAN"
            #             if "NARARABL LUP" in brick[i]:
            #                 brick[i] = "PULL BARARAN"
            #             if "D AORHARI MJ)E(V1) 61(" in brick[i]:
            #                 brick[i] = "VEHARI ROAD"
            #             if "N ERLDALTHIPI2) CHOS61(" in brick[i]:
            #                 brick[i] = "CHILDREN HOSPITAL MULTAN"
            #             if "A NELE-STAN-PI6) IBHOS" in brick[i]:
            #                 brick[i] = "IBN E SENA HOSPITAL"
            #             if "C M.A RHSNHTE" in brick[i]:
            #                 brick[i] = "AHSAN MEDICINE COMPANY NISHTER"
            #             if "HRAGN AHK" in brick[i]:
            #                 brick[i] = "KHAN GARH"
            #             if "KOOLAMTI SAB" in brick[i]:
            #                 brick[i] = "BASTI MALOOK"
            #             if "RUPA YNUD" in brick[i]:
            #                 brick[i] = "DUNYA PUR"
            #             if "NWOTN EDRAG" in brick[i]:
            #                 brick[i] = "GARDEN TOWN"
            #             if "DABAR AFFAZUM" in brick[i]:
            #                 brick[i] = "MUZAFFAR ABAD"
            #             if "NHIAWR ALAS" in brick[i]:
            #                 brick[i] = "SALAR WAHIN"
            #             if "D NAA BANDSDOAB" in brick[i]:
            #                 brick[i] = "ADDA BAND BOSAN"
            #             if "N WOTSEL ASMODBYP" in brick[i]:
            #                 brick[i] = "MODEL TOWN BYPASS"
            #             if "NAWNAR" in brick[i]:
            #                 brick[i] = "RANWAN"
            #             if "OGNARL LUP" in brick[i]:
            #                 brick[i] = "PULL RANGO"
            #             if "SALLVIH CUB" in brick[i]:
            #                 brick[i] = "BUCH VILLAS"
            #             if "L EDOMDL AAOZRAF" in brick[i]:
            #                 brick[i] = "FAZAL MODEL ROAD"
            #             if "RUPY ATAT" in brick[i]:
            #                 brick[i] = "TATAY PUR"
            #             if "TNASA LHDOB" in brick[i]:
            #                 brick[i] = "BUDHLA SANT"
            #             if "DAORH ANNA JIM" in brick[i]:
            #                 brick[i] = "M A JINNAH ROAD"
            #         bricks = brick[:-1]
            #         # for p in data:
            #         if x == len(pdf.pages) - 1:
            #             last_page = True
            #         if x == 0:
            #             sales = data[1:-1]
            #         else:
            #             sales2 = data[1:-1]
            #             for i in range(0, len(sales2)):
            #                 if sales[i][0] == sales2[i][0] and last_page == True:
            #                     sales[i] = sales[i][:] + sales2[i][1:-1]
            #                     products.append(sales[i][0])
            #                 # print(sales[i])
            #                 elif sales[i][0] == sales2[i][0]:
            #                     sales[i] = sales[i][:] + sales2[i][1:]

            #     for i in range(0, len(products)):
            #         sales[i] = sales[i][1:]
            #         if "JETEPAR 2ML INJ" in products[i]:
            #             products[i] = "004348"
            #         if "JETEPAR CAP" in products[i]:
            #             products[i] = "002392"
            #         if "JETEPAR INJ" in products[i]:
            #             products[i] = "008999"
            #         if (
            #             products[i] == "JETEPAR 10ML 5S"
            #             or products[i] == "JETEPAR 10ML INJ  5S"
            #         ):
            #             products[i] = "008999"
            #         if "JETEPAR SYP" in products[i]:
            #             products[i] = "002188"
            #         # if products[i] == 'JETEPAR SYP. 112ML':
            #         #   products[i] = '002188'
            #         if (
            #             "MAIORAD INJ" in products[i]
            #             or "MAIORAD 3ML-INJ 6,S" in products[i]
            #         ):
            #             products[i] = "009072"
            #     for p in range(0, len(products)):
            #         for s in range(0, len(sales[p])):
            #             child = []
            #             child.append(products[p])
            #             child.append(bricks[s])
            #             child.append(sales[p][s])
            #             result.append(child)
            #     for r in range(0, len(result)):
            #         for i in item_list:
            #             if result[r][0] == i[0]:
            #                 if result[r][2] != "0":
            #                     new_result.append(result[r])
            #     # print(len(new_result))
            #     for r in range(0, len(new_result)):
            #         for i in item_list:
            #             if new_result[r][0] == i[0]:
            #                 new_result[r].insert(1, i[1])
            #                 new_result[r].append(i[2])
            #                 # print(new_result[r])
            #     for r in new_result:
            #         for t in tt_list:
            #             if r[2] == t[0]:
            #                 r.insert(4, t[1])
            #     new_result = green_team_bricks(new_result)
            #     return new_result

            elif dist_city == "MULTAN":
                result = []
                products = []
                new_result = []
                brick = []
                bricks = []
                sales = []

                for x in range(0, len(pdf.pages)):
                    data = pdf.pages[x].extract_table()

                    # clean brick names
                    for i in range(1, len(data[0])):
                        data[0][i] = str(data[0][i]).replace("\n", "")
                        brick.append(data[0][i])

                    # mapping bricks
                    for i in range(0, len(brick)):
                        if "D AORR NEATTHLSUNIM" in brick[i]:
                            brick[i] = "NISHTER ROAD MULTAN"
                        if "TTNACN ATLUM" in brick[i]:
                            brick[i] = "MULTAN CANTT"
                        if (
                            "D ABAUJHDSAD OLR" in brick[i]
                            or "D ABAUJHDSALD ROO" in brick[i]
                        ):
                            brick[i] = "OLD SUJABAD ROAD"
                        if "D AORY NAAWTAILMULR" in brick[i]:
                            brick[i] = "RAILWAY ROAD"
                        if (
                            "H AHSK SWACHOABB" in brick[i]
                            or "H AHSK SWAHOABBC" in brick[i]
                        ):
                            brick[i] = "CHOWK SHAH ABBAS"
                        if "D ABAZNAATTMLUUMM" in brick[i]:
                            brick[i] = "MUMTAZABAD MULTAN"
                        if "K WOHNCAC.G. ULTB.M" in brick[i]:
                            brick[i] = "BGC CHOWK"
                        if "E TK GATANALPU" in brick[i]:
                            brick[i] = "PAK GATE"
                        if "E TAGM ANATRLAUHM" in brick[i]:
                            brick[i] = "HARAM GATE"
                        if "L AMAHAFIZ JROAD" in brick[i]:
                            brick[i] = "HAFIZ JAMAL ROAD"
                        if "E TAGT NAALTULAUDM" in brick[i]:
                            brick[i] = "DAULAT GATE MULTAN"
                        if "H AHSM ODOASOARM" in brick[i]:
                            brick[i] = "MASOOM SHAH ROAD"
                        if "1 O. NGI ANNTULHUCM" in brick[i]:
                            brick[i] = "CHUNGI NO 1"
                        if "D AONRAT.B. ULT" in brick[i]:
                            brick[i] = "T.B ROAD MULTAN"
                        if "NATLUMW EN" in brick[i]:
                            brick[i] = "NEW MULTAN"
                        if "FI AZAQNK AWTLOUHMC" in brick[i]:
                            brick[i] = "CHOWK QAZAFI"
                        if (
                            "D ABANMIJTA2) SAMUL" in brick[i]
                            or "D ABANMIJTAAUL2) SM" in brick[i]
                        ):
                            brick[i] = "SAMIJABAD"
                        if (
                            "L LRAEHLN ALWSOE TL" in brick[i]
                            or "L LRAEN HALLWSOE" in brick[i]
                        ):
                            brick[i] = "TOWN HALL WHOLE SALLER"
                        if "9 O.NUNGI LTANHUCM" in brick[i]:
                            brick[i] = "CHUNGI NO 9"
                        if "T HSANGALTULGU" in brick[i]:
                            brick[i] = "GULGASHT"
                        if "D, AON RAN.ATSLOUBM" in brick[i]:
                            brick[i] = "BOSAN ROAD"
                        if "R UPB ADWAAONR" in brick[i]:
                            brick[i] = "NAWAB PUR ROAD"
                        if "A. D.M.K ANWTOLHUCM5) 31(" in brick[i]:
                            brick[i] = "MDA CHOWK"
                        if "NI AMIAJ DRAUOORS" in brick[i]:
                            brick[i] = "SURAJ MIANI ROAD"
                        if "L ANWAHANEMULTKD" in brick[i]:
                            brick[i] = "KHANEWAL"
                        if "H AHSR DEAHOSR" in brick[i]:
                            brick[i] = "SHER SHAH ROAD"
                        if "KWOHCRI AHEV" in brick[i]:
                            brick[i] = "VEHARI CHOWK"
                        if "E RALCAEDIPITMS0)HO51(" in brick[i]:
                            brick[i] = "MEDICARE HOSPITAL"
                        if "Y ADNSALISAAWW" in brick[i]:
                            brick[i] = "WASSANDAY WALI"
                        if "LIAWNALHIOR" in brick[i]:
                            brick[i] = "ROHILLAN WALI"
                        if "NATLUSR EHAHS" in brick[i] or "SHAHER SULTAN" in brick[i]:
                            brick[i] = "SHAHER SULTAN"
                        if "RUPLI A" in brick[i]:
                            brick[i] = "ALI PUR"
                        if "RUPLALA1" in brick[i]:
                            brick[i] = "JALAL PUR"
                        if "DABAUJHS" in brick[i]:
                            brick[i] = "SHUJABAD"
                        if "M OODKHLIMAAL" in brick[i] or "M OODAKHALLIM" in brick[i]:
                            brick[i] = "MAKHDOOM ALI"
                        if "ZAIF5- K CAHC" in brick[i]:
                            brick[i] = "CHACK 5 FAIZ"
                        if "RALA DDA" in brick[i]:
                            brick[i] = "ADDA LAR MULTAN"
                        if "R AFFAHUZRAMG" in brick[i] or "R AFFAHZAURMG" in brick[i]:
                            brick[i] = "MUZAFFAR GARH"
                        if "AREESAB" in brick[i]:
                            brick[i] = "BASEERA"
                        if "LAMAH JAHS" in brick[i]:
                            brick[i] = "SHAH JAMAL MULTAN"
                        if "EROMHI SERUQ" in brick[i]:
                            brick[i] = "QURESHI MORE"
                        if "NAWANAS" in brick[i]:
                            brick[i] = "SANAWAN"
                        if "TARUJG" in brick[i]:
                            brick[i] = "GUJRAT MLT"
                        if "UNNAHCN AMI" in brick[i]:
                            brick[i] = "MIAN CHANNU"
                        if "MKIAHL UDBA" in brick[i]:
                            brick[i] = "ABDUL HAKIM"
                        if "ABMALUT" in brick[i]:
                            brick[i] = "TULAMBA"
                        if "HOHKA HCAK" in brick[i]:
                            brick[i] = "KACHA KHOH"
                        if "N SIHOMLA LDADWA" in brick[i]:
                            brick[i] = "ADDA MOHSIN WALL"
                        if "LEEM2 - 1L LUP" in brick[i]:
                            brick[i] = "PULL 12 MEEL"
                        if "RUPM ONOADRHAKHAOMP8" in brick[i]:
                            brick[i] = "MAKHDOOM PUR PAHORAN"
                        if "argabul p" in brick[i]:
                            brick[i] = "PULL BAGAR MULTAN"
                        if "ALAWRBIAK" in brick[i]:
                            brick[i] = "KABIR WALA"
                        if "LAWENAHK" in brick[i]:
                            brick[i] = "KHANEWAL"
                        if "41L - LUP" in brick[i]:
                            brick[i] = "PULL 14"
                        if "M OODDKHHIMARAS" in brick[i]:
                            brick[i] = "MAKHDOOM RASHEED"
                        if "ATTAHT" in brick[i]:
                            brick[i] = "THATTA MULTAN"
                        if "SILAIM" in brick[i]:
                            brick[i] = "MAILSI"
                        if "ATOKOD4" in brick[i]:
                            brick[i] = "DOKOTA MULTAN"
                        if "ANIAHA" in brick[i]:
                            brick[i] = "JAHANIAN"
                        if "D AORI RANATVEHMUL9) 01(" in brick[i]:
                            brick[i] = "VEHARI ROAD"
                        if (
                            "E- N-NKAH RUMULTHAM SA" in brick[i]
                            or "E- N-NKARUULTH MHAM SA" in brick[i]
                        ):
                            brick[i] = "SHAH RUKN E ALAM"
                        if "NATLUMH AGD E" in brick[i]:
                            brick[i] = "EID GAH MULTAN"
                        if "NARARABL LUP" in brick[i]:
                            brick[i] = "PULL BARARAN"
                        if "D AORHARI MJ)E(V1) 61(" in brick[i]:
                            brick[i] = "VEHARI ROAD"
                        if "N ERLDALTHIPI2) CHOS61(" in brick[i]:
                            brick[i] = "CHILDREN HOSPITAL MULTAN"
                        if "A NELE-STAN-PI6) IBHOS" in brick[i]:
                            brick[i] = "IBN E SENA HOSPITAL"
                        if "C M.A RHSNHTE" in brick[i]:
                            brick[i] = "AHSAN MEDICINE COMPANY NISHTER"
                        if "HRAGN AHK" in brick[i]:
                            brick[i] = "KHAN GARH"
                        if "KOOLAMTI SAB" in brick[i]:
                            brick[i] = "BASTI MALOOK"
                        if "RUPA YNUD" in brick[i]:
                            brick[i] = "DUNYA PUR"
                        if "NWOTN EDRAG" in brick[i]:
                            brick[i] = "GARDEN TOWN"
                        if "DABAR AFFAZUM" in brick[i]:
                            brick[i] = "MUZAFFAR ABAD"
                        if "NHIAWR ALAS" in brick[i]:
                            brick[i] = "SALAR WAHIN"
                        if "D NAA BANDSDOAB" in brick[i]:
                            brick[i] = "ADDA BAND BOSAN"
                        if "N WOTSEL ASMODBYP" in brick[i]:
                            brick[i] = "MODEL TOWN BYPASS"
                        if "NAWNAR" in brick[i]:
                            brick[i] = "RANWAN"
                        if "OGNARL LUP" in brick[i]:
                            brick[i] = "PULL RANGO"
                        if "SALLVIH CUB" in brick[i]:
                            brick[i] = "BUCH VILLAS"
                        if "L EDOMDL AAOZRAF" in brick[i]:
                            brick[i] = "FAZAL MODEL ROAD"
                        if "RUPY ATAT" in brick[i]:
                            brick[i] = "TATAY PUR"
                        if "TNASA LHDOB" in brick[i]:
                            brick[i] = "BUDHLA SANT"
                        if "DAORH ANNA JIM" in brick[i]:
                            brick[i] = "M A JINNAH ROAD"

                    bricks = brick[:-1]

                    if x == len(pdf.pages) - 1:
                        last_page = True
                    else:
                        last_page = False

                    page_rows = data[1:-1]  # drop header row + trailing Total row

                    if x == 0:
                        sales = page_rows
                    else:
                        for i, row in enumerate(page_rows):
                            if i < len(sales) and sales[i][0] == row[0]:
                                # same product continuing with more brick
                                # columns from this page
                                if last_page:
                                    sales[i] = sales[i][:] + row[1:-1]
                                else:
                                    sales[i] = sales[i][:] + row[1:]
                            else:
                                sales.append(row)

                # -----------------------------------------------------------
                # `products` is now built ONCE, after ALL pages have been
                # merged into `sales` -- not inside the multi-page merge
                # branch above. The old code only ever appended to
                # `products` when x != 0 (i.e. only on the 2nd+ page), so
                # any single-page report left `products` permanently empty,
                # which meant every loop below ran zero times and `return
                # new_result` silently came back empty -- no crash, just no
                # data. This works the same whether the report is 1 page or
                # several.
                # -----------------------------------------------------------
                for row in sales:
                    products.append(row[0])

                for i in range(0, len(products)):
                    sales[i] = sales[i][1:]
                    if "JETEPAR 2ML INJ" in products[i]:
                        products[i] = "004348"
                    if "JETEPAR CAP" in products[i]:
                        products[i] = "002392"
                    if "JETEPAR INJ" in products[i]:
                        products[i] = "008999"
                    if products[i] in ["JETEPAR 10ML 5S", "JETEPAR 10ML INJ  5S"]:
                        products[i] = "008999"
                    if "JETEPAR SYP" in products[i]:
                        products[i] = "002188"
                    if (
                        "MAIORAD INJ" in products[i]
                        or "MAIORAD 3ML-INJ 6,S" in products[i]
                    ):
                        products[i] = "009072"

                for p in range(0, len(products)):
                    for s in range(0, len(sales[p])):
                        if s >= len(bricks):
                            break
                        child = []
                        child.append(products[p])
                        child.append(bricks[s])
                        child.append(sales[p][s])
                        result.append(child)

                for r in range(0, len(result)):
                    for i in item_list:
                        if result[r][0] == i[0]:
                            val = str(result[r][2]).strip()
                            if val not in ["0", "0.0", "", "None"]:
                                new_result.append(result[r])

                for r in range(0, len(new_result)):
                    for i in item_list:
                        if new_result[r][0] == i[0]:
                            new_result[r].insert(1, i[1])
                            new_result[r].append(i[2])

                for r in new_result:
                    for t in tt_list:
                        if r[2] == t[0]:
                            r.insert(4, t[1])

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
                for x in range(0, len(pdf.pages)):
                    data = pdf.pages[x].extract_table()
                    if data[0][-1] == "Total Amount" and get_only_once_1 == True:
                        products.append(data[0][1:-1])
                        get_only_once_1 = False
                    else:
                        if get_only_once_2 == False:
                            products.append(data[0][1:])
                            get_only_once_2 = False
                    for i in range(1, len(data)):
                        if data[i][0] == "Total":
                            break
                        else:
                            sales.append(data[i][1:-1])
                            bricks.append(data[i][0])
                products1 = [b for b in products[0][:]]
                for i in range(0, len(products1)):
                    products1[i] = re.sub("006011", "004348", products1[i][0:6])
                    products1[i] = re.sub("006012", "002392", products1[i])
                    products1[i] = re.sub("006013", "002188", products1[i])
                    products1[i] = re.sub("006014", "008999", products1[i])
                    products1[i] = re.sub("006015", "012961", products1[i])
                    products1[i] = re.sub("006016", "009072", products1[i])

                    products1[i] = re.sub("031001", "002188", products1[i])
                    products1[i] = re.sub("031002", "009072", products1[i])
                    products1[i] = re.sub("031003", "012961", products1[i])
                    products1[i] = re.sub("031004", "002392", products1[i])
                    products1[i] = re.sub("031005", "008999", products1[i])
                    products1[i] = re.sub("031006", "004348", products1[i])

                for i in range(0, len(bricks)):
                    bricks1.append(bricks[i][10:])
                    bricks1[i] = re.sub("\n", "", bricks1[i])

                for s in range(0, len(sales)):
                    for i in range(0, len(sales[s])):
                        if sales[s][i] == "-":
                            sales[s][i] = "0"
                for i in range(0, len(bricks1)):
                    if bricks1[i] == "HOSPITAL ROAD-1":
                        bricks1[i] = "HOSPITAL ROAD 1"
                    if bricks1[i] == "HOSPITAL ROAD-2":
                        bricks1[i] = "HOSPITAL ROAD 2"
                    if bricks1[i] == "ABBASIA TWON":
                        bricks1[i] = "ABBASIA TOWN"
                    if bricks1[i] == "KHAN PUR ROAD RYK":
                        bricks1[i] = "KHANPUR ROAD"
                    if bricks1[i] == "GULSHAN iQBAL":
                        bricks1[i] = "GULSHAN E IQBAL"
                    if bricks1[i] == "GULSHAN USMAN":
                        bricks1[i] = "GULSHAN E USMAN"
                    if bricks1[i] == "AIR PORT ROAD RYK":
                        bricks1[i] = "AIRPORT ROAD RYK"
                    if bricks1[i] == "ABU DAHBI ROAD Ryk":
                        bricks1[i] = "ABU DHABI ROAD RYK"
                    if bricks1[i] == "Wireless Pull Ryk":
                        bricks1[i] = "WIRELESS PULL RYK"
                    if bricks1[i] == "NOOR-E-WALI":
                        bricks1[i] = "NOOR E WALI"
                    if bricks1[i] == "IQBAL NAGAR":
                        bricks1[i] = "IQBAL NAGAR RYK"
                    if bricks1[i] == "HOSPITAL ROAD-SDK":
                        bricks1[i] = "HOSPITAL ROAD SDK"
                    if bricks1[i] == "KACHA SADIQA BAD ROAD sdk":
                        bricks1[i] = "KACHA SADIQABAD ROAD"
                    if bricks1[i] == "QAID AZAM ROAD SDK":
                        bricks1[i] = "QUAID AZAM ROAD SDK"
                    if bricks1[i] == "SATTAR SHAHEED ROAD sdk":
                        bricks1[i] = "SATTAR SHAHEED ROAD SDK"
                    if bricks1[i] == "FFC":
                        bricks1[i] = "FAUJI FERTILIZER COMPANY"
                    if bricks1[i] == "HOSPITAL ROAD KHAN PUR":
                        bricks1[i] = "HOSPITAL ROAD KHANPUR"
                    if bricks1[i] == "MODAL TWON kpr":
                        bricks1[i] = "MODEL TOWN KPR"
                    if bricks1[i] == "NAWAKOT ROAD kpr":
                        bricks1[i] = "NAWAKOT ROAD KPR"
                    if bricks1[i] == "BAG-O-BAHAR ROAD KPR":
                        bricks1[i] = "BAG O BAHAR ROAD KPR"
                    if bricks1[i] == "NAWAKOT CHOWK kpr":
                        bricks1[i] = "NAWAKOT CHOWK KPR"
                    if bricks1[i] == "SHUGAR MILL":
                        bricks1[i] = "SUGAR MILL"
                    if bricks1[i] == "NAZ CINEMA ROAD KHAN PUR":
                        bricks1[i] = "NAZ CINEMA ROAD KHANPUR"
                    if bricks1[i] == "BAG-O-BHAR+ BHHISHTI":
                        bricks1[i] = "BAG O BHAR AND BAHISHTI"
                    if bricks1[i] == "PULL SUNNY":
                        bricks1[i] = "SUNNY PULL"
                    if bricks1[i] == "ALLAH BAD":
                        bricks1[i] = "ALLAH ABAD"
                    if bricks1[i] == "AMINA BAD":
                        bricks1[i] = "AMINABAD"
                    if bricks1[i] == "MIAN WALI QURESHI":
                        bricks1[i] = "MIAN WALI QURESHIAN"
                    if bricks1[i] == "KAHI KAIR SHAH":
                        bricks1[i] = "KAHI KHAIR SHAH"
                    if bricks1[i] == "JETHA BUHTA BAZAR kpr":
                        bricks1[i] = "JETHA BHUTA BAZAR"
                    if bricks1[i] == "KACHERY ROAD KHANPUR":
                        bricks1[i] = "KUTCHERY ROAD KHANPUR"
                    if bricks1[i] == "MOR BHUTTA WAAN":
                        bricks1[i] = "MOR BHUTTA WAHAN"
                    if bricks1[i] == "ZAFRA BAD":
                        bricks1[i] = "ZAFARABAD"
                    if bricks1[i] == "PULL SANNY":
                        bricks1[i] = "PULL SUNNY"
                    if bricks1[i] == "WIRLESS PULL":
                        bricks1[i] = "WIRELESS PULL RYK"
                    if bricks1[i] == "KHAN PUR ROAD":
                        bricks1[i] = "KHANPUR ROAD"
                    if bricks1[i] == "GULTION IQBAL":
                        bricks1[i] = "GULSHAN E IQBAL"
                    if bricks1[i] == "IQBAL NAGER":
                        bricks1[i] = "IQBAL NAGAR RYK"
                    if bricks1[i] == "ABBASIA TOWN/ BUSSINESMAN COLONY":
                        bricks1[i] = "ABBASIA TOWN"
                    if bricks1[i] == "SANJER PUR":
                        bricks1[i] = "SUNJAR PUR"
                    if bricks1[i] == "AHMED PUR LAMA":
                        bricks1[i] = "AHMED PUR LAMMA"
                    if bricks1[i] == "PULL 121. CHAK 103":
                        bricks1[i] = "PULL 121 CHAK 103"
                    if bricks1[i] == "TRANDA SAWAI KHAN":
                        bricks1[i] = "TARANDA SWAY KHAN"
                    if bricks1[i] == "NAWAN KOT":
                        bricks1[i] = "NAWAN KOT CITY"
                    if bricks1[i] == "PAKKA LARRAN":
                        bricks1[i] = "PAKKA LARAN"
                    if bricks1[i] == "LIAQUAT PUR CITY":
                        bricks1[i] = "LIAQAT PUR CITY"
                    if bricks1[i] == "TRANDA MUHAMMAD PANA":
                        bricks1[i] = "TRANDA MUHAMMAD PANAH"
                    if bricks1[i] == "THULL HAMZA":
                        bricks1[i] = "THUL HAMZA"
                    if bricks1[i] == "SARDAR GARRH":
                        bricks1[i] = "SARDAR GARH"
                    if bricks1[i] == "CHOWK BAHADER PUR":
                        bricks1[i] = "CHOWK BAHADAR PUR"
                    if bricks1[i] == "JAMAL DEEN WALI":
                        bricks1[i] = "JAMAL DIN WALI"
                    if bricks1[i] == "ABU DHABI ROAD":
                        bricks1[i] = "ABU DHABI ROAD RYK"
                    if bricks1[i] == "JAITHA BHUTTA":
                        bricks1[i] = "JETHA BHUTA BAZAR"
                    if bricks1[i] == "FATEH PUR PANJABIAN":
                        bricks1[i] = "FATEH PUR PUNJABIAN"
                    if bricks1[i] == "RAJAN PUR KALAN":
                        bricks1[i] = "RAJAN PUR"
                    if bricks1[i] == "KHAN PUR CITY 2":
                        bricks1[i] = "KHAN PUR CITY 2"

                for p in range(0, len(bricks1)):
                    for s in range(0, len(sales[p])):
                        child = []
                        child.append(products1[s])
                        child.append(bricks1[p])
                        child.append(sales[p][s])
                        result.append(child)

                for r in result:
                    for i in item_list:
                        if r[0] == i[0]:
                            r.insert(1, i[1])
                            r.append(i[2])
                            # print(r)
                for r in result:
                    for t in tt_list:
                        if r[2] == t[0]:
                            r.insert(4, t[1])
                result = green_team_bricks(result)
                return result

            elif dist_city == "Bahawalnagar" or dist_city == "Bahawalpur":
                bricks = [
                    "BAHAWALNAGAR CITY",
                    "DUNGA BUNGA",
                    "HAROONABAD",
                    "FAQIR WALA",
                    "KHICHI WALA",
                    "FORT ABBAS",
                    "MAROT",
                    "MADRASA",
                    "CHISHTIAN",
                    "DAHRANWALA",
                    "MINCHINABAD",
                    "MCLEOD GANJ",
                    "MANDI SADQ GANJ",
                ]
                bahawalpur_bricks = [
                    "BAHAWALPUR A",
                    "BAHAWALPUR B",
                    "BAHAWALPUR C",
                    "BAHAWALPUR D",
                    "KHAIRPUR",
                    "HASILPUR",
                    "LODHRAN",
                    "KAHROR PAKKA",
                    "YAZMAN CITY",
                    "TAILWALA",
                    "AHMEDPUR",
                    "UCH SHARIF",
                    "MUBARAKPUR",
                ]

                # Product-name -> item-code lookup. Both the old and new PDF
                # formats use (very nearly) the same product names, so one
                # shared list covers both -- a couple of harmless variants
                # (with/without a period) are listed for safety.
                PRODUCT_NAME_TO_CODE = [
                    ("JETEPAR 10ML INJ. 5S", "008999"),
                    ("JETEPAR 10ML INJ 5S", "008999"),
                    ("JETEPAR 2ML INJ. 10S", "004348"),
                    ("JETEPAR 2ML INJ 10S", "004348"),
                    ("JETEPAR CAP. 20S", "002392"),
                    ("JETEPAR CAP 20S", "002392"),
                    ("JETEPAR SYRUP 112ML", "002188"),
                    ("JETEPAR SYP 112ML", "002188"),
                    ("MAIORAD 3ML INJ. 6S", "009072"),
                    ("MAIORAD 3ML INJ 6'S", "009072"),
                    ("MAIORAD TAB. 30S", "012961"),
                    ("MAIORAD TAB 30S", "012961"),
                    ("AFLOXON 150MG CAP. 20S", "008376"),
                    ("AFLOXON 300MG TAB. 30S", "017230"),
                ]

                def code_for(name):
                    for label, code in PRODUCT_NAME_TO_CODE:
                        if label in name:
                            return code
                    return None

                result = []
                new_result = []

                for page in pdf.pages:
                    full_text = page.extract_text()
                    if not full_text:
                        continue

                    text_lines = full_text.split("\n")
                    address_line = text_lines[1] if len(text_lines) > 1 else ""
                    area_bricks = (
                        bahawalpur_bricks
                        if re.search(r"Bahawalpur", address_line)
                        else bricks
                    )

                    if "Product Pack Rate" in full_text:
                        # ============ OLD FORMAT: plain text, no grid lines ============
                        data = re.sub("\n", "$", full_text)
                        data = data.split("$")

                        info = []
                        for d in range(0, len(data)):
                            last_row_remove_len = len(data) - 5
                            if "Product Pack Rate" in data[d]:
                                info = data[d:last_row_remove_len]

                        product_sales = []
                        for i in range(0, len(info)):
                            if info[i] == "BLUE TEAM":
                                product_sales = info[i + 1 :]

                        for ps in product_sales:
                            code = code_for(ps)
                            if code is None:
                                continue
                            cleaned = re.sub(r"\s+", "$", ps)
                            parts = cleaned.split("$")
                            values = parts[-15:-2]  # 13 brick values
                            for brick, val in zip(area_bricks, values):
                                result.append([code, brick, val])

                    else:
                        # ============ NEW FORMAT: real bordered table ============
                        # (this is exactly why the old text-scraping logic
                        # broke here: this report layout no longer has a
                        # "Product Pack Rate ..." text header at all -- it's
                        # a proper table now, so extract_tables() reads it
                        # cleanly instead.)
                        tables = page.extract_tables()
                        if not tables:
                            continue
                        table = tables[0]

                        for row in table[1:]:
                            if not row or len(row) < 4:
                                continue
                            name = row[1] or row[0]
                            if not name or name.strip().lower() == "total":
                                continue
                            code = code_for(name)
                            if code is None:
                                continue
                            values = row[
                                3:-1
                            ]  # drop first 3 label cols + trailing Total col
                            for brick, val in zip(area_bricks, values):
                                qty = (
                                    "0"
                                    if val in (None, "")
                                    else str(val).replace(",", "")
                                )
                                result.append([code, brick, qty])

                for r in range(0, len(result)):
                    for i in item_list:
                        if result[r][0] == i[0]:
                            if result[r][2] != "0":
                                new_result.append(result[r])

                for r in range(0, len(new_result)):
                    for i in item_list:
                        if new_result[r][0] == i[0]:
                            new_result[r].insert(1, i[1])
                            new_result[r].append(i[2])
                for r in new_result:
                    for t in tt_list:
                        if r[2] == t[0]:
                            r.insert(4, t[1])
                return new_result
            elif dist_city == "Dadu":
                NAME_TO_ITEM_CODE = {
                    "AFLOXAN 300MG": "017230",
                    "AFLOXAN CAP 150MG": "008376",
                    "JETEPAR 10 CC INJ": "008999",
                    "JETEPAR 2ML INJ": "004348",
                    "JETEPAR CAP": "002392",
                    "JETEPAR SYP": "002188",
                    "MAIRAD INJ 3ML": "009072",
                    "MAIRAD TAB": "012961",
                    "MILLID 200 MG TAB": "006782",
                }

                # Raw brick text (as printed/extracted from the PDF) -> exact
                # Territory Tree name. Add a line here any time a new/renamed
                # brick shows up in a future month's report.
                BRICK_NAME_MAP = {
                    "BHAN": "BHAN",
                    "DADU": "DADU DU",
                    "JOHI": "JOHI",
                    "K.N.SH": "KHAIRPUR NATHAN SHAH",
                    "KAKAR": "KAKAR",
                    "MAHER": "MEHAR",
                    "PHULJI": "PHULJI",
                    "PIARO": "PIYARO",
                    "SEETA": "SEETA",
                    "SEHWAN": "SEHWAN",
                    "TANDO": "TANDO",
                }

                def canonical_brick(raw_name):
                    key = raw_name.strip().upper()
                    return BRICK_NAME_MAP.get(key, raw_name.strip())

                # -----------------------------------------------------------
                # Low level helpers: work with characters directly instead of
                # extract_text(), because this report's PDF renderer sometimes
                # draws a stray label (e.g. "INJ", "TAB", "150MG") directly on
                # top of the pack-size field, which makes extract_text() /
                # extract_words() interleave the two into garbage like
                # "1510XM2G0". Reading characters + their x/y coordinates lets
                # us undo that.
                # -----------------------------------------------------------

                def cluster_rows(chars, tol=1.5):
                    """Group characters into visual rows by their 'top' coordinate.
                    Coordinates are forced to plain `float` here (some
                    pdfplumber/pdfminer builds hand back `decimal.Decimal`
                    for x0/x1/top instead of float, which then crashes any
                    later arithmetic like `pitch * 0.45` with a
                    "decimal.Decimal and float" TypeError)."""
                    chars = [
                        dict(
                            c, x0=float(c["x0"]), x1=float(c["x1"]), top=float(c["top"])
                        )
                        for c in chars
                    ]
                    chars = sorted(chars, key=lambda c: c["top"])
                    rows, cur, cur_top = [], [], None
                    for c in chars:
                        if cur_top is None or abs(c["top"] - cur_top) <= tol:
                            cur.append(c)
                            cur_top = c["top"] if cur_top is None else cur_top
                        else:
                            rows.append(cur)
                            cur, cur_top = [c], c["top"]
                    if cur:
                        rows.append(cur)
                    for r in rows:
                        r.sort(key=lambda c: c["x0"])
                    return rows

                def chars_to_words(row_chars, gap=2.2):
                    """Turn a sorted list of chars on one row into words, breaking on x-gaps."""
                    words, cur, last_x1 = [], [], None
                    for c in row_chars:
                        if last_x1 is not None and c["x0"] - last_x1 > gap:
                            if cur:
                                words.append(cur)
                            cur = []
                        cur.append(c)
                        last_x1 = c["x1"]
                    if cur:
                        words.append(cur)
                    return [
                        {
                            "text": "".join(c["text"] for c in w),
                            "x0": w[0]["x0"],
                            "x1": w[-1]["x1"],
                            "chars": w,
                        }
                        for w in words
                    ]

                def find_size_anchor(rows, data_zone_x0, pitch):
                    """The pack-size field (e.g. '1X30') always starts at the same
                    fixed x-position on every row, whether or not it collides with
                    a stray overlapping label. Find that anchor from the rows
                    where it's unambiguous."""
                    candidates = []
                    for row in rows:
                        area = [c for c in row if c["x0"] < data_zone_x0]
                        for w in chars_to_words(area):
                            if re.match(r"^\d[\dA-Z]*X\d+$", w["text"]):
                                candidates.append(round(w["x0"], 1))
                    if not candidates:
                        return None
                    return Counter(candidates).most_common(1)[0][0]

                def split_name_size(row_chars, size_anchor_x, pitch):
                    """Reconstruct (product_name, pack_size) from a row's name/size chars."""
                    cs = sorted(row_chars, key=lambda c: c["x0"])
                    if not cs:
                        return "", ""
                    if size_anchor_x is None:
                        words = chars_to_words(cs)
                        if not words:
                            return "", ""
                        return " ".join(w["text"] for w in words[:-1]), words[-1][
                            "text"
                        ]

                    tol = pitch * 0.45
                    slots = {}
                    leftovers = []
                    for c in cs:
                        raw_k = (c["x0"] - size_anchor_x) / pitch
                        k = round(raw_k)
                        if k < 0 or abs(raw_k - k) > 0.45 or k > 12:
                            leftovers.append(c)
                            continue
                        diff = abs(c["x0"] - (size_anchor_x + k * pitch))
                        if diff > tol:
                            leftovers.append(c)
                            continue
                        if k not in slots or diff < slots[k][1]:
                            if k in slots:
                                leftovers.append(slots[k][0])
                            slots[k] = (c, diff)
                        else:
                            leftovers.append(c)

                    size = "".join(slots[k][0]["text"] for k in sorted(slots))
                    leftovers.sort(key=lambda c: c["x0"])
                    name = " ".join(w["text"] for w in chars_to_words(leftovers))
                    return name.strip(), size.strip()

                def parse_report(pdf):
                    """Uses the already-open `pdf` object (no need to reopen the file).
                    Returns (bricks, rows) where `rows` is a list of dicts:
                    {"product": ..., "size": ..., "bricks": {brick_name: qty_str}, "total_qty": ...}
                    """
                    all_rows = []
                    bricks = []
                    for page in pdf.pages:
                        rows = cluster_rows(page.chars, tol=1.5)

                        label_row_idx = None
                        for i, row in enumerate(rows):
                            joined = " ".join(w["text"] for w in chars_to_words(row))
                            if "PRODUCT" in joined and "NAME" in joined:
                                label_row_idx = i
                                break
                        if label_row_idx is None:
                            continue  # not a data page

                        brick_name_chars = []
                        for row in rows[:label_row_idx]:
                            joined = " ".join(w["text"] for w in chars_to_words(row))
                            if "Sale Summaey" in joined or "Page No" in joined:
                                brick_name_chars = []
                                continue
                            brick_name_chars.extend(row)
                        name_words = chars_to_words(brick_name_chars)
                        name_words = [
                            w for w in name_words if w["text"].strip() != "TOTAL"
                        ]

                        code_row_idx = label_row_idx + 1
                        while code_row_idx < len(rows):
                            joined = " ".join(
                                w["text"] for w in chars_to_words(rows[code_row_idx])
                            ).strip()
                            if joined == "QTY":
                                code_row_idx += 1
                                continue
                            break
                        code_words = chars_to_words(rows[code_row_idx])
                        stray = [
                            w
                            for w in code_words
                            if not re.match(r"^<\d+>?$", w["text"])
                        ]
                        for s in stray:
                            nearest = min(
                                name_words, key=lambda w: abs(w["x0"] - s["x0"])
                            )
                            nearest["text"] += s["text"]

                        page_bricks = [w["text"].strip() for w in name_words]
                        n_bricks = len(page_bricks)
                        bricks = page_bricks

                        end_idx = None
                        for i in range(code_row_idx + 1, len(rows)):
                            joined = " ".join(
                                w["text"] for w in chars_to_words(rows[i])
                            )
                            if "TOTAL SALE AMOUNT" in joined:
                                end_idx = i
                                break
                        if end_idx is None:
                            end_idx = len(rows)

                        product_rows = rows[code_row_idx + 1 : end_idx]
                        if not product_rows:
                            continue

                        sample_words = chars_to_words(product_rows[0])
                        numeric_tokens = [
                            w for w in sample_words if re.match(r"^[\d.]+$", w["text"])
                        ]
                        data_zone_x0 = (
                            (numeric_tokens[0]["x0"] - 15) if numeric_tokens else 130
                        )

                        all_gaps = []
                        for row in product_rows:
                            rs = sorted(row, key=lambda c: c["x0"])
                            all_gaps.extend(
                                rs[i + 1]["x0"] - rs[i]["x0"]
                                for i in range(len(rs) - 1)
                            )
                        normal_gaps = [g for g in all_gaps if 3 <= g <= 10]
                        pitch = (
                            (sum(normal_gaps) / len(normal_gaps))
                            if normal_gaps
                            else 6.35
                        )

                        size_anchor_x = find_size_anchor(
                            product_rows, data_zone_x0, pitch
                        )

                        for row in product_rows:
                            name_area = [c for c in row if c["x0"] < data_zone_x0]
                            data_area = [c for c in row if c["x0"] >= data_zone_x0]
                            if not name_area:
                                continue
                            name, size = split_name_size(
                                name_area, size_anchor_x, pitch
                            )
                            values = [w["text"] for w in chars_to_words(data_area)]
                            if len(values) != n_bricks + 1:
                                continue  # summary/footer row, skip
                            all_rows.append(
                                {
                                    "product": name,
                                    "size": size,
                                    "bricks": dict(zip(page_bricks, values[:-1])),
                                    "total_qty": values[-1],
                                }
                            )
                    return bricks, all_rows

                # -----------------------------------------------------------
                # From here on, build the SAME [item_code, brick, qty] ->
                # item_list/tt_list/green_team_bricks pipeline every other
                # district uses, instead of the old dict-shaped build_result()
                # that was never actually called (it lived inside a dead
                # `if __name__ == "__main__":` block that never runs here).
                # -----------------------------------------------------------
                result = []
                new_result = []

                bricks, parsed_rows = parse_report(pdf)

                for pr in parsed_rows:
                    item_code = NAME_TO_ITEM_CODE.get(pr["product"])
                    if not item_code:
                        continue
                    for raw_brick, qty in pr["bricks"].items():
                        result.append([item_code, canonical_brick(raw_brick), qty])

                for r in range(0, len(result)):
                    for i in item_list:
                        if result[r][0] == i[0]:
                            if result[r][2] != "0":
                                new_result.append(result[r])

                for r in range(0, len(new_result)):
                    for i in item_list:
                        if new_result[r][0] == i[0]:
                            new_result[r].insert(1, i[1])
                            new_result[r].append(i[2])
                for r in new_result:
                    for t in tt_list:
                        if r[2] == t[0]:
                            r.insert(4, t[1])
                new_result = green_team_bricks(new_result)
                return new_result
            # elif dist_city == "Bahawalpur":
            #     products = []
            #     bricks = []
            #     sales = []
            #     result = []
            #     new_result = []
            #     for x in range(0, len(pdf.pages)):
            #         data = pdf.pages[x].extract_table()
            #         bricks = data[0][2:-1]
            #         for b in range(0, len(bricks)):
            #             if "13-Soling" in bricks[b]:
            #                 bricks[b] = "13-SOLING"
            #             if "Adda 42 \nDB" in bricks[b]:
            #                 bricks[b] = "ADDA 42 DB"
            #             if "ADDA \nSHAHNAL" in bricks[b]:
            #                 bricks[b] = "ADDA SHAHNAL"
            #             if "Ahmed pur \n(City)" in bricks[b]:
            #                 bricks[b] = "AHMEDPUR"
            #             if "Bahawalpu\nr (A)" in bricks[b]:
            #                 bricks[b] = "BAHAWALPUR A"
            #             if "Bahawalpu\nr (B)" in bricks[b]:
            #                 bricks[b] = "BAHAWALPUR B"
            #             if "Bahawalpu\nr (C)" in bricks[b]:
            #                 bricks[b] = "BAHAWALPUR C"
            #             if "Bahawalpu\nr (D)" in bricks[b]:
            #                 bricks[b] = "BAHAWALPUR D"
            #             if "Chandi \nChowk" in bricks[b]:
            #                 bricks[b] = "CHANDI CHOWK"
            #             if "CHANNI \nGOTH" in bricks[b]:
            #                 bricks[b] = "CHANNI GOTH"
            #             if "Chowk \nBhatta" in bricks[b]:
            #                 bricks[b] = "CHOWK BHATTA"
            #             if "Chuna \nWala" in bricks[b]:
            #                 bricks[b] = "CHUNA WALA"
            #             if "Dera \nBakha" in bricks[b]:
            #                 bricks[b] = "DERA BAKHA"
            #             if "Hasilpur \nCity" in bricks[b]:
            #                 bricks[b] = "HASILPUR"
            #             if "Hataji" in bricks[b]:
            #                 bricks[b] = "HATAJI"
            #             if "Head Raj \nkan" in bricks[b]:
            #                 bricks[b] = "HEAD RAJ KAN"
            #             if "Kahror \nPacca City" in bricks[b]:
            #                 bricks[b] = "KAHROR PAKKA"
            #             if "Khan Qah \nSharif" in bricks[b]:
            #                 bricks[b] = "KHAN QAH SHARIF"
            #             if "Kotla Musa \nKhan" in bricks[b]:
            #                 bricks[b] = "KOTLA MUSA KHAN"
            #             if "Lal \nSohanra" in bricks[b]:
            #                 bricks[b] = "LAL SOHANRA"
            #             if "Lodhran \nCity" in bricks[b]:
            #                 bricks[b] = "LODHRAN"
            #             if "Mubarak \npur (City)" in bricks[b]:
            #                 bricks[b] = "MUBARAKPUR"
            #             if "Musafir \nKhana" in bricks[b]:
            #                 bricks[b] = "MUSAFIR KHANA"
            #             if "Noor Pur \nNouranga" in bricks[b]:
            #                 bricks[b] = "NOOR PUR NOURANGA"
            #             if "Pull Farooq \nAbad" in bricks[b]:
            #                 bricks[b] = "PULL FAROOQ ABAD"
            #             if "Qaim pur" in bricks[b]:
            #                 bricks[b] = "QAIM PUR"
            #             if "Shahi Wala \nBungla" in bricks[b]:
            #                 bricks[b] = "SHAHI WALA BUNGLA"
            #             if "Tailwala" in bricks[b]:
            #                 bricks[b] = "TAILWALA"
            #             if "Uch Sharif \n(City)" in bricks[b]:
            #                 bricks[b] = "UCH SHARIF"
            #             if "Yazman \nCity" in bricks[b]:
            #                 bricks[b] = "YAZMAN CITY"
            #             if "ADDA \nPARMET" in bricks[b]:
            #                 bricks[b] = "ADDA PARMET"

            #         # print(data[3:])
            #         product = data[3:]
            #         product1 = product[::2]
            #         products = []
            #         for p in range(0, len(product1)):
            #             products.append(product1[p][0:][1])
            #         for p in range(0, len(products)):
            #             if "JETEPAR 10ML" in products[p]:
            #                 products[p] = "008999"
            #             if "JETEPAR 2ML" in products[p]:
            #                 products[p] = "004348"
            #             if "JETEPAR CAP" in products[p]:
            #                 products[p] = "002392"
            #             if "JETEPAR SYRUP" in products[p]:
            #                 products[p] = "002188"
            #             if "MAIORAD 3ML" in products[p]:
            #                 products[p] = "009072"
            #             if "MAIORAD TAB" in products[p]:
            #                 products[p] = "012961"
            #             if "AFLOXAN CAP" in products[p]:
            #                 products[p] = "008376"
            #             if "AFLOXAN TAB" in products[p]:
            #                 products[p] = "017230"

            #         sale = data[3:]
            #         sale1 = sale[::2]
            #         sales = []
            #         for s in range(0, len(sale1)):
            #             sales.append(sale1[s][0:][2:])
            #             for s in range(0, len(sales)):
            #                 for i in range(0, len(sales[s])):
            #                     if sales[s][i] == "":
            #                         sales[s][i] = "0"

            #         for p in range(0, len(products)):
            #             for s in range(0, len(sales)):
            #                 for i in range(0, len(sales[s])):
            #                     # print(products[p],bricks[b],sales[s][i])
            #                     child = []
            #                     child.append(products[p])
            #                     child.append(bricks[b])
            #                     child.append(sales[s][i])
            #                     result.append(child)
            #         for r in range(0, len(result)):
            #             for i in item_list:
            #                 if result[r][0] == i[0]:
            #                     if result[r][2] != "0":
            #                         new_result.append(result[r])
            #         # print(len(new_result))
            #         for r in range(0, len(new_result)):
            #             for i in item_list:
            #                 if new_result[r][0] == i[0]:
            #                     new_result[r].insert(1, i[1])
            #                     new_result[r].append(i[2])
            #                     # print(new_result[r])
            #         for r in new_result:
            #             for t in tt_list:
            #                 if r[2] == t[0]:
            #                     r.insert(4, t[1])
            #         new_result = green_team_bricks(new_result)
            #         return new_result
