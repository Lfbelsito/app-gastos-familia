import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
import google.generativeai as genai
import json

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Finanzas Familiares Pro", layout="wide", page_icon="💳")

# --- 2. GESTIÓN DE CLAVES (SECRETS) ---
try:
    if "GOOGLE_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    else:
        pass
except:
    pass

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

# --- 6. CEREBRO DE DATOS (LECTURA) ---
@st.cache_data(ttl=60)
def cargar_todo_el_anio():
    conn = st.connection("gsheets", type=GSheetsConnection)
    resumen_kpi = []
    barra = st.progress(0, text="Analizando tu año financiero...")
    
    for i, mes in enumerate(MESES_ORDENADOS):
        barra.progress((i + 1) / len(MESES_ORDENADOS), text=f"Leyendo {mes}...")
        try:
            try:
                df_raw = conn.read(worksheet=mes, header=None)
            except: continue
            
            r_bal, c_bal = encontrar_celda(df_raw, ["Gastos fijos"], min_col=5)
            if r_bal is not None:
                bal = cortar_bloque(df_raw, r_bal, c_bal, 3, filas_aprox=1)
                if not bal.empty:
                    gastos = limpiar_valor(bal.iloc[0, 0])
                    ingresos = limpiar_valor(bal.iloc[0, 1])
                    ahorro = limpiar_valor(bal.iloc[0, 2])
                    if gastos > 0 or ingresos > 0:
                        resumen_kpi.append({"Mes": mes, "Gastos": gastos, "Ingresos": ingresos, "Ahorro": ahorro})
        except: pass
            
    barra.empty()
    return pd.DataFrame(resumen_kpi)

# --- 7. FUNCIÓN IA PRO ---
def analizar_imagen_con_ia(imagen_bytes, mime_type):
    try:
        model = genai.GenerativeModel('gemini-1.5-pro')
        
        prompt = """
        Eres un experto contable. Analiza esta factura.
        Extrae la siguiente información en JSON:
        {
            "fecha": "DD/MM/AAAA",
            "categoria": "Texto", 
            "monto": 0.00, 
            "comentario": "Texto breve"
        }
        Si no encuentras el dato, usa null.
        """
        image_part = {"mime_type": mime_type, "data": imagen_bytes}
        response = model.generate_content([prompt, image_part])
        return response.text
    except Exception as e:
        return f"Error IA: {str(e)}"

# --- 8. INTERFAZ PRINCIPAL ---

st.sidebar.title("Navegación")
if st.sidebar.button("🔄 Refrescar Datos"):
    st.cache_data.clear()
    st.rerun()

opcion = st.sidebar.radio("Ir a:", ["📊 Dashboard General", "📅 Ver Mensual", "📤 Cargar Comprobante"])

conn = st.connection("gsheets", type=GSheetsConnection)

# ==========================================
# 1. DASHBOARD
# ==========================================
if opcion == "📊 Dashboard General":
    st.title("💳 Tablero de Control Pro")
    st.markdown("### Panorama Anual")
    df_resumen = cargar_todo_el_anio()
    
    if not df_resumen.empty:
        total_ingresos = df_resumen["Ingresos"].sum()
        total_gastos = df_resumen["Gastos"].sum()
        total_ahorro = df_resumen["Ahorro"].sum()
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Ingresos", formato_visual(total_ingresos), border=True)
        c2.metric("Total Gastos", formato_visual(total_gastos), delta_color="inverse", border=True)
        c3.metric("Ahorro Acumulado", formato_visual(total_ahorro), border=True)
        st.divider()
        c_graf1, c_graf2 = st.columns(2)
        with c_graf1:
            st.subheader("Flujo de Caja")
            df_melted = df_resumen.melt(id_vars=["Mes"], value_vars=["Ingresos", "Gastos"], var_name="Tipo", value_name="Monto")
            fig = px.bar(df_melted, x="Mes", y="Monto", color="Tipo", barmode="group", text_auto='.2s', color_discrete_map={"Ingresos": "#00CC96", "Gastos": "#EF553B"})
            st.plotly_chart(fig, use_container_width=True)
        with c_graf2:
            st.subheader("Evolución del Ahorro")
            fig2 = px.line(df_resumen, x="Mes", y="Ahorro", markers=True)
            fig2.update_traces(line_color="#636EFA", line_width=4)
            st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("Cargando datos del año...")

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
                c1.metric("Gastos Fijos", formato_visual(v1))
                c2.metric("Ingresos", formato_visual(v2))
                c3.metric("Ahorro", formato_visual(v3))
            except: pass
        st.divider()
        c1, c2 = st.columns(2)
        with c1: 
            st.subheader("Gastos"); st.dataframe(gastos, hide_index=True)
        with c2: 
            st.subheader("Ingresos"); st.dataframe(ingresos, hide_index=True)
    except:
        st.warning(f"No se pudieron cargar datos para {mes_seleccionado}.")

