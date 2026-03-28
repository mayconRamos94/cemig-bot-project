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

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Envie qualquer mensagem para começar")


def validar_instalacao(texto):
    texto = texto.strip()
    return texto.isdigit() and len(texto) >= 8


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text.strip()

    # =========================
    # INICIO
    # =========================
    if user_id not in user_state:
        user_state[user_id] = {"step": "cpf"}
        await update.message.reply_text("Digite seu CPF ou CNPJ:")
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

        cpf = user_state[user_id]["cpf"]
        instalacao = text

        await update.message.reply_text("🔎 Buscando conta...")

        try:
            client = await WhatsAppClient.get_instance()

            # 🔥 AGORA SEM MES/ANO
            resultado = await client.buscar_conta(
                cpf,
                instalacao
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
            # 🔥 múltiplos PDFs
            if isinstance(resultado, list):

                for pdf in resultado:
                    await update.message.reply_document(
                        document=open(pdf, "rb"),
                        filename="fatura_cemig.pdf"
                    )

                user_state[user_id]["step"] = "confirmar_continuacao"

                await update.message.reply_text(
                    f"📄 {len(resultado)} faturas encontradas!\n\nDeseja buscar outra conta?\n\nResponda: Sim ou Não"
                )
                return


            # 🔥 PDF único (seu código atual)
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
            user_state[user_id]["step"] = "cpf"
            await update.message.reply_text("Digite o CPF ou CNPJ:")
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

    app.run_polling()


if __name__ == "__main__":
    run_bot()