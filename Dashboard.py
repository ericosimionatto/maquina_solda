import streamlit as st
import pyodbc
import random
from datetime import datetime, timedelta
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import classification_report
import matplotlib.pyplot as plt
import os
from pathlib import Path

# Configuração da aplicação
def configure_app():
    st.set_page_config(
        layout="wide",
        page_title="Monitoramento de Solda",
        page_icon="⚙️",
        initial_sidebar_state="expanded"
    )

# Função para gerar dados simulados
def gerar_e_inserir_dados(conn, n=100):
    cursor = conn.cursor()
    inseridos = 0

    for _ in range(n):
        try:
            data_hora = datetime.now() - timedelta(days=random.randint(0, 30))
            nome_maquina = random.choice(["M1", "M2", "M3"])
            lote = f"L{random.randint(1000, 9999)}"
            temp_ambiente = round(random.uniform(20.0, 30.0), 2)
            temp_min = round(random.uniform(220.0, 240.0), 2)
            temp_max = round(random.uniform(250.0, 280.0), 2)
            sensor_temp = round(random.uniform(temp_min, temp_max), 2)
            vibracao = round(random.uniform(0.5, 5.0), 2)
            inspecao_visual = random.choice(["OK", "Falha"])
            tempo_solda = round(random.uniform(10.0, 30.0), 2)
            umidade_ambiente = round(random.uniform(30.0, 90.0), 2)
            tempo_real_solda = round(random.uniform(5.0, 40.0), 2)
            status = "Crítica" if sensor_temp > 270 or vibracao > 4.5 or inspecao_visual == "Falha" else "Normal"
            observacao = "Temperatura ou vibração fora do padrão" if status == "Crítica" else "Sem anomalias"

            cursor.execute("""
                INSERT INTO MaquinaSolda (
                    DataHora, NomeMaquina, LoteFabricado, TempAmbiente, TempMin, TempMax,
                    SensorTemp, Vibracao, InspecaoVisual, TempoPadraoSolda, StatusMaq,
                    Observacao, UmidadeAmbiente, TempoRealSolda
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                data_hora, nome_maquina, lote, temp_ambiente, temp_min, temp_max,
                sensor_temp, vibracao, inspecao_visual, tempo_solda, status,
                observacao, umidade_ambiente, tempo_real_solda
            ))

            inseridos += 1
        except Exception as e:
            st.error(f"Erro ao inserir dado: {e}")

    conn.commit()
    return inseridos

# Página de visualização da topologia
def show_topology_page():
    st.title("Topologia da Aplicação")
    
    if not Path("Topologia_aplicacao.html").exists():
        st.error("Arquivo de topologia não encontrado.")
        return
    
    try:
        with open("Topologia_aplicacao.html", "r", encoding="utf-8") as f:
            html_content = f.read()
        st.components.v1.html(html_content, height=800, scrolling=True)
    except Exception as e:
        st.error(f"Erro ao carregar o arquivo de topologia: {e}")

# Função para criar e exibir gráficos
def display_charts(df_maquina, maquina):
    st.write(f"### Máquina {maquina}")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("#### Temperatura do Sensor")
        fig_temp = plt.figure(figsize=(10, 4))
        plt.plot(df_maquina['DataHora'], df_maquina['SensorTemp'], label='Temperatura', color='red')
        plt.axhline(y=270, color='r', linestyle='--', label='Limite Crítico')
        plt.xlabel("Data/Hora")
        plt.ylabel("Temperatura (°C)")
        plt.legend()
        plt.grid(True)
        plt.xticks(rotation=45)
        st.pyplot(fig_temp)
        plt.close()
        
        st.metric("Média de Temperatura", f"{df_maquina['SensorTemp'].mean():.2f} °C")
    
    with col2:
        st.write("#### Nível de Vibração")
        fig_vib = plt.figure(figsize=(10, 4))
        plt.plot(df_maquina['DataHora'], df_maquina['Vibracao'], label='Vibração', color='blue')
        plt.axhline(y=4.5, color='b', linestyle='--', label='Limite Crítico')
        plt.xlabel("Data/Hora")
        plt.ylabel("Vibração (m/s²)")
        plt.legend()
        plt.grid(True)
        plt.xticks(rotation=45)
        st.pyplot(fig_vib)
        plt.close()
        
        st.metric("Média de Vibração", f"{df_maquina['Vibracao'].mean():.2f} m/s²")
    
    st.write("#### Tempo de Solda - Real vs Padrão")
    fig_tempo = plt.figure(figsize=(10, 4))
    plt.plot(df_maquina['DataHora'], df_maquina['TempoPadraoSolda'], label='Padrão', color='green')
    plt.plot(df_maquina['DataHora'], df_maquina['TempoRealSolda'], label='Real', color='purple')
    plt.xlabel("Data/Hora")
    plt.ylabel("Tempo (s)")
    plt.legend()
    plt.grid(True)
    plt.xticks(rotation=45)
    st.pyplot(fig_tempo)
    plt.close()

# Página principal de monitoramento
def show_monitoring_page(conn):
    st.title("📊 Monitoramento de Máquinas de Solda por Onda")
    
    # Inicializa o estado de atualização se não existir
    if 'force_refresh' not in st.session_state:
        st.session_state.force_refresh = False
    
    with st.sidebar:
        st.header("Configurações de Filtro")
        
        try:
            maquinas_disponiveis = pd.read_sql("SELECT DISTINCT NomeMaquina FROM MaquinaSolda", conn)['NomeMaquina'].tolist()
        except Exception as e:
            st.error(f"Erro ao obter lista de máquinas: {e}")
            maquinas_disponiveis = ["M1", "M2", "M3"]
        
        if not maquinas_disponiveis:
            if st.button("Inserir dados de teste"):
                gerar_e_inserir_dados(conn, 50)
                st.session_state.force_refresh = not st.session_state.force_refresh
                st.success("Dados de teste inseridos com sucesso!")
            return
        
        maquinas_selecionadas = st.multiselect(
            "Selecione as máquinas:",
            maquinas_disponiveis,
            default=maquinas_disponiveis[:1] if maquinas_disponiveis else None
        )
        
        data_fim = datetime.now().date()
        data_inicio = (datetime.now() - timedelta(days=7)).date()
        
        data_inicio = st.date_input("Data de início:", value=data_inicio)
        data_fim = st.date_input("Data de fim:", value=data_fim)
        
        if st.button("Gerar dados aleatórios"):
            qtd = gerar_e_inserir_dados(conn, 50)
            st.session_state.force_refresh = not st.session_state.force_refresh
            st.success(f"{qtd} registros de teste inseridos!")

        st.markdown("---")
        if st.button("Visualizar Topologia do Sistema"):
            st.session_state.current_page = "topology"

    if not maquinas_selecionadas:
        st.warning("Selecione pelo menos uma máquina.")
        return
    
    try:
        query = """
            SELECT * FROM MaquinaSolda 
            WHERE NomeMaquina IN ({})
            AND CONVERT(DATE, DataHora) BETWEEN ? AND ?
            ORDER BY DataHora DESC
        """.format(','.join(['?'] * len(maquinas_selecionadas)))
        
        params = maquinas_selecionadas + [data_inicio, data_fim + timedelta(days=1)]
        
        df = pd.read_sql(query, conn, params=params)
        
    except Exception as e:
        st.error(f"Erro ao ler dados do banco: {e}")
        return

    if df.empty:
        st.warning("Nenhum dado encontrado com os filtros atuais.")
        return

    # Usar o estado de atualização para forçar o recarregamento
    st.session_state.force_refresh

    with st.expander("🔍 Análise de Qualidade", expanded=True):
        st.subheader("Status das Máquinas")
        
        le = LabelEncoder()
        df['StatusNum'] = le.fit_transform(df['StatusMaq'])
        
        features = ['SensorTemp', 'Vibracao', 'TempAmbiente', 'TempMin', 
                   'TempMax', 'TempoPadraoSolda', 'UmidadeAmbiente', 'TempoRealSolda']
        
        for maquina in maquinas_selecionadas:
            df_maq = df[df['NomeMaquina'] == maquina].copy()
            
            if len(df_maq) > 0:
                X = df_maq[features]
                y = df_maq['StatusNum']
                
                if len(y.unique()) > 1:
                    X_train, X_test, y_train, y_test = train_test_split(
                        X, y, test_size=0.3, random_state=42)
                    modelo = RandomForestClassifier(n_estimators=100, random_state=42)
                    modelo.fit(X_train, y_train)
                    y_pred = modelo.predict(X_test)
                    
                    col1, col2 = st.columns(2)
                    taxa_criticos = (df_maq['StatusMaq'] == 'Crítica').mean() * 100
                    precisao = modelo.score(X_test, y_test) * 100
                    
                    with col1:
                        st.metric("Taxa de Críticos", 
                                 f"{taxa_criticos:.1f}%",
                                 delta=f"-{taxa_criticos - 15:.1f}% vs esperado"
                                 if taxa_criticos > 15 else None)
                        
                    with col2:
                        st.metric("Precisão do Modelo", f"{precisao:.1f}%")
                    
                    st.text(classification_report(y_test, y_pred, target_names=['Crítica', 'Normal']))
                else:
                    st.warning(f"Máquina {maquina} tem apenas uma classe de dados.")
                
                display_charts(df_maq, maquina)
                
                with st.expander(f"📋 Dados detalhados - Máquina {maquina}", expanded=False):
                    st.dataframe(df_maq.sort_values('DataHora', ascending=False).reset_index(drop=True))

    st.download_button(
        label="Baixar dados filtrados (CSV)",
        data=df.to_csv(index=False).encode('utf-8'),
        file_name=f"dados_solda_{datetime.now().strftime('%Y%m%d-%H%M%S')}.csv",
        mime='text/csv'
    )

# Função principal
def main():
    configure_app()
    
    if 'current_page' not in st.session_state:
        st.session_state.current_page = "monitoring"
    
    try:
        conn = pyodbc.connect(
            'DRIVER={ODBC Driver 17 for SQL Server};'
            'SERVER=localhost;'
            'DATABASE=FABRICA1;'
            'UID=sa;'
            'PWD=sql'
        )
    except Exception as e:
        st.error(f"Erro de conexão com o banco: {e}")
        return

    if st.session_state.current_page == "topology":
        show_topology_page()
        if st.button("Voltar para Monitoramento"):
            st.session_state.current_page = "monitoring"
    else:
        show_monitoring_page(conn)
    
    conn.close()

if __name__ == "__main__":
    main()                
