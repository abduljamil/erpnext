// Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
let info = [];

// Cache: Territory name -> parent_territory, Item code -> trade_price
// Populated once per parse (parse_data_into_child), so brick_parent / product_price
// get set correctly even for rows set via script (fetch_from does NOT fire on
// programmatic frappe.model.set_value calls, only on user interaction).
function parse_data_into_child(info) {
	var len = info.length;

	// Collect the brick + product codes we're about to insert so we can
	// look up their parent territory / trade price in one shot.
	let brick_codes = new Set();
	let product_codes = new Set();
	for (let idx = 0; idx < len; idx++) {
		let el = info[idx];
		if (el[2]) brick_codes.add(el[2]); // brick sits at index 2 after name/product insert in most branches
		if (el[0]) product_codes.add(el[0]);
	}

	let territory_lookup = frappe.call({
		method: "frappe.client.get_list",
		args: {
			doctype: "Territory",
			filters: [["name", "in", Array.from(brick_codes)]],
			fields: ["name", "parent_territory"],
			limit_page_length: 0
		},
		async: false
	});

	let territory_parent_map = {};
	if (territory_lookup && territory_lookup.message) {
		territory_lookup.message.forEach(t => {
			territory_parent_map[t.name] = t.parent_territory;
		});
	}

	let item_lookup = frappe.call({
		method: "frappe.client.get_list",
		args: {
			doctype: "Item",
			filters: [["name", "in", Array.from(product_codes)]],
			fields: ["name", "trade_price"],
			limit_page_length: 0
		},
		async: false
	});

	let item_price_map = {};
	if (item_lookup && item_lookup.message) {
		item_lookup.message.forEach(i => {
			item_price_map[i.name] = i.trade_price;
		});
	}

	for (index = 0; index < len; index++) {
		let element = info[index];
		var child = cur_frm.add_child("selling_product");
		if (index == len) {
			cur_dialog.hide();
		}
		for (let j = 0; j < element.length; j++) {
			let nested_element = element[j];
			switch (j) {
				case 0:
					frappe.model.set_value(child.doctype, child.name, "product", nested_element);
					// Explicitly set price too — don't rely on fetch_from firing
					if (item_price_map.hasOwnProperty(nested_element)) {
						frappe.model.set_value(child.doctype, child.name, "product_price", item_price_map[nested_element]);
					}
					break;
				case 1:
					frappe.model.set_value(child.doctype, child.name, "product_name", nested_element);
					break;
				case 2:
					frappe.model.set_value(child.doctype, child.name, "brick", nested_element);
					// Explicitly set brick_parent — don't rely on fetch_from firing
					if (territory_parent_map.hasOwnProperty(nested_element)) {
						frappe.model.set_value(child.doctype, child.name, "brick_parent", territory_parent_map[nested_element]);
					}
					break;
				case 3:
					if (nested_element.includes(',')) {
						frappe.model.set_value(child.doctype, child.name, "sale_qty", parseInt(nested_element.replace(/,/g, '')));
					} else {
						frappe.model.set_value(child.doctype, child.name, "sale_qty", parseInt(nested_element));
					}
					break;
				case 4:
					frappe.model.set_value(child.doctype, child.name, "brick_parent", nested_element);
					break;
				case 5:
					frappe.model.set_value(child.doctype, child.name, "product_price", parseFloat(nested_element));
					if (child.product_price && child.sale_qty) {
						frappe.model.set_value(child.doctype, child.name, "value", child.sale_qty * child.product_price);
					}
					break;
				default:
					break;
			}
			cur_frm.refresh_field("selling_product");
		}
	}
}

