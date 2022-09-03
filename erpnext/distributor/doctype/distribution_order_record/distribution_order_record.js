// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Distribution Order Record', {
	// refresh: function(frm) {

	// }
});



frappe.ui.form.on('Distribution Order Record Child', {
	// refresh: function(frm) {

	// }
	quantity:function(frm,cdt,cdn){
		let row = locals[cdt][cdn];
		frappe.model.set_value(cdt, cdn,'quantity',row.quantity);
		if(row.quantity || row.amount){
			frappe.model.set_value(cdt, cdn,'total', row.quantity*row.amount);

		}


	},

	amount:function(frm,cdt,cdn){
		let row = locals[cdt][cdn];
		a = [];
		frappe.model.set_value(cdt, cdn,'a',row.quantity);
		if(row.quantity || row.amount){
			frappe.model.set_value(cdt, cdn,'total', row.quantity*row.amount);

		}


	},
	



});
