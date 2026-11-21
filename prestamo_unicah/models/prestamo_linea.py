from odoo import api, fields, models


class PrestamoLinea(models.Model):
    _name = "prestamo.linea"
    _description = "Equipo del préstamo"

    _equipo_unico = models.Constraint(
        "UNIQUE(prestamo_id, equipo_id)",
        "Un equipo no puede aparecer dos veces en el mismo préstamo.",
    )

    prestamo_id = fields.Many2one(
        "prestamo.prestamo", string="Préstamo", required=True, ondelete="cascade"
    )
    equipo_id = fields.Many2one(
        "prestamo.equipo",
        string="Equipo",
        required=True,
        domain="[('estado', '=', 'disponible')]",
    )
    categoria = fields.Selection(related="equipo_id.categoria", string="Categoría")
    observacion = fields.Char(string="Observación")

    @api.model_create_multi
    def create(self, vals_list):
        default_id = self.default_get(["prestamo_id"]).get("prestamo_id")
        ids = {vals.get("prestamo_id", default_id) for vals in vals_list}
        self.env["prestamo.prestamo"].browse(list(ids - {False, None}))._check_borrador()
        return super().create(vals_list)

    def write(self, vals):
        prestamos = self.prestamo_id
        if vals.get("prestamo_id"):
            prestamos |= self.env["prestamo.prestamo"].browse(vals["prestamo_id"])
        prestamos._check_borrador()
        return super().write(vals)

    @api.ondelete(at_uninstall=False)
    def _unlink_except_borrador(self):
        self.prestamo_id._check_borrador()
