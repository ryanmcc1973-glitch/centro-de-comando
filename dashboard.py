import streamlit as st
import pandas as pd
import time
import requests
import os
from datetime import datetime

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

# MUDANÇA AQUI PARA TESTE:
st.title("📈 TESTE NOVO - CENTRO DE COMANDO")

def obter_preco_atual(ativo):
    simbolo_mexc = ativo.replace("/", "_")
    url = f"https://contract.mexc.com/api/v1/contract/ticker?symbol={simbolo_mexc}"
    try:
        res = requests.get(url, timeout=5).json()
        if res['success']:
            return float(res['data']['lastPrice'])
    except Exception:
        pass
    return None

def carregar_trades_firebase():
    url = "https://robos-marcello-default-rtdb.firebaseio.com/trades.json"
    try:
        res = requests.get(url, timeout=5).json()
        if res:
            return list(res.values())
        return []
    except Exception as e:
        st.error(f"Erro ao conectar no Firebase: {e}")
        return []

trades = carregar_trades_firebase()

if not trades:
    st.info("Nenhum trade aberto no momento. Os robôs estão vigiando o mercado.")
else:
    for trade in trades:
        preco_atual = obter_preco_atual(trade.get("ativo", ""))
        
        if preco_atual is None:
            continue

        entrada = float(trade.get("entrada", 0))
        alvo = float(trade.get("alvo", 0))
        
        if entrada == 0 or alvo == 0:
            continue

        if trade.get("direcao") == "LONG":
            progresso = ((preco_atual - entrada) / (alvo - entrada)) * 100 if alvo > entrada else 0
            pnl_pct = ((preco_atual - entrada) / entrada) * 100
        else:
            progresso = ((entrada - preco_atual) / (entrada - alvo)) * 100 if alvo < entrada else 0
            pnl_pct = ((entrada - preco_atual) / entrada) * 100
            
        progresso_barra = max(0.0, min(100.0, progresso))
        
        card_class = "trade-card" if trade.get("direcao") == "LONG" else "trade-card trade-card-short"
        emoji_seta = "🟢" if trade.get("direcao") == "LONG" else "🔴"
        pnl_class = "pnl" if pnl_pct >= 0 else "pnl pnl-negative"
        
        with st.container():
            st.markdown(f'<div class="{card_class}">', unsafe_allow_html=True)
            
            col_imagem, col1, col2, col3 = st.columns([1, 3, 2, 2])
            
            with col_imagem:
                img_nome = trade.get("imagem", "alpha.png")
                if os.path.exists(img_nome):
                    st.image(img_nome, width=70)
                else:
                    st.markdown("<h1 style='text-align: center;'>🤖</h1>", unsafe_allow_html=True)
                st.markdown(f"<p style='text-align: center; font-size:12px; color:#aaa;'>{trade.get('robo', 'Robô')}</p>", unsafe_allow_html=True)

            with col1:
                st.markdown(f'<p class="title">{emoji_seta} {trade.get("ativo", "Ativo")} ({trade.get("direcao", "")})</p>', unsafe_allow_html=True)
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

time.sleep(10)
st.rerun()
