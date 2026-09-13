import customtkinter as ctk
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
from tkcalendar import Calendar
import sqlite3
import datetime
import pandas as pd
import shutil
import os
import calendar
import matplotlib
matplotlib.use('TkAgg')
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# Configuración global del tema
ctk.set_appearance_mode("Light")
ctk.set_default_color_theme("blue")

# --- 1. BASE DE DATOS ---
class BaseDatos:
    def __init__(self, db_name="negocio_final_stock.db"):
        self.db_name = db_name
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()
        self.crear_tablas()
        self.migrar_tablas()

    def crear_tablas(self):
        # Se usa REAL en stock y cantidad para soportar dosis (1/2, 0.5, etc.)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS productos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT UNIQUE,
                precio REAL,
                precio_compra REAL DEFAULT 0.0,
                stock REAL
            )
        """)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS transacciones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha TEXT,
                hora TEXT,
                tipo TEXT,
                producto TEXT,
                cantidad REAL,
                total_dinero REAL,
                encargada TEXT,
                stock_resultante REAL,
                cliente TEXT,
                proveedor TEXT,
                estado TEXT
            )
        """)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS encargadas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT UNIQUE
            )
        """)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS clientes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT UNIQUE,
                documento TEXT,
                telefono TEXT
            )
        """)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS proveedores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT UNIQUE,
                contacto TEXT,
                telefono TEXT
            )
        """)
        self.conn.commit()
        
        # Inserciones por defecto
        self.cursor.execute("SELECT count(*) FROM encargadas")
        if self.cursor.fetchone()[0] == 0:
            self.cursor.execute("INSERT INTO encargadas (nombre) VALUES ('Administradora')")
            
        self.cursor.execute("SELECT count(*) FROM clientes")
        if self.cursor.fetchone()[0] == 0:
            self.cursor.execute("INSERT INTO clientes (nombre, documento, telefono) VALUES ('PÚBLICO GENERAL', '-', '-')")
            
        self.conn.commit()

    def migrar_tablas(self):
        columnas = [
            ("transacciones", "cliente", "TEXT"),
            ("transacciones", "estado", "TEXT"),
            ("transacciones", "proveedor", "TEXT"),
            ("productos", "precio_compra", "REAL DEFAULT 0.0")
        ]
        for tabla, col, tipo in columnas:
            try:
                self.cursor.execute(f"ALTER TABLE {tabla} ADD COLUMN {col} {tipo}")
            except: pass
        self.conn.commit()

    # --- Funciones de Productos ---
    def agregar_producto(self, nombre, precio, precio_compra, stock):
        try:
            self.cursor.execute("INSERT INTO productos (nombre, precio, precio_compra, stock) VALUES (?, ?, ?, ?)", (nombre, precio, precio_compra, stock))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def modificar_producto(self, nombre_actual, nuevo_nombre, nuevo_precio, nuevo_precio_compra, nuevo_stock=None):
        try:
            if nombre_actual != nuevo_nombre:
                self.cursor.execute("UPDATE transacciones SET producto=? WHERE producto=?", (nuevo_nombre, nombre_actual))
            
            if nuevo_stock is not None:
                self.cursor.execute("UPDATE productos SET nombre=?, precio=?, precio_compra=?, stock=? WHERE nombre=?", (nuevo_nombre, nuevo_precio, nuevo_precio_compra, nuevo_stock, nombre_actual))
            else:
                self.cursor.execute("UPDATE productos SET nombre=?, precio=?, precio_compra=? WHERE nombre=?", (nuevo_nombre, nuevo_precio, nuevo_precio_compra, nombre_actual))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        except Exception as e:
            return False

    def eliminar_producto(self, nombre_producto):
        try:
            self.cursor.execute("DELETE FROM productos WHERE nombre=?", (nombre_producto,))
            self.conn.commit()
            return True
        except: return False

    def actualizar_stock_y_obtener_saldo(self, nombre, cantidad, operacion):
        if operacion == "neutro":
            curr = self.cursor.execute("SELECT stock FROM productos WHERE nombre=?", (nombre,))
            res = curr.fetchone()
            return res[0] if res else 0

        curr = self.cursor.execute("SELECT stock FROM productos WHERE nombre=?", (nombre,))
        res = curr.fetchone()
        if res:
            stock_actual = float(res[0])
            if operacion == "sumar": nuevo_stock = stock_actual + cantidad
            else: nuevo_stock = stock_actual - cantidad

            self.cursor.execute("UPDATE productos SET stock=? WHERE nombre=?", (nuevo_stock, nombre))
            self.conn.commit()
            return nuevo_stock
        return None

    # --- Funciones de Transacciones ---
    def registrar_transaccion(self, fecha_manual, tipo, producto, cantidad, total, encargada, stock_final, cliente="", proveedor="", estado="", hora_manual=None):
        hora = hora_manual if hora_manual else datetime.datetime.now().strftime("%H:%M:%S")
        self.cursor.execute("""
            INSERT INTO transacciones (fecha, hora, tipo, producto, cantidad, total_dinero, encargada, stock_resultante, cliente, proveedor, estado)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (str(fecha_manual), hora, tipo, producto, cantidad, total, encargada, stock_final, cliente, proveedor, estado))
        self.conn.commit()

    def pagar_fiado(self, id_transaccion_original):
        cur = self.cursor.execute("SELECT producto, total_dinero, cliente FROM transacciones WHERE id=?", (id_transaccion_original,))
        row = cur.fetchone()
        if not row: return False
        prod, monto, cliente = row
        
        self.cursor.execute("UPDATE transacciones SET estado='PAGADO' WHERE id=?", (id_transaccion_original,))
        fecha_hoy = datetime.date.today().strftime("%Y-%m-%d")
        stock_actual = self.actualizar_stock_y_obtener_saldo(prod, 0, "neutro")
        
        self.registrar_transaccion(fecha_hoy, "COBRO_DEUDA", prod, 1, monto, "Admin", stock_actual, cliente=cliente, estado="COMPLETADO")
        return True

    def eliminar_transaccion_y_reversar_stock(self, id_transaccion):
        cur = self.cursor.execute("SELECT tipo, producto, cantidad FROM transacciones WHERE id=?", (id_transaccion,))
        row = cur.fetchone()
        if not row: return False 
        
        tipo_orig, prod, cant = row
        try:
            if tipo_orig in ["VENTA", "FIADO"]:
                self.cursor.execute("UPDATE productos SET stock = stock + ? WHERE nombre = ?", (cant, prod))
            elif tipo_orig == "ENTRADA":
                self.cursor.execute("UPDATE productos SET stock = stock - ? WHERE nombre = ?", (cant, prod))
            
            self.cursor.execute("DELETE FROM transacciones WHERE id=?", (id_transaccion,))
            self.conn.commit()
            return "OK"
        except Exception: return "ERROR"

    # --- Contactos e Info ---
    def agregar_contacto(self, tipo, nombre, doc_cont, tel):
        tabla = "clientes" if tipo == "cliente" else "proveedores"
        col2 = "documento" if tipo == "cliente" else "contacto"
        try:
            self.cursor.execute(f"INSERT INTO {tabla} (nombre, {col2}, telefono) VALUES (?, ?, ?)", (nombre, doc_cont, tel))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError: return False

    def eliminar_contacto(self, tipo, nombre):
        if nombre == "PÚBLICO GENERAL": return False
        tabla = "clientes" if tipo == "cliente" else "proveedores"
        try:
            self.cursor.execute(f"DELETE FROM {tabla} WHERE nombre=?", (nombre,))
            self.conn.commit()
            return True
        except: return False

    def obtener_contactos(self, tipo):
        tabla = "clientes" if tipo == "cliente" else "proveedores"
        return self.cursor.execute(f"SELECT * FROM {tabla} ORDER BY nombre").fetchall()

    def obtener_nombres_contactos(self, tipo):
        tabla = "clientes" if tipo == "cliente" else "proveedores"
        return [row[0] for row in self.cursor.execute(f"SELECT nombre FROM {tabla} ORDER BY nombre")]

    def obtener_todos_productos(self):
        return self.cursor.execute("SELECT nombre, precio, precio_compra, stock FROM productos ORDER BY nombre").fetchall()
    
    def obtener_lista_nombres_productos(self):
        return [row[0] for row in self.cursor.execute("SELECT nombre FROM productos ORDER BY nombre")]

    def obtener_total_stock_actual(self):
        res = self.cursor.execute("SELECT SUM(stock) FROM productos").fetchone()
        return f"{res[0]:g}" if res[0] else 0
    
    def obtener_deudas_pendientes(self):
        return self.cursor.execute("SELECT id, fecha, cliente, producto, cantidad, total_dinero FROM transacciones WHERE tipo='FIADO' AND estado='PENDIENTE'").fetchall()

    def obtener_datos_raw(self):
        return pd.read_sql_query("SELECT * FROM transacciones", self.conn)

    def agregar_encargada(self, nombre):
        try:
            self.cursor.execute("INSERT INTO encargadas (nombre) VALUES (?)", (nombre,))
            self.conn.commit()
            return True
        except: return False

    def eliminar_encargada(self, nombre_encargada):
        if nombre_encargada == "Administradora": return False 
        try:
            self.cursor.execute("DELETE FROM encargadas WHERE nombre=?", (nombre_encargada,))
            self.conn.commit()
            return True
        except: return False

    def obtener_encargadas(self):
        return [row[0] for row in self.cursor.execute("SELECT nombre FROM encargadas")]


