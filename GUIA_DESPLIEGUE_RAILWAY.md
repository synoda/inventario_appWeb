# Guía para desplegar StockPro en Railway

## Qué le faltaba al proyecto

1. **No tenía `requirements.txt`**: Railway necesita este archivo para saber qué librerías instalar. Ya está creado con las mismas librerías de tu `.txt` de instrucciones, más `gunicorn` (servidor de producción) y `psycopg2-binary` (por si usas Postgres).
2. **No tenía `Procfile`**: le indica a Railway cómo arrancar la app. El servidor de desarrollo de Flask (`app.run(debug=True)`) **no es apto para producción**. Ahora se usa `gunicorn`.
3. **`SECRET_KEY` fija en el código**: ahora se lee desde una variable de entorno, con el valor anterior como respaldo si no la defines.
4. **La app no escuchaba en el host/puerto correctos**: Railway asigna el puerto dinámicamente a través de la variable `PORT`. Esto solo importa si alguna vez corres `python app.py` directo; con gunicorn no afecta.
5. **Base de datos SQLite**: functiona, pero con una advertencia importante (ver abajo).

## ⚠️ El punto más importante: la base de datos

Tu app usa SQLite (`inventario.db`), un archivo en el disco del contenedor. En Railway, **el sistema de archivos no es persistente entre despliegues** (cada vez que subes cambios o el servicio se reinicia, se crea un contenedor nuevo desde cero). Esto significa:

- La primera vez que arranque, se creará la base de datos y el usuario `admin` automáticamente (tu código ya lo hace).
- Mientras el contenedor siga "vivo" y no se reinicie, los datos que cargues (productos, ventas, etc.) se mantienen.
- Si haces un nuevo deploy o Railway reinicia el servicio, **se pierden los datos** y vuelve a crearse la base vacía con el admin por defecto.

Para una demostración puntual a tu profesor esto normalmente **no es un problema** (no vas a redesplegar en medio de la revisión). Pero si quieres que los datos persistan de verdad, tienes dos opciones:

- **Opción A (más simple, recomendada para tu caso):** no hagas nada más. Despliega tal cual con SQLite. Funciona perfecto para que el profesor entre y navegue la app.
- **Opción B (persistencia real):** agrega el plugin de PostgreSQL de Railway a tu proyecto (gratis dentro del plan de prueba). Railway te da automáticamente una variable `DATABASE_URL`, y el código que ya dejé lista la detecta sola y la usa en vez de SQLite — no tienes que tocar nada más.

## Pasos para desplegar

1. **Sube el proyecto a GitHub** (Railway despliega desde un repo):
   ```
   git init
   git add .
   git commit -m "Preparado para Railway"
   git branch -M main
   git remote add origin <URL_DE_TU_REPO>
   git push -u origin main
   ```
2. **Entra a [railway.com](https://railway.com/)** y crea un cuenta o inicia sesión.
3. **New Project → Deploy from GitHub repo** y selecciona tu repositorio.
4. Railway detectará automáticamente el `Procfile` y `requirements.txt` y hará el build solo.
5. **Configura las variables de entorno** (pestaña *Variables* del servicio):
   - `SECRET_KEY`: cualquier cadena larga y aleatoria (ej. genera una con `python -c "import secrets; print(secrets.token_hex(32))"`).
   - `FLASK_DEBUG`: `0` (para que no corra en modo debug en producción).
   - *(Opcional, Opción B)* Si agregas el plugin de PostgreSQL desde "New" → "Database" → "Add PostgreSQL" dentro del mismo proyecto, Railway crea `DATABASE_URL` automáticamente y la conecta sola al servicio web.
6. **Genera el dominio público**: en la pestaña *Settings* del servicio → *Networking* → *Generate Domain*. Ahí te da la URL pública para compartir con tu profesor.
7. Entra a esa URL, inicia sesión con `admin` / `admin123` (o cambia la contraseña luego desde tu módulo de usuarios).

## Notas adicionales

- Si tu carpeta de `templates/` y `static/` no están en el mismo repo que `app.py`, `forms.py` y `models.py`, asegúrate de subir *todo* el proyecto completo (no solo estos 3 archivos) al repositorio.
- `Flask-Migrate` sigue en el proyecto por si luego quieres usar migraciones formales (`flask db migrate`), pero para el primer despliegue no es necesario: `db.create_all()` ya crea las tablas automáticamente al iniciar.
- Cambia la contraseña de `admin123` después de la evaluación si vas a mantener el proyecto público.
