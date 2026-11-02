-- Datos de prueba de VetSys. Se carga con:  python scripts/sembrar.py
-- (después de python scripts/migrar.py). No hace falta para usar el sistema.

-- Red de clínicas y laboratorio central
INSERT INTO clinicas (nombre, direccion) VALUES
    ('Clínica Centro', 'Av. Colón 100, Córdoba'),
    ('Clínica Norte', 'Av. Rafael Núñez 4500, Córdoba');

INSERT INTO laboratorios (nombre, direccion) VALUES
    ('Laboratorio Central VetSys', 'Bv. Illia 250, Córdoba');

INSERT INTO veterinarios (matricula, nombre, apellido, clinica_id) VALUES
    ('MP-1001', 'Laura',  'Gómez',   (SELECT id FROM clinicas WHERE nombre = 'Clínica Centro')),
    ('MP-1002', 'Marcos', 'Ruiz',    (SELECT id FROM clinicas WHERE nombre = 'Clínica Centro')),
    ('MP-2001', 'Julia',  'Herrera', (SELECT id FROM clinicas WHERE nombre = 'Clínica Norte')),
    ('MP-2002', 'Andrés', 'Vega',    (SELECT id FROM clinicas WHERE nombre = 'Clínica Norte'));

-- Especies y su esquema de vacunas obligatorias
INSERT INTO especies (nombre) VALUES ('Perro'), ('Gato'), ('Conejo');

INSERT INTO vacunas_obligatorias (especie_id, nombre, edad_aplicacion_meses, refuerzo_cada_meses) VALUES
    ((SELECT id FROM especies WHERE nombre = 'Perro'),  'Sextuple',            2, 12),
    ((SELECT id FROM especies WHERE nombre = 'Perro'),  'Antirrabica',         3, 12),
    ((SELECT id FROM especies WHERE nombre = 'Perro'),  'Tos de las perreras', 6, 12),
    ((SELECT id FROM especies WHERE nombre = 'Gato'),   'Triple felina',       2, 12),
    ((SELECT id FROM especies WHERE nombre = 'Gato'),   'Antirrabica',         3, 12),
    ((SELECT id FROM especies WHERE nombre = 'Gato'),   'Leucemia felina',     3, 12),
    ((SELECT id FROM especies WHERE nombre = 'Conejo'), 'Mixomatosis',         2, 6);

-- Catálogo de análisis (precio en pesos; temperaturas de conservación en °C)
INSERT INTO tipos_analisis (nombre, precio, tipo_muestra, temp_min, temp_max, horas_max_transito) VALUES
    ('Hemograma',          '12500.00', 'Sangre',         2,  8, 24),
    ('Perfil bioquimico',  '18900.00', 'Suero',          2,  8, 48),
    ('Urocultivo',         '9800.50',  'Orina',          2,  8, 24),
    ('Coprocultivo',       '7600.00',  'Materia fecal',  2,  8, 24),
    ('Biopsia',            '35000.00', 'Tejido',        15, 25, 72);

-- Clientes
INSERT INTO clientes (dni, nombre, apellido, telefono, email, direccion) VALUES
    ('30111222', 'Ana',    'Paz',     '351-555-0101', 'ana.paz@mail.com',       'Calle 1 N° 100'),
    ('28444555', 'Luis',   'Gómez',   '351-555-0102', 'luis.gomez@mail.com',    'Bv. San Juan 450'),
    ('33222111', 'Marta',  'Rossi',   '351-555-0103', 'marta.rossi@mail.com',   'Obispo Trejo 22'),
    ('25666777', 'Carlos', 'Díaz',    '351-555-0104', 'carlos.diaz@mail.com',   'Av. Vélez Sarsfield 800'),
    ('31555999', 'Sofía',  'Luna',    '351-555-0105', 'sofia.luna@mail.com',    'Chacabuco 310'),
    ('29888000', 'Jorge',  'Pérez',   '351-555-0106', 'jorge.perez@mail.com',   'Av. Hipólito Yrigoyen 150'),
    ('35111444', 'Laura',  'Ferrari', '351-555-0107', 'laura.ferrari@mail.com', 'Deán Funes 75'),
    ('27333666', 'Pablo',  'Ruiz',    '351-555-0108', 'pablo.ruiz@mail.com',    'Av. Colón 1200'),
    ('32999888', 'Elena',  'Castro',  '351-555-0109', 'elena.castro@mail.com',  'Rondeau 60'),
    ('34000111', 'Diego',  'Molina',  '351-555-0110', 'diego.molina@mail.com',  'Av. Circunvalación 9000');

