import streamlit as st
import pandas as pd
import boto3
import io
from io import StringIO
import altair as alt
import time

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
    # Especificamos el tipo de datos para la columna 'serie' como int
    data['serie'] = data['serie'].astype(int)
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
        errores.append("El número de repeticiones o el tiempo debe ser un valor numérico positivo.")

    return errores

def normalizar_ejercicio(texto):
    texto = texto.strip()
    palabras = texto.split()
    # Verificar si hay palabras en la lista antes de capitalizar la primera
    if palabras:
        palabras[0] = palabras[0].capitalize()
        return ' '.join(palabras)
    else:
        return texto

def normalizar_socio(texto):
    texto = texto.strip()
    palabras = texto.split()
    palabras = [palabra.capitalize() for palabra in palabras]
    return ' '.join(palabras)

def normalizar_observaciones(texto):
    if isinstance(texto, str):
        texto = texto.strip()
        texto = texto.capitalize()
    return texto

def registra_entrenamientos_hipertrofia():
    # Conectar a S3
    s3, bucket_name = conectar_s3()

    # Cargar DataFrame desde S3
    df_total = cargar_dataframe_desde_s3(s3, bucket_name)

    st.subheader("Ingrese nombre, apellido y luego seleccione")
    # Variables ingresadas por el cliente
    socio_input = st.text_input('Nombre y Apellido')
    socio_input = normalizar_socio(socio_input)

    # Filtrar los nombres que coinciden con lo que se ha ingresado
    nombres_coincidentes = df_total['socio'][df_total['socio'].str.contains(socio_input, case=False)].unique()

    # Selectbox para mostrar nombres coincidentes
    socio = st.selectbox('Seleccionar Socio', [socio_input] + list(nombres_coincidentes))

    # Filtrar los datos del DataFrame según el socio seleccionado
    df_entrenamientos_socio = df_total[df_total['socio'] == socio]

    with st.expander('Nuevo Entrenamiento de Hipertrofia'):
        st.markdown("<h1 style='text-align: center;'>Registrá Entrenamiento de Hipertrofia</h1>", unsafe_allow_html=True)

        fecha_seleccionada = st.date_input("Seleccione la fecha", obtener_fecha_argentina())

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

            # Si el musculo se cambia, pasa lo siguiente para limpiar los campos
            if musculo != ultima_fila_socio.get('musculo', ''):
                ejercicio_input = ''
                # st.warning("El músculo seleccionado es diferente al último registro. Se ha limpiado el campo de ejercicio.")

                if musculo:
                    ejercicios_disponibles = df_total[df_total['musculo'] == musculo]['ejercicio'].unique()
                else:
                    ejercicios_disponibles = []
            
                ejercicio_input = st.text_input('Ejercicio')
                ejercicio_input = normalizar_ejercicio(ejercicio_input)

                # Calcular la frecuencia de los ejercicios
                frecuencia_ejercicios = df_entrenamientos_socio['ejercicio'].value_counts().to_dict()

                # Ordenar los ejercicios disponibles por frecuencia
                ejercicios_ordenados = sorted(ejercicios_disponibles, key=lambda x: frecuencia_ejercicios.get(x, 0), reverse=True)

                ejercicios_filtrados = [ejercicio for ejercicio in ejercicios_ordenados if ejercicio_input.lower() in ejercicio.lower()]

                ejercicio = st.selectbox('Seleccione Ejercicio', [ejercicio_input] + ejercicios_filtrados)
                # Mostrar información del último entrenamiento del socio para el ejercicio seleccionado
                            
                if ejercicio:
                    # Obtener la fecha actual
                    fecha_actual = obtener_fecha_argentina()

                    # Formatear la fecha en el formato deseado
                    fecha_actual = fecha_actual.strftime('%d/%m/%Y')
                    
                    # Filtrar los entrenamientos del ejercicio seleccionado y que no sean de la fecha actual
                    entrenamientos_ejercicio = df_entrenamientos_socio[(df_entrenamientos_socio['ejercicio'] == ejercicio) & (df_entrenamientos_socio['fecha'] != fecha_actual)]
                    
                    if not entrenamientos_ejercicio.empty:
                        # Ordenar los entrenamientos por fecha en orden descendente para obtener el más reciente primero
                        entrenamientos_ejercicio = entrenamientos_ejercicio.sort_values(by='fecha', ascending=False)
                        
                        # Obtener la fecha más reciente
                        ultima_fecha = entrenamientos_ejercicio.iloc[0]['fecha']
                        
                        st.info(f"Última vez en {ejercicio} ({ultima_fecha}):")
                        
                        # Filtrar los entrenamientos por la fecha más reciente
                        entrenamientos_ultima_fecha = entrenamientos_ejercicio[entrenamientos_ejercicio['fecha'] == ultima_fecha]
                        
                        # Iterar sobre las filas de entrenamiento y mostrar los detalles de cada serie
                        for _, fila in entrenamientos_ultima_fecha.iterrows():
                            serie = fila['serie']
                            peso = fila['peso']
                            repeticiones = fila['repeticiones']
                            
                            st.write(f"Serie {serie}: {peso} kg, repeticiones {repeticiones}")
                    else:
                        st.info(f"No hay registros de entrenamiento para {ejercicio} para {socio} que no sean de la fecha actual.")

                serie = st.number_input('Serie', min_value=0, value=1, step=1)

                peso = st.number_input('Peso',  min_value=0, value=None, step=1)

                repeticiones = st.number_input('Repeticiones',  min_value=0, value=None, step=1)

            # Si el musculo no se cambia
            else:
                if musculo:
                    ejercicios_disponibles = df_total[df_total['musculo'] == musculo]['ejercicio'].unique()
                else:
                    ejercicios_disponibles = []

                ejercicio_input = st.text_input('Ejercicio', value=ultima_fila_socio.get('ejercicio', ''))
                ejercicio_input = normalizar_ejercicio(ejercicio_input)

                # Calcular la frecuencia de los ejercicios
                frecuencia_ejercicios = df_entrenamientos_socio['ejercicio'].value_counts().to_dict()

                # Ordenar los ejercicios disponibles por frecuencia
                ejercicios_ordenados = sorted(ejercicios_disponibles, key=lambda x: frecuencia_ejercicios.get(x, 0), reverse=True)

                ejercicios_filtrados = [ejercicio for ejercicio in ejercicios_ordenados if ejercicio_input.lower() in ejercicio.lower()]

                ejercicio = st.selectbox('Seleccione Ejercicio', [ejercicio_input] + ejercicios_filtrados)
                # Mostrar información del último entrenamiento del socio para el ejercicio seleccionado
                            
                if ejercicio:
                    # Obtener la fecha actual
                    fecha_actual = obtener_fecha_argentina()

                    # Formatear la fecha en el formato deseado
                    fecha_actual = fecha_actual.strftime('%d/%m/%Y')
                    
                    # Filtrar los entrenamientos del ejercicio seleccionado y que no sean de la fecha actual
                    entrenamientos_ejercicio = df_entrenamientos_socio[(df_entrenamientos_socio['ejercicio'] == ejercicio) & (df_entrenamientos_socio['fecha'] != fecha_actual)]
                    
                    if not entrenamientos_ejercicio.empty:
                        # Ordenar los entrenamientos por fecha en orden descendente para obtener el más reciente primero
                        entrenamientos_ejercicio = entrenamientos_ejercicio.sort_values(by='fecha', ascending=False)
                        
                        # Obtener la fecha más reciente
                        ultima_fecha = entrenamientos_ejercicio.iloc[0]['fecha']
                        
                        st.info(f"Última vez en {ejercicio} ({ultima_fecha}):")
                        
                        # Filtrar los entrenamientos por la fecha más reciente
                        entrenamientos_ultima_fecha = entrenamientos_ejercicio[entrenamientos_ejercicio['fecha'] == ultima_fecha]
                        
                        # Iterar sobre las filas de entrenamiento y mostrar los detalles de cada serie
                        for _, fila in entrenamientos_ultima_fecha.iterrows():
                            serie = fila['serie']
                            peso = fila['peso']
                            repeticiones = fila['repeticiones']
                            
                            st.write(f"Serie {serie}: {peso} kg, repeticiones {repeticiones}")
                    else:
                        st.info(f"No hay registros de entrenamiento para {ejercicio} para {socio} que no sean de la fecha actual.")

                serie = st.number_input('Serie', min_value=0, value=int(ultima_fila_socio.get('serie', 1))+1, step=1)

                peso = st.number_input('Peso',  min_value=0, value=ultima_fila_socio.get('peso'), step=1)

                repeticiones = st.number_input('Repeticiones',  min_value=0, value=ultima_fila_socio.get('repeticiones'), step=1)

        else:
            grupoMuscular = st.selectbox('Grupo Muscular', ['Tren Superior', 'Tren Inferior', 'Zona Media'])

            if grupoMuscular == 'Tren Superior':
                opciones_musculos = ['Pecho', 'Espalda', 'Hombros', 'Biceps', 'Triceps']
            elif grupoMuscular == 'Tren Inferior':
                opciones_musculos = ['Cuádriceps', 'Isquiotibiales', 'Glúteos', 'Pantorrillas']
            elif grupoMuscular == 'Zona Media':
                opciones_musculos = ['abdominales']
            else:
                opciones_musculos = []

            musculo = st.selectbox('Músculo', opciones_musculos)

            if musculo:
                ejercicios_disponibles = df_total[df_total['musculo'] == musculo]['ejercicio'].unique()
            else:
                ejercicios_disponibles = []

            ejercicio_input = st.text_input('Ejercicio')
            ejercicio_input = normalizar_ejercicio(ejercicio_input)

            ejercicios_filtrados = [ejercicio for ejercicio in ejercicios_disponibles if ejercicio_input.lower() in ejercicio.lower()]

            ejercicio = st.selectbox('Seleccione Ejercicio', [ejercicio_input] + ejercicios_filtrados)

            serie = st.number_input('Serie', min_value=0, value=1, step=1)

            peso = st.number_input('Peso',  min_value=0, value=None, step=1)
            repeticiones = st.number_input('Repeticiones',  min_value=0, value=None, step=1)

        tiempo = st.number_input('Tiempo en segundos',  min_value=0, value=None, step=1)
        observaciones = st.text_input('Observaciones')
        observaciones = normalizar_observaciones(observaciones)

        # Agregar campo de multiplicador de series
        multiplicador_series = st.number_input('Multiplicador de series', min_value=1, value=1, step=1)

        # Botón para guardar el registro
        if st.button('Guardar Entrenamiento de Hipertrofia'):
            # Validar las entradas del usuario
            errores = validar_entradas(socio, grupoMuscular, musculo, ejercicio, serie, peso, repeticiones)

            if errores:
                st.error("Por favor, corrija los siguientes errores:")
                for error in errores:
                    st.error(error)
            else:
                fecha = fecha_seleccionada.strftime('%d/%m/%Y')
                hora = obtener_fecha_argentina().strftime('%H:%M')
                usuario = st.session_state.get("user_nombre_apellido", "")

                # Crear una lista de diccionarios para almacenar múltiples registros
                data = []
                for i in range(multiplicador_series):
                    data.append({
                        'idEjercicioHiper': df_total['idEjercicioHiper'].max() + 1 + i if not df_total.empty else i,
                        'fecha': fecha,
                        'hora': hora,
                        'socio': socio,
                        'grupoMuscular': grupoMuscular,
                        'musculo': musculo,
                        'ejercicio': ejercicio,
                        'serie': serie + i,
                        'peso': peso,
                        'repeticiones': repeticiones,
                        'tiempo': tiempo,
                        'observaciones': observaciones,
                        'usuario': usuario
                    })

                df_new = pd.DataFrame(data)

                # Concatenar el nuevo DataFrame con el DataFrame total
                df_total = pd.concat([df_total, df_new], ignore_index=True)

                # Cargar los datos en el archivo CSV en S3
                upload_to_s3(df_total, s3, bucket_name)

                st.success('Entrenamiento guardado con éxito!')

                # Esperar 1 segundo antes de recargar la aplicación
                time.sleep(0.1)
                
                # Recargar la aplicación
                st.rerun()
    
    if socio:
        with st.expander(f'Visualizar Entrenamientos de Hipertrofia'):
            visualizar_entrenamientos_hiper(socio)

        with st.expander('Edita Entrenamiento de Hipertrofia'):
            editar_entrenamientos_hiper()

        with st.expander('Elimina Entrenamiento de Hipertrofia'):
            eliminar_entrenamientos_hiper()

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
        'tiempo': 'Tiempo',
        'observaciones': 'Observaciones',
        'usuario': 'Entrenador'
    })

    # Establecer el orden deseado de las columnas
    column_order = ['ID', 'Fecha', 'Grupo Muscular', 'Músculo', 'Ejercicio', 'Serie', 'Peso', 'Repeticiones', 'Tiempo', 'Hora', 'Observaciones', 'Entrenador']
    df_total = df_total.reindex(columns=column_order)

    # Convertir las fechas a objetos datetime
    df_total['Fecha'] = pd.to_datetime(df_total['Fecha'], format='%d/%m/%Y')

    # Agregar filtros en el sidebar
    st.sidebar.markdown("### Filtrar entrenamientos")

    grupo_muscular_filtro = st.sidebar.selectbox('Grupo Muscular', ['Todos'] + df_total['Grupo Muscular'].unique().tolist())
    musculo_filtro = st.sidebar.selectbox('Músculo', ['Todos'] + df_total['Músculo'].unique().tolist())
    ejercicio_filtro = st.sidebar.selectbox('Ejercicio', ['Todos'] + df_total['Ejercicio'].unique().tolist())
    fecha_inicio = st.sidebar.date_input('Fecha Inicio', df_total['Fecha'].min().date())
    fecha_fin = st.sidebar.date_input('Fecha Fin', df_total['Fecha'].max().date())

    # Aplicar filtros al DataFrame
    if grupo_muscular_filtro != 'Todos':
        df_total = df_total[df_total['Grupo Muscular'] == grupo_muscular_filtro]

    if musculo_filtro != 'Todos':
        df_total = df_total[df_total['Músculo'] == musculo_filtro]

    if ejercicio_filtro != 'Todos':
        df_total = df_total[df_total['Ejercicio'] == ejercicio_filtro]

    df_total = df_total[(df_total['Fecha'] >= pd.to_datetime(fecha_inicio)) & (df_total['Fecha'] <= pd.to_datetime(fecha_fin))]

    if df_total.empty:
        st.warning("No hay entrenamientos de hipertrofia registrados con los filtros seleccionados.")
        return

    # Ordenar el DataFrame por el ID de Ejercicio de Hipertrofia de forma descendente
    df_total = df_total.sort_values(by='ID', ascending=False)

    # Convertir la columna 'Fecha' al formato deseado para mostrar en Streamlit
    df_total['Fecha'] = df_total['Fecha'].dt.strftime('%d/%m/%Y')

    # Mostrar el DataFrame de entrenamientos de hipertrofia
    st.dataframe(df_total)

    st.markdown(f"<h1 style='text-align: center;'>Peso levantado por día de {socio}</h1>", unsafe_allow_html=True)

    # Calcular peso total levantado por día
    df_total['Fecha'] = pd.to_datetime(df_total['Fecha'], format='%d/%m/%Y')
    df_total['Peso Total'] = df_total['Peso'] * df_total['Repeticiones']
    peso_total_por_dia = df_total.groupby('Fecha', as_index=False).agg({'Peso Total': 'sum', 'Músculo': lambda x: ', '.join(set(x))})

    # Convertir la columna 'Fecha' al formato deseado para mostrar en el gráfico
    peso_total_por_dia['Fecha'] = pd.to_datetime(peso_total_por_dia['Fecha'], format='%d/%m/%Y')

    # Gráfico de línea con peso total levantado por día
    line_chart = alt.Chart(peso_total_por_dia).mark_line(color='green').encode(
        x='Fecha:T',
        y='Peso Total:Q',
        tooltip=['Fecha:T', 'Peso Total:Q', 'Músculo:N']
    ).properties(
        width=500,
        height=400,
    )

    # Capa adicional con puntos sobre el gráfico
    points = alt.Chart(peso_total_por_dia).mark_circle(
        size=100,
        color='yellow',
        opacity=1
    ).encode(
        x='Fecha:T',
        y='Peso Total:Q',
        tooltip=['Fecha:T', 'Peso Total:Q', 'Músculo:N']
    )

    # Combinar el gráfico de línea y los puntos
    chart = line_chart + points

    st.altair_chart(chart)

