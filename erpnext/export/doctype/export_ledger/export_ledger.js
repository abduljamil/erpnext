// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
var balance_value = 0;
frappe.ui.form.on('Export Ledger', {




//  created a setup funtion to calculate the total
setup:function(frm){

	//set total value
	frm.compute_total_debit = function(frm,row){
		let total = 0;
		frm.doc.ledger_record.forEach(d=>{
			total = total + d.debit;
		});
		frm.set_value('total_debit',total);
		//console.log(total)
	}


	frm.compute_total_credit = function(frm,row){
		let total2 = 0;
		frm.doc.ledger_record.forEach(d=>{
			total2 = total2 + d.credit;
		});
		frm.set_value('total_credit',total2);
		//console.log(total)
	}



},
total_debit : function(frm){
	
	if(total_debit || total_credit){
		frm.set_value('difference', frm.doc.total_debit - frm.doc.total_credit);
	}

},

total_credit : function(frm){
	if(total_debit || total_credit){
		frm.set_value('difference', frm.doc.total_debit - frm.doc.total_credit);
	}

},


});


frappe.ui.form.on('Export Ledger Child', {
	


	debit : function(frm,cdt,cdn){
		let row = locals[cdt][cdn];
		frappe.model.set_value(cdt, cdn, 'debit',row.debit);
        if(row.debit){
            frappe.model.set_value(cdt, cdn, 'balance',row.debit+balance_value);
			balance_value = row.balance

			frm.compute_total_debit(frm,row);
    }  

	},
	
	credit : function(frm,cdt,cdn){
		let row = locals[cdt][cdn];
		frappe.model.set_value(cdt, cdn, 'credit',row.credit);
        if(row.credit){
            frappe.model.set_value(cdt, cdn, 'balance',balance_value-row.credit);
			balance_value = row.balance


			frm.compute_total_credit(frm,row);
    }  

	},



	// debit_in_account_currency: function(frm, cdt, cdn) {
	// 	erpnext.journal_entry.set_exchange_rate(frm, cdt, cdn);
	// 	let row = locals[cdt][cdn];
	// 	frappe.model.set_value(cdt, cdn, 'debit_in_account_currency',row.debit_in_account_currency)
	// 	if(row.debit_in_account_currency){
	// 		frappe.model.set_value(cdt, cdn, 'balance_1',row.debit_in_account_currency + balance_value)
	// 		balance_value = row.balance_1

	// 	}
	// },

	// credit_in_account_currency: function(frm, cdt, cdn) {
	// 	erpnext.journal_entry.set_exchange_rate(frm, cdt, cdn);
	// 	let row = locals[cdt][cdn];
	// 	frappe.model.set_value(cdt, cdn, 'credit_in_account_currency',row.credit_in_account_currency)
	// 	if(row.credit_in_account_currency){
	// 		frappe.model.set_value(cdt, cdn, 'balance_1',balance_value - row.credit_in_account_currency)
	// 		balance_value = row.balance_1

	// 	}
	// },
	
	// credit : function(frm){


	// },



	// balance : function(frm){


	// },






});