"""Tests for app.services.calculations.

This is the money. Everything in this module decides what a client is billed, what a
claim pays out, and whether a policy still counts as in force. A wrong branch here is
not a broken page, it is a wrong invoice.

The services take a ``config_provider`` so the percentages can come from
ConfiguracionSistema in production and from a dict here. That keeps almost every test
below on SimpleTestCase, with no database and no fixtures: the arithmetic is checked
against numbers worked out by hand, not against whatever the database happened to hold.
"""

from datetime import date, timedelta
from decimal import Decimal
from unittest import mock

from django.test import SimpleTestCase

from app.services.calculations import DetalleRamoCalculationService, FacturaCalculationService, PolizaCalculationService

# The percentages the system ships with, restated here so a test failure says which
# number moved rather than just that two unnamed Decimals differ.
PCT_SUPERINTENDENCIA = Decimal("0.035")
PCT_SEGURO_CAMPESINO = Decimal("0.005")
PCT_IVA = Decimal("0.15")


def config(**overrides):
    """Build a config_provider over the shipped defaults.

    The real provider is ``ConfiguracionSistema.get_config(clave, default)``, which falls
    back to its second argument when the key is absent. This mirrors that contract, so a
    test that overrides nothing exercises exactly the production defaults.
    """

    values = {
        "PORCENTAJE_SUPERINTENDENCIA": PCT_SUPERINTENDENCIA,
        "PORCENTAJE_SEGURO_CAMPESINO": PCT_SEGURO_CAMPESINO,
        "PORCENTAJE_IVA": PCT_IVA,
        "DIAS_LIMITE_DESCUENTO_PRONTO_PAGO": 20,
        "PORCENTAJE_DESCUENTO_PRONTO_PAGO": Decimal("0.05"),
    }
    values.update(overrides)
    return lambda clave, default=None: values.get(clave, default)


class ContribucionesTests(SimpleTestCase):
    """The two legal contributions withheld on every invoice."""

    def test_the_two_contributions_come_out_at_three_and_a_half_and_a_half_percent(self):
        resultado = FacturaCalculationService.calcular_contribuciones(Decimal("1000"), config_provider=config())

        self.assertEqual(resultado["superintendencia"], Decimal("35"))
        self.assertEqual(resultado["seguro_campesino"], Decimal("5"))

    def test_a_zero_subtotal_contributes_nothing(self):
        resultado = FacturaCalculationService.calcular_contribuciones(Decimal("0"), config_provider=config())

        self.assertEqual(resultado["superintendencia"], Decimal("0"))
        self.assertEqual(resultado["seguro_campesino"], Decimal("0"))

    def test_a_reconfigured_percentage_is_the_one_that_applies(self):
        # The point of holding these in ConfiguracionSistema is that a regulator can move
        # the rate without a redeploy. If this test ever fails, the rate has been hardcoded.
        provider = config(PORCENTAJE_SUPERINTENDENCIA=Decimal("0.04"))

        resultado = FacturaCalculationService.calcular_contribuciones(Decimal("1000"), config_provider=provider)

        self.assertEqual(resultado["superintendencia"], Decimal("40"))


class DescuentoProntoPagoTests(SimpleTestCase):
    """The early-payment discount, and the window it lives in."""

    def setUp(self):
        self.emision = date(2026, 1, 1)
        self.provider = config()

    def test_paying_inside_the_window_earns_five_percent(self):
        descuento = FacturaCalculationService.calcular_descuento_pronto_pago(
            Decimal("1000"), self.emision, date(2026, 1, 10), config_provider=self.provider
        )

        self.assertEqual(descuento, Decimal("50"))

    def test_the_last_day_of_the_window_still_counts(self):
        # Twenty days from 1 January is 21 January, and the comparison is <=. A client who
        # pays on the deadline keeps the discount.
        descuento = FacturaCalculationService.calcular_descuento_pronto_pago(
            Decimal("1000"), self.emision, date(2026, 1, 21), config_provider=self.provider
        )

        self.assertEqual(descuento, Decimal("50"))

    def test_the_day_after_the_window_earns_nothing(self):
        descuento = FacturaCalculationService.calcular_descuento_pronto_pago(
            Decimal("1000"), self.emision, date(2026, 1, 22), config_provider=self.provider
        )

        self.assertEqual(descuento, Decimal("0.00"))

    def test_an_unpaid_invoice_earns_nothing(self):
        descuento = FacturaCalculationService.calcular_descuento_pronto_pago(
            Decimal("1000"), self.emision, None, config_provider=self.provider
        )

        self.assertEqual(descuento, Decimal("0.00"))

    def test_without_an_issue_date_there_is_no_window_to_be_inside_of(self):
        descuento = FacturaCalculationService.calcular_descuento_pronto_pago(
            Decimal("1000"), None, date(2026, 1, 10), config_provider=self.provider
        )

        self.assertEqual(descuento, Decimal("0.00"))


