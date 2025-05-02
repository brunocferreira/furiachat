# app.py
"""
Streamlit UI + orquestração do agente de localidade                               ✓
"""
import streamlit as st                                         # st.text_input docs :contentReference[oaicite:8]{index=8}
import base64
from agents.location_agent import run_location_task
from leadprofile.utils.excel_report import build_audit_excel

st.set_page_config(
    page_title="Lead Profile Hunter – Localidade", layout="centered")

with st.sidebar:
    st.header("🔑 Chaves de API")
    OPENAI_API_KEY = st.text_input("OPENAI_API_KEY", type="password")
    MODULE_API_KEY = st.text_input(
        "MODULE_API_KEY", type="password")  # futuro uso

st.title("🎯 Identificador de Localidade (DDD)")

name = st.text_input("Nome do lead")
phone = st.text_input("Telefone do lead (inclua DDD, apenas números)")

if st.button("➜ Buscar Localidade", disabled=not all([name, phone, OPENAI_API_KEY])):
    with st.spinner("Consultando agente..."):
        try:
            result = run_location_task(name, phone, OPENAI_API_KEY)

            st.info(
                f"Custo da tarefa: **US$ {result['usd_cost']:.6f}** "
                f"({result['total_tokens']} tokens)"
            )

            st.markdown(result["markdown"], unsafe_allow_html=False)

            # Download Markdown
            b64_md = base64.b64encode(result["markdown"].encode()).decode()
            href_md = (
                f'<a href="data:text/markdown;base64,{b64_md}" '
                f'download="relatorio_{name}_{phone}.md">📄 Baixar Relatório de {name} de telefone {phone}</a>'
            )
            st.markdown(href_md, unsafe_allow_html=True)

            # Download Excel
            excel_buffer = build_audit_excel(
                name, phone, result["ddd"], result["data"]
            )

            st.download_button(
                label="📊 Baixar Auditoria (.xlsx)",
                data=excel_buffer,
                file_name=f"Auditoria_da_busca_{name}_{phone}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        except Exception as e:
            st.error(f"Erro: {e}")
