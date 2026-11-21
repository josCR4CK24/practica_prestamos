from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


DIAS_MAXIMOS_ESTUDIANTE = 7
LIMITE_EQUIPOS_ESTUDIANTE = 2


class PrestamoPrestamo(models.Model):
    _name = "prestamo.prestamo"
    _description = "Préstamo de equipo"
    _inherit = ["mail.thread"]
    _order = "fecha_prestamo desc, id desc"

    name = fields.Char(string="Motivo", required=True)
    partner_id = fields.Many2one("res.partner", string="Solicitante", required=True)
    tipo_solicitante = fields.Selection(
        [("estudiante", "Estudiante"), ("docente", "Docente")],
        string="Tipo de solicitante",
        required=True,
        default="estudiante",
    )
    fecha_prestamo = fields.Date(         string="Fecha de préstamo", required=True, default=fields.Date.context_today
    )
    fecha_devolucion = fields.Date(string="Fecha de devolución", required=True)
    state = fields.Selection(
        [
            ("borrador", "Borrador"),
            ("prestado", "Prestado"),
            ("devuelto", "Devuelto"),
            ("atrasado", "Atrasado"),
        ],
        string="Estado",
        required=True,
        default="borrador",
        tracking=True,
    )
    linea_ids = fields.One2many("prestamo.linea", "prestamo_id", string="Equipos")
    cantidad_equipos = fields.Integer(
        string="Cantidad de equipos", compute="_compute_cantidad_equipos", store=True
    )
    dias_prestamo = fields.Integer(
        string="Días de préstamo", compute="_compute_dias_prestamo", store=True
    )

    @api.depends("linea_ids")
    def _compute_cantidad_equipos(self):
        for prestamo in self:
            prestamo.cantidad_equipos = len(prestamo.linea_ids)

    @api.depends("fecha_prestamo", "fecha_devolucion")
    def _compute_dias_prestamo(self):
        for prestamo in self:
            if prestamo.fecha_prestamo and prestamo.fecha_devolucion:
                dias = (prestamo.fecha_devolucion - prestamo.fecha_prestamo).days
                prestamo.dias_prestamo = dias
            else:
                prestamo.dias_prestamo = 0

    @api.model_create_multi
    def create(self, vals_list):
        default_state = self.default_get(["state"]).get("state", "borrador")
        if any(vals.get("state", default_state) != "borrador" for vals in vals_list):
            raise UserError("Los préstamos se crean en borrador.")
        return super().create(vals_list)

    def _check_borrador(self):
        self.lock_for_update()
        if any(prestamo.state != "borrador" for prestamo in self):
            raise UserError("Solo se pueden modificar préstamos en borrador.")

    def write(self, vals):
        if "state" in vals:
            raise UserError("Use los botones del préstamo para cambiar su estado.")
        if vals.keys() & {"name", "partner_id", "tipo_solicitante", "fecha_prestamo",
                          "fecha_devolucion", "linea_ids"}:
            self.check_access("write")
            self._check_borrador()
        return super().write(vals)

    @api.ondelete(at_uninstall=False)
    def _unlink_except_borrador(self):
        self._check_borrador()

    def _set_state(self, state):
        return super().write({"state": state})

    def action_prestar(self):
        self.check_access("write")
        self.lock_for_update()
        for prestamo in self:
            if prestamo.state != "borrador":
                raise UserError("Solo se puede prestar un préstamo en borrador.")
            if not prestamo.linea_ids:
                raise UserError("Agregue al menos un equipo al préstamo.")
            if (
                prestamo.tipo_solicitante == "estudiante"
                and prestamo.cantidad_equipos > LIMITE_EQUIPOS_ESTUDIANTE
            ):
                raise UserError(
                    f"Un estudiante puede prestar hasta {LIMITE_EQUIPOS_ESTUDIANTE} equipos."
                )
            equipos = prestamo.linea_ids.equipo_id
            equipos.check_access("write")
            equipos.lock_for_update()
            for equipo in equipos:
                if equipo.estado != "disponible" or not equipo.active:
                    raise UserError(f"El equipo {equipo.display_name} no está disponible.")
            equipos._set_estado_prestamo("prestado")
            prestamo._set_state("prestado")
            prestamo.message_post(
                body=f"Se prestaron {prestamo.cantidad_equipos} equipo(s) "
                     f"a {prestamo.partner_id.name}."
            )

    def action_devolver(self):
        self.check_access("write")
        self.lock_for_update()
        for prestamo in self:
            if prestamo.state not in ("prestado", "atrasado"):
                raise UserError("Solo se puede devolver un préstamo activo.")
            prestamo.linea_ids.equipo_id._set_estado_prestamo("disponible")
            prestamo._set_state("devuelto")
            prestamo.message_post(body="Los equipos fueron devueltos.")

    @api.constrains("fecha_prestamo", "fecha_devolucion", "tipo_solicitante")
    def _check_fechas(self):
        for prestamo in self:
            if prestamo.fecha_devolucion < prestamo.fecha_prestamo:
                raise ValidationError("La fecha de devolución no puede ser anterior al préstamo.")
            if (
                prestamo.tipo_solicitante == "estudiante"
                and prestamo.dias_prestamo > DIAS_MAXIMOS_ESTUDIANTE
            ):
                raise ValidationError(
                    f"Un estudiante puede prestar equipos hasta por {DIAS_MAXIMOS_ESTUDIANTE} días."
                )

    def action_marcar_atrasado(self):
        self.check_access("write")
        self.lock_for_update()
        for prestamo in self:
            if prestamo.state != "prestado":
                raise UserError("Solo se puede marcar atrasado un préstamo prestado.")
            if prestamo.fecha_devolucion >= fields.Date.context_today(prestamo):
                raise UserError("La fecha de devolución todavía no ha pasado.")
            prestamo._set_state("atrasado")
            prestamo.message_post(body="El préstamo se marcó como atrasado.")
