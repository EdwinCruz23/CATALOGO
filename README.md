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

## Despliegue en Render

1. Crea un repositorio en GitHub con este proyecto.
2. En Render, crea un nuevo servicio de tipo `Web Service` y conecta tu repositorio.
3. Usa el `Start Command` `gunicorn index:app` o deja que Render detecte el `Procfile`.
4. Agrega estas variables de entorno en Render:
   - `SECRET_KEY`
   - `DATABASE_URL`

   Si prefieres, puedes seguir usando `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, y `DB_PASS` en lugar de `DATABASE_URL`.

## Notas importantes

- Esta aplicación requiere una base de datos PostgreSQL accesible desde Render.
- Tu URL de base de datos proporcionada debe guardarse en Render como `DATABASE_URL`.
- No subas tu `.env` ni tus credenciales a GitHub.
