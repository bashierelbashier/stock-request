from odoo import models, fields, api
import base64
import io

class StockRequestXLS(models.AbstractModel):
    _name = "report.stock_request.report_stock_request_excel_report_xls"
    _inherit = "report.report_xlsx.abstract"

    def add_company_header(self, row, sheet, workbook, company, bold):
        if company.logo:
            image_data = io.BytesIO(base64.b64decode(company.logo))
            row += 1

        company_cell_format = workbook.add_format({
            'bold': True,
            'border': 1,
            'border_color': 'black',
            'align': 'right',
            'valign': 'vcenter',
            'font_size': 16,
        })
        company_name = company.name[:50]
        company_logo_cell = 'B3:D6'

        sheet.merge_range(company_logo_cell, company_name, company_cell_format)
        sheet.insert_image('B3', 'download.png', {'image_data': image_data, 'x_scale': 0.2, 'y_scale': 0.2})
        sheet.conditional_format(company_logo_cell, {'type': 'no_blanks', 'format': company_cell_format})

        sheet.set_column('B3:D3', 20)

    def generate_xlsx_report(self, workbook, data, report):
        sheet = workbook.add_worksheet("Stock Request Report")
        table_border = workbook.add_format({'border': 1})
        table_header = workbook.add_format({'bold': True, 'border': 1})
        bold = workbook.add_format({'bold': True})
        company = self.env.company
        row = self.add_company_header(0, sheet, workbook, company, bold)
        table_data = [['Order Ref', report.name],
                      ['Requested Date', report.date_quotation.strftime("%Y-%m-%d")],
                      ['Destination Location', report.location_dest_id.name],
                      ['Responsible', report.user_id.name],
                      ]
        row = 2

        for data_row in table_data:
            sheet.write(row, 7, data_row[0], table_header)
            sheet.write(row, 8, data_row[1], table_border)
            row += 1

        sheet.set_column(7, 7, 20)
        sheet.set_column(8, 8, 20)

        data_rows = []
        for line in report.lines:
            data_rows.append([
                line.product_id.barcode,
                line.product_id.name,
                line.request_qty,
                line.qty,
                line.qty_in_transfer,
                line.transferred_qty,
                line.purchased_qty,
                line.available_qty
            ])

        headers = ["Product Barcode", "Product", "Requested Qty", "Approved Qty", "Qty in Transfer", "Transferred Quantity",
                   "Purchased Quantity", "Available Qty"]
        header_format = workbook.add_format(
            {'align': 'center', 'valign': 'vcenter', 'font_size': 10, 'bold': True, 'border': 1, 'font_color': 'black'})
        header_format.set_bottom(2)
        for col, header in enumerate(headers):
            sheet.write(8, col+1, header, header_format)

        regular_format = workbook.add_format(
            {'align': 'center', 'valign': 'vcenter', 'font_size': 10, 'num_format': '#,##0.00', 'border': 1,
             'font_color': 'black'})
        regular_format.set_border(1)

        for row_num, data_row in enumerate(data_rows):
            for col_num, cell_value in enumerate(data_row):
                sheet.write(row_num + 9, col_num+1, cell_value, regular_format)

        signature_format = workbook.add_format(
            {'align': 'center', 'valign': 'vcenter', 'font_size': 10, 'border': 1})
        sheet.merge_range('B' + str(row_num + 12) + ':C' + str(row_num + 13), '', signature_format)





