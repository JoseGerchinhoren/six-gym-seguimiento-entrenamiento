import pandas as pd

# Leer el archivo CSV
df = pd.read_csv('entrenamientosHipertrofia.csv')

# Función para normalizar la columna 'ejercicio'
def normalizar_ejercicio(texto):
    # Eliminar espacios en blanco al principio y al final
    texto = texto.strip()
    # Dividir el texto en palabras
    palabras = texto.split()
    # Convertir la primera palabra a mayúscula
    palabras[0] = palabras[0].capitalize()
    # Unir las palabras nuevamente en un solo texto
    return ' '.join(palabras)

# Aplicar la función a la columna 'ejercicio'
df['ejercicio'] = df['ejercicio'].apply(normalizar_ejercicio)

# Guardar el DataFrame modificado en un nuevo archivo CSV
df.to_csv('entrenamientosHipertrofia_normalizado.csv', index=False)

print("Datos normalizados y guardados correctamente en 'entrenamientosHipertrofia_normalizado.csv'.")
