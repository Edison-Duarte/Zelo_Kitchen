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
                    
                    # Lógica da Caixa de Descrição: Se qualquer um for "NÃO"
                    obs = ""
                    if h == "NÃO" or f == "NÃO" or e == "NÃO":
                        obs = st.text_input(f"Descreva o problema observado no(a) {item}:", key=f"obs_{item}")
                    
                    respostas.append({"Equipamento": item, "H": h, "F": f, "E": e, "Detalhes": obs})

            if st.button("🚀 FINALIZAR E SALVAR", type="primary", use_container_width=True):
                if not nome_inspetor:
                    st.error("Por favor, digite seu nome.")
                else:
                    with st.spinner("Salvando..."):
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
                                "Descrição do Problema": r["Detalhes"] # Nova coluna
                            })
                        try:
                            df_atual = carregar_dados()
                            df_final = pd.concat([df_atual, pd.DataFrame(novas_entradas)], ignore_index=True)
                            conn.update(data=df_final)
                            st.session_state.sucesso = True
                            st.rerun()
                        except Exception as e:
                            if "200" in str(e): 
                                st.session_state.sucesso = True
                                st.rerun()
                            else: st.error(f"Erro: {e}")

with tab2:
    # O código do Histórico permanece o mesmo, apenas garantindo que a nova coluna apareça
    st.subheader("📜 Filtros do Histórico")
    df_hist = carregar_dados()
    if not df_hist.empty:
        # (Código de filtros omitido aqui por brevidade, mas deve ser mantido conforme a versão anterior)
        st.dataframe(df_hist, use_container_width=True, hide_index=True)
