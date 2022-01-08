# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
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
	data = []
	for territory, territory_items in territory_item_group_dict.items():
		for item_group, monthwise_data in territory_items.items():
			row = [territory, item_group]
			totals = [0, 0, 0]
			for relevant_months in period_month_ranges:
				period_data = [0, 0, 0]
				for month in relevant_months:
					month_data = monthwise_data.get(month, {})
					for i, fieldname in enumerate(["target", "achieved", "variance"]):
						value = flt(month_data.get(fieldname))
						period_data[i] += value
						totals[i] += value
				period_data[2] = period_data[0] - period_data[1]
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
		for label in [_("Target") +" (%s)", _("Achieved") + " (%s)", _("Variance") + " (%s)"]:
			if group_months:
				label = label % (_(from_date.strftime("%b")) + " - " + _(to_date.strftime("%b")))
			else:
				label = label % _(from_date.strftime("%b"))
			columns.append(label+":Float:120")

	return columns + [_("Total Target") + ":Float:120", _("Total Achieved") + ":Float:120",
		_("Total Variance") + ":Float:120"]

#Get territory & item group details
def get_territory_details(filters):
	return frappe.db.sql("""
		select
			t.name, td.item_group, td.target_qty, td.target_amount, td.distribution_id
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
	start_date, end_date = get_fiscal_year(fiscal_year = filters["fiscal_year"])[1:]
	print(territory)

	# lft, rgt = frappe.db.get_value("Territory", territory, ["lft", "rgt"])
	# print(lft,rgt)
	if territory == 'LHR2':
		item_details = frappe.db.sql("""
		select bwc.product, bwc.product_name, bwc.sale_qty,bwc.value, 
			MONTHNAME(bw.to) as month_name from `tabBrick Wise Sale` bw, 
			`tabBrick Wise Sale Child` bwc
		where bwc.parent=bw.name and bw.city='Lahore' and bwc.brick_parent='LHR2'
		""", as_dict=1)
		return item_details
	elif territory =="Lahore":
	# 	item_details=""
		item_details = frappe.db.sql("""
			select bwc.product, bwc.product_name, bwc.sale_qty,bwc.value, 
				MONTHNAME(bw.to) as month_name from `tabBrick Wise Sale` bw, 
				`tabBrick Wise Sale Child` bwc
			where bwc.parent=bw.name and bw.city='Lahore'
			""", as_dict=1)
	
		return item_details
	elif territory =="Sheikhupura":
		item_details = frappe.db.sql("""
			select bwc.product, bwc.product_name, bwc.sale_qty,bwc.value, 
				MONTHNAME(bw.to) as month_name from `tabBrick Wise Sale` bw, 
				`tabBrick Wise Sale Child` bwc
			where bwc.parent=bw.name and bw.city='Sheikhupura'
			""", as_dict=1)
	
		return item_details
	elif territory =='Kasur':
		item_details = frappe.db.sql("""
			select bwc.product, bwc.product_name, bwc.sale_qty,bwc.value, 
				MONTHNAME(bw.to) as month_name from `tabBrick Wise Sale` bw, 
				`tabBrick Wise Sale Child` bwc
			where bwc.parent=bw.name and bw.city='Kasur'
			""", as_dict=1)
	
		return item_details
	elif territory =='Sahiwal':
		item_details = frappe.db.sql("""
			select bwc.product, bwc.product_name, bwc.sale_qty,bwc.value, 
				MONTHNAME(bw.to) as month_name from `tabBrick Wise Sale` bw, 
				`tabBrick Wise Sale Child` bwc
			where bwc.parent=bw.name and bw.city='Sahiwal'
			""", as_dict=1)
	
		return item_details
	elif territory =='Okara':
		item_details = frappe.db.sql("""
			select bwc.product, bwc.product_name, bwc.sale_qty,bwc.value, 
				MONTHNAME(bw.to) as month_name from `tabBrick Wise Sale` bw, 
				`tabBrick Wise Sale Child` bwc
			where bwc.parent=bw.name and bw.city='Okara'
			""", as_dict=1)
	
		return item_details
	elif territory =='Sialkot':
		item_details = frappe.db.sql("""
			select bwc.product, bwc.product_name, bwc.sale_qty,bwc.value, 
				MONTHNAME(bw.to) as month_name from `tabBrick Wise Sale` bw, 
				`tabBrick Wise Sale Child` bwc
			where bwc.parent=bw.name and bw.city='Sialkot'
			""", as_dict=1)
	
		return item_details
	elif territory =='Narowal':
		item_details = frappe.db.sql("""
			select bwc.product, bwc.product_name, bwc.sale_qty,bwc.value, 
				MONTHNAME(bw.to) as month_name from `tabBrick Wise Sale` bw, 
				`tabBrick Wise Sale Child` bwc
			where bwc.parent=bw.name and bw.city='Narowal'
			""", as_dict=1)
	
		return item_details
	elif territory =='Gujranwala':
		item_details = frappe.db.sql("""
			select bwc.product, bwc.product_name, bwc.sale_qty,bwc.value, 
				MONTHNAME(bw.to) as month_name from `tabBrick Wise Sale` bw, 
				`tabBrick Wise Sale Child` bwc
			where bwc.parent=bw.name and bw.city='Gujranwala'
			""", as_dict=1)
	
		return item_details
	elif territory =='Gujrat':
		item_details = frappe.db.sql("""
			select bwc.product, bwc.product_name, bwc.sale_qty,bwc.value, 
				MONTHNAME(bw.to) as month_name from `tabBrick Wise Sale` bw, 
				`tabBrick Wise Sale Child` bwc
			where bwc.parent=bw.name and bw.city='Gujrat'
			""", as_dict=1)
	
		return item_details
	elif territory =='Mandi Bahauddin':
		item_details = frappe.db.sql("""
			select bwc.product, bwc.product_name, bwc.sale_qty,bwc.value, 
				MONTHNAME(bw.to) as month_name from `tabBrick Wise Sale` bw, 
				`tabBrick Wise Sale Child` bwc
			where bwc.parent=bw.name and bw.city='Mandi Bahauddin'
			""", as_dict=1)
	
		return item_details


def get_territory_item_month_map(filters):
	import datetime
	territory_details = get_territory_details(filters)
	print(territory_details)
	print(frappe.session.user)
	tdd = get_target_distribution_details(filters)
	# print(tdd)
	item_groups = get_item_groups()
	# print(item_groups)
	territory_item_group_dict = {}

	for td in territory_details:
		achieved_details = get_achieved_details(filters, td.name, item_groups)
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
		# print(item_actual_details)
		# print(achieved_details)
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

			print("target",target_achieved.target)
			target_achieved.achieved = item_actual_details.get(td.item_group, {}).get(month, {})\
				.get(filters["target_on"].lower())
			print("acheive", target_achieved.achieved)
		print(territory_item_group_dict)
	return territory_item_group_dict

def get_item_groups():
	return dict(frappe.get_all("Item", fields=["name", "item_group"], as_list=1))