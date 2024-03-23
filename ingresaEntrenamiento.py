import streamlit as st
import pandas as pd
import boto3
import io
from io import StringIO

# Obtener credenciales
from config import cargar_configuracion

# Obtener fecha actual en Argentina
from horario import obtener_fecha_argentina

# Conectar a S3
def conectar_s3():
    aws_access_key, aws_secret_key, region_name, bucket_name = cargar_configuracion()
    return boto3.client('s3', aws_access_key_id=aws_access_key, aws_secret_access_key=aws_secret_key, region_name=region_name), bucket_name

def cargar_dataframe_desde_s3(s3, bucket_name):
    csv_filename = "six_gym_entrenamientos.csv"
    try:
        response = s3.get_object(Bucket=bucket_name, Key=csv_filename)
        return pd.read_csv(io.BytesIO(response['Body'].read()))
    except s3.exceptions.NoSuchKey:
        st.warning("No se encontró el archivo CSV en S3.")
        return pd.DataFrame()

def upload_to_s3(data, s3, bucket_name):
    csv_filename = "six_gym_entrenamientos.csv"
    csv_buffer = StringIO()
    data.to_csv(csv_buffer, index=False)
    csv_buffer.seek(0)
    s3.put_object(Bucket=bucket_name, Key=csv_filename, Body=csv_buffer.getvalue())

def main():
    st.title('Registro de Entrenamientos de Six Gym')

    # Conectar a S3
    s3, bucket_name = conectar_s3()

    # Cargar DataFrame desde S3
    df_total = cargar_dataframe_desde_s3(s3, bucket_name)

    # Variables ingresadas por el cliente
    cliente = st.text_input('Nombre del Socio de Six Gym')
    grupoMuscular = st.text_input('Grupo Muscular')
    musculo = st.text_input('Músculo')
    ejercicio = st.text_input('Ejercicio')
    pesoMin = st.number_input('Peso Mínimo',  min_value=0, value=None, step=1)
    repeticionespesoMin = st.number_input('Repeticiones Peso Mínimo',  min_value=0, value=None, step=1)
    pesoMax = st.number_input('Peso Máximo',  min_value=0, value=None, step=1)
    repeticionespesoMax = st.number_input('Repeticiones Peso Máximo',  min_value=0, value=None, step=1)

    # Botón para guardar el registro
    if st.button('Guardar Entrenamiento'):
        fecha = obtener_fecha_argentina().strftime('%Y-%m-%d')
        hora = obtener_fecha_argentina().strftime('%H:%M:%S')
        cliente = 'Cliente1'  # Podrías tener un campo para que el cliente ingrese su nombre

        # Crear un DataFrame con los datos ingresados
        data = {
            'idEjercicio': [len(df_total) + 1],
            'fecha': [fecha],
            'hora': [hora],
            'cliente': [cliente],
            'grupoMuscular': [grupoMuscular],
            'musculo': [musculo],
            'ejercicio': [ejercicio],
            'pesoMin': [pesoMin],
            'repeticionespesoMin': [repeticionespesoMin],
            'pesoMax': [pesoMax],
            'repeticionespesoMax': [repeticionespesoMax]
        }
        df_new = pd.DataFrame(data)

        # Concatenar el nuevo DataFrame con el DataFrame total
        df_total = pd.concat([df_total, df_new], ignore_index=True)

        # Cargar los datos en el archivo CSV en S3
        upload_to_s3(df_total, s3, bucket_name)

        st.success('Entrenamiento guardado con éxito!')

if __name__ == '__main__':
    main()
