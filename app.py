import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Finanzas Familiares", layout="wide")
st.title("💸 Tablero de Control Familiar")

# --- FUNCIONES DE LIMPIEZA E INTELIGENCIA ---

def encontrar_inicio_tabla(df_raw, fila_titulo, texto_clave):
    """
    Busca en qué columna está el 'texto_clave' dentro de la 'fila_titulo'.
    Devuelve el índice de la columna. Si no lo encuentra, devuelve None.
    """
    try:
        # Obtenemos la fila de títulos como texto
        fila = df_raw.iloc[fila_titulo].astype(str).str.strip()
        
        # Buscamos la columna que contenga la palabra clave (ej: "Fecha" o "Gastos")
        for i, valor in enumerate(fila):
            if texto_clave.lower() in valor.lower():
                return i
        return None
    except:
        return None

def formatear_fecha(valor):
    """Intenta convertir números de Excel o textos a formato fecha legible"""
    try:
        # Si es un número (formato Excel, ej: 45100)
        if isinstance(valor, (int, float)):
            return pd.to_datetime(valor, unit='D', origin='1899-12-30').strftime('%d/%m')
        # Si ya es texto o fecha
        return pd.to_datetime(valor).strftime('%d/%m')
    except:
        return valor

def limpiar_datos(df):
    """Limpia los datos para evitar errores y formatear visualmente"""
    if df.empty: return df
    
    # 1. Convertir todo a String primero para evitar errores de JSON
    df = df.astype(str)
    
    # 2. Reemplazar "nan", "None", "NaT" por guiones
    df = df.replace(["nan", "None", "NaT", "<NA>"], "")
    
    return df

def cortar_tabla_inteligente(df_raw, fila_titulo, palabra_clave, num_columnas, fila_datos_offset=1):
    """
    1. Busca dónde empieza la tabla usando la palabra clave.
    2. Corta exactamente 'num_columnas' hacia la derecha.
    """
    try:
        # Paso 1: Buscar coordenada X (Columna)
        col_inicio = encontrar_inicio_tabla(df_raw, fila_titulo, palabra_clave)
        
        if col_inicio is None:
            return pd.DataFrame() # No se encontró la tabla
            
        col_fin = col_inicio + num_columnas
        
        # Paso 2: Cortar Header y Datos
        # Header
        titulos = df_raw.iloc[fila_titulo, col_inicio:col_fin].astype(str).str.strip()
        # Parche para títulos vacíos (evita error duplicado)
        titulos = [f"Col_{i}" if t in ["nan", ""] else t for i, t in enumerate(titulos)]
        
        # Datos (empiezan 'fila_datos_offset' filas abajo del título)
        fila_datos = fila_titulo + fila_datos_offset
        datos = df_raw.iloc[fila_datos:, col_inicio:col_fin].copy()
        datos.columns = titulos
        
        # Paso 3: Limpieza de filas vacías (Si la primera columna clave está vacía, chau fila)
        datos = datos[datos.iloc[:, 0].ne("nan") & datos.iloc[:, 0].ne("")]
        
        # Paso 4: Formateo final
        datos = limpiar_datos(datos)
        
        return datos
    except Exception as e:
        return pd.DataFrame()

# --- NAVEGACIÓN ---
lista_pestanas = [
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Resumen Anual"
]
hoja_seleccionada = st.sidebar.selectbox("Selecciona el Mes:", lista_pestanas)

conn = st.connection("gsheets", type=GSheetsConnection)

try:
    if hoja_seleccionada == "Resumen Anual":
        st.info("📊 Vista de Resumen Anual")
        df = conn.read(worksheet=hoja_seleccionada, ttl=5)
        st.dataframe(limpiar_datos(df), use_container_width=True)

    else:
        st.write(f"📂 Cargando datos de: **{hoja_seleccionada}**...")
        
        # Leemos TODO el mapa "en crudo"
        df_raw = conn.read(worksheet=hoja_seleccionada, header=None, ttl=5)

        # -----------------------------------------------------------
        # EXTRACCIÓN INTELIGENTE (BUSCA LAS PALABRAS)
        # -----------------------------------------------------------

        # 1. GASTOS
        # Busca en Fila 1 (Excel 2) la palabra "Vencimiento" o "Fecha" o "Categoría"
        # Corta 5 columnas (A hasta E)
        gastos = cortar_tabla_inteligente(
            df_raw, fila_titulo=0, palabra_clave="Vencimiento", num_columnas=5, fila_datos_offset=1
        )
        # Intento secundario si la palabra clave era otra
        if gastos.empty:
            gastos = cortar_tabla_inteligente(
                df_raw, fila_titulo=0, palabra_clave="Categoría", num_columnas=5
            )

        # 2. BALANCE (RESUMEN)
        # Busca en Fila 1 (Excel 2) la palabra "Gastos fijos"
        # Corta 3 columnas (I, J, K)
        # OJO: Aquí los datos están justo en la fila siguiente (offset=1) pero solo queremos 1 fila de datos
        balance_full = cortar_tabla_inteligente(
            df_raw, fila_titulo=1, palabra_clave="Gastos fijos", num_columnas=3
        )
        # Nos quedamos solo con la primera fila de datos (el resto es basura o la tabla de abajo)
        if not balance_full.empty:
            balance = balance_full.iloc[:1] 
        else:
            balance = pd.DataFrame()

        # 3. INGRESOS
        # Busca en Fila 5 (Excel 6) la palabra "Fecha" (para evitar confundirse con la fecha de gastos)
        # Corta 6 columnas (I hasta N)
        ingresos = cortar_tabla_inteligente(
            df_raw, fila_titulo=5, palabra_clave="Fecha", num_columnas=6
        )
        # Si falla, busca "Descripcion" en esa misma fila
        if ingresos.empty:
            ingresos = cortar_tabla_inteligente(
                df_raw, fila_titulo=5, palabra_clave="Descrip", num_columnas=6
            )


        # --- MOSTRAR RESULTADOS ---
        
        st.markdown("### 💰 Balance del Mes")
        if not balance.empty:
            c1, c2, c3 = st.columns(3)
            # Extraemos valores directos
            val_1 = balance.iloc[0, 0]
            val_2 = balance.iloc[0, 1]
            val_3 = balance.iloc[0, 2]
            
            # Títulos de las columnas
            lbl_1 = balance.columns[0]
            lbl_2 = balance.columns[1]
            lbl_3 = balance.columns[2]

            c1.metric(lbl_1, val_1)
            c2.metric(lbl_2, val_2)
            c3.metric(lbl_3, val_3, delta_color="normal")
        else:
            st.warning("No se encontró la tabla de Balance (Busqué 'Gastos fijos' en la fila 2).")

        st.divider()

        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📉 Gastos")
            if not gastos.empty:
                st.dataframe(gastos, hide_index=True, use_container_width=True)
            else:
                st.info("No encontré la tabla de Gastos (Busqué 'Vencimiento' en la fila 1).")

        with col2:
            st.subheader("📈 Ingresos")
            if not ingresos.empty:
                st.dataframe(ingresos, hide_index=True, use_container_width=True)
            else:
                st.info("No encontré la tabla de Ingresos (Busqué 'Fecha' en la fila 6).")

except Exception as e:
    st.error("⚠️ Error técnico:")
    st.code(str(e))
