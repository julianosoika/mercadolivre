import os
import time
import requests
import xml.etree.ElementTree as ET
from apscheduler.schedulers.blocking import BlockingScheduler

# ================= CONFIGURAÇÕES =================
EVOLUTION_URL = "https://evolution.mxbr.com.br"
EVOLUTION_APIKEY = "429683C4C977415CAAFCCE10F7D57E11"
INSTANCE_NAME = "EnjoyWeb"

GROUP_JID = "120363408931437070@g.us"
# Substitua abaixo pela sua API Key válida do Google AI Studio se desejar
GEMINI_API_KEY = "AQ.Ab8RN6JUq7JZfzkLEj82SE8vBkNlaAkrYF-boFIDVlLwPk1CuA"
TAG_AFILIADO = "julianodossssoika"

PRODUTOS_ENVIADOS = set()

# ================= 1. BUSCAR OFERTAS =================
def buscar_ofertas_mercadolivre():
    print("📡 A consultar ofertas ativas...", flush=True)
    ofertas = []

    urls_rss = [
        "https://lista.mercadolivre.com.br/rss/ofertas",
        "https://www.mercadolivre.com.br/ofertas/rss"
    ]

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }

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

# ================= 2. GERAR COPY COM GEMINI (COM FALLBACK SEGURO) =================
def criar_copy_gemini(produto):
    print(f"🤖 A gerar copy para: {produto['titulo']}...", flush=True)
    
    prompt = f"Cria uma mensagem curta de promoção para WhatsApp:\nProduto: {produto['titulo']}\nPreço: R$ {produto['preco_novo']}\nLink: {produto['link']}"
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}]
    }
    
    try:
        res = requests.post(url, json=payload, timeout=10)
        if res.status_code == 200:
            data = res.json()
            return data["candidates"][0]["content"]["parts"][0]["text"]
        else:
            print(f"⚠️ Aviso na API Gemini (Status {res.status_code}). A usar modelo de copy padrão...", flush=True)
    except Exception as e:
        print(f"⚠️ Erro ao conectar ao Gemini: {e}. A usar modelo padrão...", flush=True)

    # Template fallback caso a API key do Gemini falhe
    copy_padrao = (
        f"🚨 *PROMOÇÃO IMPERDÍVEL!* 🚨\n\n"
        f"📦 *{produto['titulo']}*\n"
        f"💥 Por apenas: *R$ {produto['preco_novo']}*\n\n"
        f"⚡ Aproveite antes que acabe!\n"
        f"👉 {produto['link']}"
    )
    return copy_padrao

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
