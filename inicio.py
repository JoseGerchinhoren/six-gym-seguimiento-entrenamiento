import streamlit as st
import boto3
import pandas as pd

from config import cargar_configuracion
from entrenamientosHipertrofia import main as ingresaEntrenamiento
from ingresaUsuarios import ingresa_usuario
from visualizaUsuarios import main as visualiza_usuarios

# Obtener credenciales
aws_access_key, aws_secret_key, region_name, bucket_name = cargar_configuracion()

# Conecta a S3
s3 = boto3.client('s3', aws_access_key_id=aws_access_key, aws_secret_access_key=aws_secret_key, region_name=region_name)

# Función para obtener usuarios desde el archivo CSV en S3
def buscar_usuarios(nombre_usuario_input):
    try:
        # Leer el archivo CSV desde S3
        csv_file_key = 'usuarios.csv'
        response = s3.get_object(Bucket=bucket_name, Key=csv_file_key)
        usuarios_df = pd.read_csv(response['Body'])

        # Filtrar por nombre de usuario
        usuarios_df = usuarios_df[usuarios_df['nombreApellido'].str.contains(nombre_usuario_input, case=False)]

        return usuarios_df

    except Exception as e:
        st.error(f"Error al buscar usuarios: {e}")
        return pd.DataFrame()

# Definir las variables para el estado de inicio de sesión
logged_in = st.session_state.get("logged_in", False)
user_nombre_apellido = st.session_state.get("user_nombre_apellido", "")
user_rol = st.session_state.get("user_rol", "")

# Función para verificar las credenciales y obtener el rol del usuario
def login(username, password):
    try:
        # Capitalizar el nombre de usuario ingresado
        username = username.strip().title()

        usuarios_df = buscar_usuarios(username)

        if not usuarios_df.empty:
            stored_password = usuarios_df.iloc[0]['contraseña']
            if password == stored_password:
                st.session_state.logged_in = True
                st.session_state.user_rol = usuarios_df.iloc[0]['rol']
                st.session_state.user_nombre_apellido = username
                st.session_state.id_usuario = usuarios_df.iloc[0]['idUsuario']
                st.experimental_rerun()
            else:
                st.error("Credenciales incorrectas. Inténtalo de nuevo")
        else:
            st.error("Usuario no encontrado")

    except Exception as e:
        st.error(f"Error al conectar a la base de datos: {e}")

# Función para cerrar sesión
def logout():
    st.session_state.logged_in = False
    st.session_state.user_rol = ""
    st.session_state.user_nombre_apellido = ""  # Limpiar el nombre y apellido al cerrar sesión
    st.success("Sesión cerrada exitosamente")

def main():
    st.markdown("<h1 style='text-align: center; color: green;'>SixGym</h1>", unsafe_allow_html=True)
    st.markdown("<h2 style='text-align: center; color: yellow;'>🏋️‍♀️Seguimiento de Entrenamientos🏋️‍♂️</h1>", unsafe_allow_html=True)

    if logged_in:
        st.sidebar.title("Menú")

        # st.subheader(f"Bienvenido/a, {user_nombre_apellido}!")

        if user_rol == "admin":
            selected_option = st.sidebar.selectbox("Seleccione una opción:", ["Entrenamientos de Hipertrofia","Entrenamientos de Fuerza", "Usuarios"])
            # if selected_option == "Ventas":
            #     with st.expander('Ingresar Venta'):
            #         venta(st.session_state.user_nombre_apellido)
            #     with st.expander('Visualizar Ventas'):
            #         visualiza_ventas()
            if selected_option == 'Entrenamientos de Hipertrofia':
                ingresaEntrenamiento()
                
                # with st.expander('Visualiza Entrenamientos'):
                #     visualizaEntrenamiento()

            if selected_option == "Usuarios":
                st.title('Usuarios')
                with st.expander('Ingresar Usuario'):
                    ingresa_usuario()
                with st.expander('Visualizar Usuarios'):
                    visualiza_usuarios()
            
            
            # if selected_option == "Inicio":
            #     texto_inicio()            

        elif user_rol == "socio":
            selected_option = st.sidebar.selectbox("Seleccione una opción:", ["Nuevo Entrenamiento", "Visualiza Entrenamientos"])
            if selected_option == 'Nuevo Entrenamiento':
                ingresaEntrenamiento()

            # if selected_option == 'Visualiza Entrenamiento':
            #     visualizaEntrenamiento()

        st.write(f"Usuario: {user_nombre_apellido}")

    else:
        st.sidebar.title("Inicio de Sesión")

        with st.form(key="login_form"):
            username = st.text_input("Nombre de Usuario:")
            password = st.text_input("Contraseña:", type="password")

            login_submitted = st.form_submit_button("Iniciar Sesión")

            if login_submitted and username and password:
                login(username, password)

    if logged_in:
        st.sidebar.button("Cerrar Sesión", on_click=logout)

if __name__ == "__main__":
    main()