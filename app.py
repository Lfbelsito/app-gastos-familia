import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Finanzas Familiares", layout="wide")
st.title("💸 Tablero de Control Familiar")

# --- FUNCIONES DE FORMATO (LA PARTE NUEVA) ---

def formato_pesos(valor):
    """Convierte un número en formato moneda argentino: $ 1.234.567"""
    try:
        # Si es texto vacío o guión, lo dejamos igual
        if valor == "" or valor == "-": return valor
        
        # Limpiamos el valor de posibles símbolos viejos para convertirlo a numero
        valor_str = str(valor).replace("$", "").replace(".", "").replace(",", ".")
        float_val = float(valor_str)
        
        # Formateamos: Puntos para miles, coma para decimales
        # {:,.0f} pone comas en miles (formato USA). Luego reemplazamos.
        return "$ " + "{:,.0f}".format(float_val).replace(",", ".")
    except:
        return valor

def limpiar_y_formatear_df(df, columnas_moneda=[]):
    """Limpia el dataframe y aplica formato pesos a las columnas que le digamos"""
    if df.empty: return df
    
    # 1. Convertir todo a String primero para manipular
    df = df.astype(str)
    
    # 2. Limpieza básica
    df = df.replace(["nan", "None", "NaT", "<NA>"], "-")
    
    # 3. Aplicar formato moneda SOLO a las columnas detectadas
    for col in df.columns:
        # Si la columna actual coincide con alguna de nuestra lista de dinero
        # Usamos "in" para que detecte "Monto", "Total en ARS", etc.
        if any(keyword.lower() in col.lower() for keyword in columnas_moneda):
            df[col] = df[col].apply(formato_pesos)
            
    return df

# --- FUNCIONES DE INTELIGENCIA (BÚSQUEDA EN EXCEL) ---

def encontrar_inicio_tabla(df_raw, fila_titulo, texto_clave):
    try:
        fila = df_raw.iloc[fila_titulo].astype(str).str.strip()
        for i, valor in enumerate(fila):
            if texto_clave.lower() in valor.lower():
                return i
        return None
    except:
        return None

def cortar_tabla_inteligente(df_raw, fila_titulo, palabra_clave, num_columnas, fila_datos_offset=1):
    try:
        col_inicio = encontrar_inicio_tabla(df_raw, fila_titulo, palabra_clave)
        if col_inicio is None: return pd.DataFrame()
            
        col_fin = col_inicio + num_columnas
        
        # Header y Datos
        titulos = df_raw.iloc[fila_titulo, col_inicio:col_fin].astype(str).str.strip()
        titulos = [f"Col_{i}" if t in ["nan", ""] else t for i, t in enumerate(titulos)]
        
        fila_datos = fila_titulo + fila_datos_offset
        datos = df_raw.iloc[fila_datos:, col_inicio:col_fin].copy()
        datos.columns = titulos
        
        # Limpieza de filas vacías
        datos = datos[datos.iloc[:, 0].ne("nan") & datos.iloc[:, 0].ne("")]
        
        return datos
    except:
        return pd.DataFrame()

# --- NAVEGACIÓN ---
lista_pestanas = [
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Resumen Anual"
]
hoja_seleccionada = st.sidebar.selectbox("Selecciona el Mes:", lista_pestanas)

conn = st.connection("gsheets", type=GSheetsConnection)

# Lista de palabras clave que queremos que se vean como DINERO
COLUMNAS_DINERO = ["Monto", "Total", "Gastos", "Ingresos", "Ahorro", "Cotizacion"]

try:
    if hoja_seleccionada == "Resumen Anual":
        st.info("📊 Vista de Resumen Anual")
        df = conn.read(worksheet=hoja_seleccionada, ttl=5)
        st.dataframe(limpiar_y_formatear_df(df, COLUMNAS_DINERO), use_container_width=True)

    else:
        st.write(f"📂 Cargando datos de: **{hoja_seleccionada}**...")
        df_raw = conn.read(worksheet=hoja_seleccionada, header=None, ttl=5)

        # 1. GASTOS (Busca 'Vencimiento' o 'Categoría' en fila 1)
        gastos = cortar_tabla_inteligente(
            df_raw, fila_titulo=0, palabra_clave="Vencimiento", num_columnas=5
        )
        if gastos.empty:
            gastos = cortar_tabla_inteligente(df_raw, 0, "Categoría", 5)

        # 2. BALANCE (Busca 'Gastos fijos' en fila 2)
        balance_full = cortar_tabla_inteligente(
            df_raw, fila_titulo=1, palabra_clave="Gastos fijos", num_columnas=3
        )
        balance = balance_full.iloc[:1] if not balance_full.empty else pd.DataFrame()

        # 3. INGRESOS (Busca 'Fecha' en fila 6)
        ingresos = cortar_tabla_inteligente(
            df_raw, fila_titulo=5, palabra_clave="Fecha", num_columnas=6
        )

        # --- APLICAR MAQUILLAJE (FORMATOS) ---
        gastos = limpiar_y_formatear_df(gastos, COLUMNAS_DINERO)
        ingresos = limpiar_y_formatear_df(ingresos, COLUMNAS_DINERO)
        # El balance lo formateamos dato por dato abajo para los metrics

        # --- VISUALIZACIÓN ---
        
        st.markdown("### 💰 Balance del Mes")
        if not balance.empty:
            c1, c2, c3 = st.columns(3)
            # Extraemos y formateamos individualmente
            v1 = formato_pesos(balance.iloc[0, 0])
            v2 = formato_pesos(balance.iloc[0, 1])
            v3 = formato_pesos(balance.iloc[0, 2])
            
            c1.metric(balance.columns[0], v1)
            c2.metric(balance.columns[1], v2)
            c3.metric(balance.columns[2], v3)
        else:
            st.warning("No se encontró el Balance.")

        st.divider()

        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📉 Gastos")
            if not gastos.empty:
                st.dataframe(gastos, hide_index=True, use_container_width=True)
            else:
                st.info("Sin datos de gastos.")

        with col2:
            st.subheader("📈 Ingresos")
            if not ingresos.empty:
                st.dataframe(ingresos, hide_index=True, use_container_width=True)
            else:
                st.info("Sin datos de ingresos.")

except Exception as e:
    st.error("⚠️ Ocurrió un error.")
    st.code(str(e))
