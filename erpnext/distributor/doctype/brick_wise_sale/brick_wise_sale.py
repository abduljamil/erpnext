# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt
from dataclasses import fields
from dis import distb
import io
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


# brick capture support (added)
_debug_bricks = []


def _capture_bricks_from_locals(local_vars):
    """Insert `_capture_bricks_from_locals(locals())` right before every
    `return result` / `return new_result` / `return end_result` line in
    _parse_pdf. It grabs whichever of these names holds the branch's final
    brick list, in priority order, without needing to know per-branch
    which name was used."""
    global _debug_bricks
    for key in ("bricks2", "bricks1", "all_bricks", "bricks", "brick", "area_bricks"):
        val = local_vars.get(key)
        if val:
            _debug_bricks = [str(n).strip() for n in val if n and str(n).strip()]
            return


@frappe.whitelist(allow_guest=True)
def _parse_pdf(pdf_file, parse_check, parent_detail):
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
        doc = fitz.open(path)
        page1 = doc[0]
        page1_text = page1.get_text()

    if dist_city == "Gujrat" and "PRODUCT NAME" in page1_text:
        import io as _io
        from collections import defaultdict as _defaultdict

        with open(path, "rb") as _f:
            _pdf_bytes = _f.read()
        _pdf_bytes = _pdf_bytes.replace(b"/CreatorDate (\r\n", b"/CreatorDate ()\r\n")
        _pdf_bytes = _pdf_bytes.replace(b"/CreatorDate (\n", b"/CreatorDate ()\n")

        with pdfplumber.open(_io.BytesIO(_pdf_bytes)) as _pdf:
            _page = _pdf.pages[0]
            _words = _page.extract_words(x_tolerance=1)

        _rows_map = _defaultdict(list)
        for _w in _words:
            _rows_map[round(_w["top"], 1)].append(_w)
        _sorted_tops = sorted(_rows_map.keys())

        _numeric_re = re.compile(r"^-?\d+(\.\d+)?$")

        # ---- 1. header row se bricks (column names) nikaalna, x-position ke sath ----
        header_tokens = None
        header_top = None
        for _top in _sorted_tops:
            _line = sorted(_rows_map[_top], key=lambda w: w["x0"])
            _texts = [w["text"] for w in _line]
            if len(_texts) >= 2 and _texts[0] == "PRODUCT" and _texts[1] == "NAME":
                header_tokens = _line[2:]
                header_top = _top
                break

        if header_tokens is None:
            frappe.throw(
                "Gujrat (new format) PDF: header row (PRODUCT NAME ...) not found"
            )

        bricks = []
        header_x = []
        for _w in header_tokens:
            # header labels like "(SRGO" / "CPAK)" carry stray brackets - strip them
            bricks.append(_w["text"].strip("()"))
            header_x.append(_w["x0"])

        # If any of the brick names above don't exactly match your
        # Territory Tree spelling, put the correction here:
        #   "name as it comes out of the PDF": "correct Territory Tree name"
        # Example: "ShaD": "SHAHDARA GUJRAT",
        BRICK_RENAME = {
            # "PDF NAME": "TERRITORY TREE NAME",
            "PHAR": "PAHRIANWALI",
            "KOTL": "KOTLA",
            "FPUR": "FATEH PUR",
            "MANG": "MANGOWAL",
            "KUNJ": "KUNJAH",
            "DOLT": "DOLAT",
            "TAND": "TANDA",
            "SRGO": "SARGO",
            "KUTC": "KUTCH",
            "MUSL": "MUSLI",
            "JINH": "JINNA",
            "CIRC": "CIRCU",
            "RAMT": "RAMTA",
            "KHIR": "KHARIAN",
            "LALA": "LALAMUSA GUJRAT",
            "JPJ": "JALAL PUR JATTAN",
            "DNGA": "DINGA GUJRAT",
            "ShaF": "SHAHF",
            "ShaD": "SHAHD",
            "PHAL": "PHALIA",
            "MBD": "MANDI.B.DIN",
        }
        bricks = [BRICK_RENAME.get(b, b) for b in bricks]

        _edges = [(header_x[i] + header_x[i + 1]) / 2 for i in range(len(header_x) - 1)]

        def _bin_index(x):
            idx = 0
            for e in _edges:
                if x > e:
                    idx += 1
                else:
                    break
            return idx

        # ---- 3. har product row parse karna: naam + values (bin-matched) ----
        products = []
        sales = []
        for _top in _sorted_tops:
            if _top <= header_top:
                continue
            _line = sorted(_rows_map[_top], key=lambda w: w["x0"])
            if not _line:
                continue
            if _line[0]["text"] == "Total":
                # "Total Rs/=" row aur uske baad wali continuation lines
                # sirf grand-totals hain, product-wise sales nahi - stop here.
                break
            _name_parts = []
            _value_words = []
            _started_values = False
            for _w in _line:
                if not _started_values and not _numeric_re.match(_w["text"]):
                    _name_parts.append(_w["text"])
                else:
                    _started_values = True
                    if _numeric_re.match(_w["text"]):
                        _value_words.append(_w)
            if not _name_parts:
                continue
            _product_name = " ".join(_name_parts)
            _row_sales = ["0"] * len(bricks)
            for _w in _value_words:
                idx = _bin_index(_w["x0"])
                if 0 <= idx < len(bricks):
                    _row_sales[idx] = _w["text"]
            products.append(_product_name)
            sales.append(_row_sales)

        # ---- 4. product x brick nested loop, zero sale skip ----
        for p in range(0, len(products)):
            for b in range(0, len(bricks)):
                if sales[p][b] == "0":
                    continue
                child = []
                child.append(products[p])
                child.append(bricks[b])
                child.append(sales[p][b])
                result.append(child)

        NAME_TO_CODE = {
            "Cyanorin Fort Amp": "005425",
            "Jetepar 10ml Amps 5's": "008999",
            "Jetepar 2ml Amps 10's": "004348",
            "Jetepar Cap 20's": "002392",
            "Jetepar Syrup 112ml": "002188",
            "Maiorad 3ml Amps 6's": "009072",
            "Maiorad Tab 3*10's": "012961",
            "Metronidazole Tab": "081274",
            "Moxilium Syrup 125mg": "006783",
            "Supracef Cap 5's": "024820",
            "Supracef Susp 30ml": "024819",
            "Maiorad Tab 30's": "012961",
            "Moxilium Syrup 250mg": "012649",
            "Vikonon Fort Syrup": "006406",
        }

        for r in result:
            if r[0] in NAME_TO_CODE:
                r[0] = NAME_TO_CODE[r[0]]
                continue
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

        for r in result:
            for i in item_list:
                if r[0] == i[0]:
                    r.insert(1, i[1])
                    r.append(i[2])
        result = green_team_bricks(result)
        for r in result:
            for t in tt_list:
                if r[2] == t[0]:
                    r.insert(4, t[1])
        return result

    elif dist_city == "Gujrat":
        # ---- OLD FORMAT (existing dashed-line report) -- UNCHANGED ----
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
        words = page1.get_text("words")
        for i in range(0, len(words)):
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
        for k in range(b_s_index, b_e_index):
            bricks.append(words[k][4])

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
            bricks[b] = re.sub("MBD", "MANDI.B.DIN", bricks[b])

        for i in range(s_s_index, s_e_index):
            if words[i][0] > 100:
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
        for i in range(0, len(sales)):
            add_zeros = 14 - len(sales[i])
            for k in range(0, add_zeros):
                sales[i].append("0")

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
        result = green_team_bricks(result)
        for r in result:
            for t in tt_list:
                if r[2] == t[0]:
                    r.insert(4, t[1])
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
            if bricks[i] == "WORK" and Second_sheet_var == True:
                bricks[i] = "WORK SHOP ROAD SKR2"
            if bricks[i] == "WSALE" and Second_sheet_var == True:
                bricks[i] = "WHOLE SALE SUKKUR SKR2"
            if bricks[i] == "AYUBG" and Second_sheet_var == True:
                bricks[i] = "AYUB GAT SUKKUR"
            if bricks[i] == "SBMND":
                bricks[i] = "SABZI MANDI"
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
            if bricks[i] == "GMBAT" and Second_sheet_var == False:
                bricks[i] = "GAMBAT"
            if bricks[i] == "HLANI" and Second_sheet_var == False:
                bricks[i] = "HALANI"
            if bricks[i] == "HNGOR" and Second_sheet_var == False:
                bricks[i] = "HINGORJA"
            if bricks[i] == "JCD" and Second_sheet_var == False:
                bricks[i] = "JACOBABAD SUKKUR"
            if bricks[i] == "JHANI" and Second_sheet_var == False:
                bricks[i] = "JAHANIYA"
            if bricks[i] == "JINAH" and Second_sheet_var == False:
                bricks[i] = "JINNAH CHOWK"
            if bricks[i] == "K.BNG" and Second_sheet_var == False:
                bricks[i] = "KOT BANGLOW"
            if bricks[i] == "KHAI" and Second_sheet_var == False:
                bricks[i] = "KHAI SUKKUR"
            if bricks[i] == "KHP" and Second_sheet_var == False:
                bricks[i] = "KHAIRPUR"
            if bricks[i] == "KHPCV" and Second_sheet_var == False:
                bricks[i] = "KHAIR PUR CIVIL"
            if bricks[i] == "KNDYA" and Second_sheet_var == False:
                bricks[i] = "KANDYARD"
            if bricks[i] == "KPS" and Second_sheet_var == False:
                bricks[i] = "KHAIRPUR PUBLIC SCHOOL & COLLEGE"
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
            if bricks[i] == "SUKTW" and Second_sheet_var == False:
                bricks[i] = "SUKKUR TOWNSHIP SKR1"
            if bricks[i] == "SUKUR" and Second_sheet_var == False:
                bricks[i] = "SUKKUR SKR1"
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
            # if bricks[i] == "MNRAR":
            #     bricks[i] = "MINARA ROAD"
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
        result = green_team_bricks(result)
        for r in result:
            for t in tt_list:
                if r[2] == t[0]:
                    r.insert(4, t[1])
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
            if bricks[i] == " AUTO BHAN ROAD":
                bricks[i] = "AUTO BAHN ROAD"
            if bricks[i] == "RUKKAN BURIRA":
                bricks[i] = "RUKAN BURIRA"
            if bricks[i] == "JAMSHORRO":
                bricks[i] = "JAMSHORO"

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

        for r in new_result:
            for i in item_list:
                if r[0] == i[0]:
                    r.insert(1, i[1])
                    r.append(i[2])
        new_result = green_team_bricks(new_result)
        for r in new_result:
            for t in tt_list:
                if r[2] == t[0]:
                    r.insert(4, t[1])

        return new_result

    elif dist_city == "Thatta":
        result = []
        new_result = []

        # Excel/PDF header ka naam -> Territory Tree naam (purane short naam aur naye poore naam dono)
        THT_BRICKS = {
            "BAGHN": "BAGHAN THT",
            "BAGHAN": "BAGHAN THT",
            "BUHUR": "BUHURO",
            "CHAJN": "CHACH JAHAN",
            "DABHE": "DHABEEJI",
            "DABHEEJI": "DHABEEJI",
            "JHARK": "JHIRK SIDE",
            "JHARIK SIDE": "JHIRK SIDE",
            "JHIMP": "JHAMPIR",
            "JHIMPIR": "JHAMPIR",
            "SUJAW": "SUJAWAL",
            "THT": "THATTA THT",
            "THATTA": "THATTA THT",
            "C.CND": "CHATO CHAND",
            "CHOUH": "CHOUHAR JAMALI",
            "GAGAR": "GHAGHAR",
            "GHULM": "GHULLAMULLAH",
            "KHORW": "KHORWA",
            "NORAD": "NOORIABAD",
            "S.KRM": "SHAH KARIM",
            "BATHO": "BATHORO",
            "GOHRA": "GHORA BARI",
            "GULMD": "GUL MANDA",
            "GULMANDA": "GUL MANDA",
            "J,CHK": "JATI CHOWK",
            "JUNGS": "JUNGSHAI",
            "N.B": "NOOHBHATI",
            "P,T": "PATHAN COLONY",
            "GARHOO": "GARHO",
        }

        # (required keywords, item code) - pehla match jeetega. SYRUP pehle taake "112ML" 2ML se na takraye
        THT_PRODUCTS = [
            (("JETEPAR", "SYRUP"), "002188"),
            (("JETEPAR", "SYP"), "002188"),
            (("JETEPAR", "SYR"), "002188"),
            (("JETEPAR", "CAP"), "002392"),
            (("JETEPAR", "10ML"), "008999"),
            (("JETEPAR", "10CC"), "008999"),
            (("JETEPAR", "2ML"), "004348"),
            (("JETEPAR", "2CC"), "004348"),
            (("MAIORAD", "TAB"), "012961"),
            (("MAIORAD", "INJ"), "009072"),
            (("MAIORAD", "AMP"), "009072"),
            (("MAIORAD", "3ML"), "009072"),
            (("AFLOXON", "CAP"), "008376"),
            (("AFLOXAN", "CAP"), "008376"),
            (("AFLOXON", "TAB"), "017230"),
            (("AFLOXAN", "TAB"), "017230"),
            (("AFLOXON", "300"), "017230"),
            (("AFLOXAN", "300"), "017230"),
            (("AFLOXON", "150"), "008376"),
            (("AFLOXAN", "150"), "008376"),
            (("METRONIDAZOLE", "400"), "081274"),
            (("METRONIDAZOLE", "200"), "008909"),
            (("MOXILIUM", "DROP"), "006782"),
            (("MOXILIUM", "125"), "006783"),
            (("MOXILIUM", "250", "SYP"), "012649"),
            (("MOXILIUM", "250", "SUS"), "012649"),
            (("MOXILIUM", "250"), "006784"),
            (("MOXILIUM", "500"), "008908"),
            (("CYANORIN",), "005425"),
            (("DEPROGESIC", "P"), "081838"),
            (("EBAST",), "023906"),
            (("HISTAFEX", "120"), "031037"),
            (("HISTAFEX", "180"), "031038"),
            (("AVOR", "2"), "007853"),
            (("AVOR", "1"), "006584"),
            (("OBEXIL",), "032259"),
            (("PC-LAC",), "019133"),
            (("P.C.LAC",), "019133"),
            (("PROBITOR",), "016654"),
            (("SAVELOX", "250"), "032255"),
            (("SAVELOX", "500"), "029328"),
            (("SUPRACEF", "CAP"), "024820"),
            (("SUPRACEF", "DS"), "028727"),
            (("SUPRACEF", "SUS"), "024819"),
            (("SUPRALOX",), "028728"),
            (("TRAMAGESIC", "INJ"), "026920"),
            (("TRAMAGESIC", "CAP"), "029327"),
            (("VIGROL",), "007018"),
            (("VIKONON",), "006406"),
            (("VIKNON",), "006406"),
        ]

        def tht_product(name):
            n = re.sub(r"\(.*?\)", " ", str(name))  # "(TP: 450.50)" hata dein
            n = re.sub(r"\s+", " ", n).strip().upper()
            if not n or n.startswith(("PCW TEAM", "TTL", "G TTL", "ITEM", "NAN")):
                return None
            for kws, code in THT_PRODUCTS:
                if all(k in n for k in kws):
                    return code
            print(f"[Thatta] product not recognised, skipped: '{n}'")
            return None

        def tht_qty(v):
            if v is None:
                return "0"
            s = str(v).replace(",", "").strip()
            if s == "" or s.lower() == "nan":
                return "0"
            try:
                f = float(s)
            except ValueError:
                return "0"
            return str(int(f)) if f == int(f) else str(f)

        # Report kai sheets mein bati ho sakti hai (har sheet mein kuch bricks) - saari sheets parhein
        sheets = pd.read_excel(path, sheet_name=None, header=None)
        for sname, df in sheets.items():
            hdr_i = None
            for i in range(len(df)):
                if str(df.iat[i, 0]).strip().upper() == "ITEM":
                    hdr_i = i
                    break
            if hdr_i is None:
                continue

            # brick columns: "TTL QTY" / "TTL AMT" se pehle tak
            cols = []
            for c in range(1, len(df.columns)):
                h = df.iat[hdr_i, c]
                if pd.isna(h):
                    continue
                h = re.sub(r"\s+", " ", str(h)).strip().upper()
                if h.startswith("TTL"):
                    break
                cols.append((c, THT_BRICKS.get(h, h)))

            for i in range(hdr_i + 1, len(df)):
                first = re.sub(r"\s+", " ", str(df.iat[i, 0])).strip().upper()
                if first.startswith("G TTL"):
                    break
                code = tht_product(first)
                if code is None:
                    continue
                for c, bname in cols:
                    q = tht_qty(df.iat[i, c])
                    if q != "0":
                        result.append([code, bname, q])

        for r in range(0, len(result)):
            for i in item_list:
                if result[r][0] == i[0]:
                    new_result.append(result[r])
        for r in new_result:
            for i in item_list:
                if r[0] == i[0]:
                    r.insert(1, i[1])
                    r.append(i[2])
        new_result = green_team_bricks(new_result)
        for r in new_result:
            for t in tt_list:
                if r[2] == t[0]:
                    r.insert(4, t[1])
        return new_result

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
            if bricks[b] == "ISLAMKOT ":
                bricks[b] = "ISLAMKOT"
            if bricks[b] == "JHILORI":
                bricks[b] = "JHULURI"

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
        result = green_team_bricks(result)
        for r in result:
            for t in tt_list:
                if r[2] == t[0]:
                    r.insert(4, t[1])
        return result

    elif dist_city == "Nawab Shah":
        products = []
        bricks = []
        sales = []
        result = []
        df = pd.read_excel(path, header=None)

        header_row_idx = None
        for i in range(len(df)):
            if str(df.iat[i, 0]).strip().upper() == "ITEM":
                header_row_idx = i
                break

        if header_row_idx is None:
            print("DEBUG: 'ITEM' header row nahi mila")
            # return []

        header_row = df.iloc[header_row_idx]

        ttl_qty_col = None
        for c in range(2, len(header_row)):
            if str(header_row[c]).strip().upper() == "TTL QTY":
                ttl_qty_col = c
                break
        if ttl_qty_col is None:
            ttl_qty_col = len(header_row) - 2

        brick_cols = list(range(2, ttl_qty_col))

        bricks = [str(header_row[c]).strip().upper() for c in brick_cols]
        for b in range(0, len(bricks)):
            if bricks[b] == "N.FEROZ":
                bricks[b] = "NAUSHAHRO FEROZ"
            if bricks[b] == "T.SHAH":
                bricks[b] = "T SHAH"
            if bricks[b] == "B.CITY":
                bricks[b] = "BHIRIA CITY"
            if bricks[b] == "B.ROAD":
                bricks[b] = "BHIRIA ROAD"
            if bricks[b] == "P.CHANG":
                bricks[b] = "PACCA CHANG"
            if bricks[b] == "D.PUR":
                bricks[b] = "DAULAT PUR"
            if bricks[b] == "NAWABSHAH":
                bricks[b] = "NAWABSHAH NWS"
            if bricks[b] == "THARUSHAH":
                bricks[b] = "THARU SHAH"

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

        print(
            "DEBUG: result BEFORE matching (total rows =",
            len(result),
            ") sample:",
            result[:5],
        )

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

            best_ratio = 0
            best_code = None
            exact_found = False

            r0_clean = r[0].strip().upper()

            for i in item_list:
                if r0_clean == i[1].strip().upper():
                    best_code = i[0]
                    exact_found = True
                    break

            if not exact_found:
                for i in item_list:
                    final_result = fuzz.ratio(r0_clean, i[1].strip().upper())
                    if final_result > best_ratio:
                        best_ratio = final_result
                        best_code = i[0]

                if best_ratio < 95:  # confidence threshold - tune as needed
                    print(
                        f"DEBUG: NO CONFIDENT MATCH for '{r[0]}' -> best guess was "
                        f"'{best_code}' with ratio {best_ratio}"
                    )
                    best_code = None

            r[0] = best_code

        for r in result:
            for i in item_list:
                if r[0] == i[0]:
                    r.insert(1, i[1])
                    r.append(i[2])
        result = green_team_bricks(result)
        for r in result:
            for t in tt_list:
                if r[2] == t[0]:
                    r.insert(4, t[1])
        return result

    else:
        with open(path, "rb") as f:
            _pdf_bytes = f.read()
        _pdf_bytes = _pdf_bytes.replace(b"/CreatorDate (\r\n", b"/CreatorDate ()\r\n")
        _pdf_bytes = _pdf_bytes.replace(b"/CreatorDate (\n", b"/CreatorDate ()\n")
        with pdfplumber.open(io.BytesIO(_pdf_bytes)) as pdf:
            if dist_city == "Lahore":
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
                                    if b[c] == "1010115":
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
                                    elif b[c] == "1010109":
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
                                    elif b[c] == "TEZAB AAHATA":
                                        b[c] = "TEHZAB AAHATA"
                                    elif b[c] == "JALLO PIND":
                                        b[c] = "JALLO PARK"
                                    elif b[c] == "TEZAB AAHA":
                                        b[c] = "TEHZAB AAHATA"
                                    elif b[c] == "THOKAR NIA":
                                        b[c] = "THOKAR NAIZ BAIG"
                                    elif b[c] == "1010114":
                                        b[c] = "BAND ROAD"
                                    elif b[c] == "1010102":
                                        b[c] = "AL FAISAL TOWN"
                                    elif b[c] == "1010137":
                                        b[c] = "GT ROAD MANAWA"
                                    elif b[c] == "1010139":
                                        b[c] = "GARHI SHAHU BAZAR"
                                    elif b[c] == "1010147":
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
                                    elif b[c] == "KOT ABDUL MALIK":
                                        print("Hello")
                                        b[c] = "KOT ABDUL MALIK LHR1"

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
                    PRODUCT_CODES = ["002392", "002188", "004348", "008999"]
                    NAME_X0_CUTOFF = 105

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

                    result = green_team_bricks(result)
                    for r in result:
                        for t in tt_list:
                            if r[2] == t[0]:
                                r.insert(4, t[1])
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
                result = green_team_bricks(result)
                for r in result:
                    for t in tt_list:
                        if r[2] == t[0]:
                            r.insert(4, t[1])
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
                        for i in range(1, len(data) - 2):
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
                            b[c] = "THENG MORE"
                        if b[c] == "KS3":
                            b[c] = "KASUR 3"
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
                final_list = [item for z in zipped_list for item in z]
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
                end_result = green_team_bricks(end_result)
                for r in range(0, len(end_result)):
                    for t in tt_list:
                        if end_result[r][2] == t[0]:
                            end_result[r].insert(4, t[1])
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
                new_bricks = [
                    "AKHTER ABAD",
                    "BANGLA GOGERA",
                    "BASIR PUR",
                    "DEPAL PUR",
                    "DEPAL PUR CHOWK",
                    "DHA 1",
                    "DHA 2",
                    "FAISLA ABAD ROAD",
                    "GAMBER & CANTT",
                    "HABIB ABAD OKARA",
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
                        bricks[b] = "GAMBER & CANTT"
                    if "U\nO\nERA+YG PUR\nGN\nO\nG" in bricks[b]:
                        bricks[b] = "GOGERA"
                    if "D\nA\nB\nA\nB \nBI\nA\nH" in bricks[b]:
                        bricks[b] = "HABIB ABAD OKARA"
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
                result = green_team_bricks(result)
                for r in result:
                    for t in tt_list:
                        if r[2] == t[0]:
                            r.insert(4, t[1])
                return result

            elif dist_city == "Karachi":
                result = []
                new_result = []
                KHI_BRICKS = [
                    ("AL-ASIF SQUARE", "AL ASIF SQUARE"),
                    ("AZAM-BASTI,MEHMOODABAD", "AZAM-BASTI AND MEHMOODABAD"),
                    ("CIVIL HOSPITAL", "CIVIL HOSPITAL KHI"),
                    ("CLIFTON,DEFENCE", "CLIFTON AND DEFENCE"),
                    ("FEDERAL. B.AREA", "FEDERAL B AREA"),
                    ("GULISTAN-E-JAUHAR", "GULISTAN E JAUHAR"),
                    ("GULSHAN-E-IQBAL", "GULSHAN E IQBAL KHI"),
                    ("J.P.M.C, CANTT STATION", "J.P.M.C AND CANTT STATION"),
                    ("KAHTOOR,GADAP.", "KAHTOOR AND GADAP"),
                    (
                        "LANDHI,QUAIDABAD,OLD MUZAFABAD",
                        "LANDHI AND QUAIDABAD AND OLD MUZAFABAD",
                    ),
                    ("LIAQATABAD", "LIAQUATABAD"),
                    ("LYARI,CHAKIWARA", "LYARI AND CHAKIWARA"),
                    ("P.I.B,NEW TOWN", "PIR ILAHI BUKSH AND NEW TOWN"),
                    ("RANCHORE LINE, USMANABAD", "RANCHORE LANE AND USMANABAD"),
                    ("SADDAR", "SADDAR KHI"),
                    ("SHAH FAISAL COLONY", "SHAH FAISAL COLONY KHI"),
                    ("SOILDER BAZAR,GARDEN WEST", "SOILDER BAZAR AND GARDEN WEST"),
                    ("TOWER,BURNS ROAD", "TOWER AND BURNS ROAD"),
                    (
                        "WINDER,UTHAL,BELA,COASTLY BELT.",
                        "WINDER AND UTHAL AND BELA AND COASTLY BELT",
                    ),
                    ("ANKELASRIA HOSPITAL", "ANKLESARIA HOSPITAL"),
                ]

                def khi_brick(cell):
                    b = re.sub(r"\s+", " ", str(cell)).strip()
                    for key, name in KHI_BRICKS:
                        if key in b:
                            return name
                    return b

                def khi_code(header, pack):
                    """Header PDF ke hisaab se kat jata hai / kabhi kabhi padosi harf chipak jata hai
                    (e.g. 'AJETEPAR .10 M'), is liye naam + pack ke keywords se pehchante hain."""
                    h = re.sub(r"[^A-Z0-9]", "", str(header).upper())
                    pk = re.sub(r"[^A-Z0-9]", "", str(pack).upper())
                    if not h:
                        return None
                    if re.search(r"CYNRIN|CNORN|CYANORIN", h):
                        return "005425"
                    if re.search(r"DPROG|PROGS", h):
                        return "081838"
                    if "EBAST" in h:
                        return "023906"
                    if re.search(r"HIS\w*?180", h):
                        return "031038"
                    if re.search(r"HIS\w*?120", h):
                        return "031037"
                    if re.search(r"ISR\w*?1MG", h):
                        return "035294"
                    if re.search(r"ISR\w*?2MG", h):
                        return "035295"
                    if re.search(r"JETEPAR|JTPAR|JTPR", h):
                        if "CAP" in h:
                            return "002392"
                        if "SYR" in h or "SYP" in h or pk.startswith("112ML"):
                            return "002188"
                        if pk.startswith("2ML") or (
                            "INJ" in h and "2" in h and "10" not in h
                        ):
                            return "004348"
                        if "10" in h or pk.startswith("10ML"):
                            return "008999"
                    if re.search(r"MAI?ORAD", h):
                        if "TAB" in h:
                            return "012961"
                        return "009072"
                    if re.search(r"MALTM|MALTEM", h):
                        return "071560"
                    if re.search(r"METRON|MTRN", h):
                        return "008909" if "200" in h else "081274"
                    if re.search(r"MINGIR|MINGAIR|MNGAR|MNGIR", h):
                        return "038427" if "10" in h else "038426"
                    if re.search(r"^[A-Z0-9]?(MOX|MXL)", h):
                        if not re.search(r"\d", h):
                            return "006782"
                        if "125" in h:
                            return "006783"
                        if "500" in h:
                            return "008908"
                        if "250" in h:
                            return "012649" if "ML" in pk else "006784"
                    if "OBEX" in h:
                        return "032259"
                    if re.search(r"PCLC|PCLAC", h):
                        return "019133"
                    if "PROB" in h:
                        return "016654"
                    if re.search(r"SAVEL|SAVLOX|SAVELOX", h):
                        return "029328" if "500" in h else "032255"
                    if re.search(r"SPRCEF|SUPRCEF|SUPARCF|SUPRACEF", h):
                        if "DS" in h:
                            return "028727"
                        if "SUS" in h:
                            return "024819"
                        return "024820"
                    if re.search(r"SUPRLOX|SUPRALOX", h):
                        return "028728"
                    if "TRAM" in h:
                        if "SIC" in h or "INJ" in h:
                            return "026920"
                        return "029327" if "5" in h else "026920"
                    if "VIGROL" in h:
                        return "007018"
                    if re.search(r"VIKNN|VIKON", h):
                        return "006406"
                    if re.match(r"^(AVOR|AVR)", h):
                        return "006584" if "1MG" in h else "007853"
                    return None

                def khi_qty(cell):
                    """'10+2' -> 12 (sale + bonus), '-2' -> -2, '' -> 0"""
                    s = str(cell or "").replace(",", "")
                    nums = re.findall(r"[+-]?\d+(?:\.\d+)?", s)
                    if not nums:
                        return "0"
                    tot = sum(float(n) for n in nums)
                    return str(int(tot)) if tot == int(tot) else str(tot)

                for pg in pdf.pages:
                    for data in pg.extract_tables():
                        if not data or len(data[0]) < 3:
                            continue
                        header = data[0]
                        if sum(1 for c in header[1:] if c and str(c).strip()) < 2:
                            continue
                        # pack row ("A R E A", 10X10'S ...) optional
                        start = 1
                        pack = [""] * len(header)
                        if (
                            len(data) > 1
                            and re.sub(r"[^A-Z]", "", str(data[1][0] or "").upper())
                            == "AREA"
                        ):
                            pack = [c or "" for c in data[1]]
                            start = 2

                        # product columns: sirf jinka header hai (Amount / total column ka header None hota hai)
                        cols = []
                        for ci in range(1, len(header)):
                            if header[ci] and str(header[ci]).strip():
                                code = khi_code(
                                    header[ci], pack[ci] if ci < len(pack) else ""
                                )
                                if code is None:
                                    print(
                                        f"[Karachi] product header not recognised, skipped: {str(header[ci])!r} / {pack[ci] if ci < len(pack) else ''!r}"
                                    )
                                cols.append((ci, code))

                        for row in data[start:]:
                            if not row or not row[0] or not str(row[0]).strip():
                                continue  # total row (pehla cell khali)
                            brick = khi_brick(row[0])
                            for ci, code in cols:
                                if code is None or ci >= len(row):
                                    continue
                                q = khi_qty(row[ci])
                                if q != "0":
                                    result.append([code, brick, q])

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
                new_result = green_team_bricks(new_result)
                for r in new_result:
                    for t in tt_list:
                        if r[2] == t[0]:
                            r.insert(4, t[1])
                return new_result

            elif dist_city == "Sahiwal":
                SWL_BRICKS = {
                    "SWLCN": "SAHIWAL CENTER",
                    "DHQ": "DISTRICT HEAD QUARTER HOSPITAL",
                    "PAKPN": "PAK PATTAN",
                    "ARIFW": "ARIFWALA",
                    "IQNGR": "IQBAL NAGAR",
                    "KASWL": "KASSOWAL",
                    "QBLA": "QABOOLA",
                    "CCI": "CHICHAWATNI",
                    "GHABD": "GHAZIA ABAD",
                    "HARPA": "HARAPPA",
                }
                SWL_PRODUCTS = {
                    "AFLOXAN 300MG TAB 30S": "Afloxan Tablet",
                    "AFLOXAN CAP 20'S": "Afloxan Capsule",
                    "JETEPAR 10ML INJ 5S": "Jetepar Injection 10ml",
                    "JETEPAR 2ML INJ 10S": "Jetepar Injection 2ml",
                    "JETEPAR CAP 20S": "Jetepar Capsule",
                    "JETEPAR SYRUP 112ML": "Jetepar Syrup",
                    "MAIORAD 3ML INJ 6S": "Maiorad Injection",
                    "MAIORAD TAB 30S": "Maiorad Tablet",
                }

                def swl_group(words):
                    words = sorted(words, key=lambda w: w["top"])
                    lines, cur, cur_top = [], [], None
                    for w in words:
                        if cur_top is None or abs(w["top"] - cur_top) <= 3:
                            cur.append(w)
                            cur_top = w["top"] if cur_top is None else cur_top
                        else:
                            lines.append(cur)
                            cur, cur_top = [w], w["top"]
                    if cur:
                        lines.append(cur)
                    for ln in lines:
                        ln.sort(key=lambda w: w["x0"])
                    return lines

                def swl_rows(pg):
                    """har product row -> (NAAM, {brick: qty}); table lines/'#' se beparwah"""
                    words = pg.extract_words(x_tolerance=2)
                    lines = swl_group(words)
                    hdr = None
                    for ln in lines:
                        if any(w["text"].upper() in SWL_BRICKS for w in ln):
                            hdr = ln
                            break
                    if not hdr:
                        return []
                    hw = [w for w in hdr if w["text"].upper() in SWL_BRICKS]
                    centers = [
                        ((w["x0"] + w["x1"]) / 2, SWL_BRICKS[w["text"].upper()])
                        for w in hw
                    ]
                    # vertical lines (double line ko merge karke) = cell ki hudood
                    vx = sorted(
                        r["x0"] for r in pg.rects if r["width"] < 3 and r["height"] > 10
                    )
                    edges = []
                    for x in vx:
                        if not edges or x - edges[-1] > 4:
                            edges.append(x)
                    cells = []
                    for k, (c, b) in enumerate(centers):
                        half = (c - centers[k - 1][0]) / 2 if k else 20
                        left = max([e for e in edges if e <= c] or [c - half])
                        right = min([e for e in edges if e > c] or [c + 20])
                        cells.append((left, right, b))
                    name_right = cells[0][0]
                    out = []
                    for ln in lines:
                        if ln[0]["top"] <= hdr[0]["top"] + 3:
                            continue
                        name = (
                            re.sub(
                                r"\s+",
                                " ",
                                " ".join(
                                    w["text"] for w in ln if w["x0"] < name_right - 3
                                ),
                            )
                            .strip()
                            .upper()
                        )
                        if not name:
                            continue
                        vals = {}
                        for w in ln:
                            if w["x0"] < name_right - 3:
                                continue
                            # '#', khali, text -> ignore ; sirf asli number
                            if not re.fullmatch(r"-?[\d,]+(\.\d+)?", w["text"]):
                                continue
                            cx = (w["x0"] + w["x1"]) / 2
                            for l, r, b in cells:
                                if l <= cx < r:
                                    vals[b] = vals.get(b, 0) + float(
                                        w["text"].replace(",", "")
                                    )
                                    break
                        out.append((name, vals))
                    return out

                rows = []  # [product_name, brick, qty]
                for pg in pdf.pages:
                    for pname, vals in swl_rows(pg):
                        if pname not in SWL_PRODUCTS:
                            if not pname.startswith(("BLUE GROUP", "TTL", "G TTL")):
                                print(
                                    f"[Sahiwal] product not recognised, skipped: '{pname}'"
                                )
                            continue
                        for bname, f in vals.items():
                            if f == 0:
                                continue
                            q = str(int(f)) if f == int(f) else str(f)
                            rows.append([SWL_PRODUCTS[pname], bname, q])

                result = []
                for r in rows:
                    matched = None
                    for i in item_list:
                        if fuzz.token_set_ratio(r[0], i[1]) >= 100:
                            matched = i
                            break
                    if matched is None:
                        print(f"[Sahiwal] item_list mein match nahi mila: '{r[0]}'")
                        continue
                    # [code, name, brick, qty, extra]
                    result.append([matched[0], matched[1], r[1], r[2], matched[2]])

                result = green_team_bricks(result)
                for r in result:
                    for t in tt_list:
                        if r[2] == t[0]:
                            r.insert(4, t[1])
                            break
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
                        bricks[b] = "KACHEHRI ROAD SKT"
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

                    # CEO-KAY SKT-J
                    if "1011107" in bricks[b]:
                        bricks[b] = ""
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

                    if "3010201" in bricks[b]:
                        bricks[b] = "CHUNGI # 6"
                    if "2010705" in bricks[b]:
                        bricks[b] = "DEFENCE ROAD WEST SIDE"

                    # BOTH SKT-K GONDL
                    if "2020203" in bricks[b]:
                        bricks[b] = ""
                    if "2020611" in bricks[b]:
                        bricks[b] = "THQ ROAD PASRUR"
                    if "3020102" in bricks[b]:
                        bricks[b] = "DAK WALA"

                    # BOTH SKT-K GONDL
                    if "2020203" in bricks[b]:
                        bricks[b] = ""
                    if "4020103" in bricks[b]:
                        bricks[b] = "DHAMTHAL SIALKOT"
                    if "2010705" in bricks[b]:
                        bricks[b] = "DEFENCE ROAD WEST SIDE"
                    if "2010102" in bricks[b]:
                        bricks[b] = "RAJA ROAD"
                    if "2010503" in bricks[b]:
                        bricks[b] = "MUJAHID ROAD"
                    if "3020110" in bricks[b]:
                        bricks[b] = "ADDA KASSOWALA"
                    if "4020209" in bricks[b]:
                        bricks[b] = "NOOR KOT"
                    if "3020112" in bricks[b]:
                        bricks[b] = "BAN BAJWA"
                    if "20108" in bricks[b]:
                        bricks[b] = "GOHAD PUR / KHADIM ALI ROAD"
                    if "20101" in bricks[b]:
                        bricks[b] = "COMMISSIONER ROAD CITY"
                    if "20102" in bricks[b]:
                        bricks[b] = "CANTT CITY"
                    if "20103" in bricks[b]:
                        bricks[b] = "RANGPURA"
                    if "20104" in bricks[b]:
                        bricks[b] = "PULL AIK"
                    if "20105" in bricks[b]:
                        bricks[b] = "PARIS ROAD"
                    if "20106" in bricks[b]:
                        bricks[b] = "HAJI PURA"
                    if "20107" in bricks[b]:
                        bricks[b] = "KASHMIR ROAD SIALKOT"
                    if "20201" in bricks[b]:
                        bricks[b] = "KOTLI LOHARAN / KULLUWAL"
                    if "20202" in bricks[b]:
                        bricks[b] = "GONDAL"
                    if "20203" in bricks[b]:
                        bricks[b] = "SAID PUR"
                    if "20204" in bricks[b]:
                        bricks[b] = "DALUWALI"
                    if "20205" in bricks[b]:
                        bricks[b] = "KINGRA"
                    if "20206" in bricks[b]:
                        bricks[b] = "PASRUR / CHAWINDA / BADIANA"
                    if "30101" in bricks[b]:
                        bricks[b] = "DASKA CITY AREA 1"
                    if "30102" in bricks[b]:
                        bricks[b] = "DASKA CITY AREA 2"
                    if "30201" in bricks[b]:
                        bricks[b] = "MUNDEKE / KOTLI BAWA"
                    if "30202" in bricks[b]:
                        bricks[b] = "JAMKE / BHOPAL WALA"
                    if "30203" in bricks[b]:
                        bricks[b] = "SAMBRIAL SIALKOT"

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
                new_result = green_team_bricks(new_result)
                for r in new_result:
                    for t in tt_list:
                        if r[2] == t[0]:
                            r.insert(4, t[1])
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
                        bricks[b] = "KACHEHRI ROAD NAROWAL"
                    if "1010103" in bricks[b]:
                        bricks[b] = "RAILWAY ROAD NAROWAL"
                    if "1010104" in bricks[b]:
                        bricks[b] = "ZAFARWAL ROAD NAROWAL"
                    if "1010105" in bricks[b]:
                        bricks[b] = "MURIDKE ROAD NAROWAL"
                    if "1010201" in bricks[b]:
                        bricks[b] = "NURKOT"
                    if "1010202" in bricks[b]:
                        bricks[b] = "JASSAR"
                    if "1010203" in bricks[b]:
                        bricks[b] = "BUSTAN"
                    if "1010205" in bricks[b]:
                        bricks[b] = "KANJRUR 1"
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
                        bricks[b] = "KANJRUR 2"
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
                        bricks[b] = "MANZOOR PURA"
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
                new_result = green_team_bricks(new_result)
                for r in new_result:
                    for t in tt_list:
                        if r[2] == t[0]:
                            r.insert(4, t[1])
                return new_result

            elif dist_city == "Gujranwala":
                result = []
                new_result = []
                bricks = []
                sales = []

                for page in pdf.pages:
                    text = page.extract_text()
                    lines = text.split("\n")

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

                        idx = None
                        for j in range(1, len(tokens)):
                            if re.fullmatch(r"-?\d+", tokens[j]):
                                idx = j
                                break
                        if idx is None:
                            continue  # yeh brick line nahi hai

                        name = " ".join(tokens[0:idx])
                        values = tokens[idx:-1]

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
                new_result = green_team_bricks(new_result)
                for r in new_result:
                    for t in tt_list:
                        if r[2] == t[0]:
                            r.insert(4, t[1])
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
                new_result = green_team_bricks(new_result)
                for r in new_result:
                    for t in tt_list:
                        if r[2] == t[0]:
                            r.insert(4, t[1])
                return new_result

            elif dist_city == "Mardan":
                result = []

                NAME_TO_CODE = [
                    ("CYANORIN FORTE", "005425"),
                    ("MOXILIUM 125MG", "006783"),
                    ("MOXILIUM 250MG", "012649"),  # Moxilium Suspension 250mg
                    ("VIKONON FORT", "006406"),
                    ("METRONIDAZOLE", "081274"),  # Metronidazole Tablet 400mg
                    ("JETEPAR 10CC INJ", "008999"),
                    ("JETEPAR 112ML", "002188"),
                    ("JETEPAR CAP", "002392"),
                    ("JETEPAR 2ML", "004348"),
                    ("MAIORAD INJ", "009072"),
                    ("MAIORAD TAB", "012961"),
                    ("AFLOXAN CAP", "008376"),
                    ("AFLOXAN TAB", "017230"),
                ]

                def code_for(name):
                    # column names get their mid-word line-wraps rejoined
                    # with spaces (e.g. "CYANOR"+"IN"+"FORTE"), so compare
                    # with all whitespace stripped on both sides
                    n = re.sub(r"\s+", "", name.upper())
                    for label, code in NAME_TO_CODE:
                        if re.sub(r"\s+", "", label) in n:
                            return code
                    return None

                BRICK_RENAME = {
                    "SHAWAADDA+N": "SHEWA ADDA",
                    "SHAHMANSOO": "SHAHMANSOOR",
                    "M.CPLAZA": "MC PLAZA",
                    "MIRAFZALKHA": "MIR AFZAL KHAN",
                    "HOSPITALROA": "HOSPITAL ROAD MDN",
                    "PARHOTI": "PAR HOTI",
                    "RASHAKI": "RASHAKAI",
                    "M.M.C": "MARDAN MEDICAL COMPLEX",
                    "COLLAGECHO": "COLLEGE CHOWK",
                    "GHARIKAPOOR": "GHARI KAPURA",
                    "NEWADDARET": "NEW ADDA RETAIL",
                    "NEWADDAWHO": "NEW ADDA WHOLESALE",
                    "B-R-WS": "BANK ROAD WHOLESALE",
                    "SHEDANOBAR": "SHEDAN BAZAR",
                    "T.BAI": "TAKHT BHAI",
                    "LUNDKHUR": "LUND KHWAR",
                    "DAKI+SHAKNO": "DAKI AND SHAKNO",
                    "HARI CHAND": "H.CHAND",
                    "YAAR HUSSAIN": "YAR HUSSAIN",
                    "SHER GHAR": "SHERGARH",
                    "BAKHSHALI": "BAKSHALI",
                }

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

                for page in pdf.pages:
                    rows = cluster_rows(page.extract_words())

                    header_row_idx = None
                    for i, row in enumerate(rows):
                        if any(re.match(r"^\d{6}$", w["text"]) for w in row):
                            header_row_idx = i
                            break
                    if header_row_idx is None:
                        continue

                    # rebuild each product column: its 6-digit code anchors
                    # an x-position, and every following header word close
                    # to that x (until the first data row) is part of its
                    # (possibly mid-word-wrapped) name
                    col_x = []
                    col_name_parts = {}
                    i = header_row_idx
                    while i < len(rows):
                        row = rows[i]
                        texts = [w["text"] for w in row]
                        if (
                            len(texts) >= 2
                            and re.match(r"^\d{7}$", texts[0])
                            and texts[1] == "-"
                        ):
                            break  # first data row reached
                        for w in row:
                            if re.match(r"^\d{6}$", w["text"]):
                                col_x.append(w["x0"])
                                col_name_parts[w["x0"]] = []
                            elif w["text"] not in ("Total", "Amount"):
                                nearest = (
                                    min(col_x, key=lambda x: abs(x - w["x0"]))
                                    if col_x
                                    else None
                                )
                                if nearest is not None and abs(nearest - w["x0"]) < 15:
                                    col_name_parts[nearest].append(w["text"])
                        i += 1
                    col_x.sort()
                    col_codes = [code_for(" ".join(col_name_parts[x])) for x in col_x]

                    # parse region rows: "<7-digit code> - <name> <values...>"
                    while i < len(rows):
                        row = rows[i]
                        texts = [w["text"] for w in row]
                        if not texts or not re.match(r"^\d{7}$", texts[0]):
                            i += 1
                            continue
                        if len(texts) < 2 or texts[1] != "-":
                            i += 1
                            continue
                        name_words, value_words = [], []
                        for w in row[2:]:
                            if w["x0"] < col_x[0] - 10:
                                name_words.append(w["text"])
                            else:
                                value_words.append(w["text"])
                        region_name = " ".join(name_words)
                        region_name = BRICK_RENAME.get(region_name, region_name)
                        if len(value_words) >= len(col_x):
                            for c_i, code in enumerate(col_codes):
                                if code is None:
                                    continue
                                val = value_words[c_i]
                                qty = "0" if val == "-" else val.replace(",", "")
                                result.append([code, region_name, qty])
                        i += 1

                new_result = []
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
                new_result = green_team_bricks(new_result)

                for r in new_result:
                    for t in tt_list:
                        if r[2] == t[0]:
                            r.insert(4, t[1])
                return new_result

            elif dist_city == "FAISALABAD":
                result = []
                new_result = []
                bricks = []
                sales = []

                # PDF ka structure (rendered page se verify kiya hua):
                #   line     : <brick name> <N value columns> <Value total>
                #   agli line: chhota "area code" (jaise 118) -- yeh product column NAHI hai
                # N (value columns ki tadaad) pehle 15 hoti thi, lekin ab file se khud
                # nikaali jati hai taake alag-alag files (purani/nayi) mein blank columns
                # kam ya ziada hon to bhi kaam kare.
                DEFAULT_NUM_VALUE_COLS = 15

                def _to_int(s):
                    # "1,234" jaisi values ke liye bhi safe
                    return int(str(s).replace(",", ""))

                def _is_num(tok):
                    return re.fullmatch(r"-?[\d,]+", tok) is not None

                # ---- Pass 1: har page ka data range dhoondein ----
                pages_data = []
                for page in pdf.pages:
                    text = page.extract_text() or ""
                    lines = text.split("\n")

                    start_idx = None
                    end_idx = len(lines)
                    for i, line in enumerate(lines):
                        if "City/Sub City Name" in line:
                            start_idx = i + 1
                        if (
                            "Unit Totals" in line
                            or "<<SoftWave>>" in line
                            or "Total Customers" in line
                        ):
                            end_idx = min(end_idx, i)

                    if start_idx is None:
                        continue
                    pages_data.append((lines, start_idx, end_idx))

                # ---- value columns ki tadaad (N) file se nikalein ----
                # Har data line ke end mein numbers ka silsila hota hai:
                # N values + 1 total. Zyada-tar lines ka common count hi N hai
                # (jin bricks ke naam ke aakhir mein number ho, jaise "ADA 79",
                # unka count 1 zyada aayega -- mode us ko ignore kar deta hai).
                run_counts = {}
                for lines, s, e in pages_data:
                    for ln in lines[s:e]:
                        toks = ln.split()
                        run = 0
                        for tok in reversed(toks):
                            if _is_num(tok):
                                run += 1
                            else:
                                break
                        if run >= 8 and run < len(toks):  # 7 products + total, aur naam
                            run_counts[run - 1] = run_counts.get(run - 1, 0) + 1
                if run_counts:
                    NUM_VALUE_COLS = max(run_counts, key=run_counts.get)
                else:
                    NUM_VALUE_COLS = DEFAULT_NUM_VALUE_COLS

                # ---- Pass 2: bricks aur unki values parse karein ----
                for lines, start_idx, end_idx in pages_data:
                    i = start_idx
                    while i < end_idx:
                        line = lines[i].strip()
                        i += 1
                        if not line:
                            continue

                        tokens = line.split()
                        # need: name (>=1 token) + N values + 1 total
                        if len(tokens) < NUM_VALUE_COLS + 2:
                            continue  # not a brick data line
                        if not _is_num(tokens[-1]):
                            continue  # total nahi hai => data line nahi

                        # Split from the END, not from the front: some brick names end
                        # in a number of their own (e.g. "ADA 79", "SATINA 2").
                        name = " ".join(tokens[: -(NUM_VALUE_COLS + 1)])
                        values = tokens[-(NUM_VALUE_COLS + 1) : -1]

                        # ---- agli line ek chhota "area code" hai (product value NAHI) ----
                        if i < end_idx and re.fullmatch(r"-?\d+", lines[i].strip()):
                            i += 1

                        bricks.append(name)
                        sales.append(values)

                # If any brick names above don't exactly match your
                # Territory Tree spelling, put the correction here:
                #   "name as it comes out of the PDF": "correct Territory Tree name"
                BRICK_RENAME = {
                    "AFT.HOSP": "AZIZ FATIMAH HOSPITAL",
                    "ALLIED HOSP.": "ALLIED HOSPITAL",
                    "BHAI WALA": "BHAIWALA",
                    "D.TYPE": "D TYPE COLONY",
                    "G.M. ABAD": "GHULAM MUHAMMAD ABAD",
                    "GULSTAN COLONY": "GULISTAN COLONY",
                    "MADAN PUR": "MADANPUR",
                    "MADINA TOWN.FSD": "MADINA TOWN",
                    "MARZI PURA": "MIRZA PURA",
                    "NISHATABAD": "NISHAT ABAD",
                    "RAZA ABAD AREA": "RAZA ABAD",
                    "SAMAN ABAD": "SAMANABAD",
                    "SARGODHA RD": "SARGODHA ROAD",
                    "SATINA ROAD": "SATIANA ROAD",
                    "240 MORE JARAWALA": "240 MOR JARANWALA",
                    "ADA 79": "ADA 79",
                    "AMINPUR BANGLA": "AMIN PUR BANGLA",
                    "BARA GHAR": "BARA GARH",
                    "DARUL EHSAN": "DAR UL AHSAN TOWN",
                    "GAR FATEH SHAH": "GARH FATEH SHAH",
                    # "GRUSAR":"",
                    "JARANWALA": "JARAN WALA",
                    "KHURRIANWALA": "KHURRIAN WALA TOWN",
                    "KILYAN WALA": "KALYAN WALA",
                    "MAKUWANA": "MAKKUANA",
                    "MUREED WALA": "MURID WALA",
                    "MAMUN KANJAN": "MAMU KANJAN",
                    "PANSIRA": "PAINSRA",
                    "RODALA": "RODALA MANDI",
                    "SAMUNDAR MANDI": "SAMUNDARI MANDI",
                    "SANGLA HILL.": "SANGLA",
                    "SHAHKOT.": "SHAH KOT",
                    "TANDLIANWALA": "TANDLA",
                    "WHOLSALE AREA": "WHOLESALE AREA",
                    "DASUA": "DASUHA",
                }
                bricks = [BRICK_RENAME.get(b, b) for b in bricks]

                # ---- column order (from the report header): ----
                # col0 = JETEPAR10MLAMP(NEW) -> 008999
                # col1 = JETEPAR10MLAMP(OLD) -> 008999 (same product as col0, summed)
                # col2 = JETEPAR2MLAMP       -> 004348
                # col3 = JETEPARCAP(NEW)     -> 002392
                # col4 = JETEPARSYP(NEW)     -> 002188
                # col5 = JETEPARSYP(NEW1)    -> 002188 (same product as col4, summed)
                # col6 = JETEPARSYP(OLD)     -> 002188 (same product as col4, summed)
                # col7+ = header-less columns, hamesha ignore.
                # NOTE: "(NEW)"/"(OLD)"/"(NEW1)" are treated as the same
                # underlying product (different batch/packaging). If they
                # should be tracked as separate line items instead, give
                # them their own codes here rather than summing.
                for b in range(0, len(bricks)):
                    vals = sales[b]
                    if len(vals) < 7:
                        continue

                    # Har product ke liye: positive sales ka total ek row, aur negative
                    # (return) ka total alag row. Pehle dono net ho jate the
                    # (jaise BHAI WALA syrup: 5 aur -1 => 4); ab 5 aur -1 alag rows
                    # banengi.
                    product_cols = [
                        ("008999", [0, 1]),
                        ("004348", [2]),
                        ("002392", [3]),
                        ("002188", [4, 5, 6]),
                    ]

                    for code, idxs in product_cols:
                        nums = [_to_int(vals[k]) for k in idxs]
                        positive = sum(n for n in nums if n > 0)
                        negative = sum(n for n in nums if n < 0)
                        for val in (positive, negative):
                            if val == 0:
                                continue
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
                            break

                for r in new_result:
                    matched_territory = None
                    matched_price = None
                    new_result = green_team_bricks(new_result)
                    for t in tt_list:
                        if r[2] == t[0]:
                            matched_territory = t[1]
                            break
                    if matched_territory is not None:
                        for i in item_list:
                            if r[0] == i[0]:
                                matched_price = i[2]
                                break

                    r.insert(4, matched_territory)
                    r.append(matched_price)

                return new_result

            elif dist_city == "Timergara":
                code_map = {
                    "AFLOXAN CAP": "008376",
                    "AFLOXAN TAB 300MG": "017230",
                    "JETEPAR 10ML AMP": "008999",
                    "JETEPAR 2ML AMP:": "004348",
                    "JETEPAR CAPS": "002392",
                    "JETEPAR SYP": "002188",
                    "MAIORAD 3ML AMP": "009072",
                    "MAIORAD TAB": "012961",
                    "DEPROGESIC-P TABS": "081838",
                    "METRONIDAZOLE 400MG": "081274",
                    "VIKONAN 120ML SYP": "006406",
                    "CYANORIN INJ": "005425",
                    "MOXILIUM 250MG SYP": "012649",
                    "CODAMIN-P": "028729",
                    "EBAST 10MG TAB": "023906",
                    "HISTAFEX 120MG": "031037",
                    "HISTAFEX 180MG": "031038",
                    "MALTEM PLUS DS TAB": "071560",
                    "METRONIDAZOLE 200MG": "008909",
                    "MOXILIUM 250MG CAP": "006784",
                    "MOXILIUM 125MG SYP": "006783",
                    "MOXILIUM 500MG CAP": "008908",
                    "MOXILIUM DROPS": "006782",
                    "PC-LAC SYP": "019133",
                    "PROBITOR CAP 20MG": "016654",
                    "SAVELOX 250MG": "032255",
                    "SAVELOX 500MG": "029328",
                    "SUPRACEF 400MG CAP": "024820",
                    "SUPRACEF DS SUSP": "028727",
                    "SUPRACEF SUSP": "024819",
                    "SUPRALOX SUSP": "028728",
                    # "SUPRALOX TAB": "028728"
                    "TRAMAGESIC AMP": "026920",
                    "TRAMAGESIC CAPS": "029327",
                    "VIGORAL FORT TAB": "007018",
                }
                nan = float("nan")

                def clean(x):
                    return re.sub(r"\s+", " ", x or "").strip()

                def parse_table(table):
                    rows = []
                    hdr_idx = None
                    for ri, row in enumerate(table):
                        if "PRODUCT NAME" in [clean(c).upper() for c in row]:
                            hdr_idx = ri
                            break

                    if hdr_idx is not None:
                        header = [clean(c).upper() for c in table[hdr_idx]]
                        p_col = header.index("PRODUCT NAME")
                        start = (
                            next(
                                (
                                    i
                                    for i, c in enumerate(header)
                                    if c.startswith("T.PRICE")
                                ),
                                p_col + 1,
                            )
                            + 1
                        )
                        end = next(
                            (
                                i
                                for i, c in enumerate(header)
                                if c.replace(" ", "").startswith("T.QTY")
                            ),
                            len(header) - 2,
                        )
                    else:
                        hdr_idx, p_col, start = 0, 1, 3
                        header = [clean(c).upper() for c in table[0]]
                        end = len(header) - 2

                    brick_cols = []
                    for ci in range(start, end):
                        name = header[ci] if ci < len(header) else ""
                        if name:
                            if name == "TIMERGARA":
                                name = "TIMERGARA TMG"
                            if name == "CHAKDARA":
                                name = "CHAKDARA TMG"

                            brick_cols.append((ci, name))

                    for row in table[hdr_idx + 1 :]:
                        if p_col >= len(row):
                            continue
                        product = clean(row[p_col])
                        if (
                            not product
                            or product.upper() in ("PRODUCT NAME", "CODE")
                            or product.upper().startswith("GROUP TOTAL")
                        ):
                            continue
                        for ci, bname in brick_cols:
                            val = clean(row[ci]) if ci < len(row) else ""
                            val = val.replace(",", "") or "0"
                            rows.append((product, bname, val))
                    return rows

                result = []
                missing = set()

                for page in pdf.pages:
                    for table in page.extract_tables():
                        if not table:
                            continue
                        for product, brick, qty in parse_table(table):
                            code = code_map.get(product)
                            if code is None:
                                missing.add(product)
                                # code missing -> poori row mein NaN
                                result.append([nan, nan, brick, qty, nan])
                            else:
                                result.append([code, brick, qty])

                if missing:
                    print("Mapping missing for:", sorted(missing))

                for r in result:
                    for i in item_list:
                        if r[0] == i[0]:
                            r.insert(1, i[1])
                            r.append(i[2])
                result = green_team_bricks(result)
                for r in result:
                    for t in tt_list:
                        if r[2] == t[0]:
                            r.insert(4, t[1])
                return result

            elif dist_city == "Bannu":
                products = []
                sales = []
                bricks = []
                result = []
                for x in range(0, len(pdf.pages)):
                    data = pdf.pages[x].extract_table()

                    header_len = len(data[0])
                    for row_idx in range(1, len(data) - 1):
                        row = data[row_idx]
                        diff = header_len - len(row)
                        if diff > 0:
                            tokens = row[0].split(" ")
                            if len(tokens) > diff:
                                merged_vals = tokens[-diff:]
                                if all(
                                    re.match(r"^-?\d+(\.\d+)?$|^-$", t)
                                    for t in merged_vals
                                ):
                                    new_name = " ".join(tokens[:-diff])
                                    data[row_idx] = [new_name] + merged_vals + row[1:]

                    products.append(data[0][1:-1])
                    for i in range(1, len(data) - 1):
                        sales.append(data[i][1:-1])
                        bricks.append(data[i][0])
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
                        if bricks[k] == "- SURANI":
                            bricks[k] = "SURANI"
                        if bricks[k] == "- SURANI":
                            bricks[k] = "SURANI"
                        if bricks[k] == "- TAJI KALA":
                            bricks[k] = "TAJI KALA"
                        if bricks[k] == "- TAJI KALA":
                            bricks[k] = "TAJI KALA"
                        if bricks[k] == "- SABIR ABAD":
                            bricks[k] = "SABIR ABAD"
                        if bricks[k] == "- SABIR ABAD":
                            bricks[k] = "SABIR ABAD"
                        if bricks[k] == "- GHAZNI KHEL":
                            bricks[k] = "GHAZNI KHEL"
                        if bricks[k] == "RAILWAY ROAD":
                            bricks[k] = "RAILWAY ROAD BNU"
                        if bricks[k] == "- BAKA KHEL":
                            bricks[k] = "BAKA KHEL"

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
                        if "014016" in products[p][i]:
                            products[p][i] = "031038"

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

                result = green_team_bricks(result)
                for r in result:
                    for t in tt_list:
                        if r[2] == t[0]:
                            r.insert(4, t[1])

                return result
                # print(bricks)

            elif dist_city == "Dera Ismail Khan":
                result = []
                new_result = []

                DIK_DEFAULT = {
                    1: "D.I.KHAN",
                    2: "TANK",
                    3: "WANA",
                    4: "PAHAR",
                    5: "DRABAN/CHOD",
                    6: "PROVA/RAMAK",
                    7: "JANDOLA",
                    8: "ZAFAR",
                    9: "PEZU/PANYALA",
                    10: "NEW DERA",
                    11: "MAKEEN",
                }
                DIK_RENAME = {
                    "PAHAR": "PAHAR PUR",
                    "DRABAN/CHOD": "DRABAN",
                    "PEZU/PANYALA": "PANI ALA",
                    "D.I.KHAN": "DIKHAN",
                    "PROVA/RAMAK": "PROVA / RAMAK",
                }
                DIK_PRODUCTS = [
                    (("JETEPAR", "SYP"), "002188"),
                    (("JETEPAR", "SYR"), "002188"),
                    (("JETEPAR", "CAP"), "002392"),
                    (("JETEPAR", "10ML"), "008999"),
                    (("JETEPAR", "2ML"), "004348"),
                    (("MAIORAD", "TAB"), "012961"),
                    (("MAIORAD", "INJ"), "009072"),
                    (("MAIORAD", "AMP"), "009072"),
                    (("AFLOXAN", "CAP"), "008376"),
                    (("AFLOXAN", "TAB"), "017230"),
                ]

                def dik_product(name):
                    """returns (code, variant) ; variant = '(New)' / '(Old)' / ''"""
                    n = (
                        re.sub(r"\s+", " ", str(name or "").replace("\n", " "))
                        .strip()
                        .upper()
                    )
                    n = re.sub(r"^\d+\s*", "", n)  # product code (2417) hata do
                    if not n or n.startswith(("TOTAL", "P A R T")):
                        return None
                    variant = "(New)" if "NEW" in n else ("(Old)" if "OLD" in n else "")
                    for kws, code in DIK_PRODUCTS:
                        if all(k in n for k in kws):
                            return code, variant
                    print(f"[D.I.Khan] product not recognised, skipped: '{n}'")
                    return None

                def dik_group(words):
                    words = sorted(words, key=lambda w: w["top"])
                    lines, cur, cur_top = [], [], None
                    for w in words:
                        if cur_top is None or abs(w["top"] - cur_top) <= 3:
                            cur.append(w)
                            cur_top = w["top"] if cur_top is None else cur_top
                        else:
                            lines.append(cur)
                            cur, cur_top = [w], w["top"]
                    if cur:
                        lines.append(cur)
                    for ln in lines:
                        ln.sort(key=lambda w: w["x0"])
                    return lines

                def dik_legend(pg):
                    """Page ke neeche '01=D.I.KHAN', '10=NEW DERA' wali legend"""
                    amt = re.compile(r"^-?[\d,]+\.\d{2}$")  # negative amount bhi
                    legend = {}
                    for ln in dik_group(pg.extract_words(x_tolerance=1.5)):
                        for j, w in enumerate(ln):
                            m = re.match(r"^(\d{1,2})=(.*)$", w["text"])
                            if not m:
                                continue
                            parts = [m.group(2)] if m.group(2) else []
                            prev_x1 = w["x1"]
                            for w2 in ln[j + 1 :]:
                                if (
                                    re.match(r"^\d{1,2}=", w2["text"])
                                    or amt.match(w2["text"])
                                    or w2["text"].upper() == "TOTAL"
                                    or w2["x0"] - prev_x1 > 12
                                ):
                                    break
                                parts.append(w2["text"])
                                prev_x1 = w2["x1"]
                            if parts:
                                legend[int(m.group(1))] = " ".join(parts).strip()
                    return legend

                def dik_rows(pg):
                    """har product row -> (naam, {town_no: qty}) ; x-position se column pehchanta hai"""
                    words = pg.extract_words(x_tolerance=1.5)
                    lines = dik_group(words)
                    header = None
                    for ln in lines:
                        d = [w for w in ln if w["text"].isdigit() and w["x0"] > 100]
                        if len(d) >= 3:
                            header = (ln[0]["top"], d, ln)
                            break
                    if not header:
                        return []
                    h_top, d, h_line = header
                    # numbers right-aligned hote hain: header ke x1 + ~11 par value ka x1 aata hai
                    cols = [(int(w["text"]), w["x1"] + 11) for w in d]
                    first_x0 = min(w["x0"] for w in d)
                    tot = [w for w in h_line if w["text"].upper() == "TOTAL"]
                    total_x0 = tot[0]["x0"] if tot else max(w["x1"] for w in d) + 25
                    legend_top = min(
                        [w["top"] for w in words if re.match(r"^\d{1,2}=", w["text"])]
                        or [1e9]
                    )
                    out = []
                    for ln in lines:
                        top = ln[0]["top"]
                        if top <= h_top + 5 or top >= legend_top - 2:
                            continue
                        name = " ".join(
                            w["text"] for w in ln if w["x1"] <= first_x0 - 5
                        )
                        if not name:
                            continue
                        vals = {}
                        for w in ln:
                            if w["x0"] < first_x0 - 5 or w["x0"] >= total_x0 - 10:
                                continue  # naam wala hissa / TOTAL column
                            # negative values (jaise -5) bhi allow
                            if not re.fullmatch(r"-?[\d,]+(\.\d+)?", w["text"]):
                                continue
                            n, _ = min(cols, key=lambda c: abs(w["x1"] - c[1]))
                            vals[n] = vals.get(n, 0) + float(w["text"].replace(",", ""))
                        out.append((name, vals))
                    return out

                sums = {}
                order = []
                for pg in pdf.pages:
                    legend = dik_legend(pg)
                    for name, vals in dik_rows(pg):
                        p = dik_product(name)
                        if p is None:
                            continue
                        code, variant = p
                        for n, f in vals.items():
                            nm = legend.get(n) or DIK_DEFAULT.get(n)
                            if not nm:
                                continue
                            nm = re.sub(r"\s+", " ", nm).strip()
                            bname = DIK_RENAME.get(nm, nm)
                            key = (code, variant, bname)  # New / Old alag alag
                            if key not in sums:
                                sums[key] = 0.0
                                order.append(key)
                            sums[key] += f

                for key in order:
                    tot = sums[key]
                    if tot == 0:
                        continue  # jis brick mein sale 0 ho uski row nahi aayegi
                    result.append(
                        [
                            key[0],
                            key[1],
                            str(int(tot)) if tot == int(tot) else str(tot),
                            key[2],
                        ]
                    )
                # abhi row = [code, variant, qty, branch] -> [code, branch, qty, variant]
                result = [[r[0], r[3], r[2], r[1]] for r in result]

                for r in result:
                    for i in item_list:
                        if r[0] == i[0]:
                            new_result.append(r)
                            break
                for r in new_result:
                    for i in item_list:
                        if r[0] == i[0]:
                            variant = r.pop()
                            r.insert(1, f"{i[1]} {variant}".strip())  # e.g. "... (New)"
                            r.append(i[2])
                            break
                new_result = green_team_bricks(new_result)
                for r in new_result:
                    for t in tt_list:
                        if r[2] == t[0]:
                            r.insert(4, t[1])
                            break
                    else:
                        r.insert(4, "nan")  # brick territory tree mein nahi mili
                return new_result
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
                        if str(sales[s][i]).strip() in ("0", "0.0", ""):
                            continue
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
                        bricks[i] = re.sub("MULIHALMUGHLAN", "MULHAL MUGHLA", bricks[i])
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
                        if sales[s][i] == "0":
                            continue
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
                new_result = green_team_bricks(new_result)

                for r in new_result:
                    for t in tt_list:
                        if r[2] == t[0]:
                            r.insert(4, t[1])
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
                result = []
                new_result = []

                # Brick code -> Territory Tree name
                RWP_BRICK_CODES = {
                    "1010101": "G-8 MARKAZ",
                    "1010102": "G-9 MARKAZ",
                    "1010103": "PESHAWAR MORE",
                    "1010104": "G-10",
                    "1010105": "G-11",
                    "1010106": "F-10",
                    "1010107": "F-11",
                    "1010110": "F-8",
                    "1010111": "E SECTORS",
                    "1010112": "I-8",
                    "1010113": "I-9",
                    "1010114": "I-10",
                    "1010115": "PWD",
                    "1010116": "HUMMAK",
                    "1010117": "MANDRA",
                    "1010118": "B-17",
                    "1010119": "D-17",
                    "1010120": "F-17",
                    "1010121": "F-18",
                    "1010122": "D-12 MARKAZ",
                    "1010201": "F-6 SUPER MARKET",
                    "1010202": "F-7 JINNAH SUPER",
                    "1010203": "MELODY MARKET",
                    "1010204": "ABPARA MARKET",
                    "1010206": "BARA KAHU",
                    "1010207": "BLUE AREA",
                    "1010209": "ALI PUR FARASH",
                    "1010301": "CHAK SHAHZAD",
                    "1010401": "GHOURI TOWN",
                    "1020101": "CHANDNI CHOWK",
                    "1020102": "SAID PURE ROAD",
                    "1020103": "BOHAR BAZAR",
                    "1020105": "JAMIA MASJID ROAD",
                    "1020106": "OPP HFH",
                    "1020107": "KHAYABAN E SIR SYED",
                    "1020108": "PIRWADHAI",
                    "1020109": "DHOKE HASSOO",
                    "1020110": "DHQ MOHAN PURA",
                    "1020111": "SADIQABAD",
                    "1020113": "DHOKE KALA KHAN",
                    "1020114": "MURREE ROAD",
                    "1020116": "SATELLITE TOWN RWL",
                    "1020119": "MARIR HASSAN",
                    "1020201": "SADDAR",
                    "1020203": "PESHAWAR ROAD",
                    "1020204": "TENCH BHATA",
                    "1020205": "DHERI",
                    "1020206": "KAMALABAD",
                    "1020208": "DHAMIAL CHAKRI",
                    "1020209": "MORGAH",
                    "1020210": "ADYALA ROAD",
                    "1020211": "CHAKLALA SCHEME III",
                    "1020212": "BAHRIA",
                    "1020213": "NASEERABAD",
                    "1020214": "MISRIAL ROAD",
                    "1020215": "LALKURTI",
                    "1020216": "MALL ROAD RWL",
                    "1020401": "GULBERG GREEN",
                    "1030101": "TAXILLA",
                    "1030201": "WAH CANTT",
                    "1030301": "HASSAN ABDAL",
                    "1030401": "TARNOL",
                    "1030402": "G-15",
                    "1040101": "ATTOCK",
                    "1040201": "HAZRO",
                    "1040501": "KAMRA",
                    "1050101": "GUJAR KHAN",
                    "1050201": "KALLAR SAYYADAN",
                    "1050301": "KAHUTA",
                    "1050401": "MANDRA",
                    "1050402": "RAWAT",
                    "1050403": "DHA",
                    "1060101": "FATEH JANG",
                    "1060301": "PINDI GHEB",
                    "1080301": "KOTLI",
                }
                # Purane (bina code wale) reports ke naam
                RWP_BRICK_NAMES = {
                    "MALL ROAD": "MALL ROAD RWL",
                    "CHAKWAL": "CHAKWAL RWL",
                    "ALI PURE FARASH": "ALI PUR FARASH",
                    "BUNNI CHOWK": "BANNI CHOWK",
                    "KHAYABAN-E-SIR SYED": "KHAYABAN E SIR SYED",
                    "CHAKLALA SCHEME III": "CHAKLALA SCHEME III",
                    "JAMIA MASJID ROAD": "JAMIA MASJID ROAD",
                }

                def rwp_brick(cell):
                    raw = re.sub(r"\s+", " ", str(cell or "")).strip()
                    m = re.match(r"^(\d{7})\b\s*-?\s*(.*)$", raw)
                    if m:
                        code, name = m.group(1), m.group(2).strip()
                        if code in RWP_BRICK_CODES:
                            return RWP_BRICK_CODES[code]
                        raw = name  # code map mein nahi -> code hata kar naam
                    return RWP_BRICK_NAMES.get(raw.upper(), raw)

                # Product column: pehle NAAM se, phir CODE se (newline/space ignore)
                RWP_PRODUCT_CODES = {
                    "009001": "002188",
                    "009002": "002392",
                    "009003": "004348",
                    "009004": "008999",
                    "009005": "008376",
                    "009007": "012961",
                    "009008": "009072",
                }

                def rwp_product(header):
                    h = re.sub(r"\s+", "", str(header or "")).upper()
                    if not h:
                        return None
                    if "JETEPAR" in h:
                        if "SYP" in h or "SYRUP" in h:
                            return "002188"
                        if "CAP" in h:
                            return "002392"
                        if "2ML" in h or "2CC" in h:
                            return "004348"
                        if "10ML" in h or "10CC" in h:
                            return "008999"
                    if "MAIORAD" in h:
                        if "TAB" in h:
                            return "012961"
                        if "INJ" in h or "AMP" in h or "3ML" in h:
                            return "009072"
                    if "AFLOXAN" in h or "AFLOXON" in h:
                        if "TAB" in h:
                            return "017230"
                        if "CAP" in h:
                            return "008376"
                    m = re.match(r"^(\d{6})", h)
                    if m and m.group(1) in RWP_PRODUCT_CODES:
                        return RWP_PRODUCT_CODES[m.group(1)]
                    return None

                def rwp_clean_sale(v):
                    if v is None:
                        return "0"
                    s = str(v).split("\n")[0].strip().replace(",", "")
                    return "0" if s in ("", "-") else s

                col_map = None  # {column index: item code}; agle page pe header na ho to purana use hota hai
                for pg in pdf.pages:
                    for table in pg.extract_tables():
                        for row in table:
                            if not row:
                                continue
                            first = re.sub(r"\s+", " ", str(row[0] or "")).strip()

                            # header row: pehla cell khali/text aur kam az kam 1 product pehchana jaye
                            if not re.match(r"^\d{7}\b", first):
                                found = {
                                    ci: rwp_product(c)
                                    for ci, c in enumerate(row)
                                    if ci > 0 and rwp_product(c)
                                }
                                if found:
                                    col_map = found
                                    continue
                            # Total / khali row skip
                            if not first or first.upper().startswith(
                                ("TOTAL", "GRAND")
                            ):
                                continue
                            if not col_map:
                                continue

                            brick = rwp_brick(first)
                            for ci, code in col_map.items():
                                if ci < len(row):
                                    result.append(
                                        [code, brick, rwp_clean_sale(row[ci])]
                                    )

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
                new_result = green_team_bricks(new_result)
                for r in new_result:
                    for t in tt_list:
                        if r[2] == t[0]:
                            r.insert(4, t[1])
                return new_result

            elif dist_city == "Vehari":
                result = []
                new_result = []
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
                    "KACHI PAKKI",
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
                    "WHOLESALE VHR",
                    "WHOLESALE BUR",
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
                    "VEH-B": "VEHARI B",
                    "WHOLESALE BUR": "WHOLESALE BURY WALA",
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
                sales_by_product = OrderedDict()

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
                    "MOXILIUM SUS 125MG": "006783",
                    "PC-LAC SYP 120ml": "019133",
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
                new_result = green_team_bricks(new_result)
                for r in new_result:
                    for t in tt_list:
                        if r[2] == t[0]:
                            r.insert(4, t[1])

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
                    bricks[i] = re.sub("SHANAGLA MARKET", "SHANGLA MARKET", bricks[i])
                    bricks[i] = re.sub("AL MANSOOR MARKET", "AL MANSOOR", bricks[i])
                    bricks[i] = re.sub("NISHTER ABAD", "NISHTERABAD", bricks[i])
                    bricks[i] = re.sub("NISHTER ABAD", "NISHTERABAD", bricks[i])
                    bricks[i] = re.sub("PAJJAGI ROAD", "PAJAGI ROAD", bricks[i])
                    bricks[i] = re.sub("CHARSADDA ROAD", "CHARSADDA ROAD", bricks[i])
                    bricks[i] = re.sub("CHARSADDA ROAD", "CHARSADA ROAD", bricks[i])
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
                new_result = green_team_bricks(new_result)
                for r in new_result:
                    for t in tt_list:
                        if r[2] == t[0]:
                            r.insert(4, t[1])
                return new_result
            elif dist_city == "Quetta":
                result = []
                new_result = []

                QTA_HEADERS = {
                    "Alam Khan Chock": "ALAM KHAN CHOWK",
                    "Alamdar Road": "ALAMDAR ROAD",
                    "Barori": "BARORI",
                    "Cant": "QUETTA CANTONMENT",
                    "Institution": "INSTITUTION",
                    "Kandhari Bazar Jinnah Road": "JINNAH ROAD KANDHARI BAZAR",
                    "Huda Spini Road": "HUDA SPINI ROAD",
                    "Sabzal Road": "SABZAL ROAD",
                    "Sirki Road Gawalmandi Chock": "SIRKI ROAD GAWALMANDI CHOWK",
                    "Liaqat Bazar Archar FJ Road": "LIAQAT BAZAR ARCHAR_FJ ROAD",
                    "Macangi Raod": "MEKANGI ROAD",
                    "Mission Road": "MISSION ROAD",
                    "Off Jinnah Road": "OFF JINNAH ROAD",
                    "Pashtonabad": "PASHTUN ABAD",
                    "Prince Road": "PRINCE ROAD",
                    "Saryab Road": "SARIAB ROAD",
                    "Satelite Town": "SATELLITE TOWN QTA",
                    "Zargon Road": "ZARGON ROAD",
                    "Wholesale": "WHOLESALE QTA",
                    "Chaman": "CHAMAN",
                    "Dalbandin": "DALBANDIN",
                    "Dukki": "DUKKI",
                    "K_Siafullah": "QILLA SIAFULLAH",
                    "Kallat": "KALAT",
                    "Khanozai": "KHANOZAI",
                    "Kharan": "KHARAN",
                    "Khuzdar": "KHUZDAR",
                    "Kuchlack": "KUCHLACK",
                    "Loralai": "LORALAI",
                    "M_Bag": "M_BAG",
                    "Mastung": "MASTUNG",
                    "Much": "MACHH",
                    "Noshki": "NOSHKI",
                    "Pishin": "PISHIN",
                    "Sanjavi": "SANJAWI",
                    "Saranan": "SARANAN",
                    "Sibbi": "SIBI",
                    "Zhob": "ZHOB",
                }

                def qta_fp(s):
                    return "".join(sorted(re.sub(r"[^A-Z0-9]", "", str(s).upper())))

                QTA_HEADER_FP = {qta_fp(k): v for k, v in QTA_HEADERS.items()}

                def qta_subset(have, key):
                    need = Counter(key)
                    return all(have[ch] >= n for ch, n in need.items())

                def qta_classify(txt):
                    """returns ('brick', name) / ('skip', None).
                    Total columns ka text kabhi kabhi scrambled aata hai
                    (e.g. 'Q / UT / AO / A / NTITYTAL / M'), is liye sirf
                    lafz nahi, letters ke pattern se bhi pehchante hain."""
                    fp = qta_fp(txt)
                    if fp in QTA_HEADER_FP:  # exact brick header
                        return "brick", QTA_HEADER_FP[fp]
                    up = str(txt).upper()
                    if any(k in up for k in ("TOTAL", "QUANTITY", "AMOUNT")):
                        return "skip", None
                    have = Counter(fp)
                    if (
                        qta_subset(have, "QUANTITY")
                        or qta_subset(have, "AMOUNT")
                        or qta_subset(have, "TOTALAREA")
                    ):
                        return "skip", None
                    # padosi cell ka extra lafz aa jaye to sab se lamba alias
                    best, best_len = None, 0
                    for k, v in QTA_HEADER_FP.items():
                        if len(k) > best_len and qta_subset(have, k):
                            best, best_len = v, len(k)
                    if best:
                        return "brick", best
                    # naya/unknown brick: sirf tab lein jab text saaf ho (har line 3+ letters)
                    lines = [l.strip() for l in str(txt).split("\n") if l.strip()]
                    if lines and all(len(l) >= 3 for l in lines):
                        return "brick", " ".join(lines).upper()
                    return "skip", None

                # (required keywords, item code) - pehla match jeetega
                QTA_PRODUCTS = [
                    (("JETEPAR", "SYP"), "002188"),
                    (("JETEPAR", "SYRUP"), "002188"),
                    (("JETEPAR", "CAP"), "002392"),
                    (("JETEPAR", "2CC"), "004348"),
                    (("JETEPAR", "2ML"), "004348"),
                    (("JETEPAR", "10CC"), "008999"),
                    (("JETEPAR", "10ML"), "008999"),
                    (("MAIORAD", "INJ"), "009072"),
                    (("MAIORAD", "TAB"), "012961"),
                    (("AFLOXAN", "CAP"), "008376"),
                    (("AFLOXAN", "TAB"), "017230"),
                    (("DEPROGESIC", "P"), "081838"),
                    (("METRONIDAZOLE", "400"), "081274"),
                    (("METRONIDAZOLE", "200"), "008909"),
                    (("MOXILIUM", "125"), "006783"),
                    (("MOXILIUM", "250", "SYP"), "012649"),
                    (("MOXILIUM", "250", "CAP"), "006784"),
                    (("MOXILIUM", "500"), "008908"),
                    (("MOXILIUM", "DROP"), "006782"),
                    (("AVOR", "2MG"), "007853"),
                    (("AVOR", "1MG"), "006584"),
                    (("CYANORIN",), "005425"),
                    (("PC-LAC",), "019133"),
                    (("VIKONON",), "006406"),
                    (("VIGROL",), "007018"),
                    (("EBAST",), "023906"),
                    (("HISTAFEX", "120"), "031037"),
                    (("HISTAFEX", "180"), "031038"),
                    (("ISRIP", "1MG"), "035294"),
                    (("ISRIP", "2MG"), "035295"),
                    (("MINGAIR", "10"), "038427"),
                    (("MINGAIR", "5"), "038426"),
                    (("OBEXIL",), "032259"),
                    (("PROBITOR",), "016654"),
                    (("SAVELOX", "250"), "032255"),
                    (("SAVELOX", "500"), "029328"),
                    (("SUPRACEF", "CAP"), "024820"),
                    (("SUPRACEF", "DS"), "028727"),
                    (("SUPRACEF", "SUS"), "024819"),
                    (("SUPRACEF", "SYP"), "024819"),
                    (("SUPRALOX",), "028728"),
                    (("TRAMAGESIC", "INJ"), "026920"),
                    (("TRAMAGESIC", "CAP"), "029327"),
                    (("CODAMIN",), "028729"),
                    (("MALTEM", "PLUS"), "071560"),
                ]

                def qta_product(name):
                    n = re.sub(r"\s+", " ", str(name)).strip().upper()
                    if re.match(r"^(\d\s*-|GRAND|TOTAL|PRODUCTS|AREA)", n):
                        return None  # group / total / heading rows
                    for kws, code in QTA_PRODUCTS:
                        if all(k in n for k in kws):
                            return code
                    print(f"[Quetta] product not recognised, skipped: '{n}'")
                    return None

                for pg in pdf.pages:
                    tables = pg.find_tables()
                    if not tables:
                        continue
                    # header row = pehli table ki pehli row
                    hdr_cells = sorted(
                        [c for c in tables[0].rows[0].cells if c], key=lambda c: c[0]
                    )
                    if len(hdr_cells) < 3:
                        continue
                    name_edge = hdr_cells[0][2]  # product-name column ka right edge

                    cols = []  # (x0, x1, brick_name)
                    for c in hdr_cells[1:]:
                        txt = pg.crop(c).extract_text() or ""
                        kind, name = qta_classify(txt)
                        if kind == "skip":
                            if txt.strip():
                                print(
                                    f"[Quetta] header column skipped: {txt.strip()!r}"
                                )
                            continue
                        cols.append((c[0], c[2], name))

                    # words ko lines mein group karein (tolerance 3pt)
                    words = sorted(
                        pg.extract_words(x_tolerance=1.5), key=lambda w: w["top"]
                    )
                    lines, cur, cur_top = [], [], None
                    for w in words:
                        if cur_top is None or abs(w["top"] - cur_top) <= 3:
                            cur.append(w)
                            cur_top = w["top"] if cur_top is None else cur_top
                        else:
                            lines.append(cur)
                            cur, cur_top = [w], w["top"]
                    if cur:
                        lines.append(cur)

                    for ln in lines:
                        ln.sort(key=lambda w: w["x0"])
                        name_words = [w["text"] for w in ln if w["x1"] <= name_edge + 1]
                        val_words = [w for w in ln if w["x0"] > name_edge - 1]
                        if not name_words or not val_words:
                            continue
                        code = qta_product(" ".join(name_words))
                        if code is None:
                            continue
                        for w in val_words:
                            cx = (w["x0"] + w["x1"]) / 2
                            for x0, x1, bname in cols:
                                if x0 <= cx < x1:
                                    v = w["text"].replace(",", "").strip()
                                    if v not in ("", "-", "0", "0.0"):
                                        result.append([code, bname, v])
                                    break

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
                new_result = green_team_bricks(new_result)
                for r in new_result:
                    for t in tt_list:
                        if r[2] == t[0]:
                            r.insert(4, t[1])
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
                result = green_team_bricks(result)
                for r in result:
                    for t in tt_list:
                        if r[2] == t[0]:
                            r.insert(4, t[1])
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
                result = green_team_bricks(result)
                for r in result:
                    for t in tt_list:
                        if r[2] == t[0]:
                            r.insert(4, t[1])
                return result

            elif dist_city == "Toba Tek Singh":
                result = []
                NUM = re.compile(r"^-?[\d,]+$")

                BRICK_FIX = {
                    "GOJRA": "GOJRA TTS",
                    "KAMAL": "KAMAL CHOWK",
                    "PIR M": "PIR MAHAL",
                    "RAJAN": "RAJANA",
                    "S/WAL": "SAHIWAL TTS",
                    "SHORK": "SHORK",
                    "TOBA": "TOBA TEK SINGH TTS",
                }

                # (text to look for, item code) - order matters
                PRODUCT_CODES = [
                    ("JETEPAR CAP", "002392"),
                    ("JETEPAR 10", "008999"),
                    ("JETEPAR 2", "004348"),
                    ("JETEPAR SYP", "002188"),
                    ("MAIORAD 3", "009072"),
                    ("MAIORAD TAB", "012961"),
                    ("MOXILIUM CAP", "006784"),
                    ("MOXILIUM SYP 125MG", "006783"),
                    ("MOXILIUM SYP 250MG", "012649"),
                    ("P.C.LAC SYP", "019133"),
                    ("PROBITOR CAPS 20MG", "016654"),
                    ("TRAMAGESIC", "026920"),
                    ("METRONIDAZOLE 400MG", "081274"),
                    ("METRONIDAZOLE 200MG", "008909"),
                    ("SUPRALOX SUSP 40MG", "028728"),
                    ("HISTAFEX TAB 120MG", "031037"),
                    ("EBAST TAB", "023906"),
                    ("VIKNON FORTE 120ML", "006406"),
                    ("CYNORIN FORT", "005425"),
                ]

                def get_item_code(name):
                    name = re.sub(r"\s+", " ", name).strip().upper()
                    for key, code in PRODUCT_CODES:
                        if key in name:
                            return code
                    return None

                is_team_section = False

                for page in pdf.pages:
                    table = page.extract_table()
                    text = page.extract_text()
                    if not table or not table[0] or not text:
                        continue

                    # header: Packing | brick1 ... brickN | T.Qty.
                    header = table[0][1:-1]
                    bricks = []
                    for b in header:
                        b = (b or "").strip()
                        # blank header columns are treated as TOBA (same as before)
                        bricks.append(
                            BRICK_FIX.get(b, b) if b else "TOBA TEK SINGH TTS"
                        )
                    n = len(bricks)

                    for line in text.split("\n"):
                        if re.search(r"(BLUE TEAM|GREEN TEAM)", line):
                            is_team_section = True
                            continue
                        if "Total" in line:
                            is_team_section = False
                            continue
                        if not is_team_section:
                            continue

                        tokens = line.split()
                        # name/packing ... n brick values ... T.Qty ... Value
                        if len(tokens) < n + 3:
                            continue
                        if not all(NUM.match(t) for t in tokens[-(n + 2) :]):
                            continue

                        product_name = " ".join(tokens[: -(n + 2)])  # includes packing
                        qtys = tokens[-(n + 2) : -2]  # only brick quantities

                        code = get_item_code(product_name)
                        if code is None:
                            print("UNMAPPED PRODUCT:", product_name)
                            continue

                        for brick_name, qty in zip(bricks, qtys):
                            result.append([code, brick_name, qty.replace(",", "")])

                # Enrich result with item_list info
                for r in result:
                    for i in item_list:
                        if r[0] == i[0]:
                            r.insert(1, i[1])  # item name
                            r.append(i[2])  # item group

                result = green_team_bricks(result)
                for r in result:
                    for t in tt_list:
                        if r[2] == t[0]:
                            r.insert(4, t[1])
                return result
            elif dist_city == "Dera Ghazi Khan":
                # PDF item code -> your internal item code (naya product aaye to yahan add karo)
                code_map = {
                    "032003": "008999",  # JETEPAR 10ML INJ
                    "032004": "004348",  # JETEPAR 2ML INJ
                    "032005": "002392",  # JETEPAR CAP
                    "032006": "002188",  # JETEPAR SYP
                    "032007": "009072",  # MAIORAD 3ML INJ
                    "032008": "012961",  # MAIORAD TAB
                }
                # PDF town name -> your standard brick name (unmapped names jaisay hain waisay jayenge)
                town_map = {
                    "RAILWAY ROAD": "RAILWAY ROAD DGK",
                    "PIR QATTAL": "PIR QATAL",
                    "PEER AADIL": "PIR ADIL",
                    "TIBI KISSRANI": "TIBBI QAISRANI",
                    "WHOHWA": "WHOLESALE DGK",
                    "CHOTTI": "CHOTI",
                    "JHOK UTRAH": "JHOK UTRA",
                    "KOT METHAN": "KOT MITHAN",
                    "TAUNSA (1)": "TAUNSA",
                    "TAUNSA (2)": "TAUNSA",
                    "RAJAN PUR (1)": "RAJANPUR",
                    "RAJAN PUR (2)": "RAJANPUR",
                    "CHOWK CHURATA": "CHURHATTA CHOWK",
                    "JAMPUR (1)": "JAMPUR 1",
                    "JAMPUR (2)": "JAMPUR 2",
                }

                def _clean(s):
                    # "QUAID-E-AZAM\nROAD" -> "QUAID-E-AZAM ROAD"
                    return re.sub(r"\s+", " ", (s or "")).strip()

                def _to_qty(cell):
                    q = _clean(cell).replace(",", "")
                    q = q.split(" ")[0] if q else ""
                    return "0" if q in ("", "-") else q

                # ---- layout detect: header mein 032xxx codes hon to NEW, warna OLD ----
                layout = "old"
                for _pg in pdf.pages:
                    _t = _pg.extract_table()
                    if _t:
                        for _row in _t[:2]:
                            if any(re.match(r"\s*032\d{3}\b", c or "") for c in _row):
                                layout = "new"
                        break

                result = []

                if layout == "new":
                    # Towns rows mein, product codes columns mein
                    col_codes = {}  # column index -> internal item code (pages ke beech yaad rehta hai)
                    for page in pdf.pages:
                        for table in page.extract_tables() or []:
                            if not table:
                                continue

                            # header dhoondo (jis row mein 032xxx codes hon)
                            for row in table[:2]:
                                found = {}
                                for ci, cell in enumerate(row or []):
                                    m = re.match(r"\s*(\d{6})\b", cell or "")
                                    if m:
                                        found[ci] = code_map.get(
                                            m.group(1)
                                        )  # None = unmapped product
                                if found:
                                    col_codes = found
                                    break

                            for row in table:
                                if not row or not row[0]:
                                    continue
                                first = _clean(row[0])
                                if first.upper().startswith("TOTAL"):
                                    continue
                                m = re.match(
                                    r"^\d+\s*-\s*(.+)$", first
                                )  # "1010101 - FAREEDY BAZAR"
                                if not m:
                                    continue
                                town = m.group(1).strip()
                                town = town_map.get(town, town)

                                for ci, item_code in col_codes.items():
                                    if item_code is None or ci >= len(row):
                                        continue
                                    result.append([item_code, town, _to_qty(row[ci])])

                else:
                    # ================= OLD LAYOUT (tumhara original code) =================
                    products = []
                    bricks = []
                    sales = []
                    for x in range(0, len(pdf.pages)):
                        data = pdf.pages[x].extract_table()
                        brick = data[0]
                        data = data[1:7]

                        for i in range(2, len(brick)):
                            brick[i] = brick[i].replace("\n", "")
                            brick[i] = brick[i][::-1]
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
                            if "JHO KUTRAH" in brick[i]:
                                bricks.append("JHOK UTRA")
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

                # ================= COMMON LOGIC (dono layouts ke liye) =================
                new_result = []
                for r in result:
                    if r[2] != "0" and any(r[0] == i[0] for i in item_list):
                        new_result.append(r)

                for r in new_result:
                    for i in item_list:
                        if r[0] == i[0]:
                            r.insert(1, i[1])
                            r.append(i[2])
                            break

                new_result = green_team_bricks(new_result)
                for r in new_result:
                    for t in tt_list:
                        if r[2] == t[0]:
                            r.insert(4, t[1])
                return new_result

            elif dist_city == "Jhang":
                result = []
                new_result = []

                # header ka pehla lafz -> Territory name (column ke header tokens x-position se jorre jate hain)
                JHG_BRICKS = [
                    ("18", "ATHARA HAZARI"),
                    ("AHMAD", "AHMADPUR SIAL"),
                    ("BHOW", "BHOWA"),
                    ("GOJRA", "GOJRA JNG"),
                    ("KOT", "KOT SHAKIR JNG"),
                    ("SHAH", "SHAH JEEWNA"),
                    ("SHK.C", "SHORKOT CANTT"),
                    ("SHORK", "SHORKOT JNG"),
                ]

                # (required keywords, item code) - pehla match jeetega (SYP pehle taake "112ML" 2ML se na takraye)
                JHG_PRODUCTS = [
                    (("JETEPAR", "SYP"), "002188"),
                    (("JETEPAR", "SYRUP"), "002188"),
                    (("JETEPAR", "CAP"), "002392"),
                    (("JETEPAR", "10ML"), "008999"),
                    (("JETEPAR", "10CC"), "008999"),
                    (("JETEPAR", "2ML"), "004348"),
                    (("JETEPAR", "2CC"), "004348"),
                    (("MAIORAD", "TAB"), "012961"),
                    (("MAIORAD", "3ML"), "009072"),
                    (("MAIORAD", "INJ"), "009072"),
                    (("MAIORAD", "AMP"), "009072"),
                    (("AFLOXAN", "CAP"), "008376"),
                    (("AFLOXAN", "TAB"), "017230"),
                    (("AFLOXON", "CAP"), "008376"),
                    (("AFLOXON", "TAB"), "017230"),
                    (("METRONIDAZOLE", "400"), "081274"),
                    (("METRONIDAZOLE", "200"), "008909"),
                    (("MOXILIUM", "DROP"), "006782"),
                    (("MOXILIUM", "125"), "006783"),
                    (("MOXILIUM", "250", "SYP"), "012649"),
                    (("MOXILIUM", "250", "CAP"), "006784"),
                    (("MOXILIUM", "500"), "008908"),
                    (("P.C.LAC",), "019133"),
                    (("PC-LAC",), "019133"),
                    (("VIKNON",), "006406"),
                    (("VIKONON",), "006406"),
                    (("VIGROL",), "007018"),
                    (("CYANORIN",), "005425"),
                    (("EBAST",), "023906"),
                    (("HISTAFEX", "120"), "031037"),
                    (("HISTAFEX", "180"), "031038"),
                    (("AVOR", "2MG"), "007853"),
                    (("DEPROGESIC", "P"), "081838"),
                    (("OBEXIL",), "032259"),
                    (("PROBITOR",), "016654"),
                    (("SAVELOX", "250"), "032255"),
                    (("SAVELOX", "500"), "029328"),
                    (("SUPRACEF", "CAP"), "024820"),
                    (("SUPRACEF", "DS"), "028727"),
                    (("SUPRACEF", "SUS"), "024819"),
                    (("SUPRALOX",), "028728"),
                    (("TRAMAGESIC", "INJ"), "026920"),
                    (("TRAMAGESIC", "CAP"), "029327"),
                    (("MINGAIR", "10"), "038427"),
                    (("MINGAIR", "5"), "038426"),
                ]
                JHG_SKIP = (
                    "GROUP",
                    "COMPANY",
                    "GRAND",
                    "BLUE",
                    "GREEN",
                    "PRODUCT",
                    "TOTAL",
                    "PAGE",
                )

                def jhg_product(name):
                    n = re.sub(r"\s+", " ", str(name)).strip().upper()
                    if not n or n.startswith(JHG_SKIP):
                        return None
                    for kws, code in JHG_PRODUCTS:
                        if all(k in n for k in kws):
                            return code
                    print(f"[Jhang] product not recognised, skipped: '{n}'")
                    return None

                def jhg_lines(words, tol=3):
                    words = sorted(words, key=lambda w: w["top"])
                    lines, cur, cur_top = [], [], None
                    for w in words:
                        if cur_top is None or abs(w["top"] - cur_top) <= tol:
                            cur.append(w)
                            cur_top = w["top"] if cur_top is None else cur_top
                        else:
                            lines.append(cur)
                            cur, cur_top = [w], w["top"]
                    if cur:
                        lines.append(cur)
                    for ln in lines:
                        ln.sort(key=lambda w: w["x0"])
                    return lines

                num_re = re.compile(r"^-?[\d,]+(\.\d+)?$")

                for pg in pdf.pages:
                    words = pg.extract_words(x_tolerance=1.5)
                    hdr_prod = next((w for w in words if w["text"] == "Product"), None)
                    hdr_pack = next((w for w in words if w["text"] == "Packing"), None)
                    hdr_tqty = next(
                        (w for w in words if w["text"].upper().startswith("T.QTY")),
                        None,
                    )
                    if not (hdr_prod and hdr_pack and hdr_tqty):
                        continue

                    name_edge = hdr_pack["x0"] - 5  # product name is se pehle khatam
                    val_start = hdr_pack["x1"] + 1  # brick columns packing ke baad
                    cutoff = hdr_tqty["x0"] - 5  # is se aage T.Qty / Value columns

                    lines = jhg_lines(words)

                    # ---- product rows dhoondein (naam + packing + values) ----
                    prod_rows = []
                    for ln in lines:
                        nm = " ".join(w["text"] for w in ln if w["x1"] <= name_edge)
                        code = jhg_product(nm) if nm else None
                        if code is None:
                            continue
                        vals = [
                            w
                            for w in ln
                            if w["x0"] >= val_start
                            and num_re.match(w["text"])
                            and (w["x0"] + w["x1"]) / 2 < cutoff
                        ]
                        if vals:
                            prod_rows.append((code, vals))

                    # ---- value columns (right-edge clusters) ----
                    edges = sorted(w["x1"] for _, vals in prod_rows for w in vals)
                    slots = []
                    for e in edges:
                        if slots and e - slots[-1][-1] <= 4:
                            slots[-1].append(e)
                        else:
                            slots.append([e])
                    slot_x1 = [sum(s) / len(s) for s in slots]

                    # ---- header tokens ko x-position se column se jorna ----
                    hdr_top = hdr_prod["top"]
                    first_line_top = min(
                        (w["top"] for w in words if w["top"] > hdr_top + 20),
                        default=hdr_top + 40,
                    )
                    slot_tokens = [[] for _ in slot_x1]
                    for w in words:
                        if not (hdr_top - 3 <= w["top"] < first_line_top - 3):
                            continue
                        cx = (w["x0"] + w["x1"]) / 2
                        if w["x0"] < val_start or cx >= cutoff:
                            continue
                        for si, sx in enumerate(slot_x1):
                            if sx + 4 >= cx:
                                slot_tokens[si].append(w)
                                break

                    jhang_count = 0
                    slot_names = []
                    for toks in slot_tokens:
                        toks.sort(key=lambda w: (round(w["top"]), w["x0"]))
                        first = toks[0]["text"].upper() if toks else ""
                        name = None
                        for key, brick in JHG_BRICKS:
                            if first == key or (key != "18" and first.startswith(key)):
                                name = brick
                                break
                        if name == "JHANG":
                            jhang_count += 1
                            name = "JHANG %d" % jhang_count
                        if name is None and toks:
                            name = " ".join(t["text"] for t in toks).upper()
                            print(
                                f"[Jhang] brick header not recognised, using raw: '{name}'"
                            )
                        slot_names.append(name)

                    # ---- values ko un ke column mein daalna ----
                    for code, vals in prod_rows:
                        for w in vals:
                            si = min(
                                range(len(slot_x1)),
                                key=lambda k: abs(slot_x1[k] - w["x1"]),
                            )
                            bname = slot_names[si]
                            v = w["text"].replace(",", "").strip()
                            if bname and v not in ("", "-", "0", "0.0"):
                                result.append([code, bname, v])

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
                new_result = green_team_bricks(new_result)
                for r in new_result:
                    for t in tt_list:
                        if r[2] == t[0]:
                            r.insert(4, t[1])
                return new_result

            elif dist_city == "Sargodha":
                result = []
                products = []

                # Raw decoded header text (each column's text read top-to-bottom, no
                # spaces) -> real brick name. This is what makes column order/alignment
                # stop mattering: every page's header is decoded fresh and matched by
                # content, not by position. Add "RAWTEXT": "Real Name" here whenever a
                # report shows a brick this doesn't recognise yet (the printed warning
                # will show you the raw text to add).
                HEADER_ALIASES = {
                    "MLKW": "MALAKWAL SGD",
                    "AKT": "AKT",
                    "JHB": "JAUHARABAD",
                    "KHB": "KHUSHAB",
                    "MTH": "MITHA LAK",
                    "NOW": "NOWSHRA",
                    "NUR": "NOORPUR",
                    "QIAD": "QUAIDABAD",
                    "CHKI": "CHOWKI BHAGAT",
                    "BHL": "BHALWAL",
                    "BHR": "BHERA",
                    "FRQ": "FAROOKA",  # font renders "O" as "Q" in this position
                    "KOT": "KOT MOMIN",
                    "MRI": "MARI LAK",
                    "PHL": "PHULARWAN",
                    "SAHW": "SAHIWAL",
                    "SRG1": "SARGODHA 1",
                    "SHP": "SHAHPUR",
                    "SILWI": "SILLANWALI",
                    "ADA4649TAL": "ADA46 49TAL",
                    "SAG2": "SARGODHA 2",
                    "WHOLESALE": "WHOLESALE SGD",
                    "JHWN": "JAVERIA",
                    "SHCITY": "SHAHPUR CITY",
                }
                # Header columns that are report totals, not real bricks -- always dropped.
                NON_BRICK_HEADER_TOKENS = {
                    "TOTAL",
                    "TOTALQTY",
                    "TTLQTY",
                    "TTLAMT",
                    "TRADEVALUE",
                }

                # Rename any FINAL name here so it matches your territory tree exactly.
                BRICK_ALIASES = {
                    # "OLD NAME": "NEW NAME",
                    "NOWSHRA": "NOWSHERA SGD1",
                    "NUR": "NURPURTHAL",
                    "SARGODHA 1": "SARGODHA SGD1",
                    "SAHIWAL": "SAHIWAL SGD",
                    "PHL": "PHULARWAN",
                    "KOT MOMIN": "KOTMOMAN",
                    "JAVERIA": "JHAWERIAN",
                }

                PRODUCT_PREFIXES = [
                    ("AFLOXAN CAPSUL", "008376"),
                    ("AFLOXAN TABLET", "017230"),
                    ("ALOPRA 20 MG TABLET", "029986"),
                    ("AVOR 1MG TABLET", "006584"),
                    ("AVOR 2 MG TABLET", "007853"),
                    ("BIGUANAIL 250 MG TABLET", "003718"),
                    ("BIGUANAIL 500 MG TABLET", "005310"),
                    ("CODAMIN-P TABLET 50'S", "028729"),
                    ("CYANORIN FORTE INJ", "005425"),
                    ("DEPROGESIC P TAB", "081838"),
                    ("DEPROGESIC TABLET", "081838"),
                    ("EBAST TABLET 10 MG", "023906"),
                    ("HISTAFEX 120 MG TABLET", "031037"),
                    ("HISTAFEX 180 MG TABLET", "031038"),
                    ("ISRIP 1 MG TABLET", "035294"),
                    ("ISRIP 2MG TABLET", "035295"),
                    ("ISRIP 3MG TABLET", "035296"),
                    ("ISRIP 4 MG TABLET", "035297"),
                    ("JETEPAR 10 ML INF", "008999"),
                    ("JETEPAR 2CC INJ", "004348"),
                    ("JETEPAR CAPSUL", "002392"),
                    ("JETEPAR SYRUP 112ML", "002188"),
                    ("MAIROAD INJ 3 ML", "009072"),
                    ("MAIROAD TABLET", "012961"),
                    ("MALTEM 40 MG TABLET", "085180"),
                    ("MALTEM PLUS DS", "071560"),
                    ("METRONIDAZOLE TAB 200", "008909"),
                    ("METRONIDAZOLE TAB 400", "081274"),
                    # ("MILID 200 MG TABLET", "777777"),
                    # ("MILID 400 MG TABLET", "777777"),
                    ("MINGAIR 10 MG TABLET", "038427"),
                    ("MINGAIR 5 MG TABLET", "038426"),
                    ("MOXILIUM 125 MG SUSPEN 45 ML", "006783"),
                    ("MOXILIUM 250 MG CAP", "006784"),
                    ("MOXILIUM 250 MG SUSPEN 60 ML", "012649"),
                    ("MOXILIUM 500 MG CAP", "008908"),
                    ("MOXILIUM DROPS 10 ML", "006782"),
                    ("Obexil 20 mg", "032259"),
                    ("PC-LAC SYRUP 120 ML", "019133"),
                    ("PROBITOR 20 MG CAPSUL", "016654"),
                    ("SAVELOX 250MG TABLET", "032255"),
                    ("SAVELOX 500MG TABLET", "029328"),
                    ("SUPRACEF CAPSUL", "024820"),
                    ("SUPRACEF SUSPEN 30 ML", "024819"),
                    ("SUPRACEF-DS SYRUP 30 ML", "028727"),
                    ("SUPRALOX SUSPEN 50 ML", "028728"),
                    ("SUPRALOX TABLET", "028728"),
                    ("TRAMAGESIC INJ 5 AMPS", "026920"),
                    ("TRAMGESIC CAPSUL", "029327"),
                    ("VIGROL FORTE TABLET", "007018"),
                    ("VIKONON FORTE SYRUP 120 ML", "006406"),
                ]
                PRODUCT_PREFIXES.sort(key=lambda p: -len(p[0]))
                PRODUCT_START_WORDS = {
                    p.split()[0].upper() for p, _ in PRODUCT_PREFIXES
                }

                def is_zero(v):
                    # Handles "0", "0.0", "-0", blank/NaN-ish values.
                    try:
                        return float(str(v).replace(",", "")) == 0
                    except (ValueError, TypeError):
                        return str(v).strip().upper() in ("", "NAN", "-", "N/A")

                def split_name_and_values(line):
                    tokens = re.sub(r"\s+", " ", line).strip().split(" ")

                    def is_number(t):
                        return re.fullmatch(r"-?\d+(\.\d+)?", t) is not None

                    boundary = len(tokens)
                    for i in range(len(tokens)):
                        if tokens[i:] and all(is_number(t) for t in tokens[i:]):
                            boundary = i
                            break
                    return " ".join(tokens[:boundary]), tokens[boundary:]

                def decode_header_columns(page, extra_stopwords=()):
                    """
                    Reads the header block above the first product row, groups its words
                    by x-position (column), and joins each column's text top-to-bottom
                    to recover the real brick name -- regardless of column count, order,
                    or spacing. `extra_stopwords` excludes this page's own metadata text
                    (company name, "TOWN WISE REPORT", team name, dates) so nothing
                    needs to be hardcoded even if the team name changes.
                    """
                    stopwords = {w.upper() for w in extra_stopwords}
                    words = page.extract_words()
                    starts = [
                        w["top"]
                        for w in words
                        if w["text"].upper() in PRODUCT_START_WORDS
                    ]
                    if not starts:
                        return None
                    cutoff = min(starts) - 1
                    header_words = [
                        w
                        for w in words
                        if w["top"] < cutoff
                        and w["text"].upper() not in stopwords
                        and "/" not in w["text"]
                    ]
                    cols = {}
                    for w in header_words:
                        x = round(w["x0"], 1)
                        cols.setdefault(x, []).append((w["top"], w["text"]))
                    col_list = []
                    for x in sorted(cols.keys()):
                        parts = sorted(cols[x], key=lambda tw: tw[0])
                        col_list.append((x, "".join(t for _, t in parts)))
                    return col_list

                def resolve_columns(col_list):
                    """(x0, brick_name) for real bricks only -- TOTAL etc dropped, and
                    an unrecognised header keeps its raw text (never silently mislabels
                    a new brick with an old, unrelated name)."""
                    resolved, unknown = [], []
                    for x, tok in col_list:
                        if tok.upper() in NON_BRICK_HEADER_TOKENS:
                            continue
                        name = HEADER_ALIASES.get(tok)
                        if name is None:
                            name = tok
                            unknown.append(tok)
                        resolved.append((x, BRICK_ALIASES.get(name, name)))
                    if unknown:
                        print(
                            f"[Sargodha] Unrecognised header token(s): {unknown} "
                            f"-- add proper names to HEADER_ALIASES."
                        )
                    return resolved

                for page in pdf.pages:
                    raw = re.sub("\n", "$", page.extract_text()).split("$")
                    try:
                        anchor = next(
                            i for i, l in enumerate(raw) if "TOWN WISE REPORT" in l
                        )
                    except StopIteration:
                        anchor = 3
                    # company name, "TOWN WISE REPORT.." and "..TEAM.." lines
                    meta_lines = raw[: anchor + 2]
                    body = raw[anchor + 2 :]
                    body = body[:-2]

                    meta_stopwords = {
                        tok
                        for line in meta_lines
                        for tok in re.sub(r"[^A-Za-z0-9/&]", " ", line).split()
                    }
                    col_list = decode_header_columns(
                        page, extra_stopwords=meta_stopwords
                    )
                    brick_cols = resolve_columns(col_list) if col_list else []
                    brick_names_in_order = [name for _, name in brick_cols]

                    for line in body:
                        name, values = split_name_and_values(line)
                        first_word = name.split(" ")[0].upper() if name else ""
                        if first_word not in PRODUCT_START_WORDS:
                            continue

                        matched_code = None
                        for prefix, code in PRODUCT_PREFIXES:
                            if name.startswith(prefix):
                                matched_code = code
                                break
                        if matched_code is None or matched_code == "777777":
                            continue

                        # Take values left-to-right in the SAME order the header was
                        # just decoded in -- this is what makes reordering safe, and
                        # naturally drops any trailing TOTAL/trade-value columns
                        # (even when they run together with no space, e.g. "2594116859700").
                        for brick_name, val in zip(brick_names_in_order, values):
                            if is_zero(val):
                                continue
                            products.append(matched_code)
                            result.append([matched_code, brick_name, val])

                for r in result:
                    for i in item_list:
                        if r[0] == i[0]:
                            r.insert(1, i[1])
                            r.append(i[2])
                result = green_team_bricks(result)
                for r in result:
                    for t in tt_list:
                        if r[2] == t[0]:
                            r.insert(4, t[1])
                return result
            elif dist_city == "Mianwali":
                result = []
                new_result = []
                products = []

                PAGE1_NAME_ALIASES = {
                    "PIP LAN": "PIPLAN",
                    "KAMMR MASHA NI": "KAMAR MASHANI",
                    "WAN BHAC HRAN": "WAN BHACHRAN",
                    "LA WA": "LAWA",
                    "MIAN": "MAINWALI MWL",
                    "SULTN KHEL": "SULTAN KHEL",
                    "HAR HOLI": "HARNOLI",
                    "MUSA KHEL": "MUSAKHEL",
                    "SHA DIA": "SHADIA",
                    "QUAID ABAD": "QUAIDABAD MWL",
                    "DHQ MIAN": "DHQ MIANWALI",
                    "CHAK RALA": "CHAKRALA MWL",
                    "CHASH MA": "CHASHMA",
                    "KUND IAN": "KUNDIAN",
                    "RIK": "RIKHI",
                }

                PAGE2_NAME_ALIASES = {
                    "ISKND ABAD": "ISKANDERABAD",
                    "KALA BAGH": "KALABAGH",
                    "KOT CHAND": "KOT CHANDNA",
                    "MOUCH": "MOCHH",
                }

                PRODUCT_PREFIXES = [
                    ("AFLOXAN CAP 2*10.s", "008376"),
                    ("AFLOXAN TAB 3*10.s", "017230"),
                    ("JETEPAR 10ML AMPS 5.s", "008999"),
                    ("JETEPAR 2ML AMPS 10.s", "004348"),
                    ("JETEPAR CAP 20.s", "002392"),
                    ("JETEPAR SYP 112ML", "002188"),
                    ("MAIORAD 3ML AMPS 6.s", "009072"),
                    ("MAIORAD TAB 3*10.s", "012961"),
                ]

                def build_page1_bricks(page, x_tol=6):
                    # Reconstruct page 1's brick names straight from the
                    # PDF's own header, by grouping header words into
                    # columns based on their x-position (since column
                    # names can wrap across 2-3 lines in the PDF).
                    words = page.extract_words()
                    lines = {}
                    for w in words:
                        lines.setdefault(round(w["top"], 1), []).append(w)
                    sorted_tops = sorted(lines.keys())

                    # find the first product row (its top y-position) --
                    # everything above it is header/title/date text
                    first_product_top = None
                    for top in sorted_tops:
                        line_text = " ".join(
                            w["text"] for w in sorted(lines[top], key=lambda w: w["x0"])
                        )
                        if any(
                            line_text.startswith(prefix)
                            for prefix, _ in PRODUCT_PREFIXES
                        ):
                            first_product_top = top
                            break

                    # the brick header lines are everything between the
                    # last date line (contains "/") and the first product
                    # row -- this skips the company name / report title
                    # lines automatically, no matter their exact wording
                    last_date_top = None
                    for top in sorted_tops:
                        if first_product_top is not None and top >= first_product_top:
                            break
                        line_text = " ".join(w["text"] for w in lines[top])
                        if "/" in line_text:
                            last_date_top = top

                    header_tops = [
                        t
                        for t in sorted_tops
                        if (last_date_top is None or t > last_date_top)
                        and (first_product_top is None or t < first_product_top)
                    ]
                    header_words = []
                    for t in header_tops:
                        header_words.extend(lines[t])

                    # group header words into columns by x-position
                    cols = []
                    for w in sorted(header_words, key=lambda w: w["x0"]):
                        placed = False
                        for c in cols:
                            if abs(c["x0"] - w["x0"]) <= x_tol:
                                c["words"].append((w["top"], w["text"]))
                                placed = True
                                break
                        if not placed:
                            cols.append(
                                {"x0": w["x0"], "words": [(w["top"], w["text"])]}
                            )
                    cols.sort(key=lambda c: c["x0"])

                    bricks_out = []
                    for c in cols:
                        txt = " ".join(
                            t for _, t in sorted(c["words"], key=lambda x: x[0])
                        )
                        bricks_out.append(PAGE1_NAME_ALIASES.get(txt, txt))
                    return bricks_out

                sales = []
                bricks = []
                bricks2 = []
                second_page = False
                for x in range(0, len(pdf.pages)):
                    page_obj = pdf.pages[x]
                    data = page_obj.extract_text()
                    data = re.sub("\n", "$", data)
                    data = data.split("$")
                    find_second_page = re.search(r"TOTAL", data[3])
                    if find_second_page != None:
                        second_page = True
                        # Rebuild page 2's brick list from this PDF's own
                        # header (2 wrapped lines: e.g. "ISKND KALA KOT
                        # MOUCH TOTAL" + "ABAD BAGH CHAND" -> the first
                        # len(line2) names get a 2nd line joined on, the
                        # rest (MOUCH, TOTAL) are single-word).
                        line1 = data[3].split()
                        line2 = data[4].split()
                        raw_names = []
                        for w_i in range(len(line1)):
                            if w_i < len(line2):
                                raw_names.append(line1[w_i] + " " + line2[w_i])
                            else:
                                raw_names.append(line1[w_i])
                        raw_names = raw_names[:-1]  # drop trailing "TOTAL"
                        bricks2 = [PAGE2_NAME_ALIASES.get(n, n) for n in raw_names]
                        data = data[5:-1]
                    else:
                        second_page = False
                        # rebuild page 1's brick list dynamically from
                        # THIS page's own header, instead of a fixed list
                        bricks = build_page1_bricks(page_obj)
                        data = data[6:-2]
                    for i in range(0, len(data)):
                        line = re.sub(r"\s+", " ", data[i]).strip()
                        matched_code = None
                        remainder = None
                        for prefix, code in PRODUCT_PREFIXES:
                            if line.startswith(prefix):
                                matched_code = code
                                remainder = line[len(prefix) :].strip()
                                break
                        if matched_code is None:
                            continue  # not a recognised product row (e.g. the
                            # trailing "Trade Value ..." line) -- skip
                            # it instead of crashing on it
                        values = remainder.split()
                        products.append(matched_code)
                        if second_page == True:
                            sales.append(
                                values[: len(bricks2)]
                            )  # drop trailing total qty/value
                        else:
                            sales.append(
                                values[-len(bricks) :]
                            )  # dynamic column count, not hardcoded "19"

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
                        if new_result[r][0] == i[0]:
                            new_result[r].insert(1, i[1])
                            new_result[r].append(i[2])
                new_result = green_team_bricks(new_result)
                for r in new_result:
                    for t in tt_list:
                        if r[2] == t[0]:
                            r.insert(4, t[1])
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
                new_result = green_team_bricks(new_result)
                for r in new_result:
                    for t in tt_list:
                        if r[2] == t[0]:
                            r.insert(4, t[1])
                return new_result
            elif dist_city == "Mingora":
                result = []
                new_result = []
                PRODUCT_NAME_TO_CODE = [
                    ("JETEPAR INJ 10ML", "008999"),
                    ("JETEFAR 112ML SYP", "002188"),
                    ("JETEPAR 112ML SYP", "002188"),
                    ("JETEPAR CAP", "002392"),
                    ("JETEPAR INJ 2ML", "004348"),
                    ("MAIORAD TAB", "012961"),
                    ("MAIORAD INJ", "009072"),
                ]

                OLD_ID_TO_CODE = {
                    "2700": "008999",
                    "2701": "004348",
                    "2702": "002392",
                    "2703": "002188",
                    "2727": "008376",
                    "2728": "017230",
                    "2737": "009072",
                    "2738": "012961",
                    "2705": "024819",
                    "2706": "028727",
                    "2707": "024820",
                    "2708": "006406",
                    "2709": "007018",
                    "2710": "005425",
                    "2713": "028729",
                    "2714": "016654",
                    "2730": "006783",
                    "2731": "012649",
                    "2732": "008908",
                    "2733": "006784",
                    "2734": "006782",
                    "2739": "026920",
                    "2740": "029327",
                    "2741": "028728",
                    "2754": "019133",
                    "2756": "038426",
                    "2757": "038426",
                    "2759": "032259",
                    "2760": "032255",
                    "2761": "029328",
                    "7153": "081838",
                    "7154": "081274",
                }

                def code_for(name, groupid):
                    for label, code in PRODUCT_NAME_TO_CODE:
                        if label in name:
                            return code
                    return OLD_ID_TO_CODE.get(groupid)

                BRICK_VOCAB = [
                    (("MINGORA-1",), "MINGORA 1"),
                    (("MINGORA-2",), "MINGORA 2"),
                    (("MINGORA-3",), "MINGORA 3"),
                    (("BARIKOT",), "BARIKOT"),
                    (("BUTKHELA",), "BATKHELA MALAKAND"),
                    (("BUNIR",), "BUNER"),
                    (("BESHAM",), "BISHAM"),
                    (("MATTA",), "MATTA SWAT"),
                    (("K.KHELA-4BAG",), "KHWAZA KHELA"),
                    (("AIRPORT", "ROAD+KABAL"), "AIRPORT ROAD & KABAL"),
                    (("KABAL",), "KABAL"),
                    (("MAD.BAH.FATH",), "MADYAN & BAHRAIN SWAT & FATHE KHAN"),
                    (("PURAN",), "PURAN"),
                    (("SAIDU+CENTER",), "SAIDU & CENTER"),
                    (("COUNTER", "SALE"), "COUNTER SALE"),
                    (("SAIDU", "DOCTORS"), "SAIDU DOCTORS"),
                    (("LOCAL",), "LOCAL"),
                    (("TIMARGARA",), "TIMARGARA MGR"),
                    (("SOLD",), "SOLD AREA"),
                ]
                DROP_TOKENS = {("Total", "Sale")}

                def match_bricks(tokens):
                    names = []
                    i = 0
                    while i < len(tokens):
                        matched = False
                        for span in (2, 1):
                            if i + span > len(tokens):
                                continue
                            chunk = tuple(tokens[i : i + span])
                            if chunk in DROP_TOKENS:
                                i += span
                                matched = True
                                break
                            for vocab_tokens, clean in BRICK_VOCAB:
                                if vocab_tokens == chunk:
                                    names.append(clean)
                                    i += span
                                    matched = True
                                    break
                            if matched:
                                break
                        if not matched:
                            names.append(
                                tokens[i]
                            )  # unknown -- keep raw so it's visible, not silently dropped
                            i += 1
                    return names

                all_rows = {}  # groupid -> {"code":..., "bricks": {brick: qty}}

                for page in pdf.pages:
                    txt = page.extract_text()
                    if not txt:
                        continue
                    lines = txt.split("\n")

                    header_idx = None
                    for i, l in enumerate(lines):
                        if l.startswith("Product N") and "Trade" in l:
                            header_idx = i
                            break
                    if header_idx is None:
                        continue

                    header_rest = re.sub(r"^.*?Trade\s+", "", lines[header_idx])
                    tokens = header_rest.split()

                    # a brick name can wrap onto the line right after the
                    # header (e.g. "AIRPORT" / "ROAD+KABAL") -- that
                    # continuation line sits before the "Groupid ..." line
                    row_i = header_idx + 1
                    if row_i < len(lines) and not lines[row_i].strip().startswith(
                        "Groupid"
                    ):
                        cont_tokens = lines[row_i].strip().split()
                        # the wrapped 2nd line belongs to whichever earlier
                        # column needed it (here: "AIRPORT" -> "ROAD+KABAL"),
                        # not necessarily the last column on the first line
                        if "AIRPORT" in tokens:
                            insert_at = tokens.index("AIRPORT") + 1
                            tokens = (
                                tokens[:insert_at] + cont_tokens + tokens[insert_at:]
                            )
                        else:
                            tokens += cont_tokens
                        row_i += 1

                    page_bricks = match_bricks(tokens)

                    # skip down to the first real data row (starts with a
                    # numeric Groupid)
                    while row_i < len(lines) and not re.match(
                        r"^\d{3,6}\s", lines[row_i].strip()
                    ):
                        row_i += 1

                    while row_i < len(lines):
                        line = lines[row_i].strip()
                        if line.startswith("Group Sale Amount"):
                            break
                        m = re.match(r"^(\d{3,6})\s+(.*)$", line)
                        if not m:
                            row_i += 1
                            continue
                        groupid, rest = m.group(1), m.group(2)
                        rtokens = rest.split()
                        price_idx = None
                        for ti, tok in enumerate(rtokens):
                            if re.match(r"^-?\d+\.\d+$", tok):
                                price_idx = ti
                                break
                        if price_idx is None:
                            row_i += 1
                            continue
                        name = " ".join(rtokens[:price_idx])
                        values = rtokens[price_idx + 1 :]

                        code = code_for(name, groupid)
                        if code:
                            entry = all_rows.setdefault(
                                groupid, {"code": code, "bricks": {}}
                            )
                            for b_i, brick in enumerate(page_bricks):
                                u_idx, bo_idx = b_i * 2, b_i * 2 + 1
                                units = int(values[u_idx]) if u_idx < len(values) else 0
                                bonus = (
                                    int(values[bo_idx]) if bo_idx < len(values) else 0
                                )
                                entry["bricks"][brick] = (
                                    entry["bricks"].get(brick, 0) + units + bonus
                                )
                        row_i += 1

                for groupid, entry in all_rows.items():
                    for brick, qty in entry["bricks"].items():
                        result.append([entry["code"], brick, str(qty)])

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
                new_result = green_team_bricks(new_result)
                for r in new_result:
                    for t in tt_list:
                        if r[2] == t[0]:
                            r.insert(4, t[1])
                return new_result

            elif dist_city == "Multan":
                result = []
                products = []
                new_result = []
                sales = []

                KNOWN_BRICKS = [
                    "Others",
                    "GARDEN TOWN",
                    "MUZAFFAR ABAD",
                    "MODEL TOWN BYPASS",
                    "BUCH VILLAS",
                    "M.A JINNAH ROAD",
                    "NISHTER ROAD MULTAN",
                    "MULTAN CANTT",
                    "OLD SHUJABAD ROAD, MULTAN.",
                    "RAILWAY ROAD MULTAN",
                    "CHOWK SHAH ABBAS, MULTAN.",
                    "MUMTAZABAD MULTAN",
                    "B.C.G. CHOWK MULTAN",
                    "VEHARI ROAD MULTAN",
                    "CHUNGI NO.14 MULTAN",
                    "CHUNGI NO. 1 MULTAN",
                    "T.B. ROAD MULTAN",
                    "NEW MULTAN",
                    "CHOWK QAZAFI MULTAN",
                    "SAMIJABAD MULTAN",
                    "TOWN HALL WH-SALE MULTAN",
                    "CHUNGI NO.9 MULTAN",
                    "GULGASHT MULTAN",
                    "BOSAN ROAD, MULTAN.",
                    "NAWAB PUR ROAD MULTAN",
                    "KHANEWAL ROAD MULTAN",
                    "SHER SHAH ROAD",
                    "TOWN HALL RETAIL MULTAN",
                    "SHAH RUKN-EALAM MULTAN",
                    "VEHARI CHOWK MULTAN",
                    "PULL BARARAN",
                    "PAK ARAB",
                    "QASIM BELA",
                    "IBN-E-SENA HOSPITAL",
                    "VEHARI ROAD (MJ)",
                    "AHSAN M.C NISHTER",
                    "KHAN GARH",
                    "W-WALI",
                    "ROHILANWALI",
                    "SHAHARSULTAN",
                    "JALALPUR",
                    "SHUJABAD",
                    "NISHTER-II",
                    "MAKH-AALI",
                    "ADDALAR",
                    "BASTI MALOOK",
                    "DUNYA PUR",
                    "MUZAFFAR GRAH",
                    "SHAH JAMAL",
                    "GUJRAT",
                    "BASEERA",
                    "QURESHIMORE",
                    "MIAN CHANNU",
                    "ABDUL HAKIM",
                    "TULAMBA",
                    "MAKH-PUR",
                    "PulBagar",
                    "PULL 12 - MEEL",
                    "SALAR WAHIN",
                    "ADDA BAND BOSAN",
                    "KABIRWALA",
                    "KHANEWAL",
                    "RANWAN",
                    "TATAY PUR",
                    "BODHLA SANT",
                    "PULL - 14",
                    "MAKH-RASHID",
                    "THATTA",
                    "MAILSI",
                    "JAHANIA",
                    "CMH Multan Cantt",
                    "OLD SHUJABAD ROAD",
                    "PAK GATE MULTAN",
                    "HAFIZ JAMAL ROAD",
                    "DAULAT GATE MULTAN",
                    "MASOOM SHAH ROAD",
                    "TOWN HALL WHOLE SALLER",
                    "TUGHLAQ ROAD MULTAN",
                    "CHOWK M.D.A. MULTAN",
                    "SOURAJ MIANI ROAD",
                    "TOWN HALL RETAILERS",
                    "WASSANDAY WALI",
                    "MAKHDOOM ALLI",
                    "CHACK 5- FAIZ",
                    "ADDA LAR",
                    "QURESHI MORE",
                    "SANAWAN",
                    "EID GAH MULTAN",
                    "MAKHDOOM RASHID",
                    "TARIQ ROAD",
                    "CHOWK SHAH ABBAS",
                    "NAWAB PUR ROAD",
                    "VEHARI CHOWK",
                    "KHAN BELA",
                    "MAKHDOOM PUR POHARAN",
                ]

                OLD_CODE_VARIANTS = {
                    "(117) CHUNGI NO. 1 MULTAN": "CHUNGI NO. 1 MULTAN",
                    "(129) CHUNGI NO.9 MULTAN": "CHUNGI NO.9 MULTAN",
                    "(406) CHACK 5- FAIZ": "CHACK 5- FAIZ",
                    "(706) PULL 12 - MEEL": "PULL 12 - MEEL",
                    "(804) PULL - 14": "PULL - 14",
                }

                def fp_full(s):
                    letters = re.sub(r"[^A-Za-z0-9]", "", s).upper()
                    return "".join(sorted(letters))

                def fp_nodigit(s):
                    letters = re.sub(r"[^A-Za-z]", "", s).upper()
                    return "".join(sorted(letters))

                FULL_MAP = {fp_full(n): n for n in KNOWN_BRICKS}
                for raw, clean in OLD_CODE_VARIANTS.items():
                    FULL_MAP[fp_full(raw)] = clean
                NODIGIT_MAP = {}
                for name in KNOWN_BRICKS:
                    if re.search(r"\d", name):
                        continue  # skip ambiguous ones (see ADDA LAR/ADDALAR etc.)
                    NODIGIT_MAP[fp_nodigit(name)] = name

                def decode_brick(cell):
                    """Try an exact (digit-preserving) fingerprint match
                    first (works for the new format and for old-format
                    bricks with a registered code variant), then fall back
                    to a digit-stripped match (works for the rest of the
                    old format's "(code) name" cells). Unknown bricks fall
                    back to the raw decoded text so they stay visible
                    instead of silently vanishing -- add a new entry to
                    KNOWN_BRICKS above if you see one of those."""
                    if cell is None:
                        return ""
                    literal = " ".join(str(cell).split("\n")).strip()
                    f1 = fp_full(literal)
                    if f1 in FULL_MAP:
                        return FULL_MAP[f1]
                    f2 = fp_nodigit(literal)
                    if f2 in NODIGIT_MAP:
                        return NODIGIT_MAP[f2]
                    return literal

                all_bricks = []
                for x in range(0, len(pdf.pages)):
                    data = pdf.pages[x].extract_table()
                    header = data[0]
                    page_bricks = [
                        decode_brick(header[i]) for i in range(1, len(header) - 1)
                    ]
                    all_bricks.extend(page_bricks)

                    last_page = x == len(pdf.pages) - 1
                    page_rows = data[1:-1]  # drop header row + trailing Total row

                    if x == 0:
                        sales = page_rows
                    else:
                        for i, row in enumerate(page_rows):
                            if i < len(sales) and sales[i][0] == row[0]:
                                if last_page:
                                    sales[i] = sales[i][:] + row[1:-1]
                                else:
                                    sales[i] = sales[i][:] + row[1:]
                            else:
                                sales.append(row)
                bricks = all_bricks

                BRICK_RENAME = {
                    # "PDF/DECODED NAME": "TERRITORY TREE NAME",
                    "CHOWK QAZAFI MULTAN": "CHOWK QAZAFI",
                    "TOWN HALL WH-SALE MULTAN": "TOWN HALL WHOLE SALLER",
                    "CHUNGI NO.9 MULTAN": "CHUNGI NO 9",
                    "GULGASHT MULTAN": "GULGASHT",
                    "SHAH RUKN-EALAM MULTAN": "SHAH RUKN E ALAM",
                    "ROHILANWALI": "ROHILLAN WALI",
                    "JALALPUR": "JALAL PUR",
                    "GUJRAT": "GUJRAT OS",
                    "PulBagar": "PULL BAGAR MULTAN",
                    "PULL 12 - MEEL": "PULL 12 MEEL",
                    "KABIRWALA": "KABIR WALA",
                    "BODHLA SANT": "BUDHLA SANT",
                    "MAKH-RASHID": "MAKHDOOM RASHEED",
                    "MAKH-AALI": "MAKHDOOM ALI",
                    "MUZAFFAR GRAH": "MUZAFFAR GARH",
                    "NAWAB PUR ROAD MULTAN": "NAWAB PUR ROAD",
                    "OLD SHUJABAD ROAD, MULTAN.": "OLD SHUJABAD ROAD",
                    "B.C.G. CHOWK MULTAN": "BCG CHOWK",
                    "VEHARI ROAD MULTAN": "VEHARI ROAD",
                    "CHUNGI NO.14 MULTAN": "CHUNGI NO 14",
                    "VEHARI CHOWK MULTAN": "VEHARI CHOWK",
                    "W-WALI": "WASSANDAY WALI",
                    "SHAHARSULTAN": "SHAHER SULTAN",
                    "NISHTER-II": "NISHTER 2",
                    "MAKH-PUR": "MAKHDOOM PUR PAHORAN",
                    "PULL - 14": "PULL 14",
                    "THATTA": "THATTA MULTAN",
                    "JAHANIA": "JAHANIAN",
                    "RAILWAY ROAD MULTAN": "RAILWAY ROAD",
                    "CHOWK SHAH ABBAS, MULTAN.": "CHOWK SHAH ABBAS",
                    "CHUNGI NO. 1 MULTAN": "CHUNGI NO 1",
                    "SAMIJABAD MULTAN": "SAMIJABAD",
                    "BOSAN ROAD, MULTAN.": "BOSAN ROAD",
                    "NAWAB PUR ROAD MULTAN": "NAWAB PUR ROAD",
                    "KHANEWAL ROAD MULTAN": "KHANEWAL",
                    "TOWN HALL RETAIL MULTAN": "TOWN HALL RETAILERS",
                    "VEHARI ROAD (MJ)": "VEHARI ROAD MJ",
                    "AHSAN M.C NISHTER": "AHSAN MEDICINE COMPANY NISHTER",
                }
                bricks = [BRICK_RENAME.get(b, b) for b in bricks]

                for row in sales:
                    products.append(row[0])

                for i in range(0, len(products)):
                    sales[i] = sales[i][1:]
                    name = re.sub(r"\s+", " ", str(products[i])).strip().upper()
                    if "JETEPAR 2ML INJ" in name:
                        products[i] = "004348"
                    elif "JETEPAR CAP" in name:
                        products[i] = "002392"
                    elif "JETEPAR SYP" in name:
                        products[i] = "002188"
                    elif "JETEPAR" in name and "10ML" in name:
                        products[i] = "008999"
                    elif "MAIORAD INJ" in name or "MAIORAD 3ML" in name:
                        products[i] = "009072"

                for p in range(0, len(products)):
                    for s in range(0, len(sales[p])):
                        if s >= len(bricks):
                            break
                        child = [products[p], bricks[s], sales[p][s]]
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
                            break
                new_result = green_team_bricks(new_result)
                for r in new_result:
                    matched_territory = None
                    matched_price = None
                    for t in tt_list:
                        if r[2] == t[0]:
                            matched_territory = t[1]
                            break
                    if matched_territory is not None:
                        for i in item_list:
                            if r[0] == i[0]:
                                matched_price = i[2]
                                break
                    r.insert(4, matched_territory)
                    r.append(matched_price)
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
                result = green_team_bricks(result)
                for r in result:
                    for t in tt_list:
                        if r[2] == t[0]:
                            r.insert(4, t[1])
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
                    "KHAIRPUR TAMIWALI",
                    "HASILPUR",
                    "LODHRAN",
                    "KAHROR PAKKA",
                    "YAZMAN CITY",
                    "TAILWALA",
                    "AHMEDPUR",
                    "UCH SHARIF",
                    "MUBARAKPUR",
                ]

                # ---------- helpers (local to this block) ----------
                def _clean(s):
                    """Uppercase, unify quotes, collapse newlines/spaces."""
                    s = (s or "").replace("\u2019", "'").replace("`", "'")
                    return re.sub(r"\s+", " ", s).strip().upper()

                def _k(s):
                    """Key for brick header matching: letters/digits only."""
                    return re.sub(r"[^a-z0-9]", "", (s or "").lower())

                # Product-name -> item-code lookup (old + new PDFs)
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
                    ("MAIORAD 3ML INJ 6S", "009072"),
                    ("MAIORAD TAB. 30S", "012961"),
                    ("MAIORAD TAB 30S", "012961"),
                    ("AFLOXON 150MG CAP. 20S", "008376"),
                    ("AFLOXON 150MG CAP 20S", "008376"),
                    ("AFLOXON 300MG TAB. 30S", "017230"),
                    ("AFLOXON 300MG TAB 30S", "017230"),
                ]

                def code_for(name):
                    name = _clean(name)
                    if not name:
                        return None
                    for label, code in PRODUCT_NAME_TO_CODE:
                        if _clean(label) in name:
                            return code
                    return None

                # Header text (as printed in PDF) -> brick name
                LOCAL_ALIASES = {
                    # Bahawalnagar
                    "bwncity": "BAHAWALNAGAR CITY",
                    "bahawalnagarcity": "BAHAWALNAGAR CITY",
                    "bahawalnagar": "BAHAWALNAGAR CITY",
                    "dongabonga": "DUNGA BUNGA",
                    "dungabunga": "DUNGA BUNGA",
                    "haroonabad": "HAROONABAD",
                    "faqirwali": "FAQIR WALA",
                    "faqirwala": "FAQIR WALA",
                    "khichiwala": "KHICHI WALA",
                    "fortabbas": "FORT ABBAS",
                    "maroot": "MAROT",
                    "marot": "MAROT",
                    "madrasa": "MADRASA",
                    "madrasah": "MADRASA",
                    "chishtian": "CHISHTIAN",
                    "dharanwala": "DAHRANWALA",
                    "dahranwala": "DAHRANWALA",
                    "minchinaabad": "MINCHINABAD",
                    "minchinabad": "MINCHINABAD",
                    "mclodganj": "MCLEOD GANJ",
                    "mcleodganj": "MCLEOD GANJ",
                    "mandisadqganj": "MANDI SADQ GANJ",
                    "mandisadiqganj": "MANDI SADQ GANJ",
                    "bahawalpura": "BAHAWALPUR A",
                    "bahawalpurb": "BAHAWALPUR B",
                    "bahawalpurc": "BAHAWALPUR C",
                    "bahawalpurd": "BAHAWALPUR D",
                    "khairpur": "KHAIRPUR TAMIWALI",
                    "khairpurtamiwali": "KHAIRPUR TAMIWALI",
                    "hasilpur": "HASILPUR",
                    "lodhran": "LODHRAN",
                    "kahrorpakka": "KAHROR PAKKA",
                    "yazmancity": "YAZMAN CITY",
                    "yazman": "YAZMAN CITY",
                    "tailwala": "TAILWALA",
                    "ahmedpur": "AHMEDPUR",
                    "uchsharif": "UCH SHARIF",
                    "mubarakpur": "MUBARAKPUR",
                }

                def _qty(val):
                    """Cell -> clean quantity string ('0' if empty/invalid)."""
                    val = (val or "").split("\n")[0]
                    val = val.strip().replace(",", "")
                    if val == "":
                        return "0"
                    try:
                        float(val)
                    except ValueError:
                        return "0"
                    return val

                result = []
                new_result = []

                for page in pdf.pages:
                    full_text = page.extract_text()
                    if not full_text:
                        continue

                    # Bahawalpur vs Bahawalnagar: check the whole page header
                    is_bahawalpur = bool(
                        re.search(r"Bahawalpur", full_text, re.I)
                        and not re.search(r"Bahawalnagar", full_text, re.I)
                    )
                    area_bricks = bahawalpur_bricks if is_bahawalpur else bricks

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
                        # ============ NEW FORMAT: bordered brick grid ============
                        # Columns are mapped by header text, so it works with or
                        # without the trailing "Total" column, and with wrapped
                        # product names ("JETEPAR 10ML\nINJ 5S").
                        for table in page.extract_tables() or []:
                            if not table:
                                continue

                            # 1) header row -> {column index: brick}
                            col_map = {}
                            for row in table:
                                if not row:
                                    continue
                                m = {}
                                for ci, cell in enumerate(row):
                                    b = LOCAL_ALIASES.get(_k(cell))
                                    if b:
                                        m[ci] = b
                                if len(m) >= 3:
                                    col_map = m
                                    break

                            # 2) product rows
                            for row in table:
                                if not row:
                                    continue
                                name_idx = None
                                for ci, cell in enumerate(row):
                                    if cell and code_for(cell):
                                        name_idx = ci
                                        break
                                if name_idx is None:
                                    continue
                                code = code_for(row[name_idx])

                                if col_map:
                                    pairs = [
                                        (b, row[ci])
                                        for ci, b in col_map.items()
                                        if ci < len(row)
                                    ]
                                else:
                                    # fallback: cells after name + rate col
                                    pairs = list(zip(area_bricks, row[name_idx + 2 :]))

                                for brick, val in pairs:
                                    result.append([code, brick, _qty(val)])

                # ---------- same post-processing as before ----------
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
                new_result = green_team_bricks(new_result)
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
                new_result = green_team_bricks(new_result)
                for r in new_result:
                    for t in tt_list:
                        if r[2] == t[0]:
                            r.insert(4, t[1])
                return new_result


