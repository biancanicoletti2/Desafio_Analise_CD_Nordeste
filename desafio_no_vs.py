import os
import random 
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
import sys 
import warnings #  Importação do módulo warnings nativo do Python
from dotenv import load_dotenv 
from langchain_google_genai import ChatGoogleGenerativeAI 
from langchain_core.tools import tool 


# ======================================================================
# --- 1. CONFIGURAÇÃO DE AMBIENTE E CHAVES DE API ---
# ======================================================================

# 1. Carrega as variáveis do arquivo .env para o ambiente Python
# Isso permite manter a chave da API em um arquivo separado e não expor no código.
load_dotenv() 

# 2. CONFIGURAÇÃO DA CHAVE DE API
GOOGLE_API_KEY = os.environ.get('GEMINI_API_KEY') 

if not GOOGLE_API_KEY:
    raise ValueError("ERRO: A variável de ambiente 'GEMINI_API_KEY' não foi definida no arquivo .env. Defina-a para continuar.")
else:
    print("Ambiente configurado. Chave Gemini carregada via .env.")

# --- CORREÇÃO DE AMBIENTE ---
os.environ['LANGCHAIN_TRACING_V2'] = 'false'
os.environ['LANGCHAIN_CALLBACKS_BACKGROUND'] = 'false'


# ======================================================================
# --- 2. DEFINIÇÃO DAS FUNÇÕES AUXILIARES ---
# ======================================================================

def coletar_dados_imoveis(cidade: str) -> pd.DataFrame:
    """Simula a coleta de dados de imóveis para regressão de custo.
    - Recife e Salvador possuem preços base diferentes
    - A função gera uma amostra aleatória de imóveis com área e preço.
    """
    n_registros = 50 
    
    if cidade == 'Recife':
        base_preco = 10_000_000 
        variacao_logistica = 0.8
    else: # Salvador
        base_preco = 12_000_000 
        variacao_logistica = 1.2
        
    df = pd.DataFrame({
        'cidade': cidade,
        'area_m2': np.random.randint(5000, 15000, n_registros),
        'preco': (base_preco * variacao_logistica + 
                  np.random.randn(n_registros) * 2_000_000)
    })
    return df

def calculate_ors_matrix(origens: list, destinos: list) -> dict:
    """Simula cálculo de matriz de distâncias e durações entre cidades.
    - Substitui a chamada real ao ORS (OpenRouteService).
    - Usa distribuições aleatórias para gerar distância e tempo.
    """
    print("Simulando chamada ORS...")

    coords = {
        'Recife, PE': [-34.8828, -8.0578],
        'Salvador, BA': [-38.5014, -12.9714],
        'Natal, RN': [-35.2104, -5.7945],
        'Fortaleza, CE': [-38.5267, -3.7319],
        'Maceió, AL': [-35.7350, -9.6659],
        'João Pessoa, PB': [-34.8645, -7.1195],
        'Aracaju, SE': [-37.0731, -10.9472]
    }

    distances = []
    durations = []
    
    for origem_str in origens:
        row_dist = []
        row_dur = []
        
        for _ in destinos:
            if 'Recife' in origem_str:
                dist = random.uniform(300000, 700000)
                dur = dist / 1000 * 40
            else: 
                dist = random.uniform(500000, 1000000)
                dur = dist / 1000 * 45
            
            row_dist.append(dist)
            row_dur.append(dur)
        
        distances.append(row_dist)
        durations.append(row_dur)

    return {
        'status': 'ok',
        'distances_meters': distances,
        'durations_seconds': durations,
        'message': 'Dados simulados com sucesso.'
    }

