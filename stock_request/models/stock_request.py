# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class StockRequest(models.Model):
    _name = "stock.request"
    _inherit = ["mail.thread"]
    _description = "Stock Request"

    name = fields.Char(
        string="Order Ref", required=True, readonly=True, copy=False, default="/"
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        readonly=True,
        default=lambda self: self.env.user.company_id,
    )

    user_id = fields.Many2one(
        "res.users", string="Responsible", default=lambda self: self.env.user
    )
    date_quotation = fields.Datetime(
        string="Request Date", readonly=True, index=True, default=fields.Datetime.now
    )
    date_order = fields.Date(string="Order Date", readonly=True, index=True)
    amount_tax = fields.Float(string="Taxes", digits=0, default=1.2)
    amount_total = fields.Float(string="Total", digits=0)
    lines = fields.One2many(
        "stock.request.line", "order_id", string="Order Lines", copy=True
    )
    partner_id = fields.Many2one(
        "res.partner", string="Customer", change_default=True, index=True
    )
    employee_id = fields.Many2one("hr.employee", string="Employee", index=True)
    state = fields.Selection(
        [
            ("draft", "New"),
            ("approve", "Approve"),
            ("confirmed", "Confirmed"),
            ("picking", "Waiting"),
            ("done", "Transferred"),
            ("cancel", "Canceled"),
        ],
        "Status",
        readonly=True,
        copy=False,
        default="draft",
        tracking=True,
    )
    note = fields.Text(string="Internal Notes")
    fiscal_position_id = fields.Many2one(
        "account.fiscal.position", string="Fiscal Position"
    )
    location_src_id = fields.Many2one("stock.location", string="Source Location")
    location_dest_id = fields.Many2one(
        "stock.location",
        string="Destination Location",
        readonly=False,
        domain="[('usage', '=', 'internal')]",
    )
    picking_type_id = fields.Many2one(
        "stock.picking.type",
        string="Operation Type",
        domain=[("code", "=", "internal")],
    )
    picking_ids = fields.One2many(
        "stock.picking", "stock_request_id", string="Pickings"
    )
    transfer_ids = fields.One2many(
        "stock.warehouse.transfer", "stock_request_id", string="Transfers"
    )
    order_ids = fields.One2many(
        "purchase.order", "stock_request_id", string="Purchase Orders", tracking=True
    )
    delivery_count = fields.Integer(
        string="Picking Orders", compute="_compute_picking_ids"
    )
    fully_transferred = fields.Boolean(
        default=False,
    )
    check_state = fields.Boolean(string="", compute="_compute_state", store=1)

    @api.depends("picking_ids.move_line_ids_without_package.state")
    def _compute_state(self):
        for rec in self:
            rec.check_state = False
            flag = True
            for line in rec.lines:
                if (
                        line.transferred_qty < line.qty
                        or len(rec.picking_ids.filtered(lambda pk: pk.state == "done")) <= 1
                ):
                    flag = False
            if flag:
                rec.state = "done"
                for ll in rec.lines:
                    ll.state = "done"

    def _set_to_done(self):
        pass

    @api.onchange("user_id")
    def _onchange_user_id(self):
        if self.user_id:
            self.employee_id = (
                self.user_id.employee_ids[0]
                if len(self.user_id.employee_ids) > 0
                else False
            )
        else:
            self.employee_id = self.employee_id

    @api.depends("picking_ids")
    def _compute_picking_ids(self):
        for order in self:
            order.delivery_count = len(order.picking_ids)

    @api.model
    def create(self, vals):
        if vals.get("name", "/") == "/":
            vals["name"] = self.env["ir.sequence"].next_by_code("stock.request") or "/"
        return super(StockRequest, self).create(vals)

    def action_approve(self):
        self.state = "approve"

    def action_cancel(self):
        self.state = "cancel"

    def action_confirm(self):
        self.state = "confirmed"
        for line in self.lines:
            line.state = "confirmed"

    def action_view_picking(self):
        action = self.env.ref("stock.action_picking_tree_all").sudo().read()[0]
        action["domain"] = [("id", "in", self.picking_ids.ids)]
        return action

    def print_pdf_report(self):
        return self.env.ref("stock_request.print_pdf_report").report_action(self)

    def print_excel_report(self):
        return self.env.ref("stock_request.print_excel_report").report_action(self)


