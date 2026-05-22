from flask import Flask, render_template, request, redirect, url_for, session, send_file, flash
import psycopg2
from psycopg2.extras import RealDictCursor
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import os
from dotenv import load_dotenv
import hashlib
from functools import wraps
import time
import random
import logging

# Configuración básica de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

load_dotenv()

app = Flask(__name__)

# Es vital tener una clave secreta fuerte y única para la sesión
app.secret_key = os.getenv("SECRET_KEY", "un_secreto_muy_largo_y_dificil_de_adivinar_110512") 

# Configuración de la base de datos
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DATABASE_URL = os.getenv("DATABASE_URL")

# ----------------------------------------
#   Función de conexión a PostgreSQL
# ----------------------------------------
def get_conn():
    """Establece y devuelve una conexión a la base de datos PostgreSQL."""
    try:
        if DATABASE_URL:
            return psycopg2.connect(DATABASE_URL)
        return psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASS
        )
    except Exception as e:
        logging.error(f"Error al conectar a la base de datos: {e}")
        # En una aplicación real, se manejaría este error mejor
        raise e

# ----------------------------------------
#   Función de Utilidad para Interacción con DB
# ----------------------------------------
def _db_query(sql, params=None, fetch_one=False, fetch_all=False, commit=False):
    """
    Ejecuta una consulta SQL de forma segura, manejando la conexión y el cursor.
    Retorna los resultados si es una consulta SELECT, o None.
    """
    conn = None
    cur = None
    results = None
    try:
        conn = get_conn()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(sql, params or ())

        if commit:
            conn.commit()
            logging.info("Transacción de DB exitosa.")
        elif fetch_one:
            results = cur.fetchone()
        elif fetch_all:
            results = cur.fetchall()
            
        return results

    except psycopg2.IntegrityError as e:
        if conn: conn.rollback()
        logging.error(f"Error de integridad de datos (IntegrityError): {e}")
        flash("Error de datos: El registro que intentas crear ya existe o faltan datos requeridos.", "error")
        raise e
    except psycopg2.Error as e:
        if conn: conn.rollback()
        logging.error(f"Error de DB general: {e}")
        flash(f"Ocurrió un error en la base de datos. Intenta de nuevo. Detalles: {e}", "error")
        raise e
    except Exception as e:
        if conn: conn.rollback()
        logging.error(f"Error inesperado de DB: {e}")
        flash("Ocurrió un error inesperado. Por favor, contacta a soporte.", "error")
        raise e
    finally:
        if cur: cur.close()
        if conn: conn.close()