# --- Função de ANÁLISE (Wrapper para o cálculo) ---
def realizar_analise_avancada(df_imoveis: pd.DataFrame, capitais_alvo: list, fuel_cost_factor: float = 1.0) -> dict:
    
    # Usa o módulo warnings nativo do Python para suprimir warnings do sklearn
    with warnings.catch_warnings(): #Evita poluição no terminal durante testes.
        warnings.filterwarnings("ignore", message="X does not have valid feature names")
        
        resultados = {}
        
        # 1. ANÁLISE DE CUSTOS E INSTALAÇÃO (REGRESSÃO)
        print("Executando Regressão para Custos Imobiliários...")
        if not df_imoveis.empty and len(df_imoveis) > 10:
            df_imoveis['cidade_cod'] = df_imoveis['cidade'].apply(lambda x: 1 if x == 'Recife' else 0)
            features_regressao = df_imoveis[['area_m2', 'cidade_cod']]
            target_regressao = df_imoveis['preco']

            modelo_regressao = RandomForestRegressor(n_estimators=100, random_state=42) # Bom para não-linearidade, robusto contra overfitting, não exige normalização
            modelo_regressao.fit(features_regressao, target_regressao)

            previsao_recife = modelo_regressao.predict([[10000, 1]])[0]
            previsao_salvador = modelo_regressao.predict([[10000, 0]])[0]
            custo_instalacao = {'Recife': 5_000_000, 'Salvador': 6_500_000} 
            
            resultados['custos'] = {
                'Recife': previsao_recife + custo_instalacao['Recife'],
                'Salvador': previsao_salvador + custo_instalacao['Salvador'],
                'Recife_imovel': previsao_recife,
                'Salvador_imovel': previsao_salvador,
            }
        else:
            resultados['custos'] = {'Recife': 0, 'Salvador': 0, 'erro': 'Dados insuficientes para Regressão.'}


        # 2. ANÁLISE LOGÍSTICA (MATRIX API ORS E CUSTO TOTAL)
        print("Executando Análise Logística Avançada (Matrix ORS)...")
        origens = ['Recife, PE', 'Salvador, BA']
        matrix_data = calculate_ors_matrix(origens, capitais_alvo) 

        if matrix_data['status'] == 'ok':
            df_distancia = pd.DataFrame(matrix_data['distances_meters'], index=origens, columns=capitais_alvo)
            df_duracao = pd.DataFrame(matrix_data['durations_seconds'], index=origens, columns=capitais_alvo)
            
            CUSTO_POR_KM = (1.50 * fuel_cost_factor) #O custo por km é ajustado pelo fator de combustível, 
            DEMANDA_CAPITAIS = pd.Series([1.0, 1.2, 0.8, 0.9, 0.7], index=capitais_alvo) #A demanda relativa de cada capital pondera o custo.
            df_custo_mensal = (df_distancia / 1000) * CUSTO_POR_KM * DEMANDA_CAPITAIS
            custo_logistico_recife = df_custo_mensal.loc['Recife, PE'].sum()
            custo_logistico_salvador = df_custo_mensal.loc['Salvador, BA'].sum()
            
            resultados['logistica'] = {
                'Recife_total_custo': custo_logistico_recife,
                'Salvador_total_custo': custo_logistico_salvador,
                'media_tempo_recife': df_duracao.loc['Recife, PE'].mean() / 3600,
                'media_tempo_salvador': df_duracao.loc['Salvador, BA'].mean() / 3600,
            }
        else:
            resultados['logistica'] = {'Recife_total_custo': 99999, 'Salvador_total_custo': 99999, 'erro': matrix_data['message']}


        # 3. ANÁLISE DE MERCADO E CRITÉRIOS MÚLTIPLOS (PONDERAÇÃO)
        print("Executando Análise Multicritério (Ponderação)...")
        
        dados_cidades = pd.DataFrame({
            'cidade': ['Recife', 'Salvador'],
            'populacao_regiao_milhoes': [20.0, 25.0],
            'pib_regiao_bilhoes': [350, 420],
            'acesso_rodovias': [5, 3], 
            'proximidade_portos': [4, 5], 
            'incentivos_fiscais': [3, 4] 
        })
        
        custo_total_r = resultados['custos']['Recife']
        custo_total_s = resultados['custos']['Salvador']
        log_custo_r = resultados['logistica']['Recife_total_custo']
        log_custo_s = resultados['logistica']['Salvador_total_custo']
        
        max_custo = max(custo_total_r, custo_total_s)
        min_custo = min(custo_total_r, custo_total_s)
        score_custo_r = 100 * (1 - (custo_total_r - min_custo) / (max_custo - min_custo + 1e-9)) 
        score_custo_s = 100 * (1 - (custo_total_s - min_custo) / (max_custo - min_custo + 1e-9))
        max_log = max(log_custo_r, log_custo_s)
        min_log = min(log_custo_r, log_custo_s)
        score_log_r = 100 * (1 - (log_custo_r - min_log) / (max_log - min_log + 1e-9))
        score_log_s = 100 * (1 - (log_custo_s - min_log) / (max_log - min_log + 1e-9))
        dados_cidades['score_mercado'] = dados_cidades[['acesso_rodovias', 'proximidade_portos', 'incentivos_fiscais']].mean(axis=1) * 20 
        score_mercado_r = dados_cidades.loc[dados_cidades['cidade'] == 'Recife', 'score_mercado'].iloc[0]
        score_mercado_s = dados_cidades.loc[dados_cidades['cidade'] == 'Salvador', 'score_mercado'].iloc[0]

        peso_log = 0.40 #Os pesos são hiperparâmetros de decisão estratégica: podem ser alterados pela diretoria para refletir prioridade.
        peso_custo = 0.30
        peso_mercado = 0.30

        score_final_r = (score_log_r * peso_log) + (score_custo_r * peso_custo) + (score_mercado_r * peso_mercado)
        score_final_s = (score_log_s * peso_log) + (score_custo_s * peso_custo) + (score_mercado_s * peso_mercado)
        
        resultados['score_final'] = {
            'Recife': score_final_r,
            'Salvador': score_final_s,
            'Ponderacao_Usada': {'Logistica': 40, 'Custo': 30, 'Mercado': 30}
        }
        
        return resultados

