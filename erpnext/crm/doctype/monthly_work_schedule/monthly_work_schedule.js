// Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
function addDays(days) {
    var date = new Date(this.valueOf());
    date.setDate(date.getDate() + days);
    return date;
}
frappe.ui.form.on('Monthly Work Schedule', {
	from_date: function(frm) {
		cur_frm.clear_table("work_schedule_detail");
			// for get last date
		var depreciation_start_date = moment(frm.doc.from_date).endOf('month').format('YYYY-MM-DD');
		frm.set_value('to_date',depreciation_start_date);
		//check to date exists
		if(frm.doc.to_date){
			//get date array which contain all the date between the from and to date
			var dateArray = new Array();
			var stopDate = new Date(frm.doc.to_date).getDate();
			var currentDate = new Date(frm.doc.from_date).getDate();
			while (currentDate <= stopDate) {

				var tomorrow = new Date(frm.doc.from_date);
				tomorrow.setDate(currentDate);
				dateArray.push(tomorrow);
				currentDate = currentDate+1
			}
			if(dateArray!=[]){
				//map the date array 
				for (let index = 0; index < dateArray.length; index++) {
					let element = dateArray[index];
					//get day by date
					var a = new Date(element);
					if(a.getDay()!==0){
						var weekDays = ['Sunday', 'Monday','Tuesday','Wednesday','Thursday','Friday','Saturday'];
						var child = cur_frm.add_child("work_schedule_detail");
						frappe.model.set_value(child.doctype, child.name, "day", weekDays[a.getDay()]);
						// check if area is enter then also default set the area town 
						if(frm.doc.area){
							frappe.model.set_value(child.doctype, child.name, "area_town", frm.doc.area);
						}
						cur_frm.refresh_field("work_schedule_detail")
					}
					
				}
			}
		}
	
	}
});
