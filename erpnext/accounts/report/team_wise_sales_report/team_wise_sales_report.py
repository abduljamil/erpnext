import frappe
from frappe import _

def execute(filters=None):
    if not filters:
        filters = {}

    from_date = filters.get("from_date")
    to_date = filters.get("to_date")

    # Columns
    columns = [
        {"label": _("Month"), "fieldname": "month", "fieldtype": "Data", "width": 120},
        {"label": _("Blue Sales"), "fieldname": "blue_sales", "fieldtype": "Currency", "width": 150},
        {"label": _("Green Sales"), "fieldname": "green_sales", "fieldtype": "Currency", "width": 150},
        {"label": _("Total Sales"), "fieldname": "total_sales", "fieldtype": "Currency", "width": 150},
    ]

    # Data
    data = frappe.db.sql(
        """
        SELECT
            DATE_FORMAT(DATE(si.posting_date - INTERVAL DAY(si.posting_date)-1 DAY), '%%M %%y') AS month,
            SUM(CASE WHEN isplit.team = 'Blue'
                     THEN (isplit.team_amount / isplit.invoice_total_items) * si.base_grand_total
                     ELSE 0 END) AS blue_sales,
            SUM(CASE WHEN isplit.team = 'Green'
                     THEN (isplit.team_amount / isplit.invoice_total_items) * si.base_grand_total
                     ELSE 0 END) AS green_sales,
            SUM(si.base_grand_total) AS total_sales
        FROM `tabSales Invoice` si
        JOIN `tabCustomer` c ON si.customer = c.name
        JOIN (
            SELECT
                sii.parent AS sales_invoice,
                itm.belong_to AS team,
                SUM(sii.base_amount) AS team_amount,
                SUM(SUM(sii.base_amount)) OVER (PARTITION BY sii.parent) AS invoice_total_items
            FROM `tabSales Invoice Item` sii
            LEFT JOIN `tabItem` itm ON sii.item_code = itm.name
            GROUP BY sii.parent, itm.belong_to
        ) AS isplit ON si.name = isplit.sales_invoice
        WHERE si.docstatus = 1
          AND c.customer_group = 'Local'
          AND si.posting_date BETWEEN %(from_date)s AND %(to_date)s
        GROUP BY YEAR(si.posting_date), MONTH(si.posting_date)

        UNION ALL

        SELECT
            'Grand Total' AS month,
            SUM(CASE WHEN isplit.team = 'Blue'
                     THEN (isplit.team_amount / isplit.invoice_total_items) * si.base_grand_total
                     ELSE 0 END) AS blue_sales,
            SUM(CASE WHEN isplit.team = 'Green'
                     THEN (isplit.team_amount / isplit.invoice_total_items) * si.base_grand_total
                     ELSE 0 END) AS green_sales,
            SUM(si.base_grand_total) AS total_sales
        FROM `tabSales Invoice` si
        JOIN `tabCustomer` c ON si.customer = c.name
        JOIN (
            SELECT
                sii.parent AS sales_invoice,
                itm.belong_to AS team,
                SUM(sii.base_amount) AS team_amount,
                SUM(SUM(sii.base_amount)) OVER (PARTITION BY sii.parent) AS invoice_total_items
            FROM `tabSales Invoice Item` sii
            LEFT JOIN `tabItem` itm ON sii.item_code = itm.name
            GROUP BY sii.parent, itm.belong_to
        ) AS isplit ON si.name = isplit.sales_invoice
        WHERE si.docstatus = 1
          AND c.customer_group = 'Local'
          AND si.posting_date BETWEEN %(from_date)s AND %(to_date)s
        """,
        {"from_date": from_date, "to_date": to_date},
        as_dict=True,
    )

    # Chart data
    chart_data = {
        "data": {
            "labels": [d["month"] for d in data if d["month"] != "Grand Total"],
            "datasets": [
                {
                    "name": "Blue Sales",
                    "values": [float(d["blue_sales"] or 0) for d in data if d["month"] != "Grand Total"],
                },
                {
                    "name": "Green Sales",
                    "values": [float(d["green_sales"] or 0) for d in data if d["month"] != "Grand Total"],
                },
            ],
        },
        "type": "line",
        "colors": ["#1E90FF", "#28a745"],
        "valuesOverPoints": 1,  # show values on graph points
    }

    return columns, data, None, chart_data

