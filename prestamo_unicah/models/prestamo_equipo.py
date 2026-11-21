from odoo import api, fields, models
from odoo.exceptions import UserError


class PrestamoEquipo(models.Model):
    _name = "prestamo.equipo"
    _description = "Equipo para préstamo"

    name = fields.Char(string="Nombre", required=True)
    codigo = fields.Char(string="Código de inventario", required=True, copy=False)
    categoria = fields.Selection(
        [
            ("laptop", "Laptop"),
            ("proyector", "Proyector"),
            ("audio", "Audio"),
            ("laboratorio", "Laboratorio"),
        ],
        string="Categoría",
        required=True,
        default="laptop",
    )
    estado = fields.Selection(
        [
            ("disponible", "Disponible"),
            ("prestado", "Prestado"),
            ("mantenimiento", "En mantenimiento"),
        ],
        string="Estado",
        required=True,
        default="disponible",
    )
    notas = fields.Text(string="Notas")
    active = fields.Boolean(string="Activo", default=True)

    linea_ids = fields.One2many("prestamo.linea", "equipo_id", string="Líneas de préstamo")
    veces_prestado = fields.Integer(string="Veces prestado", compute="_compute_veces_prestado")

    @api.depends("linea_ids")
    def _compute_veces_prestado(self):
        resultados = self.env["prestamo.linea"]._read_group(
            [("equipo_id", "in", self.ids)], ["equipo_id"], ["__count"]
        )
        cantidades = {equipo.id: cantidad for equipo, cantidad in resultados}
        for equipo in self:
            equipo.veces_prestado = cantidades.get(equipo.id, 0)

    @api.model_create_multi
    def create(self, vals_list):
        default_estado = self.default_get(["estado"]).get("estado", "disponible")
        if any(vals.get("estado", default_estado) == "prestado" for vals in vals_list):
            raise UserError("El estado Prestado se asigna desde un préstamo.")
        return super().create(vals_list)

    def write(self, vals):
        if "estado" in vals or vals.get("active") is False:
            self.check_access("write")
            self.lock_for_update()
            if vals.get("estado") == "prestado" or any(equipo.estado == "prestado" for equipo in self):
                raise UserError("Cambie el estado de un equipo prestado desde su préstamo.")
        return super().write(vals)

    def _set_estado_prestamo(self, estado):
        return super().write({"estado": estado})

    def action_mantenimiento(self):
        return self.write({"estado": "mantenimiento"})

    def action_disponible(self):
        return self.write({"estado": "disponible"})
