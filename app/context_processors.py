from .models import Alerta


def alertas_context(request):

    if request.user.is_authenticated:

        alertas_count = Alerta.objects.filter(estado__in=["pendiente", "enviada"]).count()

        alertas_recientes = (
            Alerta.objects.filter(estado__in=["pendiente", "enviada"])
            .select_related("poliza", "factura", "siniestro")
            .order_by("-fecha_creacion")[:5]
        )

        return {
            "alertas_pendientes_count": alertas_count,
            "alertas_recientes": alertas_recientes,
        }

    return {
        "alertas_pendientes_count": 0,
        "alertas_recientes": [],
    }
