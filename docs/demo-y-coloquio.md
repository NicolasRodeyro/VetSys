# Guion de demostración y defensa

## Antes de exponer

Instalar las dependencias y abrir la aplicación al menos una vez con conexión: Flet puede descargar su cliente de escritorio. Usar una base de demostración separada de datos reales. Ejecutar `python scripts/migrar.py` y `python scripts/sembrar.py`, o iniciar la aplicación y elegir «Cargar datos de prueba» cuando lo ofrezca. Completar el campo Operador. Reservar tiempo para comprobar que abre en el equipo que se usará en clase.

El seed contiene a Ana Paz y su mascota Toby, clínicas, veterinarios y el análisis Hemograma. Si se reutiliza una base con operaciones previas, usar identificadores y códigos de conservadora y precinto nuevos, y elegir un turno libre.

## Recorrido 1: recepción aceptada

1. En Turnos, seleccionar un veterinario y Toby, y reservar un horario libre. Mostrar el control de superposición.
2. En Consultas, registrar la atención con el turno, diagnóstico y tratamiento si corresponde. Si aparecen vacunas pendientes, mostrar que advierte y permite continuar. Emitir una orden de Hemograma.
3. En Muestras, seleccionar cliente, mascota, consulta y orden; registrar la extracción. Mostrar el primer evento de trazabilidad.
4. En Conservadoras, crear una de capacidad suficiente con rango 4 a 6 °C, empaquetar la muestra y colocar un precinto único. El rango elegido debe ser compatible con Hemograma.
5. En Remitos, crear uno para la clínica y el laboratorio, agregar la conservadora, cerrar y despachar. Registrar un tramo si se quiere mostrar la cadena de envío.
6. En Recepción, elegir el remito, indicar precinto intacto y temperatura de 5 °C. Mostrar la muestra Recibida y el remito Recibido.
7. En Resultados, registrar por ejemplo Hematocrito 41 %, referencia 37 a 55. Mostrar el aviso en pantalla y el historial de la muestra Analizada.
8. En Comprobantes, cerrar la consulta con honorarios y mostrar los ítems. También se puede cerrar antes del resultado, una vez emitidas las órdenes.
9. En Reportes, generar facturación, explicar que agrupa por meses completos y compara con el mes anterior. El gráfico depende de que haya datos en el rango elegido.

## Recorrido 2: rechazo y reextracción

Crear otra consulta y orden, extraer una muestra y preparar un remito nuevo como en los pasos anteriores. En Recepción indicar **precinto roto** y una temperatura dentro del rango. Mostrar el motivo, el aviso y el estado Rechazada. En Muestras seleccionar la rechazada y usar Reextraer: se crea una muestra nueva asociada a la misma orden. Enviar esa nueva muestra en otra conservadora y remito, recibirla con precinto intacto, registrar resultado y cerrar la consulta. Mostrar que el comprobante cobra una sola orden pese a las dos extracciones y que ambas muestras conservan historiales distintos.

## Preguntas para practicar

**¿Dónde está la regla de una muestra activa?** En `OrdenDerivacion.agregar_muestra()`. Una rechazada deja de estar activa; una analizada sigue activa.

**¿Por qué State?** Cada estado de muestra o remito implementa sus operaciones válidas; las demás fallan. Las entidades delegan, y los estados colaboran cuando un remito se despacha o recibe.

**¿Qué hace Observer?** La muestra notifica cambios. RegistroTrazabilidad agrega eventos; AlertaRechazo y NotificadorCliente generan textos para mostrar. No hay envío externo implementado.

**¿Qué garantiza la trazabilidad?** Cada cambio incluye estado anterior y nuevo, momento, responsable, ubicación, observación y posibles motivos. El historial se expone como tupla y la base prohíbe modificar o borrar eventos y motivos mediante triggers.

**¿Qué hace una transacción?** Los servicios cargan objetos, ejecutan el caso de uso y guardan en una misma conexión; si hay excepción, se revierte la operación.

**¿Por qué Decimal?** Para operar con importes sin errores de representación binaria; se guardan como texto en SQLite.

**¿Qué pruebas hay?** Dominio sin base, integración y servicios con SQLite temporal, lógica de pantallas sin ventana y reportes. Hay recorridos completos feliz y con rechazo. La ejecución automatizada no reemplaza la prueba visual en el equipo de exposición.

**¿Qué reportes hay?** Tiempos de tránsito y procesamiento, tasa de rechazos, vacunas pendientes y facturación por clínica y servicio. Los cuatro se consultan desde la pantalla Reportes. La presencia y preparación de todos los integrantes deben verificarse con el equipo.
