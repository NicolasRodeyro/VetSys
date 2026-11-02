"""Clínica de la red veterinaria."""


class Clinica:
    def __init__(self, nombre: str, direccion: str) -> None:
        self.id: int | None = None  # lo asigna la persistencia; el dominio no lo usa
        self.nombre = nombre
        self.direccion = direccion
