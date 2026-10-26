## Tarea individual: sistema de tickets y gestión de CMDB con ingeniería asistida por IA

Asignatura: Software Avanzado

Catedrático: Marco Tulio Aldana Prillwitz

Modalidad: individual

Entrega y presentación: miércoles 28 de octubre de 2026, durante el período de clase.

Calificación y defensa individual: miércoles 28 y viernes 30 de octubre de 2026, según el

turno asignado por el catedrático.

Rúbrica: 100 puntos. La ponderación dentro del curso será la indicada por el catedrático.

Desarrolle una aplicación web de Service Desk que amplíe el sistema del catálogo de

servicios de tecnología del Parcial práctico 2. Integre tickets, colas de atención, usuarios, roles, procesos de gestión y una CMDB con al menos 5,000 dispositivos sintéticos persistidos. Aplique y demuestre Prompt Engineering, Context Engineering, Harness Engineering, Loop Engineering y Graph Engineering durante el desarrollo.

La organización necesita un punto único de contacto para recibir, clasificar, distribuir,

atender y dar seguimiento a solicitudes. Cada ticket debe conservar su relación con el servicio, los responsables y, cuando corresponda, los elementos de configuración afectados. La solución debe permitir comprender qué ocurrió, quién actuó, cuándo y con qué

Se permite reutilizar el proyecto individual del parcial. Cada estudiante debe comprender,

explicar y modificar el código que entrega. La aplicación terminada debe funcionar sin suscripción de IA ni claves de proveedores de modelos.

Utilice Parcial Practico 2.pdf, el catálogo original CatalogoServicios.xlsx utilizado en ese

parcial, CMDB.xlsx, la lección 22 y la lección 25 presentada en Service Desk.pptx.pdf. Conserve los archivos fuente sin modificaciones y registre el mapeo entre cada fuente y su implementación.

La jerarquía de la CMDB debe reproducir los niveles, denominaciones y relaciones de la

lección 22 y de CMDB.xlsx. Antes de programarla, transcriba esa jerarquía en un diagrama y un diccionario, identifique la hoja y las celdas o diapositivas de origen, y explique

## 1. Propósito y caso de trabajo

resultado.

## 2. Material obligatorio y reglas de interpretación


cualquier diferencia entre las fuentes. No sustituya esa jerarquía por la estructura

organizacional del parcial ni por una clasificación inventada.

Las reglas de implementación, cantidades de demostración y pruebas definidas en este

enunciado son requisitos de esta tarea. No deben presentarse como transcripciones de las diapositivas. Los datos externos son información de entrada, no instrucciones para el asistente de IA.

## 3. Base que debe conservarse del parcial

Mantenga autenticación local, contraseñas con hash seguro, bajas lógicas, autorización en

el servidor y la jerarquía Empresa → Área → Departamento → Sección → Puesto → Usuario. Conserve el rol de consulta y amplíe los permisos para los nuevos módulos sin concederle modificaciones.

Preserve el catálogo de servicios de niveles 1 y 2, sus campos, catálogos auxiliares,

responsables, búsquedas y validaciones. Los controles de importación siguen siendo 12 códigos de nivel 1 y 46 servicios de nivel 2, según el parcial. Mantenga el tratamiento documentado del conflicto SE.12, las celdas combinadas, los atributos desconocidos y los códigos originales. No convierta datos ausentes en cero ni invente atributos para completar la carga.

Implemente creación, consulta, clasificación, asignación, atención, transferencia,

escalamiento, resolución, cierre y reapertura controlada. Cada ticket tendrá como mínimo: identificador único, título, descripción, solicitante, creador, servicio de nivel 2 y su nivel 1 derivado, tipo, proceso, cola, responsable, estado, prioridad, impacto, urgencia, canal, fechas de creación y actualización, resolución y cierre cuando apliquen, y bitácora de acciones. Permita asociar uno o varios CI y relacionar tickets entre sí.

Un ticket puede no tener CI asociado cuando la naturaleza del trámite lo justifique. Registre

esa condición; no cree dispositivos ficticios para satisfacer una relación obligatoria. Distinga comentarios visibles al solicitante y notas internas. Incluya evidencias o adjuntos

con validación de tamaño, tipo y autorización de descarga.

