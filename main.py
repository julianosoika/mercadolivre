import os
import random
import re
import requests
import feedparser
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# ==========================================
# CONFIGURAÇÕES E VARIÁVEIS DE AMBIENTE
# ==========================================
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# ==========================================
# LISTA DE OFERTAS GARANTIDAS (FALLBACK)
# ==========================================
# URLs formatadas para busca direta para evitar erro de "Página Inexistente" (/p/MLB...)
OFERTAS_FALLBACK = [
    {
        'titulo': 'Smartphone Samsung Galaxy A54 5G 128GB',
        'link': 'https://lista.mercadolivre.com.br/samsung-galaxy-a54',
        'preco': '1.699,00'
    },
    {
        'titulo': 'Fone de Ouvido Bluetooth JBL Wave Flex',
        'link': 'https://lista.mercadolivre.com.br/jbl-wave-flex',
        'preco': '249,00'
    },
    {
        'titulo': 'Smart TV 50" 4K UHD LED LG',
        'link': 'https://lista.mercadolivre.com.br/smart-tv-50-4k-lg',
        'preco': '2.199,00'
    },
    {
        'titulo': 'Console PlayStation 5 Slim Edição Digital',
        'link': 'https://lista.mercadolivre.com.br/playstation-5-slim',
        'preco': '3.499,00'
    },
    {
        'titulo': 'Fritadeira Elétrica Airfryer Mondial 4L',
        'link': 'https://lista.mercadolivre.com.br/airfryer-mondial-4l',
        'preco': '279,00'
    }
]

# ==========================================
# FUNÇÃO PARA GERAR TEXTO COM GEMINI
# ==========================================
def gerar_legenda_gemini(titulo: str, preco: str, link: str) -> str:
    """Gera uma legenda persuasiva usando a API REST do Gemini."""
    if not GEMINI_API_KEY:
        return f"🔥 **OFERTA IMPERDÍVEL!**\n\n📌 **{titulo}**\n💰 Por apenas: R$ {preco}\n\n🛒 Compre aqui: {link}"

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    prompt = (
        f"Escreva uma mensagem promocional curta, entusiasmada e persuasiva para o Telegram sobre este produto:\n"
        f"Produto: {titulo}\n"
        f"Preço: R$ {preco}\n"
        f"Link: {link}\n\n"
        f"Use emojis, destaque o preço e coloque o link de compra claramente no final."
    )
    
    payload = {
        "contents": [{"parts": [{"text": prompt}]}]
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            dados = response.json()
            texto = dados['candidates'][0]['content']['parts'][0]['text']
            return texto
        else:
            print(f"⚠️ Erro no Gemini API (Status {response.status_code}). Utilizando texto padrão.")
    except Exception as e:
        print(f"⚠️ Falha ao conectar ao Gemini: {e}")

    # Mensagem padrão caso a API do Gemini falhe
    return (
        f"🔥 **SUPER OFERTA NO MERCADO LIVRE!**\n\n"
        f"📦 **{titulo}**\n"
        f"💵 **Preço Especial:** R$ {preco}\n\n"
        f"🔗 **Ganta o seu antes que acabe:**\n{link}"
    )

# ==========================================
# BUSCA DE OFERTAS (RSS OU FALLBACK)
# ==========================================
def obter_ofertas():
    """Tenta buscar ofertas via RSS do Mercado Livre; usa fallback se falhar."""
    rss_url = "https://noticias.mercadolivre.com.br/feed/"
    ofertas = []
    
    try:
        feed = feedparser.parse(rss_url)
        for entry in feed.entries[:10]:
            # Tenta extrair o preço do título se presente
            preco_match = re.search(r'R\$\s?([\d\.,]+)', entry.title)
            preco = preco_match.group(1) if preco_match else "Confira no site"
            
            ofertas.append({
                'titulo': entry.title,
                'link': entry.link,
                'preco': preco
            })
    except Exception as e:
        print(f"⚠️ Erro ao ler Feed RSS: {e}")

    if not ofertas:
        print("⚠️ Utilizando lista garantida de ofertas populares...", flush=True)
        ofertas = OFERTAS_FALLBACK

    return ofertas

# ==========================================
# COMANDOS DO TELEGRAM
# ==========================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /start"""
    await update.message.reply_text(
        "👋 Olá! Eu sou o Bot de Ofertas do Mercado Livre.\n\n"
        "Comandos disponíveis:\n"
        "/oferta - Envia uma oferta promocional agora."
    )

async def enviar_oferta(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /oferta"""
    ofertas = obter_ofertas()
    oferta_escolhida = random.choice(ofertas)

    # Gera a mensagem persuasiva
    mensagem = gerar_legenda_gemini(
        titulo=oferta_escolhida['titulo'],
        preco=oferta_escolhida['preco'],
        link=oferta_escolhida['link']
    )

    await update.message.reply_text(
        text=mensagem,
        parse_mode="Markdown",
        disable_web_page_preview=False
    )

# ==========================================
# INICIALIZAÇÃO DO BOT
# ==========================================
def main():
    if not TELEGRAM_BOT_TOKEN:
        raise ValueError("❌ A variável de ambiente TELEGRAM_BOT_TOKEN não foi definida!")

    print("🚀 Bot iniciado com sucesso! Aguardando comandos...", flush=True)

    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    # Registra os manipuladores de comandos
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("oferta", enviar_oferta))

    # Inicia o Bot
    app.run_polling()

if __name__ == "__main__":
    main()
