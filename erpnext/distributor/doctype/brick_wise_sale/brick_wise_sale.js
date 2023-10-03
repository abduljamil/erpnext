// Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
let info=[];
function parse_data_into_child(info){
	var len = info.length;
	// cur_dialog.hide()
	// i = 0,j = array.length; i < j; i += chunk
	for (index = 0; index < len; index++) {
		let element = info[index];
		var child = cur_frm.add_child("selling_product");
	if(index == len){
		cur_dialog.hide()
	}
		for (let j = 0; j < element.length; j++) {
			let nested_element = element[j];
			// setTimeout((j)=>{
			switch (j) {
				case 0:
					frappe.model.set_value(child.doctype, child.name, "product", nested_element)
					break;
				case 1:
					frappe.model.set_value(child.doctype, child.name, "product_name", nested_element);
					break;
				case 2:
					frappe.model.set_value(child.doctype, child.name, "brick", nested_element);
					break;	
				case 3:
					if (nested_element.includes(',')){
						frappe.model.set_value(child.doctype, child.name, "sale_qty", parseInt(nested_element.replace(/,/g, '')))
					}else{
					frappe.model.set_value(child.doctype, child.name, "sale_qty", parseInt(nested_element))	
					}break;
				case 4:
					frappe.model.set_value(child.doctype, child.name, "brick_parent", nested_element)
					break;
				case 5:
					// console.log(parseInt(nested_element))
					frappe.model.set_value(child.doctype, child.name, "product_price",parseFloat(nested_element))
					if(child.product_price && child.sale_qty){
						frappe.model.set_value(child.doctype, child.name, "value",child.sale_qty*child.product_price)	
					}
					break;	
				default:
					break;
			}
		// }, time)
			cur_frm.refresh_field("selling_product")
		}	
	}
}
frappe.ui.form.on('Brick Wise Sale', {
    setup:function(frm){
        //set total value sale
        frm.compute_total_value_sale = function(frm,row){
			// console.log(frm)
            let total = 0;
            frm.doc.selling_product.forEach(d=>{
				// console.log(d)
                total = total + d.value;
            });
			if(total>0){
            frm.set_value('total_value',total);
        }}
		//set total stock value
		// frm.compute_total_stock_value = function(frm, row){
		// 	let total = 0;
		// 	frm.doc.selling_product.forEach(d=>{
		// 		total = total + d.total;
		// 	});
		// 	// console.log(total)
		// 	frm.set_value('total_value',total);
		// }
		
    },

	refresh: function(frm) {
        // This event occurs when the document is loaded
        if (frm.doc.fiscal_year) {
            // Get the value from the parent field
            var parentValue = frm.doc.fiscal_year;
			// console.log(parentValue)

            // Loop through the child table and set the value in each row
            $.each(frm.doc.selling_product || [], function(i, row) {
				frappe.model.set_value(row.doctype, row.name, 'fiscal_year', parentValue);
            });
        }
    },

	
	fiscal_year: function(frm) {
        // This event occurs when the document is loaded
        if (frm.doc.fiscal_year) {
            // Get the value from the parent field
            var parentValue = frm.doc.fiscal_year;
			// console.log(parentValue)

            // Loop through the child table and set the value in each row
            $.each(frm.doc.selling_product || [], function(i, row) {
				frappe.model.set_value(row.doctype, row.name, 'fiscal_year', parentValue);
            });
        }
    },



	apply_price: function(frm){

		cur_frm.clear_table("selling_product");
		if(frm.doc.item_code){
			info.map(item=>{
				if(item[0]== frm.doc.item_code){
					item[5] = frm.doc.item_price
				}
			})
			parse_data_into_child(info)
		}
	}
	,
    file:function(frm){
		cur_frm.clear_table("selling_product");
		cur_frm.refresh_fields();
		if(frm.doc.file){
			frappe.msgprint({
				title: __('File Upload Successfully.'),
				indicator: 'green',
				message: __('Now, You can click on the proceed button.')
			});			
		}
	},
    process_pdf:function(frm){
		let isCheck = false;
		cur_frm.clear_table("selling_product");
		cur_frm.refresh_fields();
		let pdf_file = frm.doc.file;
		frappe.show_progress('Reading pdf file..', 50, 100, 'Please wait');
		if(frm.doc.city){
			if(frm.doc.having_different_bricks>0){
				isCheck = true;
			}
			frappe.call({
				method: "erpnext.distributor.doctype.brick_wise_sale.brick_wise_sale.parse_pdf",
				args: {
					'pdf_file': pdf_file,
					'parse_check':isCheck,
					'parent_detail': {
						city:frm.doc.city,
						fromDate:frm.doc.from,
						toDate:frm.doc.to,
					},
				},
				callback: function (r) {
					if(r.message){
						frappe.hide_progress();
					}
					info = r.message;
					parse_data_into_child(info);
					
				}
			})
			
		}else{
			frappe.msgprint({
				title: __('Required Field'),
				indicator: 'yellow',
				message: __('Kindly mention the city name.')
			});	
		}
	
    }
});


frappe.ui.form.on('Brick Wise Sale Child',{
	
	sale_qty:function(frm,cdt,cdn){
		//grab the row
		let row = locals[cdt][cdn];
		if(row.sale_qty){
			frappe.model.set_value(cdt, cdn, 'value', row.sale_qty*row.product_price);
		}
		if(row.value){
			// console.log(row.value)
			frm.compute_total_value_sale(frm,row);
		}	
	},
	product_price:function(frm,cdt,cdn){
		let row = locals[cdt][cdn];
		if(row.sale_qty){
			frappe.model.set_value(cdt, cdn, 'value', row.sale_qty*row.product_price);
		}
		if(row.value){
			// console.log(row.value)
			frm.compute_total_value_sale(frm,row);
		}	
	}
	
});