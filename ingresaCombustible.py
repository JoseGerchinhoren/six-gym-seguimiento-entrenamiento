import streamlit as st
from horario import obtener_fecha_argentina
import pandas as pd
from config import cargar_configuracion
import io
import boto3
from botocore.exceptions import NoCredentialsError
from visualizaCombustible import main as visualizaCombustible
import time
from visualizaMovimientos import main as visualizaMovimientos

# Obtener credenciales
aws_access_key, aws_secret_key, region_name, bucket_name = cargar_configuracion()

# Conectar a S3
s3 = boto3.client('s3', aws_access_key_id=aws_access_key, aws_secret_access_key=aws_secret_key, region_name=region_name)

csv_filename = "cargasCombustible.csv"

# Inicializar la lista de números de colectivo
numeros_colectivos = [
    1, 2, 3, 4, 6, 7, 8, 9, 10, 11, 12, 15, 18, 52,
    101, 102, 103, 104, 105, 106, 107, 108, 109, 110,
    111, 112, 113, 114, 115, 116, 117, 118, 119, 120, 121
]

formato_fecha = '%d/%m/%Y'
formato_hora = '%H:%M'

def obtener_ultimo_registro_por_coche(coche, df_total):
    """
    Función para obtener el último registro de un coche específico.
    Retorna el valor del número de precinto nuevo si existe, o None si no hay registros.
    """
    filtro_coche = df_total['coche'] == coche
    registros_coche = df_total[filtro_coche]
    if not registros_coche.empty:
        ultimo_registro = registros_coche.iloc[-1]
        return ultimo_registro['numeroPrecintoNuevo']
    else:
        return None
    
def cargar_dataframe_desde_s3():
    # Función para cargar el DataFrame desde S3
    try:
        response = s3.get_object(Bucket=bucket_name, Key=csv_filename)
        return pd.read_csv(io.BytesIO(response['Body'].read()))
    except s3.exceptions.NoSuchKey:
        st.warning("No se encontró el archivo CSV en S3.")

def restar_litros_del_tanque(litros_cargados, s3, bucket_name):
    stock_tanque_filename = "stock_tanque_config.txt"
    
    try:
        # Intentar obtener el contenido actual del archivo desde S3
        try:
            response = s3.get_object(Bucket=bucket_name, Key=stock_tanque_filename)
            stock_tanque_litros = int(response['Body'].read())
        except s3.exceptions.NoSuchKey:
            st.warning(f"No se encontró el archivo {stock_tanque_filename} en S3. Creando un nuevo archivo.")
            stock_tanque_litros = 0 - litros_cargados
            s3.put_object(Body=str(stock_tanque_litros), Bucket=bucket_name, Key=stock_tanque_filename)
            st.success(f"Se creó un nuevo archivo {stock_tanque_filename} con un stock inicial de {-litros_cargados} litros.")

        # Restar los litros cargados al stock
        stock_tanque_litros -= litros_cargados
        
        # Actualizar el contenido del archivo en S3
        s3.put_object(Body=str(stock_tanque_litros), Bucket=bucket_name, Key=stock_tanque_filename)

        st.success(f"Se restaron {litros_cargados} litros del tanque. Nuevo stock: {stock_tanque_litros} litros.")

    except NoCredentialsError:
        st.error("Credenciales de AWS no disponibles. Verifica la configuración.")

    except ValueError:
        st.error("El contenido del archivo no es un número entero. Verifica el contenido del archivo.")

    except Exception as e:
        st.error(f"Error al restar litros del tanque: {e}")

