# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class DoctorList(Document):
    pass


@frappe.whitelist()
def get_Territory():
    territory_list = frappe.db.get_all(
        "Territory",
        fields=["territory_name", "brick_name", "parent_territory"],
        as_list=True,
    )
    return territory_list


@frappe.whitelist()
def get_parent_territory_direct(territory):
    return frappe.db.get_value("Territory", territory, "parent_territory")
