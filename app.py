import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import pytz

# --- CONFIGURAÇÕES DA PÁGINA ---
st.set_page_config(page_title="Zelo Kitchen - Inspeção", page_icon="🍳", layout="wide")

# Estilo CSS personalizado para forçar a quebra de linha (wrap) nas tabelas
st.markdown("""
    <style>
        /* Força o texto a pular linha e crescer para baixo no dataframe */
        [data-testid="stDataFrame"] td {
            white-space: normal !important;
            word-wrap: break-word !important;
        }
        div[data-testid="stExpander"] div[role="button"] p {
            font-weight: bold;
            font-size: 1.1rem;
        }
    </style>
""", unsafe_allow_html=True)

fuso_br = pytz.timezone('America/Sao_Paulo')
def obter_agora_br():
    return datetime.now(fuso_br)

# --- CONEXÃO COM GOOGLE SHEETS ---
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error(f"Erro na conexão com o banco de dados: {e}")

def carregar_dados():
    try:
        df = conn.read(ttl=0)
        # Converte a coluna de data para o formato correto do Pandas
        if not df.empty and "Data/Hora" in df.columns:
            df["Data/Hora"] = pd.to_datetime(df["Data/Hora"], dayfirst=True)
        return df
    except Exception as e:
        # Retorna estrutura vazia caso a planilha não exista ou esteja inacessível
        return pd.DataFrame(columns=["Data/Hora", "Funcionário", "Setor", "Equipamento", "Status", "Falhas", "Descrição do Problema"])

# --- ESTRUTURA DO CHECKLIST ---
setores_lista = ["Espaço Café", "Cozinha", "Mirante", "Refeitório"]
itens_setores = {
    "Espaço Café": ["Estufa quente", "Estufa fria", "Geladeiras balcão", "Frigobares", "Máquina de café expresso"],
    "Cozinha": ["Geladeiras Bacio di Latte", "Geladeiras Resfriados", "Câmaras Frias", "Freezers Horizontais", "Fornos", "Fogões", "Fritadeiras", "Chapas", "Geladeiras Balcões", "Coifas", "Pista Fria"],
    "Mirante": ["Freezer Sorvete Dona Mazza", "Adega Vinhos", "Geladeiras", "Geladeiras Balcões", "Lava Louças", "Coifas", "Pista Fria", "Elevador Monta Carga", "Freezer Horizontal", "Churrasqueira", "Forno a Lenha"],
    "Refeitório": ["Lava Louças", "Geladeira Resfriados", "Rechaud"]
}

# --- INTERFACE PRINCIPAL ---
st.title("🍳 Sistema de Inspeção Zelo Kitchen")

tab1, tab2 = st.tabs(["📝 Nova Inspeção", "📜 Histórico"])

