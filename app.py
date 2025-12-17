import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Finanzas Familiares", layout="wide", page_icon="💰")
st.title("💸 Tablero de Control Familiar")

# --- LISTA DE MESES Y DINERO PARA FORMATO ---
MESES = [
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", 
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
]
# Palabras clave para detectar qué columnas llevan signo $
COLUMNAS_DINERO = ["Monto", "Total", "Gastos", "Ingresos", "Ahorro", "Cotizacion", "Saldo", "Valor", "Pesos", "USD"] + MESES

# --- FUNCIONES DE FORMATO Y LIMPIEZA ---

def formato_pesos(valor):
    """Convierte 123456 en $ 123.456"""
    try:
        if str(valor).strip() in ["", "-", "nan", "None"]: return "-"
        # Limpiamos símbolos viejos
        val_str = str(valor).replace("$", "").replace(".", "").replace(",", ".")
        val_float = float(val_str)
        return "$ " + "{:,.0f}".format(val_float).replace(",", ".")
    except:
        return valor

def limpiar_y_formatear_df(df, forzar_formato=False):
    """Limpia la tabla y aplica formato dinero a las columnas correspondientes"""
    if df.empty: return df
    
    # 1. Convertir a string para evitar errores
    df = df.astype(str)
    df = df.replace(["nan", "None", "NaT", "<NA>"], "-")
    
    # 2. Formato Dinero Inteligente
    for col in df.columns:
        # Si forzamos formato (para tablas que son 100% dinero) o si el nombre coincide
        es_columna_dinero = any(k.lower() in col.lower() for k in COLUMNAS_DINERO)
        
        if forzar_formato or es_columna_dinero:
            # No formateamos columnas que parezcan texto (ej: "Categoría", "Fuente")
            if "categor" not in col.lower() and "fuente" not in col.lower() and "dolare" not in col.lower():
                df[col] = df[col].apply(formato_pesos)
            
    return df

# --- MOTOR DE CORTE INTELIGENTE ---

def encontrar_fila(df_raw, texto_clave, col_busqueda=0):
    """Busca en qué FILA está un texto (ej: 'Saldos Mensuales')"""
    try:
        # Buscamos en la columna especificada (por defecto la A -> 0)
        columna = df_raw.iloc[:, col_busqueda].astype(str)
        for idx, val in columna.items():
            if texto_clave.lower() in val.lower():
                return idx
        return None
    except:
        return None

def cortar_seccion(df_raw, fila_header, num_cols=15, filas_datos=None):
    """Corta una tabla dado su encabezado"""
    try:
        # 1. Encabezados
        titulos = df_raw.iloc[fila_header, 0:num_cols].astype(str).str.strip().tolist()
        titulos = [f"Col_{i}" if t in ["nan", ""] else t for i, t in enumerate(titulos)]
        
        # 2. Datos
        inicio_datos = fila_header + 1
        if filas_datos:
            # Si queremos una cantidad fija de filas (ej: solo 1 fila para Saldos)
            fin_datos = inicio_datos + filas_datos
            datos = df_raw.iloc[inicio_datos:fin_datos, 0:num_cols].copy()
        else:
            # Si queremos hasta que se acabe (detectando vacío)
            datos = df_raw.iloc[inicio_datos:, 0:num_cols].copy()
            # Cortamos cuando la columna A se vacía
            datos = datos[datos.iloc[:, 0].ne("nan") & datos.iloc[:, 0].ne("")]

        datos.columns = titulos
        return datos
    except:
        return pd.DataFrame()

# --- INTERFAZ PRINCIPAL ---

lista_pestanas = ["Resumen Anual"] + MESES[6:] + MESES[:6] # Orden personalizado
hoja_seleccionada = st.sidebar.selectbox("📅 Selecciona Período:", lista_pestanas)

conn = st.connection("gsheets", type=GSheetsConnection)

