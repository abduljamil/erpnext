// Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
function transposingArray(info,len){
	// console.log(info,len)
	var newArray = [];
    for(var i = 0; i < info.length; i++){
        newArray.push([]);
    };

    for(var i = 0; i < info.length; i++){
        for(var j = 0; j < len; j++){
            newArray[j].push(info[i][j]);
        };
    };

    console.log(newArray);
}
frappe.ui.form.on('Brick Wise Sale', {
    setup:function(frm){
        //check duplicate item 
        // frm.check_dupilcate_item = function(frm,row){
        //     frm.doc.selling_product.forEach(p=>{
        //         if(row.product== '' || row.idx ==p.idx){
        //             //pass
        //         }else{
        //             if(row.product == p.product){
        //                 row.product = '';
        //                 frappe.throw(__(`${p.product} already exists at row ${p.idx}.`));
        //                 frm.refresh_field('selling_product');
        //             }
        //         }
        //     })
        // }
        //set total value sale
        frm.compute_total_value_sale = function(frm,row){
			// console.log(frm)
            let total = 0;
            frm.doc.selling_product.forEach(d=>{
				// console.log(d)
                total = total + d.value;
            });
			if(total>0){
            console.log(total)
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
				method: "erpnext.distributor.doctype.brick_wise_sale.brick_wise_sale.parse_pdf",
				args: {
					'pdf_file': pdf_file,
					'dist_city': dist_city,
				},
				callback: function (r) {
					var info = r.message;
					//get pdf length
                    console.log(info)
					// if(!info){
					// 	frappe.show_progress('Loading',25,50,75,100,'Please Wait until the data load')
					// }
					var len = info.length;
					// let newArr = transposingArray(info,len)
					for (let index = 0; index < len; index++) {
						let element = info[index];
					var child = cur_frm.add_child("selling_product");
					// console.log(element)
					// if(element[0]=='PRODUCT NAME PACK'){
						var sum= 0
						for (let j = 0; j < element.length; j++) {
							let nested_element = element[j];
							// console.log(element[j])
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
							cur_frm.refresh_field("selling_product")
						}
												
					}
					
				}
			})
			
		}else{
			frappe.msgprint({
				title: __('Required Field'),
				indicator: 'yellow',
				message: __('Kindly mention the city name.')
			});	
		}
		/**/
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
	
	
});