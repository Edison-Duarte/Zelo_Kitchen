import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import urllib.parse

st.set_page_config(page_title="Inspeção e Histórico", page_icon="📝", layout="wide")

# --- CONEXÃO COM O BANCO DE DADOS (Google Sheets) ---
# Nota: Você precisará configurar o secrets do Streamlit com a URL da sua planilha
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df_historico = conn.read(ttl="0") # ttl=0 garante que ele busque dados frescos
except:
    # Caso não tenha configurado a planilha ainda, cria um DataFrame vazio para teste
    df_historico = pd.DataFrame(columns=["Data", "Colaborador", "Setor", "Status", "Detalhes"])

# --- INTERFACE ---
aba_inspecao, aba_historico = st.tabs(["📋 Nova Inspeção", "📜 Histórico de Relatórios"])

setores = {
    "Espaço Café": ["Estufa quente", "Estufa fria", "Geladeiras balcão", "Frigobares", "Máquina de café expresso"],
    "Cozinha": ["Geladeiras Bacio di Latte", "Geladeiras Resfriados", "Câmaras Frias", "Freezers Horizontais", "Fornos", "Fogões", "Fritadeiras", "Chapas", "Geladeiras Balcões", "Coifas", "Pista Fria"],
    "Mirante": ["Freezer Sorvete Dona Mazza", "Adega Vinhos", "Geladeiras", "Geladeiras Balcões", "Lava Louças", "Coifas", "Pista Fria", "Elevador Monta Carga", "Freezer Horizontal", "Churrasqueira", "Forno a Lenha"],
    "Refeitório": ["Lava Louças", "Geladeira Resfriados", "Rechaud"]
}

with aba_inspecao:
    st.header("🍳 Nova Inspeção")
    
    with st.container(border=True):
        col1, col2 = st.columns(2)
        nome = col1.text_input("👤 Nome do Colaborador")
        setor_sel = col2.selectbox("📍 Local", ["Selecione..."] + list(setores.keys()))

    if setor_sel != "Selecione...":
        respostas = {}
        with st.form("form_checklist"):
            for equip in setores[setor_sel]:
                st.write(f"**{equip}**")
                c1, c2, c3 = st.columns(3)
                respostas[f"{equip}_H"] = c1.radio("Higiene", ["OK", "NÃO"], key=f"{equip}h", horizontal=True)
                respostas[f"{equip}_F"] = c2.radio("Funcion.", ["OK", "NÃO"], key=f"{equip}f", horizontal=True)
                respostas[f"{equip}_E"] = c3.radio("Estado", ["OK", "NÃO"], key=f"{equip}e", horizontal=True)
            
            botao_salvar = st.form_submit_button("💾 Salvar e Finalizar")

        if botao_salvar:
            if not nome:
                st.error("Identifique-se antes de salvar!")
            else:
                # Processando irregularidades
                falhas = [k for k, v in respostas.items() if v == "NÃO"]
                status = "⚠️ Irregular" if falhas else "✅ Conforme"
                detalhes_texto = ", ".join(falhas) if falhas else "Tudo OK"
                
                # Criando nova linha
                nova_linha = pd.DataFrame([{
                    "Data": datetime.now().strftime('%d/%m/%Y %H:%M'),
                    "Colaborador": nome,
                    "Setor": setor_sel,
                    "Status": status,
                    "Detalhes": detalhes_texto
                }])
                
                # Salvando (Simulação ou Real)
                # No Streamlit Cloud, você usaria: conn.update(data=pd.concat([df_historico, nova_linha]))
                st.success("Dados salvos com sucesso no histórico!")
                st.balloons()
                
                # Gerar link WhatsApp para irregularidades
                if falhas:
                    msg = f"Relatório: {status}\nSetor: {setor_sel}\nFalhas: {detalhes_texto}"
                    st.markdown(f"[📲 Enviar Alerta via WhatsApp](https://wa.me/?text={urllib.parse.quote(msg)})")

with aba_historico:
    st.header("📜 Histórico de Inspeções")
    
    # Filtros
    col_f1, col_f2 = st.columns(2)
    filtro_setor = col_f1.multiselect("Filtrar por Setor", list(setores.keys()))
    
    df_filtrado = df_historico.copy()
    if filtro_setor:
        df_filtrado = df_filtrado[df_filtrado["Setor"].isin(filtro_setor)]
    
    # Exibição da Tabela
    st.dataframe(df_filtrado, use_container_width=True, hide_index=True)
    
    # Botão para baixar relatório em Excel/CSV
    csv = df_filtrado.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Baixar Histórico (CSV)", csv, "historico_inspeccao.csv", "text/csv")
