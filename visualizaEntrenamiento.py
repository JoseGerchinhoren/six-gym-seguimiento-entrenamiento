import streamlit as st
import pandas as pd
import io
from config import cargar_configuracion
import boto3
from datetime import datetime
import time
import re

# Obtener credenciales
aws_access_key, aws_secret_key, region_name, bucket_name = cargar_configuracion()

# Conectar a S3
s3 = boto3.client('s3', aws_access_key_id=aws_access_key, aws_secret_access_key=aws_secret_key, region_name=region_name)

csv_filename_cargas_combustible = "cargasCombustible.csv"

# Inicializar la lista de números de colectivo
numeros_colectivos = [
    1, 2, 3, 4, 6, 7, 8, 9, 10, 11, 12, 15, 18, 52,
    101, 102, 103, 104, 105, 106, 107, 108, 109, 110,
    111, 112, 113, 114, 115, 116, 117, 118, 119, 120, 121
]

def formatear_fecha(x):
    if pd.notnull(x):
        try:
            return x.strftime('%d/%m/%Y')
        except AttributeError:
            return x
    else:
        return ''
    
def visualizar_cargas_combustible():
    st.title("Visualizar Cargas de Combustible")

    # Cargar el archivo cargasCombustible.csv desde S3
    s3_csv_key_cargas_combustible = csv_filename_cargas_combustible
    try:
        response_cargas_combustible = s3.get_object(Bucket=bucket_name, Key=s3_csv_key_cargas_combustible)
        cargas_combustible_df = pd.read_csv(io.BytesIO(response_cargas_combustible['Body'].read()))
    except s3.exceptions.NoSuchKey:
        st.warning("No se encontró el archivo cargasCombustible.csv en S3")

    # Reemplazar comas por puntos en campos numéricos
    numeric_columns = ['idCarga', 'coche', 'contadorLitrosInicio', 'contadorLitrosCierre', 'litrosCargados', 'numeroPrecintoViejo', 'numeroPrecintoNuevo', 'precio']
    for column in numeric_columns:
        # Convertir la columna a tipo string antes de reemplazar comas por puntos
        cargas_combustible_df[column] = cargas_combustible_df[column].astype(str).str.replace(',', '.', regex=False)

    # Filtrar por número de coche
    numero_coche = st.selectbox("Filtrar por Número de Coche", ['Todos'] + sorted(numeros_colectivos))
    
    if numero_coche != 'Todos':
        cargas_combustible_df = cargas_combustible_df[cargas_combustible_df['coche'] == numero_coche]

    # Filtrar por lugar de carga
    lugar_carga_filtrado = st.selectbox("Filtrar por Lugar de Carga", ['Todos'] + sorted(cargas_combustible_df['lugarCarga'].unique()))
    
    if lugar_carga_filtrado != 'Todos':
        cargas_combustible_df = cargas_combustible_df[cargas_combustible_df['lugarCarga'] == lugar_carga_filtrado]

    # Filtro de fecha con checkbox
    if st.checkbox("Filtrar por Fecha"):
        # Convierte las fechas al formato datetime solo si no lo han sido
        cargas_combustible_df['fecha'] = pd.to_datetime(cargas_combustible_df['fecha'], errors='coerce', format='%d/%m/%Y')
        
        fecha_min = cargas_combustible_df['fecha'].min().date()
        # fecha_max = cargas_combustible_df['fecha'].max().date()

        fecha_seleccionada = st.date_input("Seleccionar Fecha", min_value=fecha_min, max_value=datetime.today())

        cargas_combustible_df = cargas_combustible_df[cargas_combustible_df['fecha'].dt.date == fecha_seleccionada]

    # Formatear las fechas en el DataFrame antes de mostrarlo, usando la función formatear_fecha
    cargas_combustible_df['fecha'] = cargas_combustible_df['fecha'].apply(formatear_fecha)

    # Ordenar el DataFrame por la columna 'idCarga' de forma descendente
    cargas_combustible_df = cargas_combustible_df.sort_values(by='idCarga', ascending=False)

    # Mostrar el DataFrame de cargas de combustible
    st.dataframe(cargas_combustible_df)

