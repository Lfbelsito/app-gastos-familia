import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
import google.generativeai as genai
import json

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Finanzas Familiares Pro", layout="wide", page_icon="📈")

# --- 2. GESTIÓN DE CLAVES (SECRETS) ---
try:
    if "GOOGLE_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    else: pass
except: pass

# --- 3. LISTAS Y CONFIG ---
MESES_ORDENADOS = [
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
]
COLUMNAS_DINERO = ["Monto", "Total", "Gastos", "Ingresos", "Ahorro", "Valor", "Pesos", "USD"]

# --- 4. FUNCIONES DE LIMPIEZA ---
def limpiar_valor(val):
    if isinstance(val, (int, float)): return float(val)
    try:
        val_str = str(val).strip()
        if val_str in ["", "-", "nan", "None"]: return 0.0
        val_str = val_str.replace("$", "").replace("USD", "").replace("Ars", "").strip()
        val_str = val_str.replace(".", "").replace(",", ".")
        return float(val_str)
    except: return 0.0

def formato_visual(val):
    return "$ {:,.0f}".format(val).replace(",", ".")

# --- 5. FUNCIONES DE LECTURA DE EXCEL ---
def encontrar_celda(df_raw, palabras_clave, min_col=0, min_row=0):
    try:
        zona = df_raw.iloc[min_row:, min_col:]
        for r_idx, row in zona.iterrows():
            for c_idx, val in enumerate(row):
                val_str = str(val).lower()
                for p in palabras_clave:
                    if p.lower() in val_str:
                        return r_idx, (c_idx + min_col)
        return None, None
    except: return None, None

def cortar_bloque(df_raw, fila, col, num_cols, filas_aprox=30):
    try:
        headers = df_raw.iloc[fila, col : col + num_cols].astype(str).str.strip().tolist()
        headers = [f"C{i}" if h in ["nan", ""] else h for i,h in enumerate(headers)]
        start = fila + 1
        df = df_raw.iloc[start : start + filas_aprox, col : col + num_cols].copy()
        df = df[~((df.iloc[:, 0].astype(str).isin(["nan", "", "None"])) & (df.iloc[:, 1].astype(str).isin(["nan", "", "None"])))]
        df.columns = headers
        return df
    except: return pd.DataFrame()

# --- 6. CEREBRO DE DATOS (AHORA LEE DETALLES) ---
@st.cache_data(ttl=60)
def cargar_todo_el_anio():
    conn = st.connection("gsheets", type=GSheetsConnection)
    resumen_kpi = []
    todos_los_gastos = [] # Aquí guardaremos cada fila de gasto de cada mes
    
    barra = st.progress(0, text="Analizando tu economía al detalle...")
    
    for i, mes in enumerate(MESES_ORDENADOS):
        barra.progress((i + 1) / len(MESES_ORDENADOS), text=f"Procesando {mes}...")
        try:
            try:
                df_raw = conn.read(worksheet=mes, header=None)
            except: continue
            
            # 1. KPI GENERALES
            r_bal, c_bal = encontrar_celda(df_raw, ["Gastos fijos"], min_col=5)
            if r_bal is not None:
                bal = cortar_bloque(df_raw, r_bal, c_bal, 3, filas_aprox=1)
                if not bal.empty:
                    gastos = limpiar_valor(bal.iloc[0, 0])
                    ingresos = limpiar_valor(bal.iloc[0, 1])
                    ahorro = limpiar_valor(bal.iloc[0, 2])
                    if gastos > 0 or ingresos > 0:
                        resumen_kpi.append({"Mes": mes, "Gastos": gastos, "Ingresos": ingresos, "Ahorro": ahorro})
            
            # 2. DETALLE DE GASTOS (NUEVO)
            r_gas, c_gas = encontrar_celda(df_raw, ["Vencimiento", "Categoría"], min_col=0)
            if r_gas is not None:
                # Cortamos la tabla de gastos
                df_gastos_mes = cortar_bloque(df_raw, r_gas, c_gas, 5, 40)
                # Limpiamos el monto
                if not df_gastos_mes.empty:
                    # Buscamos cual columna es Monto y cual Categoria
                    cols = df_gastos_mes.columns
                    col_monto = [c for c in cols if "monto" in c.lower()][0]
                    col_cat = [c for c in cols if "categ" in c.lower()][0]
                    
                    df_gastos_mes["Monto_Clean"] = df_gastos_mes[col_monto].apply(limpiar_valor)
                    df_gastos_mes["Mes"] = mes # Le ponemos etiqueta del mes
                    df_gastos_mes["Orden_Mes"] = i # Para ordenar cronologicamente
                    
                    # Guardamos solo lo importante: Mes, Categoria, Monto
                    df_mini = df_gastos_mes[["Mes", "Orden_Mes", col_cat, "Monto_Clean"]].copy()
                    df_mini.columns = ["Mes", "Orden_Mes", "Categoria", "Monto"]
                    
                    todos_los_gastos.append(df_mini)

        except: pass
            
    barra.empty()
    
    # Consolidamos todo
    df_kpi = pd.DataFrame(resumen_kpi)
    df_detalles = pd.concat(todos_los_gastos) if todos_los_gastos else pd.DataFrame()
    
    return df_kpi, df_detalles

