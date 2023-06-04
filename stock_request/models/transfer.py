# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class Transfer(models.TransientModel):
    _name = "transfer"

    transfer_lines = fields.One2many(comodel_name='transfer.line', inverse_name='transfer_id', string='Transfer Lines')


class TransferLine(models.TransientModel):
    _name = "transfer.line"

    transfer_id = fields.Many2one(comodel_name='transfer', string='Transfer')
    stock_request_id = fields.Many2one(comodel_name='stock.request', string='request')
    stock_request_line_id = fields.Many2one(comodel_name='stock.request.line', string='request line')

    @api.model
    def _get_default_product_qty(self):
        return 1.0

    product_id = fields.Many2one(comodel_name="product.product", string="Product")
    product_qty = fields.Float(string="Quantity", default=_get_default_product_qty)
    available_qty = fields.Float(string="Available Qty")
    product_uom_id = fields.Many2one(comodel_name="uom.uom", string="Unit of Measure")
    source_location = fields.Many2one(comodel_name="stock.location", string="Source Location", store=True)
    dest_location = fields.Many2one(comodel_name="stock.location", string="Destination Location", store=True)
    company_id = fields.Many2one(comodel_name="res.company", string="Company", required=True,
                                 default=lambda self: self.env.user.company_id, )
    lot_id = fields.Many2one(string="Lot/Serial Number", comodel_name="stock.production.lot",
                             domain="[('product_id','=',product_id)]")
    tracking = fields.Selection(related='product_id.tracking')
    inventory_quantity_auto_apply = fields.Float(comodel_name="stock.quant", string="On Hand Quantity")
    request_qty = fields.Float("Requested Qty", tracking=True)
    location_id = fields.Many2one("stock.location", domain=[('usage', '=', 'internal')])
    quantity = fields.Float(string="Quantity", digits="Product Unit of Measure", default=1, required=True)
    transfer_qty = fields.Float(string="Transfer Quantity")

    def do_transfer(self):
        active_request = self.env.context.get("stock_request_id")
        self = self.sudo()
        if self.transfer_qty > 0:

            stock_warehouse_id = self.env["stock.warehouse.transfer"].search([
                ("stock_request_id", "=", self.stock_request_id.id),
                ("source_location", "=", self.location_id.id),
                ("dest_location", "=", self.dest_location.id),
            ])
            if not stock_warehouse_id:
                picking = {
                    "company_id": self.stock_request_id.company_id.id,
                    "source_location": self.location_id.id,
                    "dest_location": self.dest_location.id,
                    "stock_request_id": self.stock_request_id.id,
                    "trans_location": self.env["stock.location"]
                    .with_context(check_accesses=False)
                    .search([("usage", "=", "transit")], limit=1)
                    .id,
                }
                stock_warehouse_id = self.env['stock.warehouse.transfer'].create(picking)
            if not (self.stock_request_line_id.qty_in_transfer + self.transfer_qty > self.stock_request_line_id.qty):
                picking_qty = self.env["stock.warehouse.transfer.line"].create({
                    "transfer": stock_warehouse_id.id,
                    "product_id": self.stock_request_line_id.product_id.id,
                    "product_uom_id": self.stock_request_line_id.product_id.uom_id.id,
                    "product_qty": self.transfer_qty,
                    "request_line_id": self.stock_request_line_id.id,
                })
                print(picking_qty)
                self.transfer_qty = 0
                if stock_warehouse_id and stock_warehouse_id.lines:
                    stock_warehouse_id.action_create_picking_new()
                    stock_warehouse_id.state = 'picking'
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
