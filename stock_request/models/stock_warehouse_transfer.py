from odoo import models, fields


class StockWarehouseTransfer(models.Model):
    _inherit = "stock.warehouse.transfer"

    stock_request_id = fields.Many2one(
        "stock.request", "Stock Request", index=True, copy=True
    )

    def get_picking_vals(self):
        picking_vals = super(StockWarehouseTransfer, self).get_picking_vals()
        picking_vals.update({
            "stock_request_id": self.stock_request_id.id
        })
        return picking_vals


class StockWarehouseTransferLine(models.Model):
    _inherit = "stock.warehouse.transfer.line"

    stock_request_id = fields.Many2one(
        "stock.request", string="Stock Request", copy=True
    )

    request_line_id = fields.Many2one(
        "stock.request.line", "QTY Request", index=True, copy=True
    )

    def get_move_vals(self, picking, group):
        move_vals = super(StockWarehouseTransferLine, self).get_move_vals(picking, group)
        move_vals.update({
            "request_line_id": self.request_line_id.id
        })
        return move_vals
