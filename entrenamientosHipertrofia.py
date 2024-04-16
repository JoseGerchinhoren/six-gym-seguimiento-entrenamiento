import streamlit as st
import pandas as pd
import boto3
import io
from io import StringIO
import altair as alt

# Obtener credenciales
from config import cargar_configuracion

# Obtener fecha actual en Argentina
from horario import obtener_fecha_argentina

# Conectar a S3
def conectar_s3():
    aws_access_key, aws_secret_key, region_name, bucket_name = cargar_configuracion()
    return boto3.client('s3', aws_access_key_id=aws_access_key, aws_secret_access_key=aws_secret_key, region_name=region_name), bucket_name

def cargar_dataframe_desde_s3(s3, bucket_name):
    csv_filename = "entrenamientosHipertrofia.csv"
    try:
        response = s3.get_object(Bucket=bucket_name, Key=csv_filename)
        return pd.read_csv(io.BytesIO(response['Body'].read()))
    except s3.exceptions.NoSuchKey:
        st.warning("No se encontró el archivo CSV en S3.")
        return pd.DataFrame()

def upload_to_s3(data, s3, bucket_name):
    csv_filename = "entrenamientosHipertrofia.csv"
    csv_buffer = StringIO()
    data.to_csv(csv_buffer, index=False)
    csv_buffer.seek(0)
    s3.put_object(Bucket=bucket_name, Key=csv_filename, Body=csv_buffer.getvalue())

def validar_entradas(socio, grupoMuscular, musculo, ejercicio, serie, peso, repeticiones):
    errores = []

    # Validar campos obligatorios
    if not socio:
        errores.append("El nombre del socio es obligatorio.")
    if not grupoMuscular:
        errores.append("El grupo muscular es obligatorio.")
    if not musculo:
        errores.append("El músculo es obligatorio.")
    if not ejercicio:
        errores.append("El nombre del ejercicio es obligatorio.")
    
    # Validar valores numéricos
    if serie is None or serie < 0:
        errores.append("La serie debe ser un valor numérico positivo.")
    if peso is None or peso < 0:
        errores.append("El peso debe ser un valor numérico positivo.")
    if repeticiones is None or repeticiones < 0:
        errores.append("El número de repeticiones debe ser un valor numérico positivo.")

    return errores

