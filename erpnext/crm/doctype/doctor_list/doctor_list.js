// Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

function build_doctor_code(frm) {
	let brick_code = frm.doc.brick ? (frm.doc.brick.match(/\b(\w)/g) || []).join('') : '';
	let city = frm.doc.city || '';
	let area_code = frm.doc.area ? (frm.doc.area.match(/\b(\w)/g) || []).join('') : '';
	let zone_code = frm.doc.zone ? (frm.doc.zone.match(/\b(\w)/g) || []).join('') : '';

	let parts = [zone_code, area_code, city, brick_code].filter(Boolean);
	frm.set_value('doctor_code', parts.join('-'));
}

frappe.ui.form.on('Doctor List', {
	before_save: function(frm) {
		if (!frm.doc.brick || !frm.doc.city || !frm.doc.area || !frm.doc.zone) {
			frappe.throw({
				title: __('Error'),
				indicator: "red",
				message: __('Kindly Fill the brick, city, area and zone to proceed further.')
			});
		}
	},

	brick: function(frm) {
		if (!frm.doc.brick) {
			frm.set_value('city', '');
			frm.set_value('area', '');
			frm.set_value('zone', '');
			build_doctor_code(frm);
			return;
		}

		frappe.call({
			method: 'get_territory_hierarchy',
			args: { territory: frm.doc.brick },
			callback: function(r) {
				if (r.message) {
					frm.set_value('city', r.message.city || '');
					frm.set_value('area', r.message.area || '');
					frm.set_value('zone', r.message.zone || '');
				}
				build_doctor_code(frm);
			}
		});
	},

	city: function(frm) {
		build_doctor_code(frm);
	},

	area: function(frm) {
		build_doctor_code(frm);
	},

	zone: function(frm) {
		build_doctor_code(frm);
	}
});
