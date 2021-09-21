// Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Sale Stock Detail', {
    setup:function(frm){
        //check duplicate item 
        frm.check_dupilcate_item = function(frm,row){
            frm.doc.selling_product.forEach(p=>{
                if(row.product== '' || row.idx ==p.idx){
                    //pass
                }else{
                    if(row.product == p.product){
                        row.product = '';
                        frappe.throw(__(`${p.product} already exists at row ${p.idx}.`));
                        frm.refresh_field('selling_product');
                    }
                }
            })
        }
        //set total value sale
        frm.compute_total_value_sale = function(frm,row){
            let total = 0;
            frm.doc.selling_product.forEach(d=>{
                total = total + d.value;
            });
            frm.set_value('total_value',total);
            //console.log(total)
        }
		//set total stock value
		frm.compute_total_stock_value = function(frm, row){
			let total = 0;
			frm.doc.selling_product.forEach(d=>{
				total = total + d.closing_value;
			});
			frm.set_value('total_stock_value',total);
		}
    },
    file:function(frm){
		cur_frm.clear_table("selling_product");
		cur_frm.refresh_fields();
		if(frm.doc.file){
			//let full_path = frappe.get_site_path('private', 'files', frm.doc.file);
			//console.log(frm.doc.file,frm.doc.city)
			frappe.msgprint({
				title: __('File Upload Successfully.'),
				indicator: 'green',
				message: __('Now, You can click on the proceed button.')
			});			
		}
	},
    process_pdf:function(frm){
		cur_frm.clear_table("selling_product");
		cur_frm.refresh_fields();
		let pdf_file = frm.doc.file;
		if(frm.doc.city){
			let dist_city = frm.doc.city;
			frappe.call({
				method: "erpnext.distributor.doctype.sale_stock_detail.sale_stock_detail.parse_pdf",
				args: {
					'pdf_file': pdf_file,
					'dist_city': dist_city,
				},
				callback: function (r) {
					var info = r.message;
					//get pdf length
                    //console.log(info)
					var len = info.length;
					for (let index = 0; index < len; index++) {
						let element = info[index];
						var child = cur_frm.add_child("selling_product");
						frappe.model.set_value(child.doctype, child.name, "code", element.id)
						frappe.model.set_value(child.doctype, child.name, "product_name", element.item)
						if(dist_city=="Bhakkar" || dist_city=="Faisalabad"){
							frappe.model.set_value(child.doctype, child.name, "trade_price", parseFloat(element.DB_trade_price))
						} else {
							frappe.model.set_value(child.doctype, child.name, "trade_price", parseFloat(element.trade_price))
						}
						frappe.model.set_value(child.doctype, child.name, "opening_stock", parseFloat(element.opening_stock))
						frappe.model.set_value(child.doctype, child.name, "purchase", parseFloat(element.purchase))
						frappe.model.set_value(child.doctype, child.name, "return", parseFloat(element.return))
						frappe.model.set_value(child.doctype, child.name, "sale", parseFloat(element.sale))
						frappe.model.set_value(child.doctype, child.name, "bonus", parseFloat(element.bonus))
						cur_frm.refresh_field("selling_product")							
					}
				}
			})
			
		}
		/**/
    }
});


frappe.ui.form.on('SSR Product Detail',{
	setup : function(frm){
		let row = locals[cdt][cdn]
		frm.pass_pdf_parse(frm,row)
	},
	product:function(frm,cdt,cdn){
		let row = locals[cdt][cdn];
		//frm.check_dupilcate_item(frm,row);
	},
	opening_stock:function(frm,cdt,cdn){
		//grab the entire row
		let row = locals[cdt][cdn];
		frappe.model.set_value(cdt, cdn, 'total', row.opening_stock+row.purchase);
		frappe.model.set_value(cdt, cdn, 'closing_stock', row.opening_stock);
	},
	purchase:function(frm,cdt,cdn){
		//grab the entire row
		let row = locals[cdt][cdn];
		frappe.model.set_value(cdt, cdn, 'total', row.opening_stock+row.purchase);
		frappe.model.set_value(cdt, cdn, 'closing_stock', row.opening_stock+row.purchase);	
	},
	return:function(frm,cdt,cdn){
		//grab the entire row
		let row = locals[cdt][cdn];
		if(!row.return){
			frappe.model.set_value(cdt,cdn,'return',0)
		}
	},
	sale:function(frm,cdt,cdn){
		//grab the row
		let row = locals[cdt][cdn];
		if(row.sale){
			frappe.model.set_value(cdt,cdn, 'value', row.sale*row.trade_price);
			frappe.model.set_value(cdt, cdn, 'closing_stock', row.total-row.return-row.sale);
		}
		if(row.value){
			frm.compute_total_value_sale(frm,row);
		}	
	},
	bonus:function(frm,cdt,cdn){
		//grab the entire row
		let row = locals[cdt][cdn];
		frappe.model.set_value(cdt,cdn,'closing_stock',row.total-row.return-row.sale-row.bonus);
	},
	closing_stock:function(frm,cdt,cdn){
		let row = locals[cdt][cdn];
		frappe.model.set_value(cdt,cdn, 'closing_value', row.closing_stock*row.trade_price);
		if(row.closing_value){
			frm.compute_total_stock_value(frm,row);
		}
		
	}
	
});