from django.shortcuts import render
from django.http import HttpResponse
import requests
from . import utils
from gekko import GEKKO
from .utils import run_gekko, load_data_from_github 
from .utils import multiplicar_diccionario, plot_fertilizer_resultados
from django.shortcuts import render
import base64

def index(request):

    csv_url = 'https://raw.githubusercontent.com/Agrofertilab/calculatorGR/refs/heads/main/Fertilizantes_Granulados.csv'
    df = load_data_from_github(csv_url)
    # Convertir el DataFrame a HTML

    if request.method == 'POST':
        area = float(request.POST['area'])
        cultivo = request.POST['cultivo']

        if cultivo == 'papa':
            resultado = multiplicar_diccionario(utils.cultivos[cultivo], area)
        elif cultivo == 'pasto':
            resultado = multiplicar_diccionario(utils.cultivos[cultivo], area)
        elif cultivo == 'maiz':
            resultado = multiplicar_diccionario(utils.cultivos[cultivo], area)
        elif cultivo == 'avena':
            resultado = multiplicar_diccionario(utils.cultivos[cultivo], area)
        elif cultivo == 'otro':
            resultado = multiplicar_diccionario(utils.cultivos[cultivo], area)
        else:
            resultado = "Operación inválida"
        
        # Llamada a run_gekko
        resultado_gekko = run_gekko(df, resultado, area)
        #grafico= plot_fertilizer_resultados(df, resultado_gekko, Valor_Fertilizantes)
        df_html, image_data, Valor_Fertilizantes = plot_fertilizer_resultados(df, resultado_gekko)

        # Convertir a base64 para incluir en el HTML
        image_data_base64 = base64.b64encode(image_data).decode('utf-8')
        image_tag = f"data:image/png;base64,{image_data_base64}"

        # Actualizar el contexto con el nuevo resultado
        context = {'df_html': df_html, 'image_data': image_tag, 'Valor_Fertilizantes': Valor_Fertilizantes}
   
        return render(request, 'pages/index.html', context)
    else:
        return render(request, 'pages/index.html')
    
    