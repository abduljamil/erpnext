// Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

function strip_gt_suffix(str) {
	if (!str) return '';
	return str.replace(/[-\s]?GT$/i, '').trim();
}

// Single token abbreviation:
// - Agar token chota hai (<=4 chars) ya usme digit hai (jese NWS, SKR1, PSW1, PSW) -> as-is rakho (ye already codes hain)
// - Warna (jese BANDHI, Sukkur, Larkana) -> vowels hata kar pehle 2 letters lo
function smart_abbr(token) {
	let upper = token.toUpperCase();
	if (upper.length <= 4 || /\d/.test(upper)) {
		return upper;
	}
	let first = upper.charAt(0);
	let rest = upper.slice(1).replace(/[AEIOU]/g, '');
	return (first + rest).substring(0, 2);
}

function build_code_part(str) {
	let cleaned = strip_gt_suffix(str);
	if (!cleaned) return '';
	let tokens = cleaned.split(/[-\s]+/).filter(Boolean);
	if (tokens.length > 1) {
		// Multi-word: har word ka pehla letter
		return tokens.map(t => t.charAt(0).toUpperCase()).join('');
	}
	return smart_abbr(tokens[0]);
}

function build_doctor_code(frm) {
	let zone_code = build_code_part(frm.doc.zone);
	let area_code = build_code_part(frm.doc.area);
	let city_code = build_code_part(frm.doc.city);
	let parent_brick_code = build_code_part(frm.doc.parent_brick);
	let brick_code = build_code_part(frm.doc.brick);

	let parts = [zone_code, area_code, city_code, parent_brick_code, brick_code].filter(Boolean);
	let code = parts.join('-');

	let is_green_team = frm.doc.brick && frm.doc.brick.toUpperCase().includes('GT');
	if (is_green_team) {
		code = 'GTP-' + code;
	}

	frm.set_value('doctor_code', code);
}

function get_parent_territory(territory) {
	return new Promise((resolve) => {
		frappe.call({
			method: 'erpnext.crm.doctype.doctor_list.doctor_list.get_parent_territory_direct',
			args: { territory: territory },
			callback: function (r) {
				console.log('parent of', territory, '=>', r.message);
				resolve(r.message || '');
			}
		});
	});
}

async function build_hierarchy(brick) {
	let ancestors = [];
	let zone = '';
	let area = '';
	let current = brick;
	let safety = 0;

	while (safety < 10) {
		safety++;
		let parent = await get_parent_territory(current);
		if (!parent) break;

		let lower = parent.toLowerCase();

		if (lower.includes('zone')) {
			zone = parent;
			break;
		}

		if (lower.includes('area')) {
			area = parent;
			current = parent;
			continue;
		}

		ancestors.push(parent);
		current = parent;
	}

	console.log('FINAL ancestors:', ancestors, 'area:', area, 'zone:', zone);

	let parent_brick = '';
	let city = '';

	if (ancestors.length >= 2) {
		parent_brick = ancestors[0];
		city = ancestors[1];
	} else if (ancestors.length === 1) {
		city = ancestors[0];
	}

	return { city, area, zone, parent_brick };
}

frappe.ui.form.on('Doctor List', {
	onload: function (frm) {
		frm.toggle_display('parent_brick', !!frm.doc.parent_brick);
	},

	before_save: function (frm) {
		if (!frm.doc.brick || !frm.doc.city || !frm.doc.area || !frm.doc.zone) {
			frappe.throw({
				title: __('Error'),
				indicator: "red",
				message: __('Kindly Fill the brick, city, area and zone to proceed further.')
			});
		}
	},

	brick: async function (frm) {
		frm.set_value('city', '');
		frm.set_value('area', '');
		frm.set_value('zone', '');
		frm.set_value('parent_brick', '');
		frm.toggle_display('parent_brick', false);
		build_doctor_code(frm);

		if (!frm.doc.brick) {
			return;
		}

		let result = await build_hierarchy(frm.doc.brick);

		frm.set_value('city', result.city || '');
		frm.set_value('area', result.area || '');
		frm.set_value('zone', result.zone || '');
		frm.set_value('parent_brick', result.parent_brick || '');
		frm.toggle_display('parent_brick', !!result.parent_brick);

		build_doctor_code(frm);
	},

	city: function (frm) {
		build_doctor_code(frm);
	},

	area: function (frm) {
		build_doctor_code(frm);
	},

	zone: function (frm) {
		build_doctor_code(frm);
	}
});