def _is_zero_sale(val):
    if val is None:
        return False
    s = str(val).strip().replace(",", "")
    if s == "" or s.lower() in ("nan", "none", "-"):
        return False
    try:
        return float(s) == 0
    except ValueError:
        return False


def _remove_zero_sale_rows(rows):
    if not rows:
        return rows
    out = []
    for r in rows:
        try:
            # matched rows: [code, name, brick, sale, parent, price] -> sale index 3
            # unmatched rows: [code, brick, sale] -> sale index 2
            idx = 3 if len(r) >= 5 else 2
            if _is_zero_sale(r[idx]):
                continue
        except (IndexError, TypeError):
            pass
        out.append(r)
    return out


# new code
@frappe.whitelist(allow_guest=True)
def parse_pdf(pdf_file, parse_check, parent_detail):
    global _debug_bricks
    _debug_bricks = []
    result = _parse_pdf(pdf_file, parse_check, parent_detail)
    result = _remove_zero_sale_rows(result)
    return {"result": result, "parsed_bricks": _debug_bricks}


# ======================================================================
# VALIDATE CODE  — apni MAUJUDA brick_wise_sale.py ke bilkul NEECHE paste karein
# (aapka purana parse_pdf / class / baqi code jaisa hai waisa hi rahe)
#
# Shart: isi file mein `parse_pdf` function maujood ho (wo aapke paas hai),
# kyunke validate usi ko dobara chala kar PDF ka expected output leta hai.
# Helper names `_bw_` se shuru hote hain taake aapke purane code se na takrayein.
# ======================================================================
import json
import math
import re
from collections import defaultdict

