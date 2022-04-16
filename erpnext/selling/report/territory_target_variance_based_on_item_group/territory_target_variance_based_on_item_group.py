# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
from dataclasses import fields
from operator import contains
import re
from tabnanny import check
from numpy import full
import frappe
from frappe import _, msgprint
from frappe.utils import flt
import copy
from erpnext.accounts.utils import get_fiscal_year
from erpnext.controllers.trends import get_period_date_ranges, get_period_month_ranges

from erpnext.selling.report.sales_partner_target_variance_based_on_item_group.item_group_wise_sales_target_variance import get_data_column

def execute(filters=None):
	if not filters: filters = {}

	columns = get_columns(filters)
	period_month_ranges = get_period_month_ranges(filters["period"], filters["fiscal_year"])
	territory_item_group_dict = get_territory_item_month_map(filters)
	# print(territory_item_group_dict)
	copy_data = copy.deepcopy(territory_item_group_dict)
	total_area_target_achieved = {}
	if filters.get('territory'):
		for k, v in copy_data.items():  # data is the original data dict
			for ik, iv in v.items():
				temp = total_area_target_achieved.get(ik, {})
				if not temp:
					total_area_target_achieved[ik] = iv
				else:
					for tk, tv in temp.items():
						for itk, itv in tv.items():
							if (temp[tk][itk] is None):
								temp[tk][itk] = 0.00
							temp[tk][itk] += float(0 if iv[tk][itk] is None else iv[tk][itk])
	net_total = {}
	filter_value = filters.get('territory')
	net_total[filter_value] = total_area_target_achieved
	# ** operator for packing and unpacking items in order
	final_dict = {**net_total, **territory_item_group_dict}
	item_list = get_item_groups()
	data = []
	for territory, territory_items in final_dict.items():
		for item_group, monthwise_data in territory_items.items():
			name = item_list[item_group]
			row = [territory, name]
			totals = [0, 0, 0]
			for relevant_months in period_month_ranges:
				period_data = [0, 0, 0]
				for month in relevant_months:
					month_data = monthwise_data.get(month, {})
					for i, fieldname in enumerate(["target", "achieved", "variance"]):
						value = flt(month_data.get(fieldname))
						period_data[i] += round(value)
						totals[i] += round(value)
				period_data[2] = round(period_data[0]) - round(period_data[1])
				row += period_data
			totals[2] = totals[0] - totals[1]
			row += totals
			data.append(row)
	return columns, data
	# return columns, sorted(data, key=lambda x: (x[0], x[1]))
def get_columns(filters):
	for fieldname in ["fiscal_year", "period", "target_on"]:
		if not filters.get(fieldname):
			label = (" ".join(fieldname.split("_"))).title()
			msgprint(_("Please specify") + ": " + label, raise_exception=True)

	columns = [_("Territory") + ":Link/Territory:120", _("Item Group") + ":Link/Item Group:120"]

	group_months = False if filters["period"] == "Monthly" else True

	for from_date, to_date in get_period_date_ranges(filters["period"], filters["fiscal_year"]):
		for label in [_("Tgt") +" (%s)", _("Ach") + " (%s)", _("Var") + " (%s)"]:
			if group_months:
				label = label % (_(from_date.strftime("%b")) + " - " + _(to_date.strftime("%b")))
			else:
				label = label % _(from_date.strftime("%b"))
			columns.append(label+":Int:90")

	return columns + [_("Target") + ":Int:100", _("Achievement") + ":Int:100",
		_("Variance") + ":Int:100"]

#Get territory & item group details
def get_territory_details(filters):
	return frappe.db.sql("""
		select
			t.name,t.territory_manager,t.parent_territory ,td.item_group, td.target_qty, td.target_amount, td.distribution_id
		from
			`tabTerritory` t, `tabTarget Detail` td
		where
			td.parent=t.name and td.fiscal_year=%s order by t.name
		""", (filters["fiscal_year"]), as_dict=1)

#Get target distribution details of item group
def get_target_distribution_details(filters):
	target_details = {}

	for d in frappe.db.sql("""
		select
			md.name, mdp.month, mdp.percentage_allocation
		from
			`tabMonthly Distribution Percentage` mdp, `tabMonthly Distribution` md
		where
			mdp.parent=md.name and md.fiscal_year=%s
		""", (filters["fiscal_year"]), as_dict=1):
			target_details.setdefault(d.name, {}).setdefault(d.month, flt(d.percentage_allocation))

	return target_details

#Get achieved details from sales order
def get_achieved_details(filters, territory, item_groups):
	# start_date, end_date = get_fiscal_year(fiscal_year = filters["fiscal_year"])[1:]
	values = {'territory':territory}
	contains_digit = any(map(str.isdigit, territory))
	filter_digit = ''
	if filters.get('territory'):
		filter_digit = bool(re.search(r'\d', filters.get('territory')))


	if not filter_digit:
		contains_digit = False

	if contains_digit:
		tt_list = get_territory_dict()
		parent_brick = tt_list.get(territory)
		nested_values = { 'parent_brick':parent_brick , 'territory':territory}
		item_details = frappe.db.sql("""
		select bwc.product, bwc.product_name, bwc.sale_qty,bwc.value, 
			MONTHNAME(bw.to) as month_name from `tabBrick Wise Sale` bw, 
			`tabBrick Wise Sale Child` bwc
		where bwc.parent=bw.name and bw.city=%(parent_brick)s and bwc.brick_parent=%(territory)s
		""",values = nested_values ,as_dict=1)
		return item_details
	else:
		item_details = frappe.db.sql("""
			select bwc.product, bwc.product_name, bwc.sale_qty,bwc.value, 
				MONTHNAME(bw.to) as month_name from `tabBrick Wise Sale` bw, 
				`tabBrick Wise Sale Child` bwc
			where bwc.parent=bw.name and bw.city= %(territory)s
			""",values = values ,as_dict=1)
		return item_details
	


