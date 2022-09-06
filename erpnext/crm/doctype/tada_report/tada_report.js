// Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('TADA Report', {

//  created a setup funtion to calculate the total
    setup:function(frm){

//set total value
frm.compute_total = function(frm,row){
    let total = 0;
    frm.doc.expense_report.forEach(d=>{
        total = total + d.amount;
    });
    frm.set_value('total_expenses',total);
    //console.log(total)
}
    
// //to set grand total value
// frm.grand_total = function(frm){
//     let g_total = 0;
//     // frm.doc.expense_report.forEach(d=>{
//         g_total = postage + stationery + telephone + fright + tool_tax + parking + misc_1 + misc_2 + misc_3 + misc_4 + misc_5 + misc_6 + total_expenses;
//     // });
//     frm.set_value('grand_total',g_total);
//     //console.log(total)
// }
    


},  

    

	
	from_date: function(frm) {
        cur_frm.clear_table("expense_report");
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
                    if(a.getDay()!==7){
                        var weekDays = ['Sunday', 'Monday','Tuesday','Wednesday','Thursday','Friday','Saturday'];
                        var child = cur_frm.add_child("expense_report");
                        frappe.model.set_value(child.doctype, child.name, "day", weekDays[a.getDay()]);
                        // check if area is enter then also default set the area town
                        // if(frm.doc.area){
                        //     frappe.model.set_value(child.doctype, child.name, "os_from", frm.doc.area);
                        // }
                        cur_frm.refresh_field("expense_report")
                    }
                }
            }

		}
	},
	

  // For Grand Total of all expense
  postage : function(frm){
  
   if(frm.doc.postage || frm.doc.stationery || frm.doc.telephone || frm.doc.fright || frm.doc.tool_tax || frm.doc.parking || frm.doc.misc_1 || frm.doc.misc_2 || frm.doc.misc_3 || frm.doc.misc_4 || frm.doc.misc_5 || frm.doc.misc_6  || frm.doc.total_expenses){
                
    frm.set_value('grand_total', frm.doc.postage + frm.doc.stationery + frm.doc.telephone + frm.doc.fright + frm.doc.tool_tax + frm.doc.parking + frm.doc.misc_1 + frm.doc.misc_2 + frm.doc.misc_3 + frm.doc.misc_4 + frm.doc.misc_5 +  frm.doc.misc_6 + frm.doc.total_expenses) ;
}






},
stationery:function(frm){
    if(frm.doc.postage || frm.doc.stationery || frm.doc.telephone || frm.doc.fright || frm.doc.tool_tax || frm.doc.parking || frm.doc.misc_1 || frm.doc.misc_2 || frm.doc.misc_3 || frm.doc.misc_4 || frm.doc.misc_5 || frm.doc.misc_6 || frm.doc.total_expenses){          
        frm.set_value('grand_total', frm.doc.postage + frm.doc.stationery + frm.doc.telephone + frm.doc.fright + frm.doc.tool_tax + frm.doc.parking + frm.doc.misc_1 + frm.doc.misc_2 + frm.doc.misc_3 + frm.doc.misc_4 + frm.doc.misc_5 +  frm.doc.misc_6 + frm.doc.total_expenses) ;    
    }



},
telephone:function(frm){

    if(frm.doc.postage || frm.doc.stationery || frm.doc.telephone || frm.doc.fright || frm.doc.tool_tax || frm.doc.parking || frm.doc.misc_1 || frm.doc.misc_2 || frm.doc.misc_3 || frm.doc.misc_4 || frm.doc.misc_5 || frm.doc.misc_6 || frm.doc.total_expenses){          
        frm.set_value('grand_total', frm.doc.postage + frm.doc.stationery + frm.doc.telephone + frm.doc.fright + frm.doc.tool_tax + frm.doc.parking + frm.doc.misc_1 + frm.doc.misc_2 + frm.doc.misc_3 + frm.doc.misc_4 + frm.doc.misc_5 +  frm.doc.misc_6 + frm.doc.total_expenses) ;    
    }



},

fright:function(frm){

    
    if(frm.doc.postage || frm.doc.stationery || frm.doc.telephone || frm.doc.fright || frm.doc.tool_tax || frm.doc.parking || frm.doc.misc_1 || frm.doc.misc_2 || frm.doc.misc_3 || frm.doc.misc_4 || frm.doc.misc_5 || frm.doc.misc_6 || frm.doc.total_expenses){          
        frm.set_value('grand_total', frm.doc.postage + frm.doc.stationery + frm.doc.telephone + frm.doc.fright + frm.doc.tool_tax + frm.doc.parking + frm.doc.misc_1 + frm.doc.misc_2 + frm.doc.misc_3 + frm.doc.misc_4 + frm.doc.misc_5 +  frm.doc.misc_6 + frm.doc.total_expenses) ;    
    }



},