class MontoTotalTests(SimpleTestCase):
    """What is owed once everything is added and taken off."""

    def test_the_total_adds_tax_and_contributions_and_subtracts_the_rest(self):
        total = FacturaCalculationService.calcular_monto_total(
            subtotal=Decimal("1000"),
            iva=Decimal("150"),
            contribucion_super=Decimal("35"),
            contribucion_campesino=Decimal("5"),
            retenciones=Decimal("100"),
            descuento=Decimal("50"),
        )

        self.assertEqual(total, Decimal("1040"))

    def test_deductions_larger_than_the_invoice_floor_at_zero_rather_than_going_negative(self):
        # A negative total would mean the company owes the client money for taking out a
        # policy, and it would print that way on the invoice.
        total = FacturaCalculationService.calcular_monto_total(
            subtotal=Decimal("100"),
            iva=Decimal("15"),
            contribucion_super=Decimal("3.5"),
            contribucion_campesino=Decimal("0.5"),
            retenciones=Decimal("500"),
        )

        self.assertEqual(total, Decimal("0.00"))


class EstadoFacturaTests(SimpleTestCase):
    """Which of the four states an invoice reports."""

    def setUp(self):
        self.vencimiento = date(2026, 3, 31)
        self.total = Decimal("1000")

    def test_paying_the_exact_amount_marks_it_paid(self):
        estado = FacturaCalculationService.determinar_estado_factura(
            self.total, Decimal("1000"), self.vencimiento, fecha_actual=date(2026, 3, 1)
        )

        self.assertEqual(estado, "pagada")

    def test_overpaying_also_marks_it_paid(self):
        estado = FacturaCalculationService.determinar_estado_factura(
            self.total, Decimal("1200"), self.vencimiento, fecha_actual=date(2026, 3, 1)
        )

        self.assertEqual(estado, "pagada")

    def test_a_part_payment_beats_being_overdue(self):
        # Deliberate: an invoice past its date with money against it reports 'parcial',
        # not 'vencida'. Collections needs to see that someone has started paying.
        estado = FacturaCalculationService.determinar_estado_factura(
            self.total, Decimal("400"), self.vencimiento, fecha_actual=date(2026, 6, 1)
        )

        self.assertEqual(estado, "parcial")

    def test_nothing_paid_after_the_due_date_is_overdue(self):
        estado = FacturaCalculationService.determinar_estado_factura(
            self.total, Decimal("0.00"), self.vencimiento, fecha_actual=date(2026, 4, 1)
        )

        self.assertEqual(estado, "vencida")

    def test_the_due_date_itself_is_not_yet_overdue(self):
        # The comparison is strictly greater than, so a client has the whole of the last day.
        estado = FacturaCalculationService.determinar_estado_factura(
            self.total, Decimal("0.00"), self.vencimiento, fecha_actual=self.vencimiento
        )

        self.assertEqual(estado, "pendiente")


