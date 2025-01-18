import pandas as pd
import requests
from gekko import GEKKO
import io
import matplotlib.pyplot as plt

cultivos = {
    'papa': {'N': 210, 'P': 100.0, 'K': 350.0, 'Ca': 80.0, 'Mg': 40.0, 'S': 20.0},
    'pasto': {'N': 150, 'P': 60.0, 'K': 200.0, 'Ca': 70.0, 'Mg': 30.0, 'S': 15.0},
    'maiz': {'N': 180, 'P': 90.0, 'K': 300.0, 'Ca': 100.0, 'Mg': 50.0, 'S': 25.0},
    'avena': {'N': 200, 'P': 80.0, 'K': 250.0, 'Ca': 90.0, 'Mg': 35.0, 'S': 18.0},
    'otro': {'N': 100, 'P': 100, 'K': 100, 'Ca': 100, 'Mg': 20, 'S': 20}
}

def multiplicar_diccionario(diccionario, factor):
  """Multiplica los valores de un diccionario por un factor.
  Args:
    diccionario: El diccionario cuyos valores se van a multiplicar.
    factor: El factor por el cual se van a multiplicar los valores.

  Returns:
    Un nuevo diccionario con los valores multiplicados.
  """
  nuevo_diccionario = {}
  for clave, valor in diccionario.items():
    nuevo_diccionario[clave] = valor * factor
  return nuevo_diccionario

def load_data_from_github(url):
    response = requests.get(url)
    decoded_content = response.content.decode('utf-8')  
    df = pd.read_csv(io.StringIO(decoded_content))
    return df

# @title gekko
def run_gekko(df, resultado, area):
    m = GEKKO(remote=False)  # Crea un modelo Gekko remoto

    # Definición de L
    L = len(df)

    # Define variables de control a partir del DataFrame
    variables = {}
    for index, row in df.iterrows():
        variable_name = row['VARIABLE']
        variables[variable_name] = m.Var(lb=0, ub=10000)  # Restricciones para las variables de fertilizantes

    # Crea parámetros a partir del DataFrame (Precio de fertilizantes)
    parametros = {}
    for index, row in df.iterrows():
        nombre_parametro = f"c{index+1}"
        parametros[nombre_parametro] = m.Param(value=row['PRECIO'])

    # Crea las ecuaciones para cada nutriente (N, P, K, etc.)
    for nutriente in ['N', 'P', 'K', 'Ca', 'Mg', 'S']:
        equation = 0
        for i in range(L):
            equation += variables[df['VARIABLE'][i]] * df[nutriente][i]  # Nutrientes por fertilizantes

        # Definir la restricción de tolerancia al error (5%)
        error_margin = resultado[nutriente] * 0.05  # Tolerancia del 5%
        m.Equation(equation >= resultado[nutriente] - error_margin)
        m.Equation(equation <= resultado[nutriente] + error_margin)

    # Formula de minimización (Costo total)
    objective_function = 0
    for index, row in df.iterrows():
        variable_name = row['VARIABLE']
        price = row['PRECIO']
        objective_function += variables[variable_name] * price

    m.Minimize(objective_function)  # Minimizar el costo total de los fertilizantes

    # Configuramos la tolerancia de optimización
    m.options.IMODE = 3  # Modo de optimización
    m.options.SOLVER = 3  # Solucionador APOPT
    m.options.MV_TYPE = 1  # Variables de control
    m.options.OTOL = 1e-5  # Tolerancia de la optimización
    m.options.MAX_ITER = 10000  # Número máximo de iteraciones
    m.options.MAX_TIME = 10000  # Tiempo máximo para la solución
    m.solve(disp=True)

    # Extraer los resultados de forma segura y eficiente
    resultados = {}
    for var_name in m._variables:
        resultados[var_name.name] = var_name.value[0]

    # Filtrar los resultados eliminando valores menores a 50 y redondear a múltiplos de 50
    resultados_filtrados = {k: round(v / 50) * 50 for k, v in resultados.items() if v >= 50}

    # Eliminar resultados menores al filtro
    resultados_filtrados = {k: v for k, v in resultados_filtrados.items() if v >= area * 50}


    return resultados_filtrados

def plot_fertilizer_resultados(df, resultados):

    resultados_df = pd.DataFrame.from_dict(resultados, orient='index', columns=['value'])

    Filtro = resultados_df[resultados_df['value'] != 0]

    fertilizers = []
    values = []
    for index, row in Filtro.iterrows():
        variable_name = index
        if variable_name in resultados and resultados[variable_name] is not None and resultados[variable_name] != 0:
            var_index = int(variable_name[1:]) - 1
            if 0 <= var_index < len(df):
                fertilizers.append(df['FERTILIZANTE'][var_index])
                values.append(resultados[variable_name])
            else:
                print(f"Atencion: Index {var_index} Fuera del rango de la tabla de datos 'df'")

        # Filtrar el DataFrame para que solo contenga las filas donde la columna 'FERTILIZANTE' esté en la lista 'fertilizers'
    df_filtered = df[df['FERTILIZANTE'].isin(fertilizers)]

    # Seleccionar solo las columnas que necesitamos: 'FERTILIZANTE', 'MARCA', 'PRECIO'
    df_filtered = df_filtered[['FERTILIZANTE', 'MARCA', 'PRECIO']]

    # Agregar la nueva columna 'CANTIDAD KG' con los valores proporcionados en el vector 'values'
    df_filtered['CANTIDAD KG'] = values

    # Crear una nueva columna 'TOTAL' que sea el resultado de multiplicar 'PRECIO' por 'CANTIDAD KG'
    df_filtered['TOTAL'] = df_filtered['PRECIO'] * df_filtered['CANTIDAD KG']

    # Sumar la columna 'TOTAL' y almacenar el resultado en la variable 'Valor_Fertilizantes'
    Valor_Fertilizantes = df_filtered['TOTAL'].sum()

    # Formatear el valor en formato de dinero (por ejemplo, con dos decimales y símbolo de moneda)
    Valor_Fertilizantes = "${:,.2f}".format(Valor_Fertilizantes)

    # Formatear las columnas 'PRECIO' y 'TOTAL' como formato de dinero
    df_filtered['PRECIO'] = df_filtered['PRECIO'].apply(lambda x: "${:,.2f}".format(x))
    df_filtered['TOTAL'] = df_filtered['TOTAL'].apply(lambda x: "${:,.2f}".format(x))

    # Convertir el DataFrame a formato HTML
    df_html = df_filtered.to_html(classes='table-custom')

    # Create the bar plot with different colors and units
    plt.figure(figsize=(10, 8))
    colors = plt.cm.get_cmap('viridis', len(fertilizers))
    plt.bar(fertilizers, values, color=colors(range(len(fertilizers))))
    plt.xlabel("Fertilizantes", fontsize=14)
    plt.ylabel("Cantidad (kg)", fontsize=14)  # Added 'kg' unit to y-axis label
    plt.title("Cantidad de Fertilizantes Recomendada", fontsize=16)
    plt.xticks(rotation=25, ha='right')
    plt.subplots_adjust(top=0.85, bottom=0.2)

    for i, v in enumerate(values):
        plt.text(i, v, f"{round(v, 2)} kg", ha='center', va='bottom', fontsize=8)  # Added 'kg' unit to value labels

    # Guardar la imagen en un buffer
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png')
    plt.close()

    # Retornar los datos de la imagen como bytes
    return df_html, buffer.getvalue(), Valor_Fertilizantes  # Retornar el contenido del buffer (imagen en bytes)