def guardar_carga_empresa_en_s3(data, filename, tipo_carga):
    try:
        # Leer el archivo CSV desde S3 o crear un DataFrame vacío con las columnas definidas
        try:
            response = s3.get_object(Bucket=bucket_name, Key=filename)
            df_total = pd.read_csv(io.BytesIO(response['Body'].read()))
        except s3.exceptions.NoSuchKey:
            st.warning("No se encontró el archivo CSV en S3")

        # Obtener el ID de la carga (máximo ID existente + 1)
        id_carga = df_total['idCarga'].max() + 1 if not df_total.empty else 0

        # Crear un diccionario con la información de la carga
        nueva_carga = {
            'idCarga': id_carga,
            'coche': int(data['coche']),
            'fecha': data['fecha'],
            'hora': data['hora'],
            'lugarCarga': data['lugarCarga'],
            'contadorLitrosInicio': int(data.get('contadorLitrosInicio', 0)),
            'contadorLitrosCierre': int(data.get('contadorLitrosCierre', 0)),
            'litrosCargados': int(data.get('litrosCargados', 0)),
            'precio': int(data.get('precio', 0)),
            'numeroPrecintoViejo': int(data.get('numeroPrecintoViejo', 0)),
            'numeroPrecintoNuevo': int(data.get('numeroPrecintoNuevo', 0)),
            'observacion': data.get('observacion', ''),
            'usuario': data['usuario']
        }

        # Agregar información específica del lugar de carga
        if data['lugarCarga'] == 'Surtidor':
            nueva_carga['lugarCarga'] = 'Surtidor'
            nueva_carga['precio'] = int(data.get('precio', 0))

        # Actualizar el DataFrame con los valores del nuevo registro
        df_total = pd.concat([df_total, pd.DataFrame([nueva_carga])], ignore_index=True)

        # Guardar el DataFrame actualizado en S3
        with io.StringIO() as csv_buffer:
            df_total.to_csv(csv_buffer, index=False)
            s3.put_object(Body=csv_buffer.getvalue(), Bucket=bucket_name, Key=filename)

        # Actualizar litros en el archivo litros_colectivos
        actualizar_litros_en_colectivo(data['coche'], data['litrosCargados'], s3, bucket_name)

        st.success("Información guardada exitosamente!")

    except NoCredentialsError:
        st.error("Credenciales de AWS no disponibles. Verifica la configuración.")

    except Exception as e:
        st.error(f"Error al guardar la información: {e}")

def obtener_contador_tanque_s3():
    try:
        response = s3.get_object(Bucket=bucket_name, Key="contador_tanque_combustible.txt")
        return int(response['Body'].read().decode())
    except s3.exceptions.NoSuchKey:
        st.warning("No se encontró el archivo contador_tanque_combustible.txt en S3. Creando un nuevo archivo.")
        s3.put_object(Body='0', Bucket=bucket_name, Key="contador_tanque_combustible.txt")
        return 0
    except Exception as e:
        st.error(f"Error al obtener el contador del tanque desde S3: {e}")
        return 0

def actualizar_contador_tanque_s3(nuevo_valor):
    try:
        s3.put_object(Body=str(nuevo_valor), Bucket=bucket_name, Key="contador_tanque_combustible.txt")
    except Exception as e:
        st.error(f"Error al actualizar el contador del tanque en S3: {e}")

