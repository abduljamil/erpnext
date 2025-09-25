frappe.query_reports["Team Wise Sales Report"] = {
    "filters": [
        {
            "fieldname": "from_date",
            "label": __("From Date"),
            "fieldtype": "Date",
            "reqd": 1
        },
        {
            "fieldname": "to_date",
            "label": __("To Date"),
            "fieldtype": "Date",
            "reqd": 1
        }
    ],

    onload: function(report) {
        // Show chart
        report.page.add_inner_button(__("Generate Graph"), function() {
            if (report.chart) {
                report.chart.parent.chart_options.valuesOverPoints = 1;
                report.chart.draw(true);
                report.chart.show();
            } else {
                frappe.msgprint(__("No chart data found"));
            }
        });

        // Print chart + table with values
        report.page.add_inner_button(__("Print with Graph"), function() {
            if (!report.chart) {
                frappe.msgprint(__("No chart data found to print"));
                return;
            }

            // Serialize SVG
            let serializer = new XMLSerializer();
            let svgNode = report.chart.svg;
            let svgString = serializer.serializeToString(svgNode);

            let canvas = document.createElement("canvas");
            let ctx = canvas.getContext("2d");
            let DOMURL = self.URL || self.webkitURL || window;

            let img = new Image();
            let svgBlob = new Blob([svgString], {type: "image/svg+xml;charset=utf-8"});
            let url = DOMURL.createObjectURL(svgBlob);

            img.onload = function() {
                canvas.width = img.width;
                canvas.height = img.height;
                ctx.drawImage(img, 0, 0);

                // Draw values over each point
                let datasets = report.chart.data.datasets;
                let labels = report.chart.data.labels;
                let chart_width = canvas.width;
                let chart_height = canvas.height;

                let padding = 40; // approx padding
                let maxVal = Math.max(...[].concat(...datasets.map(ds => ds.values)));

                datasets.forEach((ds, dsIndex) => {
                    ds.values.forEach((v, i) => {
                        let x = padding + (i / (labels.length - 1)) * (chart_width - 2*padding);
                        let y = chart_height - padding - (v / maxVal) * (chart_height - 2*padding);
                        ctx.fillStyle = dsIndex === 0 ? "#1E90FF" : "#28a745";
                        ctx.font = "bold 14px Arial";
                        ctx.textAlign = "center";
                        ctx.fillText(v.toFixed(0), x, y - 5);
                    });
                });

                let imgURL = canvas.toDataURL("image/png");
                DOMURL.revokeObjectURL(url);

                // Build table
                let tableHTML = '<table><thead><tr>';
                report.columns.forEach(col => {
                    tableHTML += `<th>${col.label}</th>`;
                });
                tableHTML += '</tr></thead><tbody>';

                report.data.forEach(row => {
                    tableHTML += '<tr>';
                    report.columns.forEach(col => {
                        let val = row[col.fieldname] || '';
                        tableHTML += `<td>${val}</td>`;
                    });
                    tableHTML += '</tr>';
                });
                tableHTML += '</tbody></table>';

                // Open print window
                let win = window.open("");
                win.document.write(`
                    <html>
                    <head>
                        <title>Team Wise Sales Report</title>
                        <style>
                            body { font-family: Arial, sans-serif; padding: 20px; }
                            table { border-collapse: collapse; width: 100%; margin-top: 20px; }
                            th, td { border: 1px solid #ccc; padding: 8px; text-align: left; }
                        </style>
                    </head>
                    <body>
                        <h2>Team Wise Sales Report</h2>
                        <img src="${imgURL}" style="max-width:100%; margin-bottom:20px;"/>
                        ${tableHTML}
                    </body>
                    </html>
                `);
                win.document.close();
                win.print();
            };
            img.src = url;
        });
    }
};