# --- 2. INTERFAZ GRÁFICA (CustomTkinter) ---
class Aplicacion(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Sistema Agro-Negocio Familiar v4.0 Pro")
        self.geometry("1200x800")
        self.db = BaseDatos()
        
        self.carrito_ventas = [] 
        self.carrito_compras = []

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        style = ttk.Style()
        style.theme_use('clam')
        style.configure("Treeview", font=("Segoe UI", 10), rowheight=30, background="#FFFFFF", fieldbackground="#FFFFFF")
        style.configure("Treeview.Heading", font=("Segoe UI", 11, "bold"), background="#E0E0E0")
        
        self.crear_sidebar()
        self.crear_frames_principales()
        
        self.actualizar_combos_personas()
        
        self.seleccionar_frame("ventas")

    def parse_cantidad(self, valor_str):
        valor_str = str(valor_str).strip().replace(',', '.')
        if '/' in valor_str:
            num, den = valor_str.split('/')
            return float(num) / float(den)
        return float(valor_str)

    def crear_sidebar(self):
        self.sidebar_frame = ctk.CTkFrame(self, width=220, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(8, weight=1)

        ctk.CTkLabel(self.sidebar_frame, text="Agro-Negocio", font=ctk.CTkFont(size=22, weight="bold"), text_color="#1F6AA5").grid(row=0, column=0, padx=20, pady=(30, 20))

        ctk.CTkLabel(self.sidebar_frame, text="Encargada:", font=ctk.CTkFont(size=12, weight="bold")).grid(row=1, column=0, padx=20, pady=(10, 0), sticky="w")
        self.combo_encargada = ctk.CTkOptionMenu(self.sidebar_frame, values=["Administradora"])
        self.combo_encargada.grid(row=2, column=0, padx=20, pady=(5, 10))
        self.actualizar_lista_encargadas()

        f_enc_botones = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent")
        f_enc_botones.grid(row=3, column=0, padx=20, pady=(0, 15))
        ctk.CTkButton(f_enc_botones, text="+", width=40, command=self.nueva_encargada).pack(side="left", padx=5)
        ctk.CTkButton(f_enc_botones, text="🗑", width=40, fg_color="#F44336", hover_color="#D32F2F", command=self.borrar_encargada).pack(side="left", padx=5)

        self.btn_ventas = ctk.CTkButton(self.sidebar_frame, text="🛒 Ventas", font=ctk.CTkFont(size=14), height=40, command=lambda: self.seleccionar_frame("ventas"))
        self.btn_ventas.grid(row=4, column=0, padx=20, pady=8)

        self.btn_compras = ctk.CTkButton(self.sidebar_frame, text="🚚 Compras", font=ctk.CTkFont(size=14), height=40, command=lambda: self.seleccionar_frame("compras"))
        self.btn_compras.grid(row=5, column=0, padx=20, pady=8)
        
        self.btn_contactos = ctk.CTkButton(self.sidebar_frame, text="👥 Contactos", font=ctk.CTkFont(size=14), height=40, command=lambda: self.seleccionar_frame("contactos"))
        self.btn_contactos.grid(row=6, column=0, padx=20, pady=8)

        self.btn_fiados = ctk.CTkButton(self.sidebar_frame, text="📒 Fiados", font=ctk.CTkFont(size=14), height=40, command=lambda: self.seleccionar_frame("fiados"))
        self.btn_fiados.grid(row=7, column=0, padx=20, pady=8)

        self.btn_prod = ctk.CTkButton(self.sidebar_frame, text="📝 Inventario", font=ctk.CTkFont(size=14), height=40, command=lambda: self.seleccionar_frame("productos"))
        self.btn_prod.grid(row=8, column=0, padx=20, pady=8, sticky="n")

        self.btn_rep = ctk.CTkButton(self.sidebar_frame, text="📊 Reportes", font=ctk.CTkFont(size=14), height=40, command=lambda: self.seleccionar_frame("reportes"))
        self.btn_rep.grid(row=9, column=0, padx=20, pady=8)

        self.btn_respaldo = ctk.CTkButton(self.sidebar_frame, text="💾 Respaldar BD", fg_color="#4CAF50", hover_color="#388E3C", command=self.respaldar_bd)
        self.btn_respaldo.grid(row=10, column=0, padx=20, pady=(20, 5))

        self.btn_restaurar = ctk.CTkButton(self.sidebar_frame, text="📂 Restaurar BD", fg_color="#FF9800", hover_color="#F57C00", command=self.restaurar_bd)
        self.btn_restaurar.grid(row=11, column=0, padx=20, pady=(5, 20))

    def crear_frames_principales(self):
        self.frames = {}
        for name in ["ventas", "compras", "contactos", "fiados", "productos", "reportes"]:
            f = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
            f.grid(row=0, column=1, sticky="nsew")
            self.frames[name] = f

        self.construir_tab_ventas(self.frames["ventas"])
        self.construir_tab_compras(self.frames["compras"])
        self.construir_tab_contactos(self.frames["contactos"])
        self.construir_tab_fiados(self.frames["fiados"])
        self.construir_tab_productos(self.frames["productos"])
        self.construir_tab_reportes(self.frames["reportes"])

    def seleccionar_frame(self, name):
        for f in self.frames.values():
            f.grid_remove()
        self.frames[name].grid()
        if name == "contactos": self.cargar_tablas_contactos()

    # Utilidad BD
    def respaldar_bd(self):
        fp = filedialog.asksaveasfilename(defaultextension=".db", filetypes=[("SQLite DB", "*.db")], initialfile="Copia_AgroNegocio.db")
        if fp:
            try:
                shutil.copy("negocio_final_stock.db", fp)
                messagebox.showinfo("Éxito", "Copia guardada en:\n" + fp)
            except Exception as e: messagebox.showerror("Error", f"Fallo al respaldar: {e}")

    def restaurar_bd(self):
        fp = filedialog.askopenfilename(filetypes=[("SQLite DB", "*.db")], title="Selecciona el archivo")
        if fp:
            if messagebox.askyesno("⚠️ Advertencia", "Esto reemplazará TODOS los datos actuales.\n¿Continuar?"):
                try:
                    self.db.conn.close()
                    shutil.copy(fp, "negocio_final_stock.db")
                    self.db = BaseDatos()
                    self.actualizar_combos_personas()
                    self.cargar_tabla_productos()
                    self.cargar_fiados()
                    messagebox.showinfo("Éxito", "Base de datos restaurada.")
                except Exception as e: messagebox.showerror("Error", f"Fallo al restaurar: {e}")

    # Utilidad Fecha Reutilizable
    def abrir_calendario_popup(self, entry_widget):
        top = tk.Toplevel(self)
        top.title("Seleccionar Fecha")
        top.geometry("300x300")
        top.grab_set()
        cal = Calendar(top, selectmode='day', date_pattern='yyyy-mm-dd')
        cal.pack(pady=20, expand=True, fill="both")
        def seleccionar():
            entry_widget.configure(state='normal')
            entry_widget.delete(0, tk.END)
            entry_widget.insert(0, cal.get_date())
            entry_widget.configure(state='readonly')
            top.destroy()
        ctk.CTkButton(top, text="Confirmar Fecha", fg_color="#4CAF50", hover_color="#388E3C", command=seleccionar).pack(pady=10)

    # --- PANTALLA: VENTAS ---
    def construir_tab_ventas(self, frame_main):
        frame_main.grid_columnconfigure(0, weight=3)
        frame_main.grid_columnconfigure(1, weight=1)
        frame_main.grid_rowconfigure(0, weight=1)

        f_izq = ctk.CTkFrame(frame_main)
        f_izq.grid(row=0, column=0, padx=15, pady=15, sticky="nsew")

        ctk.CTkLabel(f_izq, text="INVENTARIO (DESPACHO)", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=10)

        f_buscador = ctk.CTkFrame(f_izq, fg_color="transparent")
        f_buscador.pack(fill="x", padx=15, pady=5)
        ctk.CTkLabel(f_buscador, text="🔍 Buscar:").pack(side="left")
        self.ent_buscar_ventas = ctk.CTkEntry(f_buscador)
        self.ent_buscar_ventas.pack(side="left", fill="x", expand=True, padx=10)
        self.ent_buscar_ventas.bind("<KeyRelease>", lambda e: self.cargar_tabla_productos(self.ent_buscar_ventas.get(), target_tree=self.tree_ventas))

        container = ctk.CTkFrame(f_izq)
        container.pack(fill='both', expand=True, padx=15, pady=10)
        scroll_inv = ttk.Scrollbar(container, orient="vertical")
        self.tree_ventas = ttk.Treeview(container, columns=("Producto", "Precio", "Stock"), show="headings", yscrollcommand=scroll_inv.set)
        scroll_inv.config(command=self.tree_ventas.yview)
        
        self.tree_ventas.heading("Producto", text="Producto")
        self.tree_ventas.heading("Precio", text="P. Venta")
        self.tree_ventas.heading("Stock", text="Stock Disp.")
        self.tree_ventas.column("Producto", width=300)
        self.tree_ventas.column("Precio", width=100, anchor="center")
        self.tree_ventas.column("Stock", width=100, anchor="center")
        self.tree_ventas.tag_configure('bajo_stock', foreground='#D32F2F', font=('Segoe UI', 10, 'bold'))

        scroll_inv.pack(side="right", fill="y")
        self.tree_ventas.pack(side="left", fill="both", expand=True)
        self.tree_ventas.bind("<<TreeviewSelect>>", lambda e: self.al_seleccionar_producto(self.tree_ventas, self.lbl_sel_prod_ventas))

        f_acciones = ctk.CTkFrame(frame_main, width=350)
        f_acciones.grid(row=0, column=1, padx=(0, 15), pady=15, sticky="nsew")
        
        ctk.CTkLabel(f_acciones, text="CARRITO DE VENTAS", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(15, 5))

        f_fecha = ctk.CTkFrame(f_acciones, fg_color="transparent")
        f_fecha.pack(fill="x", padx=20, pady=5)
        self.ent_fecha_ventas = ctk.CTkEntry(f_fecha, justify='center')
        self.ent_fecha_ventas.pack(side="left", fill="x", expand=True)
        self.ent_fecha_ventas.insert(0, datetime.date.today().strftime("%Y-%m-%d"))
        self.ent_fecha_ventas.configure(state='readonly')
        ctk.CTkButton(f_fecha, text="📆", width=40, command=lambda: self.abrir_calendario_popup(self.ent_fecha_ventas)).pack(side="right", padx=5)

        self.lbl_sel_prod_ventas = ctk.CTkLabel(f_acciones, text="---", font=ctk.CTkFont(size=14, weight="bold"), text_color="#1F6AA5")
        self.lbl_sel_prod_ventas.pack(anchor="w", padx=20, pady=(10, 0))

        f_cant = ctk.CTkFrame(f_acciones, fg_color="transparent")
        f_cant.pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(f_cant, text="Cant (ej. 1/2):").pack(side="left")
        self.ent_cantidad_ventas = ctk.CTkEntry(f_cant, width=60)
        self.ent_cantidad_ventas.pack(side="left", padx=10)
        ctk.CTkButton(f_cant, text="➕ Agregar", width=100, command=self.agregar_al_carrito_ventas).pack(side="right")

        self.tree_cart_ventas = ttk.Treeview(f_acciones, columns=("Prod", "P.Unit", "Cant", "Subt"), show="headings", height=5)
        self.tree_cart_ventas.heading("Prod", text="Prod"); self.tree_cart_ventas.column("Prod", width=110)
        self.tree_cart_ventas.heading("P.Unit", text="P.Unit"); self.tree_cart_ventas.column("P.Unit", width=60, anchor="center")
        self.tree_cart_ventas.heading("Cant", text="Cant"); self.tree_cart_ventas.column("Cant", width=40, anchor="center")
        self.tree_cart_ventas.heading("Subt", text="Subt"); self.tree_cart_ventas.column("Subt", width=60, anchor="e")
        self.tree_cart_ventas.pack(fill="x", padx=20, pady=5)
        
        self.tree_cart_ventas.bind("<Double-1>", self.editar_celda_carrito_ventas)
        ctk.CTkLabel(f_acciones, text="(Doble clic en Precio, Cantidad o Subtotal para editar)", font=ctk.CTkFont(size=11, slant="italic")).pack()

        self.lbl_total_ventas = ctk.CTkLabel(f_acciones, text="TOTAL: S/. 0.00", font=ctk.CTkFont(size=16, weight="bold"), text_color="#D32F2F")
        self.lbl_total_ventas.pack(anchor="e", padx=20, pady=(0, 5))

        f_botones_cart = ctk.CTkFrame(f_acciones, fg_color="transparent")
        f_botones_cart.pack(fill="x", padx=20, pady=(0, 10))
        ctk.CTkButton(f_botones_cart, text="🗑️ Quitar Item", fg_color="#FF9800", hover_color="#F57C00", command=self.quitar_del_carrito_ventas).pack(side="left", expand=True, padx=(0, 5))
        ctk.CTkButton(f_botones_cart, text="🗑️ Vaciar Todo", fg_color="#F44336", hover_color="#D32F2F", command=lambda: self.vaciar_carrito("ventas")).pack(side="right", expand=True, padx=(5, 0))

        # Selección de Cliente
        ctk.CTkLabel(f_acciones, text="Cliente:").pack(anchor="w", padx=20, pady=(5, 0))
        f_cli = ctk.CTkFrame(f_acciones, fg_color="transparent")
        f_cli.pack(fill="x", padx=20, pady=5)
        self.combo_cliente_venta = ctk.CTkOptionMenu(f_cli, values=["PÚBLICO GENERAL"])
        self.combo_cliente_venta.pack(side="left", fill="x", expand=True)
        ctk.CTkButton(f_cli, text="➕", width=35, command=lambda: self.abrir_popup_contacto("cliente")).pack(side="right", padx=(5, 0))

        ctk.CTkButton(f_acciones, text="💰 FINALIZAR VENTA", fg_color="#4CAF50", hover_color="#388E3C", height=40, font=ctk.CTkFont(weight="bold"), command=lambda: self.procesar_boleta("VENTA")).pack(fill="x", padx=20, pady=(15, 5))
        ctk.CTkButton(f_acciones, text="📒 FINALIZAR FIADO", fg_color="#FFC107", hover_color="#FFA000", text_color="black", height=40, font=ctk.CTkFont(weight="bold"), command=lambda: self.procesar_boleta("FIADO")).pack(fill="x", padx=20, pady=5)

    # --- PANTALLA: COMPRAS ---
    def construir_tab_compras(self, frame_main):
        frame_main.grid_columnconfigure(0, weight=3)
        frame_main.grid_columnconfigure(1, weight=1)
        frame_main.grid_rowconfigure(0, weight=1)

        f_izq = ctk.CTkFrame(frame_main)
        f_izq.grid(row=0, column=0, padx=15, pady=15, sticky="nsew")

        ctk.CTkLabel(f_izq, text="INGRESO DE MERCADERÍA", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=10)

        f_buscador = ctk.CTkFrame(f_izq, fg_color="transparent")
        f_buscador.pack(fill="x", padx=15, pady=5)
        ctk.CTkLabel(f_buscador, text="🔍 Buscar:").pack(side="left")
        self.ent_buscar_compras = ctk.CTkEntry(f_buscador)
        self.ent_buscar_compras.pack(side="left", fill="x", expand=True, padx=10)
        self.ent_buscar_compras.bind("<KeyRelease>", lambda e: self.cargar_tabla_productos(self.ent_buscar_compras.get(), target_tree=self.tree_compras))

        container = ctk.CTkFrame(f_izq)
        container.pack(fill='both', expand=True, padx=15, pady=10)
        scroll_inv = ttk.Scrollbar(container, orient="vertical")
        self.tree_compras = ttk.Treeview(container, columns=("Producto", "P.Compra", "Stock"), show="headings", yscrollcommand=scroll_inv.set)
        scroll_inv.config(command=self.tree_compras.yview)
        
        self.tree_compras.heading("Producto", text="Producto")
        self.tree_compras.heading("P.Compra", text="Costo Ref.")
        self.tree_compras.heading("Stock", text="Stock Actual")
        self.tree_compras.column("Producto", width=300)
        self.tree_compras.column("P.Compra", width=100, anchor="center")
        self.tree_compras.column("Stock", width=100, anchor="center")

        scroll_inv.pack(side="right", fill="y")
        self.tree_compras.pack(side="left", fill="both", expand=True)
        self.tree_compras.bind("<<TreeviewSelect>>", lambda e: self.al_seleccionar_producto(self.tree_compras, self.lbl_sel_prod_compras))

        f_acciones = ctk.CTkFrame(frame_main, width=350)
        f_acciones.grid(row=0, column=1, padx=(0, 15), pady=15, sticky="nsew")
        
        ctk.CTkLabel(f_acciones, text="FACTURA / BOLETA COMPRA", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(15, 5))

        f_fecha = ctk.CTkFrame(f_acciones, fg_color="transparent")
        f_fecha.pack(fill="x", padx=20, pady=5)
        self.ent_fecha_compras = ctk.CTkEntry(f_fecha, justify='center')
        self.ent_fecha_compras.pack(side="left", fill="x", expand=True)
        self.ent_fecha_compras.insert(0, datetime.date.today().strftime("%Y-%m-%d"))
        self.ent_fecha_compras.configure(state='readonly')
        ctk.CTkButton(f_fecha, text="📆", width=40, command=lambda: self.abrir_calendario_popup(self.ent_fecha_compras)).pack(side="right", padx=5)

        self.lbl_sel_prod_compras = ctk.CTkLabel(f_acciones, text="---", font=ctk.CTkFont(size=14, weight="bold"), text_color="#1F6AA5")
        self.lbl_sel_prod_compras.pack(anchor="w", padx=20, pady=(10, 0))

        f_cant = ctk.CTkFrame(f_acciones, fg_color="transparent")
        f_cant.pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(f_cant, text="Cant (ej. 1.5):").pack(side="left")
        self.ent_cantidad_compras = ctk.CTkEntry(f_cant, width=60)
        self.ent_cantidad_compras.pack(side="left", padx=10)
        ctk.CTkButton(f_cant, text="➕ Agregar", width=100, command=self.agregar_al_carrito_compras).pack(side="right")

        self.tree_cart_compras = ttk.Treeview(f_acciones, columns=("Prod", "P.Unit", "Cant", "Subt"), show="headings", height=5)
        self.tree_cart_compras.heading("Prod", text="Prod"); self.tree_cart_compras.column("Prod", width=110)
        self.tree_cart_compras.heading("P.Unit", text="Costo U."); self.tree_cart_compras.column("P.Unit", width=60, anchor="center")
        self.tree_cart_compras.heading("Cant", text="Cant"); self.tree_cart_compras.column("Cant", width=40, anchor="center")
        self.tree_cart_compras.heading("Subt", text="Subt"); self.tree_cart_compras.column("Subt", width=60, anchor="e")
        self.tree_cart_compras.pack(fill="x", padx=20, pady=5)

        # SE AGREGÓ LA INTERACCIÓN DE DOBLE CLIC AQUÍ
        self.tree_cart_compras.bind("<Double-1>", self.editar_celda_carrito_compras)
        ctk.CTkLabel(f_acciones, text="(Doble clic en Precio, Cantidad o Subtotal para editar)", font=ctk.CTkFont(size=11, slant="italic")).pack()

        self.lbl_total_compras = ctk.CTkLabel(f_acciones, text="TOTAL GASTO: S/. 0.00", font=ctk.CTkFont(size=16, weight="bold"), text_color="#2196F3")
        self.lbl_total_compras.pack(anchor="e", padx=20, pady=(0, 5))

        # SE MODIFICÓ LA LISTA DE BOTONES AQUÍ
        f_botones_cart_comp = ctk.CTkFrame(f_acciones, fg_color="transparent")
        f_botones_cart_comp.pack(fill="x", padx=20, pady=(0, 10))
        ctk.CTkButton(f_botones_cart_comp, text="🗑️ Quitar Item", fg_color="#FF9800", hover_color="#F57C00", command=self.quitar_del_carrito_compras).pack(side="left", expand=True, padx=(0, 5))
        ctk.CTkButton(f_botones_cart_comp, text="🗑️ Vaciar Todo", fg_color="#F44336", hover_color="#D32F2F", command=lambda: self.vaciar_carrito("compras")).pack(side="right", expand=True, padx=(5, 0))

        # Selección de Proveedor
        ctk.CTkLabel(f_acciones, text="Proveedor:").pack(anchor="w", padx=20, pady=(15, 0))
        f_prov = ctk.CTkFrame(f_acciones, fg_color="transparent")
        f_prov.pack(fill="x", padx=20, pady=5)
        self.combo_proveedor_compra = ctk.CTkOptionMenu(f_prov, values=[])
        self.combo_proveedor_compra.pack(side="left", fill="x", expand=True)
        ctk.CTkButton(f_prov, text="➕", width=35, command=lambda: self.abrir_popup_contacto("proveedor")).pack(side="right", padx=(5, 0))

        ctk.CTkButton(f_acciones, text="🚚 PROCESAR ENTRADA", fg_color="#2196F3", hover_color="#1976D2", height=40, font=ctk.CTkFont(weight="bold"), command=self.procesar_boleta_compra).pack(fill="x", padx=20, pady=(20, 5))

    # --- PANTALLA: CONTACTOS (Clientes y Proveedores) ---
    def construir_tab_contactos(self, frame):
        ctk.CTkLabel(frame, text="DIRECTORIO DE CONTACTOS", font=ctk.CTkFont(size=20, weight="bold")).pack(pady=15)
        
        self.tab_contactos = ctk.CTkTabview(frame)
        self.tab_contactos.pack(fill="both", expand=True, padx=30, pady=10)
        
        t_cli = self.tab_contactos.add("👥 Clientes")
        t_prov = self.tab_contactos.add("🏭 Proveedores")

        # Tab Clientes
        f_form_cli = ctk.CTkFrame(t_cli, fg_color="transparent")
        f_form_cli.pack(fill="x", pady=10)
        ctk.CTkLabel(f_form_cli, text="Nombre:").pack(side="left", padx=5)
        self.ent_cli_nom = ctk.CTkEntry(f_form_cli, width=200); self.ent_cli_nom.pack(side="left", padx=5)
        ctk.CTkLabel(f_form_cli, text="DNI/RUC:").pack(side="left", padx=5)
        self.ent_cli_doc = ctk.CTkEntry(f_form_cli, width=120); self.ent_cli_doc.pack(side="left", padx=5)
        ctk.CTkLabel(f_form_cli, text="Teléfono:").pack(side="left", padx=5)
        self.ent_cli_tel = ctk.CTkEntry(f_form_cli, width=120); self.ent_cli_tel.pack(side="left", padx=5)
        ctk.CTkButton(f_form_cli, text="Guardar", command=lambda: self.guardar_contacto("cliente")).pack(side="left", padx=20)
        ctk.CTkButton(f_form_cli, text="🗑️ Borrar", fg_color="#F44336", command=lambda: self.borrar_contacto("cliente")).pack(side="left", padx=5)

        self.tree_clientes = ttk.Treeview(t_cli, columns=("ID", "Nombre", "Documento", "Teléfono"), show="headings")
        self.tree_clientes.heading("Nombre", text="Nombre"); self.tree_clientes.column("Nombre", width=300)
        self.tree_clientes.heading("Documento", text="DNI/RUC"); self.tree_clientes.column("Documento", width=150)
        self.tree_clientes.heading("Teléfono", text="Teléfono"); self.tree_clientes.column("Teléfono", width=150)
        self.tree_clientes.column("ID", width=0, stretch=tk.NO)
        self.tree_clientes.pack(fill="both", expand=True, pady=10)

        # Tab Proveedores
        f_form_prov = ctk.CTkFrame(t_prov, fg_color="transparent")
        f_form_prov.pack(fill="x", pady=10)
        ctk.CTkLabel(f_form_prov, text="Empresa/Nombre:").pack(side="left", padx=5)
        self.ent_prov_nom = ctk.CTkEntry(f_form_prov, width=200); self.ent_prov_nom.pack(side="left", padx=5)
        ctk.CTkLabel(f_form_prov, text="Contacto (Persona):").pack(side="left", padx=5)
        self.ent_prov_doc = ctk.CTkEntry(f_form_prov, width=150); self.ent_prov_doc.pack(side="left", padx=5)
        ctk.CTkLabel(f_form_prov, text="Teléfono:").pack(side="left", padx=5)
        self.ent_prov_tel = ctk.CTkEntry(f_form_prov, width=120); self.ent_prov_tel.pack(side="left", padx=5)
        ctk.CTkButton(f_form_prov, text="Guardar", command=lambda: self.guardar_contacto("proveedor")).pack(side="left", padx=20)
        ctk.CTkButton(f_form_prov, text="🗑️ Borrar", fg_color="#F44336", command=lambda: self.borrar_contacto("proveedor")).pack(side="left", padx=5)

        self.tree_proveedores = ttk.Treeview(t_prov, columns=("ID", "Nombre", "Contacto", "Teléfono"), show="headings")
        self.tree_proveedores.heading("Nombre", text="Empresa/Nombre"); self.tree_proveedores.column("Nombre", width=300)
        self.tree_proveedores.heading("Contacto", text="Contacto Vendedor"); self.tree_proveedores.column("Contacto", width=200)
        self.tree_proveedores.heading("Teléfono", text="Teléfono"); self.tree_proveedores.column("Teléfono", width=150)
        self.tree_proveedores.column("ID", width=0, stretch=tk.NO)
        self.tree_proveedores.pack(fill="both", expand=True, pady=10)

    # --- PANTALLA: FIADOS ---
    def construir_tab_fiados(self, frame):
        ctk.CTkLabel(frame, text="CUENTAS POR COBRAR (FIADOS)", font=ctk.CTkFont(size=20, weight="bold"), text_color="#D32F2F").pack(pady=20)
        
        container = ctk.CTkFrame(frame)
        container.pack(fill="both", expand=True, padx=30, pady=10)
        
        self.tree_fiados = ttk.Treeview(container, columns=("ID", "Fecha", "Cliente", "Producto", "Cantidad", "Monto"), show="headings", height=15)
        self.tree_fiados.heading("ID", text="ID"); self.tree_fiados.column("ID", width=0, stretch=tk.NO)
        self.tree_fiados.heading("Fecha", text="Fecha"); self.tree_fiados.column("Fecha", width=100)
        self.tree_fiados.heading("Cliente", text="Cliente"); self.tree_fiados.column("Cliente", width=200)
        self.tree_fiados.heading("Producto", text="Producto"); self.tree_fiados.column("Producto", width=200)
        self.tree_fiados.heading("Cantidad", text="Cant."); self.tree_fiados.column("Cantidad", width=80, anchor="center")
        self.tree_fiados.heading("Monto", text="Deuda Total"); self.tree_fiados.column("Monto", width=100, anchor="e")
        
        scroll = ttk.Scrollbar(container, orient="vertical", command=self.tree_fiados.yview)
        scroll.pack(side="right", fill="y")
        self.tree_fiados.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        self.tree_fiados.configure(yscrollcommand=scroll.set)

        self.tree_fiados.bind("<Double-1>", self.ver_historial_cliente)

        btn_frame = ctk.CTkFrame(frame, fg_color="transparent")
        btn_frame.pack(pady=20)
        ctk.CTkButton(btn_frame, text="🔄 Actualizar", command=self.cargar_fiados).pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="✅ REGISTRAR PAGO", fg_color="#4CAF50", hover_color="#388E3C", height=40, font=ctk.CTkFont(weight="bold"), command=self.cobrar_deuda).pack(side="left", padx=10)
        ctk.CTkLabel(btn_frame, text="(Doble clic en un cliente para ver detalles)", font=ctk.CTkFont(size=12, slant="italic")).pack(side="left", padx=20)
        
        self.cargar_fiados()

    def ver_historial_cliente(self, event):
        sel = self.tree_fiados.selection()
        if not sel: return
        cliente = self.tree_fiados.item(sel[0])['values'][2]

        top = ctk.CTkToplevel(self)
        top.title(f"Historial de Deudas - {cliente}")
        top.geometry("600x400")
        top.grab_set()

        ctk.CTkLabel(top, text=f"Desglose de deuda: {cliente}", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=15)

        cols = ("Fecha", "Producto", "Cantidad", "Subtotal")
        tree_hist = ttk.Treeview(top, columns=cols, show="headings")
        for col in cols: tree_hist.heading(col, text=col)
        tree_hist.column("Fecha", width=100); tree_hist.column("Producto", width=250)
        tree_hist.column("Cantidad", width=80, anchor="center"); tree_hist.column("Subtotal", width=100, anchor="e")

        scroll = ttk.Scrollbar(top, orient="vertical", command=tree_hist.yview)
        scroll.pack(side="right", fill="y"); tree_hist.pack(side="left", fill="both", expand=True, padx=15, pady=10)
        tree_hist.configure(yscrollcommand=scroll.set)

        df = self.db.obtener_datos_raw()
        if not df.empty:
            historial = df[(df['cliente'] == cliente) & (df['tipo'] == 'FIADO') & (df['estado'] == 'PENDIENTE')]
            for _, row in historial.iterrows():
                tree_hist.insert("", "end", values=(row['fecha'], row['producto'], f"{row['cantidad']:g}", f"S/. {row['total_dinero']:.2f}"))
        ctk.CTkButton(top, text="Cerrar", command=top.destroy).pack(pady=10)

    # --- PANTALLA: INVENTARIO (PRODUCTOS) ---
    def construir_tab_productos(self, frame):
        f_crear = ctk.CTkFrame(frame)
        f_crear.pack(fill="x", padx=30, pady=(30, 10))
        ctk.CTkLabel(f_crear, text="CREAR NUEVO PRODUCTO", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(15, 10))
        
        f_campos = ctk.CTkFrame(f_crear, fg_color="transparent")
        f_campos.pack(pady=10)
        ctk.CTkLabel(f_campos, text="Nombre:").grid(row=0, column=0, padx=5)
        self.e_new_nom = ctk.CTkEntry(f_campos, width=160); self.e_new_nom.grid(row=0, column=1, padx=5)
        
        ctk.CTkLabel(f_campos, text="P. Venta:").grid(row=0, column=2, padx=5)
        self.e_new_prec = ctk.CTkEntry(f_campos, width=70); self.e_new_prec.grid(row=0, column=3, padx=5)
        
        ctk.CTkLabel(f_campos, text="P. Compra (Costo):").grid(row=0, column=4, padx=5)
        self.e_new_prec_comp = ctk.CTkEntry(f_campos, width=70); self.e_new_prec_comp.grid(row=0, column=5, padx=5)
        
        ctk.CTkLabel(f_campos, text="Stock Inicial:").grid(row=0, column=6, padx=5)
        self.e_new_stk = ctk.CTkEntry(f_campos, width=70); self.e_new_stk.grid(row=0, column=7, padx=5)
        
        ctk.CTkButton(f_campos, text="Guardar", fg_color="#2196F3", width=80, command=self.crear_producto).grid(row=0, column=8, padx=20)

        f_edit = ctk.CTkFrame(frame)
        f_edit.pack(fill="x", padx=30, pady=10)
        ctk.CTkLabel(f_edit, text="GESTIÓN DE PRODUCTOS EXISTENTES", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(15, 10))
        
        f_campos_edit = ctk.CTkFrame(f_edit, fg_color="transparent")
        f_campos_edit.pack(pady=10)
        
        ctk.CTkLabel(f_campos_edit, text="Seleccione:").grid(row=0, column=0, padx=5)
        self.combo_edit_prod = ctk.CTkOptionMenu(f_campos_edit, values=[], width=140, command=self.al_seleccionar_producto_editar)
        self.combo_edit_prod.grid(row=0, column=1, padx=5)
        
        ctk.CTkLabel(f_campos_edit, text="Nombre:").grid(row=0, column=2, padx=5)
        self.e_edit_nom = ctk.CTkEntry(f_campos_edit, width=120); self.e_edit_nom.grid(row=0, column=3, padx=5)
        
        ctk.CTkLabel(f_campos_edit, text="P. Venta:").grid(row=0, column=4, padx=5)
        self.e_edit_prec = ctk.CTkEntry(f_campos_edit, width=60); self.e_edit_prec.grid(row=0, column=5, padx=5)
        
        ctk.CTkLabel(f_campos_edit, text="P. Compra:").grid(row=0, column=6, padx=5)
        self.e_edit_prec_comp = ctk.CTkEntry(f_campos_edit, width=60); self.e_edit_prec_comp.grid(row=0, column=7, padx=5)
        
        ctk.CTkLabel(f_campos_edit, text="Stock:").grid(row=0, column=8, padx=5)
        self.e_edit_stk = ctk.CTkEntry(f_campos_edit, width=60); self.e_edit_stk.grid(row=0, column=9, padx=5)
        
        ctk.CTkButton(f_campos_edit, text="Actualizar", fg_color="#FF9800", hover_color="#F57C00", width=80, command=self.actualizar_producto).grid(row=0, column=10, padx=10)
        ctk.CTkButton(f_campos_edit, text="🗑️", fg_color="#D32F2F", hover_color="#C62828", width=40, command=self.borrar_producto).grid(row=0, column=11, padx=5)

        f_lista = ctk.CTkFrame(frame)
        f_lista.pack(fill="both", expand=True, padx=30, pady=(10, 30))
        ctk.CTkLabel(f_lista, text="LISTA COMPLETA: PRECIOS Y STOCK ACTUALIZADO", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=10)
        
        self.tree_precios = ttk.Treeview(f_lista, columns=("Producto", "Stock", "P. Venta", "P. Compra Unit."), show="headings")
        self.tree_precios.heading("Producto", text="Producto"); self.tree_precios.column("Producto", width=300)
        self.tree_precios.heading("Stock", text="Stock Actual"); self.tree_precios.column("Stock", width=100, anchor="center")
        self.tree_precios.heading("P. Venta", text="Precio Venta"); self.tree_precios.column("P. Venta", width=150, anchor="center")
        self.tree_precios.heading("P. Compra Unit.", text="Costo Unit. Compra"); self.tree_precios.column("P. Compra Unit.", width=150, anchor="center")
        
        scroll_precios = ttk.Scrollbar(f_lista, orient="vertical", command=self.tree_precios.yview)
        scroll_precios.pack(side="right", fill="y"); self.tree_precios.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        self.tree_precios.configure(yscrollcommand=scroll_precios.set)
        
        self.tree_precios.bind("<<TreeviewSelect>>", self.al_seleccionar_producto_tabla_editar)

        self.actualizar_combo_productos()
        self.cargar_tabla_productos()

    # --- PANTALLA: REPORTES ---
    def construir_tab_reportes(self, frame):
        f_filtro = ctk.CTkFrame(frame)
        f_filtro.pack(fill="x", padx=20, pady=10)

        ctk.CTkLabel(f_filtro, text="Mes/Año:").pack(side="left", padx=5)
        meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
        self.combo_mes = ctk.CTkOptionMenu(f_filtro, values=meses, width=100, command=self.actualizar_dias)
        self.combo_mes.set(meses[datetime.datetime.now().month - 1]); self.combo_mes.pack(side="left", padx=2)
        anios = [str(x) for x in range(2024, 2031)]
        self.combo_anio = ctk.CTkOptionMenu(f_filtro, values=anios, width=80, command=self.actualizar_dias)
        self.combo_anio.set(str(datetime.datetime.now().year)); self.combo_anio.pack(side="left", padx=2)
        ctk.CTkLabel(f_filtro, text="Día:").pack(side="left", padx=5)
        self.combo_dia = ctk.CTkOptionMenu(f_filtro, values=["Todos"], width=70); self.combo_dia.pack(side="left", padx=2)
        self.actualizar_dias()

        ctk.CTkLabel(f_filtro, text=" | ").pack(side="left", padx=5)
        
        ctk.CTkLabel(f_filtro, text="Cliente:").pack(side="left", padx=2)
        self.combo_rep_cli = ctk.CTkOptionMenu(f_filtro, values=["Todos"], width=120)
        self.combo_rep_cli.pack(side="left", padx=2)
        
        ctk.CTkLabel(f_filtro, text="Proveedor:").pack(side="left", padx=2)
        self.combo_rep_prov = ctk.CTkOptionMenu(f_filtro, values=["Todos"], width=120)
        self.combo_rep_prov.pack(side="left", padx=2)

        ctk.CTkButton(f_filtro, text="🔎 CONSULTAR", fg_color="#673AB7", command=self.generar_reporte_mensual).pack(side="right", padx=10)

        f_cards = ctk.CTkFrame(frame, fg_color="transparent")
        f_cards.pack(fill="x", padx=20, pady=5)
        
        self.card_ventas = ctk.CTkLabel(f_cards, text="INGRESOS (Caja)\nS/. 0.00", font=ctk.CTkFont(size=14, weight="bold"), fg_color="#C8E6C9", text_color="black", width=200, height=60, corner_radius=8)
        self.card_ventas.pack(side="left", padx=5, expand=True)
        self.card_gastos = ctk.CTkLabel(f_cards, text="COMPRAS\nS/. 0.00", font=ctk.CTkFont(size=14, weight="bold"), fg_color="#FFCCBC", text_color="black", width=200, height=60, corner_radius=8)
        self.card_gastos.pack(side="left", padx=5, expand=True)
        self.card_ganancia = ctk.CTkLabel(f_cards, text="CAJA REAL\nS/. 0.00", font=ctk.CTkFont(size=14, weight="bold"), fg_color="#BBDEFB", text_color="black", width=200, height=60, corner_radius=8)
        self.card_ganancia.pack(side="left", padx=5, expand=True)
        self.card_fiados = ctk.CTkLabel(f_cards, text="POR COBRAR\nS/. 0.00", font=ctk.CTkFont(size=14, weight="bold"), fg_color="#FFF9C4", text_color="black", width=200, height=60, corner_radius=8)
        self.card_fiados.pack(side="left", padx=5, expand=True)
        self.card_stock_total = ctk.CTkLabel(f_cards, text="STOCK TOTAL\n0", font=ctk.CTkFont(size=14, weight="bold"), fg_color="#E0E0E0", text_color="black", width=150, height=60, corner_radius=8)
        self.card_stock_total.pack(side="left", padx=5, expand=True)

        f_mid = ctk.CTkFrame(frame, fg_color="transparent")
        f_mid.pack(fill="x", padx=20, pady=(15, 0))
        f_mid.grid_columnconfigure(0, weight=1); f_mid.grid_columnconfigure(1, weight=1)

        container1 = ctk.CTkFrame(f_mid, height=180)
        container1.grid(row=0, column=0, sticky="nsew", padx=(0, 5)); container1.pack_propagate(False)
        ctk.CTkLabel(container1, text="RESUMEN DE STOCK:", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=10, pady=(5, 0))
        self.tree_resumen_prod = ttk.Treeview(container1, columns=("Producto", "Ventas", "Compras", "Cierre"), show="headings")
        self.tree_resumen_prod.heading("Producto", text="Producto"); self.tree_resumen_prod.column("Producto", width=180)
        self.tree_resumen_prod.heading("Ventas", text="Salidas"); self.tree_resumen_prod.column("Ventas", width=70, anchor="center")
        self.tree_resumen_prod.heading("Compras", text="Entradas"); self.tree_resumen_prod.column("Compras", width=70, anchor="center")
        self.tree_resumen_prod.heading("Cierre", text="Stock Cierre"); self.tree_resumen_prod.column("Cierre", width=80, anchor="center")
        scroll_prod = ttk.Scrollbar(container1, orient="vertical", command=self.tree_resumen_prod.yview)
        scroll_prod.pack(side="right", fill="y"); self.tree_resumen_prod.pack(side="left", fill="both", expand=True)

        self.f_grafico = ctk.CTkFrame(f_mid, height=180)
        self.f_grafico.grid(row=0, column=1, sticky="nsew", padx=(5, 0)); self.f_grafico.pack_propagate(False)
        self.canvas_grafico = None

        f_toolbar = ctk.CTkFrame(frame, fg_color="transparent")
        f_toolbar.pack(fill="x", padx=20, pady=(15, 0))
        ctk.CTkLabel(f_toolbar, text="DETALLE CRONOLÓGICO:", font=ctk.CTkFont(size=14, weight="bold")).pack(side="left")
        ctk.CTkButton(f_toolbar, text="🗑️ ELIMINAR SELECCIÓN", fg_color="#F44336", hover_color="#D32F2F", command=self.borrar_operacion).pack(side="right")

        container2 = ctk.CTkFrame(frame)
        container2.pack(fill="both", expand=True, padx=20, pady=5)
        
        self.tree_mensual = ttk.Treeview(container2, columns=("ID", "Fecha", "Tipo", "Producto", "Total", "Persona", "Encargada"), show="tree headings")
        self.tree_mensual.column("#0", width=40, stretch=tk.NO, anchor="center") 
        self.tree_mensual.heading("#0", text="Ver")
        self.tree_mensual.column("ID", width=0, stretch=tk.NO) 
        self.tree_mensual.heading("Fecha", text="Fecha"); self.tree_mensual.column("Fecha", width=80)
        self.tree_mensual.heading("Tipo", text="Tipo"); self.tree_mensual.column("Tipo", width=100)
        self.tree_mensual.heading("Producto", text="Producto"); self.tree_mensual.column("Producto", width=150)
        self.tree_mensual.heading("Total", text="Total"); self.tree_mensual.column("Total", width=80, anchor="e")
        self.tree_mensual.heading("Persona", text="Cliente/Proveedor"); self.tree_mensual.column("Persona", width=150)
        self.tree_mensual.heading("Encargada", text="Encargada"); self.tree_mensual.column("Encargada", width=80)
        
        scroll_det = ttk.Scrollbar(container2, orient="vertical", command=self.tree_mensual.yview)
        scroll_det.pack(side="right", fill="y"); self.tree_mensual.pack(side="left", fill="both", expand=True)

        ctk.CTkButton(frame, text="📥 Exportar Excel", fg_color="#4CAF50", hover_color="#388E3C", command=self.exportar_excel).pack(pady=10)

    # --- LÓGICAS GENERALES ---
    
    def quitar_del_carrito_ventas(self):
        seleccion = self.tree_cart_ventas.selection()
        if not seleccion:
            return messagebox.showwarning("Atención", "Selecciona un producto del carrito para quitarlo.")
        
        item_id = seleccion[0]
        idx = self.tree_cart_ventas.index(item_id)
        
        del self.carrito_ventas[idx]
        self.actualizar_cart_ui("ventas")

    # SE AGREGÓ FUNCIÓN PARA QUITAR DE COMPRAS
    def quitar_del_carrito_compras(self):
        seleccion = self.tree_cart_compras.selection()
        if not seleccion:
            return messagebox.showwarning("Atención", "Selecciona un producto del carrito para quitarlo.")
        
        item_id = seleccion[0]
        idx = self.tree_cart_compras.index(item_id)
        
        del self.carrito_compras[idx]
        self.actualizar_cart_ui("compras")

    def editar_celda_carrito_ventas(self, event):
        region = self.tree_cart_ventas.identify_region(event.x, event.y)
        if region != "cell": return

        item_id = self.tree_cart_ventas.identify_row(event.y)
        column = self.tree_cart_ventas.identify_column(event.x)

        if column not in ('#2', '#3', '#4'): return

        idx = self.tree_cart_ventas.index(item_id)
        x, y, width, height = self.tree_cart_ventas.bbox(item_id, column)

        prod = self.carrito_ventas[idx]['producto']
        if column == '#2':
            val_actual = str(self.carrito_ventas[idx]['precio_unit'])
        elif column == '#3':
            val_actual = str(self.carrito_ventas[idx]['cantidad'])
        else: # '#4' - Subtotal
            val_actual = str(self.carrito_ventas[idx]['subtotal'])

        entry = ttk.Entry(self.tree_cart_ventas)
        entry.place(x=x, y=y, width=width, height=height)
        entry.insert(0, val_actual)
        entry.select_range(0, tk.END)
        entry.focus()

        def guardar_edicion(e=None):
            nuevo_val_str = entry.get()
            entry.destroy()
            try:
                # 1. Si editan el Precio Unitario
                if column == '#2': 
                    nuevo_precio = float(nuevo_val_str.replace('S/.', '').strip())
                    if nuevo_precio < 0: raise ValueError
                    if nuevo_precio != self.carrito_ventas[idx]['precio_unit']:
                        self.carrito_ventas[idx]['precio_unit'] = nuevo_precio
                        self.carrito_ventas[idx]['subtotal'] = nuevo_precio * self.carrito_ventas[idx]['cantidad']
                        
                # 2. Si editan la Cantidad (recalcula subtotal automático)
                elif column == '#3': 
                    nueva_cant = self.parse_cantidad(nuevo_val_str)
                    if nueva_cant <= 0: raise ValueError
                    self.carrito_ventas[idx]['cantidad'] = nueva_cant
                    self.carrito_ventas[idx]['subtotal'] = nueva_cant * self.carrito_ventas[idx]['precio_unit']
                
                # 3. Si editan el Subtotal (para descuentos fijos)
                elif column == '#4':
                    nuevo_subtotal = float(nuevo_val_str.replace('S/.', '').strip())
                    if nuevo_subtotal < 0: raise ValueError
                    # Solo modificamos el subtotal que se cobrará finalmente
                    self.carrito_ventas[idx]['subtotal'] = nuevo_subtotal
                    # (Ya no se ajusta el precio_unit, queda como registro del valor original)
                
                self.actualizar_cart_ui("ventas")
            except ValueError:
                messagebox.showerror("Error", "Por favor ingresa un número numérico válido o fracción (ej. 1/2) mayor a cero.")

        def cancelar_edicion(e=None):
            entry.destroy()

        entry.bind("<Return>", guardar_edicion)
        entry.bind("<FocusOut>", guardar_edicion)
        entry.bind("<Escape>", cancelar_edicion)

    # SE AGREGÓ FUNCIÓN PARA EDITAR CELDA DE COMPRAS
    def editar_celda_carrito_compras(self, event):
        region = self.tree_cart_compras.identify_region(event.x, event.y)
        if region != "cell": return

        item_id = self.tree_cart_compras.identify_row(event.y)
        column = self.tree_cart_compras.identify_column(event.x)

        if column not in ('#2', '#3', '#4'): return

        idx = self.tree_cart_compras.index(item_id)
        x, y, width, height = self.tree_cart_compras.bbox(item_id, column)

        prod = self.carrito_compras[idx]['producto']
        if column == '#2':
            val_actual = str(self.carrito_compras[idx]['precio_unit'])
        elif column == '#3':
            val_actual = str(self.carrito_compras[idx]['cantidad'])
        else: # '#4' - Subtotal
            val_actual = str(self.carrito_compras[idx]['subtotal'])

        entry = ttk.Entry(self.tree_cart_compras)
        entry.place(x=x, y=y, width=width, height=height)
        entry.insert(0, val_actual)
        entry.select_range(0, tk.END)
        entry.focus()

        def guardar_edicion(e=None):
            nuevo_val_str = entry.get()
            entry.destroy()
            try:
                # 1. Si editan el Precio Unitario
                if column == '#2': 
                    nuevo_precio = float(nuevo_val_str.replace('S/.', '').strip())
                    if nuevo_precio < 0: raise ValueError
                    if nuevo_precio != self.carrito_compras[idx]['precio_unit']:
                        self.carrito_compras[idx]['precio_unit'] = nuevo_precio
                        self.carrito_compras[idx]['subtotal'] = nuevo_precio * self.carrito_compras[idx]['cantidad']
                        
                # 2. Si editan la Cantidad (recalcula subtotal automático)
                elif column == '#3': 
                    nueva_cant = self.parse_cantidad(nuevo_val_str)
                    if nueva_cant <= 0: raise ValueError
                    self.carrito_compras[idx]['cantidad'] = nueva_cant
                    self.carrito_compras[idx]['subtotal'] = nueva_cant * self.carrito_compras[idx]['precio_unit']
                
                # 3. Si editan el Subtotal (para ajustes fijos)
                elif column == '#4':
                    nuevo_subtotal = float(nuevo_val_str.replace('S/.', '').strip())
                    if nuevo_subtotal < 0: raise ValueError
                    self.carrito_compras[idx]['subtotal'] = nuevo_subtotal
                
                self.actualizar_cart_ui("compras")
            except ValueError:
                messagebox.showerror("Error", "Por favor ingresa un número numérico válido o fracción (ej. 1/2) mayor a cero.")

        def cancelar_edicion(e=None):
            entry.destroy()

        entry.bind("<Return>", guardar_edicion)
        entry.bind("<FocusOut>", guardar_edicion)
        entry.bind("<Escape>", cancelar_edicion)

    def actualizar_dias(self, value=None):
        try:
            meses = {"Enero": 1, "Febrero": 2, "Marzo": 3, "Abril": 4, "Mayo": 5, "Junio": 6,
                     "Julio": 7, "Agosto": 8, "Septiembre": 9, "Octubre": 10, "Noviembre": 11, "Diciembre": 12}
            mes = meses[self.combo_mes.get()]
            anio = int(self.combo_anio.get())
            dias_en_mes = calendar.monthrange(anio, mes)[1]
            opciones = ["Todos"] + [str(i) for i in range(1, dias_en_mes + 1)]
            sel_actual = self.combo_dia.get()
            self.combo_dia.configure(values=opciones)
            self.combo_dia.set(sel_actual if sel_actual in opciones else "Todos")
        except: pass

    # Lógica Contactos
    def guardar_contacto(self, tipo):
        if tipo == "cliente":
            n = self.ent_cli_nom.get().strip().upper()
            d = self.ent_cli_doc.get().strip()
            t = self.ent_cli_tel.get().strip()
            if not n: return messagebox.showerror("Error", "Nombre de cliente obligatorio")
            if self.db.agregar_contacto("cliente", n, d, t):
                self.ent_cli_nom.delete(0, tk.END); self.ent_cli_doc.delete(0, tk.END); self.ent_cli_tel.delete(0, tk.END)
                self.cargar_tablas_contactos()
            else: messagebox.showerror("Error", "Cliente ya existe")
        else:
            n = self.ent_prov_nom.get().strip().upper()
            d = self.ent_prov_doc.get().strip()
            t = self.ent_prov_tel.get().strip()
            if not n: return messagebox.showerror("Error", "Nombre de proveedor obligatorio")
            if self.db.agregar_contacto("proveedor", n, d, t):
                self.ent_prov_nom.delete(0, tk.END); self.ent_prov_doc.delete(0, tk.END); self.ent_prov_tel.delete(0, tk.END)
                self.cargar_tablas_contactos()
            else: messagebox.showerror("Error", "Proveedor ya existe")

    def borrar_contacto(self, tipo):
        tree = self.tree_clientes if tipo == "cliente" else self.tree_proveedores
        sel = tree.selection()
        if not sel: return
        nombre = tree.item(sel[0])['values'][1]
        if messagebox.askyesno("Borrar", f"¿Eliminar a {nombre}?"):
            if self.db.eliminar_contacto(tipo, nombre): self.cargar_tablas_contactos()
            else: messagebox.showerror("Error", "No se puede eliminar (quizás es PÚBLICO GENERAL)")

    def cargar_tablas_contactos(self):
        for r in self.tree_clientes.get_children(): self.tree_clientes.delete(r)
        for r in self.tree_proveedores.get_children(): self.tree_proveedores.delete(r)
        for c in self.db.obtener_contactos("cliente"): self.tree_clientes.insert("", "end", values=c)
        for p in self.db.obtener_contactos("proveedor"): self.tree_proveedores.insert("", "end", values=p)
        self.actualizar_combos_personas()

    def actualizar_combos_personas(self):
        clis = self.db.obtener_nombres_contactos("cliente")
        provs = self.db.obtener_nombres_contactos("proveedor")
        
        if clis:
            self.combo_cliente_venta.configure(values=clis)
            if "PÚBLICO GENERAL" in clis: self.combo_cliente_venta.set("PÚBLICO GENERAL")
            else: self.combo_cliente_venta.set(clis[0])
            self.combo_rep_cli.configure(values=["Todos"] + clis)
            self.combo_rep_cli.set("Todos")
            
        if provs:
            self.combo_proveedor_compra.configure(values=provs)
            self.combo_proveedor_compra.set(provs[0])
            self.combo_rep_prov.configure(values=["Todos"] + provs)
            self.combo_rep_prov.set("Todos")

    def abrir_popup_contacto(self, tipo):
        top = ctk.CTkToplevel(self)
        top.title(f"Nuevo {'Cliente' if tipo=='cliente' else 'Proveedor'}")
        top.geometry("300x250")
        top.grab_set()
        ctk.CTkLabel(top, text="Nombre/Empresa:").pack(pady=(10,0))
        e_nom = ctk.CTkEntry(top, width=200); e_nom.pack(pady=5)
        ctk.CTkLabel(top, text="DNI/RUC/Contacto:").pack(pady=(5,0))
        e_doc = ctk.CTkEntry(top, width=200); e_doc.pack(pady=5)
        
        def guardar():
            n = e_nom.get().strip().upper()
            if not n: return
            if self.db.agregar_contacto(tipo, n, e_doc.get().strip(), ""):
                self.cargar_tablas_contactos()
                if tipo == "cliente": self.combo_cliente_venta.set(n)
                else: self.combo_proveedor_compra.set(n)
                top.destroy()
        ctk.CTkButton(top, text="Guardar Rápido", command=guardar).pack(pady=15)

    # Lógica de Carrito Ventas
    def agregar_al_carrito_ventas(self):
        prod = self.lbl_sel_prod_ventas.cget("text")
        if prod == "---": return messagebox.showwarning("Atención", "Selecciona un producto primero.")
        try:
            cant = self.parse_cantidad(self.ent_cantidad_ventas.get())
            if cant <= 0: raise ValueError
        except: return messagebox.showerror("Error", "La cantidad debe ser un número o fracción (ej: 1/2) mayor a cero.")
        
        item_id = self.tree_ventas.selection()[0]
        
        precio_str = str(self.tree_ventas.item(item_id)['values'][1])
        precio_venta = float(precio_str.replace('S/.', '').strip())
        stock_disp = float(self.tree_ventas.item(item_id)['values'][2]) 
        
        if stock_disp < cant:
            if not messagebox.askyesno("Advertencia de Stock", f"Intenta vender más del stock disponible en pantalla ({stock_disp:g}). Quedará negativo.\n\n¿Continuar de todos modos?"):
                return
            
        self.carrito_ventas.append({'producto': prod, 'precio_unit': precio_venta, 'cantidad': cant, 'subtotal': cant * precio_venta})
        self.actualizar_cart_ui("ventas")
        self.ent_cantidad_ventas.delete(0, tk.END)

    # Lógica de Carrito Compras
    def agregar_al_carrito_compras(self):
        prod = self.lbl_sel_prod_compras.cget("text")
        if prod == "---": return messagebox.showwarning("Atención", "Selecciona un producto primero.")
        try:
            cant = self.parse_cantidad(self.ent_cantidad_compras.get())
            if cant <= 0: raise ValueError
        except: return messagebox.showerror("Error", "La cantidad debe ser un número o fracción (ej: 1/2) mayor a cero.")
        
        item_id = self.tree_compras.selection()[0]
        
        costo_str = str(self.tree_compras.item(item_id)['values'][1])
        costo_sugerido = float(costo_str.replace('S/.', '').strip())
        
        costo_unitario = simpledialog.askfloat("Costo Compra", f"Precio UNITARIO de compra para {prod} (S/.):", initialvalue=costo_sugerido)
        if costo_unitario is None or costo_unitario <= 0: return

        self.carrito_compras.append({'producto': prod, 'precio_unit': costo_unitario, 'cantidad': cant, 'subtotal': cant * costo_unitario})
        self.actualizar_cart_ui("compras")
        self.ent_cantidad_compras.delete(0, tk.END)

    def actualizar_cart_ui(self, tipo):
        tree = self.tree_cart_ventas if tipo == "ventas" else self.tree_cart_compras
        carrito = self.carrito_ventas if tipo == "ventas" else self.carrito_compras
        lbl_tot = self.lbl_total_ventas if tipo == "ventas" else self.lbl_total_compras
        prefix = "TOTAL: S/." if tipo == "ventas" else "TOTAL GASTO: S/."

        for r in tree.get_children(): tree.delete(r)
        tot = 0.0
        for item in carrito:
            tree.insert("", "end", values=(item['producto'], f"S/. {item['precio_unit']:.2f}", f"{item['cantidad']:g}", f"S/. {item['subtotal']:.2f}"))
            tot += item['subtotal']
        lbl_tot.configure(text=f"{prefix} {tot:.2f}")

        if tipo == "ventas":
            self.cargar_tabla_productos(self.ent_buscar_ventas.get(), target_tree=self.tree_ventas)

    def vaciar_carrito(self, tipo):
        if tipo == "ventas": self.carrito_ventas = []
        else: self.carrito_compras = []
        self.actualizar_cart_ui(tipo)

    # Procesar Boletas
    def procesar_boleta(self, tipo):
        if not self.carrito_ventas: return messagebox.showwarning("Atención", "Carrito vacío.")
        fecha_txt = self.ent_fecha_ventas.get()
        encargada = self.combo_encargada.get()
        cliente = self.combo_cliente_venta.get()
        hora_boleta = datetime.datetime.now().strftime("%H:%M:%S")

        if tipo == "FIADO" and cliente == "PÚBLICO GENERAL":
            return messagebox.showwarning("Cancelado", "Debe seleccionar un cliente específico para el fiado.")

        estado = "PAGADO" if tipo == "VENTA" else "PENDIENTE"

        for item in self.carrito_ventas:
            prod, cant, dinero = item['producto'], item['cantidad'], item['subtotal']
            nuevo_stk = self.db.actualizar_stock_y_obtener_saldo(prod, cant, "restar")
            if nuevo_stk is not None:
                self.db.registrar_transaccion(fecha_txt, tipo, prod, cant, dinero, encargada, nuevo_stk, cliente=cliente, estado=estado, hora_manual=hora_boleta)

        self.vaciar_carrito("ventas"); self.ent_buscar_ventas.delete(0, tk.END)
        self.cargar_tabla_productos()
        if tipo == "FIADO": self.cargar_fiados()
        messagebox.showinfo("Éxito", f"Operación de {tipo} registrada.")

    def procesar_boleta_compra(self):
        if not self.carrito_compras: return messagebox.showwarning("Atención", "La lista de ingreso está vacía.")
        fecha_txt = self.ent_fecha_compras.get()
        encargada = self.combo_encargada.get()
        proveedor = self.combo_proveedor_compra.get()
        hora_boleta = datetime.datetime.now().strftime("%H:%M:%S")

        if not proveedor: return messagebox.showwarning("Atención", "Seleccione un proveedor.")

        for item in self.carrito_compras:
            prod, cant, dinero = item['producto'], item['cantidad'], item['subtotal']
            nuevo_stk = self.db.actualizar_stock_y_obtener_saldo(prod, cant, "sumar")
            if nuevo_stk is not None:
                self.db.registrar_transaccion(fecha_txt, "ENTRADA", prod, cant, dinero, encargada, nuevo_stk, proveedor=proveedor, estado="PAGADO", hora_manual=hora_boleta)
                self.db.cursor.execute("UPDATE productos SET precio_compra=? WHERE nombre=?", (item['precio_unit'], prod))
        self.db.conn.commit()

        self.vaciar_carrito("compras"); self.ent_buscar_compras.delete(0, tk.END)
        self.cargar_tabla_productos()
        messagebox.showinfo("Éxito", "Ingreso de mercadería registrado.")

    def generar_reporte_mensual(self):
        meses = {"Enero": "01", "Febrero": "02", "Marzo": "03", "Abril": "04", "Mayo": "05", "Junio": "06",
                 "Julio": "07", "Agosto": "08", "Septiembre": "09", "Octubre": "10", "Noviembre": "11", "Diciembre": "12"}
        filtro_mes = f"{self.combo_anio.get()}-{meses[self.combo_mes.get()]}"
        dia_selecc = self.combo_dia.get()
        filtro_cli = self.combo_rep_cli.get()
        filtro_prov = self.combo_rep_prov.get()

        df = self.db.obtener_datos_raw()
        for row in self.tree_mensual.get_children(): self.tree_mensual.delete(row)
        for row in self.tree_resumen_prod.get_children(): self.tree_resumen_prod.delete(row)
        self.card_stock_total.configure(text=f"STOCK TOTAL\n{self.db.obtener_total_stock_actual()} unid.")

        if self.canvas_grafico:
            self.canvas_grafico.get_tk_widget().destroy()
            self.canvas_grafico = None

        if df.empty: return

        df['fecha'] = pd.to_datetime(df['fecha'])
        df_filtrado = df[df['fecha'].dt.strftime('%Y-%m') == filtro_mes].copy()
        
        # Filtros estrictos
        if dia_selecc != "Todos": 
            df_filtrado = df_filtrado[df_filtrado['fecha'].dt.day == int(dia_selecc)]
        if filtro_cli != "Todos": 
            df_filtrado = df_filtrado[df_filtrado['cliente'] == filtro_cli]
        if filtro_prov != "Todos": 
            df_filtrado = df_filtrado[df_filtrado['proveedor'] == filtro_prov]

        if df_filtrado.empty:
            self.card_ventas.configure(text="INGRESOS (Caja)\nS/. 0.00")
            self.card_gastos.configure(text="COMPRAS\nS/. 0.00")
            self.card_ganancia.configure(text="CAJA REAL\nS/. 0.00", fg_color="#BBDEFB")
            self.card_fiados.configure(text="POR COBRAR\nS/. 0.00")
            return

        ingresos = df_filtrado[df_filtrado['tipo'].isin(['VENTA', 'COBRO_DEUDA'])]['total_dinero'].sum()
        gastos = df_filtrado[df_filtrado['tipo'] == 'ENTRADA']['total_dinero'].sum()
        por_cobrar = df_filtrado[(df_filtrado['tipo'] == 'FIADO') & (df_filtrado['estado'] == 'PENDIENTE')]['total_dinero'].sum()
        
        balance = ingresos - gastos
        self.card_ventas.configure(text=f"INGRESOS (Caja)\nS/. {ingresos:.2f}")
        self.card_gastos.configure(text=f"COMPRAS\nS/. {gastos:.2f}")
        self.card_ganancia.configure(text=f"CAJA REAL\nS/. {balance:.2f}", fg_color="#C8E6C9" if balance >= 0 else "#FFCDD2")
        self.card_fiados.configure(text=f"POR COBRAR\nS/. {por_cobrar:.2f}")

        for prod in df_filtrado['producto'].unique():
            if not prod: continue 
            df_prod = df_filtrado[df_filtrado['producto'] == prod]
            vendido = df_prod[df_prod['tipo'].isin(['VENTA', 'FIADO'])]['cantidad'].sum()
            comprado = df_prod[df_prod['tipo'] == 'ENTRADA']['cantidad'].sum()
            mov_stock = df_prod[df_prod['tipo'] != 'COBRO_DEUDA']
            cierre = mov_stock.sort_values(by=["fecha", "hora"], ascending=False).iloc[0]['stock_resultante'] if not mov_stock.empty else "-" 
            
            cierre_fmt = f"{cierre:g}" if cierre != "-" else "-"
            self.tree_resumen_prod.insert("", "end", values=(prod, f"{vendido:g}", f"{comprado:g}", cierre_fmt))

        df_filtrado['grupo_boleta'] = df_filtrado['fecha'].dt.strftime("%Y-%m-%d") + " " + df_filtrado['hora'] + " | " + df_filtrado['tipo']
        df_ordenado = df_filtrado.sort_values(by=["fecha", "hora"], ascending=False)

        for boleta_id, group in df_ordenado.groupby('grupo_boleta', sort=False):
            row_rep = group.iloc[0]
            persona = row_rep['cliente'] if pd.notna(row_rep['cliente']) and row_rep['cliente'] != "" else row_rep['proveedor']
            if pd.isna(persona): persona = ""

            total_boleta = group['total_dinero'].sum()
            titulo_boleta = "🛒 TOTAL BOLETA" if len(group) > 1 else "🛒 BOLETA (1 Item)"
            
            parent_iid = self.tree_mensual.insert("", "end", text="➕", 
                values=("", row_rep['fecha'].strftime("%Y-%m-%d"), row_rep['tipo'], titulo_boleta, f"S/. {total_boleta:.2f}", persona, row_rep['encargada']), 
                tags=('boleta_total',), open=False)

            for _, row in group.iterrows():
                self.tree_mensual.insert(parent_iid, "end", text="↳", 
                    values=(row['id'], "", "", f"{row['producto']} (x{row['cantidad']:g})", f"S/. {row['total_dinero']:.2f}", "", ""))

        self.tree_mensual.tag_configure('boleta_total', background='#E3F2FD', font=('Segoe UI', 10, 'bold'))

        fig = Figure(figsize=(4, 2), dpi=100)
        fig.patch.set_facecolor('#EBEBEB')
        ax = fig.add_subplot(111)
        ax.bar(['Ingresos', 'Gastos'], [ingresos, gastos], color=['#4CAF50', '#F44336'])
        ax.set_ylabel('Soles (S/.)')
        ax.set_title('Desempeño del Periodo', fontsize=10)
        fig.tight_layout()
        
        self.canvas_grafico = FigureCanvasTkAgg(fig, master=self.f_grafico)
        self.canvas_grafico.draw()
        self.canvas_grafico.get_tk_widget().pack(fill="both", expand=True)

    def borrar_operacion(self):
        seleccion = self.tree_mensual.selection()
        if not seleccion: return
        
        if messagebox.askyesno("Confirmar", f"¿Estás seguro de eliminar {len(seleccion)} fila(s) seleccionada(s)? (Si seleccionaste una boleta entera, se revertirán todos sus productos)"):
            
            ids_a_eliminar = set() # Set para evitar eliminar el mismo ID dos veces si selecciona padre e hijo
            
            for item_iid in seleccion:
                values = self.tree_mensual.item(item_iid)['values']
                children = self.tree_mensual.get_children(item_iid)
                
                if children: # Si la selección tiene hijos, es una boleta padre completa
                    for child in children:
                        child_vals = self.tree_mensual.item(child)['values']
                        if str(child_vals[0]).isdigit():
                            ids_a_eliminar.add(child_vals[0])
                else: # Si no tiene hijos, es un producto individual específico
                    if str(values[0]).isdigit(): # Validar que sí existe un ID real de la base de datos
                        ids_a_eliminar.add(values[0])

            if ids_a_eliminar:
                for db_id in ids_a_eliminar:
                    self.db.eliminar_transaccion_y_reversar_stock(db_id)
                
                self.generar_reporte_mensual()
                self.cargar_tabla_productos()
                self.cargar_fiados()

    def nueva_encargada(self):
        nom = simpledialog.askstring("Nuevo", "Nombre:")
        if nom and self.db.agregar_encargada(nom.title()): self.actualizar_lista_encargadas()
    
    def borrar_encargada(self):
        nombre = self.combo_encargada.get()
        if messagebox.askyesno("Borrar", f"¿Borrar a {nombre}?"):
            if self.db.eliminar_encargada(nombre): self.actualizar_lista_encargadas()
            else: messagebox.showerror("Error", "No se puede borrar Administradora.")

    def actualizar_lista_encargadas(self):
        l = self.db.obtener_encargadas()
        self.combo_encargada.configure(values=l)
        if l: self.combo_encargada.set(l[0])
    
    def cargar_tabla_productos(self, filtro="", target_tree=None):
        trees = [self.tree_ventas, self.tree_compras, self.tree_precios] if target_tree is None else [target_tree]
        for t in trees:
            if t and hasattr(self, 'tree_precios'):
                for r in t.get_children(): t.delete(r)
        
        cart_qty = {}
        for item in self.carrito_ventas:
            cart_qty[item['producto']] = cart_qty.get(item['producto'], 0.0) + float(item['cantidad'])

        for p in self.db.obtener_todos_productos():
            nombre, precio, precio_compra, stock = p
            p_comp_val = precio_compra if precio_compra else 0.0
            stock_float = float(stock)
            
            if filtro.lower() in nombre.lower():
                if self.tree_ventas in trees:
                    stock_disp = stock_float - cart_qty.get(nombre, 0.0)
                    self.tree_ventas.insert("", "end", values=(nombre, f"S/. {precio:.2f}", f"{stock_disp:g}"), tags=('bajo_stock' if stock_disp <= 5 else 'normal',))
                
                if self.tree_compras in trees:
                    self.tree_compras.insert("", "end", values=(nombre, f"S/. {p_comp_val:.2f}", f"{stock_float:g}"))
            
            if hasattr(self, 'tree_precios') and self.tree_precios in trees:
                if target_tree is None or target_tree == self.tree_precios:
                    self.tree_precios.insert("", "end", values=(nombre, f"{stock_float:g}", f"S/. {precio:.2f}", f"S/. {p_comp_val:.2f}"))
    
    def cargar_fiados(self):
        for r in self.tree_fiados.get_children(): self.tree_fiados.delete(r)
        for d in self.db.obtener_deudas_pendientes(): 
            val_format = (d[0], d[1], d[2], d[3], f"{d[4]:g}", f"S/. {d[5]:.2f}")
            self.tree_fiados.insert("", "end", values=val_format)

    def cobrar_deuda(self):
        sel = self.tree_fiados.selection()
        if not sel: return
        val = self.tree_fiados.item(sel[0])['values']
        if messagebox.askyesno("Cobro", f"¿{val[2]} paga {val[5]}?"):
            if self.db.pagar_fiado(val[0]): self.cargar_fiados(); self.generar_reporte_mensual()

    def al_seleccionar_producto(self, tree, label_target):
        s = tree.selection()
        if s: label_target.configure(text=tree.item(s[0])['values'][0])

    def al_seleccionar_producto_tabla_editar(self, event):
        s = self.tree_precios.selection()
        if s:
            nombre = self.tree_precios.item(s[0])['values'][0]
            self.combo_edit_prod.set(nombre)
            self.al_seleccionar_producto_editar(nombre)

    def al_seleccionar_producto_editar(self, nombre):
        if not nombre: return
        cur = self.db.cursor.execute("SELECT precio, precio_compra, stock FROM productos WHERE nombre=?", (nombre,))
        row = cur.fetchone()
        if row:
            self.e_edit_nom.delete(0, tk.END); self.e_edit_nom.insert(0, nombre)
            self.e_edit_prec.delete(0, tk.END); self.e_edit_prec.insert(0, row[0])
            self.e_edit_prec_comp.delete(0, tk.END); self.e_edit_prec_comp.insert(0, row[1] if row[1] else 0.0)
            self.e_edit_stk.delete(0, tk.END); self.e_edit_stk.insert(0, f"{row[2]:g}")
    
    def actualizar_combo_productos(self, event=None):
        l = self.db.obtener_lista_nombres_productos()
        if hasattr(self, 'combo_edit_prod') and l:
            self.combo_edit_prod.configure(values=l)
            if self.combo_edit_prod.get() not in l: self.combo_edit_prod.set(l[0])
            self.al_seleccionar_producto_editar(self.combo_edit_prod.get())
    
    def crear_producto(self):
        nombre = self.e_new_nom.get().strip().upper()
        if not nombre: return messagebox.showerror("Error", "Nombre vacío.")
        try:
            precio = float(self.e_new_prec.get())
            p_compra = float(self.e_new_prec_comp.get()) if self.e_new_prec_comp.get() else 0.0
            stock = self.parse_cantidad(self.e_new_stk.get())
            if precio <= 0 or stock < 0: return messagebox.showerror("Error", "Valores numéricos inválidos.")
            if self.db.agregar_producto(nombre, precio, p_compra, stock):
                self.cargar_tabla_productos(); self.actualizar_combo_productos()
                self.e_new_nom.delete(0, tk.END); self.e_new_prec.delete(0, tk.END)
                self.e_new_prec_comp.delete(0, tk.END); self.e_new_stk.delete(0, tk.END)
                messagebox.showinfo("Éxito", "Producto agregado.")
            else: messagebox.showerror("Error", "El producto ya existe.")
        except ValueError: messagebox.showerror("Error", "Use números o fracciones válidas (ej: 1/2).")
    
    def actualizar_producto(self):
        prod = self.combo_edit_prod.get()
        n_nom = self.e_edit_nom.get().strip().upper()
        if not prod or not n_nom: return
        try:
            n_prec = float(self.e_edit_prec.get())
            n_p_comp = float(self.e_edit_prec_comp.get()) if self.e_edit_prec_comp.get() else 0.0
            stk_str = self.e_edit_stk.get().strip()
            n_stk = self.parse_cantidad(stk_str) if stk_str else None
            if n_prec <= 0: return messagebox.showerror("Error", "Precio > 0.")
            if self.db.modificar_producto(prod, n_nom, n_prec, n_p_comp, n_stk):
                self.cargar_tabla_productos(); self.actualizar_combo_productos()
                self.combo_edit_prod.set(n_nom)
                messagebox.showinfo("Ok", "Producto actualizado.")
        except ValueError: messagebox.showerror("Error", "Datos numéricos inválidos.")

    def borrar_producto(self):
        if messagebox.askyesno("Eliminar", f"¿Eliminar '{self.combo_edit_prod.get()}'?"):
            if self.db.eliminar_producto(self.combo_edit_prod.get()):
                self.cargar_tabla_productos(); self.actualizar_combo_productos()

    def exportar_excel(self):
        df = self.db.obtener_datos_raw()
        if df.empty: return
        fp = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel", "*.xlsx")])
        if fp: df.to_excel(fp, index=False); messagebox.showinfo("Listo", "Exportado.")

if __name__ == "__main__":
    app = Aplicacion()
    app.mainloop()