def get_territory_item_month_map(filters):
	import datetime
	territory_details = get_territory_details(filters)
	tdd = get_target_distribution_details(filters)
	item_groups = get_item_groups()
	territory_item_group_dict = {}

	check_territory = {}
	user = frappe.session.user
	## get user full name from db
	users = frappe.db.get_value("User", user, ["full_name"], as_dict=True)
	## get all employee record
	employee_list = frappe.db.get_list("Employee",fields=['name','employee_name','Territory','employee_team_'])
	
	tt_list = frappe.db.get_list("Territory",fields=['name','parent_territory'])
	
	full_name = users.full_name
	## find specific login employee record
	login_user = ''
	area = ''
	for e in employee_list:
		if e.get('employee_name') == full_name:
			login_user = e
	## team wise items 
	if login_user.get('employee_team_'):
		team_wise_items = frappe.db.get_list('Item',
								filters={
									'belong_to': login_user.get('employee_team_')
								},
								fields=['item_code', 'item_name','belong_to'],
								as_list=True
							)
	##check filters and set territory
	if filters.get('territory'):
		login_user['Territory'] = filters.get('territory')
	## get all area that login user can access
	if login_user:
		area = login_user.get('Territory')
		check_territory[area] = area
	## find respective territory under all area 
	for territory  in tt_list:
		if area == territory['parent_territory']:
			for tt in tt_list:
				if territory['name'] == tt['parent_territory']:
					name = tt['name']
					check_territory[name] = name
	for td in territory_details:
		if td.parent_territory == check_territory.get(td.parent_territory) or td.name==check_territory.get(td.name):
			if filters.get('territory'):
				for k in list(check_territory.keys()):
					if re.findall("[0-9]", check_territory[k]):
						del check_territory[k]
			achieved_details = get_achieved_details(filters, td.name, item_groups)
			## get index list 
			item_actual_details = {}
			for d in achieved_details:
				if td.item_group == d.product:
					item_group = item_groups[d.product]
					item_actual_details.setdefault(td.item_group, frappe._dict())\
						.setdefault(d.month_name, frappe._dict({
							"quantity": 0,
							"amount": 0
						}))

					value_dict = item_actual_details[td.item_group][d.month_name]
					value_dict.quantity += flt(d.sale_qty)
					value_dict.amount += flt(d.value)
			for month_id in range(1, 13):
				for team in team_wise_items:
					if team[0] == td.item_group:
						month = datetime.date(2013, month_id, 1).strftime('%B')
						territory_item_group_dict.setdefault(td.name, {}).setdefault(td.item_group, {})\
							.setdefault(month, frappe._dict({
								"target": 0.0, "achieved": 0.0
							}))

						target_achieved = territory_item_group_dict[td.name][td.item_group][month]
						month_percentage = tdd.get(td.distribution_id, {}).get(month, 0) \
							if td.distribution_id else 100.0/12


						if (filters["target_on"] == "Quantity"):
							target_achieved.target = flt(td.target_qty) * month_percentage / 100
						else:
							target_achieved.target = flt(td.target_amount) * month_percentage / 100

						target_achieved.achieved = item_actual_details.get(td.item_group, {}).get(month, {})\
							.get(filters["target_on"].lower())
			
		elif full_name=='Administrator':
			achieved_details = get_achieved_details(filters, td.name, item_groups)
			item_actual_details = {}
			
			for d in achieved_details:
				if td.item_group == d.product:
					item_group = item_groups[d.product]
					item_actual_details.setdefault(td.item_group, frappe._dict())\
						.setdefault(d.month_name, frappe._dict({
							"quantity": 0,
							"amount": 0
						}))

					value_dict = item_actual_details[td.item_group][d.month_name]
					value_dict.quantity += flt(d.sale_qty)
					value_dict.amount += flt(d.value)
			for month_id in range(1, 13):
				month = datetime.date(2013, month_id, 1).strftime('%B')
				territory_item_group_dict.setdefault(td.name, {}).setdefault(td.item_group, {})\
					.setdefault(month, frappe._dict({
						"target": 0.0, "achieved": 0.0
					}))

				target_achieved = territory_item_group_dict[td.name][td.item_group][month]
				month_percentage = tdd.get(td.distribution_id, {}).get(month, 0) \
					if td.distribution_id else 100.0/12


				if (filters["target_on"] == "Quantity"):
					target_achieved.target = flt(td.target_qty) * month_percentage / 100
				else:
					target_achieved.target = flt(td.target_amount) * month_percentage / 100

				target_achieved.achieved = item_actual_details.get(td.item_group, {}).get(month, {})\
					.get(filters["target_on"].lower())
		
	return territory_item_group_dict
	
def get_item_groups():
	return dict(frappe.get_all("Item", fields=["name","item_name"], as_list=1))

def get_territory_dict():
	return dict(frappe.get_all("Territory",fields=["name","parent_territory"],as_list=1))