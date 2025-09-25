# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import erpnext
import frappe
from erpnext.hr.utils import get_holiday_list_for_employee
from frappe import _
from frappe.desk.form import assign_to
from frappe.model.document import Document
from frappe.utils import (add_days, cstr, flt, format_datetime, formatdate,
    get_datetime, getdate, nowdate, today, unique, get_link_to_form)

# Compatibility fix for live server
class InactiveEmployeeStatusError(frappe.ValidationError): pass

class DuplicateDeclarationError(frappe.ValidationError): pass


# Wrapper for live server Frappe 13.7.0 compatibility
from erpnext.hr.doctype.employee.employee import get_holidays_for_employee

def get_holiday_list_for_employee(employee, raise_exception=True):
    """Wrapper to mimic newer ERPNext function for older Frappe"""
    holidays = get_holidays_for_employee(employee, '2000-01-01', '2099-12-31', raise_exception=raise_exception)
    return [frappe._dict({"holiday_date": h.holiday_date, "description": h.description}) for h in holidays]

class DuplicateDeclarationError(frappe.ValidationError): pass

class EmployeeBoardingController(Document):
    '''
        Create the project and the task for the boarding process
        Assign to the concerned person and roles as per the onboarding/separation template
    '''
    def validate(self):
        validate_active_employee(self.employee)
        # remove the task if linked before submitting the form
        if self.amended_from:
            for activity in self.activities:
                activity.task = ''

    def on_submit(self):
        # create the project for the given employee onboarding
        project_name = _(self.doctype) + " : "
        if self.doctype == "Employee Onboarding":
            project_name += self.job_applicant
        else:
            project_name += self.employee

        project = frappe.get_doc({
                "doctype": "Project",
                "project_name": project_name,
                "expected_start_date": self.date_of_joining if self.doctype == "Employee Onboarding" else self.resignation_letter_date,
                "department": self.department,
                "company": self.company
            }).insert(ignore_permissions=True, ignore_mandatory=True)

        self.db_set("project", project.name)
        self.db_set("boarding_status", "Pending")
        self.reload()
        self.create_task_and_notify_user()

    def create_task_and_notify_user(self):
        # create the task for the given project and assign to the concerned person
        for activity in self.activities:
            if activity.task:
                continue

            task = frappe.get_doc({
                "doctype": "Task",
                "project": self.project,
                "subject": activity.activity_name + " : " + self.employee_name,
                "description": activity.description,
                "department": self.department,
                "company": self.company,
                "task_weight": activity.task_weight
            }).insert(ignore_permissions=True)
            activity.db_set("task", task.name)

            users = [activity.user] if activity.user else []
            if activity.role:
                user_list = frappe.db.sql_list('''
                    SELECT DISTINCT(has_role.parent)
                    FROM `tabHas Role` has_role
                    LEFT JOIN `tabUser` user
                    ON has_role.parent = user.name
                    WHERE has_role.parenttype = 'User'
                    AND user.enabled = 1
                    AND has_role.role = %s
                ''', activity.role)
                users = unique(users + user_list)

                if "Administrator" in users:
                    users.remove("Administrator")

            # assign the task the users
            if users:
                self.assign_task_to_users(task, users)

    def assign_task_to_users(self, task, users):
        for user in users:
            args = {
                'assign_to': [user],
                'doctype': task.doctype,
                'name': task.name,
                'description': task.description or task.subject,
                'notify': self.notify_users_by_email
            }
            assign_to.add(args)

    def on_cancel(self):
        # delete task project
        for task in frappe.get_all("Task", filters={"project": self.project}):
            frappe.delete_doc("Task", task.name, force=1)
        frappe.delete_doc("Project", self.project, force=1)
        self.db_set('project', '')
        for activity in self.activities:
            activity.db_set("task", "")

@frappe.whitelist()
def get_onboarding_details(parent, parenttype):
    return frappe.get_all("Employee Boarding Activity",
        fields=["activity_name", "role", "user", "required_for_employee_creation", "description", "task_weight"],
        filters={"parent": parent, "parenttype": parenttype},
        order_by= "idx")

@frappe.whitelist()
def get_boarding_status(project):
    status = 'Pending'
    if project:
        doc = frappe.get_doc('Project', project)
        if flt(doc.percent_complete) > 0.0 and flt(doc.percent_complete) < 100.0:
            status = 'In Process'
        elif flt(doc.percent_complete) == 100.0:
            status = 'Completed'
        return status

def set_employee_name(doc):
    if doc.employee and not doc.employee_name:
        doc.employee_name = frappe.db.get_value("Employee", doc.employee, "employee_name")

def update_employee(employee, details, date=None, cancel=False):
    internal_work_history = {}
    for item in details:
        fieldtype = frappe.get_meta("Employee").get_field(item.fieldname).fieldtype
        new_data = item.new if not cancel else item.current
        if fieldtype == "Date" and new_data:
            new_data = getdate(new_data)
        elif fieldtype =="Datetime" and new_data:
            new_data = get_datetime(new_data)
        setattr(employee, item.fieldname, new_data)
        if item.fieldname in ["department", "designation", "branch"]:
            internal_work_history[item.fieldname] = item.new
    if internal_work_history and not cancel:
        internal_work_history["from_date"] = date
        employee.append("internal_work_history", internal_work_history)
    return employee

@frappe.whitelist()
def get_employee_fields_label():
    fields = []
    for df in frappe.get_meta("Employee").get("fields"):
        if df.fieldname in ["salutation", "user_id", "employee_number", "employment_type",
            "holiday_list", "branch", "department", "designation", "grade",
            "notice_number_of_days", "reports_to", "leave_policy", "company_email"]:
                fields.append({"value": df.fieldname, "label": df.label})
    return fields

@frappe.whitelist()
def get_employee_field_property(employee, fieldname):
    if employee and fieldname:
        field = frappe.get_meta("Employee").get_field(fieldname)
        value = frappe.db.get_value("Employee", employee, fieldname)
        options = field.options
        if field.fieldtype == "Date":
            value = formatdate(value)
        elif field.fieldtype == "Datetime":
            value = format_datetime(value)
        return {
            "value" : value,
            "datatype" : field.fieldtype,
            "label" : field.label,
            "options" : options
        }
    else:
        return False

def validate_active_employee(employee):
    if frappe.db.get_value("Employee", employee, "status") == "Inactive":
        frappe.throw(_("Transactions cannot be created for an Inactive Employee {0}.").format(
            get_link_to_form("Employee", employee)), InactiveEmployeeStatusError)