frappe.ui.form.on('Brick Wise Sale', {
	setup: function (frm) {
		// set total value sale
		frm.compute_total_value_sale = function (frm, row) {
			let total = 0;
			frm.doc.selling_product.forEach(d => {
				total = total + d.value;
			});
			if (total) {
				frm.set_value('total_value', total);
			}
		}
	},

	calculate: function (frm) {
		frm.doc.selling_product.forEach(function (row) {
			if (row.sale_qty && row.product_price) {
				frappe.model.set_value(row.doctype, row.name, 'value', row.sale_qty * row.product_price);
			}
		});
		frm.compute_total_value_sale(frm);
	},

	refresh: function (frm) {
		// --- fiscal_year sync into child table (was previously in a separate,
		//     overwritten `refresh` key — now merged here so it actually runs) ---
		if (frm.doc.fiscal_year) {
			var parentValue = frm.doc.fiscal_year;
			$.each(frm.doc.selling_product || [], function (i, row) {
				frappe.model.set_value(row.doctype, row.name, 'fiscal_year', parentValue);
			});
		}

		// --- Validate button ---
		frm.add_custom_button(__('Validate'), function () {
			frappe.call({
				method: "erpnext.distributor.doctype.brick_wise_sale.brick_wise_sale.validate_sale",
				args: { doc: frm.doc },
				freeze: true,
				freeze_message: __('Validating...'),
				callback: function (r) {
					if (!r.message) return;
					let res = r.message;

					if (res.passed) {
						frappe.msgprint({
							title: __('Validation'),
							indicator: 'green',
							message: __('Pass — no issues found.') +
								(res.parsed_brick_count
									? ` (${res.matched_brick_count}/${res.parsed_brick_count} bricks matched)`
									: '')
						});
					} else {
						let html = '<ul style="padding-left:18px;margin:0;">' +
							res.errors.map(e => `<li style="margin-bottom:4px;">${frappe.utils.escape_html(e)}</li>`).join('') +
							'</ul>';
						frappe.msgprint({
							title: __('Validation Failed (' + res.errors.length + ' issue(s))'),
							indicator: 'red',
							message: html
						});
					}
				}
			});
		});
	},

	fiscal_year: function (frm) {
		if (frm.doc.fiscal_year) {
			var parentValue = frm.doc.fiscal_year;
			$.each(frm.doc.selling_product || [], function (i, row) {
				frappe.model.set_value(row.doctype, row.name, 'fiscal_year', parentValue);
			});
		}
	},

	apply_price: function (frm) {
		cur_frm.clear_table("selling_product");
		if (frm.doc.item_code) {
			info.map(item => {
				if (item[0] == frm.doc.item_code) {
					item[5] = frm.doc.item_price
				}
			})
			parse_data_into_child(info)
		}
	},

	file: function (frm) {
		cur_frm.clear_table("selling_product");
		cur_frm.refresh_fields();
		if (frm.doc.file) {
			frappe.msgprint({
				title: __('File Upload Successfully.'),
				indicator: 'green',
				message: __('Now, You can click on the proceed button.')
			});
		}
	},

	process_pdf: function (frm) {
		let isCheck = false;
		cur_frm.clear_table("selling_product");
		cur_frm.refresh_fields();
		let pdf_file = frm.doc.file;
		frappe.show_progress('Reading pdf file..', 50, 100, 'Please wait');
		if (frm.doc.city) {
			if (frm.doc.having_different_bricks > 0) {
				isCheck = true;
			}
			frappe.call({
				method: "erpnext.distributor.doctype.brick_wise_sale.brick_wise_sale.parse_pdf",
				args: {
					'pdf_file': pdf_file,
					'parse_check': isCheck,
					'parent_detail': {
						city: frm.doc.city,
						fromDate: frm.doc.from,
						toDate: frm.doc.to,
					},
				},
				callback: function (r) {
					if (r.message) {
						frappe.hide_progress();
					}
					// parse_pdf now returns {"result": [...], "parsed_bricks": [...]}
					// instead of a bare list — unpack both pieces here.
					let payload = r.message || {};
					info = payload.result || [];

					// Store the exact brick list this PDF produced, so Validate
					// can compare against it instead of the whole Territory tree.
					frm.set_value('parsed_bricks', JSON.stringify(payload.parsed_bricks || []));

					parse_data_into_child(info);
				}
			})
		} else {
			frappe.msgprint({
				title: __('Required Field'),
				indicator: 'yellow',
				message: __('Kindly mention the city name.')
			});
		}
	}
});

frappe.ui.form.on('Brick Wise Sale Child', {
	sale_qty: function (frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		if (row.sale_qty) {
			frappe.model.set_value(cdt, cdn, 'value', row.sale_qty * row.product_price);
		}
		if (row.value) {
			frm.compute_total_value_sale(frm, row);
		}
	},
	product_price: function (frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		if (row.sale_qty) {
			frappe.model.set_value(cdt, cdn, 'value', row.sale_qty * row.product_price);
		}
		if (row.value) {
			frm.compute_total_value_sale(frm, row);
		}
	}
});