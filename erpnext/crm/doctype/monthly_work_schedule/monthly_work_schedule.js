// Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Monthly Work Schedule', {
	from_date: function(frm) {
			// for get last date
	var depreciation_start_date = moment(frm.doc.from_date).endOf('month').format('DD-MM-YYYY');
	frm.set_value('to_date',depreciation_start_date);
	
	// for get day of selected month
	// var a = new Date(cur_frm.doc.from_date);
	// var child = cur_frm.add_child("work_schedule_detail");


	// if( (a.getHours()>= 8 && a.getMinutes() >= 30) && (a.getHours()<= 10 && a.getMinutes() <= 30) ){
	// 	// cur_frm.set_value("session","First Session")
	// 	frappe.model.set_value(child.doctype, child.name, "day", "First Session")
	// } else if ( a.getHours()>= 11 && a.getHours()<= 14 ){
	// 	// cur_frm.set_value("session","Second Session")
	// 	frappe.model.set_value(child.doctype, child.name, "day", "Second Session")
		
	// } else if ( a.getHours()>= 15 && a.getHours()<= 17  ){
	// 	// cur_frm.set_value("session","Third Session")
	// 	frappe.model.set_value(child.doctype, child.name, "day", "Third Session")
	// }
	
	}
});
