"""
Servicio de verificación de Alertas automáticas.
Responsabilidad única: verificar y generar alertas programadas.
"""

from typing import Dict, List
from .broker import BrokerNotifier
from .responsable import ResponsableNotifier


class AlertasService:
    """
    Servicio para verificación y generación de alertas automáticas.
    Diseñado para ejecutarse como tarea periódica (Celery, cron, etc.).
    
    USO:
        service = AlertasService()
        resultados = service.verificar_todas()
        
        # O verificar tipos específicos
        resultados = service.verificar_respuestas_pendientes()
    """
    
    def __init__(self):
        self._broker_notifier = BrokerNotifier()
        self._responsable_notifier = ResponsableNotifier()
    
    def verificar_todas(self) -> Dict[str, any]:
        """
        Verifica todas las alertas programadas.
        
        Returns:
            Dict con resumen de alertas generadas
        """
        resultados = {
            'alertas_respuesta': 0,
            'alertas_responsable': 0,
            'alertas_deposito': 0,
            'alertas_documentacion': 0,
            'errores': [],
        }
        
        # Ejecutar todas las verificaciones
        r1 = self.verificar_respuestas_pendientes()
        resultados['alertas_respuesta'] = r1['generadas']
        resultados['errores'].extend(r1['errores'])
        
        r2 = self.verificar_notificacion_responsables()
        resultados['alertas_responsable'] = r2['generadas']
        resultados['errores'].extend(r2['errores'])
        
        r3 = self.verificar_documentacion_pendiente()
        resultados['alertas_documentacion'] = r3['generadas']
        resultados['errores'].extend(r3['errores'])
        
        r4 = self.verificar_depositos_pendientes()
        resultados['alertas_deposito'] = r4['generadas']
        resultados['errores'].extend(r4['errores'])
        
        return resultados
    
    def verificar_respuestas_pendientes(self) -> Dict[str, any]:
        """
        Verifica siniestros esperando respuesta de la aseguradora.
        
        Returns:
            Dict con cantidad generada y errores
        """
        from app.models import Siniestro
        
        resultado = {'generadas': 0, 'errores': []}
        
        siniestros = Siniestro.objects.filter(
            estado='enviado_aseguradora',
            fecha_envio_aseguradora__isnull=False,
            fecha_respuesta_aseguradora__isnull=True,
        )
        
        for siniestro in siniestros:
            if siniestro.alerta_respuesta_aseguradora:
                try:
                    notif = self._broker_notifier.crear_alerta_respuesta(siniestro)
                    if notif:
                        resultado['generadas'] += 1
                except Exception as e:
                    resultado['errores'].append(
                        f"Siniestro {siniestro.numero_siniestro}: {str(e)}"
                    )
        
        return resultado
    
    def verificar_notificacion_responsables(self) -> Dict[str, any]:
        """
        Verifica siniestros que requieren notificar al responsable.
        
        Returns:
            Dict con cantidad generada y errores
        """
        from app.models import Siniestro
        
        resultado = {'generadas': 0, 'errores': []}
        
        siniestros = Siniestro.objects.filter(
            estado__in=['registrado', 'documentacion_pendiente', 'enviado_aseguradora', 'en_evaluacion'],
            fecha_notificacion_responsable__isnull=True,
        )
        
        for siniestro in siniestros:
            if siniestro.alerta_notificar_responsable:
                try:
                    notif = self._responsable_notifier.notificar_siniestro_pendiente(siniestro)
                    if notif:
                        resultado['generadas'] += 1
                except Exception as e:
                    resultado['errores'].append(
                        f"Siniestro {siniestro.numero_siniestro}: {str(e)}"
                    )
        
        return resultado
    
    def verificar_documentacion_pendiente(self) -> Dict[str, any]:
        """
        Verifica siniestros con documentación pendiente (recordatorio cada 8 días).
        
        Returns:
            Dict con cantidad generada y errores
        """
        from app.models import Siniestro
        
        resultado = {'generadas': 0, 'errores': []}
        
        siniestros = Siniestro.objects.filter(estado='documentacion_pendiente')
        
        for siniestro in siniestros:
            dias = siniestro.dias_desde_registro
            # Enviar recordatorio cada 8 días
            if dias > 0 and dias % 8 == 0:
                try:
                    notif = self._responsable_notifier.notificar_documentacion_pendiente(siniestro)
                    if notif:
                        resultado['generadas'] += 1
                except Exception as e:
                    resultado['errores'].append(
                        f"Siniestro {siniestro.numero_siniestro}: {str(e)}"
                    )
        
        return resultado
    
    def verificar_depositos_pendientes(self) -> Dict[str, any]:
        """
        Verifica siniestros con depósito de indemnización pendiente.
        
        Returns:
            Dict con cantidad generada y errores
        """
        from app.models import Siniestro
        
        resultado = {'generadas': 0, 'errores': []}
        
        siniestros = Siniestro.objects.filter(
            fecha_firma_indemnizacion__isnull=False,
            fecha_pago__isnull=True,
        )
        
        for siniestro in siniestros:
            if siniestro.alerta_deposito_pendiente:
                try:
                    notif = self._broker_notifier.crear_alerta_deposito(siniestro)
                    if notif:
                        resultado['generadas'] += 1
                except Exception as e:
                    resultado['errores'].append(
                        f"Siniestro {siniestro.numero_siniestro}: {str(e)}"
                    )
        
        return resultado
