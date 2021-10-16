# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt
from __future__ import unicode_literals

from frappe import _,msgprint
import frappe


def execute(filters=None):
	return get_columns(), get_data(filters)

def get_data(filters):
    ##date range
    _from, to = filters.get('from'), filters.get('to')
    ##conditions
    conditions = " AND 1=1 "
    if(filters.get('manager_name')):conditions += f" AND manager_name LIKE '%{filters.get('manager_name')}' "
    if(filters.get('medicine_name')):conditions += f" AND medicine_name LIKE '%{filters.get('medicine_name')}' "
    
    data = frappe.db.sql("""SELECT A.manager_name,A.from,A.to,B.medicine_code,
        B.medicine_name,B.target,B.achieve,B.percentage FROM `tabSet Field Target` as A 
        INNER JOIN `tabRSM Target Child` AS B;""",as_dict=True)
    return data    
    # where docstatus<2 %s order by posting_date, name desc"""%
	# 	conditions, filters, as_dict=1)


def get_columns():
    return[
        "Manager Name:Data:150",
        "From:Date:100",
        "To:Date:100",
        "Medicine Code:Link/Item:100",
        "Medicine Name:Data:150",
        "Target:Int:100",
        "Achieve:Int:100",
        "Percentage:Percent:100"

    ]