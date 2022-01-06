// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Distributor Order Form', {
	setup: function(frm) {
		frm.compute_total_value_sale = function(frm,row){
			// console.log(frm)
            let total = 0;
            frm.doc.order_form_items.forEach(d=>{
				// console.log(d)
                total = total + d.item_value;
            });
			if(total>0){
            frm.set_value('total_order_value',total);
        }}
    }

	
});
frappe.ui.form.on('Order Form Items',{
	
	item_qty:function(frm,cdt,cdn){
		//grab the row
		let row = locals[cdt][cdn];
		if(row.item_qty){
			frappe.model.set_value(cdt, cdn, 'item_value', row.item_qty*row.item_price);
		}
		if(row.item_value){
			frm.compute_total_value_sale(frm,row);
		}	
	},
	
	
});