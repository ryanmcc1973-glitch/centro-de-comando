import streamlit as st
import pandas as pd
import time
import requests
import os
from datetime import datetime

# ==========================================
# CONFIGURAÇÃO DA PÁGINA (Visual Dark/Neon)
# ==========================================
st.set_page_config(page_title="Alpha Terminal", layout="wide", page_icon="👾")

# CSS Customizado para deixar o painel com cara de "Terminal de Trading"
st.markdown("""
    <style>
    /* Fundo geral */
    .stApp {
        background-color: #050505;
        color: #00ffcc;
        font-family: 'Courier New', Courier, monospace;
    }
    
    /* Header */
    h1 {
        color: #00ffcc;
        text-align: center;
        text-shadow: 0 0 10px #00ffcc;
        border-bottom: 2px solid #00ffcc;
        padding-bottom: 10px;
    }
    
    /* Cards */
    .trade-card {
        background: linear-gradient(145deg, #0a0a0a, #111111);
        padding: 20px;
        border-radius: 15px;
        border: 1px solid #333;
        border-left: 8px solid #00ffcc; /* Verde Neon para Long */
        margin-bottom: 25px;
        box-shadow: 0 0 15px rgba(0, 255, 204, 0.1);
        transition: 0.3s;
    }
    .trade-card:hover {
        box-shadow: 0 0 25px rgba(0, 255, 204, 0.4);
        transform: translateY(-2px);
    }
    
    /* Card Short (Vermelho Neon) */
    .trade-card-short {
        border-left: 8px solid #ff0055;
        box-shadow: 0 0 15px rgba(255, 0, 85, 0.1);
    }
    .trade-card-short:hover {
        box-shadow: 0 0 25px rgba(255, 0, 85, 0.4);
    }

    /* Textos */
    .title {
        font-size: 26px;
        font-weight: bold;
        color: #ffffff;
        margin-bottom: 10px;
    }
    .pnl {
        font-size: 28px;
        font-weight: bold;
        color: #00ffcc;
        text-shadow: 0 0 8px #00ffcc;
    }
    .pnl-negative {
        color: #ff0055;
        text-shadow: 0 0 8px #ff0055;
    }
    .info {
        font-size: 16px;
        color: #aaaaaa;
        margin: 5px 0;
    }
    .info-value {
        color: #ffffff;
        font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)

st.title("👾 ALPHA TERMINAL")

# ==========================================
# FUNÇÕES (Firebase e MEXC)
# ==========================================
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
            # Pega a lista de valores do Firebase
            lista_trades = list(res.values())
            # OPÇÃO: Descomente a linha abaixo se quiser mostrar APENAS os trades mais recentes
            # lista_trades = lista_trades[-10:] 
            return lista_trades
        return []
    except Exception as e:
        st.error(f"Erro de conexão com o Banco: {e}")
        return []

# ==========================================
# LÓGICA PRINCIPAL
# ==========================================
trades = carregar_trades_firebase()

if not trades:
    st.markdown("<h3 style='text-align:center; color:#666;'>Nenhum sinal ativo no momento. Aguardando o Alpha...</h3>", unsafe_allow_html=True)
else:
    # Ordena para os mais recentes primeiro (se houver timestamp, ou apenas inverte a lista)
    trades.reverse()
    
    for trade in trades:
        ativo = trade.get("ativo", "").replace("_", "/")
        if not ativo: continue

        preco_atual = obter_preco_atual(ativo)
        
        # Se a MEXC não tiver o preço (ex: ação AAPLSTOCK), usa o preço da entrada para não zerar o card
        if preco_atual is None:
            preco_atual = float(trade.get("entrada", 0))
            preco_real = False
        else:
            preco_real = True

        entrada = float(trade.get("entrada", 0))
        alvo = float(trade.get("alvo", 0))
        direcao = trade.get("direcao", "LONG")

        if entrada == 0 or alvo == 0: continue

        # Cálculos
        if direcao == "LONG":
            progresso = ((preco_atual - entrada) / (alvo - entrada)) * 100 if alvo > entrada else 0
            pnl_pct = ((preco_atual - entrada) / entrada) * 100
        else:
            progresso = ((entrada - preco_atual) / (entrada - alvo)) * 100 if alvo < entrada else 0
            pnl_pct = ((entrada - preco_atual) / entrada) * 100
            
        progresso_barra = max(0.0, min(100.0, progresso))
        
        # Visual
        card_class = "trade-card" if direcao == "LONG" else "trade-card trade-card-short"
        emoji = "🟢" if direcao == "LONG" else "🔴"
        pnl_class = "pnl" if pnl_pct >= 0 else "pnl pnl-negative"
        preco_icon = "⚡" if preco_real else "⚠️(Preço Mock)"
        
        # Renderiza o Card
        with st.container():
            st.markdown(f'<div class="{card_class}">', unsafe_allow_html=True)
            col1, col2, col3 = st.columns([2, 1.5, 1.5])
            
            with col1:
                st.markdown(f'<p class="title">{emoji} {ativo} ({direcao})</p>', unsafe_allow_html=True)
                st.markdown(f'<p class="info">Entrada: <span class="info-value">{entrada}</span></p>', unsafe_allow_html=True)
                st.markdown(f'<p class="info">Preço Atual: <span class="info-value">{preco_atual:.4f} {preco_icon}</span></p>', unsafe_allow_html=True)
                st.markdown(f'<p class="info">Alvo: <span class="info-value">{alvo}</span></p>', unsafe_allow_html=True)
                
            with col2:
                st.markdown('<p class="info">Progresso do Alvo</p>', unsafe_allow_html=True)
                st.progress(progresso_barra / 100)
                st.write(f"{progresso:.1f}%")
                
            with col3:
                st.markdown('<p class="info">PnL Parcial</p>', unsafe_allow_html=True)
                st.markdown(f'<p class="{pnl_class}">{pnl_pct:+.2f}%</p>', unsafe_allow_html=True)
                
            st.markdown('</div>', unsafe_allow_html=True)

st.write("---")
st.caption(f"Alpha Terminal v2.0 | Atualiza a cada 10s | Última leitura: {datetime.now().strftime('%H:%M:%S')}")

time.sleep(10)
st.rerun()
