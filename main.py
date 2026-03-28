from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
import os
from dotenv import load_dotenv
from whatsapp_client import WhatsAppClient
import re

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN não encontrado no .env")

user_state = {}

def validar_mes_ano(texto):
    return re.match(r"^(0[1-9]|1[0-2])/\d{4}$", texto)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Envie qualquer mensagem para começar")

def validar_instalacao(texto):
# remove espaços
    texto = texto.strip()

    # só números e mínimo 8 dígitos
    return texto.isdigit() and len(texto) >= 8
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text.strip()

    # =========================
    # INICIO
    # =========================
    if user_id not in user_state:
        user_state[user_id] = {"step": "cpf"}
        await update.message.reply_text("Digite seu CPF:")
        return

    # =========================
    # CPF
    # =========================
    if user_state[user_id]["step"] == "cpf":
        user_state[user_id]["cpf"] = text
        user_state[user_id]["step"] = "instalacao"

        await update.message.reply_text("Digite o número da instalação:")
        return

    # =========================
    # INSTALAÇÃO
    # =========================
   
    if user_state[user_id]["step"] == "instalacao":

        if not validar_instalacao(text):
            await update.message.reply_text(
                "Número de instalação inválido.\n\nDigite apenas números com pelo menos 8 dígitos."
            )
            return

        user_state[user_id]["instalacao"] = text
        user_state[user_id]["step"] = "mes_ano"

        await update.message.reply_text("Digite o mês/ano da fatura (ex: 01/2024):")
        return
    # =========================
    # MÊS/ANO
    # =========================
    if user_state[user_id]["step"] == "mes_ano":

        if not validar_mes_ano(text):
            await update.message.reply_text("Formato inválido. Use MM/AAAA (ex: 01/2024)")
            return

        cpf = user_state[user_id]["cpf"]
        instalacao = user_state[user_id]["instalacao"]
        mes_ano = text

        await update.message.reply_text("🔎 Buscando conta...")

        try:
            client = await WhatsAppClient.get_instance()

            # 🔥 AGORA É ASYNC DE VERDADE
            resultado = await client.buscar_conta(
                cpf,
                instalacao,
                mes_ano
            )

            # =========================
            # RESULTADO VAZIO
            # =========================
            if not resultado:
                await update.message.reply_text("⚠️ Não consegui obter a fatura.")
                return

            # =========================
            # PDF
            # =========================
            if isinstance(resultado, str) and resultado.endswith(".pdf"):

                await update.message.reply_document(
                    document=open(resultado, "rb"),
                    filename="fatura_cemig.pdf"
                )

                user_state[user_id]["step"] = "confirmar_continuacao"

                await update.message.reply_text(
                    "📄 Fatura encontrada!\n\nDeseja buscar outra conta?\n\nResponda: Sim ou Não"
                )
                return

            # =========================
            # DICT
            # =========================
            if isinstance(resultado, dict):

                if resultado.get("tipo") == "confirmacao":
                    user_state[user_id]["step"] = "confirmar_continuacao"

                    await update.message.reply_text(
                        "Deseja buscar outra conta?\n\nResponda: Sim ou Não"
                    )
                    return

            # =========================
            # TEXTO NORMAL
            # =========================
            await update.message.reply_text(resultado)

            del user_state[user_id]
            return

        except Exception as e:
            print("Erro no bot:", e)
            await update.message.reply_text("⚠️ Erro ao consultar. Tente novamente.")

            if user_id in user_state:
                del user_state[user_id]
            return

    # =========================
    # CONFIRMAÇÃO FINAL
    # =========================
    if user_state[user_id]["step"] == "confirmar_continuacao":

        resposta = text.lower()

        if resposta == "sim":
            user_state[user_id]["step"] = "mes_ano"

            await update.message.reply_text("Digite o mês/ano da próxima fatura:")
            return

        elif resposta in ["não", "nao"]:
            await update.message.reply_text("✅ Atendimento finalizado!")

            del user_state[user_id]
            return

        else:
            await update.message.reply_text("Responda apenas com Sim ou Não.")
            return


def run_bot():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Bot rodando...")

    # 🔥 SEM while, SEM loop duplicado
    app.run_polling()


if __name__ == "__main__":
    run_bot()
    
    