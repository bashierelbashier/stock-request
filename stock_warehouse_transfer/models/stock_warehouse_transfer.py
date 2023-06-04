import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class Location(models.Model):
    _inherit = "stock.location"
    _rec_name = ""


class Warehouse(models.Model):
    _inherit = "stock.warehouse"

    transfer_user_ids = fields.Many2many(
        "res.users", "transfer_warehouses_rel", "uuid", "ww_id", string="Transfer Users"
    )


class PickingType(models.Model):
    _inherit = "stock.picking.type"

    users_ids = fields.Many2many(
        "res.users", "users_operations_types_rel", string="Users"
    )

    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        if self.env.user.has_group(
            "stock_warehouse_transfer.access_own_operation_types"
        ) and self._context.get("check_accesses", False):
            args += [("users_ids", "in", [self.env.user.id])]
        return super(PickingType, self).search(
            args=args, offset=offset, limit=limit, order=order, count=count
        )


class StockWarehouseTransfer(models.Model):
    _name = "stock.warehouse.transfer"
    _description = "Stock Warehouse Transfer"
    _inherit = ["mail.thread"]
    _order = "date desc, name desc"

    @api.model
    def create(self, vals):
        vals["name"] = self.env["ir.sequence"].get("stock.warehouse.transfer") or "/"
        return super(StockWarehouseTransfer, self).create(vals)

    @api.model
    def _get_default_date(self):
        return fields.Date.context_today(self)

    @api.model
    def _get_default_trans_location(self):
        loc_obj = self.env["stock.location"]
        return loc_obj.with_context(check_accesses=False).search(
            [("usage", "=", "transit")], limit=1
        )

    @api.model
    def _get_default_state(self):
        return "draft"

    @api.depends("pickings.state")
    def _calc_transfer_state(self):
        for rec in self:
            if rec.pickings:
                picking_states = [p.state for p in rec.pickings]
                if "done" in picking_states:
                    rec.state = "done"
                else:
                    rec.state = "picking"

            else:
                rec.state = "draft"

    @api.depends("source_warehouse", "state")
    def get_transfer_from_check(self):
        j_obj = self.env["stock.warehouse"]
        for rec in self:
            if rec.source_warehouse:
                if j_obj.search(
                    [
                        ("transfer_user_ids", "in", [self.env.user.id]),
                        ("id", "=", rec.source_warehouse.id),
                    ]
                ):
                    rec.transfer_from_check = True
                else:
                    rec.transfer_from_check = False
            else:
                rec.transfer_from_check = False

    transfer_from_check = fields.Boolean(
        compute="get_transfer_from_check", string="Transfer From Warehouse"
    )

    name = fields.Char(string="Reference", default="/", copy=False)
    date = fields.Date(string="Date", copy=True, default=_get_default_date)
    source_warehouse = fields.Many2one(
        comodel_name="stock.warehouse",
        copy=True,
        string="Source Warehouse",
        compute="compute_warehouse",
        store=True,
    )
    dest_warehouse = fields.Many2one(
        comodel_name="stock.warehouse",
        copy=True,
        string="Destination Warehouse",
        compute="compute_warehouse",
        store=True,
    )
    source_location = fields.Many2one(
        "stock.location",
        copy=True,
        string="From Location",
        domain=[("usage", "=", "internal")],
    )
    dest_location = fields.Many2one(
        "stock.location",
        copy=True,
        string="To Location",
        domain=[("usage", "=", "internal")],
    )
    trans_location = fields.Many2one(
        "stock.location",
        copy=True,
        string="Transit Location",
        domain=[("usage", "=", "transit")],
        default=_get_default_trans_location,
    )
    state = fields.Selection(
        selection=[("draft", "Draft"), ("picking", "Picking"), ("done", "Done")],
        string="Status",
        default=_get_default_state,
        copy=True,
        store=True,
        compute=_calc_transfer_state,
    )
    lines = fields.One2many(
        comodel_name="stock.warehouse.transfer.line",
        copy=True,
        inverse_name="transfer",
        string="Transfer Lines",
    )
    pickings = fields.One2many(
        comodel_name="stock.picking", inverse_name="transfer", string="Related Picking"
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.user.company_id,
    )

    @api.depends("source_location", "dest_location")
    def compute_warehouse(self):
        for rec in self:
            rec.source_warehouse = rec.source_location.warehouse_id.id
            rec.dest_warehouse = rec.dest_location.warehouse_id.id

    def get_transfer_picking_type(self):
        self.ensure_one()
        picking_types = (
            self.env["stock.picking.type"]
            .with_context(check_accesses=False)
            .search(
                [
                    ("default_location_src_id", "=", self.source_location.id),
                    ("code", "=", "internal"),
                ]
            )
        )
        if not picking_types:
            _logger.error("No picking tye found")
            # TODO: Exception Raise

        return picking_types and picking_types[0]

    def get_picking_vals(self):
        self.ensure_one()

        transit_location = self.trans_location.id

        picking_type = self.get_transfer_picking_type()
        if not picking_type:
            raise UserError(_("No picking type found!"))

        if not transit_location:
            raise UserError(_("No transit location found!"))

        picking_vals = {
            "picking_type_id": picking_type.id,
            "transfer": self.id,
            "origin": self.name,
            "move_type": "one",
            "location_id": self.source_location.id,
            "location_dest_id": transit_location,
        }
        return picking_vals

    def action_create_picking_new(self):
        for rec in self:
            if rec.source_warehouse == rec.dest_warehouse:
                raise UserError(
                    _(
                        "Sorry, Source Warehouse must"
                        " be Different than Destination Warehouse ."
                    )
                )
            picking_vals = rec.get_picking_vals()
            _logger.debug("Picking Vals: %s", picking_vals)
            picking = rec.pickings.create(picking_vals)
            if not picking:
                _logger.error("Error Creating Picking")
                # TODO: Add  Exception

            pc_group = rec._get_procurement_group()
            transit_location = self.trans_location.id
            m_obj = self.env["stock.move"]
            for line in rec.lines:
                move_vals = line.get_move_vals(picking, pc_group)
                if move_vals:
                    _logger.debug("Move Vals: %s", move_vals)
                move_vals.update(
                    {
                        "location_id": self.source_location.id,
                        "location_dest_id": transit_location,
                    }
                )

                m_obj.create(move_vals)
            picking.action_confirm()
            picking.action_assign()

    @api.model
    def _prepare_procurement_group(self):
        return {"name": self.name}

    @api.model
    def _get_procurement_group(self):
        pc_groups = (
            self.env["procurement.group"]
            .with_context(check_accesses=False)
            .search([("name", "=", self.name)])
        )
        if pc_groups:
            pc_group = pc_groups[0]
        else:
            pc_vals = self._prepare_procurement_group()
            pc_group = self.env["procurement.group"].create(pc_vals)
        return pc_group or False