def editar_entrenamientos_hiper():
    st.header('Editar Entrenamiento de Hipertrofia')

    # Ingresar el ID del ejercicio a editar
    id_ejercicio_editar = st.number_input('Ingrese el ID del ejercicio a editar', value=None, min_value=0)

    if id_ejercicio_editar is not None:
        # Conectar a S3
        s3, bucket_name = conectar_s3()

        # Cargar DataFrame desde S3
        df_total = cargar_dataframe_desde_s3(s3, bucket_name)

        # Filtrar el DataFrame para obtener el ejercicio específico por ID
        ejercicio_editar_df = df_total[df_total['idEjercicioHiper'] == id_ejercicio_editar]

        if not ejercicio_editar_df.empty:
            # Mostrar la información actual del ejercicio
            st.write("Información actual del ejercicio:")
            st.dataframe(ejercicio_editar_df)

            # Mostrar campos para editar cada variable
            for column in ejercicio_editar_df.columns:
                valor_actual = ejercicio_editar_df.iloc[0][column]

                nuevo_valor = None
                if column in ['idEjercicioHiper','grupoMuscular', 'musculo', 'ejercicio', 'observaciones']:
                    nuevo_valor = st.text_input(f"Nuevo valor para {column}", value=str(valor_actual))
                elif column == 'fecha':
                    # Convertir la fecha al formato deseado para mostrar
                    fecha_actual = pd.to_datetime(valor_actual, format='%d/%m/%Y')
                    nuevo_valor = st.date_input(f"Nuevo valor para {column}", value=fecha_actual)
                    # Convertir la fecha al formato "%d/%m/%Y" antes de actualizar el DataFrame
                    nuevo_valor = nuevo_valor.strftime('%d/%m/%Y')
                elif column in ['serie', 'peso', 'repeticiones', 'tiempo']:
                    if column == 'serie':
                        nuevo_valor = st.number_input(f"Nuevo valor para {column}", value=int(valor_actual))
                    else:
                        nuevo_valor = st.number_input(f"Nuevo valor para {column}", value=valor_actual)

                if nuevo_valor is not None:
                    ejercicio_editar_df.at[ejercicio_editar_df.index[0], column] = nuevo_valor

            # Botón para guardar los cambios
            if st.button("Guardar modificación"):
                # Actualizar el DataFrame original con los cambios realizados
                df_total.update(ejercicio_editar_df)

                # Guardar el DataFrame actualizado en S3
                upload_to_s3(df_total, s3, bucket_name)

                st.success("¡Entrenamiento de hipertrofia actualizado correctamente!")

                # Esperar 2 segundos antes de recargar la aplicación
                time.sleep(2)

                # Recargar la aplicación
                st.rerun()
        else:
            st.error(f"No se encontró ningún entrenamiento de hipertrofia con el ID {id_ejercicio_editar}")
    else:
        st.warning('Ingrese el ID del ejercicio para editar la información del entrenamiento')

