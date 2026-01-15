import streamlit as st
import pandas as pd
import os
import io

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Validador Logístico", layout="wide", page_icon="🚚")

# --- CONFIGURACIÓN DE RUTAS ---
PATH_MAESTRO = "data/maestro.csv" 

st.title("🚚 Control planning CDMA")
st.markdown("Coteja el planning diario de Trafico contra la el calendario de tiendas")

if not os.path.exists(PATH_MAESTRO):
    st.error(f"⚠️ No se encontró el archivo maestro en: {PATH_MAESTRO}")
    st.stop()

# --- CARGA DEL PLANNING DIARIO ---
st.subheader("1. Subir Planning diario de Tráfico")
file_planning = st.file_uploader("Arrastra aquí el archivo del Planning", type=['xlsx', 'csv'])

def obtener_letra_dia(fecha):
    if pd.isna(fecha): return "?"
    # Mapeo estándar: L, M, X (Miércoles), J, V, S, D
    mapa = {0: 'L', 1: 'M', 2: 'X', 3: 'J', 4: 'V', 5: 'S', 6: 'D'}
    return mapa[fecha.weekday()]

if file_planning:
    try:
        # 1. Cargar Maestro (Traemos Pto Op, CALENDARIZADO y Zona Geografica)
        df_maestro = pd.read_csv(PATH_MAESTRO, sep=None, engine='python', encoding='latin-1')
        df_maestro.columns = df_maestro.columns.str.strip()
        
        # Renombrar columnas del maestro para procesar
        df_maestro = df_maestro.rename(columns={
            'Pto Op': 'ID_Tienda', 
            'CALENDARIZADO': 'Frecuencia_Maestro',
            'Zona Geografica': 'Zona'
        })
        
        # 2. Cargar Planning (Detección de formato)
        if file_planning.name.endswith(('xlsx', 'xls')):
            df_planning = pd.read_excel(file_planning)
        else:
            df_planning = pd.read_csv(file_planning, sep=None, engine='python', encoding='latin-1')

        df_planning.columns = df_planning.columns.str.strip()

        # --- PROCESAMIENTO ---
        # Convertir Fecha y calcular día de la semana (L, M, X...)
        df_planning['Fecha_Entrega'] = pd.to_datetime(df_planning['FECHA'], errors='coerce')
        df_planning['Dia_Semana_Plan'] = df_planning['Fecha_Entrega'].apply(obtener_letra_dia)
        
        # Normalizar IDs de tienda a entero
        df_planning['ID_Tienda'] = pd.to_numeric(df_planning['TIENDA'], errors='coerce').fillna(0).astype(int)
        df_maestro['ID_Tienda'] = pd.to_numeric(df_maestro['ID_Tienda'], errors='coerce').fillna(0).astype(int)

        # 3. Cruce de Datos (Traemos Frecuencia y Zona del maestro)
        df_final = pd.merge(
            df_planning, 
            df_maestro[['ID_Tienda', 'Frecuencia_Maestro', 'Zona']], 
            on='ID_Tienda', 
            how='left'
        )

        # 4. Lógica de Validación (Comparar día de la FECHA vs CALENDARIZADO)
        def validar(row):
            dia_planificado = str(row['Dia_Semana_Plan'])
            frecuencia_permitida = str(row['Frecuencia_Maestro'])
            
            if pd.isna(row['Frecuencia_Maestro']) or frecuencia_permitida == "" or frecuencia_permitida == "nan": 
                return "⚠️ No en Maestro"
            
            # Si el día de la fecha (L, M, X, etc) está dentro de la frecuencia del maestro, es OK
            return "✅ OK" if dia_planificado in frecuencia_permitida else "❌ No Reparte"

        df_final['Estado'] = df_final.apply(validar, axis=1)

        # --- ORDENAR Y FILTRAR ---
        # Priorizamos las columnas que necesitas ver primero
        cols_visualizacion = ['Estado', 'ID_Tienda', 'NOMBRE_TIENDA', 'Zona', 'FECHA', 'Dia_Semana_Plan', 'Frecuencia_Maestro', 'EXPEDICION', 'VIAJE_TMS']
        
        # Filtrar solo las que existen para evitar errores si falta alguna columna en el planning
        cols_existentes = [c for c in cols_visualizacion if c in df_final.columns]
        
        st.subheader("2. Resultados del Análisis")
        solo_errores = st.checkbox("Mostrar solo errores (Tiendas fuera de frecuencia o faltantes)")
        
        df_resultado = df_final[cols_existentes]
        if solo_errores:
            df_resultado = df_resultado[df_resultado['Estado'] != "✅ OK"]

        # --- MOSTRAR TABLA ---
        st.dataframe(df_resultado.style.applymap(
            lambda v: 'background-color: #ffcccc' if '❌' in str(v) else ('background-color: #fff4cc' if '⚠️' in str(v) else ''),
            subset=['Estado']
        ), use_container_width=True)

        # --- BOTÓN DE DESCARGA ---
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_resultado.to_excel(writer, index=False, sheet_name='Validacion_Rutas')
        
        st.download_button(
            label="📥 Descargar Reporte de Validación",
            data=output.getvalue(),
            file_name=f"Control_Planning_{df_planning['FECHA'].iloc[0]}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    except Exception as e:
        st.error(f"Error al procesar el archivo: {e}")
        st.info("Asegúrate de que el maestro esté en 'data/maestro.csv' con las columnas 'Pto Op', 'CALENDARIZADO' y 'Zona Geografica'.")