tool_tax:function(frm){
   
   
    if(frm.doc.postage || frm.doc.stationery || frm.doc.telephone || frm.doc.fright || frm.doc.tool_tax || frm.doc.parking || frm.doc.misc_1 || frm.doc.misc_2 || frm.doc.misc_3 || frm.doc.misc_4 || frm.doc.misc_5 || frm.doc.misc_6 || frm.doc.total_expenses){          
        frm.set_value('grand_total', frm.doc.postage + frm.doc.stationery + frm.doc.telephone + frm.doc.fright + frm.doc.tool_tax + frm.doc.parking + frm.doc.misc_1 + frm.doc.misc_2 + frm.doc.misc_3 + frm.doc.misc_4 + frm.doc.misc_5 +  frm.doc.misc_6 + frm.doc.total_expenses) ;    
    }

    
},
    
    parking:function(frm){
 
      
        if(frm.doc.postage || frm.doc.stationery || frm.doc.telephone || frm.doc.fright || frm.doc.tool_tax || frm.doc.parking || frm.doc.misc_1 || frm.doc.misc_2 || frm.doc.misc_3 || frm.doc.misc_4 || frm.doc.misc_5 || frm.doc.misc_6 || frm.doc.total_expenses){          
            frm.set_value('grand_total', frm.doc.postage + frm.doc.stationery + frm.doc.telephone + frm.doc.fright + frm.doc.tool_tax + frm.doc.parking + frm.doc.misc_1 + frm.doc.misc_2 + frm.doc.misc_3 + frm.doc.misc_4 + frm.doc.misc_5 +  frm.doc.misc_6 + frm.doc.total_expenses) ;        
        }
    
       
        
    },



    misc_1:function(frm){
    
        
        if(frm.doc.postage || frm.doc.stationery || frm.doc.telephone || frm.doc.fright || frm.doc.tool_tax || frm.doc.parking || frm.doc.misc_1 || frm.doc.misc_2 || frm.doc.misc_3 || frm.doc.misc_4 || frm.doc.misc_5 || frm.doc.misc_6 || frm.doc.total_expenses){          
            frm.set_value('grand_total', frm.doc.postage + frm.doc.stationery + frm.doc.telephone + frm.doc.fright + frm.doc.tool_tax + frm.doc.parking + frm.doc.misc_1 + frm.doc.misc_2 + frm.doc.misc_3 + frm.doc.misc_4 + frm.doc.misc_5 +  frm.doc.misc_6 + frm.doc.total_expenses) ;        
        }
    
        

    },

        
    misc_2:function(frm){
    
      
        if(frm.doc.postage || frm.doc.stationery || frm.doc.telephone || frm.doc.fright || frm.doc.tool_tax || frm.doc.parking || frm.doc.misc_1 || frm.doc.misc_2 || frm.doc.misc_3 || frm.doc.misc_4 || frm.doc.misc_5 || frm.doc.misc_6 || frm.doc.total_expenses){          
            frm.set_value('grand_total', frm.doc.postage + frm.doc.stationery + frm.doc.telephone + frm.doc.fright + frm.doc.tool_tax + frm.doc.parking + frm.doc.misc_1 + frm.doc.misc_2 + frm.doc.misc_3 + frm.doc.misc_4 + frm.doc.misc_5 +  frm.doc.misc_6 + frm.doc.total_expenses) ;        
        }
    
       
        
    },

        
        misc_3:function(frm){
  
            
            if(frm.doc.postage || frm.doc.stationery || frm.doc.telephone || frm.doc.fright || frm.doc.tool_tax || frm.doc.parking || frm.doc.misc_1 || frm.doc.misc_2 || frm.doc.misc_3 || frm.doc.misc_4 || frm.doc.misc_5 || frm.doc.misc_6 || frm.doc.total_expenses){          
                frm.set_value('grand_total', frm.doc.postage + frm.doc.stationery + frm.doc.telephone + frm.doc.fright + frm.doc.tool_tax + frm.doc.parking + frm.doc.misc_1 + frm.doc.misc_2 + frm.doc.misc_3 + frm.doc.misc_4 + frm.doc.misc_5 +  frm.doc.misc_6 + frm.doc.total_expenses) ;            
            }
        
           
            
        },

        
        misc_4:function(frm){
    
       
            if(frm.doc.postage || frm.doc.stationery || frm.doc.telephone || frm.doc.fright || frm.doc.tool_tax || frm.doc.parking || frm.doc.misc_1 || frm.doc.misc_2 || frm.doc.misc_3 || frm.doc.misc_4 || frm.doc.misc_5 || frm.doc.misc_6 || frm.doc.total_expenses){          
                frm.set_value('grand_total', frm.doc.postage + frm.doc.stationery + frm.doc.telephone + frm.doc.fright + frm.doc.tool_tax + frm.doc.parking + frm.doc.misc_1 + frm.doc.misc_2 + frm.doc.misc_3 + frm.doc.misc_4 + frm.doc.misc_5 +  frm.doc.misc_6 + frm.doc.total_expenses) ;            
            }
        
        
    },

        
        misc_5:function(frm){
    
             
            if(frm.doc.postage || frm.doc.stationery || frm.doc.telephone || frm.doc.fright || frm.doc.tool_tax || frm.doc.parking || frm.doc.misc_1 || frm.doc.misc_2 || frm.doc.misc_3 || frm.doc.misc_4 || frm.doc.misc_5 || frm.doc.misc_6 || frm.doc.total_expenses){          
                frm.set_value('grand_total', frm.doc.postage + frm.doc.stationery + frm.doc.telephone + frm.doc.fright + frm.doc.tool_tax + frm.doc.parking + frm.doc.misc_1 + frm.doc.misc_2 + frm.doc.misc_3 + frm.doc.misc_4 + frm.doc.misc_5 +  frm.doc.misc_6 + frm.doc.total_expenses) ;            
            }
           
        },

        
        misc_6:function(frm){
            
            if(frm.doc.postage || frm.doc.stationery || frm.doc.telephone || frm.doc.fright || frm.doc.tool_tax || frm.doc.parking || frm.doc.misc_1 || frm.doc.misc_2 || frm.doc.misc_3 || frm.doc.misc_4 || frm.doc.misc_5 || frm.doc.misc_6 || frm.doc.total_expenses){          
                frm.set_value('grand_total', frm.doc.postage + frm.doc.stationery + frm.doc.telephone + frm.doc.fright + frm.doc.tool_tax + frm.doc.parking + frm.doc.misc_1 + frm.doc.misc_2 + frm.doc.misc_3 + frm.doc.misc_4 + frm.doc.misc_5 +  frm.doc.misc_6 + frm.doc.total_expenses) ;            
            }
                
            
        },
        
        
        // console.log(frm.doc.postage , frm.doc.stationery , frm.doc.telephone , frm.doc.fright , frm.doc.tool_tax , frm.doc.parking , frm.doc.misc_1 , frm.doc.misc_2 , frm.doc.misc_3 , frm.doc.misc_4 , frm.doc.misc_5 , frm.doc.misc_6)



        local_sale:function(frm){
            
            if(frm.doc.local_sale || frm.doc.out_station_sale){
                
                frm.set_value('total_sale', frm.doc.local_sale + frm.doc.out_station_sale) ;
                
            }
                
            
        },
        
        
        out_station_sale:function(frm){
            
            if(frm.doc.local_sale || frm.doc.out_station_sale){
                
                frm.set_value('total_sale', frm.doc.local_sale + frm.doc.out_station_sale) ;
                
            }
                
            
        },



    total_expenses:function(frm){

        if(frm.doc.local_sale || frm.doc.out_station_sale){
                
            frm.set_value('total_sale', frm.doc.local_sale + frm.doc.out_station_sale) ;
            
        }

    }
    
    
    



});


