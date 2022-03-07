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
from erpnext.accounts.utils import get_fiscal_year
from erpnext.controllers.trends import get_period_date_ranges, get_period_month_ranges

from erpnext.selling.report.sales_partner_target_variance_based_on_item_group.item_group_wise_sales_target_variance import get_data_column

def execute(filters=None):
	if not filters: filters = {}

	columns = get_columns(filters)
	period_month_ranges = get_period_month_ranges(filters["period"], filters["fiscal_year"])
	territory_item_group_dict = get_territory_item_month_map(filters)
	# print(territory_item_group_dict)
	item_list = get_item_groups()
	data = []
	for territory, territory_items in territory_item_group_dict.items():
		for item_group, monthwise_data in territory_items.items():
			# print(item_list[item_group])
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

	return columns, sorted(data, key=lambda x: (x[0], x[1]))
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

	# print(filter_digit, " filter")
	# print(contains_digit, " contain")

	if not filter_digit:
		contains_digit = False
		values ={'territory':""}

	if contains_digit:
		## get territory list 
		print('im in if')
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
	# 	item_details=""
		print('im in else')
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
	# print(item_groups)
	territory_item_group_dict = {}

	check_territory = {}
	user = frappe.session.user
	## get user full name from db
	users = frappe.db.get_value("User", user, ["full_name"], as_dict=True)
	## get all employee record
	employee_list = frappe.db.get_list("Employee",fields=['name','employee_name','Territory'])
	
	tt_list = frappe.db.get_list("Territory",fields=['name','parent_territory'])
	# print(tt_list)
	full_name = users.full_name
	# print(full_name)
	## find specific login employee record
	login_user = ''
	area = ''
	for e in employee_list:
		if e.get('employee_name') == full_name:
			login_user = e
	##check filters and set territory
	if filters.get('territory'):
		print(filters.get('territory'))
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
	# print(check_territory)
	
	for td in territory_details:
		if td.parent_territory == check_territory.get(td.parent_territory) or td.name==check_territory.get(td.name):
			# if check_territory == td.parent_territory:
			# print(td)
			if filters.get('territory'):
				for k in list(check_territory.keys()):
					print(check_territory[k])
					if re.findall("[0-9]", check_territory[k]):
						del check_territory[k]
			print(check_territory)
			achieved_details = get_achieved_details(filters, td.name, item_groups)
			# print(achieved_details)
			item_actual_details = {}
			
			for d in achieved_details:
				if td.item_group == d.product:
					# print(td.item_group)
					item_group = item_groups[d.product]
					# print(item_group)
					item_actual_details.setdefault(td.item_group, frappe._dict())\
						.setdefault(d.month_name, frappe._dict({
							"quantity": 0,
							"amount": 0
						}))

					value_dict = item_actual_details[td.item_group][d.month_name]
					value_dict.quantity += flt(d.sale_qty)
					value_dict.amount += flt(d.value)
			# print(td)
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

				# print("target",target_achieved.target)
				target_achieved.achieved = item_actual_details.get(td.item_group, {}).get(month, {})\
					.get(filters["target_on"].lower())
				# print("acheive", target_achieved.achieved)
			# print(territory_item_group_dict)
		elif full_name=='Administrator' or full_name=='Sh Abdul Rauf' or full_name=='Zafar Hameed Paracha':
			achieved_details = get_achieved_details(filters, td.name, item_groups)
			print(achieved_details)
			item_actual_details = {}
			
			for d in achieved_details:
				if td.item_group == d.product:
					# print(td.item_group)
					item_group = item_groups[d.product]
					# print(item_group)
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

				# print("target",target_achieved.target)
				target_achieved.achieved = item_actual_details.get(td.item_group, {}).get(month, {})\
					.get(filters["target_on"].lower())
			
	return territory_item_group_dict

def get_item_groups():
	return dict(frappe.get_all("Item", fields=["name","item_name"], as_list=1))

def get_territory_dict():
	return dict(frappe.get_all("Territory",fields=["name","parent_territory"],as_list=1))