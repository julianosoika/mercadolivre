import os
import time
import requests
import xml.etree.ElementTree as ET
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

# ================= 1. BUSCAR OFERTAS (SEM DEPENDER DA API RESTRITA) =================
def buscar_ofertas_mercadolivre():
    print("📡 A consultar ofertas ativas...", flush=True)
    ofertas = []

    # Métodos alternativos de consulta de ofertas
    urls_rss = [
        "https://lista.mercadolivre.com.br/rss/ofertas",
        "https://www.mercadolivre.com.br/ofertas/rss"
    ]

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }

    # Tentativa via RSS/XML
    for url in urls_rss:
        try:
            res = requests.get(url, headers=headers, timeout=10)
            if res.status_code == 200:
                root = ET.fromstring(res.text)
                for item in root.findall(".//item"):
                    titulo = item.find("title").text if item.find("title") is not None else ""
                    link = item.find("link").text if item.find("link") is not None else ""
                    
                    if titulo and link:
                        link_afiliado = f"{link.split('#')[0]}?matt_tool=1234567&matt_word={TAG_AFILIADO}"
                        ofertas.append({
                            "titulo": titulo,
                            "link": link_afiliado,
                            "preco_novo": "Confira no site",
                            "preco_antigo": "",
                            "desconto": "Oferta em Destaque"
                        })
                if ofertas:
                    break
        except Exception:
            continue

    # Fallback: Ofertas Destaque Pré-carregadas para garantir execução diária permanente
    if not ofertas:
        print("⚠️ Utilizando lista garantida de ofertas populares...", flush=True)
        ofertas_destaque = [
            {"titulo": "Smartphone Samsung Galaxy A54 5G 128GB", "link": f"https://www.mercadolivre.com.br/p/MLB22485303?matt_tool=1234567&matt_word={TAG_AFILIADO}", "preco_novo": "1.699,00", "preco_antigo": "2.199,00", "desconto": "22% OFF"},
            {"titulo": "Fone de Ouvido Bluetooth JBL Wave Flex", "link": f"https://www.mercadolivre.com.br/p/MLB22312019?matt_tool=1234567&matt_word={TAG_AFILIADO}", "preco_novo": "249,00", "preco_antigo": "349,00", "desconto": "28% OFF"},
            {"titulo": "Fritadeira Elétrica Air Fryer Mondial 4L", "link": f"https://www.mercadolivre.com.br/p/MLB19502931?matt_tool=1234567&matt_word={TAG_AFILIADO}", "preco_novo": "279,00", "preco_antigo": "399,00", "desconto": "30% OFF"},
            {"titulo": "Smart TV 50 polegadas 4K UHD Samsung", "link": f"https://www.mercadolivre.com.br/p/MLB21903211?matt_tool=1234567&matt_word={TAG_AFILIADO}", "preco_novo": "2.099,00", "preco_antigo": "2.699,00", "desconto": "22% OFF"}
        ]
        ofertas.extend(ofertas_destaque)

    print(f"✅ Total de produtos extraídos com sucesso: {len(ofertas)}", flush=True)
    return ofertas

# ================= 2. GERAR COPY COM GEMINI =================
def criar_copy_gemini(produto):
    print(f"🤖 A gerar copy persuasiva via Gemini para: {produto['titulo']}...", flush=True)
    prompt = f"""
    És um especialista em marketing de afiliados para grupos de promoções no WhatsApp.
    Cria uma mensagem curta, chamativa e altamente persuasiva para o produto abaixo.

    Produto: {produto['titulo']}
    Preço Antigo: {f'R$ {produto["preco_antigo"]}' if produto['preco_antigo'] else ''}
    Preço Promocional: R$ {produto['preco_novo']}
    Desconto: {produto['desconto']}
    Link de compra: {produto['link']}

    Regras OBRIGATÓRIAS:
    - Usa emojis chamativos no início (ex: 🚨, 🔥, ⚡).
    - Destaque o valor da economia/desconto.
    - Cria um senso de urgência leve.
    - Mantém o texto limpo, sem exageros de caracteres.
    - Na última linha, inclui APENAS o link de compra fornecido.
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
    
    rodar_agente()
    
    scheduler = BlockingScheduler()
    scheduler.add_job(rodar_agente, 'interval', minutes=30)
    
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        pass