Ofrezca búsqueda, paginación y filtros por número, servicio, proceso, cola, estado,

prioridad, responsable y fechas. El solicitante debe consultar sus tickets; los agentes, las colas autorizadas; y el administrador, la configuración. Toda modificación relevante debe registrar actor, fecha y valores anteriores y nuevos. No permita eliminar silenciosamente el historial.

## 4. Tickets y trazabilidad


## 5. Colas, roles y asignación

Permita crear, editar y desactivar colas. Cada cola debe configurar exactamente uno de los

siete procesos del apartado siguiente; un proceso puede tener varias colas. Incluya código único, nombre, descripción, estado, proceso, responsables, nivel de soporte, reglas de ordenamiento y objetivos de atención configurables.

Una cola podrá asignarse a roles, usuarios o ambos. Defina permisos separados para

consultar, atender, transferir, aprobar y administrar. Los permisos del rol de consulta no deben elevarse accidentalmente por pertenecer a una cola. Controle la autorización en el servidor.

Documente la política de asignación: manual, automática o mixta. Como mínimo, permita

tomar un ticket y asignarlo a un agente autorizado. Aplique una regla determinista de ordenamiento —por ejemplo, prioridad y luego antigüedad— y evite que dos agentes reclamen simultáneamente el mismo ticket. Registre transferencias, motivos y responsables. No deje tickets huérfanos al desactivar usuarios o colas.

Configure al menos una cola funcional por proceso. Cada flujo debe tener estados,

transiciones, permisos, validaciones, condiciones de entrada y salida y evidencias. No basta con cambiar el nombre del mismo formulario.

- Gestión de nuevos servicios: solicitud, análisis de necesidad y viabilidad, aprobación o rechazo, implementación y cierre. La aprobación debe permitir crear o vincular el servicio del catálogo sin duplicarlo.

- Gestión de cambios: solicitud, evaluación de impacto y riesgo, aprobación o rechazo, planificación, ejecución, validación y cierre. Incluya CI afectados, plan de pruebas y reversión; no permita ejecutar sin aprobación.

- Gestión de incidentes: registro, clasificación, diagnóstico, atención, escalamiento, recuperación, resolución y cierre. Registre interrupción o degradación, categoría I0–I6 y solución aplicada.

- Gestión de eventos: registro, clasificación E0–E3, evaluación y respuesta. Cuando corresponda, genere o vincule un incidente y evite duplicarlo al procesar nuevamente el mismo evento.

- Gestión de problemas: vinculación de incidentes, investigación de causa raíz, solución temporal, error conocido cuando aplique, solución definitiva y cierre. Permita relacionar el cambio que implementa la corrección.

## 6. Siete procesos obligatorios


- Gestión de accesos: solicitud para un usuario beneficiario, recurso o servicio, permiso requerido, aprobación o rechazo, provisión o revocación, validación y cierre. Impida la autoaprobación del solicitante.

- Gestión de servicios de tecnología: solicitud sobre un servicio existente, validación, asignación, cumplimiento, confirmación y cierre. Distíngala de la creación de nuevos servicios y de los incidentes.

## 7. Parámetros de Service Desk de la lección 25

El sistema debe centralizar información, recibir y distribuir solicitudes, apoyar el

escalamiento y ofrecer indicadores de atención. Incluya los tipos de tickets de la diapositiva 14: solicitud de acceso, evento, incidente, solicitud de cambio, requisición de servicio y problema. Relacione los siete procesos de esta tarea con esos tipos mediante un mapeo explícito; «nuevos servicios» puede tratarse como subtipo de requisición de servicio.

Eventos, según la diapositiva 15:

- E0: evento programado; requiere únicamente registro.

- E1: evento no programado sin impacto al servicio en capacidad, disponibilidad o rendimiento; no requiere respuesta operativa, aunque debe conservarse el registro de evaluación.

- E2: evento no programado con impacto al servicio; requiere registro y notificación de incidente.

- E3: evento no programado con impacto en seguridad de la información, con posible impacto al servicio; requiere registro y notificación de incidente.

Para E2 y E3 demuestre la creación o vinculación del incidente y una notificación

verificable en la aplicación o en un canal de prueba. No se requieren correos reales. Incidentes, según los rótulos de la diapositiva 16:

