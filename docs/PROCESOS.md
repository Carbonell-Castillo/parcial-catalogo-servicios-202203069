# Procesos, colas y permisos

| Proceso | Tipo | Ruta normal | Control |
|---|---|---|---|
| Nuevos servicios | Requisición/nuevo | solicitud→análisis→aprobado→implementación→resuelto→cerrado | necesidad y viabilidad |
| Cambios | Cambio | solicitud→evaluación→aprobado→planificación→ejecución→validación→resuelto→cerrado | riesgo, pruebas y reversión |
| Incidentes | Incidente | registro→clasificación→diagnóstico→atención→escalado→recuperación→resuelto→cerrado | I0–I6 y redundancia |
| Eventos | Evento | registro→clasificación→evaluación→respuesta→resuelto→cerrado | E0–E3; E2/E3 crean incidente una vez |
| Problemas | Problema | registro→investigación→causa raíz→error conocido→solución definitiva→resuelto→cerrado | causa y cambio correctivo |
| Accesos | Acceso | solicitud→aprobado→provisión→validación→resuelto→cerrado | sin autoaprobación |
| Servicios TI | Requisición | solicitud→validación→asignación→cumplimiento→confirmación→resuelto→cerrado | evidencia de cumplimiento |

Asignación mixta. El reclamo usa `UPDATE WHERE responsable_id IS NULL`. Orden: crítica, alta, media, baja y antigüedad. Transferir exige motivo y mismo proceso. No se desactiva una cola con tickets abiertos.

E0 registra, E1 evalúa, E2/E3 notifican incidente. I0–I6 no se infieren: una duración exige justificación manual debido a solapes/huecos. I6 exige seguridad. Duración no es SLA.

Niveles configurables: 0 Autoservicio, 1 Help Desk, 2 Soporte Técnico, 3 Ingenieros/proveedores y 4 Externo. El esquema 0–3 agrupa proveedor en 3. Los porcentajes no son cuotas.

`consulta` sigue sin mutaciones. Roles operativos y permisos de cola son concesiones separadas. Cerrar exige resolución; reabrir conserva actor, motivo, historial y contador.
