-- Baja lógica de clientes y mascotas: se marcan como inactivos en lugar de borrarse,
-- así sus consultas, muestras y comprobantes conservan a quién pertenecen.

ALTER TABLE clientes ADD COLUMN activo INTEGER NOT NULL DEFAULT 1 CHECK (activo IN (0, 1));
ALTER TABLE mascotas ADD COLUMN activa INTEGER NOT NULL DEFAULT 1 CHECK (activa IN (0, 1));

CREATE INDEX idx_clientes_apellido ON clientes(apellido);