def calcular_e_analisar(df_imoveis: pd.DataFrame, capitais_alvo: list, fuel_cost_factor: float = 1.0) -> dict:
    return realizar_analise_avancada(df_imoveis, capitais_alvo, fuel_cost_factor)

# --- Função de RELATÓRIO (o @tool) ---
@tool #Integração com LangChain para expor funções ao agente.
def gerar_relatorio_final_avancado(resultados_base: dict, resultados_risco: dict) -> str:
    """Gera o relatório executivo final com base nos resultados de análise de custos e riscos."""
    return "Relatório gerencial final pronto."


# ======================================================================
# --- 3. EXECUÇÃO DA ANÁLISE E GERAÇÃO DE RELATÓRIO ---
# ======================================================================
CAPITAIS_ALVO = ['Natal, RN', 'Fortaleza, CE', 'Maceió, AL', 'João Pessoa, PB', 'Aracaju, SE']

print("\n--- 1. PREPARAÇÃO DE DADOS ---")
df_imoveis_recife = coletar_dados_imoveis('Recife') 
df_imoveis_salvador = coletar_dados_imoveis('Salvador')
df_imoveis_total = pd.concat([df_imoveis_recife, df_imoveis_salvador], ignore_index=True)
print(f"Total de {len(df_imoveis_total)} registros de imóveis para análise.")

# 2. Execução do CENÁRIO BASE
CENARIO_BASE_NOME = "Cenário Base (Custo de Combustível Estável)"
print(f"\n--- 2. EXECUTANDO: {CENARIO_BASE_NOME} ---")
resultados_base = calcular_e_analisar( 
    df_imoveis=df_imoveis_total, 
    capitais_alvo=CAPITAIS_ALVO, 
    fuel_cost_factor=1.0 
)

# 3. Execução do CENÁRIO DE RISCO
CENARIO_RISCO_NOME = "Cenário de Risco (Aumento de 20% no Custo de Combustível)"
print(f"\n--- 3. EXECUTANDO: {CENARIO_RISCO_NOME} ---")
resultados_risco = calcular_e_analisar(
    df_imoveis=df_imoveis_total, 
    capitais_alvo=CAPITAIS_ALVO, 
    fuel_cost_factor=1.20
)


# 4. ORQUESTRAÇÃO FINAL
print("\n--- 4. ORQUESTRAÇÃO FINAL: GERAÇÃO DE RELATÓRIO GERENCIAL ---")

tools = [gerar_relatorio_final_avancado] 

MODELO_AGENTE = 'gemini-2.5-pro' 
llm_agente = ChatGoogleGenerativeAI(
    model=MODELO_AGENTE, 
    temperature=0.2, #A temperature=0.2 foi escolhida para relatórios consistentes e formais, evitando variação criativa excessiva.
    google_api_key=GOOGLE_API_KEY,  # <--- FORÇA O USO DA CHAVE CARREGADA
    model_kwargs={"tools": tools}   
)

resultados_base_str = str(resultados_base)
resultados_risco_str = str(resultados_risco)
#Esse prompt define persona e contexto, forçando o modelo a escrever em tom executivo.
prompt_relatorio = f"""
Você é um **Analista de Localização Sênior** focado em Logística e Imobiliário.

Sua tarefa é elaborar um **Relatório Executivo de Recomendação** para a diretoria, que precisa decidir entre **Recife** e **Salvador** para a instalação de um novo Centro de Distribuição (CD).
... [O prompt continua] ...

**Dados de Análise (OBRIGATÓRIO USAR ESTES DADOS):**
**CENÁRIO BASE (Custo de Combustível Estável):**
{CENARIO_BASE_NOME}
{resultados_base_str}

**CENÁRIO DE RISCO (Aumento de 20% no Custo de Combustível):**
{CENARIO_RISCO_NOME}
{resultados_risco_str}

...
"""

# Chama o modelo para gerar o relatório
relatorio_executivo = llm_agente.invoke(prompt_relatorio)

print("\n" + "="*80)
print(f"RELATÓRIO EXECUTIVO GERADO PELO AGENTE ({MODELO_AGENTE})")
print("="*80)
print(relatorio_executivo.content)
print("="*80)