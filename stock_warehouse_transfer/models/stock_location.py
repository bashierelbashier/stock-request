from collections import OrderedDict
from odoo import models, fields


class StockLocation(models.Model):
    _inherit = "stock.location"

    warehouse_id = fields.Many2one("stock.warehouse", compute="_compute_warehouse_id")

    def _compute_warehouse_id(self):
        warehouses = self.env["stock.warehouse"].search(
            [("view_location_id", "parent_of", self.ids)]
        )
        view_by_wh = OrderedDict((wh.view_location_id.id, wh.id) for wh in warehouses)
        self.warehouse_id = False
        for loc in self:
            path = set(int(loc_id) for loc_id in loc.parent_path.split("/")[:-1])
            for view_location_id in view_by_wh:
                if view_location_id in path:
                    loc.warehouse_id = view_by_wh[view_location_id]
                    break