class FacturaCompletaTests(SimpleTestCase):
    """The one call that assembles a whole invoice.

    It reaches ConfiguracionSistema directly rather than taking a config_provider, so the
    lookup is patched here instead of injected.
    """

    def setUp(self):
        patcher = mock.patch("app.models.ConfiguracionSistema.get_config", side_effect=config())
        self.get_config = patcher.start()
        self.addCleanup(patcher.stop)

    def test_an_unpaid_invoice_reports_every_component_and_a_pending_state(self):
        # Unlike determinar_estado_factura, this entry point takes no fecha_actual and
        # reads the clock itself, so the due date has to be expressed relative to today
        # or the test would start reporting 'vencida' the day it was written.
        hoy = date.today()

        resultado = FacturaCalculationService.calcular_factura_completa(
            subtotal=Decimal("1000"),
            iva=Decimal("150"),
            fecha_emision=hoy,
            fecha_vencimiento=hoy + timedelta(days=30),
        )

        self.assertEqual(resultado["contribucion_superintendencia"], Decimal("35"))
        self.assertEqual(resultado["contribucion_seguro_campesino"], Decimal("5"))
        self.assertEqual(resultado["descuento_pronto_pago"], Decimal("0.00"))
        self.assertEqual(resultado["monto_total"], Decimal("1190"))
        self.assertEqual(resultado["estado"], "pendiente")

    def test_an_early_payment_shows_up_as_a_discount_and_lowers_the_total(self):
        hoy = date.today()

        resultado = FacturaCalculationService.calcular_factura_completa(
            subtotal=Decimal("1000"),
            iva=Decimal("150"),
            fecha_emision=hoy,
            fecha_vencimiento=hoy + timedelta(days=30),
            fecha_primer_pago=hoy + timedelta(days=5),
            total_pagado=Decimal("500"),
        )

        self.assertEqual(resultado["descuento_pronto_pago"], Decimal("50"))
        self.assertEqual(resultado["monto_total"], Decimal("1140"))
        self.assertEqual(resultado["estado"], "parcial")


class DerechosEmisionTests(SimpleTestCase):
    """The stepped issue fee. Every boundary, because that is where a table gets it wrong."""

    def test_each_bracket_returns_its_own_fee(self):
        casos = [
            (Decimal("0"), Decimal("0.50")),
            (Decimal("250"), Decimal("0.50")),
            (Decimal("250.01"), Decimal("1.00")),
            (Decimal("500"), Decimal("1.00")),
            (Decimal("500.01"), Decimal("3.00")),
            (Decimal("1000"), Decimal("3.00")),
            (Decimal("2000"), Decimal("5.00")),
            (Decimal("4000"), Decimal("7.00")),
        ]

        for prima, esperado in casos:
            with self.subTest(prima=prima):
                emision = DetalleRamoCalculationService.calcular_derechos_emision(prima, config_provider=config())

                self.assertEqual(emision, esperado)

    def test_a_premium_above_every_limit_falls_into_the_open_ended_bracket(self):
        emision = DetalleRamoCalculationService.calcular_derechos_emision(Decimal("1000000"), config_provider=config())

        self.assertEqual(emision, Decimal("9.00"))

    def test_a_table_supplied_by_configuration_replaces_the_shipped_one(self):
        provider = config(TABLA_TASAS_EMISION=[{"limite": 100, "tasa": "2.00"}, {"limite": None, "tasa": "20.00"}])

        self.assertEqual(
            DetalleRamoCalculationService.calcular_derechos_emision(Decimal("50"), config_provider=provider),
            Decimal("2.00"),
        )
        self.assertEqual(
            DetalleRamoCalculationService.calcular_derechos_emision(Decimal("5000"), config_provider=provider),
            Decimal("20.00"),
        )

    def test_a_table_whose_last_bracket_is_bounded_still_answers_above_it(self):
        # A table is meant to end with an open bracket. If someone edits that away in the
        # admin, a premium above every limit must still get a fee rather than raising.
        provider = config(TABLA_TASAS_EMISION=[{"limite": 100, "tasa": "2.00"}, {"limite": 200, "tasa": "4.00"}])

        emision = DetalleRamoCalculationService.calcular_derechos_emision(Decimal("999"), config_provider=provider)

        self.assertEqual(emision, Decimal("4.00"))


