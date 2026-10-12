from unittest import mock

from app.signals import siniestro_post_save


def test_failed_broker_notification_is_logged_and_does_not_break_save():
    siniestro = mock.Mock(creado_por=None)
    with (
        mock.patch("app.signals.NotificacionesService") as service,
        mock.patch("app.signals.logger") as log,
    ):
        service.notificar_siniestro_a_broker.side_effect = RuntimeError("smtp down")
        siniestro_post_save(sender=None, instance=siniestro, created=True)

    log.warning.assert_called_once()
    assert "broker" in log.warning.call_args.args[0]