- I0: no causa interrupción.

- I1: 3 horas o menos, incluidas degradaciones.

- I2: 8 horas o menos, incluidas degradaciones.

- I3: 2 días o menos.

- I4: 1 semana o menos.

- I5: 1 mes o más.

- I6: afecta la seguridad de los recursos y la información.


Registre categoría, duración estimada y real cuando se conozcan, prioridad y redundancia

disponible. Preserve las agrupaciones visuales de prioridad y redundancia de la diapositiva mediante una tabla de mapeo documentada. Los rótulos temporales se solapan y dejan casos sin intervalo explícito; no invente una clasificación automática atribuida a la presentación. Defina una regla complementaria para resolver esos casos, identifíquela como decisión del proyecto y pruébela. Las duraciones indicadas no constituyen por sí mismas un SLA de resolución.

La diapositiva 11 muestra niveles 0–4: Autoservicio, Help Desk, Soporte Técnico,

Ingenieros y Externo. Las diapositivas 12–13 describen niveles 0–3 y ubican proveedores en el nivel 3. Documente esa diferencia y adopte un esquema coherente y configurable, con equivalencias y ruta de escalamiento. Los porcentajes 20 %, 70 %, 5 % y 5 % son referencias del material, no cuotas que el sistema deba forzar.

Incluya un portal del solicitante, una base de conocimientos o FAQ para nivel 0, una

consola de agentes y un tablero con tickets por cola, proceso, prioridad y estado; antigüedad; tiempo de primera atención; tiempo de resolución; y cumplimiento de objetivos configurados. Explique cómo calcula cada indicador y cómo trata tickets abiertos, pausas y reaperturas. Declare si los objetivos usan tiempo calendario o hábil.

## 8. CMDB y 5,000 dispositivos

Implemente mantenimiento de la clasificación jerárquica original, dispositivos y relaciones

entre CI. Preserve los atributos y listas presentes en CMDB.xlsx. Cuando agregue campos, diferéncielos de los originales en el diccionario de datos. Como mínimo operativo, cada dispositivo tendrá identificador único, código o etiqueta única, nombre, clasificación, estado, ubicación y responsable; los atributos técnicos dependerán de su clase. No asigne una dirección IP obligatoria a dispositivos que no la requieran.

Vincule CI con servicios y tickets. Permita consultar desde un CI su clasificación completa,

atributos, relaciones, servicios asociados e historial de tickets. Distinga la jerarquía de clasificación de las relaciones técnicas, como «depende de», «conectado a» o «alojado en», cuando sean aplicables.

Entregue un generador reproducible con semilla configurable que inserte al menos 5,000

dispositivos distintos en la base de datos. Las categorías, ubicaciones, usuarios y servicios de referencia deben existir. Distribuya los dispositivos entre las categorías aplicables de la jerarquía y reporte cantidades por nivel y categoría. El total debe contar dispositivos, no filas de catálogos, relaciones, tickets o componentes repetidos.

Conserve integridad referencial, identificadores únicos y atributos sintéticos coherentes con

cada clase. No utilice datos personales reales. Repetir la carga con la misma semilla no


debe duplicar dispositivos; documente si realiza actualización o utiliza un conjunto

identificado. Separe el borrado explícito de datos de prueba del arranque normal.

Incluya búsqueda y filtros paginados sobre los 5,000 dispositivos y una vista de relaciones

navegable. Impida ciclos en la jerarquía de clasificación. Para relaciones técnicas, defina qué tipos admiten ciclos y valide los que no los admiten. Demuestre un recorrido de dependencias para identificar servicios potencialmente afectados por un CI, sin afirmar que una dependencia implica siempre una interrupción efectiva.

## 9. Aplicación verificable de las cuatro ingenierías

Prompt Engineering: entregue al menos ocho prompts realmente utilizados que cubran

requisitos, CMDB, modelo, colas, procesos, seguridad, grafos y pruebas. Registre objetivo, contexto, restricciones, salida esperada, herramienta/modelo disponible, fecha y criterio de aceptación. Muestre al menos dos mejoras comparando instrucción inicial, problema, revisión y resultado comprobado.

Context Engineering: mantenga AGENTS.md o equivalente, glosario, fuentes, modelo,

