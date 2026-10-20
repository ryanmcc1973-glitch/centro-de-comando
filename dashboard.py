import streamlit as st
import pandas as pd
import time
import requests
import os
from datetime import datetime

# ==========================================
# CONFIGURAÇÃO DA PÁGINA (Visual)
# ==========================================
st.set_page_config(page_title="Painel de Trades", layout="wide", page_icon="📈")

st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: white; }
    .trade-card { background-color: #1e1e1e; padding: 20px; border-radius: 12px; border-left: 6px solid #00ff00; margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }
    .trade-card-short { border-left: 6px solid #ff4b4b; }
    .title { font-size: 22px; font-weight: bold; margin-bottom: 5px; }
    .pnl { font-size: 24px; font-weight: bold; color: #00ff00; }
    .pnl-negative { color: #ff4b4b; }
    .info { font-size: 14px; color: #aaaaaa; margin: 2px 0; }
    </style>
""", unsafe_allow_html=True)

st.title("📈 Meu Centro de Comando (Tempo Real)")

# ==========================================
# FUNÇÃO: PUXAR PREÇO REAL DA MEXC
# ==========================================
def obter_preco_atual(ativo):
    simbolo_mexc = ativo.replace("/", "_")
    url = f"https://contract.mexc.com/api/v1/contract/ticker?symbol={simbolo_mexc}"
    try:
        res = requests.get(url, timeout=5).json()
        if res['success']:
            return float(res['data']['lastPrice'])
    except Exception as e:
        pass
    return None

# ==========================================
# LER OS DADOS DO FIREBASE (NUVEM)
# ==========================================
def carregar_trades_firebase():
    url = "https://robos-marcello-default-rtdb.firebaseio.com/trades.json"
    try:
        res = requests.get(url, timeout=5).json()
        if res:
            # Transforma o dicionário do Firebase em uma lista
            return list(res.values())
        return []
    except Exception as e:
        st.error(f"Erro ao conectar no Firebase: {e}")
        return []

trades = carregar_trades_firebase()

# ==========================================
# CONSTRUÇÃO DOS CARDS (Frontend)
# ==========================================
if not trades:
    st.info("Nenhum trade aberto no momento. Os robôs estão vigiando o mercado.")
else:
    for trade in trades:
        # Pega o preço atual na MEXC. Se for um teste que não existe lá, ele ignora.
        preco_atual = obter_preco_atual(trade["ativo"])
        
        if preco_atual is None:
            st.warning(f"Não foi possível obter o preço de {trade['ativo']} na MEXC. (Pode ser um ativo de teste).")
            continue

        entrada = trade["entrada"]
        alvo = trade["alvo"]
        
        # Cálculo do Progresso
        if trade["direcao"] == "LONG":
            progresso = ((preco_atual - entrada) / (alvo - entrada)) * 100 if alvo > entrada else 0
            pnl_pct = ((preco_atual - entrada) / entrada) * 100
        else:
            progresso = ((entrada - preco_atual) / (entrada - alvo)) * 100 if alvo < entrada else 0
            pnl_pct = ((entrada - preco_atual) / entrada) * 100
            
        progresso_barra = max(0.0, min(100.0, progresso))
        
        card_class = "trade-card" if trade["direcao"] == "LONG" else "trade-card trade-card-short"
        emoji_seta = "🟢" if trade["direcao"] == "LONG" else "🔴"
        pnl_class = "pnl" if pnl_pct >= 0 else "pnl pnl-negative"
        
        with st.container():
            st.markdown(f'<div class="{card_class}">', unsafe_allow_html=True)
            
            col_imagem, col1, col2, col3 = st.columns([1, 3, 2, 2])
            
            with col_imagem:
                if os.path.exists(trade["imagem"]):
                    st.image(trade["imagem"], width=70)
                else:
                    st.markdown("<h1 style='text-align: center;'>🤖</h1>", unsafe_allow_html=True)
                st.markdown(f"<p style='text-align: center; font-size:12px; color:#aaa;'>{trade['robo']}</p>", unsafe_allow_html=True)

            with col1:
                st.markdown(f'<p class="title">{emoji_seta} {trade["ativo"]} ({trade["direcao"]})</p>', unsafe_allow_html=True)
                st.markdown(f'<p class="info">Entrada: {entrada}</p>', unsafe_allow_html=True)
                st.markdown(f'<p class="info">Preço Atual: {preco_atual} 🔄</p>', unsafe_allow_html=True)
                st.markdown(f'<p class="info">Alvo (TP): {alvo}</p>', unsafe_allow_html=True)
                
            with col2:
                st.markdown('<p class="info">Progresso do Alvo</p>', unsafe_allow_html=True)
                st.progress(progresso_barra / 100)
                st.write(f"{progresso:.1f}% atingido")
                
            with col3:
                st.markdown('<p class="info">Resultado (Spot)</p>', unsafe_allow_html=True)
                st.markdown(f'<p class="{pnl_class}">{pnl_pct:+.2f}%</p>', unsafe_allow_html=True)
                
            st.markdown('</div>', unsafe_allow_html=True)

st.write("---")
st.caption(f"Última atualização: {datetime.now().strftime('%H:%M:%S')} (Atualiza a cada 10s)")

# Loop de atualização
time.sleep(10)
st.rerun()