def eliminar_entrenamientos_hiper():
    st.header('Eliminar Entrenamiento de Hipertrofia')

    # Ingresar el idEjercicioHiper a eliminar
    id_ejercicio_eliminar = st.number_input('Ingrese el idEjercicioHiper a eliminar', value=None, min_value=0)

    if id_ejercicio_eliminar is not None:
        st.error(f'¿Está seguro de eliminar el entrenamiento de hipertrofia con idEjercicioHiper {id_ejercicio_eliminar}?')

        if st.button('Eliminar Entrenamiento'):
            # Conectar a S3 y obtener el DataFrame
            s3, bucket_name = conectar_s3()
            csv_file_key = 'entrenamientosHipertrofia.csv'
            response = s3.get_object(Bucket=bucket_name, Key=csv_file_key)
            entrenamientos_hipertrofia_df = pd.read_csv(io.BytesIO(response['Body'].read()))

            # Verificar si el entrenamiento con el idEjercicioHiper a eliminar existe en el DataFrame
            if id_ejercicio_eliminar in entrenamientos_hipertrofia_df['idEjercicioHiper'].values:
                # Eliminar el entrenamiento de hipertrofia con el idEjercicioHiper especificado
                entrenamientos_hipertrofia_df = entrenamientos_hipertrofia_df[entrenamientos_hipertrofia_df['idEjercicioHiper'] != id_ejercicio_eliminar]

                # Guardar el DataFrame actualizado en S3
                with io.StringIO() as csv_buffer:
                    entrenamientos_hipertrofia_df.to_csv(csv_buffer, index=False)
                    s3.put_object(Body=csv_buffer.getvalue(), Bucket=bucket_name, Key=csv_file_key)

                st.success(f"¡Entrenamiento de hipertrofia con idEjercicioHiper {id_ejercicio_eliminar} eliminado correctamente!")

                # Esperar 2 segundos antes de recargar la aplicación
                time.sleep(2)
                
                # Recargar la aplicación
                st.rerun()
            else:
                st.error(f"No se encontró ningún entrenamiento de hipertrofia con el ID {id_ejercicio_eliminar}")
    else:
        st.error('Ingrese el ID para eliminar el entrenamiento')

def main():
    
    registra_entrenamientos_hipertrofia()

if __name__ == '__main__':
    main()