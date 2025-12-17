import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# --- 1. CONFIGURACIÓN INICIAL ---
st.set_page_config(page_title="Finanzas Familiares", layout="wide", page_icon="💰")
st.title("💸 Tablero de Control Familiar")

# --- 2. LISTAS DE CONFIGURACIÓN ---
MESES = [
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", 
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
]
COLUMNAS_DINERO = [
    "Monto", "Total", "Gastos", "Ingresos", "Ahorro", 
    "Cotizacion", "Saldo", "Valor", "Pesos", "USD", "Ars"
] + MESES

# --- 3. FUNCIONES DE LIMPIEZA Y FORMATO ---

def formato_pesos(valor):
    """Convierte cualquier dato a formato moneda $ 1.000"""
    try:
        val_str = str(valor).strip()
        if val_str in ["", "-", "nan", "None", "0", "0.0"]: return "-"
        
        # Quitamos simbolos para poder convertir a numero
        val_str = val_str.replace("$", "").replace("USD", "").replace("Ars", "").strip()
        val_str = val_str.replace(".", "").replace(",", ".") # Formato USA para conversion
        
        val_float = float(val_str)
        # Formato final con puntos para miles
        return "$ " + "{:,.0f}".format(val_float).replace(",", ".")
    except:
        return valor

def limpiar_y_formatear(df):
    """Limpia la tabla y le pone signo pesos a lo que corresponda"""
    if df.empty: return df
    
    # Rellenamos vacios
    df = df.astype(str).replace(["nan", "None", "<NA>"], "-")
    
    for col in df.columns:
        # Si el nombre de la columna parece dinero
        if any(k.lower() in col.lower() for k in COLUMNAS_DINERO):
            # No formateamos si es "Descripcion" o "Moneda"
            if "descrip" not in col.lower() and "moneda" not in col.lower():
                df[col] = df[col].apply(formato_pesos)
    return df

# --- 4. FUNCIONES DE RADAR (BÚSQUEDA INTELIGENTE) ---

def encontrar_coordenadas(df_raw, palabras_clave, min_col=0, min_row=0):
    """Busca (fila, columna) donde aparece alguna palabra clave"""
    try:
        zona = df_raw.iloc[min_row:, min_col:]
        for r_idx, row in zona.iterrows():
            for c_idx, val in enumerate(row):
                val_str = str(val).lower()
                for palabra in palabras_clave:
                    if palabra.lower() in val_str:
                        # Retornamos indices absolutos
                        return r_idx, (c_idx + min_col)
        return None, None
    except:
        return None, None

def cortar_desde_coordenada(df_raw, fila, col, num_cols, filas_datos=None):
    """Corta la tabla desde la coordenada encontrada"""
    try:
        # Encabezados
        headers = df_raw.iloc[fila, col : col + num_cols].astype(str).str.strip().tolist()
        headers = [f"C{i}" if h in ["nan", ""] else h for i,h in enumerate(headers)]
        
        inicio_datos = fila + 1
        
        if filas_datos:
            # Corte fijo (ej: 1 fila para saldos)
            df = df_raw.iloc[inicio_datos : inicio_datos + filas_datos, col : col + num_cols].copy()
        else:
            # Corte dinámico (hasta encontrar vacío)
            df = df_raw.iloc[inicio_datos:, col : col + num_cols].copy()
            # Validamos que la primera columna tenga datos
            df = df[df.iloc[:, 0].ne("nan") & df.iloc[:, 0].ne("")]
            
        df.columns = headers
        return df
    except:
        return pd.DataFrame()

# --- 5. LÓGICA PRINCIPAL ---

lista_pestanas = ["Resumen Anual"] + MESES[6:] + MESES[:6]
hoja_seleccionada = st.sidebar.selectbox("📅 Selecciona Período:", lista_pestanas)

conn = st.connection("gsheets", type=GSheetsConnection)

# Leemos los datos una sola vez
try:
    df_raw = conn.read(worksheet=hoja_seleccionada, header=None, ttl=5)
except Exception as e:
    st.error(f"Error de conexión con Google Sheets: {e}")
    st.stop()