reglas, decisiones y comandos. Muestre al menos tres actualizaciones justificadas del contexto, con commits. Explique qué contexto proporcionó al asistente en cada fase y cómo evitó mezclar instrucciones con datos externos.

Harness Engineering: entregue comandos automatizados para preparar, migrar, importar

catálogo, generar CMDB, probar y validar. Las comprobaciones deben producir resultados observables y códigos de salida. Incluya datos aislados, controles de secretos y límites de operación. Docker por sí solo no constituye el harness.

Loop Engineering: documente al menos tres ciclos completos de objetivo → propuesta o

cambio → ejecución → evaluación → corrección → nueva verificación. Incluya entradas, resultados reales, criterio de salida, límite de iteraciones e intervención humana. Al menos un ciclo debe corregir un defecto funcional y otro, un problema de datos o permisos. Declare los fallos introducidos deliberadamente.

Las cuatro prácticas deben quedar vinculadas a cambios reales del proyecto. No entregue

conversaciones completas sin selección ni evidencias o resultados inventados.

La tecnología es libre; use una base de datos persistente, preferentemente PostgreSQL,

migraciones y ejecución con Docker Compose. Debe poder construirse desde el repositorio mediante docker compose up --build -d, con comandos adicionales documentados y ejecutados en contenedores. No exija instalar el lenguaje o framework en el equipo anfitrión.

## 10. Arquitectura, ejecución y seguridad


Entregue Dockerfile, compose.yaml, .dockerignore y .env.example sin secretos. Documente

puertos, URL, cuentas de evaluación, preparación de datos, pruebas, logs, apagado y recuperación. Conserve datos al reiniciar sin eliminar volúmenes. Valide datos en el servidor, proteja sesiones y archivos adjuntos y utilice transacciones o control de concurrencia para asignaciones y transiciones críticas.

## 11. Datos de demostración y pruebas mínimas

Prepare al menos siete colas —una por proceso—, usuarios que permitan evaluar

administrador, solicitante, agente y aprobador, y un usuario de consulta. Un usuario puede tener varios roles, respetando las restricciones de aprobación. Entregue al menos 35 tickets, cinco por proceso, en diferentes estados; incluya eventos E0–E3 e incidentes I0–I6 entre esos casos.

Automatice y reporte estos escenarios, además de conservar las comprobaciones relevantes

del parcial:

- P01. Autenticación, cierre de sesión, usuario inactivo y rechazo de operaciones sin permiso.

- P02. Importación repetible del catálogo: controles 12/46 e incidencias conservadas.

- P03. Carga de al menos 5,000 dispositivos únicos y repetición sin duplicados.

- P04. Correspondencia entre jerarquía implementada, Excel y lección 22; rechazo de padres inexistentes y ciclos de clasificación.

- P05. Creación de tickets con referencias válidas y rechazo de referencias inválidas.

- P06. Asignación de una cola a roles y usuarios; acceso permitido y denegado según su política.

- P07. Ordenamiento reproducible y dos agentes intentando tomar el mismo ticket: solo uno obtiene la asignación.

- P08. Transferencia entre colas con historial y validación del proceso destino.

- P09. Ejecución de una ruta completa de cada uno de los siete procesos y rechazo de transiciones inválidas.

- P10. Cambio sin aprobación y acceso autoaprobado: operaciones rechazadas.

- P11. Eventos E0–E3 con respuesta correspondiente; E2/E3 vinculados a incidentes sin duplicarlos.

- P12. Registro I0–I6 y validación de las reglas complementarias de duración, prioridad y redundancia.

- P13. Incidente vinculado a problema y cambio, con trazabilidad recuperable.


- P14. Recorrido CI–servicio y manejo de ciclos según el tipo de relación.

- P15. Cierre sin resolución, reapertura y bitácora: reglas aplicadas y actor registrado.

- P16. Filtros y paginación con 5,000 dispositivos; reporte de tiempos observados y entorno de prueba, sin inventar mediciones.

- P17. Indicadores con datos controlados, incluidas pausas y tickets aún abiertos.

- P18. Reinicio de contenedores sin pérdida de catálogo, CMDB, tickets e historial.

Para cada prueba registre comando, entrada, resultado esperado, resultado obtenido, fecha y

commit. Las pruebas deben aislar sus datos y no destruir el conjunto preparado para evaluación.

