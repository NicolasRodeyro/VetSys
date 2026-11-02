"""Laboratorio central que recibe las muestras de todas las clínicas."""


class Laboratorio:
    def __init__(self, nombre: str, direccion: str) -> None:
        self.id: int | None = None  # lo asigna la persistencia; el dominio no lo usa
        self.nombre = nombre
        self.direccion = direccion