def editar_carga_combustible():
    st.header('Editar Carga de Combustible en Colectivo')

    # Ingresar el idCarga a editar
    id_carga_editar = st.number_input('Ingrese el idCarga a editar', value=None, min_value=0)

    if id_carga_editar is not None:

        # Descargar el archivo CSV desde S3 y cargarlo en un DataFrame
        try:
            csv_file_key = 'cargasCombustible.csv'
            response = s3.get_object(Bucket=bucket_name, Key=csv_file_key)
            cargas_combustible_df = pd.read_csv(io.BytesIO(response['Body'].read()))
        except s3.exceptions.NoSuchKey:
            st.warning("No se encontró el archivo CSV en S3.")
            return

        # Filtrar el DataFrame para obtener la carga específica por idCarga
        carga_editar_df = cargas_combustible_df[cargas_combustible_df['idCarga'] == id_carga_editar]

        if not carga_editar_df.empty:
            # Mostrar la información actual de la carga
            st.write("Información actual de la carga:")
            st.dataframe(carga_editar_df)

            # Mostrar campos para editar cada variable
            for column in carga_editar_df.columns:
                valor_actual = carga_editar_df.iloc[0][column]

                if column in ['idCarga', 'coche', 'contadorLitrosInicio', 'contadorLitrosCierre', 'litrosCargados', 'numeroPrecintoViejo', 'numeroPrecintoNuevo', 'precio']:
                    nuevo_valor = st.text_input(f"Nuevo valor para {column}", value=str(valor_actual))
                    # Verificar si es un número
                    if not nuevo_valor.isdigit():
                        st.warning(f"El valor para {column} debe ser un número.")
                        continue  # Salta a la próxima iteración si no es un número
                elif column == 'lugarCarga':
                    opciones_lugar_carga = ['Surtidor', 'Tanque']
                    nuevo_valor = st.selectbox(f"Nuevo valor para {column}", opciones_lugar_carga, index=opciones_lugar_carga.index(valor_actual))
                elif column in ['fecha', 'hora']:
                    formato = '%d/%m/%Y' if column == 'fecha' else '%H:%M'
                    nuevo_valor = st.text_input(f"Nuevo valor para {column}", value=valor_actual.strftime(formato) if isinstance(valor_actual, pd.Timestamp) else valor_actual)
                    # Verificar el formato de la fecha o hora ingresada
                    if column == 'fecha':
                        if re.match(r'^\d{2}/\d{2}/\d{4}$', nuevo_valor) is None:
                            st.warning("Formato incorrecto para fecha. Use el formato DD/MM/AAAA.")
                            continue
                    elif column == 'hora':
                        if re.match(r'^\d{2}:\d{2}$', nuevo_valor) is None:
                            st.warning("Formato incorrecto para hora. Use el formato HH:MM.")
                            continue
                else:
                    nuevo_valor = st.text_input(f"Nuevo valor para {column}", value=str(valor_actual))

                carga_editar_df.at[carga_editar_df.index[0], column] = nuevo_valor

            # Botón para guardar los cambios
            if st.button("Guardar modificación"):
                # Actualizar el DataFrame original con los cambios realizados
                cargas_combustible_df.update(carga_editar_df)

                # Guardar el DataFrame actualizado en S3
                with io.StringIO() as csv_buffer:
                    cargas_combustible_df.to_csv(csv_buffer, index=False)
                    s3.put_object(Body=csv_buffer.getvalue(), Bucket=bucket_name, Key=csv_file_key)

                st.success("¡Carga de combustible actualizada correctamente!")

                # Esperar 2 segundos antes de recargar la aplicación
                time.sleep(2)
                
                # Recargar la aplicación
                st.rerun()
        else:
            st.warning(f"No se encontró ninguna carga de combustible con el idCarga {id_carga_editar}")
        
    else: 
        st.warning('Ingrese el idCarga para editar la información de la carga')

def eliminar_carga_combustible():
    st.header('Eliminar Carga de Combustible en Colectivo')

    # Ingresar el idCarga a eliminar
    id_carga_eliminar = st.number_input('Ingrese el idCarga a eliminar', value=None, min_value=0)

    if id_carga_eliminar is not None:
        st.error(f'¿Está seguro de eliminar la carga de combustible con idCarga {id_carga_eliminar}?')

        if st.button('Eliminar Carga'):
            # Descargar el archivo CSV desde S3 y cargarlo en un DataFrame
            csv_file_key = 'cargasCombustible.csv'
            response = s3.get_object(Bucket=bucket_name, Key=csv_file_key)
            cargas_combustible_df = pd.read_csv(io.BytesIO(response['Body'].read()))

            # Verificar si la carga con el idCarga a eliminar existe en el DataFrame
            if id_carga_eliminar in cargas_combustible_df['idCarga'].values:
                # Eliminar la carga de combustible con el idCarga especificado
                cargas_combustible_df = cargas_combustible_df[cargas_combustible_df['idCarga'] != id_carga_eliminar]

                # Guardar el DataFrame actualizado en S3
                with io.StringIO() as csv_buffer:
                    cargas_combustible_df.to_csv(csv_buffer, index=False)
                    s3.put_object(Body=csv_buffer.getvalue(), Bucket=bucket_name, Key=csv_file_key)

                st.success(f"¡Carga de combustible con idCarga {id_carga_eliminar} eliminada correctamente!")

                # Esperar 2 segundos antes de recargar la aplicación
                time.sleep(2)
                
                # Recargar la aplicación
                st.rerun()
            else:
                st.error(f"No se encontró ninguna carga de combustible con el idCarga {id_carga_eliminar}")
    else:
        st.error('Ingrese el idCarga para eliminar la carga')

def main():
    visualizar_cargas_combustible()
    # Verificar si el usuario es admin
    if st.session_state.user_rol == "admin":
        editar_carga_combustible()
        eliminar_carga_combustible()
        
if __name__ == "__main__":
    main()
