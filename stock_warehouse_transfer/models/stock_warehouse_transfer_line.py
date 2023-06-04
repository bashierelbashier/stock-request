import logging

from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class StockWarehouseTransferLine(models.Model):
    _name = "stock.warehouse.transfer.line"
    _rec_name = "product_id"

    # @api.depends('product_id','product_uom_id','source_location')
    def _get_qty_avble(self):
        for rec in self:
            if not rec.transfer.source_warehouse:
                rec.available_qty = 0
                continue
            rec1 = rec.product_id.with_context(
                {"warehouse": rec.transfer.source_warehouse.id}
            )
            res = rec1._compute_quantities_dict(
                self._context.get("lot_id"),
                self._context.get("owner_id"),
                self._context.get("package_id"),
                self._context.get("from_date"),
                self._context.get("to_date"),
            )
            if res:
                rec.available_qty = rec1.uom_id._compute_quantity(
                    (res[rec1.id]["qty_available"]), rec.product_uom_id
                )
            else:
                rec.available_qty = 0

    @api.model
    def _get_default_product_qty(self):
        return 1.0

    product_id = fields.Many2one(comodel_name="product.product", string="Product")
    product_qty = fields.Float(string="Quantity", default=_get_default_product_qty)
    available_qty = fields.Float(string="Available Qty")
    product_uom_id = fields.Many2one(comodel_name="uom.uom", string="Unit of Measure")
    transfer = fields.Many2one(
        comodel_name="stock.warehouse.transfer", string="Transfer"
    )
    note = fields.Text(string="Note")
    source_location = fields.Many2one(
        comodel_name="stock.location", string="Source Location", store=True
    )
    dest_location = fields.Many2one(
        comodel_name="stock.location", string="Destination Location", store=True
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.user.company_id,
    )

    @api.onchange("product_id")
    def product_id_change(self):
        for rec in self:
            if rec.product_id:
                rec.product_uom_id = (
                    rec.product_id.uom_id and self.product_id.uom_id.id or False
                )
                self._get_qty_avble()
            else:
                rec.product_uom_id = False

    @api.model
    def default_get(self, fields):
        res = super(StockWarehouseTransferLine, self).default_get(fields)
        # get manager user id
        source_location = self.env.context.get("source_location")
        # dest_location = self.env.context.get('dest_location')
        if source_location:
            res.update({"source_location": source_location})
        # if dest_location:
        #     res.update({'dest_location': dest_location})
        return res

    @api.depends("transfer.source_warehouse", "transfer.dest_warehouse")
    def _get_transfer_locations(self):
        for rec in self:
            # rec.source_location = rec.transfer.source_warehouse.lot_stock_id.id
            dest_location = False
            transit_locations = self.env["stock.location"].search(
                [("usage", "=", "transit")]
            )
            for location in transit_locations:
                if location.get_warehouse() == rec.transfer.dest_warehouse:
                    dest_location = location.id

            if not dest_location:
                rec.dest_location = rec.transfer.dest_warehouse.lot_stock_id.id
            else:
                rec.dest_location = dest_location

    def get_move_vals(self, picking, group):
        """
        Get the correct move values
        :param picking:
        :param group:
        :return: dict
        """

        self.ensure_one()

        return {
            "name": self.product_id and self.product_id.name or "Warehouse Transfer",
            "product_id": self.product_id.id,
            "product_uom": self.product_uom_id.id,
            "product_uom_qty": self.product_qty,
            "location_id": self.source_location.id,
            "location_dest_id": self.dest_location.id,
            "picking_id": picking.id,
            "group_id": group.id,
        }