def main():
    # Cargar el DataFrame desde S3
    df_total = cargar_dataframe_desde_s3()

    st.title("Cargas de Combustible en Colectivos")

    usuario = st.session_state.user_nombre_apellido

    # Mostrar información actual de litros en el tanque
    try:
        response = s3.get_object(Bucket=bucket_name, Key="stock_tanque_config.txt")
        current_litros = int(response['Body'].read().decode())
    except s3.exceptions.NoSuchKey:
        st.warning("No se encontró el archivo stock_tanque_config.txt en S3. No hay datos de litros disponibles.")

    # Mostrar información sobre colectivos con menos de 50 litros
    litros_colectivos = obtener_litros_colectivos(s3, bucket_name)
    colectivos_bajos_litros = obtener_colectivos_bajos_litros(litros_colectivos)

    if colectivos_bajos_litros:
        mensaje_colectivos_bajos_litros = f"Los colectivos {', '.join(map(str, colectivos_bajos_litros))} tienen menos de 100 litros."
        st.info(mensaje_colectivos_bajos_litros)
    else:
        st.info("Todos los colectivos tienen al menos 100 litros.")

    # Utilizando st.expander para la sección "Carga en Surtidor"
    with st.expander('Cargar en Surtidor'):
        coche_surtidor = st.selectbox("Seleccione número de coche:", numeros_colectivos)

        # Obtén el último número de precinto nuevo para el coche seleccionado
        ultimo_numero_precinto = obtener_ultimo_registro_por_coche(coche_surtidor, df_total)

        # Muestra el campo de número de precinto viejo o utiliza el valor obtenido
        numeroPrecintoViejo_surtidor = st.number_input('Ingrese el numero de precinto viejo', min_value=0, value=ultimo_numero_precinto or None, step=1)

        litrosCargados_surtidor = st.number_input('Ingrese la cantidad de litros cargados', min_value=0, value=None, step=1)
        precio_surtidor = st.number_input('Ingrese el precio de la carga en pesos', min_value=0, value=None, step=1)
        numeroPrecintoNuevo_surtidor = st.number_input('Ingrese el numero de precinto nuevo', min_value=0, value=None, step=1)
        observacion_surtidor = st.text_input('Ingrese una observacion, si se desea')
        
        # Obtener fecha y hora actual en formato de Argentina
        fecha_surtidor = obtener_fecha_argentina().strftime(formato_fecha)
        hora_surtidor = obtener_fecha_argentina().strftime(formato_hora)

        # Botón para realizar acciones asociadas a "Carga en Surtidor"
        if st.button('Guardar Carga de Combustible en Surtidor'):
            # Validar campos obligatorios antes de guardar
            campos_faltantes_surtidor = validar_campos_surtidor(coche_surtidor, numeroPrecintoViejo_surtidor, litrosCargados_surtidor, precio_surtidor, numeroPrecintoNuevo_surtidor)
            
            if campos_faltantes_surtidor:
                st.warning(f"¡Por favor, complete los siguientes campos obligatorios para Carga en Surtidor: {', '.join(campos_faltantes_surtidor)}!")
            else:
                # Continuar con el proceso de guardar
                data_surtidor = {
                    'lugarCarga': 'Surtidor',
                    'coche': coche_surtidor,
                    'fecha': fecha_surtidor,
                    'hora': hora_surtidor,
                    'numeroPrecintoViejo': numeroPrecintoViejo_surtidor,
                    'litrosCargados': litrosCargados_surtidor,
                    'precio': precio_surtidor,
                    'numeroPrecintoNuevo': numeroPrecintoNuevo_surtidor,
                    'observacion': observacion_surtidor,
                    'usuario': usuario,
                }
                guardar_carga_empresa_en_s3(data_surtidor, csv_filename, 'Surtidor')
                # Esperar 2 segundos antes de recargar la aplicación
                time.sleep(2)
                
                # Recargar la aplicación
                st.rerun()

    # Utilizando st.expander para la sección "Carga en Tanque"
    with st.expander('Cargar en Tanque'):
        st.info(f"{current_litros} Litros en Tanque de Empresa")

        coche_tanque = st.selectbox("Seleccione número de coche: ", numeros_colectivos)

        # Obtén el último número de precinto nuevo para el coche seleccionado
        ultimo_numero_precinto = obtener_ultimo_registro_por_coche(coche_tanque, df_total)

        # Muestra el campo de número de precinto viejo o utiliza el valor obtenido
        numeroPrecintoViejo = st.number_input('Ingrese el numero de precinto viejo ', min_value=0, value=ultimo_numero_precinto or None, step=1)

        contadorLitrosInicio = st.number_input('Contador Inicio', min_value=0, value=obtener_contador_tanque_s3(), step=1)

        contadorLitrosCierre = st.number_input('Contador Final', min_value=0, value=obtener_contador_tanque_s3(), step=1)

        litrosCargados = contadorLitrosCierre - contadorLitrosInicio

        st.subheader(f"Litros Cargados: {litrosCargados}")

        numeroPrecintoNuevo = st.number_input('Ingrese el numero de precinto nuevo ', min_value=0, value=None, step=1)
        observacion = st.text_input('Ingrese una observacion, si se desea ')

        # Validar campos obligatorios
        campos_faltantes_tanque = []
        if coche_tanque is None:
            campos_faltantes_tanque.append("Número de coche")
        if numeroPrecintoViejo is None:
            campos_faltantes_tanque.append("Número de precinto viejo")
        if contadorLitrosInicio is None:
            campos_faltantes_tanque.append("Contador de litros al inicio")
        if litrosCargados is None:
            campos_faltantes_tanque.append("Litros cargados")
        if numeroPrecintoNuevo is None:
            campos_faltantes_tanque.append("Número de precinto nuevo")

        # Mostrar mensaje de advertencia solo si se ha intentado guardar
        if st.button('Guardar Carga de Combustible en Tanque'):
            if campos_faltantes_tanque:
                st.error(f"¡Por favor, complete los siguientes campos obligatorios para Carga en Tanque: {', '.join(campos_faltantes_tanque)}!")
            else:
                # Continuar con el proceso de guardar
                fecha_tanque = obtener_fecha_argentina().strftime(formato_fecha)
                hora_tanque = obtener_fecha_argentina().strftime(formato_hora)

                data_tanque = {
                    'lugarCarga': 'Tanque',
                    'coche': coche_tanque,
                    'fecha': fecha_tanque,
                    'hora': hora_tanque,
                    'numeroPrecintoViejo': numeroPrecintoViejo,
                    'contadorLitrosInicio': contadorLitrosInicio,
                    'litrosCargados': litrosCargados,
                    'contadorLitrosCierre': contadorLitrosCierre,
                    'numeroPrecintoNuevo': numeroPrecintoNuevo,
                    'observacion': observacion,
                    'usuario': usuario
                }
                guardar_carga_empresa_en_s3(data_tanque, csv_filename, 'Tanque')
                restar_litros_del_tanque(litrosCargados, s3, bucket_name)

                # Actualizar el contador del tanque en S3
                actualizar_contador_tanque_s3(contadorLitrosCierre)

                # Esperar 2 segundos antes de recargar la aplicación
                time.sleep(2)
                
                # Recargar la aplicación
                st.rerun()

    # Utilizando st.expander para la sección "Visualiza Cantidad de Combustible en Colectivos"
    with st.expander('Visualizar Cantidad de Combustible en Colectivos'):
        visualizar_litros_colectivos()

    # Utilizando st.expander para la sección "Visualiza Cargas de Combustible"
    with st.expander('Visualizar Cargas de Combustible'):
        visualizaCombustible()
    