def registra_entrenamientos_hipertrofia():
    # Conectar a S3
    s3, bucket_name = conectar_s3()

    # Cargar DataFrame desde S3
    df_total = cargar_dataframe_desde_s3(s3, bucket_name)

    st.subheader("Ingrese nombre, apellido y luego seleccione")
    # Variables ingresadas por el cliente
    socio_input = st.text_input('Nombre y Apellido')

    # Filtrar los nombres que coinciden con lo que se ha ingresado
    nombres_coincidentes = df_total['socio'][df_total['socio'].str.contains(socio_input, case=False)].unique()

    # Selectbox para mostrar nombres coincidentes
    socio = st.selectbox('Seleccionar Socio', [socio_input] + list(nombres_coincidentes))

    # Filtrar los datos del DataFrame según el socio seleccionado
    df_entrenamientos_socio = df_total[df_total['socio'] == socio]

    with st.expander('Nuevo Entrenamiento de Hipertrofia'):
        st.markdown("<h1 style='text-align: center;'>Registrá Entrenamiento de Hipertrofia</h1>", unsafe_allow_html=True)

        # grupoMuscular = st.selectbox('Grupo Muscular', ['','Tren Superior', 'Tren Inferior', 'Zona Media'])

        # if grupoMuscular == 'Tren Superior':
        #     opciones_musculos = ['','Pecho', 'Espalda', 'Hombros', 'Biceps', 'Triceps']            
        # elif grupoMuscular == 'Tren Inferior':
        #     opciones_musculos = ['', 'Cuádriceps', 'Isquiotibiales', 'Glúteos', 'Pantorrillas']
        # elif grupoMuscular == 'Zona Media':
        #     opciones_musculos = ['abdominales']
        # else:
        #     opciones_musculos = []

        # musculo = st.selectbox('Músculo', opciones_musculos)

        # if musculo:
        #     ejercicios_disponibles = df_entrenamientos_socio[df_entrenamientos_socio['musculo'] == musculo]['ejercicio'].unique()
        # else:
        #     ejercicios_disponibles = []

        # ejercicio_input = st.text_input('Ejercicio')

        # ejercicios_filtrados = [ejercicio for ejercicio in ejercicios_disponibles if ejercicio_input.lower() in ejercicio.lower()]

        # ejercicio = st.selectbox('Seleccione Ejercicio', [ejercicio_input] + ejercicios_filtrados)

        # serie = st.number_input('Serie', min_value=0, value=1, step=1)

        # Aquí se modificó la lógica para cargar automáticamente los datos del último ejercicio
        # realizado por el socio en los campos respectivos
        if not df_entrenamientos_socio.empty:
            ultima_fila_socio = df_entrenamientos_socio.iloc[-1]

            gruposMusculares = ['Tren Superior', 'Tren Inferior', 'Zona Media']

            grupoMuscular = st.selectbox('Grupo Muscular', gruposMusculares, index=gruposMusculares.index(ultima_fila_socio.get('grupoMuscular', '')) if ultima_fila_socio.get('grupoMuscular') in gruposMusculares else 0)

            if grupoMuscular == 'Tren Superior':
                opciones_musculos = ['','Pecho', 'Espalda', 'Hombros', 'Biceps', 'Triceps']            
            elif grupoMuscular == 'Tren Inferior':
                opciones_musculos = ['', 'Cuádriceps', 'Isquiotibiales', 'Glúteos', 'Pantorrillas']
            elif grupoMuscular == 'Zona Media':
                opciones_musculos = ['abdominales']
            else:
                opciones_musculos = []

            musculo = st.selectbox('Músculo', opciones_musculos, index=opciones_musculos.index(ultima_fila_socio.get('musculo', '')) if ultima_fila_socio.get('musculo') in opciones_musculos else 0)


            if musculo:
                ejercicios_disponibles = df_entrenamientos_socio[df_entrenamientos_socio['musculo'] == musculo]['ejercicio'].unique()
            else:
                ejercicios_disponibles = []

            ejercicio_input = st.text_input('Ejercicio', value=ultima_fila_socio.get('ejercicio', ''))

            ejercicios_filtrados = [ejercicio for ejercicio in ejercicios_disponibles if ejercicio_input.lower() in ejercicio.lower()]

            ejercicio = st.selectbox('Seleccione Ejercicio', [ejercicio_input] + ejercicios_filtrados)

            serie = st.number_input('Serie', min_value=0, value=int(ultima_fila_socio.get('serie', 1)), step=1)


            peso = st.number_input('Peso',  min_value=0, value=ultima_fila_socio.get('peso'), step=1)

            repeticiones = st.number_input('Repeticiones',  min_value=0, value=ultima_fila_socio.get('repeticiones'), step=1)
        else:
            peso = st.number_input('Peso',  min_value=0, value=None, step=1)
            repeticiones = st.number_input('Repeticiones',  min_value=0, value=None, step=1)

        observaciones = st.text_input('Observaciones')

        # Botón para guardar el registro
        if st.button('Guardar Entrenamiento de Hipertrofia'):
            # Validar las entradas del usuario
            errores = validar_entradas(socio, grupoMuscular, musculo, ejercicio, serie, peso, repeticiones)

            if errores:
                st.error("Por favor, corrija los siguientes errores:")
                for error in errores:
                    st.error(error)
            else:
                fecha = obtener_fecha_argentina().strftime('%d/%m/%Y')
                hora = obtener_fecha_argentina().strftime('%H:%M')
                usuario = st.session_state.get("user_nombre_apellido", "")

                # Crear un DataFrame con los datos ingresados
                data = {
                    'idEjercicioHiper': [df_total['idEjercicioHiper'].max() + 1 if not df_total.empty else 0],
                    'fecha': [fecha],
                    'hora': [hora],
                    'socio': [socio],
                    'grupoMuscular': [grupoMuscular],
                    'musculo': [musculo],
                    'ejercicio': [ejercicio],
                    'serie': [serie],
                    'peso': [peso],
                    'repeticiones': [repeticiones],
                    'observaciones': [observaciones],
                    'usuario': [usuario]
                }
                df_new = pd.DataFrame(data)

                # Concatenar el nuevo DataFrame con el DataFrame total
                df_total = pd.concat([df_total, df_new], ignore_index=True)

                # Cargar los datos en el archivo CSV en S3
                upload_to_s3(df_total, s3, bucket_name)

                st.success('Entrenamiento guardado con éxito!')
    
    if socio:
        with st.expander(f'Visualizar Entrenamientos de Hipertrofia'):
            visualizar_entrenamientos_hiper(socio)

