from ast import literal_eval
from datetime import date, timedelta

from unittest.mock import patch

from lxml import etree
from psycopg2 import IntegrityError

from odoo import Command, fields
from odoo.exceptions import UserError, ValidationError
from odoo.tests import TransactionCase, tagged
from odoo.tests.common import new_test_user


@tagged("post_install", "-at_install")
class TestPrestamos(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        user = new_test_user(cls.env, login="operador_prestamos")
        cls.Equipo = cls.env["prestamo.equipo"].with_user(user)
        cls.Prestamo = cls.env["prestamo.prestamo"].with_user(user)
        cls.Linea = cls.env["prestamo.linea"].with_user(user)
        cls.contacto = cls.env["res.partner"].create({"name": "Solicitante de prueba"})
        cls.equipos = cls.Equipo.browse([
            cls.env.ref(f"prestamo_unicah.{xmlid}").id
            for xmlid in ("equipo_laptop_01", "equipo_laptop_02", "equipo_proyector_01", "equipo_bocina_01")
        ])

    def _prestamo(self, dias=3, equipos=None, tipo="estudiante"):
        inicio = date(2026, 11, 1)
        return self.Prestamo.create({
            "name": "Clase de Redes",
            "partner_id": self.contacto.id,
            "tipo_solicitante": tipo,
            "fecha_prestamo": inicio,
            "fecha_devolucion": inicio + timedelta(days=dias),
            "linea_ids": [Command.create({"equipo_id": equipo.id}) for equipo in (equipos or [])],
        })

    def test_catalogo_y_permisos(self):
        self.assertEqual(set(self.equipos.mapped("codigo")), {"LAP-001", "LAP-002", "PRO-001", "AUD-001"})
        self.assertEqual(set(self.equipos.mapped("estado")), {"disponible"})
        equipo = self.Equipo.create({"name": "Micrófono 01", "codigo": "AUD-002", "categoria": "audio"})
        equipo.write({"active": False})
        self.assertFalse(self.Equipo.search([("id", "=", equipo.id)]))
        equipo.unlink()

    def test_relaciones_flujo_y_chatter(self):
        prestamo = self._prestamo(equipos=self.equipos[:2])
        self.assertEqual(prestamo.state, "borrador")
        self.assertEqual(prestamo.linea_ids.prestamo_id, prestamo)
        self.assertEqual(prestamo.linea_ids.mapped("categoria"), ["laptop", "laptop"])
        self.assertEqual(prestamo.cantidad_equipos, 2)
        self.assertEqual(prestamo.dias_prestamo, 3)
        self.assertIn(prestamo.id, self.contacto.prestamo_ids.ids)
        self.env.flush_all()
        self.env.cr.precommit.run()
        prestamo.action_prestar()
        self.env.flush_all()
        self.env.cr.precommit.run()
        self.assertEqual(prestamo.state, "prestado")
        self.assertEqual(set(self.equipos[:2].mapped("estado")), {"prestado"})
        self.assertTrue(any("Se prestaron" in m.body for m in prestamo.message_ids if m.body))
        self.assertTrue(self.env["mail.message"].search_count([("model", "=", prestamo._name), ("res_id", "=", prestamo.id), ("message_type", "=", "tracking")]))
        with self.assertRaises(UserError):
            prestamo.linea_ids[0].write({"observacion": "Cambio inválido"})
        with self.assertRaises(UserError):
            self.equipos[0].write({"estado": "mantenimiento"})
        prestamo.action_devolver()
        self.assertEqual(prestamo.state, "devuelto")
        self.assertEqual(set(self.equipos[:2].mapped("estado")), {"disponible"})
        self.assertTrue(any("equipos fueron devueltos" in m.body for m in prestamo.message_ids if m.body))

    def test_fechas_y_limite_dias(self):
        with self.assertRaisesRegex(ValidationError, "anterior"):
            self._prestamo(dias=-1)
        with self.assertRaisesRegex(ValidationError, "7 días"):
            self._prestamo(dias=10)

    def test_equipo_repetido(self):
        prestamo = self._prestamo(equipos=self.equipos[:1])
        with self.assertRaises(IntegrityError):
            self.Linea.create({"prestamo_id": prestamo.id, "equipo_id": self.equipos[0].id})

    def test_limite_equipos(self):
        prestamo = self._prestamo(equipos=self.equipos[:3])
        with self.assertRaisesRegex(UserError, "2 equipos"):
            prestamo.action_prestar()
        self.assertEqual(prestamo.state, "borrador")

    def test_disponibilidad(self):
        prestamo = self._prestamo(equipos=self.equipos[:1])
        self.equipos[0].write({"estado": "mantenimiento"})
        with self.assertRaisesRegex(UserError, "Laptop Dell 01"):
            prestamo.action_prestar()

    def test_docente_y_segundo_prestamo(self):
        primero = self._prestamo(equipos=self.equipos[:3], dias=10, tipo="docente")
        segundo = self._prestamo(equipos=self.equipos[:1])
        primero.action_prestar()
        self.assertEqual(primero.state, "prestado")
        with self.assertRaisesRegex(UserError, "Laptop Dell 01"):
            segundo.action_prestar()

    def test_filtros_agrupaciones_y_vistas(self):
        activo = self._prestamo(equipos=self.equipos[:1])
        activo.action_prestar()
        segundo = self._prestamo()
        segundo._set_state("atrasado")
        self._prestamo()
        view = self.env.ref("prestamo_unicah.prestamo_prestamo_view_search")
        arch = etree.fromstring(view.arch)
        for nombre, esperados in (("activos", activo | segundo), ("atrasados", segundo)):
            filtro = arch.xpath(f"//filter[@name='{nombre}']")[0]
            self.assertEqual(self.Prestamo.search(literal_eval(filtro.get("domain"))), esperados)
        for nombre, campo in (("agrupar_estado", "state"), ("agrupar_solicitante", "partner_id")):
            filtro = arch.xpath(f"//filter[@name='{nombre}']")[0]
            self.assertEqual(literal_eval(filtro.get("context"))["group_by"], campo)
            self.assertTrue(self.Prestamo._read_group([], [campo], ["__count"]))
        kanban = self.Equipo.get_view(view_type="kanban")
        self.assertEqual(etree.fromstring(kanban["arch"]).get("default_group_by"), "estado")
        contacto = self.contacto.get_view(view_type="form")
        self.assertTrue(etree.fromstring(contacto["arch"]).xpath("//field[@name='prestamo_ids'][@readonly='1']"))

    def test_marcar_atrasado(self):
        prestamo = self._prestamo(equipos=self.equipos[:1])
        with self.assertRaises(UserError):
            prestamo.action_marcar_atrasado()
        prestamo.action_prestar()
        with patch.object(fields.Date, "context_today", return_value=prestamo.fecha_devolucion):
            with self.assertRaisesRegex(UserError, "todavía no ha pasado"):
                prestamo.action_marcar_atrasado()
        with patch.object(fields.Date, "context_today", return_value=prestamo.fecha_devolucion + timedelta(days=1)):
            prestamo.action_marcar_atrasado()
        self.assertEqual(prestamo.state, "atrasado")
        self.assertEqual(self.equipos[0].estado, "prestado")
        self.assertTrue(any("se marcó como atrasado" in m.body for m in prestamo.message_ids if m.body))
        prestamo.action_devolver()
        self.assertEqual(self.equipos[0].estado, "disponible")
