-- Trazabilidad inmutable: una vez registrado, un cambio de estado de una muestra
-- no se puede modificar ni borrar. Se agrega un renglón nuevo por cada cambio.
-- Los motivos del rechazo forman parte de ese cambio, así que también se protegen.

CREATE TRIGGER cambios_estado_sin_update
BEFORE UPDATE ON cambios_estado
BEGIN
    SELECT RAISE(ABORT, 'La trazabilidad es inmutable: no se puede modificar un cambio de estado');
END;

CREATE TRIGGER cambios_estado_sin_delete
BEFORE DELETE ON cambios_estado
BEGIN
    SELECT RAISE(ABORT, 'La trazabilidad es inmutable: no se puede borrar un cambio de estado');
END;

CREATE TRIGGER cambio_estado_motivos_sin_update
BEFORE UPDATE ON cambio_estado_motivos
BEGIN
    SELECT RAISE(ABORT, 'La trazabilidad es inmutable: no se puede modificar un motivo de rechazo');
END;

CREATE TRIGGER cambio_estado_motivos_sin_delete
BEFORE DELETE ON cambio_estado_motivos
BEGIN
    SELECT RAISE(ABORT, 'La trazabilidad es inmutable: no se puede borrar un motivo de rechazo');
END;