import frappe
from frappe.utils import cint, flt, getdate
from frappe.utils.nestedset import get_descendants_of

_BW_TOL = 0.01
_BW_NAN = {"nan", "none", "null", "nat", "undefined", "#n/a"}
_BW_MAX_ERRORS = 300


def _bw_bad(v):
    """None / khali / NaN / 'nan' text"""
    if v is None:
        return True
    if isinstance(v, float) and math.isnan(v):
        return True
    return isinstance(v, str) and (not v.strip() or v.strip().lower() in _BW_NAN)


def _bw_num(v):
    """'1,200' -> 1200.0 ; kharab value -> None"""
    if _bw_bad(v):
        return None
    try:
        return float(str(v).replace(",", "").strip())
    except ValueError:
        return None


def _bw_total_like(brick):
    """brick ki jagah 'Total' ya amount ('6,298.50', '984,357') likha ho."""
    b = str(brick).strip().lower()
    if re.search(r"\b(grand\s*total|sub\s*total|total|amount)\b", b):
        return True
    return bool(re.fullmatch(r"-?\d{1,3}(,\d{3})+(\.\d+)?|-?\d+\.\d+", b))


def _bw_city(city):
    city = (city or "").strip()
    return city or None  # DocType ka default "\n" hai


def _bw_run_parse(doc):
    """Aapka apna parse_pdf dobara chala kar PDF ka expected output lo."""
    detail = {
        "city": _bw_city(doc.get("city")),
        "fromDate": doc.get("from"),
        "toDate": doc.get("to"),
    }
    check = cint(doc.get("having_different_bricks")) > 0
    try:
        out = parse_pdf(doc.get("file"), check, detail)
    except Exception:
        # agar parse_pdf HTTP ki tarah string args expect karta ho
        out = parse_pdf(
            doc.get("file"),
            "true" if check else "false",
            json.dumps(detail, default=str),
        )
    if isinstance(out, dict):
        return out.get("result") or [], out.get("parsed_bricks") or []
    return out or [], []


