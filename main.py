import os
import time
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
from apscheduler.schedulers.blocking import BlockingScheduler

# ================= CONFIGURAÇÕES =================
EVOLUTION_URL = "https://evolution.mxbr.com.br"
EVOLUTION_APIKEY = "429683C4C977415CAAFCCE10F7D57E11"
INSTANCE_NAME = "EnjoyWeb"

GROUP_JID = "120363408931437070@g.us"
GEMINI_API_KEY = "AQ.Ab8RN6JUq7JZfzkLEj82SE8vBkNlaAkrYF-boFIDVlLwPk1CuA"
TAG_AFILIADO = "julianodossssoika"

genai.configure(api_key=GEMINI_API_KEY)
PRODUTOS_ENVIADOS = set()

# ================= 1. BUSCAR OFERTAS =================
def buscar_ofertas_mercadolivre():
    url = "https://www.mercadolivre.com.br/ofertas"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
    }
    
    print("📡 A fazer requisição à página do Mercado Livre...", flush=True)
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        print(f"❌ Erro HTTP {response.status_code} ao aceder às ofertas", flush=True)
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    
    # Busca por links de produtos de forma mais ampla
    cards = soup.select(".promotion-item") or soup.select(".ui-search-result") or soup.find_all("li", class_="promotion-item")
    print(f"🔍 Elementos de promoção encontrados na página: {len(cards)}", flush=True)
    
    ofertas = []

    for card in cards:
        try:
            titulo_elem = card.select_one(".promotion-item__title") or card.select_one(".ui-search-item__title")
            link_elem = card.select_one("a.promotion-item__link-link") or card.select_one("a.ui-search-link")
            preco_novo_elem = card.select_one(".promotion-item__price span") or card.select_one(".price-tag-fraction")
            preco_antigo_elem = card.select_one(".promotion-item__old-price")
            desconto_elem = card.select_one(".promotion-item__discount")

            if titulo_elem and link_elem and preco_novo_elem:
                titulo = titulo_elem.text.strip()
                link_original = link_elem["href"].split("#")[0]
                preco_novo = preco_novo_elem.text.strip()
                preco_antigo = preco_antigo_elem.text.strip() if preco_antigo_elem else ""
                desconto = desconto_elem.text.strip() if desconto_elem else ""

                ofertas.append({
                    "titulo": titulo,
                    "link": link_original,
                    "preco_novo": preco_novo,
                    "preco_antigo": preco_antigo,
                    "desconto": desconto
                })
        except Exception as e:
            continue

    print(f"✅ Total de ofertas extraídas com sucesso: {len(ofertas)}", flush=True)
    return ofertas

# ================= 2. GERAR COPY COM GEMINI =================
def criar_copy_gemini(produto):
    print(f"🤖 A gerar copy persuasiva via Gemini para: {produto['titulo']}...", flush=True)
    prompt = f"""
    És um especialista em marketing de afiliados para grupos de promoções no WhatsApp.
    Cria uma mensagem curta, chamativa e altamente persuasiva para o produto abaixo.

    Produto: {produto['titulo']}
    Preço Antigo: {produto['preco_antigo']}
    Preço Promocional: R$ {produto['preco_novo']}
    Desconto: {produto['desconto']}
    Link original: {produto['link']}

    Regras OBRIGATÓRIAS:
    - Usa emojis chamativos no início (ex: 🚨, 🔥, ⚡).
    - Destaque o valor da economia/desconto.
    - Cria um senso de urgência leve.
    - Mantém o texto limpo, sem exageros de caracteres.
    - Na última linha, inclui o link do produto.
    """
    
    model = genai.GenerativeModel('gemini-1.5-flash')
    response = model.generate_content(prompt)
    return response.text

# ================= 3. ENVIAR PARA A EVOLUTION API =================
def enviar_whatsapp(texto_mensagem):
    print("📲 A enviar mensagem via Evolution API...", flush=True)
    endpoint = f"{EVOLUTION_URL}/message/sendText/{INSTANCE_NAME}"
    headers = {
        "apikey": EVOLUTION_APIKEY,
        "Content-Type": "application/json"
    }
    payload = {
        "number": GROUP_JID,
        "text": texto_mensagem,
        "delay": 1200
    }
    
    res = requests.post(endpoint, json=payload, headers=headers)
    print(f"📊 Resposta Evolution API: Status {res.status_code} - {res.text[:100]}", flush=True)
    return res.status_code in [200, 201]

# ================= EXECUÇÃO DO AGENTE =================
def rodar_agente():
    print("\n🔎 Agente a procurar novas ofertas no Mercado Livre...", flush=True)
    ofertas = buscar_ofertas_mercadolivre()
    
    if not ofertas:
        print("⚠️ Nenhuma oferta válida encontrada nesta verificação.", flush=True)
        return

    for produto in ofertas:
        if produto['link'] in PRODUTOS_ENVIADOS:
            continue
        
        print(f"📦 Nova oferta selecionada: {produto['titulo']}", flush=True)
        
        try:
            copy = criar_copy_gemini(produto)
            sucesso = enviar_whatsapp(copy)
            
            if sucesso:
                print("✅ Oferta enviada com sucesso para o grupo de WhatsApp!", flush=True)
                PRODUTOS_ENVIADOS.add(produto['link'])
                break
            else:
                print("❌ Falha no envio através da Evolution API.", flush=True)
        except Exception as err:
            print(f"❌ Erro durante o processamento do produto: {err}", flush=True)

if __name__ == "__main__":
    print("🚀 Agente de ofertas iniciado!", flush=True)
    
    # Executa imediatamente no arranque
    rodar_agente()
    
    scheduler = BlockingScheduler()
    scheduler.add_job(rodar_agente, 'interval', minutes=30)
    
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        pass
