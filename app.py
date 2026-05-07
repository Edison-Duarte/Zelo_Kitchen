import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import pytz

# --- CONFIGURAÇÕES DA PÁGINA ---
st.set_page_config(page_title="Zelo Kitchen - Inspeção", page_icon="🍳", layout="wide")

fuso_br = pytz.timezone('America/Sao_Paulo')
def obter_agora_br():
    return datetime.now(fuso_br)

# --- CONEXÃO ---
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error(f"Erro na conexão: {e}")

def carregar_dados():
    try:
        df = conn.read(ttl=0)
        # Limpeza de colunas vazias que apareceram na sua imagem (None)
        df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
        if not df.empty and "Data/Hora" in df.columns:
            df["Data/Hora"] = pd.to_datetime(df["Data/Hora"], dayfirst=True)
        return df
    except Exception as e:
        return pd.DataFrame(columns=["Data/Hora", "Funcionário", "Setor", "Equipamento", "Status", "Falhas", "Descrição do Problema"])

# --- ESTRUTURA DO CHECKLIST ---
setores_lista = ["Espaço Café", "Cozinha", "Mirante", "Refeitório"]
itens_setores = {
    "Espaço Café": ["Estufa quente", "Estufa fria", "Geladeiras balcão", "Frigobares", "Máquina de café expresso"],
    "Cozinha": ["Geladeiras Bacio di Latte", "Geladeiras Resfriados", "Câmaras Frias", "Freezers Horizontais", "Fornos", "Fogões", "Fritadeiras", "Chapas", "Geladeiras Balcões", "Coifas", "Pista Fria"],
    "Mirante": ["Freezer Sorvete Dona Mazza", "Adega Vinhos", "Geladeiras", "Geladeiras Balcões", "Lava Louças", "Coifas", "Pista Fria", "Elevador Monta Carga", "Freezer Horizontal", "Churrasqueira", "Forno a Lenha"],
    "Refeitório": ["Lava Louças", "Geladeira Resfriados", "Rechaud"]
}

st.title("🍳 Sistema de Inspeção Zelo Kitchen")

tab1, tab2 = st.tabs(["📝 Nova Inspeção", "📜 Histórico"])

with tab1:
    if 'sucesso' in st.session_state and st.session_state.sucesso:
        st.success("✅ Inspeção salva com sucesso!")
        if st.button("Realizar Nova Inspeção"):
            st.session_state.sucesso = False
            st.rerun()
    else:
        with st.expander("📌 Identificação", expanded=True):
            col1, col2 = st.columns(2)
            nome_inspetor = col1.text_input("Seu Nome:")
            setor_selecionado = col2.selectbox("Setor a Inspecionar:", ["Selecione..."] + setores_lista)

        if setor_selecionado != "Selecione...":
            respostas = []
            for item in itens_setores[setor_selecionado]:
                with st.container(border=True):
                    st.write(f"**{item}**")
                    c1, c2, c3 = st.columns(3)
                    h = c1.radio(f"Higiene", ["OK", "NÃO"], key=f"h_{item}", horizontal=True)
                    f = c2.radio(f"Funcionamento", ["OK", "NÃO"], key=f"f_{item}", horizontal=True)
                    e = c3.radio(f"Estado Geral", ["OK", "NÃO"], key=f"e_{item}", horizontal=True)
                    
                    obs = ""
                    if h == "NÃO" or f == "NÃO" or e == "NÃO":
                        obs = st.text_area(f"Descreva o problema no(a) {item}:", key=f"obs_{item}")
                    
                    respostas.append({"Equipamento": item, "H": h, "F": f, "E": e, "Detalhes": obs})

            if st.button("🚀 FINALIZAR E SALVAR", type="primary", use_container_width=True):
                if not nome_inspetor:
                    st.error("Por favor, preencha seu nome.")
                else:
                    with st.spinner("Gravando..."):
                        agora = obter_agora_br().strftime("%d/%m/%Y %H:%M")
                        novas_entradas = []
                        for r in respostas:
                            falhas = [n for n, v in zip(["Higiene", "Funcionamento", "Estado"], [r["H"], r["F"], r["E"]]) if v == "NÃO"]
                            novas_entradas.append({
                                "Data/Hora": agora,
                                "Funcionário": nome_inspetor,
                                "Setor": setor_selecionado,
                                "Equipamento": r["Equipamento"],
                                "Status": "❌ FALHA" if falhas else "✅ OK",
                                "Falhas": ", ".join(falhas) if falhas else "Nenhuma",
                                "Descrição do Problema": r["Detalhes"]
                            })
                        try:
                            df_atual = carregar_dados()
                            df_final = pd.concat([df_atual, pd.DataFrame(novas_entradas)], ignore_index=True)
                            conn.update(data=df_final)
                            st.session_state.sucesso = True
                            st.rerun()
                        except Exception as e:
                            if "200" in str(e): st.session_state.sucesso = True; st.rerun()
                            else: st.error(f"Erro: {e}")

with tab2:
    st.subheader("📜 Filtros e Histórico")
    df_hist = carregar_dados()
    
    if not df_hist.empty:
        with st.expander("🔍 Filtros de Busca", expanded=True):
            col_d1, col_d2 = st.columns(2)
            data_min = df_hist["Data/Hora"].min().date()
            data_max = df_hist["Data/Hora"].max().date()
            data_inicio = col_d1.date_input("Início", value=data_min)
            data_fim = col_d2.date_input("Fim", value=data_max)
            
            col_f1, col_f2 = st.columns(2)
            filtro_setor = col_f1.multiselect("Setores", options=setores_lista, default=setores_lista)
            filtro_status = col_f2.multiselect("Status", options=["✅ OK", "❌ FALHA"], default=["❌ FALHA"])

        # Aplicação dos filtros
        mask = (
            (df_hist["Data/Hora"].dt.date >= data_inicio) & 
            (df_hist["Data/Hora"].dt.date <= data_fim) &
            (df_hist["Setor"].isin(filtro_setor)) &
            (df_hist["Status"].isin(filtro_status))
        )
        
        df_filtrado = df_hist.loc[mask].sort_values(by="Data/Hora", ascending=False)
        
        # Selecionamos apenas as colunas que importam para não poluir a tela
        colunas_exibicao = ["Data/Hora", "Funcionário", "Setor", "Equipamento", "Status", "Falhas", "Descrição do Problema"]
        df_display = df_filtrado[colunas_exibicao].copy()
        df_display["Data/Hora"] = df_display["Data/Hora"].dt.strftime("%d/%m/%Y %H:%M")
        
        st.write(f"Exibindo **{len(df_display)}** registros encontrados:")

        # --- A SOLUÇÃO DEFINITIVA ---
        # Usamos st.table porque ele força a quebra de linha (text-wrap) automaticamente 
        # e cresce a célula para baixo.
        if not df_display.empty:
            st.table(df_display)
        else:
            st.info("Nenhum item encontrado com os filtros aplicados.")
    else:
        st.info("Nenhum registro encontrado.")
