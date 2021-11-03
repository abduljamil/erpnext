// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Sale Achieve Report"] = {
	"filters": [
		{
            "fieldname":"manager_name",
            "label": __("Manager Name"),
            "fieldtype": "Data",
			"width":100,
			"reqd":0
        },
		{
            "fieldname":"from",
            "label": __("From Date"),
            "fieldtype": "Date",
			"width":80,
			"reqd":0,
			default:dateutil.year_start()

        },
		{
            "fieldname":"to",
            "label": __("To Date"),
            "fieldtype": "Date",
			"width":80,
			"reqd":0,
			default:dateutil.year_end()
        },
		{
            "fieldname":"medicine_name",
            "label": __("Medicine Name"),
            "fieldtype": "Data",
			"width":100,
			"reqd":0
        },
	]
};