-- Mascotas (toda mascota tiene su responsable)
INSERT INTO mascotas (cliente_id, especie_id, nombre, sexo, fecha_nacimiento) VALUES
    ((SELECT id FROM clientes WHERE dni = '30111222'), (SELECT id FROM especies WHERE nombre = 'Perro'),  'Toby',   'MACHO', '2025-08-12'),
    ((SELECT id FROM clientes WHERE dni = '30111222'), (SELECT id FROM especies WHERE nombre = 'Gato'),   'Mimi',   'HEMBRA','2024-03-02'),
    ((SELECT id FROM clientes WHERE dni = '28444555'), (SELECT id FROM especies WHERE nombre = 'Perro'),  'Rex',    'MACHO', '2023-05-20'),
    ((SELECT id FROM clientes WHERE dni = '33222111'), (SELECT id FROM especies WHERE nombre = 'Gato'),   'Luna',   'HEMBRA','2026-07-01'),
    ((SELECT id FROM clientes WHERE dni = '25666777'), (SELECT id FROM especies WHERE nombre = 'Perro'),  'Bruno',  'MACHO', '2026-06-15'),
    ((SELECT id FROM clientes WHERE dni = '31555999'), (SELECT id FROM especies WHERE nombre = 'Conejo'), 'Coco',   'HEMBRA','2025-11-30'),
    ((SELECT id FROM clientes WHERE dni = '29888000'), (SELECT id FROM especies WHERE nombre = 'Perro'),  'Nala',   'HEMBRA','2022-01-10'),
    ((SELECT id FROM clientes WHERE dni = '35111444'), (SELECT id FROM especies WHERE nombre = 'Gato'),   'Simba',  'MACHO', '2025-02-14'),
    ((SELECT id FROM clientes WHERE dni = '27333666'), (SELECT id FROM especies WHERE nombre = 'Perro'),  'Kira',   'HEMBRA','2026-03-22'),
    ((SELECT id FROM clientes WHERE dni = '32999888'), (SELECT id FROM especies WHERE nombre = 'Gato'),   'Michi',  'MACHO', '2021-09-09'),
    ((SELECT id FROM clientes WHERE dni = '34000111'), (SELECT id FROM especies WHERE nombre = 'Perro'),  'Thor',   'MACHO', '2024-10-05'),
    ((SELECT id FROM clientes WHERE dni = '34000111'), (SELECT id FROM especies WHERE nombre = 'Conejo'), 'Pelusa', 'HEMBRA','2026-01-20');

-- Una historia clínica por mascota
INSERT INTO historias_clinicas (mascota_id) SELECT id FROM mascotas;

UPDATE historias_clinicas SET alergias = 'Alergia a la penicilina'
    WHERE mascota_id = (SELECT id FROM mascotas WHERE nombre = 'Rex');
UPDATE historias_clinicas SET antecedentes = 'Operada de cadera en 2024'
    WHERE mascota_id = (SELECT id FROM mascotas WHERE nombre = 'Nala');

-- Vacunas ya aplicadas (algunas mascotas al día, otras con refuerzos vencidos o sin vacunar)
INSERT INTO vacunas_aplicadas (historia_id, vacuna_id, fecha)
SELECT h.id, v.id, a.fecha
FROM (
    SELECT 'Toby'  AS mascota, 'Sextuple'    AS vacuna, '2025-10-15' AS fecha UNION ALL
    SELECT 'Toby',             'Antirrabica',            '2025-11-20'          UNION ALL
    SELECT 'Rex',              'Sextuple',               '2026-04-10'          UNION ALL
    SELECT 'Rex',              'Antirrabica',            '2026-04-10'          UNION ALL
    SELECT 'Rex',              'Tos de las perreras',    '2026-04-10'          UNION ALL
    SELECT 'Nala',             'Sextuple',               '2025-01-05'          UNION ALL
    SELECT 'Nala',             'Antirrabica',            '2025-01-05'          UNION ALL
    SELECT 'Mimi',             'Triple felina',          '2026-05-02'          UNION ALL
    SELECT 'Mimi',             'Antirrabica',            '2026-05-02'          UNION ALL
    SELECT 'Mimi',             'Leucemia felina',        '2026-05-02'          UNION ALL
    SELECT 'Simba',            'Triple felina',          '2025-04-20'          UNION ALL
    SELECT 'Thor',             'Sextuple',               '2026-10-01'          UNION ALL
    SELECT 'Thor',             'Antirrabica',            '2026-10-01'          UNION ALL
    SELECT 'Thor',             'Tos de las perreras',    '2026-10-01'
) AS a
JOIN mascotas m ON m.nombre = a.mascota
JOIN historias_clinicas h ON h.mascota_id = m.id
JOIN vacunas_obligatorias v ON v.especie_id = m.especie_id AND v.nombre = a.vacuna;