frappe.ui.form.on('TADA Report Child', {


    // To Calculate the total of Expense Report 
	da : function(frm,cdt,cdn){
		let row = locals[cdt][cdn];
		frappe.model.set_value(cdt, cdn, 'da',row.da);
        if(row.da || row.dt || row.ns || row.km || row.fare){
            frappe.model.set_value(cdt, cdn, 'amount',row.da+row.dt+row.ns+row.km+row.fare);
    }  
    },
	dt:function(frm,cdt,cdn){
		let row = locals[cdt][cdn];
		frappe.model.set_value(cdt, cdn, 'dt',row.dt);
        if(row.da || row.dt || row.ns || row.km || row.fare){
            frappe.model.set_value(cdt, cdn, 'amount',row.da+row.dt+row.ns+row.km+row.fare);
    }  
    },
	ns:function(frm,cdt,cdn){
		let row = locals[cdt][cdn];
		frappe.model.set_value(cdt, cdn, 'ns',row.ns);
        if(row.da || row.dt || row.ns || row.km || row.fare){
            frappe.model.set_value(cdt, cdn, 'amount',row.da+row.dt+row.ns+row.km+row.fare);
    }  
    },

	km:function(frm,cdt,cdn){
		
		let row = locals[cdt][cdn];
		frappe.model.set_value(cdt, cdn, 'km',row.km);
        if(row.da || row.dt || row.ns || row.km || row.fare){
            frappe.model.set_value(cdt, cdn, 'amount',row.da+row.dt+row.ns+row.km+row.fare);
    }  
	},

	fare:function(frm,cdt,cdn){
		
		let row = locals[cdt][cdn];
		frappe.model.set_value(cdt, cdn, 'fare',row.fare);
		//  console.log(row.da, row.dt, row.ns, row.km, row.fare)
         if(row.da || row.dt || row.ns || row.km || row.fare){
             frappe.model.set_value(cdt, cdn, 'amount',row.da+row.dt+row.ns+row.km+row.fare);
            }  
        },
        
        amount:function(frm,cdt,cdn){
            
            let row = locals[cdt][cdn];
            frappe.model.set_value(cdt, cdn, 'amount',row.amount);
            //  console.log(row.da, row.dt, row.ns, row.km, row.fare)
            if(row.amount){
            //  console.log(row.amount)
                frm.compute_total(frm,row);
            }
        },
    
      
    
    
});