def validar_campos_surtidor(coche, numero_precinto_viejo, litros_cargados, precio, numero_precinto_nuevo):
    campos_faltantes_surtidor = []
    if coche is None:
        campos_faltantes_surtidor.append("Número de coche")
    if numero_precinto_viejo is None:
        campos_faltantes_surtidor.append("Número de precinto viejo")
    if litros_cargados is None:
        campos_faltantes_surtidor.append("Litros cargados")
    if precio is None:
        campos_faltantes_surtidor.append("Precio")
    if numero_precinto_nuevo is None:
        campos_faltantes_surtidor.append("Número de precinto nuevo")

    return campos_faltantes_surtidor

def actualizar_litros_en_colectivo(coche, litros, s3, bucket_name):
    try:
        # Obtener el contenido actual del archivo desde S3
        response = s3.get_object(Bucket=bucket_name, Key="litros_colectivos.csv")
        df_litros_colectivos = pd.read_csv(response['Body'])

        # Actualizar los litros
        df_litros_colectivos.loc[df_litros_colectivos['idColectivo'] == coche, 'litros'] += litros
        df_litros_colectivos['litros'] = df_litros_colectivos['litros'].clip(lower=0, upper=500)  # No permitir litros negativos y limitar a 500 litros

        # Actualizar el contenido del archivo en S3
        with io.StringIO() as csv_buffer:
            df_litros_colectivos.to_csv(csv_buffer, index=False)
            s3.put_object(Body=csv_buffer.getvalue(), Bucket=bucket_name, Key="litros_colectivos.csv")

        st.success(f"Se actualizó el stock de combustible del colectivo {coche}. Nuevo stock: {df_litros_colectivos.loc[df_litros_colectivos['idColectivo'] == coche, 'litros'].values[0]} litros.")

    except NoCredentialsError:
        st.error("Credenciales de AWS no disponibles. Verifica la configuración.")

    except Exception as e:
        st.error(f"Error al actualizar litros en colectivo: {e}")

def obtener_litros_colectivos(s3, bucket_name):
    try:
        # Obtener el contenido actual del archivo desde S3
        response = s3.get_object(Bucket=bucket_name, Key="litros_colectivos.csv")
        df_litros_colectivos = pd.read_csv(response['Body'])
        
        # Convertir DataFrame a un diccionario y devolverlo
        litros_colectivos = df_litros_colectivos.set_index('idColectivo').to_dict(orient='index')
        return litros_colectivos
    except (s3.exceptions.NoSuchKey, NoCredentialsError, pd.errors.EmptyDataError, ValueError) as e:
        st.error(f"Error al obtener datos de litros de colectivos: {e}")
        return {}

