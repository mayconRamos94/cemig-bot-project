from playwright.async_api import async_playwright
import asyncio
import os
from datetime import datetime

class WhatsAppClient:

    _instance = None

    def __init__(self):
        self.ultima_msg_processada = None
        self.mensagem_inicial_count = 0
        self.reset_count = 0  # 🔥 controle de reset

    # =========================
    @classmethod
    async def get_instance(cls):
        if cls._instance is None:
            cls._instance = WhatsAppClient()
            await cls._instance.init()
        return cls._instance

    # =========================
    async def init(self):
        
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=False)

        session_file = "whatsapp_session.json"

        if os.path.exists(session_file):
            print("🔄 Carregando sessão existente...")
            self.context = await self.browser.new_context(storage_state=session_file)
        else:
            print("⚠️ Nova sessão - escaneie o QR code")
            self.context = await self.browser.new_context()

        self.page = await self.context.new_page()
        await self.page.goto("https://web.whatsapp.com")

        print("⏳ Aguardando WhatsApp carregar...")
        await self.page.wait_for_selector("#pane-side", timeout=60000)

        print("✅ WhatsApp pronto!")
        await self.context.storage_state(path=session_file)

    # =========================
    async def abrir_conversa_cemig(self):
        await self.page.goto("https://web.whatsapp.com/send?phone=553135061160")
        await asyncio.sleep(5)

        try:
            await self.page.locator("text=Continuar conversa").click(timeout=5000)
        except:
            pass

        await self.page.wait_for_selector("div[contenteditable='true']")

    # =========================
    async def enviar_mensagem(self, texto):
        await asyncio.sleep(1)
        input_box = self.page.locator("div[contenteditable='true']").last
        await input_box.click()
        await input_box.fill(texto)
        await self.page.keyboard.press("Enter")

        print(f"📤 {texto}")
        await asyncio.sleep(2)

    # =========================
    async def get_ultima_mensagem(self):
        try:
            await asyncio.sleep(1)

            mensagens = await self.page.locator("div.message-in").all()

            if not mensagens:
                return ""

            ultima = mensagens[-1]
            texto = (await ultima.inner_text()).lower().strip()

            # 🚨 evita repetir mensagem
            if texto == self.ultima_msg_processada:
                return ""

            return texto

        except Exception as e:
            print("⚠️ erro ao ler mensagem:", e)
            return ""
    # =========================
    async def tem_pdf(self):
        mensagens = self.page.locator("div.message-in")
        total = await mensagens.count()

        for i in range(self.mensagem_inicial_count, total):
            msg = mensagens.nth(i)
            texto = (await msg.inner_text()).lower()

            if ".pdf" in texto:
                return True

            if await msg.locator("span[data-icon='document']").count() > 0:
                return True

        return False

    # =========================
    async def baixar_pdf(self):
        mensagens = self.page.locator("div.message-in")
        total = await mensagens.count()

        for i in range(total - 1, -1, -1):
            msg = mensagens.nth(i)
            texto = (await msg.inner_text()).lower()

            if ".pdf" in texto or await msg.locator("span[data-icon='document']").count() > 0:
                async with self.page.expect_download() as download_info:
                    await msg.click()

                download = await download_info.value
                path = os.path.join(os.getcwd(), download.suggested_filename)
                await download.save_as(path)

                print("✅ PDF salvo:", path)
                return path

        return None

    
    async def responder_fluxo(self, cpf, instalacao):
        await asyncio.sleep(1.0)
        ultima = await self.get_ultima_mensagem()
        ultima = ultima.lower().strip()

        # 🚨 TRAVA DUPLICAÇÃO
        if ultima == self.ultima_msg_processada:
            await asyncio.sleep(1)
            return "AGUARDAR"
        self.ultima_msg_processada = ultima

        print(f"🧠 → {ultima}")

        # 🔥 LOG
        from datetime import datetime
        with open("log_conversa.txt", "a", encoding="utf-8") as f:
            f.write(f"\n[{datetime.now()}]\n{ultima}\n{'-'*50}\n")
            
        if "já entrou em contato" in ultima or "ja entrou em contato" in ultima:
            print("♻️ Detectado contexto antigo → aguardando pergunta")
            return "AGUARDAR"

        if "confirme seus dados" in ultima:
            print("📋 Ignorando confirmação antiga")
            return "AGUARDAR"

        # 🚨 IGNORA LIXO
        if len(ultima) < 5:
            return "AGUARDAR"

        if any(x in ultima for x in [
            "disponível nas lojas",
            "veja no vídeo",
            "youtube.com",
            "aplicativo da cemig",
        ]):
            return "AGUARDAR"

        # 🚨 INFORMAÇÃO (não responder)
        if "não há débitos" in ultima or "nao ha debitos" in ultima:
            return "AGUARDAR"

        # =========================
        # 🔥 PRIORIDADE MÁXIMA
        # =========================
        
        if "deseja atendimento" in ultima:
            print("⚡ Novo atendimento - ignorando contexto antigo")

            await self.enviar_mensagem("Não")
           
            return "OK"

        # CONFIRMAÇÃO (PRIORIDADE)
        if "é isso mesmo" in ultima or "e isso mesmo" in ultima:
            print("✅ Respondendo confirmação imediatamente")
            await self.enviar_mensagem("Sim")
            return "OK"
        # CPF
        if "cpf" in ultima or "cnpj" in ultima:
            print("📄 Enviando CPF")
            await self.enviar_mensagem(cpf)
            return "OK"

        # INSTALAÇÃO
        if (
            "instalação" in ultima
            or "instalacao" in ultima
            or "unidade consumidora" in ultima
        ):
            print("🏠 Enviando instalação")
            await self.enviar_mensagem(instalacao)
            return "OK"
        
        if "titular da conta" in ultima:
            print("👤 Detectou titular → aguardando confirmação")
            return "AGUARDAR"

        # TITULAR (CASO ESPECÍFICO)
        if (
            "titular" in ultima
            and "cpf" not in ultima
            and "cnpj" not in ultima
        ):
            print("👤 Confirmando titular")
            await self.enviar_mensagem("Sim")
            return "OK"

        # =========================
        # 🔥 FLUXO CRÍTICO
        # =========================

        # SEM DÉBITO → CONFIRMAÇÃO FINAL
        if "ainda assim" in ultima and "segunda via" in ultima:
            print("📄 Sem débito → finalizando")
            await self.enviar_mensagem("Não")
            return "OK"

        # =========================
        # 🔥 ERROS / RECUPERAÇÃO
        # =========================

        if "não entendi" in ultima or "nao entendi" in ultima:
            print("🔄 Reset leve")
            await self.enviar_mensagem("2 via fatura")
            return "OK"

        if "não estou conseguindo te identificar" in ultima:
            print("🔄 Reset por identificação")
            await self.enviar_mensagem("Oi")
            await asyncio.sleep(1)
            await self.enviar_mensagem("2 via fatura")
            return "OK"

        # =========================
        # 🔥 FINALIZAÇÃO
        # =========================

        if (
            "te ajudo em algo mais" in ultima
            or "algo mais" in ultima
            or "quer tirar outra" in ultima
        ):
            print("🔚 Finalizando atendimento")
            await self.enviar_mensagem("Não")
            return "OK"

        if "como você avalia" in ultima:
            print("⭐ Avaliação")
            await self.enviar_mensagem("10")
            return "FINALIZADO"

        if "foi um prazer conversar" in ultima:
            print("♻️ Reiniciando fluxo")
            await self.enviar_mensagem("Oi")
            await asyncio.sleep(1)
            await self.enviar_mensagem("2 via fatura")
            return "OK"

        # =========================
        # 🔥 MENU (POR ÚLTIMO)
        # =========================

        if (
            "como posso te ajudar" in ultima
            or "digite em poucas palavras" in ultima
        ):
            print("📄 Enviando serviço")
            await self.enviar_mensagem("2 via fatura")
            return "OK"

        # =========================
        # 🔥 PDF
        # =========================

        if await self.tem_pdf():
            print("📥 PDF detectado")
            return "PDF"

        # =========================
        # 🔥 FALLBACK
        # =========================

        return "AGUARDAR"
    
    async def esperar_nova_resposta(self, timeout=15):
        mensagens = self.page.locator("div.message-in")
        inicial = await mensagens.count()

        for _ in range(timeout * 2):  # checa mais vezes
            await asyncio.sleep(0.5)

            atual = await mensagens.count()
            if atual > inicial:
                return True

        return False

    # =========================
    async def buscar_conta(self, cpf, instalacao):
        self.ultima_msg_processada = None
        await self.abrir_conversa_cemig()
        await self.limpar_conversa()

        await self.enviar_mensagem("Oi")
        await self.esperar_nova_resposta()

        mensagens = self.page.locator("div.message-in")
        self.mensagem_inicial_count = await mensagens.count()

        await self.enviar_mensagem("2 via fatura")
        await self.esperar_nova_resposta()

        for _ in range(20):

            # 🔥 prioridade máxima: PDF
            if await self.tem_pdf():
                pdfs = await self.baixar_todos_pdfs()

                if len(pdfs) == 1:
                    return pdfs[0]

                return pdfs

            resultado = await self.responder_fluxo(cpf, instalacao)

            if resultado == "SEM_CONTA":
                return "❌ Conta não encontrada"
            
            if resultado == "SEM_DEBITO":
                return "❌ Não foram encontrados débitos para essa instalação."

            if resultado == "FINALIZADO":
                return {"tipo": "confirmacao"}

            if resultado == "AGUARDAR":
                await self.esperar_nova_resposta()

            # 🔥 verifica de novo após resposta
            if await self.tem_pdf():
                pdfs = await self.baixar_todos_pdfs()

                if len(pdfs) == 1:
                    return pdfs[0]

                return pdfs

        return "⚠️ Não consegui obter a fatura."

    # =========================
    async def limpar_conversa(self):
        for _ in range(5):
            ultima = await self.get_ultima_mensagem()

            if "mais alguma conta" in ultima:
                await self.enviar_mensagem("Não")
                await self.esperar_nova_resposta()

            elif "quer tirar outra dúvida" in ultima:
                await self.enviar_mensagem("Não")
                await self.esperar_nova_resposta()

            elif "como você avalia" in ultima:
                await self.enviar_mensagem("10")
                await self.esperar_nova_resposta()

            else:
                break
            
    async def baixar_todos_pdfs(self):
        mensagens = self.page.locator("div.message-in")
        total = await mensagens.count()

        arquivos = []

        for i in range(self.mensagem_inicial_count, total):
            msg = mensagens.nth(i)

            if await msg.locator("span[data-icon='document']").count() > 0:
                async with self.page.expect_download() as download_info:
                    await msg.click()

                download = await download_info.value
                path = os.path.join(os.getcwd(), download.suggested_filename)
                await download.save_as(path)

                print("📥 PDF salvo:", path)
                arquivos.append(path)

        return arquivos