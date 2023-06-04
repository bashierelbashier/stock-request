# -*- coding: utf-8 -*-

from odoo import models, fields, _


class ProductQuantity(models.TransientModel):
    _name = "product.quantity"

    quant_id = fields.Many2many(
        "stock.quant", string="Location", compute="_compute_stock_quant_ids"
    )


class StockQuant(models.Model):
    _inherit = "stock.quant"

    transfer_qty = fields.Float(string="Transfer Quantity")

    def do_transfer(self):
        active_request = self.env.context.get("stock_request_id")
        obj = self.env["stock.request"].browse(active_request)
        self = self.sudo()
        if self.transfer_qty > 0:

            picking_id = self.env["stock.warehouse.transfer"].search(
                [
                    ("stock_request_id", "=", obj.id),
                    ("state", "=", "draft"),
                    ("source_location", "=", self.location_id.id),
                    ("dest_location", "=", obj.location_dest_id.id),
                ]
            )
            if not picking_id:
                picking = {
                    "company_id": obj.company_id.id,
                    "source_location": self.location_id.id,
                    "dest_location": obj.location_dest_id.id,
                    "stock_request_id": obj.id,
                    "trans_location": self.env["stock.location"]
                    .with_context(check_accesses=False)
                    .search([("usage", "=", "transit")], limit=1)
                    .id,
                }
                picking_id = self.env["stock.warehouse.transfer"].create(picking)
            line_id = [x.id for x in obj.lines if x.product_id == self.product_id]
            request_line_id = self.env["stock.request.line"].sudo().browse(line_id[0])
            if not (
                request_line_id.qty_in_transfer + self.transfer_qty
                > request_line_id.qty
            ):
                self.env["stock.warehouse.transfer.line"].create(
                    {
                        "transfer": picking_id.id,
                        "product_id": self.product_id.id,
                        "product_uom_id": self.product_id.uom_id.id,
                        "product_qty": self.transfer_qty,
                        "request_line_id": line_id[0],
                    }
                )
                self.transfer_qty = 0
                return {
                    "type": "ir.actions.client",
                    "tag": "display_notification",
                    "params": {
                        "type": "info",
                        "sticky": False,
                        "message": _("Transfer Created Successfully"),
                    },
                }
            else:
                return {
                    "type": "ir.actions.client",
                    "tag": "display_notification",
                    "params": {
                        "type": "warning",
                        "sticky": False,
                        "message": _(
                            "Cannot create transfer with quantity greater than approved!"
                        ),
                    },
                }
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "type": "warning",
                "sticky": False,
                "message": _("Cannot create transfer with quantity 0!"),
            },
        }

    # return {
    #     'name': 'Product Avilable Quantity',
    #     'view_mode': 'tree',
    #     'view_id': self.env.ref('stock_request.stock_quant_quantity_view').id,
    #     'res_model': 'stock.quant',
    #     'type': 'ir.actions.act_window',
    #     'target': 'new',
    #     'domain': [("product_id","=",self.product_id.id),("location_id","!=",obj.location_dest_id.id)],
    #     'context': {'search_default_internal_loc': 1,'stock_request_id':obj.id}
    # }
