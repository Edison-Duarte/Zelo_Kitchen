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

# CSS para interface geral e botões
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
        # 1. Limpeza: Remove colunas "fantasmas" (Unnamed)
        df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
        
        # Cria a coluna de Resolução se ela não existir na planilha
        if "Resolução" not in df.columns:
            df["Resolução"] = ""
            
        # Guarda o índice original da planilha para garantir atualizações sem erros
        df["original_index"] = df.index
        
        if not df.empty and "Data/Hora" in df.columns:
            # Garante que a data seja lida corretamente
            df_dt = pd.to_datetime(df["Data/Hora"], dayfirst=True, errors='coerce')
            
            # 2. Otimização: Cria colunas separadas no padrão Brasileiro
            df["Data"] = df_dt.dt.strftime('%d/%m/%Y')
            df["Hora"] = df_dt.dt.strftime('%H:%M')
        else:
            df["Data"] = ""
            df["Hora"] = ""
        
        # 3. Otimização: Seleciona apenas as colunas únicas e corretas
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

# --- ABA 2: HISTÓRICO CORRIGIDO COM QUEBRA DE LINHA E FLUXO DE RESOLUÇÃO ---
with tab2:
    st.subheader("📜 Histórico de Registros")
    df_hist = carregar_dados()
    
    if not df_hist.empty:
        df_hist["Resolução"] = df_hist["Resolução"].fillna("").astype(str).str.strip()
        
        with st.expander("🔍 Filtros de Busca", expanded=True):
            col_v1, col_v2, col_v3 = st.columns(3)
            
            # Filtro essencial para separar Pendentes de Solucionados
            tipo_visao = col_v1.radio("Visualização:", ["🔴 Apenas Pendentes", "🟢 Apenas Solucionados", "📋 Todos os Registros"], horizontal=True)
            f_set = col_v2.multiselect("Setores", options=setores_lista, default=setores_lista)
            f_sta = col_v3.multiselect("Status", options=["✅ OK", "❌ FALHA"], default=["❌ FALHA"])

            col_d1, col_d2 = st.columns(2)
            df_hist["dt_temp"] = pd.to_datetime(df_hist["Data"], dayfirst=True, errors='coerce').dt.date
            data_min = df_hist["dt_temp"].dropna().min() if not df_hist["dt_temp"].dropna().empty else obter_agora_br().date()
            data_max = df_hist["dt_temp"].dropna().max() if not df_hist["dt_temp"].dropna().empty else obter_agora_br().date()
            
            d_ini = col_d1.date_input("Início", value=data_min)
            d_fim = col_d2.date_input("Fim", value=data_max)

        # Aplicação estrutural dos filtros
        mask = (df_hist["dt_temp"] >= d_ini) & (df_hist["dt_temp"] <= d_fim) & \
               (df_hist["Setor"].isin(f_set)) & (df_hist["Status"].isin(f_sta))
        
        # Filtro condicional baseado na Resolução do problema
        if tipo_visao == "🔴 Apenas Pendentes":
            mask = mask & (df_hist["Resolução"] == "")
        elif tipo_visao == "🟢 Apenas Solucionados":
            mask = mask & (df_hist["Resolução"] != "")
        
        df_filtrado = df_hist[mask].drop(columns=["dt_temp"]).sort_values(by=["Data", "Hora"], ascending=False)
        
        # Captura se o usuário clicou em algum botão de resolver via parâmetro de URL interno do Streamlit
        query_params = st.query_params
        if "resolver_id" in query_params:
            id_para_resolver = int(query_params["resolver_id"])
            with st.spinner("Registrando solução da não conformidade..."):
                data_solucao = obter_agora_br().strftime("%d/%m/%Y %H:%M")
                
                # Carrega o Sheets bruto
                df_original_sheets = conn.read(ttl=0)
                df_original_sheets = df_original_sheets.loc[:, ~df_original_sheets.columns.str.contains('^Unnamed')]
                
                if "Resolução" not in df_original_sheets.columns:
                    df_original_sheets["Resolução"] = ""
                
                # Registra o encerramento na linha exata mapeada
                df_original_sheets.loc[id_para_resolver, "Resolução"] = f"Solucionado em {data_solucao}"
                
                conn.update(data=df_original_sheets)
                st.query_params.clear() # Limpa a URL
                st.success("🎉 Problema marcado como solucionado!")
                st.rerun()

        # TABELA HTML EM INLINE COM QUEBRA DE LINHA FORÇADA E BOTÃO INTEGRADO
        if not df_filtrado.empty:
            # Determina as colunas no cabeçalho baseadas na visão selecionada
            coluna_acao_header = "<th>Ação</th>" if tipo_visao == "🔴 Apenas Pendentes" else "<th>Histórico de Resolução</th>"
            
            html_tabela = f"""
            <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.2.3/dist/css/bootstrap.min.css">
            <style>
                body {{ background-color: transparent !important; font-family: sans-serif; }}
                th {{ background-color: #2c3e50 !important; color: white !important; font-size: 14px; position: sticky; top: 0; }}
                td {{ font-size: 13px; vertical-align: middle; word-break: break-word !important; white-space: normal !important; }}
                .table-container {{ max-height: 450px; overflow-y: auto; border: 1px solid #dee2e6; border-radius: 4px; }}
                .btn-solucionar {{ background-color: #2ecc71; color: white; border: none; padding: 4px 8px; font-size: 11px; border-radius: 3px; cursor: pointer; text-decoration: none; font-weight: bold; }}
                .btn-solucionar:hover {{ background-color: #27ae60; color: white; }}
            </style>
            <div class="table-container">
                <table class="table table-striped table-hover m-0">
                    <thead>
                        <tr>
                            <th>Data</th><th>Hora</th><th>Funcionário</th><th>Setor</th><th>Equipamento</th><th>Status</th><th>Falhas</th><th>Descrição do Problema</th>{coluna_acao_header}
                        </tr>
                    </thead>
                    <tbody>
            """
            for _, row in df_filtrado.iterrows():
                desc_p = row.get('Descrição do Problema', '')
                desc_p = str(desc_p) if pd.notna(desc_p) else ""
                idx_real = row.get('original_index')
                resolucao_texto = row.get('Resolução', '')
                
                # Monta a última célula dinamicamente
                if tipo_visao == "🔴 Apenas Pendentes":
                    coluna_acao_td = f'<td><a href="?resolver_id={idx_real}" target="_self" class="btn-solucionar">✔️ Solucionado</a></td>'
                elif tipo_visao == "🟢 Apenas Solucionados":
                    coluna_acao_td = f'<td class="text-success fw-bold">{resolucao_texto}</td>'
                else:
                    # Na visão de "Todos os registros", mostra o texto se houver, ou "Pendente"
                    if resolucao_texto != "":
                        coluna_acao_td = f'<td class="text-success fw-bold">{resolucao_texto}</td>'
                    else:
                        coluna_acao_td = f'<td class="text-danger fw-bold">🔴 Pendente</td>'
                
                html_tabela += f"""
                        <tr>
                            <td>{row.get('Data','')}</td>
                            <td>{row.get('Hora','')}</td>
                            <td>{row.get('Funcionário','')}</td>
                            <td>{row.get('Setor','')}</td>
                            <td>{row.get('Equipamento','')}</td>
                            <td>{row.get('Status','')}</td>
                            <td>{row.get('Falhas','')}</td>
                            <td style="min-width: 250px; max-width: 400px;">{desc_p}</td>
                            {coluna_acao_td}
                        </tr>
                """
            html_tabela += "</tbody></table></div>"
            
            # Injeta o HTML nativo
            st.components.v1.html(html_tabela, height=460, scrolling=False)
        else:
            st.write("Nenhum dado corresponde aos filtros selecionados.")

        # --- SEÇÃO DE RELATÓRIO ---
        st.divider()
        st.subheader("📊 Enviar Relatório de Não Conformidades")
        st.info("💡 **Aviso:** O relatório enviado será baseado exclusivamente no conteúdo **filtrado** na tabela acima.")
        
        if not df_filtrado.empty:
            texto_rel = f"*RELATÓRIO ZELO KITCHEN - {obter_agora_br().strftime('%d/%m/%Y')}*\n"
            texto_rel += f"Filtro aplicado: {tipo_visao}\n\n"
            
            for _, row in df_filtrado.iterrows():
                status_res = f"\n✅ {row['Resolução']}" if row['Resolução'] != "" else "\n🔴 Status: Pendente de manutenção"
                texto_rel += f"⚠️ *{row['Equipamento']}* ({row['Setor']})\nFalha: {row['Falhas']}\nObs: {row['Descrição do Problema']}{status_res}\n---\n"
            
            col_rel1, col_rel2, col_rel3 = st.columns(3)
            col_rel1.link_button("🟢 WhatsApp", f"https://wa.me/?text={urllib.parse.quote(texto_rel)}", use_container_width=True)
            col_rel2.link_button("📧 E-mail", f"mailto:?subject=Relatorio&body={urllib.parse.quote(texto_rel)}", use_container_width=True)
            col_rel3.download_button("📥 PDF", gerar_pdf(df_filtrado), f"Relatorio_{obter_agora_br().strftime('%Y%m%d')}.pdf", "application/pdf", use_container_width=True)
        else:
            st.warning("Não há falhas para exibir com os filtros atuais.")
    else:
        st.info("Nenhum registro encontrado.")