def visualizar_entrenamientos_hiper(socio):
    st.markdown(f"<h1 style='text-align: center;'>Entrenamientos de Hipertrofia de {socio}</h1>", unsafe_allow_html=True)

    # Conectar a S3
    s3, bucket_name = conectar_s3()

    # Cargar DataFrame desde S3
    df_total = cargar_dataframe_desde_s3(s3, bucket_name)

    # Filtrar el DataFrame por el socio seleccionado
    df_total = df_total[df_total['socio'] == socio]

    if df_total.empty:
        st.warning("No hay entrenamientos de hipertrofia registrados.")
        return

    # Renombrar las columnas del DataFrame
    df_total = df_total.rename(columns={
        'idEjercicioHiper': 'ID',
        'fecha': 'Fecha',
        'hora': 'Hora',
        'socio': 'Socio',
        'grupoMuscular': 'Grupo Muscular',
        'musculo': 'Músculo',
        'ejercicio': 'Ejercicio',
        'serie': 'Serie',
        'peso': 'Peso',
        'repeticiones': 'Repeticiones',
        'observaciones': 'Observaciones',
        'usuario': 'Entrenador'
    })

    # Establecer el orden deseado de las columnas
    column_order = ['Fecha', 'Grupo Muscular', 'Músculo', 'Ejercicio', 'Serie', 'Peso', 'Repeticiones', 'Hora', 'Observaciones', 'Entrenador','ID']
    df_total = df_total.reindex(columns=column_order)

    # Ordenar el DataFrame por el ID de Ejercicio de Hipertrofia de forma descendente
    df_total = df_total.sort_values(by='ID', ascending=False)

    # Mostrar el DataFrame de entrenamientos de hipertrofia
    st.dataframe(df_total)

    st.markdown(f"<h1 style='text-align: center;'>Peso levantado por día de {socio}</h1>", unsafe_allow_html=True)

    # Calcular peso total levantado por día
    df_total['Fecha'] = pd.to_datetime(df_total['Fecha'])
    df_total['Peso Total'] = df_total['Peso'] * df_total['Repeticiones']
    peso_total_por_dia = df_total.groupby('Fecha')['Peso Total'].sum().reset_index()

    # Gráfico de línea con peso total levantado por día
    line_chart = alt.Chart(peso_total_por_dia).mark_line().encode(
        x='Fecha:T',
        y='Peso Total:Q',
        tooltip=['Fecha:T', 'Peso Total:Q']
    ).properties(
        width=600,
        height=400
    )

    # Capa adicional con puntos sobre el gráfico
    points = alt.Chart(peso_total_por_dia).mark_circle(
        size=100,
        color='red',
        opacity=0.5
    ).encode(
        x='Fecha:T',
        y='Peso Total:Q'
    )

    # Combinar el gráfico de línea y los puntos
    chart = line_chart + points

    st.altair_chart(chart)

def main():
    
    # with st.expander('Nuevo Entrenamiento de Hipertrofia'):
    registra_entrenamientos_hipertrofia()

if __name__ == '__main__':
    main()


# def formatear_fecha(x):
#     if pd.notnull(x):
#         try:
#             return x.strftime('%d/%m/%Y')
#         except AttributeError:
#             return x
#     else:
#         return ''

# def visualizar_cargas_combustible():
#     st.title("Visualizar Cargas de Combustible")

#     # Cargar el archivo cargasCombustible.csv desde S3
#     s3_csv_key_cargas_combustible = csv_filename_cargas_combustible
#     try:
#         response_cargas_combustible = s3.get_object(Bucket=bucket_name, Key=s3_csv_key_cargas_combustible)
#         cargas_combustible_df = pd.read_csv(io.BytesIO(response_cargas_combustible['Body'].read()))
#     except s3.exceptions.NoSuchKey:
#         st.warning("No se encontró el archivo cargasCombustible.csv en S3")