class ValoresDetalleTests(SimpleTestCase):
    """A full line of a policy, worked through by hand.

    Suma asegurada 100,000 at a rate of 2.5:

        prima            = 100000 x 2.5 / 100      = 2500.00
        superintendencia = 2500 x 3.5%             =   87.50
        campesino        = 2500 x 0.5%             =   12.50
        emision          = bracket for 2500        =    7.00
        base imponible   = 2500 + 87.50 + 12.50 + 7 = 2607.00
        IVA              = 2607 x 15%              =  391.05
        total facturado                             = 2998.05
    """

    def setUp(self):
        self.valores = DetalleRamoCalculationService.calcular_valores_detalle(
            suma_asegurada=Decimal("100000"), tasa=Decimal("2.5"), config_provider=config()
        )

    def test_the_premium_is_the_rate_applied_to_the_sum_insured(self):
        self.assertEqual(self.valores["total_prima"], Decimal("2500"))

    def test_the_taxable_base_gathers_the_premium_the_contributions_and_the_fee(self):
        self.assertEqual(self.valores["contribucion_superintendencia"], Decimal("87.50"))
        self.assertEqual(self.valores["seguro_campesino"], Decimal("12.50"))
        self.assertEqual(self.valores["emision"], Decimal("7.00"))
        self.assertEqual(self.valores["base_imponible"], Decimal("2607.00"))

    def test_tax_is_charged_on_the_base_and_not_on_the_premium_alone(self):
        # 15% of the premium would be 375.00. Charging it on the base gives 391.05, and the
        # difference is what the contributions and the issue fee add.
        self.assertEqual(self.valores["iva"], Decimal("391.05"))
        self.assertEqual(self.valores["total_facturado"], Decimal("2998.05"))

    def test_an_ordinary_client_has_nothing_withheld_and_pays_the_invoice_as_billed(self):
        self.assertEqual(self.valores["retencion_prima"], Decimal("0.00"))
        self.assertEqual(self.valores["retencion_iva"], Decimal("0.00"))
        self.assertEqual(self.valores["valor_por_pagar"], Decimal("2998.05"))

    def test_a_large_taxpayer_withholds_one_percent_of_the_premium_and_all_of_the_tax(self):
        valores = DetalleRamoCalculationService.calcular_valores_detalle(
            suma_asegurada=Decimal("100000"),
            tasa=Decimal("2.5"),
            es_gran_contribuyente=True,
            config_provider=config(),
        )

        self.assertEqual(valores["retencion_prima"], Decimal("25.00"))
        self.assertEqual(valores["retencion_iva"], Decimal("391.05"))
        self.assertEqual(valores["valor_por_pagar"], Decimal("2582.00"))

    def test_the_invoice_and_the_withholdings_reconcile(self):
        # Anything that changes one side of this and not the other is an accounting error,
        # whatever else it looks like.
        valores = DetalleRamoCalculationService.calcular_valores_detalle(
            suma_asegurada=Decimal("87431.19"),
            tasa=Decimal("1.37"),
            es_gran_contribuyente=True,
            config_provider=config(),
        )

        self.assertEqual(
            valores["valor_por_pagar"],
            valores["total_facturado"] - valores["retencion_prima"] - valores["retencion_iva"],
        )

    def test_a_zero_rate_produces_a_line_that_still_carries_the_issue_fee(self):
        valores = DetalleRamoCalculationService.calcular_valores_detalle(
            suma_asegurada=Decimal("100000"), tasa=Decimal("0"), config_provider=config()
        )

        self.assertEqual(valores["total_prima"], Decimal("0"))
        self.assertEqual(valores["emision"], Decimal("0.50"))
        self.assertEqual(valores["base_imponible"], Decimal("0.50"))


class EstadoPolizaTests(SimpleTestCase):
    """Whether a policy reads as in force, expiring or expired."""

    def setUp(self):
        self.hoy = date(2026, 6, 15)

    def test_a_policy_whose_end_date_has_passed_is_expired(self):
        estado = PolizaCalculationService.determinar_estado_poliza(
            date(2025, 1, 1), date(2026, 6, 14), fecha_actual=self.hoy
        )

        self.assertEqual(estado, "vencida")

    def test_a_policy_ending_inside_the_alert_window_is_flagged_as_expiring(self):
        estado = PolizaCalculationService.determinar_estado_poliza(
            date(2025, 1, 1), self.hoy + timedelta(days=29), fecha_actual=self.hoy
        )

        self.assertEqual(estado, "por_vencer")

    def test_a_policy_ending_beyond_the_alert_window_is_simply_in_force(self):
        estado = PolizaCalculationService.determinar_estado_poliza(
            date(2025, 1, 1), self.hoy + timedelta(days=31), fecha_actual=self.hoy
        )

        self.assertEqual(estado, "vigente")

    def test_the_alert_window_is_configurable(self):
        estado = PolizaCalculationService.determinar_estado_poliza(
            date(2025, 1, 1), self.hoy + timedelta(days=45), fecha_actual=self.hoy, dias_alerta=60
        )

        self.assertEqual(estado, "por_vencer")

    def test_a_cancelled_policy_that_has_not_started_stays_cancelled(self):
        estado = PolizaCalculationService.determinar_estado_poliza(
            self.hoy + timedelta(days=10),
            self.hoy + timedelta(days=375),
            fecha_actual=self.hoy,
            estado_actual="cancelada",
        )

        self.assertEqual(estado, "cancelada")

    def test_a_policy_that_has_not_started_yet_reads_as_in_force(self):
        # Debatable as business logic, but it is what the system does, and the renewals
        # screen depends on it: a policy signed for next month is not shown as expired.
        estado = PolizaCalculationService.determinar_estado_poliza(
            self.hoy + timedelta(days=10), self.hoy + timedelta(days=375), fecha_actual=self.hoy
        )

        self.assertEqual(estado, "vigente")

    def test_missing_dates_do_not_crash_the_caller(self):
        self.assertEqual(
            PolizaCalculationService.determinar_estado_poliza(None, None, fecha_actual=self.hoy), "vigente"
        )