# === CASO A: RESUMEN ANUAL ===
if hoja_seleccionada == "Resumen Anual":
    st.header("📊 Resumen Anual")
    
    # 1. EVOLUCIÓN GASTOS (Busca 'Categoría')
    r, c = encontrar_coordenadas(df_raw, ["Categoría", "Categoria"])
    if r is not None:
        st.subheader("📉 Evolución de Gastos")
        df = cortar_desde_coordenada(df_raw, r, c, num_cols=14)
        st.dataframe(limpiar_y_formatear(df), hide_index=True)
    
    st.divider()
    
    # 2. SALDOS MENSUALES (Busca 'Saldos Mensuales', header abajo)
    r, c = encontrar_coordenadas(df_raw, ["Saldos Mensuales"])
    if r is not None:
        st.subheader("💰 Saldos Mensuales")
        df = cortar_desde_coordenada(df_raw, r + 1, c, num_cols=14, filas_datos=1)
        st.dataframe(limpiar_y_formatear(df), hide_index=True)
        
    st.divider()
    
    # 3. TABLAS INFERIORES
    c1, c2 = st.columns([1, 2])
    
    with c1:
        st.subheader("🏦 Mis Ahorros")
        # Busca directamente los encabezados de columna
        r, c = encontrar_coordenadas(df_raw, ["Fuente", "Monto Inicial"])
        if r is not None:
            df = cortar_desde_coordenada(df_raw, r, c, num_cols=5)
            st.dataframe(limpiar_y_formatear(df), hide_index=True)
        else:
            st.info("No se encontró la tabla de Ahorros.")
    
    with c2:
        st.subheader("🔄 Cambio de Dólares")
        # Busca encabezado singular o cotizacion
        r, c = encontrar_coordenadas(df_raw, ["Cambio de dolare", "Cotizacion"])
        if r is not None:
            df = cortar_desde_coordenada(df_raw, r, c, num_cols=13)
            st.dataframe(limpiar_y_formatear(df), hide_index=True)
        else:
            st.info("No se encontró la tabla de Cambio.")

# === CASO B: MESES INDIVIDUALES ===
else:
    st.write(f"📂 Viendo mes de: **{hoja_seleccionada}**")

    # 1. BALANCE (KPIs)
    r_bal, c_bal = encontrar_coordenadas(df_raw, ["Gastos fijos"], min_col=4)
    balance = pd.DataFrame()
    if r_bal is not None:
        balance = cortar_desde_coordenada(df_raw, r_bal, c_bal, num_cols=3, filas_datos=1)

    # 2. GASTOS (Izquierda)
    r_gastos, c_gastos = encontrar_coordenadas(df_raw, ["Vencimiento", "Categoría"])
    gastos = pd.DataFrame()
    if r_gastos is not None:
        gastos = cortar_desde_coordenada(df_raw, r_gastos, c_gastos, num_cols=5)

    # 3. INGRESOS (Derecha)
    r_ing, c_ing = encontrar_coordenadas(df_raw, ["Fecha", "Descripcion"], min_col=5, min_row=4)
    ingresos = pd.DataFrame()
    if r_ing is not None:
        ingresos = cortar_desde_coordenada(df_raw, r_ing, c_ing, num_cols=6)

    # --- VISUALIZACIÓN ---
    st.markdown("### 💰 Balance del Mes")
    if not balance.empty:
        c1, c2, c3 = st.columns(3)
        try:
            v1 = formato_pesos(balance.iloc[0, 0])
            v2 = formato_pesos(balance.iloc[0, 1])
            v3 = formato_pesos(balance.iloc[0, 2])
            c1.metric(balance.columns[0], v1)
            c2.metric(balance.columns[1], v2)
            c3.metric(balance.columns[2], v3)
        except: 
            st.warning("Datos encontrados pero formato incorrecto.")
    else: 
        st.warning("No se encontró tabla de Balance.")

    st.divider()
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("📉 Gastos")
        if not gastos.empty: 
            st.dataframe(limpiar_y_formatear(gastos), hide_index=True)
        else: 
            st.info("Sin gastos.")
    
    with col2:
        st.subheader("📈 Ingresos")
        if not ingresos.empty: 
            st.dataframe(limpiar_y_formatear(ingresos), hide_index=True)
        else: 
            st.info("Sin ingresos.")