#     # Reemplazar comas por puntos en campos numéricos
#     numeric_columns = ['idCarga', 'coche', 'contadorLitrosInicio', 'contadorLitrosCierre', 'litrosCargados', 'numeroPrecintoViejo', 'numeroPrecintoNuevo', 'precio']
#     for column in numeric_columns:
#         # Convertir la columna a tipo string antes de reemplazar comas por puntos
#         cargas_combustible_df[column] = cargas_combustible_df[column].astype(str).str.replace(',', '.', regex=False)

#     # Filtrar por número de coche
#     numero_coche = st.selectbox("Filtrar por Número de Coche", ['Todos'] + sorted(numeros_colectivos))
    
#     if numero_coche != 'Todos':
#         cargas_combustible_df = cargas_combustible_df[cargas_combustible_df['coche'] == numero_coche]

#     # Filtrar por lugar de carga
#     lugar_carga_filtrado = st.selectbox("Filtrar por Lugar de Carga", ['Todos'] + sorted(cargas_combustible_df['lugarCarga'].unique()))
    
#     if lugar_carga_filtrado != 'Todos':
#         cargas_combustible_df = cargas_combustible_df[cargas_combustible_df['lugarCarga'] == lugar_carga_filtrado]

#     # Filtro de fecha con checkbox
#     if st.checkbox("Filtrar por Fecha"):
#         # Convierte las fechas al formato datetime solo si no lo han sido
#         cargas_combustible_df['fecha'] = pd.to_datetime(cargas_combustible_df['fecha'], errors='coerce', format='%d/%m/%Y')
        
#         fecha_min = cargas_combustible_df['fecha'].min().date()
#         # fecha_max = cargas_combustible_df['fecha'].max().date()

#         fecha_seleccionada = st.date_input("Seleccionar Fecha", min_value=fecha_min, max_value=datetime.today())

#         cargas_combustible_df = cargas_combustible_df[cargas_combustible_df['fecha'].dt.date == fecha_seleccionada]

#     # Formatear las fechas en el DataFrame antes de mostrarlo, usando la función formatear_fecha
#     cargas_combustible_df['fecha'] = cargas_combustible_df['fecha'].apply(formatear_fecha)

#     # Ordenar el DataFrame por la columna 'idCarga' de forma descendente
#     cargas_combustible_df = cargas_combustible_df.sort_values(by='idCarga', ascending=False)

#     # Mostrar el DataFrame de cargas de combustible
#     st.dataframe(cargas_combustible_df)

# def editar_carga_combustible():
#     st.header('Editar Carga de Combustible en Colectivo')

#     # Ingresar el idCarga a editar
#     id_carga_editar = st.number_input('Ingrese el idCarga a editar', value=None, min_value=0)

#     if id_carga_editar is not None:

#         # Descargar el archivo CSV desde S3 y cargarlo en un DataFrame
#         try:
#             csv_file_key = 'cargasCombustible.csv'
#             response = s3.get_object(Bucket=bucket_name, Key=csv_file_key)
#             cargas_combustible_df = pd.read_csv(io.BytesIO(response['Body'].read()))
#         except s3.exceptions.NoSuchKey:
#             st.warning("No se encontró el archivo CSV en S3.")
#             return

#         # Filtrar el DataFrame para obtener la carga específica por idCarga
#         carga_editar_df = cargas_combustible_df[cargas_combustible_df['idCarga'] == id_carga_editar]

#         if not carga_editar_df.empty:
#             # Mostrar la información actual de la carga
#             st.write("Información actual de la carga:")
#             st.dataframe(carga_editar_df)

#             # Mostrar campos para editar cada variable
#             for column in carga_editar_df.columns:
#                 valor_actual = carga_editar_df.iloc[0][column]

