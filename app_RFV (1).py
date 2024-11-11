# Imports
import pandas as pd
import streamlit as st
import numpy as np
from datetime import datetime
from io import BytesIO

# Funções auxiliares para conversão de DataFrame
@st.cache
def convert_df(df):
    """Converte um DataFrame para CSV codificado em UTF-8."""
    return df.to_csv(index=False).encode('utf-8')

@st.cache
def to_excel(df):
    """Converte um DataFrame para um arquivo Excel em Bytes, para download."""
    output = BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    df.to_excel(writer, index=False, sheet_name='Sheet1')
    writer.save()
    processed_data = output.getvalue()
    return processed_data

# Funções de classificação para recência, frequência e valor (RFV)
def recencia_class(x, r, q_dict):
    """Classifica recência em quartis, com o menor quartil como melhor."""
    if x <= q_dict[r][0.25]:
        return 'A'
    elif x <= q_dict[r][0.50]:
        return 'B'
    elif x <= q_dict[r][0.75]:
        return 'C'
    else:
        return 'D'

def freq_val_class(x, fv, q_dict):
    """Classifica frequência e valor em quartis, com o maior quartil como melhor."""
    if x <= q_dict[fv][0.25]:
        return 'D'
    elif x <= q_dict[fv][0.50]:
        return 'C'
    elif x <= q_dict[fv][0.75]:
        return 'B'
    else:
        return 'A'

# Funções para calcular RFV
def calcula_recencia(df, dia_atual):
    """Calcula a recência para cada cliente."""
    df_recencia = df.groupby('ID_cliente', as_index=False)['DiaCompra'].max()
    df_recencia.columns = ['ID_cliente', 'DiaUltimaCompra']
    df_recencia['Recencia'] = df_recencia['DiaUltimaCompra'].apply(lambda x: (dia_atual - x).days)
    df_recencia.drop('DiaUltimaCompra', axis=1, inplace=True)
    return df_recencia

def calcula_frequencia(df):
    """Calcula a frequência de compras para cada cliente."""
    df_frequencia = df.groupby('ID_cliente').count()['CodigoCompra'].reset_index()
    df_frequencia.columns = ['ID_cliente', 'Frequencia']
    return df_frequencia

def calcula_valor(df):
    """Calcula o valor total gasto para cada cliente."""
    df_valor = df.groupby('ID_cliente').sum()['ValorTotal'].reset_index()
    df_valor.columns = ['ID_cliente', 'Valor']
    return df_valor

# Função principal
def main():
    # Configuração inicial da página da aplicação
    st.set_page_config(page_title='RFV', layout="wide", initial_sidebar_state='expanded')
    st.title("RFV - Segmentação de Clientes")

    # Carregar o arquivo
    st.sidebar.write("## Suba o arquivo")
    data_file = st.sidebar.file_uploader("Bank marketing data", type=['csv', 'xlsx'])

    if data_file:
        # Carregar dados
        df_compras = pd.read_csv(data_file, infer_datetime_format=True, parse_dates=['DiaCompra'])
        dia_atual = df_compras['DiaCompra'].max()

        # Calcular recência, frequência e valor
        df_recencia = calcula_recencia(df_compras, dia_atual)
        df_frequencia = calcula_frequencia(df_compras)
        df_valor = calcula_valor(df_compras)

        # Combinar os dados RFV em um único DataFrame
        df_RFV = df_recencia.merge(df_frequencia, on='ID_cliente').merge(df_valor, on='ID_cliente')
        df_RFV.set_index('ID_cliente', inplace=True)

        # Segmentação com quartis
        quartis = df_RFV.quantile(q=[0.25, 0.5, 0.75])
        df_RFV['R_quartil'] = df_RFV['Recencia'].apply(recencia_class, args=('Recencia', quartis))
        df_RFV['F_quartil'] = df_RFV['Frequencia'].apply(freq_val_class, args=('Frequencia', quartis))
        df_RFV['V_quartil'] = df_RFV['Valor'].apply(freq_val_class, args=('Valor', quartis))
        df_RFV['RFV_Score'] = df_RFV['R_quartil'] + df_RFV['F_quartil'] + df_RFV['V_quartil']

        # Mapear ações de marketing
        acoes_marketing = {
            'AAA': 'Enviar cupons de desconto, Pedir para indicar nosso produto pra algum amigo, Ao lançar um novo produto enviar amostras grátis pra esses.',
            'DDD': 'Churn! clientes que gastaram bem pouco e fizeram poucas compras, fazer nada',
            'DAA': 'Churn! clientes que gastaram bastante e fizeram muitas compras, enviar cupons de desconto para tentar recuperar',
            'CAA': 'Churn! clientes que gastaram bastante e fizeram muitas compras, enviar cupons de desconto para tentar recuperar'
        }
        df_RFV['acoes de marketing/crm'] = df_RFV['RFV_Score'].map(acoes_marketing)

        # Download do arquivo final
        df_xlsx = to_excel(df_RFV)
        st.download_button(label='📥 Download', data=df_xlsx, file_name='RFV_.xlsx')
        st.write(df_RFV)

if __name__ == '__main__':
    main()
