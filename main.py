import os
import time
import requests
import xml.etree.ElementTree as ET
from apscheduler.schedulers.blocking import BlockingScheduler

# ==================== CONFIGURAÇÕES ====================
EVOLUTION_URL = "https://evolution.mxbr.com.br"
EVOLUTION_APIKEY = "429683C4C977415CAAFCCE10F7D57E11"
INSTANCE_NAME = "EnjoyWeb"

GROUP_JID = "120363408931437070@g.us"

# Sua API Key do Gemini (AI Studio / GCP)
GEMINI_API_KEY = "AIzaSyBaqIS0hRVNkzqz93_XEloarm43Yjxj_pI"
TAG_AFILIADO = "julianodosssoika"

PRODUTOS_ENVIADOS = set()


# ==================== 1. BUSCAR OFERTAS ====================
def buscar_ofertas_mercadolivre():
    print("🔎 A consultar ofertas ativas...", flush=True)
    ofertas = []

    urls_rss = [
        "https://lista.mercadolivre.com.br/rss/ofertas",
        "https://www.mercadolivre.com.br/ofertas/rss"
    ]

    for url in urls_rss:
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                root = ET.fromstring(response.content)
                for item in root.findall('./channel/item'):
                    title = item.find('title').text if item.find('title') is not None else ""
                    link = item.find('link').text if item.find('link') is not None else ""
                    
                    if title and link:
                        # Limpa parâmetros extras e mantém a URL do produto intacta
                        link_limpo = link.split('?')[0].split('#')[0]
                        ofertas.append({
                            'titulo': title,
                            'link': link_limpo
                        })
        except Exception as e:
            print(f"⚠️ Erro ao procurar no RSS ({url}): {e}", flush=True)

    # Se o RSS estiver indisponível, utiliza lista de segurança
    if not ofertas:
        print("⚠️ Utilizando lista garantida de ofertas populares...", flush=True)
        ofertas = [
            {
                'titulo': 'Smartphone Samsung Galaxy A54 5G 128GB',
                'link': 'https://www.mercadolivre.com.br/p/MLB22485303',
                'preco': '1.699,00'
            },
            {
                'titulo': 'Fone de Ouvido Bluetooth JBL Wave Flex',
                'link': 'https://www.mercadolivre.com.br/p/MLB22912019',
                'preco': '249,00'
            }
        ]

    return ofertas


# ==================== 2. GERAR COPY COM GEMINI ====================
def gerar_copy_gemini(produto):
    titulo = produto.get('titulo', '')
    preco = produto.get('preco', '')
    link = produto.get('link', '')

    # Modelo de texto padrão (Fallback)
    copy_padrao = (
        f"🚨 *PROMOÇÃO IMPERDÍVEL!* 🚨\n\n"
        f"📦 *{titulo}*\n"
    )
    if preco:
        copy_padrao += f"💰 *Por apenas: R$ {preco}*\n\n"
    else:
        copy_padrao += "\n"
    
    copy_padrao += f"⚡ Aproveite antes que acabe!\n👉 {link}"

    if not GEMINI_API_KEY:
        return copy_padrao

    url_gemini = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    
    prompt = f"""Crie uma mensagem curta, persuasiva e vendedora para o WhatsApp sobre a seguinte oferta do Mercado Livre.
Produto: {titulo}
{f'Preço: R$ {preco}' if preco else ''}
Link: {link}

Regras:
1. Use emojis atrativos no início das frases.
2. Destaque o nome do produto e o preço (se fornecido).
3. Inclua uma chamada para ação clara incentivando a compra.
4. Mantenha o link exatamente como fornecido: {link}
5. Retorne APENAS o texto formatado para o WhatsApp."""

    payload = {
        "contents": [{
            "parts": [{"text": prompt}]
        }]
    }

    headers = {"Content-Type": "application/json"}

    try:
        response = requests.post(url_gemini, json=payload, headers=headers, timeout=15)
        if response.status_code == 200:
            res_data = response.json()
            text = res_data['candidates'][0]['content']['parts'][0]['text']
            return text.strip()
        else:
            print(f"⚠️ Aviso na API Gemini (Status {response.status_code}). A usar modelo de copy padrão...", flush=True)
            return copy_padrao
    except Exception as e:
        print(f"⚠️ Erro de conexão com o Gemini: {e}. A usar copy padrão...", flush=True)
        return copy_padrao


# ==================== 3. ENVIAR MENSAGEM VIA EVOLUTION API ====================
def enviar_mensagem_whatsapp(texto):
    url = f"{EVOLUTION_URL}/message/sendText/{INSTANCE_NAME}"
    headers = {
        "apikey": EVOLUTION_APIKEY,
        "Content-Type": "application/json"
    }
    payload = {
        "number": GROUP_JID,
        "text": texto
    }

    try:
        print("🚀 A enviar mensagem via Evolution API...", flush=True)
        response = requests.post(url, json=payload, headers=headers, timeout=15)
        print(f"📩 Resposta Evolution API: Status {response.status_code} - {response.text}", flush=True)
        if response.status_code in [200, 201]:
            print("✅ Oferta enviada com sucesso para o grupo de WhatsApp!", flush=True)
            return True
    except Exception as e:
        print(f"❌ Erro ao enviar mensagem no WhatsApp: {e}", flush=True)
    return False


# ==================== 4. AGENTE DE OFERTAS ====================
def executar_agente_ofertas():
    print("\n🔎 Agente a procurar novas ofertas no Mercado Livre...", flush=True)
    ofertas = buscar_ofertas_mercadolivre()
    
    print(f"✅ Total de produtos extraídos com sucesso: {len(ofertas)}", flush=True)

    for produto in ofertas:
        link = produto['link']
        if link not in PRODUTOS_ENVIADOS:
            print(f"📦 Nova oferta selecionada: {produto['titulo']}", flush=True)
            print(f"🤖 A gerar copy para: {produto['titulo']}...", flush=True)
            
            mensagem = gerar_copy_gemini(produto)
            sucesso = enviar_mensagem_whatsapp(mensagem)

            if sucesso:
                PRODUTOS_ENVIADOS.add(link)
                break  # Envia uma oferta por ciclo
            else:
                print("⚠️ Falha ao enviar oferta. Tentando no próximo ciclo.", flush=True)


# ==================== INICIALIZAÇÃO ====================
if __name__ == "__main__":
    print("🚀 Agente de ofertas iniciado!", flush=True)
    
    # Executa a primeira vez imediatamente
    executar_agente_ofertas()

    # Agenda a execução a cada 30 minutos
    scheduler = BlockingScheduler()
    scheduler.add_job(executar_agente_ofertas, 'interval', minutes=30)

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        print("🛑 Agente de ofertas parado com sucesso.", flush=True)
