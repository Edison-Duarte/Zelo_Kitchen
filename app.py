import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import pytz
import urllib.parse
from fpdf import FPDF
import io

# --- CONFIGURAÇÕES DA PÁGINA ---
st.set_page_config(page_title="Zelo Kitchen - Inspeção", page_icon="🍳", layout="wide")

st.markdown("""
    <style>
        .main { background-color: #f9f9f9; }
        .stButton>button { border-radius: 5px; height: 3em; width: 100%; }
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
        df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
        
        # Cria a coluna de Resolução se não existir
        if "Resolução" not in df.columns:
            df["Resolução"] = ""
            
        # Guarda o índice real da planilha para podermos atualizar a linha exata depois
        df["original_index"] = df.index
            
        if not df.empty and "Data/Hora" in df.columns:
            # Conversão segura para formato de data do pandas
            df_dt = pd.to_datetime(df["Data/Hora"], dayfirst=True, errors='coerce')
            df["Data"] = df_dt.dt.strftime('%d/%m/%Y')
            df["Hora"] = df_dt.dt.strftime('%H:%M')
        else:
            df["Data"] = ""
            df["Hora"] = ""
        
        colunas_desejadas = ["Data", "Hora", "Funcionário", "Setor", "Equipamento", "Status", "Falhas", "Descrição do Problema", "Resolução", "original_index"]
        df_limpo = df[[c for c in colunas_desejadas if c in df.columns]]
        return df_limpo
    except Exception as e:
        return pd.DataFrame(columns=["Data", "Hora", "Funcionário", "Setor", "Equipamento", "Status", "Falhas", "Descrição do Problema", "Resolução", "original_index"])

# --- FUNÇÃO PARA GERAR PDF ---
def gerar_pdf(df_filtrado):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(190, 10, "Relatorio de Nao Conformidades - Zelo Kitchen", ln=True, align="C")
    pdf.set_font("Arial", "", 10)
    pdf.cell(190, 10, f"Gerado em: {obter_agora_br().strftime('%d/%m/%Y %H:%M')}", ln=True, align="C")
    pdf.ln(10)

    for i, row in df_filtrado.iterrows():
        pdf.set_font("Arial", "B", 11)
        pdf.set_fill_color(240, 240, 240)
        pdf.cell(190, 8, f"{row.get('Equipamento', 'N/A')} ({row.get('Setor', 'N/A')})", ln=True, fill=True)
        pdf.set_font("Arial", "", 10)
        desc = str(row.get('Descrição do Problema', '')).replace('\n', ' ') if row.get('Descrição do Problema') else "Nenhuma"
        resolvido = f"\nSolucionado em: {row.get('Resolução')}" if pd.notna(row.get('Resolução')) and row.get('Resolução') != "" else "\nStatus: PENDENTE"
        pdf.multi_cell(190, 7, f"Identificado em: {row.get('Data', '')} {row.get('Hora', '')}\nInspetor: {row.get('Funcionário', '')}\nFalha: {row.get('Falhas', '')}\nDescricao: {desc}{resolvido}")
        pdf.ln(5)
    return pdf.output(dest='S').encode('latin-1')

# --- ESTRUTURA DO CHECKLIST ---
setores_lista = ["Espaço Café", "Cozinha", "Mirante", "Refeitório"]
itens_setores = {
    "Espaço Café": ["Estufa quente", "Estufa fria", "Geladeiras balcão", "Frigobares", "Máquina de café expresso"],
    "Cozinha": ["Geladeiras Bacio di Latte", "Geladeiras Resfriados", "Câmaras Frias", "Freezers Horizontais", "Fornos", "Fogões", "Fritadeiras", "Chapas", "Geladeiras Balcões", "Coifas", "Pista Fria"],
    "Mirante": ["Freezer Sorvete Dona Mazza", "Adega Vinhos", "Geladeiras", "Geladeiras Balcões", "Lava Louças", "Coifas", "Pista Fria", "Elevador Monta Carga", "Freezer Horizontal", "Churrasqueira", "Forno a Lenha"],
    "Refeitório": ["Lava Louças", "Geladeira Resfriados", "Rechaud"]
}

st.title("🍳 Sistema de Inspeção Zelo Kitchen")
tab1, tab2 = st.tabs(["📝 Nova Inspeção", "📜 Painel de Pendências & Histórico"])

# --- ABA 1: NOVA INSPEÇÃO ---
with tab1:
    if 'sucesso' in st.session_state and st.session_state.sucesso:
        st.success("✅ Inspeção salva com sucesso na planilha!")
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
                    
                    detalhes_obs = ""
                    if any(x == "NÃO" for x in [h, f, e]):
                        detalhes_obs = st.text_area(f"Descreva o problema:", key=f"obs_{item}")
                    
                    respostas.append({"Equipamento": item, "H": h, "F": f, "E": e, "Detalhes": detalhes_obs})

            if st.button("🚀 FINALIZAR E SALVAR", type="primary"):
                if not nome_inspetor:
                    st.error("Por favor, preencha o nome do inspetor.")
                else:
                    with st.spinner("Salvando dados..."):
                        agora = obter_agora_br().strftime("%d/%m/%Y %H:%M")
                        novas_entradas = []
                        for r in respostas:
                            f_list = [n for n, v in zip(["Higiene", "Funcionamento", "Estado"], [r["H"], r["F"], r["E"]]) if v == "NÃO"]
                            novas_entradas.append({
                                "Data/Hora": agora, "Funcionário": nome_inspetor, "Setor": setor_selecionado,
                                "Equipamento": r["Equipamento"], "Status": "❌ FALHA" if f_list else "✅ OK",
                                "Falhas": ", ".join(f_list) if f_list else "Nenhuma", "Descrição do Problema": r["Detalhes"],
                                "Resolução": ""
                            })
                        
                        try:
                            df_atual = conn.read(ttl=0)
                            df_final = pd.concat([df_atual, pd.DataFrame(novas_entradas)], ignore_index=True)
                            conn.update(data=df_final)
                            st.session_state.sucesso = True
                            st.rerun()
                        except Exception as ex:
                            if "200" in str(ex): st.session_state.sucesso = True; st.rerun()
                            else: st.error(f"Erro ao salvar: {ex}")

# --- ABA 2: HISTÓRICO & GERENCIAMENTO ---
with tab2:
    df_hist = carregar_dados()
    
    if not df_hist.empty:
        df_hist["Resolução"] = df_hist["Resolução"].fillna("").astype(str).str.strip()
        
        st.subheader("🔍 Filtros de Visualização")
        col_f1, col_f2, col_f3 = st.columns(3)
        
        tipo_visao = col_f1.radio("Exibir problemas:", ["🔴 Apenas Pendentes", "🟢 Apenas Solucionados", "📋 Todos os Registros"], horizontal=True)
        f_set = col_f2.multiselect("Setores", options=setores_lista, default=setores_lista)
        f_sta = col_f3.multiselect("Status da Inspeção", options=["✅ OK", "❌ FALHA"], default=["❌ FALHA"])

        # Filtro de datas corrigido (Tratando a remoção correta do .date())
        df_hist["dt_temp"] = pd.to_datetime(df_hist["Data"], dayfirst=True, errors='coerce').dt.date
        col_d1, col_d2 = st.columns(2)
        
        data_valida_min = df_hist["dt_temp"].dropna().min() if not df_hist["dt_temp"].dropna().empty else obter_agora_br().date()
        data_valida_max = df_hist["dt_temp"].dropna().max() if not df_hist["dt_temp"].dropna().empty else obter_agora_br().date()
        
        d_ini = col_d1.date_input("De:", value=data_valida_min)
        d_fim = col_d2.date_input("Até:", value=data_valida_max)

        mask = (df_hist["dt_temp"] >= d_ini) & (df_hist["dt_temp"] <= d_fim) & \
               (df_hist["Setor"].isin(f_set)) & (df_hist["Status"].isin(f_sta))
        
        if tipo_visao == "🔴 Apenas Pendentes":
            mask = mask & (df_hist["Resolução"] == "")
        elif tipo_visao == "🟢 Apenas Solucionados":
            mask = mask & (df_hist["Resolução"] != "")

        df_filtrado = df_hist[mask].drop(columns=["dt_temp"]).sort_values(by=["Data", "Hora"], ascending=False)

        st.markdown("---")
        
        if tipo_visao == "🔴 Apenas Pendentes" and not df_filtrado.empty:
            st.subheader("🚨 Lista de Pendências em Aberto")
            st.caption("Marque a caixinha na coluna **'Solucionar'** e clique no botão vermelho abaixo para salvar.")
            
            df_filtrado.insert(0, "Solucionar", False)
            
            df_editado = st.data_editor(
                df_filtrado,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Solucionar": st.column_config.CheckboxColumn("Solucionar", default=False),
                    "Descrição do Problema": st.column_config.TextColumn("Descrição do Problema", width="large"),
                    "Resolução": None,
                    "original_index": None  # Deixa o index oculto para o usuário
                },
                disabled=["Data", "Hora", "Funcionário", "Setor", "Equipamento", "Status", "Falhas", "Descrição do Problema"]
            )
            
            if st.button("💾 CONFIRMAR SOLUÇÃO DOS ITENS MARCADOS", type="primary"):
                itens_marcados = df_editado[df_editado["Solucionar"] == True]
                
                if not itens_marcados.empty:
                    with st.spinner("Atualizando banco de dados no Google Sheets..."):
                        data_solucao = obter_agora_br().strftime("%d/%m/%Y %H:%M")
                        
                        # Carrega os dados brutos oficiais direto da planilha
                        df_original_sheets = conn.read(ttl=0)
                        if "Resolução" not in df_original_sheets.columns:
                            df_original_sheets["Resolução"] = ""
                        
                        # Aplica a alteração usando o índice mapeado absoluto (Infalível e limpo)
                        for idx, row in itens_marcados.iterrows():
                            idx_planilha = int(row["original_index"])
                            df_original_sheets.loc[idx_planilha, "Resolução"] = f"Solucionado em {data_solucao}"
                        
                        # Remove possíveis colunas fantasmas geradas localmente antes do push
                        df_original_sheets = df_original_sheets.loc[:, ~df_original_sheets.columns.str.contains('^Unnamed')]
                        if "original_index" in df_original_sheets.columns:
                            df_original_sheets = df_original_sheets.drop(columns=["original_index"])
                        
                        conn.update(data=df_original_sheets)
                        st.success("🎉 Itens atualizados com sucesso! A lista de pendências foi atualizada.")
                        st.rerun()
                else:
                    st.warning("Nenhum item foi selecionado. Clique no quadradinho da coluna 'Solucionar' primeiro.")
                    
        else:
            st.subheader("📋 Registros Filtrados")
            st.dataframe(
                df_filtrado,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Descrição do Problema": st.column_config.TextColumn("Descrição do Problema", width="large"),
                    "Resolução": st.column_config.TextColumn("Histórico de Resolução", width="medium"),
                    "original_index": None
                }
            )

        # --- SEÇÃO DE RELATÓRIO DINÂMICO ---
        st.divider()
        st.subheader("📊 Enviar Relatório das Não Conformidades Filtradas")
        st.info("💡 **Aviso:** O relatório enviado será baseado exclusivamente no conteúdo **filtrado** na tabela acima.")
        
        if not df_filtrado.empty:
            df_enviar = df_filtrado.drop(columns=["Solucionar"]) if "Solucionar" in df_filtrado.columns else df_filtrado
            if "original_index" in df_enviar.columns:
                df_enviar = df_enviar.drop(columns=["original_index"])
            
            texto_rel = f"*RELATÓRIO ZELO KITCHEN - {obter_agora_br().strftime('%d/%m/%Y')}*\n"
            texto_rel += f"Filtro applied: {tipo_visao}\n\n"
            
            for _, row in df_enviar.iterrows():
                status_res = f"\n✅ {row['Resolução']}" if row['Resolução'] != "" else "\n🔴 Status: Pendente de manutenção"
                texto_rel += f"⚠️ *{row['Equipamento']}* ({row['Setor']})\nFalha: {row['Falhas']}\nObs: {row['Descrição do Problema']}{status_res}\n---\n"
            
            col_rel1, col_rel2, col_rel3 = st.columns(3)
            col_rel1.link_button("🟢 WhatsApp", f"https://wa.me/?text={urllib.parse.quote(texto_rel)}", use_container_width=True)
            col_rel2.link_button("📧 E-mail", f"mailto:?subject=Relatorio_Zelo_Kitchen&body={urllib.parse.quote(texto_rel)}", use_container_width=True)
            col_rel3.download_button("📥 PDF", gerar_pdf(df_enviar), f"Relatorio_{obter_agora_br().strftime('%Y%m%d')}.pdf", "application/pdf", use_container_width=True)
        else:
            st.warning("Não há falhas na lista atual para gerar relatórios.")
    else:
        st.info("Nenhum registro encontrado.")