try:
    # ==========================================
    # LÓGICA DEL RESUMEN ANUAL
    # ==========================================
    if hoja_seleccionada == "Resumen Anual":
        st.header("📊 Resumen Anual 2025")
        
        # Leemos todo el mapa
        df_raw = conn.read(worksheet=hoja_seleccionada, header=None, ttl=5)
        
        # --- 1. EVOLUCIÓN DE GASTOS ---
        # Buscamos la fila donde dice "Categoría" en la Columna A (0)
        fila_gastos = encontrar_fila(df_raw, "Categoría", col_busqueda=0)
        if fila_gastos is not None:
            df_gastos = cortar_seccion(df_raw, fila_gastos, num_cols=15) # Hasta col O
            # Quitamos filas vacías o totales raros si molestan
            st.subheader("📉 Evolución de Gastos")
            st.dataframe(limpiar_y_formatear_df(df_gastos), hide_index=True)
        else:
            st.warning("No encontré la tabla 'Categoría'.")

        st.divider()

        # --- 2. SALDOS MENSUALES ---
        # Buscamos "Saldos Mensuales" (Título verde). Los headers (Enero...) están 1 fila abajo.
        fila_titulo_saldo = encontrar_fila(df_raw, "Saldos Mensuales")
        if fila_titulo_saldo is not None:
            # Headers están en fila_titulo + 1
            # Datos están en fila_titulo + 2. Queremos solo 1 fila de datos.
            df_saldos = cortar_seccion(df_raw, fila_header=fila_titulo_saldo+1, num_cols=15, filas_datos=1)
            
            st.subheader("💰 Saldos Mensuales (Ahorro Neto)")
            # Mostramos métricas rápidas si hay datos
            if not df_saldos.empty:
                st.dataframe(limpiar_y_formatear_df(df_saldos, forzar_formato=True), hide_index=True)
        
        st.divider()

        # --- 3. AHORROS (ACTIVOS) Y CAMBIO DE DÓLARES ---
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.subheader("🏦 Mis Ahorros / Activos")
            # Buscamos "Fuente" (Encabezado de la tablita chica)
            fila_ahorro = encontrar_fila(df_raw, "Fuente")
            if fila_ahorro is not None:
                df_ahorro = cortar_seccion(df_raw, fila_ahorro, num_cols=5) # Solo 5 columnas (A-E)
                st.dataframe(limpiar_y_formatear_df(df_ahorro), hide_index=True)
        
        with col2:
            st.subheader("🔄 Cambio de Dólares")
            # Buscamos "Cambio de dolare" o "Cotizacion" en col A
            fila_cambio = encontrar_fila(df_raw, "Cambio de dolare")
            if fila_cambio is not None:
                df_cambio = cortar_seccion(df_raw, fila_cambio, num_cols=15)
                st.dataframe(limpiar_y_formatear_df(df_cambio), hide_index=True)

    # ==========================================
    # LÓGICA DE MESES INDIVIDUALES (YA PROBADA)
    # ==========================================
    else:
        st.write(f"📂 Viendo detalles de: **{hoja_seleccionada}**")
        df_raw = conn.read(worksheet=hoja_seleccionada, header=None, ttl=5)

        # 1. GASTOS (Busca 'Vencimiento' o 'Categoría')
        col_busqueda_gastos = 0 # Columna A
        # A veces la palabra clave no está en la primera celda, iteramos filas 0 y 1
        gastos = pd.DataFrame()
        # Intento 1: Buscar en Fila 0 (Excel 1)
        if "Vencimiento" in str(df_raw.iloc[0].values):
            gastos = cortar_seccion(df_raw, 0, 5)
        # Intento 2: Buscar en Fila 1 (Excel 2)
        elif "Vencimiento" in str(df_raw.iloc[1].values):
            gastos = cortar_seccion(df_raw, 1, 5)
        # Fallback: Buscar "Categoría"
        elif encontrar_fila(df_raw, "Categoría") is not None:
             f = encontrar_fila(df_raw, "Categoría")
             gastos = cortar_seccion(df_raw, f, 5)

        # 2. BALANCE (Busca 'Gastos fijos' en fila 1 o 2)
        f_bal = encontrar_fila(df_raw.iloc[:, 8:12], "Gastos fijos") # Busca en col I aprox
        # Ajuste manual: suele estar en fila 1 (Excel 2)
        balance = df_raw.iloc[2:3, 8:11].copy() if not df_raw.empty else pd.DataFrame()
        # Titulos manuales para prevenir errores
        balance.columns = ["Gastos Fijos", "Ingresos", "Ahorro Mensual"]

        # 3. INGRESOS (Busca 'Fecha' en columna I/8, fila aprox 5-6)
        # Cortamos un sub-dataframe desde la fila 4 para buscar ahí
        sub_search = df_raw.iloc[4:10, 8:10].astype(str) # Buscamos en un rango pequeño
        fila_ingresos = None
        for idx, row in sub_search.iterrows():
            if "Fecha" in row.values or "Descripcion" in row.values:
                fila_ingresos = idx
                break
        
        ingresos = pd.DataFrame()
        if fila_ingresos:
            # Header en fila_ingresos, datos desde +1. Columnas 8 a 14 (I a N)
            # Mi funcion cortar_seccion asume col 0. Hacemos corte manual aquí para ser precisos:
            titulos = df_raw.iloc[fila_ingresos, 8:14].astype(str).str.strip().tolist()
            titulos = [f"C{i}" if t in ["", "nan"] else t for i,t in enumerate(titulos)]
            datos_ing = df_raw.iloc[fila_ingresos+1:, 8:14].copy()
            datos_ing.columns = titulos
            ingresos = datos_ing[datos_ing.iloc[:,0].ne("nan") & datos_ing.iloc[:,0].ne("")]

        # --- VISUALIZACIÓN MES ---
        
        # Balance
        st.markdown("### 💰 Balance del Mes")
        if not balance.empty:
            c1, c2, c3 = st.columns(3)
            try:
                c1.metric("Gastos Fijos", formato_pesos(balance.iloc[0, 0]))
                c2.metric("Ingresos", formato_pesos(balance.iloc[0, 1]))
                c3.metric("Ahorro", formato_pesos(balance.iloc[0, 2]))
            except: st.warning("Revisando datos...")
        
        st.divider()

        c1, c2 = st.columns(2)
        with c1:
            st.subheader("📉 Gastos")
            st.dataframe(limpiar_y_formatear_df(gastos), hide_index=True)
        with c2:
            st.subheader("📈 Ingresos")
            st.dataframe(limpiar_y_formatear_df(ingresos), hide_index=True)

except Exception as e:
    st.error("⚠️ Hubo un problema cargando los datos.")
    st.code(str(e))