class StockPicking(models.Model):
    _inherit = "stock.picking"

    original_location_id = fields.Many2one("stock.location")

    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        if self.env.user.has_group(
            "stock_warehouse_transfer.access_own_operation_types"
        ) and self._context.get("check_accesses", False):
            args += [("picking_type_id.users_ids", "in", [self.env.user.id])]
        return super(StockPicking, self).search(
            args=args, offset=offset, limit=limit, order=order, count=count
        )

    def button_validate(self):
        # TDE FIXME: should work in batch
        transfer_id = self.sudo().transfer
        self.ensure_one()
        res = super(StockPicking, self).button_validate()

        transfer = False
        transfer_ids = (
            self.env["stock.picking"]
            .with_context(check_accesses=False)
            .sudo()
            .search_count([("transfer", "=", transfer_id.id)])
        )

        if transfer_ids < 2:
            transfer = False
        if transfer_ids >= 2:
            transfer = True

        m_obj = self.env["stock.move"]
        if transfer_id:
            transit_location = transfer_id.trans_location.id

            picking_types = (
                self.env["stock.picking.type"]
                .with_context(check_accesses=False)
                .search(
                    [
                        ("warehouse_id", "=", transfer_id.dest_warehouse.id),
                        ("code", "=", "internal"),
                    ],
                    limit=1,
                )
            )

            if not picking_types:
                raise UserError("Please create operation for the destination warehouse")
            if not transfer:

                picking_vals = {
                    "picking_type_id": picking_types.id,
                    "transfer": transfer_id.id,
                    "origin": self.name + "  " + transfer_id.name,
                    "move_type": "one",
                    "location_dest_id": transfer_id.dest_location.id,
                    "location_id": transit_location,
                    "original_location_id": self.location_id.id,
                    "immediate_transfer": False,
                }
                picking = self.create(picking_vals)

                for line in self.move_ids_without_package:
                    if line.product_qty > 0:
                        move_vals = {
                            "product_id": line.product_id.id,
                            "product_uom_qty": line.product_qty,
                            "product_uom": line.product_uom.id,
                            "name": line.product_id.name,
                            "location_dest_id": transfer_id.dest_location.id,
                            "location_id": transit_location,
                            "picking_id": picking.id,
                        }
                        m_obj.create(move_vals)
                picking.action_confirm()
                picking.action_assign()
                for line in picking.move_line_ids_without_package:
                    line.update(
                        {
                            "location_dest_id": transfer_id.dest_location.id,
                            "location_id": transit_location,
                            "lot_id": line.lot_id.id,
                        }
                    )
        return res