# ==========================================
# 3. CARGAR COMPROBANTE (MEJORADO CON DROPDOWN)
# ==========================================
elif opcion == "📤 Cargar Comprobante":
    st.title("📸 Escáner Inteligente de Facturas")
    st.markdown("Sube una foto y decide si actualizamos un gasto fijo o creamos uno nuevo.")
    
    col_izq, col_der = st.columns([1, 1.5])
    
    with col_izq:
        mes_destino = st.selectbox("Mes a impactar:", MESES_ORDENADOS)
        
        # --- LÓGICA PARA BUSCAR CATEGORÍAS EXISTENTES ---
        categorias_existentes = []
        try:
            # Leemos rápido el mes para sacar las categorías
            df_mes = conn.read(worksheet=mes_destino, header=None)
            r_gas, c_gas = encontrar_celda(df_mes, ["Vencimiento", "Categoría"], min_col=0)
            if r_gas is not None:
                # Cortamos la tabla de gastos
                df_temp = cortar_bloque(df_mes, r_gas, c_gas, 5, 40)
                # Buscamos la columna 'Categoría' (o similar)
                cols_cat = [c for c in df_temp.columns if "categ" in c.lower()]
                if cols_cat:
                    cats = df_temp[cols_cat[0]].unique().tolist()
                    # Limpiamos vacíos
                    categorias_existentes = [c for c in cats if c and str(c).lower() not in ["nan", "none", ""]]
        except: pass
        
        # Desplegable inteligente
        opciones_dropdown = ["-- Nueva Fila (Gasto Nuevo) --"] + categorias_existentes
        categoria_seleccionada = st.selectbox("¿A qué ítem corresponde?", opciones_dropdown)
        
        uploaded_file = st.file_uploader("Sube el archivo aquí", type=["png", "jpg", "jpeg", "pdf"])
    
    if uploaded_file is not None:
        with col_izq:
            if uploaded_file.type != "application/pdf":
                st.image(uploaded_file, caption="Vista previa", use_container_width=True)
        
        with col_der:
            st.write("---")
            if st.button("✨ Extraer Datos con IA", type="primary"):
                with st.spinner("Gemini Pro analizando..."):
                    if "GOOGLE_API_KEY" not in st.secrets:
                        st.error("⚠️ Falta API Key."); st.stop()
                    
                    bytes_data = uploaded_file.getvalue()
                    resultado_texto = analizar_imagen_con_ia(bytes_data, uploaded_file.type)
                    
                    try:
                        clean_json = resultado_texto.replace("```json", "").replace("```", "").strip()
                        datos_factura = json.loads(clean_json)
                        st.session_state['datos_ia'] = datos_factura
                    except:
                        st.error("Error leyendo respuesta IA.")

    # Formulario de Revisión
    if 'datos_ia' in st.session_state:
        datos = st.session_state['datos_ia']
        
        st.success("Datos extraídos. Verifica antes de guardar.")
        
        with st.form("form_guardar_gasto"):
            c1, c2 = st.columns(2)
            fecha = c1.text_input("Fecha", datos.get("fecha", ""))
            
            # Si el usuario eligió una categoría existente en el dropdown, la usamos por defecto
            cat_default = datos.get("categoria", "")
            if categoria_seleccionada != "-- Nueva Fila (Gasto Nuevo) --":
                cat_default = categoria_seleccionada
                
            categoria = c2.text_input("Categoría", cat_default)
            monto = c1.number_input("Monto ($)", value=float(datos.get("monto", 0.0)), step=100.0)
            comentario = c2.text_input("Comentario", datos.get("comentario", ""))
            pagado = st.checkbox("¿Pagado?", value=True)
            
            submitted = st.form_submit_button("💾 Generar Datos para Guardar")
            
            if submitted:
                st.write("---")
                # LÓGICA: Distinguimos si es actualización o nuevo
                if categoria_seleccionada != "-- Nueva Fila (Gasto Nuevo) --":
                    st.info(f"💡 **ACTUALIZACIÓN DE GASTO FIJO ({categoria_seleccionada})**")
                    st.write("Copia estos valores y pégalos sobre la fila existente de tu Excel para no romper el orden:")
                    st.code(f"{fecha}\t{monto}\t{'Si' if pagado else 'No'}\t{comentario}")
                    st.caption("Nota: Copia y pega en las columnas Fecha, Monto, Pagado y Comentario de esa fila.")
                else:
                    st.info("🆕 **NUEVO GASTO**")
                    st.write("Pega esta fila nueva al final de tu tabla de gastos:")
                    st.code(f"{fecha}\t{categoria}\t{monto}\t{'Si' if pagado else 'No'}\t{comentario}")
                
                del st.session_state['datos_ia']
