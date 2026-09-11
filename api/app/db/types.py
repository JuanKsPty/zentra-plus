"""
Tipos de columna compartidos.

Estan aqui y no repetidos en cada modelo para que la unidad del dinero sea una
decision de un solo sitio: numeric(10,2) en Postgres, Decimal en Python. Nunca
float — y no hace falta el truco de guardar centavos enteros, que existe porque
JavaScript no tiene decimales y Python si.
"""

from sqlalchemy import DateTime, Numeric

# Importes. psycopg devuelve numeric como Decimal de forma nativa.
Dinero = Numeric(10, 2)

# Existencias: tres decimales para poder contar en kilos o litros.
Cantidad = Numeric(12, 3)

# Siempre con zona horaria. Un timestamp sin zona guardado por un proceso en
# UTC y leido por uno en hora local es como se pierde la ultima madrugada de
# un reporte.
TimestampTZ = DateTime(timezone=True)
