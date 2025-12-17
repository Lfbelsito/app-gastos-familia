import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Finanzas Familiares", layout="wide", page_icon="💰")
st.title("💸 Tablero de Control Familiar")

# --- LISTAS Y CONFIGURACIÓN ---
MESES = [
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", 
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
]
COLUMNAS_DINERO = [
    "Monto", "Total", "Gastos", "Ingresos", "Ahorro", 
    "Cotizacion", "Saldo", "Valor", "Pesos", "USD", "Ars"
] + MESES

# --- FUNCIONES ---

def formato_pesos(valor):
    """Convierte números a formato $"""
    try:
        val_str = str(valor).strip()
        if val_str in ["", "-", "nan", "None", "0", "0.0"]: return "-"
        val_str = val_str.replace("$", "").replace("USD", "").replace("Ars", "").strip()
        val_str = val_str.replace(".", "").replace(",", ".")
        val_float = float(val_str)
        return "$ " + "{:,.0f}".format(val_float).replace(",", ".")
    except:
        return valor

def limpiar_y_formatear(df):
    """Limpia y aplica formato dinero"""
    if df.empty: return df
    df = df.astype(str).replace(["nan", "None", "<NA>"], "-")
    for col in df.columns:
        if any(k.lower() in col.lower() for k in COLUMNAS_DINERO):
            if "descrip" not in col.lower() and "moneda" not in col.lower():
                df[col] = df[col].apply(formato_pesos)
    return df

def encontrar_coordenadas(df_raw, palabras_clave, min_col=0, min_row=0):
    """RADAR: Escanea toda la hoja buscando la palabra clave"""
    try:
        zona = df_raw.iloc[min_row:, min_col:]
        for r_idx, row in zona.iterrows():
            for c_idx, val in enumerate(row):
                val_str = str(val).lower()
                for palabra in palabras_clave:
                    # Usamos 'match' exacto o parcial fuerte para evitar falsos positivos
                    if palabra.lower() in val_str:
                        return r_idx, (c_idx + min_col)
        return None, None
    except:
        return None, None

def cortar_desde_coordenada(df_raw, fila, col, num_cols, filas_datos=None):
    """Corta la tabla asumiendo que (fila, col) es el primer encabezado"""
    try:
        # Headers
        headers = df_raw.iloc[fila, col : col + num_cols].astype(str).str.strip().tolist()
        # Parche para headers vacíos
        headers = [f"C{i}" if h in ["nan", ""] else h for i,h in enumerate(headers)]
        
        inicio_datos = fila + 1
        
        if filas_datos:
            df = df_raw.iloc[inicio_datos : inicio_datos + filas_datos, col : col + num_cols].copy()
        else:
            df = df_raw.iloc[inicio_datos:, col : col + num_cols].copy()
            # Cortar si la primera columna (ej: Fuente) está vacía
            df = df[df.iloc[:, 0].ne("nan") & df.iloc[:, 0].ne("")]
            
        df.columns = headers
        return df
    except:
        return pd.DataFrame()

# --- APP PRINCIPAL ---

lista_pestanas = ["Resumen Anual"] + MESES[6:] + MESES[:6]
hoja_seleccionada = st.sidebar.selectbox("📅 Selecciona Período:", lista_pestanas)

conn = st.connection("gsheets", type=GSheetsConnection)

try:
    df_raw = conn.read(worksheet=hoja_seleccionada, header=None, ttl=5)
    
    # ==========================================
    # RESUMEN ANUAL
    # ==========================================
    if hoja_seleccionada == "Resumen Anual":
        st.header("📊 Resumen Anual")
        
        # 1. EVOLUCIÓN (Busca 'Categoría')
        r, c = encontrar_coordenadas(df_raw, ["Categoría", "Categoria"])
        if r is not None:
            st.subheader("📉 Evolución de Gastos")
            df = cortar_desde_coordenada(df_raw, r, c, num_cols=14)
            st.dataframe(limpiar_y_formatear(df), hide_index=True)
        
        st.divider()
        
        # 2. SALDOS MENSUALES (Busca 'Saldos Mensuales')
        r, c = encontrar_coordenadas(df_raw, ["Saldos Mensuales"])
        if r is not None:
            # Aquí sí sumamos +1 porque lo que buscamos es el Título Verde
            df = cortar_desde_coordenada(df_raw, r + 1, c, num_cols=14, filas_datos=1)
            st.subheader("💰 Saldos Mensuales")
            st.dataframe(limpiar_y_formatear(df), hide_index=True)
            
        st.divider()
        
        # 3. TABLAS INFERIORES (AQUÍ ESTABA EL PROBLEMA)
        c1, c2 = st.columns([1, 2])
        
        with c1:
            st.subheader("🏦 Mis Ahorros")
            # ESTRATEGIA: Buscar directamente el encabezado de columna "Fuente"
            # O "Monto Inicial" que es único de esa tabla.
            r, c = encontrar_coordenadas(df_raw, ["Fuente", "Monto Inicial"])
            
            if r is not None:
                df = cortar_desde_coordenada(df_raw, r, c, num_cols=5)
                st.dataframe(limpiar_y_formatear(df), hide_index=True)
            else:
                st.info("No encontré la columna 'Fuente' ni 'Monto Inicial'.")
        
        with c2:
            st.subheader("🔄 Cambio de Dólares")
            # ESTRATEGIA: Buscar "Cambio de dolare" (SINGULAR) que es el encabezado real
            # O "Cotizacion".
            r, c = encontrar_coordenadas(df_raw, ["Cambio de dolare", "Cotizacion"])
            
            if r is not None:
                # Si encontró el header, cortamos desde ahí (13 columnas ancho para cubrir todo el año)
                df = cortar_desde_coordenada(df_raw, r, c, num_cols=14)
                st.dataframe(limpiar_y_formatear(df), hide_index=True)
            else:
                st.info("No encontré la columna 'Cambio de dolare'.")

    # ==========================================
    # MESES INDIVIDUALES (ESTO YA FUNCIONABA)
    # ==========================================
    else:
        st.write(f"📂 Viendo mes de: **{hoja_seleccionada}**")

        # Balance
        r_bal, c_bal = encontrar_coordenadas(df_raw, ["Gastos fijos"], min_col=4)
        balance = pd.DataFrame()
        if r_bal is not None:
            balance = cortar_desde_coordenada(df_raw, r_bal, c_bal, num_cols=3, filas_datos=1)

        # Gastos
        r_gastos, c_gastos = encontrar_coordenadas(df_raw, ["Vencimiento", "Categoría"])
        gastos = pd.DataFrame()
