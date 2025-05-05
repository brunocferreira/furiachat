# app.py
"""
Streamlit UI + orquestração do agente de chat da Fúria
"""
import streamlit as st
import base64
from agents.hltv_agents import run_pantera_task
from furiachat.utils.excel_report import build_audit_excel

st.set_page_config(
    page_title="FuriaChat – Pantera-Bot", layout="centered")

with st.sidebar:
    st.header("🔑 Chaves de API")
    OPENAI_API_KEY = st.text_input("OPENAI_API_KEY", type="password")
    # MODULE_API_KEY = st.text_input( "MODULE_API_KEY", type="password")  # futuro uso

st.title("😼 =FuriaChat= 💬")

user_q = st.chat_input("Pergunte sobre a FURIA...")

if user_q:
    with st.spinner("Consultando..."):
        try:
            answer = run_pantera_task(user_q, OPENAI_API_KEY)
            # answer = {                 # mock provisório
            #     "answer": "Fala, torcedor! A próxima partida é amanhã às 15 h vs MOUZ.",
            #     "usd_cost": 0.00023,
            #     "total_tokens": 57,
            # }

            st.info(
                f"Custo da tarefa: **US$ {answer['usd_cost']:.6f}** " f"({answer['total_tokens']} tokens)")

        except Exception as e:
            st.error(f"Erro: {e}")

    st.chat_message("assistant").markdown(answer["answer"])