class DiasParaVencerTests(SimpleTestCase):
    def test_it_counts_the_days_left(self):
        dias = PolizaCalculationService.calcular_dias_para_vencer(date(2026, 7, 15), fecha_actual=date(2026, 6, 15))

        self.assertEqual(dias, 30)

    def test_a_date_already_past_counts_negative(self):
        # Callers rely on the sign: the reports read anything below zero as overdue.
        dias = PolizaCalculationService.calcular_dias_para_vencer(date(2026, 6, 1), fecha_actual=date(2026, 6, 15))

        self.assertEqual(dias, -14)

    def test_a_policy_without_an_end_date_reports_zero(self):
        self.assertEqual(PolizaCalculationService.calcular_dias_para_vencer(None), 0)


class DeducibleTests(SimpleTestCase):
    """What the client absorbs before the policy pays anything."""

    def test_with_no_percentage_the_fixed_amount_is_the_deductible(self):
        deducible = PolizaCalculationService.calcular_deducible_aplicable(
            Decimal("10000"), deducible_fijo=Decimal("500")
        )

        self.assertEqual(deducible, Decimal("500"))

    def test_a_percentage_is_taken_against_the_claim(self):
        deducible = PolizaCalculationService.calcular_deducible_aplicable(
            Decimal("10000"), porcentaje_deducible=Decimal("10")
        )

        self.assertEqual(deducible, Decimal("1000"))

    def test_when_both_apply_the_larger_one_wins(self):
        mayor_el_porcentaje = PolizaCalculationService.calcular_deducible_aplicable(
            Decimal("10000"), deducible_fijo=Decimal("500"), porcentaje_deducible=Decimal("10")
        )
        mayor_el_fijo = PolizaCalculationService.calcular_deducible_aplicable(
            Decimal("10000"), deducible_fijo=Decimal("2000"), porcentaje_deducible=Decimal("10")
        )

        self.assertEqual(mayor_el_porcentaje, Decimal("1000"))
        self.assertEqual(mayor_el_fijo, Decimal("2000"))

    def test_the_minimum_lifts_a_percentage_that_falls_under_it(self):
        deducible = PolizaCalculationService.calcular_deducible_aplicable(
            Decimal("1000"), porcentaje_deducible=Decimal("10"), deducible_minimo=Decimal("500")
        )

        self.assertEqual(deducible, Decimal("500"))


class IndemnizacionTests(SimpleTestCase):
    """What is actually paid out."""

    def test_the_payout_is_the_claim_less_the_deductible_and_the_depreciation(self):
        monto = PolizaCalculationService.calcular_monto_indemnizacion(Decimal("10000"), Decimal("1000"), Decimal("500"))

        self.assertEqual(monto, Decimal("8500"))

    def test_deductions_larger_than_the_claim_pay_nothing_rather_than_billing_the_client(self):
        monto = PolizaCalculationService.calcular_monto_indemnizacion(Decimal("1000"), Decimal("2000"), Decimal("500"))

        self.assertEqual(monto, Decimal("0.00"))

    def test_a_claim_with_no_deductible_pays_in_full(self):
        monto = PolizaCalculationService.calcular_monto_indemnizacion(Decimal("10000"), Decimal("0.00"))

        self.assertEqual(monto, Decimal("10000"))
