# PowerRent

PowerRent es una plataforma de **alquiler de equipos de construcción liviana** (taladros, compactadoras, mezcladoras, cortadoras, generadores portátiles) orientada a reservas en línea.

## Descripción del producto

El sistema permite que un cliente:
- Explore equipos por categoría.
- Consulte disponibilidad en un rango de fechas.
- Cree reservas y realice pagos.

Y permite que un administrador:
- Gestione inventario de equipos y categorías.
- Bloquee equipos por mantenimiento o incidencias.
- Supervise reservas, pagos y ocupación.

## Público objetivo

1. **Contratistas y maestros de obra** que requieren equipos por días o semanas.
2. **Pequeñas empresas de construcción** que necesitan disponibilidad rápida.
3. **Particulares** para proyectos de mejoras del hogar.

## Propuesta de valor

- **Reserva instantánea** con validación de disponibilidad por fechas.
- **Control de mantenimiento** mediante bloqueos de disponibilidad.
- **Gestión unificada de roles** (cliente/administrador) en un solo modelo de usuario.
- **Trazabilidad de pagos y reservas** con estados operativos.

## Arquitectura implementada

- `usuarios`: modelo `Usuario` con roles.
- `equipos`: `Categoria`, `Equipo`, `ImagenEquipo`, `BloqueoDisponibilidad`.
- `reservas`: modelo `Reserva` + `ReservaService`.
- `pagos`: modelo `Pago` + `PagoService`.

## Ejecutar localmente

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py test
python manage.py runserver
```


## Funcionalidades adicionales incorporadas

- Notificaciones asociadas a reserva (confirmación, recordatorio de entrega y devolución).
- Sistema de calificación de equipos tras completar una reserva.

## Qué falta (roadmap sugerido)

- Integrar envío real de notificaciones por email/SMS/WhatsApp.
- Implementar pasarelas reales de Stripe/PayPal (actualmente mocks básicos).
- Crear vistas/API, autenticación JWT y front-end para clientes/admin.
- Dashboard con reportes de ocupación, ingresos y mantenimiento.