class StockQuotationLine(models.Model):
    _name = "stock.request.line"
    _description = "Lines of stock request"
    _rec_name = "product_id"

    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.user.company_id,
    )
    name = fields.Char(string="Line No")
    notice = fields.Char(string="Discount Notice")
    product_id = fields.Many2one(
        "product.product",
        string="Product",
        domain=[("sale_ok", "=", True)],
        required=True,
        change_default=True,
    )
    request_qty = fields.Float("Requested Qty", default=1, tracking=True)
    qty = fields.Float("Approved Qty", default=0.0, tracking=True)
    order_id = fields.Many2one("stock.request", string="Order Ref", ondelete="cascade")
    state = fields.Selection(
        [
            ("draft", "New"),
            ("confirmed", "Confirmed"),
            ("purchase", "To Purchase"),
            ("picking", "Waiting"),
            ("done", "Transferred"),
        ],
        "Status",
        readonly=True,
        copy=False,
        default="draft",
        store=True,
    )
    date_quotation = fields.Datetime(
        string="Request Date",
        readonly=True,
        index=True,
        default=fields.Datetime.now,
        related="order_id.date_quotation",
        store=True,
    )
    date_order = fields.Date(
        string="Order Date",
        readonly=True,
        index=True,
        related="order_id.date_order",
        store=True,
    )
    employee_id = fields.Many2one(
        "hr.employee",
        string="Employee",
        index=True,
        related="order_id.employee_id",
        store=True,
    )
    location_src_id = fields.Many2one(
        "stock.location",
        string="Source Location",
        related="order_id.location_src_id",
        store=True,
    )
    location_dest_id = fields.Many2one(
        "stock.location",
        string="Destination Location",
        related="order_id.location_dest_id",
        store=True,
    )
    transfer_status = fields.Selection(
        [
            ("waiting", "To Transfer"),
            ("partially", "Partially Transfer"),
            ("transferred", "Transferred"),
            ("purchase", "To Purchase"),
            ("purchased", "Purchased"),
        ],
        string="Transfer Status",
        store=True,
    )
    move_ids = fields.One2many("stock.move", "request_line_id", string="Stock Moves")
    transferred_qty = fields.Float(
        string="Transferred Quantity", compute="compute_transferred_qty"
    )
    purchased_qty = fields.Float(
        string="Purchased Quantity",
    )
    available_qty = fields.Float(
        String="Available Qty", compute="compute_available_qty"
    )
    qty_left = fields.Float(String="Qty Left")
    partner_id = fields.Many2one(
        "res.partner",
        string="Customer",
        change_default=True,
        index=True,
        related="order_id.partner_id",
        store=True,
    )
    qty_in_transfer = fields.Float(
        "Qty In Transfer", compute="_compute_qty_in_transfer"
    )
    user_id = fields.Many2one(related="order_id.user_id", store=1)

    def compute_transferred_qty(self):
        for line in self:
            for picking in line.order_id.picking_ids:
                if (
                        picking.location_dest_id.id == line.order_id.location_dest_id.id
                ) and picking.state == "done":
                    for move_line in picking.move_line_ids_without_package:
                        if move_line.product_id == line.product_id:
                            line.transferred_qty = move_line.qty_done
            line.qty_left = line.qty - line.transferred_qty
            if line.transfer_status not in ["purchase", "purchased"]:
                if line.transferred_qty >= line.qty:
                    line.transfer_status = "transferred"
                elif 0 < line.transferred_qty < line.qty:
                    line.transfer_status = "partially"
                else:
                    line.transfer_status = "waiting"

    def _compute_qty_in_transfer(self):
        for line in self:
            total_qty_in_transfer = 0.0
            for rec in line.env["stock.warehouse.transfer.line"].search(
                    [("request_line_id", "=", line.id)]
            ):
                total_qty_in_transfer += rec.product_qty
            line.qty_in_transfer = total_qty_in_transfer

    @api.depends("location_src_id", "transferred_qty", "move_ids.quantity_done")
    def compute_available_qty(self):
        for line in self:
            product_id = line.product_id.with_context(
                {"location_id": line.location_dest_id.id}
            )
            quants = self.env["stock.quant"].search(
                [
                    ("product_id", "=", product_id.id),
                    ("location_id", "=", line.order_id.location_dest_id.id),
                ]
            )
            line.available_qty = sum(quants.mapped("quantity"))

    def action_opening_quants(self):
        view_id = self.env.ref('stock_request.transfer_quantity_view').id

        transfer_lines = []

        stock_quants = self.env['stock.quant'].search([
            ('product_id', '=', self.product_id.id)])

        for quant in stock_quants:
            if quant.available_quantity > 0:
                print(quant.available_quantity, "***********************")
                transfer_lines.append((0, 0, {
                    'product_id': quant.product_id.id,
                    'available_qty': quant.available_quantity,
                    'location_id': quant.location_id.id,
                    'lot_id': quant.lot_id.id,
                    'stock_request_id': self.order_id.id,
                    'stock_request_line_id': self.id,
                    'quantity': self.qty,
                    'dest_location': self.location_dest_id.id
                }))

                transfer_lines = transfer_lines

        return {
            'name': 'Transfer',
            'view_type': 'form',
            'views': [(view_id, 'form')],
            'res_model': 'transfer',
            'view_id': view_id,
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': {
                'default_transfer_lines': transfer_lines
            },
        }

    def action_do_purchase(self):
        return {
            "name": "Make Purchase Order",
            "view_mode": "form",
            "res_model": "purchase.wizard",
            "type": "ir.actions.act_window",
            "target": "new",
            "context": {"stock_request_id": self.order_id.id},
        }


class StockPicking(models.Model):
    _inherit = "stock.picking"

    stock_request_id = fields.Many2one(
        "stock.request", string="Stock Request", copy=True
    )

    @api.model
    def create(self, vals):
        res = super(StockPicking, self).create(vals)
        if res.transfer and res.transfer.stock_request_id and not res.stock_request_id:
            res.stock_request_id = res.transfer.stock_request_id.id
        return res

    def button_validate(self):
        res = super(StockPicking, self).button_validate()
        for line in self.move_ids_without_package:
            if line.request_line_id:
                line.request_line_id.transfer_status = "transferred"
                line.request_line_id.transferred_qty = line.quantity_done
        return res


class StockMove(models.Model):
    _inherit = "stock.move"
    request_line_id = fields.Many2one(
        "stock.request.line", "QTY Request", index=True, copy=True
    )


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    picking_type_id = fields.Many2one(
        "stock.picking.type",
        string="Operation Type",
        domain=[("code", "=", "internal")],
    )

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        get_param = self.env["ir.config_parameter"].sudo().get_param
        res["picking_type_id"] = int(get_param("stock_request.picking_type_id"))
        return res

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        set_param = self.env["ir.config_parameter"].sudo().set_param
        set_param("stock_request.picking_type_id", int(self.picking_type_id.id))
