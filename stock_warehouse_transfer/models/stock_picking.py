import logging

from odoo import models, fields

_logger = logging.getLogger(__name__)


class StockPicking(models.Model):
    _inherit = "stock.picking"

    transfer = fields.Many2one(
        comodel_name="stock.warehouse.transfer", string="Transfer", copy=False
    )
