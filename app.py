import streamlit as st
import pandas as pd
from datetime import datetime
import urllib.parse

# Configuração da página
st.set_page_config(page_title="Checklist Operacional", page_icon="🍳", layout="centered")

# --- INICIALIZAÇÃO DA MEMÓRIA TEMPORÁRIA ---
if 'historico' not in st.session_state:
    # Criamos um DataFrame vazio na primeira vez que o app roda
    st.session_state.historico = pd.DataFrame(columns=["Data", "Colaborador", "Setor", "Status", "Irregularidades"])

# --- DADOS ---
setores = {
    "Espaço Café": ["Estufa quente", "Estufa fria", "Geladeiras balcão", "Frigobares", "Máquina de café expresso"],
    "Cozinha": ["Geladeiras Bacio di Latte", "Geladeiras Resfriados", "Câmaras Frias", "Freezers Horizontais", "Fornos", "Fogões", "Fritadeiras", "Chapas", "Geladeiras Balcões", "Coifas", "Pista Fria"],
    "Mirante": ["Freezer Sorvete Dona Mazza", "Adega Vinhos", "Geladeiras", "Geladeiras Balcões", "Lava Louças", "Coifas", "Pista Fria", "Elevador Monta Carga", "Freezer Horizontal", "Churrasqueira", "Forno a Lenha"],
    "Refeitório": ["Lava Louças", "Geladeira Resfriados", "Rechaud"]
}

# --- INTERFACE ---
st.title("🍳 Sistema de Inspeção")

tab1, tab2 = st.tabs(["📝 Nova Inspeção", "📜 Histórico Temporário"])

with tab1:
    st.info("Nota: Os dados desta sessão serão perdidos se a página for atualizada (F5).")
    
    with st.container(border=True):
        col1, col2 = st.columns(2)
        nome = col1.text_input("👤 Nome do Inspetor:")
        setor_sel = col2.selectbox("📍 Setor:", ["Selecione..."] + list(setores.keys()))

    if setor_sel != "Selecione...":
        respostas = {}
        
        with st.form("form_checklist"):
            st.markdown(f"### Itens de: {setor_sel}")
            
            for equip in setores[setor_sel]:
                st.markdown(f"**{equip}**")
                c1, c2, c3 = st.columns(3)
                # Usamos nomes curtos para caber no celular
                respostas[f"{equip}_H"] = c1.radio("Higiene", ["Conforme", "Não Conf."], key=f"{equip}_h", horizontal=True)
                respostas[f"{equip}_F"] = c2.radio("Funcion.", ["Conforme", "Não Conf."], key=f"{equip}_f", horizontal=True)
                respostas[f"{equip}_E"] = c3.radio("Estado", ["Conforme", "Não Conf."], key=f"{equip}_e", horizontal=True)
                st.divider()
            
            submit = st.form_submit_button("🚀 Finalizar Inspeção")

        if submit:
            if not nome or nome.strip() == "":
                st.error("Por favor, preencha o nome do colaborador.")
            else:
                # 1. Identificar falhas
                falhas = []
                for chave, valor in respostas.items():
                    if valor == "Não Conf.":
                        # Limpa o nome da chave para o relatório
                        item_nome = chave.rsplit('_', 1)[0]
                        falhas.append(item_nome)
                
                # Remover duplicatas de itens que falharam em mais de um critério
                falhas_unicas = list(set(falhas))
                status = "❌ Irregular" if falhas_unicas else "✅ Conforme"
                detalhes = ", ".join(falhas_unicas) if falhas_unicas else "Nenhuma"

                # 2. Salvar no Histórico da Sessão
                nova_entrada = pd.DataFrame([{
                    "Data": datetime.now().strftime("%d/%m/%Y %H:%M"),
                    "Colaborador": nome,
                    "Setor": setor_sel,
                    "Status": status,
                    "Irregularidades": detalhes
                }])
                
                st.session_state.historico = pd.concat([st.session_state.historico, nova_entrada], ignore_index=True)
                
                st.success("Inspeção registrada no histórico local!")
                
                # 3. Gerar link para WhatsApp
                relatorio_zap = f"🚨 *RELATÓRIO DE INSPEÇÃO*\n\n"
                relatorio_zap += f"👤 *Inspetor:* {nome}\n"
                relatorio_zap += f"📍 *Setor:* {setor_sel}\n"
                relatorio_zap += f"📊 *Status:* {status}\n"
                if falhas_unicas:
                    relatorio_zap += f"⚠️ *Itens com falha:* {detalhes}\n"
                
                url_whatsapp = f"https://wa.me/?text={urllib.parse.quote(relatorio_zap)}"
                st.markdown(f"""
                    <a href="{url_whatsapp}" target="_blank">
                        <button style="width:100%; background-color:#25d366; color:white; border:none; padding:15px; border-radius:10px; font-weight:bold; cursor:pointer;">
                            🟢 Enviar para WhatsApp
                        </button>
                    </a>
                """, unsafe_allow_html=True)

with tab2:
    st.header("📜 Relatórios da Sessão")
    
    if st.session_state.historico.empty:
        st.write("Nenhuma inspeção realizada nesta sessão.")
    else:
        # Exibe a tabela do histórico
        st.dataframe(
            st.session_state.historico, 
            use_container_width=True, 
            hide_index=True
        )
        
        # Botão para limpar o histórico manualmente
        if st.button("🗑️ Limpar Histórico Atual"):
            st.session_state.historico = pd.DataFrame(columns=["Data", "Colaborador", "Setor", "Status", "Irregularidades"])
            st.rerun()

        # Download como CSV (caso o usuário queira salvar antes de fechar o navegador)
        csv = st.session_state.historico.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Baixar em Excel (CSV)",
            data=csv,
            file_name=f"inspecoes_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
        )