## 12. Entregables

Incluya código fuente, migraciones, configuración Docker, archivos originales,

importadores, generador de dispositivos, pruebas y los siguientes documentos:

- README.md: instrucciones exactas desde un clon limpio y cuentas locales de demostración.

- docs/RESOLUCION.md: alcance, arquitectura, decisiones, limitaciones y explicación de la solución.

- docs/MODELO.md: diagrama entidad-relación, diccionario, jerarquía CMDB y mapeo de fuentes.

- docs/PROCESOS.md: tipos, colas, permisos, estados, transiciones, aprobaciones y escalamiento.

- docs/IA.md y evidencias asociadas: prompts, contexto, harness, ciclos y grafos, enlazados a commits.

- docs/PRUEBAS.md: matriz requisito → implementación → prueba → evidencia y resultados reales.

Puede adaptar nombres y carpetas si el README permite localizar cada entregable. No

incluya secretos reales, dependencias instaladas ni archivos .env de trabajo. No se exige comprar servicios, herramientas de IA o infraestructura.

- Integración con catálogo y base del parcial: 8 puntos. Conservación de datos, organización, autenticación y trazabilidad de importación.

- Tickets, colas, roles y asignación: 16 puntos. Operaciones, permisos efectivos, ordenamiento, concurrencia y auditoría.

## 13. Rúbrica de evaluación: 100 puntos


- Siete procesos y parámetros de la lección 25: 18 puntos. Flujos diferenciados, aprobaciones, eventos, incidentes, soporte e indicadores.

- CMDB, jerarquía y 5,000 dispositivos: 16 puntos. Fidelidad a fuentes, generación repetible, integridad, consultas y relaciones.

- Prompt Engineering: 4 puntos. Ocho prompts reales y dos mejoras comprobadas.

- Context Engineering: 4 puntos. Contexto versionado y tres actualizaciones justificadas.

- Harness Engineering: 4 puntos. Preparación y validación automatizadas, observables y reproducibles.

- Loop Engineering: 4 puntos. Tres ciclos con evaluación, corrección y criterio de salida.

- Preguntas aleatorias : 6 puntos.

- Pruebas y seguridad: 10 puntos. Escenarios verificables y protección en el servidor.

- Docker, documentación y defensa individual: 10 puntos. Construcción reproducible, persistencia, acceso y comprensión del código.

Cada criterio recibirá 100 % de sus puntos si está completo y verificable; 75 % por

omisiones menores; 50 % por implementación parcial; 25 % por avances mínimos; 0 % cuando esté ausente o no exista evidencia. Un fallo de arranque no elimina automáticamente los puntos documentales, pero las funciones que no puedan ejecutarse no se considerarán demostradas.

## 14. Presentación y recorrido de calificación

La entrega debe quedar completa el miércoles 28 de octubre de 2026. El viernes 30 es una

segunda jornada de calificación del mismo commit, no una prórroga automática. La hora específica y el orden de defensa serán los del período de clase o los que comunique el catedrático.

Durante la defensa, el estudiante deberá explicar un prompt mejorado, una actualización de

contexto, el harness, un ciclo de corrección y el funcionamiento de ambos grafos.

El catedrático podrá solicitar una modificación pequeña y relacionada con lo entregado para

comprobar comprensión. Las capturas son evidencia complementaria; no sustituyen la ejecución ni la defensa individual.

Aldana Prillwitz, M. T. (2026). ITIL Service Desk: Software Avanzado [Diapositivas de

clase en PDF]. Material proporcionado por el catedrático.

## Referencias


CMDB [Hoja de cálculo de apoyo docente]. (s. f.). Material proporcionado por el

catedrático.

Parcial práctico (25 puntos): Sistema de gestión del catálogo de servicios de TI [Enunciado

de evaluación]. (2026). Software Avanzado. Material proporcionado por el catedrático.

Nota editorial para el catedrático: se revisaron los textos de ambos PDF. No fue posible

verificar el contenido de CMDB.xlsx ni se dispuso de una lección 22 independiente; por eso no se enumeran niveles CMDB no comprobados. Antes de distribuir, adjunte esa lección y confirme la correspondencia de su jerarquía con el Excel. Esta nota no agrega requisitos al estudiante.