def _bw_file_dates(pdf_file):
    """PDF ke upar likhi 'Date From: dd/mm/yyyy To: dd/mm/yyyy' -> (from_date, to_date) ya None"""
    try:
        path = frappe.get_doc("File", {"file_url": pdf_file}).get_full_path()
        lib = None
        for mod in ("pypdf", "PyPDF2"):
            try:
                lib = __import__(mod)
                break
            except ImportError:
                continue
        if not lib:
            return None
        text = " ".join((p.extract_text() or "") for p in lib.PdfReader(path).pages[:1])
        m = re.search(
            r"Date From:\s*(\d{1,2}/\d{1,2}/\d{4})\s*To:\s*(\d{1,2}/\d{1,2}/\d{4})",
            text,
        )
        if not m:
            return None
        to_date = lambda t: getdate(
            "-".join(reversed(t.split("/")))
        )  # dd/mm/yyyy -> yyyy-mm-dd
        return to_date(m.group(1)), to_date(m.group(2))
    except Exception:
        return None


def _bw_fiscal_year(d):
    fy = frappe.get_all(
        "Fiscal Year",
        filters={"year_start_date": ["<=", d], "year_end_date": [">=", d]},
        pluck="name",
        limit=1,
    )
    return fy[0] if fy else None


@frappe.whitelist()
def get_fiscal_year_from_file(pdf_file, from_date=None):
    """File ki date se Fiscal Year (JS isay file upload / process ke baad call karta hai)."""
    dates = _bw_file_dates(pdf_file)
    d = dates[0] if dates else (getdate(from_date) if from_date else None)
    return {
        "fiscal_year": _bw_fiscal_year(d) if d else None,
        "from": str(dates[0]) if dates else None,
        "to": str(dates[1]) if dates else None,
    }