# --- ABA 1: NOVA INSPEÇÃO ---
with tab1:
    if 'sucesso' in st.session_state and st.session_state.sucesso:
        st.success("✅ Inspeção salva com sucesso na planilha!")
        if st.button("Realizar Nova Inspeção"):
            st.session_state.sucesso = False
            st.rerun()
    else:
        with st.expander("📌 Identificação do Inspetor", expanded=True):
            col1, col2 = st.columns(2)
            nome_inspetor = col1.text_input("Seu Nome:")
            setor_selecionado = col2.selectbox("Setor a Inspecionar:", ["Selecione..."] + setores_lista)

        if setor_selecionado != "Selecione...":
            st.info(f"📋 Realizando checklist em: **{setor_selecionado}**")
            respostas = []
            
            for item in itens_setores[setor_selecionado]:
                with st.container(border=True):
                    st.write(f"**{item}**")
                    c1, c2, c3 = st.columns(3)
                    h = c1.radio(f"Higiene", ["OK", "NÃO"], key=f"h_{item}", horizontal=True)
                    f = c2.radio(f"Funcionamento", ["OK", "NÃO"], key=f"f_{item}", horizontal=True)
                    e = c3.radio(f"Estado Geral", ["OK", "NÃO"], key=f"e_{item}", horizontal=True)
                    
                    # Caixa de Descrição dinâmica: Aparece se houver qualquer "NÃO"
                    detalhes_obs = ""
                    if h == "NÃO" or f == "NÃO" or e == "NÃO":
                        detalhes_obs = st.text_area(f"Descreva o problema no(a) {item}:", 
                                                    key=f"obs_{item}", 
                                                    placeholder="Ex: Borracha da porta solta, temperatura oscilando...")
                    
                    respostas.append({"Equipamento": item, "H": h, "F": f, "E": e, "Detalhes": detalhes_obs})

            if st.button("🚀 FINALIZAR E SALVAR", type="primary", use_container_width=True):
                if not nome_inspetor:
                    st.error("Por favor, digite seu nome antes de salvar.")
                else:
                    with st.spinner("Enviando dados para a planilha..."):
                        agora = obter_agora_br().strftime("%d/%m/%Y %H:%M")
                        novas_entradas = []
                        
                        for r in respostas:
                            falhas_detectadas = [n for n, v in zip(["Higiene", "Funcionamento", "Estado"], [r["H"], r["F"], r["E"]]) if v == "NÃO"]
                            
                            novas_entradas.append({
                                "Data/Hora": agora,
                                "Funcionário": nome_inspetor,
                                "Setor": setor_selecionado,
                                "Equipamento": r["Equipamento"],
                                "Status": "❌ FALHA" if falhas_detectadas else "✅ OK",
                                "Falhas": ", ".join(falhas_detectadas) if falhas_detectadas else "Nenhuma",
                                "Descrição do Problema": r["Detalhes"]
                            })
                        
                        try:
                            df_atual = carregar_dados()
                            df_final = pd.concat([df_atual, pd.DataFrame(novas_entradas)], ignore_index=True)
                            conn.update(data=df_final)
                            st.session_state.sucesso = True
                            st.rerun()
                        except Exception as e:
                            # Tratamento para falso erro 200 (sucesso que retorna mensagem de erro)
                            if "200" in str(e):
                                st.session_state.sucesso = True
                                st.rerun()
                            else:
                                st.error(f"Erro ao salvar: {e}")

# --- ABA 2: HISTÓRICO ---
with tab2:
    st.subheader("📜 Filtros e Histórico")
    df_hist = carregar_dados()
    
    if not df_hist.empty:
        with st.expander("🔍 Filtrar Resultados", expanded=True):
            col_d1, col_d2 = st.columns(2)
            # Define datas mínimas e máximas baseadas na planilha
            data_min = df_hist["Data/Hora"].min().date()
            data_max = df_hist["Data/Hora"].max().date()
            
            data_inicio = col_d1.date_input("Início", value=data_min)
            data_fim = col_d2.date_input("Fim", value=data_max)
            
            col_f1, col_f2 = st.columns(2)
            filtro_setor = col_f1.multiselect("Setores", options=setores_lista, default=setores_lista)
            # PADRÃO: Sempre inicia mostrando apenas o que for FALHA
            filtro_status = col_f2.multiselect("Status", options=["✅ OK", "❌ FALHA"], default=["❌ FALHA"])

        # Aplicação lógica dos filtros
        mask = (
            (df_hist["Data/Hora"].dt.date >= data_inicio) & 
            (df_hist["Data/Hora"].dt.date <= data_fim) &
            (df_hist["Setor"].isin(filtro_setor)) &
            (df_hist["Status"].isin(filtro_status))
        )
        
        df_filtrado = df_hist.loc[mask].sort_values(by="Data/Hora", ascending=False)
        
        # Formatação visual para o usuário
        df_display = df_filtrado.copy()
        df_display["Data/Hora"] = df_display["Data/Hora"].dt.strftime("%d/%m/%Y %H:%M")
        
        st.write(f"Exibindo **{len(df_display)}** registros encontrados.")
        
        # Exibição da tabela com configuração de quebra de linha (wrap)
        st.dataframe(
            df_display, 
            use_container_width=True, 
            hide_index=True,
            column_config={
                "Descrição do Problema": st.column_config.TextColumn(
                    "Descrição do Problema",
                    width="large"
                ),
                "Status": st.column_config.TextColumn("Status", width="small"),
                "Data/Hora": st.column_config.TextColumn("Data/Hora", width="medium")
            }
        )
    else:
        st.info("Nenhum registro encontrado na planilha.")
