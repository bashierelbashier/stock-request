# -*- coding: utf-8 -*-
#################################################################################
# Author      : Plus Tech.
# Copyright(c): 2021-Present TechPlus IT Solutions.
# All Rights Reserved.
#
#
# This program is copyright property of the author mentioned above.
# You can`t redistribute it and/or modify it.
#
#
# You should have received a copy of the License along with this program.
# If not, see <www.plustech.com/license>
#################################################################################

{
    "name": "Stock Request",
    "summary": "Internal request for stock",
    "version": "14.0.2.0",
    "license": "LGPL-3",
    "website": "www.plustech.com",
    "author": "Plus Tech",
    "category": "Warehouse Management",
    "depends": [
        "stock",
        "purchase",
        "hr",
        "stock_warehouse_transfer",
        "report_xlsx",
    ],
    "data": [
        "security/stock_request_security.xml",
        "security/ir.model.access.csv",
        "views/stock_request_reports.xml",
        "views/stock_request_views.xml",
        "views/res_config_settings_views.xml",
        "views/stock_request_menu.xml",
        # "views/transfer.xml",
        "data/stock_request_sequence_data.xml",
        "wizard/pending_orders_wizard_view.xml",
        "wizard/product_quantity.xml",
        "wizard/product_transfer_quantity.xml",
        "wizard/purchase_wizard.xml",
        "report/print_pdf_report.xml",
        "report/stock_request_pdf_report.xml",
    ],
    "installable": True,
}