@frappe.whitelist()
def validate_sale(doc):
    if isinstance(doc, str):
        doc = frappe.parse_json(doc)
    doc = frappe._dict(doc)

    errors = []
    add = errors.append
    rows = doc.get("selling_product") or []
    city = _bw_city(doc.get("city"))

    if not rows:
        return {
            "passed": False,
            "errors": ["Selling Product table khali hai."],
            "parsed_brick_count": 0,
            "matched_brick_count": 0,
        }

    # ---------- lookups (ek hi baar) ----------
    # purani saved docs mein qty 0 wali rows hoti thi — ab parser unhein nahi banata, is liye ignore
    rows = [r for r in rows if _bw_num(r.get("sale_qty")) != 0]
    bricks = {str(r.get("brick")).strip() for r in rows if not _bw_bad(r.get("brick"))}
    products = {
        str(r.get("product")).strip() for r in rows if not _bw_bad(r.get("product"))
    }

    territory = {
        t.name: t
        for t in frappe.get_all(
            "Territory",
            fields=["name", "parent_territory", "is_group"],
            filters={"name": ["in", list(bricks)]} if bricks else {"name": ""},
            limit_page_length=0,
        )
    }
    items = {
        i.name: i
        for i in frappe.get_all(
            "Item",
            fields=["name", "item_name", "trade_price", "disabled", "belong_to"],
            filters={"name": ["in", list(products)]} if products else {"name": ""},
            limit_page_length=0,
        )
    }
    city_tree = set()
    if city:
        city_tree = set(get_descendants_of("Territory", city)) | {city}
    # Green products ki bricks "<City> GT" tree (jaise "Okara GT") se aati hain
    green_root = (
        f"{city} GT" if city and frappe.db.exists("Territory", f"{city} GT") else None
    )
    green_tree = (
        (set(get_descendants_of("Territory", green_root)) | {green_root})
        if green_root
        else set()
    )
    green_root_missing_told = False

    # ---------- 1) table ki har row ----------
    seen = defaultdict(list)
    row_sum = 0.0
    for pos, r in enumerate(rows, start=1):
        no = r.get("idx") or pos
        tag = f"Row {no}"
        prod, brick = r.get("product"), r.get("brick")
        qty, price, value = (
            _bw_num(r.get("sale_qty")),
            _bw_num(r.get("product_price")),
            _bw_num(r.get("value")),
        )

        if _bw_bad(prod) and qty is None:
            add(
                f"{tag}: Khali row hai (product aur qty nahi, brick '{brick}') — delete kar dein."
            )
            continue

        for field, label in [
            ("product", "Product code"),
            ("product_name", "Product name"),
            ("brick", "Brick"),
            ("sale_qty", "Sale qty"),
            ("product_price", "Product price"),
            ("value", "Value"),
            ("brick_parent", "Brick parent"),
        ]:
            if _bw_bad(r.get(field)):
                add(f"{tag}: {label} khali / NaN hai (product={prod}, brick={brick}).")

        if (
            qty is not None
            and price is not None
            and value is not None
            and abs(qty * price - value) > _BW_TOL
        ):
            add(
                f"{tag}: Value galat — {qty:g} x {price:g} = {qty * price:g}, row mein {value:g} ({prod} / {brick})."
            )
        row_sum += value or 0

        # product
        item = None
        if not _bw_bad(prod):
            prod = str(prod).strip()
            item = items.get(prod)
            if not item:
                add(f"{tag}: Product '{prod}' Item master mein nahi mila.")
            else:
                if item.disabled:
                    add(f"{tag}: Product '{prod}' disabled hai.")
                if (
                    price is not None
                    and item.trade_price is not None
                    and abs(flt(item.trade_price) - price) > _BW_TOL
                ):
                    add(
                        f"{tag}: Price galat — row mein {price:g}, Item master (trade price) mein {flt(item.trade_price):g} ({prod})."
                    )
                pname = str(r.get("product_name") or "")
                if (
                    pname
                    and item.item_name
                    and pname.strip().lower() != item.item_name.strip().lower()
                ):
                    add(
                        f"{tag}: Product name '{pname}' Item master ke naam '{item.item_name}' se match nahi karta."
                    )
            if re.search(
                r"\bactive\b",
                f"{r.get('product_name') or ''} {item.item_name if item else ''}",
                re.I,
            ):
                add(
                    f"{tag}: Product naam mein 'Active' word hai — '{r.get('product_name')}' ({prod})."
                )

        # brick
        if not _bw_bad(brick):
            brick = str(brick).strip()
            if _bw_total_like(brick):
                add(f"{tag}: Brick ki jagah Total / amount likha hai: '{brick}'.")
            is_green = bool(item and item.get("belong_to") == "Green")
            ends_gt = brick.upper().endswith(" GT")
            if is_green and not ends_gt:
                add(
                    f"{tag}: '{prod}' Green product hai, brick ke aakhir mein 'GT' hona chahiye — '{brick}'."
                )
            if not is_green and item and ends_gt:
                add(
                    f"{tag}: '{prod}' Blue product hai lekin brick GT wali hai — '{brick}'."
                )
            t = territory.get(brick)
            if not t:
                hint = (
                    frappe.get_all(
                        "Territory",
                        filters={"name": ["like", f"%{brick}%"]},
                        pluck="name",
                        limit=1,
                    )
                    if len(brick) >= 4 and not _bw_total_like(brick)
                    else []
                )
                tip = f" Shayad sahi naam '{hint[0]}' hai." if hint else ""
                add(
                    f"{tag}: Brick '{brick}' Territory tree mein nahi hai (code ya naam galat).{tip}"
                )
            else:
                if t.is_group:
                    add(f"{tag}: '{brick}' brick nahi, group territory hai.")
                if (
                    not _bw_bad(r.get("brick_parent"))
                    and r.get("brick_parent") != t.parent_territory
                ):
                    add(
                        f"{tag}: Brick parent galat — row mein '{r.get('brick_parent')}', tree mein '{t.parent_territory}' ({brick})."
                    )
                if is_green and city:
                    if green_root and brick not in green_tree:
                        add(
                            f"{tag}: Green brick '{brick}' '{green_root}' ke neeche nahi aati (parent: {t.parent_territory})."
                        )
                    elif not green_root and not green_root_missing_told:
                        green_root_missing_told = True
                        add(
                            f"Territory '{city} GT' nahi mili — Green bricks ka tree check nahi ho saka."
                        )
                elif city and brick not in city_tree:
                    add(
                        f"{tag}: Brick '{brick}' city '{city}' ke neeche nahi aati (parent: {t.parent_territory})."
                    )

        if not _bw_bad(prod) and not _bw_bad(brick):
            seen[(str(prod).strip(), str(brick).strip())].append(no)

    for (p, b), nos in seen.items():
        if len(nos) > 1:
            add(
                f"Duplicate: Product '{p}' brick '{b}' {len(nos)} baar hai (rows {', '.join(map(str, nos))})."
            )

    if abs(flt(doc.get("total_value")) - row_sum) > 1:
        add(
            f"Total Value Sale galat — rows ka jama {row_sum:,.2f}, field mein {flt(doc.get('total_value')):,.2f} (Calculate dabayein)."
        )

    # ---------- 2) PDF se muqabla ----------
    parsed_brick_count = matched_brick_count = 0
    if not doc.get("file"):
        add("File attach nahi hai — PDF se muqabla nahi ho saka.")
    else:
        try:
            parsed, parsed_bricks = _bw_run_parse(doc)
        except Exception as e:
            parsed, parsed_bricks = [], []
            add(f"File dobara parse nahi ho saki: {e}")

        p_map = defaultdict(list)
        unmatched = defaultdict(
            set
        )  # brick -> product codes (Territory tree se match nahi hui)
        parsed_nonzero = 0
        for i, e in enumerate(parsed, start=1):
            unmatched_row = (
                len(e) < 6
            )  # parse_pdf ne parent insert nahi kiya => brick tree mein nahi mili
            e = list(e) + [None] * (6 - len(e))
            if _bw_num(e[3]) == 0:
                continue
            parsed_nonzero += 1
            if unmatched_row and not _bw_bad(e[2]):
                unmatched[str(e[2]).strip()].add(str(e[0]).strip())
            if any(_bw_bad(x) for x in (e[0], e[2], e[3])):
                add(
                    f"File row {i}: product / brick / qty NaN ya khali parse hua (product={e[0]}, brick={e[2]}, qty={e[3]})."
                )
                continue
            if _bw_total_like(e[2]):
                add(
                    f"File row {i}: Brick ki jagah Total / amount parse hua: '{e[2]}' (product {e[0]})."
                )
            p_map[(str(e[0]).strip(), str(e[2]).strip())].append(
                {"i": i, "qty": _bw_num(e[3]), "price": _bw_num(e[5])}
            )

        if unmatched:
            green_codes = set(
                frappe.get_all(
                    "Item",
                    filters={
                        "name": [
                            "in",
                            list({c for v in unmatched.values() for c in v}),
                        ],
                        "belong_to": "Green",
                    },
                    pluck="name",
                )
            )
            for b, codes in sorted(unmatched.items()):
                kind = "Green" if codes & green_codes else "Blue"
                tip = (
                    f" ('{city} GT' tree mein '{b}' naam se add karein)"
                    if kind == "Green" and city
                    else ""
                )
                add(
                    f"NaN: File ki brick '{b}' ({kind}) Territory tree se match nahi hui — spelling check karein ya tree mein add karein.{tip}"
                )

        for (p, b), lst in p_map.items():
            if len(lst) > 1:
                add(
                    f"File mein duplicate: Product '{p}' brick '{b}' {len(lst)} baar hai (file rows {', '.join(str(x['i']) for x in lst)})."
                )

        t_map = defaultdict(list)
        for pos, r in enumerate(rows, start=1):
            if not _bw_bad(r.get("product")) and not _bw_bad(r.get("brick")):
                t_map[
                    (str(r.get("product")).strip(), str(r.get("brick")).strip())
                ].append((r.get("idx") or pos, r))

        for key, lst in p_map.items():
            if key not in t_map:
                for x in lst:
                    add(
                        f"MISSING: File mein product '{key[0]}' brick '{key[1]}' qty {x['qty']:g} hai, table mein nahi."
                    )
        for key, lst in t_map.items():
            if key not in p_map:
                for no, _r in lst:
                    add(
                        f"Row {no}: Product '{key[0]}' brick '{key[1]}' table mein hai, file mein nahi mila."
                    )

        for key in set(p_map) & set(t_map):
            plist = sorted(p_map[key], key=lambda x: x["qty"] or 0)
            tlist = sorted(t_map[key], key=lambda x: _bw_num(x[1].get("sale_qty")) or 0)
            if len(plist) != len(tlist):
                add(
                    f"Count mismatch: '{key[0]}' / '{key[1]}' file mein {len(plist)} baar, table mein {len(tlist)} baar."
                )
            for x, (no, r) in zip(plist, tlist):
                tq, tp = _bw_num(r.get("sale_qty")), _bw_num(r.get("product_price"))
                if (
                    x["qty"] is not None
                    and tq is not None
                    and abs(x["qty"] - tq) > _BW_TOL
                ):
                    add(
                        f"Row {no}: Qty galat — file mein {x['qty']:g}, table mein {tq:g} ({key[0]} / {key[1]})."
                    )
                if (
                    x["price"] is not None
                    and tp is not None
                    and abs(x["price"] - tp) > _BW_TOL
                ):
                    add(
                        f"Row {no}: Price galat — file mein {x['price']:g}, table mein {tp:g} ({key[0]} / {key[1]})."
                    )

        if parsed_nonzero != len(rows):
            add(
                f"Row count mismatch: file se {parsed_nonzero} rows aayi, table mein {len(rows)} (qty 0 ke baghair) rows hain."
            )

        pb = set()
        try:
            stored = json.loads(doc.get("parsed_bricks") or "[]")
        except ValueError:
            stored = []
        for b in parsed_bricks or stored:
            pb.add(
                str(b.get("name") or b.get("brick")) if isinstance(b, dict) else str(b)
            )
        parsed_brick_count = len(pb)
        matched_brick_count = len(pb & bricks)
        for b in sorted(pb - bricks):
            add(f"Brick '{b}' file mein hai, lekin table mein ek bhi row nahi.")
        if pb:
            for b in sorted(bricks - pb):
                add(f"Brick '{b}' table mein hai, lekin file se parse nahi hui.")

    errors = list(dict.fromkeys(errors))
    if len(errors) > _BW_MAX_ERRORS:
        extra = len(errors) - _BW_MAX_ERRORS
        errors = errors[:_BW_MAX_ERRORS] + [
            f"... aur {extra} errors (pehle yeh theek karein, phir dobara Validate dabayein)."
        ]
    fy = None
    if doc.get("file"):
        dates = _bw_file_dates(doc.get("file"))
        fy = _bw_fiscal_year(dates[0]) if dates else None
    return {
        "passed": not errors,
        "errors": errors,
        "fiscal_year": fy,
        "parsed_brick_count": parsed_brick_count,
        "matched_brick_count": matched_brick_count,
    }
