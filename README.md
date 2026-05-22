# BD_tenis3

Aplicación web Flask para tienda de tenis.

## Preparar el repositorio

1. Copia `.env.example` a `.env`.
2. Completa los valores de la base de datos y `SECRET_KEY`.
3. Crea un repositorio en GitHub y sube todo el contenido.

## Dependencias

```bash
python -m pip install -r requirements.txt
```

## Ejecutar localmente

```bash
python index.py
```

## Despliegue en Vercel

1. Crea un repositorio en GitHub con este proyecto.
2. En Vercel, importa el repositorio.
3. Vercel detectará `vercel.json` y usará `@vercel/python` para desplegar la app.
4. Agrega estas variables de entorno en Vercel:
   - `SECRET_KEY`
   - `DATABASE_URL`

   No es necesario usar `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, o `DB_PASS` si ya tienes `DATABASE_URL`.

## Base de datos en Render

- Usa Render solo para crear/gestionar la base de datos PostgreSQL.
- Copia la URL de conexión de Render y pégala en Vercel como `DATABASE_URL`.
- Ejemplo de URL:
  `postgresql://sneaker_point_user:ymMckxB9NtiC4upQpqCewk1NlzhrCQKJ@dpg-d87sb7m7r5hc73f1i9rg-a.oregon-postgres.render.com/sneaker_point`

## Notas importantes

- No subas tu `.env` ni tus credenciales a GitHub.