def visualizar_litros_colectivos():
    st.title("Litros de Combustible por Colectivo")

    litros_colectivos = obtener_litros_colectivos(s3, bucket_name)

    if not litros_colectivos:
        st.warning("No se pudieron obtener los datos de litros de colectivos.")
        return

    # Crear un DataFrame con los valores de litros
    df_litros_colectivos = pd.DataFrame(litros_colectivos).T.reset_index()
    df_litros_colectivos.columns = ['Colectivo', 'Litros', 'Estado']

    # Ordenar el DataFrame por la columna "Litros" de menor a mayor y luego por la columna "Colectivo"
    df_litros_colectivos = df_litros_colectivos.sort_values(by=['Litros', 'Colectivo'], ascending=[True, True])

    # Seleccionar las columnas del DataFrame original y luego aplicar estilo
    df_litros_colectivos_selected = df_litros_colectivos[['Colectivo', 'Litros', 'Estado']]
    df_litros_colectivos_styled = df_litros_colectivos_selected.style.applymap(colorizar_celda, subset=['Litros'])

    # Mostrar el DataFrame ordenado y estilizado
    st.dataframe(df_litros_colectivos_styled)

    # Verificar si el usuario es admin
    if st.session_state.user_rol == "admin":
        st.header('Editar Informacion de Colectivo')

        # Modifica la línea de la creación del selectbox
        colectivo_a_editar = st.selectbox('Ingrese el número de colectivo a editar', ["Colectivos"] + numeros_colectivos)

        if colectivo_a_editar is not "Colectivos":
            # Obtener el valor actual del estado
            estado_actual = litros_colectivos[colectivo_a_editar]['estado'] if colectivo_a_editar in litros_colectivos else False

            if estado_actual == True:
                estado_actual = 'Disponible'

            else: estado_actual = 'No Disponible'

            # Utilizar el valor actual como valor predeterminado para el radio button
            nuevo_estado = st.radio('Estado', ['Disponible', 'No Disponible'], index=['Disponible', 'No Disponible'].index(estado_actual))

            if nuevo_estado == 'Disponible':
                nuevo_estado = True
            
            else: nuevo_estado = False

            nuevos_litros = st.number_input('Ingrese nuevos litros ', min_value=0, value=df_litros_colectivos[df_litros_colectivos['Colectivo'] == colectivo_a_editar]['Litros'].iloc[0])

            # Botón para realizar la edición y guardar los cambios
            if st.button('Guardar Cambios '):
                editar_colectivo(colectivo_a_editar, nuevos_litros, nuevo_estado, s3, bucket_name)
        else:
            st.warning("Por favor, seleccione un número de colectivo para editar.")

def obtener_colectivos_bajos_litros(litros_colectivos, umbral_litros=100):
    """
    Función para obtener los colectivos que tienen menos de cierta cantidad de litros.
    """
    colectivos_bajos_litros = [colectivo for colectivo, litros_info in litros_colectivos.items() if litros_info['litros'] < umbral_litros]
    return colectivos_bajos_litros

def editar_colectivo(colectivo, nuevos_litros, nuevo_estado, s3, bucket_name):
    try:
        # Obtener el contenido actual del archivo desde S3
        response = s3.get_object(Bucket=bucket_name, Key="litros_colectivos.csv")
        df_litros_colectivos = pd.read_csv(response['Body'])

        # Actualizar los litros y el estado del colectivo
        df_litros_colectivos.loc[df_litros_colectivos['idColectivo'] == colectivo, 'litros'] = nuevos_litros
        df_litros_colectivos.loc[df_litros_colectivos['idColectivo'] == colectivo, 'estado'] = nuevo_estado

        # Actualizar el contenido del archivo en S3
        with io.StringIO() as csv_buffer:
            df_litros_colectivos.to_csv(csv_buffer, index=False)
            s3.put_object(Body=csv_buffer.getvalue(), Bucket=bucket_name, Key="litros_colectivos.csv")

        st.success(f"Se actualizó la información del colectivo {colectivo}.")

    except NoCredentialsError:
        st.error("Credenciales de AWS no disponibles. Verifica la configuración.")

    except Exception as e:
        st.error(f"Error al editar colectivo: {e}")

def colorizar_celda(val):
    if val < 100:
        color = 'red'
    elif 100 <= val < 200:
        color = 'orange'
    else:
        color = 'green'
    return f'background-color: {color}; color: white'

if __name__ == "__main__":
    main()
    visualizaCombustible()