def login_required(f):
    """Decorador para asegurar que una ruta solo sea accesible si el usuario ha iniciado sesión."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "loggedin" not in session:
            flash("Debes iniciar sesión primero.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapper


# ======================================================
#                 AUTENTICACIÓN
# ======================================================

@app.route("/login", methods=["GET", "POST"]) 
def login():
    if session.get("loggedin") and request.method == "GET":
        return redirect(url_for("index"))

    if request.method == "POST":
        correo = request.form.get("correo")
        password = request.form.get("contraseña")

        if not correo or not password:


            flash("Por favor, ingresa correo y contraseña.", "error")
            return redirect(url_for("login"))

        # Encriptar la contraseña para compararla con la BD
        hashed_password = hashlib.sha256(password.encode()).hexdigest()

        try:
            cliente = _db_query(
                """
                SELECT id_clientes, nombre, apellido, correo, telefono
                FROM clientes
                WHERE correo = %s AND contraseña = %s
                """,
                (correo, hashed_password),
                fetch_one=True
            )
        except Exception:
            return render_template("login.html") # Redirigir a login si hay un error de DB

        if cliente:
            session["loggedin"] = True
            session["id_cliente"] = cliente["id_clientes"]
            session["nombre_cliente"] = cliente["nombre"]
            session["apellido_cliente"] = cliente["apellido"]
            session["correo_cliente"] = cliente["correo"]
            session["telefono_cliente"] = cliente["telefono"]
            flash(f"¡Bienvenido de nuevo, {cliente['nombre']}!", "success")
            return redirect(url_for("index"))

        flash("Correo o contraseña incorrectos.", "error")

    return render_template("login.html")


@app.route("/registro", methods=["GET", "POST"])
def registro():
    if request.method == "POST":
        
        nombre = request.form.get("nombre")
        apellido = request.form.get("apellido")
        correo = request.form.get("correo")
        password = request.form.get("contraseña")
        telefono = request.form.get("telefono")
        
        # Validaciones básicas
        if not all([nombre, apellido, correo, password, telefono]):
            flash("Todos los campos son obligatorios.", "error")
            return render_template("registro.html")

        hashed_password = hashlib.sha256(password.encode()).hexdigest()

        try:
            _db_query("""
                INSERT INTO clientes (nombre, apellido, correo, contraseña, telefono)
                VALUES (%s, %s, %s, %s, %s)
            """, (nombre, apellido, correo, hashed_password, telefono), commit=True)
            
            flash("¡Registro exitoso! Por favor, inicia sesión.", "success")
            return redirect(url_for("login"))
            
        except psycopg2.IntegrityError:
            flash("El correo ya está registrado o hay un error de integridad de datos.", "error")
        except Exception:
            # El error ya es flasheado por _db_query, solo renderizamos
            pass
            
    return render_template("registro.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("Has cerrado sesión.", "info")
    return redirect(url_for("index"))


@app.route("/actualizar_perfil", methods=["POST"])
@login_required
def actualizar_perfil():
    id_cliente = session.get("id_cliente")
    if not id_cliente:
        flash("Tu sesión expiró. Por favor inicia sesión de nuevo.", "error")
        return redirect(url_for("login"))

    nombre = request.form.get("nombre", "").strip()
    apellido = request.form.get("apellido", "").strip()
    telefono = request.form.get("telefono", "").strip()

    if not nombre or not apellido or not telefono:
        flash("Por favor completa nombre, apellido y teléfono para actualizar tu perfil.", "error")
        return redirect(url_for("index"))

    try:
        _db_query(
            "UPDATE clientes SET nombre = %s, apellido = %s, telefono = %s WHERE id_clientes = %s",
            (nombre, apellido, telefono, id_cliente),
            commit=True,
        )
        session["nombre_cliente"] = nombre
        session["apellido_cliente"] = apellido
        session["telefono_cliente"] = telefono
        session.modified = True
        flash("Perfil actualizado correctamente.", "success")
    except Exception:
        flash("No se pudo actualizar tu perfil. Intenta de nuevo más tarde.", "error")

    return redirect(request.referrer or url_for("index"))

# ======================================================
#                CATÁLOGO PRINCIPAL
# ======================================================

@app.route("/")
@app.route("/index")
def index():
    try:
        productos = _db_query("SELECT * FROM productos ORDER BY nombre", fetch_all=True)
    except Exception:
        productos = [] # Retorna lista vacía en caso de error de DB

    return render_template("index.html", productos=productos)


# ======================================================
#                FUNCIÓN DE BÚSQUEDA POR MARCA
# ======================================================

@app.route('/search')
def search_products():
    query = request.args.get('q', '').strip()
    
    if not query:
        flash('Por favor, ingresa una marca o nombre para buscar.', 'warning')
        return redirect(url_for('index')) 
    
    products = []
    
    try:
        search_term = f"%{query}%"
        
        products = _db_query(
            """
            SELECT *
            FROM productos 
            WHERE marca ILIKE %s OR nombre ILIKE %s
            ORDER BY nombre;
            """, 
            (search_term, search_term), # Buscar por marca O nombre
            fetch_all=True
        )

        if not products:
            flash(f"No se encontraron productos para la búsqueda '{query}'.", 'info')
        else:
            flash(f"Mostrando {len(products)} resultados para la búsqueda '{query}'.", 'success')

    except Exception:
        # El error de DB es flasheado por _db_query
        return redirect(url_for('index'))
            
    return render_template('index.html', productos=products, search_query=query)


# ======================================================
#                    CARRITO
# ======================================================

@app.route("/add_cart", methods=["POST"])
@login_required
def add_cart():
    try:
        # Usar .get() para evitar KeyError si el formulario no envía algo
        product_id_str = request.form.get("id_producto")
        cantidad_str = request.form.get("cantidad")
        talla = request.form.get("talla")
        
        if not product_id_str or not cantidad_str or not talla:
             flash("Error: Asegúrate de seleccionar un producto, talla y cantidad.", "error")
             return redirect(url_for("index"))

        product_id = int(product_id_str)
        cantidad = int(cantidad_str)
        
    except (ValueError, TypeError):
        flash("Error: La cantidad o ID del producto no son válidos.", "error")
        return redirect(url_for("index"))

    # Clave compuesta: id_producto_talla
    cart_key = f"{product_id}_{talla}"
    
    if "cart" not in session:
        session["cart"] = {}

    carrito = session["cart"]
    carrito[cart_key] = carrito.get(cart_key, 0) + cantidad
    
    session.modified = True
    
    flash(f"Producto ID {product_id} (Talla {talla}) agregado al carrito.", "success")
    return redirect(url_for("index"))


@app.route("/carrito")
@login_required
def carrito():
    if "cart" not in session or len(session["cart"]) == 0:
        return render_template("carrito.html", items=[], total=0)

    cart_items = session["cart"]
    product_ids = [k.split('_')[0] for k in cart_items.keys() if '_' in k]
    
    if not product_ids:
        flash("Advertencia: El formato de los productos en el carrito es inválido.", "warning")
        session["cart"] = {} # Limpiar carrito inválido
        session.modified = True
        return render_template("carrito.html", items=[], total=0)

    # Consulta optimizada para obtener todos los productos del carrito en una sola llamada
    placeholders = ', '.join(['%s'] * len(product_ids))
    sql = f"SELECT * FROM productos WHERE id_producto IN ({placeholders})"

    try:
        productos_db = _db_query(sql, tuple(product_ids), fetch_all=True)
    except Exception:
        return render_template("carrito.html", items=[], total=0)
    
    products_map = {p["id_producto"]: p for p in productos_db}

    items = []
    total = 0

    for cart_key, qty in cart_items.items():
        try:
            idp_str, talla = cart_key.split('_')
            idp = int(idp_str)
        except ValueError:
            logging.warning(f"Producto inválido en carrito: {cart_key}")
            continue 

        p = products_map.get(idp)
        
        if p:
            subtotal = p["precio"] * qty
            items.append({"producto": p, "cantidad": qty, "subtotal": subtotal, "talla_seleccionada": talla, "cart_key": cart_key})
            total += subtotal
        else:
            logging.warning(f"Producto con ID {idp} no encontrado en la base de datos, omitido.")

    return render_template("carrito.html", items=items, total=total)


@app.route("/eliminar/<path:cart_key>")
@login_required
def eliminar(cart_key):
    if "cart" in session and cart_key in session["cart"]:
        session["cart"].pop(cart_key)
        session.modified = True 
        flash(f"Producto eliminado del carrito.", "info")
    else:
        flash("Ese producto no se encontró en tu carrito.", "error")

    return redirect(url_for("carrito")) 


# ======================================================
#                 COMPRAR
# ======================================================

@app.route("/comprar", methods=["GET", "POST"])
@login_required
def comprar():
    id_cliente_existente = session.get("id_cliente") 
    
    if not id_cliente_existente:
        flash("Tu sesión expiró. Por favor, vuelve a iniciar sesión.", "error")
        return redirect(url_for("login"))
    
    if "cart" not in session or not session["cart"]:
        flash("Tu carrito está vacío. Agrega productos antes de comprar.", "warning")
        return redirect(url_for("index"))

    if request.method == "GET":
        return render_template("compra.html")

    # Datos del formulario de compra
    codigo_postal = request.form.get("CP", "N/A") 
    calle = request.form.get("calle", "N/A")
    num_ext = request.form.get("num_ext", "S/N")
    num_int = request.form.get("num_int", "")
    metodo_pago = request.form.get("metodo_pago", "Tarjeta/Transferencia")

    referencia_pago = None
    if metodo_pago == "Efectivo":
        # Generar referencia de pago única para OXXO (12 caracteres)
        unique_string = f"{id_cliente_existente}_{time.time()}_{random.randint(1000, 9999)}"
        referencia_pago = hashlib.sha256(unique_string.encode()).hexdigest()[:12].upper()
    
    conn = None
    cur = None
    ticket_items = []
    
    try:
        conn = get_conn()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # 1. Verificar stock e insertar ventas en una transacción única
        for cart_key, qty in session["cart"].items():
            
            try:
                idp_str, talla = cart_key.split('_')
                idp = int(idp_str)
            except ValueError:
                raise ValueError("Error: Producto en carrito con formato inválido.")
                    
            cur.execute("SELECT precio, stock, nombre, marca FROM productos WHERE id_producto = %s", (idp,))
            result = cur.fetchone()

            if not result:
                raise ValueError(f"Error: Producto ID {idp} no encontrado en la base de datos.")
            
            if result["stock"] < qty:
                raise ValueError(f"Stock insuficiente para el producto {result['nombre']} (disponibles: {result['stock']}).")
                            
            precio = result["precio"]
            total_item = precio * qty

            ticket_items.append({
                "id_producto": idp,
                "nombre_producto": result["nombre"],
                "marca": result["marca"],
                "cantidad": qty,
                "talla": talla,
                "precio_unitario": precio,
                "total": total_item
            })

            # Inserción en tabla de ventas
            cur.execute("""
                INSERT INTO ventas (id_producto, id_clientes, cantidad, total, talla, fecha_salida, referencia_pago)
                VALUES (%s, %s, %s, %s, %s, CURRENT_DATE, %s)
            """, (idp, id_cliente_existente, qty, total_item, talla, referencia_pago))

            # Actualización de stock
            cur.execute("""
                UPDATE productos SET stock = stock - %s WHERE id_producto = %s
            """, (qty, idp))

        # 2. Si todo fue exitoso, confirmar la transacción
        conn.commit()
            
    except ValueError as e:
        # Errores de lógica de negocio (stock, formato)
        if conn: conn.rollback()
        flash(f"Error de compra: {e}", "error")
        return redirect(url_for("carrito"))
    except psycopg2.Error as e:
        # Errores de la base de datos
        if conn: conn.rollback()
        logging.error(f"Error crítico en transacción de compra: {e}")
        flash(f"Ocurrió un error al procesar la compra en la base de datos.", "error")
        return redirect(url_for("carrito"))
    except Exception as e:
        # Cualquier otro error inesperado
        if conn: conn.rollback()
        logging.critical(f"Error desconocido en comprar: {e}")
        flash(f"Ocurrió un error inesperado al finalizar la compra.", "error")
        return redirect(url_for("carrito"))
            
    finally:
        if cur: cur.close()
        if conn: conn.close()

    # 3. Limpiar carrito y guardar datos en sesión para el ticket
    session.pop("cart", None)
    
    # Guardar datos del ticket en sesión temporalmente
    session["ticket_data"] = {
        "id_cliente": id_cliente_existente,
        "cp": codigo_postal,
        "calle": calle,
        "num_ext": num_ext,
        "num_int": num_int,
        "metodo_pago": metodo_pago,
        "referencia_pago": referencia_pago,
        "items": ticket_items
    }
    
    if metodo_pago == "Efectivo" and referencia_pago:
        flash(f"¡Compra en proceso! Usa la referencia {referencia_pago} para pagar en OXXO. Tu pedido será procesado al confirmar el pago.", "success")
    else:
        flash("¡Compra realizada con éxito! Generando su ticket.", "success")
    
    return redirect(url_for("descargar_ticket"))


# ======================================================
#                   DESCARGAR TICKET
# ======================================================

@app.route("/descargar_ticket")
@login_required
def descargar_ticket():
    """Retorna una página HTML que descarga el PDF automáticamente y redirige al carrito."""
    # Recuperar datos del ticket desde la sesión
    ticket_data = session.get("ticket_data")
    
    if not ticket_data:
        flash("Error: No se encontraron datos del ticket.", "error")
        return redirect(url_for("carrito"))
    
    return render_template("descargar_ticket.html", ticket_data=ticket_data)


@app.route("/generar_pdf_ticket")
@login_required
def generar_pdf_ticket():
    """Genera y retorna el PDF del ticket."""
    # Recuperar datos del ticket desde la sesión
    ticket_data = session.get("ticket_data")
    
    if not ticket_data:
        flash("Error: No se encontraron datos del ticket.", "error")
        return redirect(url_for("carrito"))
    
    id_cliente = ticket_data["id_cliente"]
    cp = ticket_data["cp"]
    calle = ticket_data["calle"]
    num_ext = ticket_data["num_ext"]
    num_int = ticket_data["num_int"]
    metodo_pago = ticket_data["metodo_pago"]
    referencia_pago = ticket_data["referencia_pago"]

    ventas = ticket_data.get("items", [])
    if not ventas:
        flash("No se encontraron productos para generar el ticket.", "error")
        return redirect(url_for("index"))

    # ======================================================
    #   GENERACIÓN DE PDF
    # ======================================================

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    page_width = letter[0]
    
    # Colores
    COLOR_PRINCIPAL = (0.36, 0.25, 0.62) # Morado oscuro
    COLOR_TEXTO = (0.1, 0.1, 0.1) 
    COLOR_ERROR = (0.7, 0.1, 0.1)

    # Título principal
    titulo_texto = "SNEAKER POINT - Ticket de Compra"
    pdf.setFillColorRGB(*COLOR_PRINCIPAL) 
    pdf.setFont("Times-Bold", 24)
    text_width = pdf.stringWidth(titulo_texto, "Times-Bold", 24)
    x_position = (page_width - text_width) / 2
    pdf.drawString(x_position, 750, titulo_texto)
    
    pdf.setFillColorRGB(*COLOR_TEXTO)
    pdf.setFont("Helvetica", 12)
    y = 720
    
    # Información del cliente y fecha
    pdf.drawString(50, y, f"Cliente: {session.get('nombre_cliente', 'Cliente')}")
    fecha_str = time.strftime('%d/%m/%Y')
    pdf.drawString(300, y, f"Fecha: {fecha_str}")
    y -= 20

    # Datos de Envío y Pago
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(50, y, "Datos de Envío y Pago:")
    y -= 15
    pdf.setFont("Helvetica", 11)

    direccion_completa = f"Calle: {calle}"
    numeros = f"Ext: {num_ext}"
    if num_int:
        numeros += f" Int: {num_int}"
        
    pdf.drawString(50, y, direccion_completa)
    pdf.drawString(300, y, numeros)
    y -= 15
    pdf.drawString(50, y, f"Código Postal: {cp}")
    pdf.drawString(300, y, f"Método de Pago: {metodo_pago}")
    y -= 20
    
    # Referencia de Pago en Efectivo (OXXO)
    if metodo_pago == 'Efectivo' and referencia_pago:
        pdf.setFillColorRGB(*COLOR_ERROR)
        pdf.setFont("Helvetica-Bold", 14)
        pdf.drawString(50, y, "PAGO PENDIENTE (Referencia OXXO):")
        y -= 20
        pdf.setFont("Helvetica-Bold", 20)
        ref_text_width = pdf.stringWidth(referencia_pago, "Helvetica-Bold", 20)
        ref_x_position = (page_width - ref_text_width) / 2
        pdf.drawString(ref_x_position, y, referencia_pago)
        y -= 25
        
        pdf.setFont("Helvetica-Oblique", 10)
        pdf.drawString(50, y, "Instrucción: Utiliza esta referencia numérica para pagar en cualquier caja de OXXO.")
        pdf.drawString(50, y - 12, "El procesamiento de tu pedido comenzará tras la confirmación del pago.")
        y -= 40
        pdf.setFillColorRGB(*COLOR_TEXTO) # Restablecer color de texto
    else:
        y -= 10

    # Encabezados de la tabla de productos
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(40, y, "PRODUCTO")
    pdf.drawString(205, y, "MARCA")
    pdf.drawString(310, y, "TALLA") 
    pdf.drawString(370, y, "CANTIDAD")
    pdf.drawString(490, y, "TOTAL")
    y -= 15
    pdf.line(40, y, 520, y)
    y -= 15

    pdf.setFont("Helvetica", 11)
    subtotal_total = 0

    # Iterar y dibujar los productos vendidos
    for v in ventas: 
        total_str = "{:,.2f}".format(v['total'])
        pdf.drawString(40, y, f"{v['nombre_producto']}")
        pdf.drawString(205, y, f"{v['marca']}")
        pdf.drawString(310, y, f"{v['talla']}") 
        pdf.drawRightString(430, y, f"{v['cantidad']}") # Alinear a la derecha la cantidad
        pdf.drawRightString(520, y, f"${total_str}") # Alinear a la derecha el total
        
        subtotal_total += v["total"]
        y -= 20
        
        if y < 50:
            pdf.showPage()
            pdf.setFont("Helvetica", 12)
            y = 750

    # Total final
    pdf.line(40, y - 10, 520, y - 10)
    pdf.setFont("Times-Bold", 14)
    pdf.setFillColorRGB(*COLOR_PRINCIPAL)
    pdf.drawRightString(390, y - 30, "TOTAL:")
    pdf.drawRightString(520, y - 30, f"${'{:,.2f}'.format(subtotal_total)}")

    pdf.save()
    buffer.seek(0)

    # Enviar el archivo
    return send_file(buffer, as_attachment=True, download_name="ticket.pdf", mimetype="application/pdf")


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5030, debug=True)
