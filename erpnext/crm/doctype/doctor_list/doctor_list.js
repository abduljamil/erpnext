// Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Doctor List', {
	before_save:function(frm){
		if(frm.doc.doctor_code){
			let check = frm.doc.doctor_code;
			var count = (check.match(/-/g) || []).length;
			if(count == 3){
				return 
			}else{
				frappe.throw({
					title:__('Error'),
					indicator:"red",
					message:__('Kindly Fill the brick,city,area and zone to proceed further.')
				})
			}
		}
	},
	brick:function(frm){
		if(frm.doc.brick){
			let check = frm.doc.brick;
			// console.log(check.match(/\b(\w)/g))
			let match =  check.match(/\b(\w)/g)
			// console.log(match.join(''))
			let brick_code = match.join('')
			frm.set_value('doctor_code',brick_code)
			console.log(frm.doc.doctor_code)
		}
	},
	city:function(frm){
		if(frm.doc.city){
			// console.log(frm.doc.city)
			let city = frm.doc.city;
			// let city_match = city.match(/\b(\w)/g);
			// let city_code = city_match.join('');
			frm.set_value('doctor_code', city+ "-" +frm.doc.doctor_code)

			console.log(frm.doc.doctor_code)
		}
	},
	area:function(frm){
		if(frm.doc.area){
			let area = frm.doc.area;
			let area_match = area.match(/\b(\w)/g)
			let area_code = area_match.join('')
			let zone_code = '';
			if(frm.doc.zone){
				let zone = frm.doc.zone;
				let zone_match = zone.match(/\b(\w)/g)
				zone_code = zone_match.join('')
			}
			if(area_code && zone_code){
				console.log(zone_code,area_code)
				frm.set_value('doctor_code',zone_code+"-"+area_code +"-"+ frm.doc.doctor_code)
			
			}
			console.log(frm.doc.doctor_code)
		}
	},

	
	
});
