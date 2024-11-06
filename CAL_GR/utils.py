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

def run_gekko(df, resultado):

    m = GEKKO(remote=True)  # Crea un modelo Gekko remoto

    # Definición de L
    L = len(df)

    # Define variables a partir del DataFrame
    variables = {}
    for index, row in df.iterrows():
        variable_name = row['VARIABLE']
        variables[variable_name] = m.Var(lb=0, ub=10000)

    # Crea parámetros a partir del DataFrame
    parametros = {}
    for index, row in df.iterrows():
        nombre_parametro = f"c{index+1}"
        parametros[nombre_parametro] = m.Param(value=row['PRECIO'])

    # Crea una lista para almacenar las ecuaciones
    equations = []

    # Itera sobre los nutrientes (N, P, K, etc.)
    for nutriente in ['N', 'P', 'K', 'Ca', 'Mg', 'S']:

        # Crea la ecuación para cada nutriente directamente con Gekko
        equation = 0  
        for i in range(L):
            equation += variables[df['VARIABLE'][i]] * df[nutriente][i]  

        equations.append(m.Equation(equation == resultado[nutriente]))  

    # Formula de minimización
    objective_function = 0  
    for index, row in df.iterrows():
        variable_name = row['VARIABLE']
        price = row['PRECIO']
        objective_function += variables[variable_name] * price  

    m.Minimize(objective_function)

    m.options.IMODE = 3
    m.options.SOLVER = 3
    m.solve()

    # Extraer los resultados de forma segura y eficiente
    resultados = {}
    for var_name in m._variables:
        resultados[var_name.name] = var_name.value[0]
    
    # Eliminar valores menores a 50
    resultados_filtrados = {k: v for k, v in resultados.items() if v >= 50}

    # Obtener el valor del objetivo
    Valor_Fertilizantes = m.options.OBJFCNVAL
    # Convertir a formato de dinero (ejemplo con dos decimales y el signo $)
    Valor_Fertilizantes = "${:,.2f}".format(Valor_Fertilizantes)

    # Crear un DataFrame con los resultados filtrados
    resultados_df = pd.DataFrame.from_dict(resultados_filtrados, orient='index', columns=['value'])

    # Filtrar resultados y mapear a fertilizantes
    Filtro = resultados_df[resultados_df['value'] != 0]
    Filtro['fertilizante'] = Filtro.index.str[1:].astype(int) - 1
    Filtro['fertilizante'] = Filtro['fertilizante'].map(df.set_index('VARIABLE')['FERTILIZANTE'])

    return resultados_filtrados, Valor_Fertilizantes

def plot_fertilizer_resultados(df, resultados, Valor_Fertilizantes):

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
                print(f"Warning: Index {var_index} out of range for DataFrame 'df'")

    # Create the bar plot with different colors and units
    plt.figure(figsize=(10, 6))
    colors = plt.cm.get_cmap('viridis', len(fertilizers))
    plt.bar(fertilizers, values, color=colors(range(len(fertilizers))))
    plt.xlabel("Fertilizantes", fontsize=12)
    plt.ylabel("Cantidad (kg)", fontsize=12)  # Added 'kg' unit to y-axis label
    plt.title("Cantidad de Fertilizantes Recomendada", fontsize=14)
    plt.xticks(rotation=45, ha='right')

    for i, v in enumerate(values):
        plt.text(i, v, f"{round(v, 2)} kg", ha='center', va='bottom', fontsize=8)  # Added 'kg' unit to value labels

    # Guardar la imagen en un buffer
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png')
    plt.close()

    # Retornar los datos de la imagen como bytes
    return buffer.getvalue(), Valor_Fertilizantes  # Retornar el contenido del buffer (imagen en bytes)