# --- 7. FUNCIÓN IA PRO ---
def analizar_imagen_con_ia(imagen_bytes, mime_type):
    try:
        model = genai.GenerativeModel('gemini-1.5-pro')
        prompt = """Eres un experto contable. Extrae en JSON: {"fecha": "DD/MM/AAAA", "categoria": "Texto", "monto": 0.00, "comentario": "Texto"}. Si no hay dato, null."""
        image_part = {"mime_type": mime_type, "data": imagen_bytes}
        response = model.generate_content([prompt, image_part])
        return response.text
    except Exception as e: return f"Error IA: {str(e)}"

# --- 8. INTERFAZ PRINCIPAL ---

st.sidebar.title("Navegación")
if st.sidebar.button("🔄 Refrescar Datos"):
    st.cache_data.clear(); st.rerun()

opcion = st.sidebar.radio("Ir a:", ["📊 Dashboard Inteligente", "📅 Ver Mensual", "📤 Cargar Comprobante"])
conn = st.connection("gsheets", type=GSheetsConnection)

# ==========================================
# 1. DASHBOARD INTELIGENTE
# ==========================================
if opcion == "📊 Dashboard Inteligente":
    st.title("📈 Análisis Financiero 360°")
    
    # Cargamos las DOS bases de datos (Totales y Detalles)
    df_resumen, df_detalles = cargar_todo_el_anio()
    
    # --- SECCIÓN SUPERIOR: TOTALES ---
    if not df_resumen.empty:
        c1, c2, c3 = st.columns(3)
        c1.metric("Ingresos Anuales", formato_visual(df_resumen["Ingresos"].sum()), border=True)
        c2.metric("Gastos Anuales", formato_visual(df_resumen["Gastos"].sum()), delta_color="inverse", border=True)
        c3.metric("Ahorro Anual", formato_visual(df_resumen["Ahorro"].sum()), border=True)
    
    st.divider()

    # --- SECCIÓN NUEVA: LUPA DE GASTOS ---
    st.subheader("🔍 Lupa de Gastos: Evolución Categoría por Categoría")
    
    if not df_detalles.empty:
        # 1. Selector de Categoría
        # Sacamos lista única de categorías y limpiamos vacíos
        lista_categorias = sorted(df_detalles["Categoria"].unique().astype(str))
        lista_categorias = [c for c in lista_categorias if c.lower() not in ["nan", "none", ""]]
        
        col_sel, col_stat = st.columns([1, 2])
        
        with col_sel:
            categoria_elegida = st.selectbox("Selecciona un gasto para analizar:", lista_categorias)
            
            # Filtramos los datos
            df_filtrado = df_detalles[df_detalles["Categoria"] == categoria_elegida].sort_values("Orden_Mes")
            
            if not df_filtrado.empty:
                # Calculamos variación respecto al mes anterior
                ultimo_monto = df_filtrado.iloc[-1]["Monto"]
                
                variacion_str = "Sin datos previos"
                color_delta = "off"
                
                if len(df_filtrado) > 1:
                    penultimo_monto = df_filtrado.iloc[-2]["Monto"]
                    if penultimo_monto > 0:
                        pct = ((ultimo_monto - penultimo_monto) / penultimo_monto) * 100
                        variacion_str = f"{pct:+.1f}% vs mes anterior"
                        color_delta = "inverse" if pct > 0 else "normal" # Rojo si sube, Verde si baja
                
                st.metric(f"Último valor ({df_filtrado.iloc[-1]['Mes']})", 
                          formato_visual(ultimo_monto), 
                          variacion_str, 
                          delta_color=color_delta)

        with col_stat:
            # Gráfico de Línea Específico
            if not df_filtrado.empty:
                fig = px.line(df_filtrado, x="Mes", y="Monto", markers=True, title=f"Evolución de costo: {categoria_elegida}")
                fig.update_traces(line_color="#EF553B", line_width=4, texttemplate='%{y:.2s}', textposition='top center')
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No hay datos históricos para esta categoría.")

        # Tabla Resumen de esa categoría
        with st.expander(f"Ver historial completo de {categoria_elegida}"):
            df_tabla = df_filtrado[["Mes", "Monto"]].copy()
            df_tabla["Monto"] = df_tabla["Monto"].apply(formato_visual)
            st.dataframe(df_tabla, use_container_width=True)

    else:
        st.info("Aún no hay detalles de gastos cargados.")