#                 if column in ['idCarga', 'coche', 'contadorLitrosInicio', 'contadorLitrosCierre', 'litrosCargados', 'numeroPrecintoViejo', 'numeroPrecintoNuevo', 'precio']:
#                     nuevo_valor = st.text_input(f"Nuevo valor para {column}", value=str(valor_actual))
#                     # Verificar si es un número
#                     if not nuevo_valor.isdigit():
#                         st.warning(f"El valor para {column} debe ser un número.")
#                         continue  # Salta a la próxima iteración si no es un número
#                 elif column == 'lugarCarga':
#                     opciones_lugar_carga = ['Surtidor', 'Tanque']
#                     nuevo_valor = st.selectbox(f"Nuevo valor para {column}", opciones_lugar_carga, index=opciones_lugar_carga.index(valor_actual))
#                 elif column in ['fecha', 'hora']:
#                     formato = '%d/%m/%Y' if column == 'fecha' else '%H:%M'
#                     nuevo_valor = st.text_input(f"Nuevo valor para {column}", value=valor_actual.strftime(formato) if isinstance(valor_actual, pd.Timestamp) else valor_actual)
#                     # Verificar el formato de la fecha o hora ingresada
#                     if column == 'fecha':
#                         if re.match(r'^\d{2}/\d{2}/\d{4}$', nuevo_valor) is None:
#                             st.warning("Formato incorrecto para fecha. Use el formato DD/MM/AAAA.")
#                             continue
#                     elif column == 'hora':
#                         if re.match(r'^\d{2}:\d{2}$', nuevo_valor) is None:
#                             st.warning("Formato incorrecto para hora. Use el formato HH:MM.")
#                             continue
#                 else:
#                     nuevo_valor = st.text_input(f"Nuevo valor para {column}", value=str(valor_actual))

#                 carga_editar_df.at[carga_editar_df.index[0], column] = nuevo_valor

#             # Botón para guardar los cambios
#             if st.button("Guardar modificación"):
#                 # Actualizar el DataFrame original con los cambios realizados
#                 cargas_combustible_df.update(carga_editar_df)

#                 # Guardar el DataFrame actualizado en S3
#                 with io.StringIO() as csv_buffer:
#                     cargas_combustible_df.to_csv(csv_buffer, index=False)
#                     s3.put_object(Body=csv_buffer.getvalue(), Bucket=bucket_name, Key=csv_file_key)

#                 st.success("¡Carga de combustible actualizada correctamente!")

#                 # Esperar 2 segundos antes de recargar la aplicación
#                 time.sleep(2)
                
#                 # Recargar la aplicación
#                 st.rerun()
#         else:
#             st.warning(f"No se encontró ninguna carga de combustible con el idCarga {id_carga_editar}")
        
#     else: 
#         st.warning('Ingrese el idCarga para editar la información de la carga')

# def eliminar_carga_combustible():
#     st.header('Eliminar Carga de Combustible en Colectivo')

#     # Ingresar el idCarga a eliminar
#     id_carga_eliminar = st.number_input('Ingrese el idCarga a eliminar', value=None, min_value=0)

#     if id_carga_eliminar is not None:
#         st.error(f'¿Está seguro de eliminar la carga de combustible con idCarga {id_carga_eliminar}?')

#         if st.button('Eliminar Carga'):
#             # Descargar el archivo CSV desde S3 y cargarlo en un DataFrame
#             csv_file_key = 'cargasCombustible.csv'
#             response = s3.get_object(Bucket=bucket_name, Key=csv_file_key)
#             cargas_combustible_df = pd.read_csv(io.BytesIO(response['Body'].read()))

#             # Verificar si la carga con el idCarga a eliminar existe en el DataFrame
#             if id_carga_eliminar in cargas_combustible_df['idCarga'].values:
#                 # Eliminar la carga de combustible con el idCarga especificado
#                 cargas_combustible_df = cargas_combustible_df[cargas_combustible_df['idCarga'] != id_carga_eliminar]

#                 # Guardar el DataFrame actualizado en S3
#                 with io.StringIO() as csv_buffer:
#                     cargas_combustible_df.to_csv(csv_buffer, index=False)
#                     s3.put_object(Body=csv_buffer.getvalue(), Bucket=bucket_name, Key=csv_file_key)

#                 st.success(f"¡Carga de combustible con idCarga {id_carga_eliminar} eliminada correctamente!")

#                 # Esperar 2 segundos antes de recargar la aplicación
#                 time.sleep(2)
                
#                 # Recargar la aplicación
#                 st.rerun()
#             else:
#                 st.error(f"No se encontró ninguna carga de combustible con el idCarga {id_carga_eliminar}")
#     else:
#         st.error('Ingrese el idCarga para eliminar la carga')

# def main():
#     visualizar_cargas_combustible()
#     # Verificar si el usuario es admin
#     if st.session_state.user_rol == "admin":
#         editar_carga_combustible()
#         eliminar_carga_combustible()