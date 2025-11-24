from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from scheduling.models import Cita
from core.models import NotificacionEmail
from django.utils import timezone

class Command(BaseCommand):
    help = 'HU1: Envía recordatorios de citas por email (ejecutar diariamente)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simula el envío sin enviar emails realmente',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        # Buscar citas que necesitan recordatorio
        citas = Cita.objects.filter(
            estado__in=[Cita.Estado.PENDIENTE, Cita.Estado.CONFIRMADA]
        ).select_related('cliente', 'barbero', 'servicio', 'sucursal')
        
        enviados = 0
        errores = 0
        
        for cita in citas:
            if not cita.debe_enviar_recordatorio():
                continue
            
            try:
                # Preparar contexto del email
                context = cita.obtener_datos_email_recordatorio()
                
                # Renderizar templates
                html_message = render_to_string(
                    'emails/recordatorio_cita.html',
                    context
                )
                plain_message = render_to_string(
                    'emails/recordatorio_cita.txt',
                    context
                )
                
                if not dry_run:
                    # Enviar email
                    send_mail(
                        subject=f'Recordatorio: Tu cita en BarberFlow mañana a las {context["hora"]}',
                        message=plain_message,
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[cita.cliente.email],
                        html_message=html_message,
                        fail_silently=False,
                    )
                    
                    # Registrar envío exitoso
                    NotificacionEmail.objects.create(
                        destinatario=cita.cliente,
                        cita=cita,
                        tipo=NotificacionEmail.TipoNotificacion.RECORDATORIO_CITA,
                        asunto=f'Recordatorio: Tu cita mañana',
                        exitoso=True
                    )
                
                enviados += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f'✓ Recordatorio enviado: {cita.cliente.email} (Cita #{cita.id})'
                    )
                )
                
            except Exception as e:
                errores += 1
                
                if not dry_run:
                    # Registrar error
                    NotificacionEmail.objects.create(
                        destinatario=cita.cliente,
                        cita=cita,
                        tipo=NotificacionEmail.TipoNotificacion.RECORDATORIO_CITA,
                        asunto=f'Recordatorio: Tu cita mañana',
                        exitoso=False,
                        error=str(e)
                    )
                
                self.stdout.write(
                    self.style.ERROR(
                        f'✗ Error enviando a {cita.cliente.email}: {str(e)}'
                    )
                )
        
        # Resumen
        modo = "[DRY RUN] " if dry_run else ""
        self.stdout.write(
            self.style.SUCCESS(
                f'\n{modo}Resumen:\n'
                f'  • Emails enviados: {enviados}\n'
                f'  • Errores: {errores}'
            )
        )