# ==========================================
# 2. VER MENSUAL
# ==========================================
elif opcion == "📅 Ver Mensual":
    mes_seleccionado = st.sidebar.selectbox("Selecciona Mes:", MESES_ORDENADOS)
    st.title(f"Detalle de {mes_seleccionado}")
    try:
        df_raw = conn.read(worksheet=mes_seleccionado, header=None)
        
        r_bal, c_bal = encontrar_celda(df_raw, ["Gastos fijos"], min_col=5)
        balance = cortar_bloque(df_raw, r_bal, c_bal, 3, 1) if r_bal is not None else pd.DataFrame()
        
        r_gas, c_gas = encontrar_celda(df_raw, ["Vencimiento", "Categoría"], min_col=0)
        gastos = cortar_bloque(df_raw, r_gas, c_gas, 5, 40) if r_gas is not None else pd.DataFrame()
        
        r_ing, c_ing = encontrar_celda(df_raw, ["Fecha", "Descripcion"], min_col=6, min_row=3)
        ingresos = cortar_bloque(df_raw, r_ing, c_ing, 6, 20) if r_ing is not None else pd.DataFrame()

        if not balance.empty:
            c1, c2, c3 = st.columns(3)
            try:
                v1 = limpiar_valor(balance.iloc[0,0]); v2 = limpiar_valor(balance.iloc[0,1]); v3 = limpiar_valor(balance.iloc[0,2])
                c1.metric("Gastos Fijos", formato_visual(v1)); c2.metric("Ingresos", formato_visual(v2)); c3.metric("Ahorro", formato_visual(v3))
            except: pass
        st.divider()
        c1, c2 = st.columns(2)
        with c1: st.subheader("Gastos"); st.dataframe(gastos, hide_index=True)
        with c2: st.subheader("Ingresos"); st.dataframe(ingresos, hide_index=True)
    except: st.warning("Mes sin datos.")

# ==========================================
# 3. CARGAR COMPROBANTE
# ==========================================
elif opcion == "📤 Cargar Comprobante":
    st.title("📸 Escáner IA")
    col_izq, col_der = st.columns([1, 1.5])
    with col_izq:
        mes_destino = st.selectbox("Mes:", MESES_ORDENADOS)
        # Dropdown inteligente (reutilizamos la lógica de lectura rápida)
        categorias_existentes = []
        try:
            df_mes = conn.read(worksheet=mes_destino, header=None)
            r_gas, c_gas = encontrar_celda(df_mes, ["Vencimiento", "Categoría"], min_col=0)
            if r_gas is not None:
                df_temp = cortar_bloque(df_mes, r_gas, c_gas, 5, 40)
                cols_cat = [c for c in df_temp.columns if "categ" in c.lower()]
                if cols_cat: categorias_existentes = [c for c in df_temp[cols_cat[0]].unique() if str(c) not in ["nan", ""]]
        except: pass
        
        cat_sel = st.selectbox("Categoría existente:", ["-- Nuevo Gasto --"] + categorias_existentes)
        archivo = st.file_uploader("Archivo", type=["png", "jpg", "pdf"])

    if archivo and st.button("✨ Analizar"):
        with st.spinner("Leyendo..."):
            if "GOOGLE_API_KEY" not in st.secrets: st.error("Falta API Key"); st.stop()
            res = analizar_imagen_con_ia(archivo.getvalue(), archivo.type)
            try:
                datos = json.loads(res.replace("```json", "").replace("```", "").strip())
                st.session_state['datos_ia'] = datos
            except: st.error("Error IA")

    if 'datos_ia' in st.session_state:
        d = st.session_state['datos_ia']
        with st.form("save"):
            c1, c2 = st.columns(2)
            f = c1.text_input("Fecha", d.get("fecha"))
            cat_def = cat_sel if cat_sel != "-- Nuevo Gasto --" else d.get("categoria")
            cat = c2.text_input("Categoría", cat_def)
            m = c1.number_input("Monto", value=float(d.get("monto", 0)), step=100.0)
            comm = c2.text_input("Nota", d.get("comentario"))
            pag = st.checkbox("Pagado", True)
            if st.form_submit_button("💾 Generar"):
                st.info("Copia esto en tu Excel:"); st.code(f"{f}\t{m}\t{'Si' if pag else 'No'}\t{comm}")
                del st.session_state['datos_ia']
