# WhatsApp: contactos con número oculto (BSUID)

Esta implementación admite textos con teléfono, BSUID o ambos; conserva un `students.id` estable y resuelve cada envío desde la identidad actual de la conversación. La compatibilidad local está verificada con identidades sintéticas y transporte simulado. La validación de entrega real del canal sigue pendiente; aceptar un webhook o recibir un `wamid` no garantiza que el usuario reciba la respuesta.

## Contrato de Meta y contrato de esta aplicación

Referencias oficiales consultadas el 13 de noviembre de 2026: [BSUID y alcance de portfolio](https://developers.facebook.com/documentation/business-messaging/whatsapp/business-scoped-user-ids/), [mensajes de texto](https://developers.facebook.com/documentation/business-messaging/whatsapp/webhooks/reference/messages/text), [eventos system](https://developers.facebook.com/documentation/business-messaging/whatsapp/webhooks/reference/messages/system/) y [envío con BSUID](https://developers.facebook.com/documentation/business-messaging/whatsapp/business-scoped-user-ids/#send-message-requests). Meta puede revisar este contrato; comprobarlo antes del despliegue.

| Dato de entrada | Uso en esta implementación |
| --- | --- |
| `messages[].from` | Teléfono observado del remitente; asociación académica solo si no hay conflicto. Puede faltar. |
| `messages[].from_user_id`, `contacts[].user_id` | BSUID opaco: guardar completo, sin normalización de teléfono. Emparejar contactos por identificadores, nunca por posición en el array. |
| `from_parent_user_id`, `parent_user_id` | Metadatos opcionales; el resolvedor sigue usando el BSUID del portfolio, sin fusionar contactos entre portfolios. |
| `contacts[].profile.username` | Presentación/búsqueda en el panel; nunca clave de identidad o credencial académica. |
| `metadata.phone_number_id` | Número empresarial emisor; no es el WABA ID de `entry[].id` ni el ID de portfolio. |
| `system.user_id`, `system.previous_user_id` | Rotación `user_changed_user_id` o `user_changed_number`; puede llegar sin `from` ni `from_user_id` externos. |
| `system.wa_id` | Ruta opaca tras cambio de número, almacenada aparte; nunca se convierte en teléfono académico, aunque parezca numérica. |

Un texto sin teléfono ni BSUID utilizable se rechaza. Se conservan HMAC, deduplicación por `wamid`, citas y estados. Un contexto de reenvío sin `context.id` es válido. Los estados se correlacionan por ID de mensaje; `failed` puede omitir `contacts` e identificadores de destinatario. Véase la [referencia oficial de estados](https://developers.facebook.com/documentation/business-messaging/whatsapp/webhooks/reference/messages/status).

La aplicación envía exactamente uno de `to` (teléfono o ruta WhatsApp opaca de contingencia) o `recipient` (BSUID actual), con `recipient_type: individual`. Prefiere el BSUID actual cuando existe. Nunca usa el username como destino. Mantiene la versión Graph configurada (`v21.0` por defecto); la comprobación de capacidades reales para esa versión y cuenta queda pendiente.

## Configuración del alcance

Definir `META_BUSINESS_PORTFOLIO_ID` con el ID del portfolio que posee el número empresarial antes de habilitar BSUID. Aplicar los mismos valores en API y todos los workers, junto con `META_PHONE_NUMBER_ID`. No copiar el WABA ID ni el ID del número en este campo. No publicar tokens o secretos en documentación, logs de QA o fixtures.

El alcance persistido es `portfolio:<id>`. Si falta el portfolio, el sistema usa `sender:<phone_number_id>` como contingencia aislada para ese emisor; si tampoco puede identificar al emisor, rechaza textos BSUID sin alcance. La contingencia evita compartir aliases entre emisores, pero no reemplaza la configuración de portfolio para el rollout.

Cambiar después de `sender:*` a `portfolio:*`, cambiar el portfolio o cambiar el emisor **requiere planificar una migración de identidades**. La configuración por sí sola no reescribe los aliases, eventos ni contactos persistidos: podrían aparecer contactos separados y los envíos con alcance/emisor incompatible se bloquearán. Antes de reanudar tráfico, auditar los alcances existentes y preparar una migración transaccional revisada que conserve IDs, aliases históricos y aislamiento, detecte colisiones y actualice las referencias de alcance coherentemente. No hay comando automático para convertir estos datos. Un portfolio compartido no permite a este servicio enviar desde un emisor diferente del observado/configurado.

## Identidad, perfiles y panel

La migración `0024_whatsapp_identities` conserva los IDs de conversaciones, mensajes, etiquetas y relaciones, asigna IDs internos a los alumnos existentes y cambia la relación de conversación a `student_id`. `student_phone` queda nullable como espejo legado. Los aliases históricos permiten encontrar el mismo historial tras una rotación; el destino actual se mantiene por separado.

Un BSUID nuevo puede asociarse a un contacto legado por un teléfono observado sin conflicto. Ante un teléfono o alias ya asociado de forma incompatible, el sistema mantiene historiales separados o rechaza la rotación conflictiva; no fusiona contactos automáticamente. Cuando un BSUID existente observa el teléfono de otro contacto, pierde su asociación académica antes de continuar. Los cambios de número eliminan el vínculo académico previo y los espejos de teléfono; solo una observación posterior de `messages[].from`, sin conflicto y con orden temporal válido, puede establecerlo de nuevo. Eventos repetidos o anteriores no deben restaurar destinos retirados.

BSUID, username, nombre, tarjetas compartidas y `system.wa_id` nunca buscan perfiles o deudas. Los contactos desconocidos pueden consultar información general mediante RAG; sin teléfono asociado seguro se omite el perfil y pagos devuelve su respuesta de falta de datos, sin consultar cuentas por otra identidad. Los trabajos pendientes y envíos manuales resuelven el destinatario actual por conversación; las respuestas personales preparadas con un teléfono que cambió se descartan/rechazan.

El API devuelve `student_id: number`, `student_phone: string | null`, `whatsapp_user_id: string | null` y `whatsapp_username: string | null` en lista y detalle. `StudentRead` usa `id: number` (no `student_id`) y `phone_e164: string | null`; ambos campos WhatsApp tienen valor nulo por defecto en los schemas. `StudentProfile.phone_e164` sigue siendo obligatorio cuando existe un perfil seguro.

El panel conserva su diseño: nombre disponible, teléfono real o etiqueta `WhatsApp ID: …`, y `Contacto #<student_id>` como último recurso. Las iniciales se calculan con nombre/teléfono real o `WA`; nunca se fabrican números a partir del BSUID. La ficha muestra número ausente, BSUID y username por separado. La búsqueda local incluye estos metadatos y los mensajes ya cargados; no reemplaza el filtro de teléfono del API ni busca toda la base.

## Rollout coordinado y recuperación

No desplegar solo el parser, ni mezclar workers/API antiguos con el esquema nuevo: el código antiguo no puede crear conversaciones sin el nuevo `student_id` obligatorio. La compatibilidad de argumentos de tareas antiguas no hace compatible al worker antiguo.

1. Preparar un respaldo restaurable previo a `0024` y registrar conteos/relaciones para comprobar conservación; revisar portfolio/emisor y la migración de alcance si hubo contingencia. Ensayar en base desechable.
2. Pausar productores de tareas (webhook, envíos manuales y productores programados). Permitir que workers antiguos terminen los trabajos en cola, incluidos activos, reservados y diferidos/ETA; verificar que no quedan pendientes ni reintentos que reaparezcan. No purgar tareas sin un registro y una recuperación controlados. Mantener el webhook detenido con una respuesta reintentable/controlada; no confirmar recepción de eventos que no se guardarán.
3. Detener todos los workers y procesos API antiguos. Con productores detenidos y cola drenada, ejecutar `alembic upgrade head` desde `apps/api` contra la base prevista, usando configuración protegida. Comprobar backfill de `student_id`, relaciones y conteos antes de reanudar.
4. Instalar esta misma revisión en API, workers y panel. Arrancar primero los workers nuevos, después el API nuevo, verificar configuración idéntica y solo entonces reanudar productores. Cualquier tarea antigua recuperada debe ejecutarse exclusivamente en workers nuevos que resuelvan el destino actual.
5. Revisar errores de alcance/emisor, conflictos, estados y continuidad del historial. No remediar un conflicto asociando por username o copiando teléfonos desde rutas opacas.

El downgrade a `0023` tiene guardas: rechaza contactos sin teléfono, BSUID actual, rutas opacas, aliases/eventos de identidad o desacuerdos entre teléfono actual y espejo legado. Falla antes de DDL destructivo. Solo un estado exclusivamente telefónico representable permite downgrade; se probó en datos sintéticos. Tras adoptar BSUID, conservar `0024` y usar código compatible, o restaurar un respaldo previo verificado en una parada coordinada, planificando la conservación/reconciliación de datos posteriores. **No borrar identidades, eventos o historiales para forzar downgrade, ni arrancar código antiguo contra `0024`.** Un respaldo previo no contiene las conversaciones creadas después.

## Matriz QA sin envíos reales

Los cuatro casos del [simulador oficial](https://developers.facebook.com/documentation/business-messaging/whatsapp/business-scoped-user-ids/#webhook-testing) se reproducen localmente con fixtures sintéticos y transporte mock. La siguiente tabla es también la lista para una futura sesión autorizada del simulador en un entorno QA aislado; no se ejecutó el App Dashboard en este trabajo.

| Caso del simulador | Payload relevante | Comprobar |
| --- | --- | --- |
| Sin username adoptado | Teléfono + BSUID, sin username | Contacto legado continúa; se conserva teléfono seguro; salida exclusiva y válida. |
| Username con teléfono no disponible | BSUID + username; faltan teléfono/`wa_id` | Entrada válida, contacto estable, RAG general, `recipient` actual y panel sin excepción ni perfil ajeno. |
| Username con teléfono disponible | Teléfono + BSUID + username | Mismo contacto sin conflicto; ambos IDs visibles y perfil solo por teléfono seguro. |
| Parent BSUID presente | BSUID + parent BSUID opcional | Se conserva metadato; destino por BSUID del portfolio; no se mezclan portfolios. |

Además, cubrir teléfono legado sin BSUID; ocultar/reaparecer teléfono; cambios de username; ambas rotaciones `system` sin IDs externos; replay y eventos fuera de orden; dos primeras entradas concurrentes; lotes con orden de contactos distinto; colisiones de teléfono/alias y alcance/emisor distinto; cita cruzada bloqueada; tarea antigua tras rotación; envío manual y automático; perfil/pagos desconocidos; cambio de teléfono mientras se prepara una respuesta personal. Probar `sent`, `delivered`, `read` y `failed` sin contactos, y contexto reenviado sin ID. Las pruebas backend de contrato, identidad, webhook y migración están en `apps/api/tests/test_whatsapp_bsuid_contract.py`, `test_whatsapp_identity.py`, `test_webhook_whatsapp.py` y `test_whatsapp_identity_migration.py`.

## Validación pendiente del canal

En una sesión QA autorizada posterior, comprobar con cuentas reales tanto teléfono visible como oculto: recepción, respuesta automática/manual, aislamiento académico, continuidad tras rotación, `wamid` y acuses de entrega/lectura. Registrar fallos Meta, permisos, ventana de mensajería, versión de API y comportamiento de takeover por separado. Esta implementación no garantiza entrega a todos los usuarios: dependen también del transporte, la cuenta, las políticas del canal y los proveedores. No se desplegó ni se enviaron mensajes reales durante este trabajo.
