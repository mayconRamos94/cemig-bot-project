from playwright.async_api import async_playwright
import asyncio
import os


class WhatsAppClient:

    _instance = None

    def __init__(self):
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
        input_box = self.page.locator("div[contenteditable='true']").last
        await input_box.click()
        await input_box.fill(texto)
        await self.page.keyboard.press("Enter")

        print(f"📤 {texto}")
        await asyncio.sleep(2)

    # =========================
    async def get_ultima_mensagem(self):
        try:
            mensagens = self.page.locator("div.message-in")

            # espera existir pelo menos 1 mensagem
            if await mensagens.count() == 0:
                await mensagens.first.wait_for(timeout=10000)

            # 🔥 usa last direto (mais seguro)
            ultima = mensagens.last

            texto = await ultima.inner_text(timeout=10000)

            return texto.lower()

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

    # =========================
    async def responder_fluxo(self, cpf, instalacao, mes_ano):
        ultima = await self.get_ultima_mensagem()
        print("🧠 Analisando:", ultima)

        # =====================================================
        # 🔥 RESET CONTROLADO (ENTENDER)
        # =====================================================
        if "não estou conseguindo te entender" not in ultima:
            self.reset_count = 0

        if "não estou conseguindo te entender" in ultima or "nao estou conseguindo te entender" in ultima:
            self.reset_count += 1
            print(f"🔄 Resetando... ({self.reset_count})")

            if self.reset_count > 3:
                return "SEM_CONTA"

            await self.enviar_mensagem("Oi")
            await self.esperar_nova_resposta()
            await self.enviar_mensagem("2 via fatura")
            return "OK"

        # =====================================================
        # 🔥 RESET POR IDENTIFICAÇÃO (NOVO)
        # =====================================================
        elif (
            "não estou conseguindo te identificar" in ultima
            or "nao estou conseguindo te identificar" in ultima
        ):
            print("🔄 Reset por erro de identificação")

            await self.enviar_mensagem("Oi")
            await self.esperar_nova_resposta()
            await self.enviar_mensagem("2 via fatura")

            return "OK"

        # =====================================================
        # 🔥 FINALIZAÇÃO
        # =====================================================
        elif (
            "mais alguma conta" in ultima
            or "quer tirar outra dúvida" in ultima
            or "quer tirar outra duvida" in ultima
            or "outra dúvida" in ultima
            or "outra duvida" in ultima
        ):
            print("🔚 Finalizando atendimento")
            await self.enviar_mensagem("Não")
            return "OK"

        elif "como você avalia" in ultima:
            await self.enviar_mensagem("10")
            return "FINALIZADO"

        # =====================================================
        # 🔥 ENCERRAMENTO COMPLETO (NOVO)
        # =====================================================
        elif (
            "foi um prazer conversar com você" in ultima
            or "foi um prazer conversar com voce" in ultima
            or "até mais" in ultima
            or "ate mais" in ultima
        ):
            print("🔚 Conversa encerrada pela Cemig")
            return "FINALIZADO"

        # =====================================================
        # 🔥 DECISÕES
        # =====================================================
        
        elif (
            "deseja atendimento" in ultima
            and (
                "mesma instalação" in ultima
                or "mesma instalacao" in ultima
                or "mesma unidade" in ultima
                or "unidade consumidora" in ultima
            )
        ):
            print("🏠 Respondendo mesma unidade/instalação")
            await self.enviar_mensagem("Não")
            return "OK"
        
        elif (
            "é isso mesmo" in ultima
            or "e isso mesmo" in ultima
        ):
            print("✅ Confirmando titular")
            await self.enviar_mensagem("Sim")
            return "OK"

        elif (
            "ainda assim você precisa" in ultima
            or "ainda assim voce precisa" in ultima
            or "precisa de segunda via" in ultima
        ):
            print("📄 Confirmando segunda via")
            await self.enviar_mensagem("Sim")
            return "OK"

        # =====================================================
        # 🔥 DADOS (PRIORIDADE MÁXIMA)
        # =====================================================
        elif (
            "cpf" in ultima
            or "cnpj" in ultima
            or "digitar apenas os números" in ultima
            or "digite apenas os números" in ultima
            or "números do cpf" in ultima
        ):
            print("📄 Enviando CPF")
            await self.enviar_mensagem(cpf)
            return "OK"
        
        elif (
            "digite para mim o número da unidade" in ultima
            or "digite o número da unidade" in ultima
            or "número da unidade consumidora" in ultima
        ):
            print("🏠 Enviando instalação")
            await self.enviar_mensagem(instalacao)
            return "OK"

        elif (
            "digite a instalação" in ultima
            or "informe a instalação" in ultima
            or "número da instalação" in ultima
        ):
            print("🏠 Enviando instalação")
            await self.enviar_mensagem(instalacao)
            return "OK"

        elif "mês e ano" in ultima:
            print("📅 Enviando mês/ano")
            await self.enviar_mensagem(mes_ano)
            return "OK"

        # =====================================================
        # 🔥 CONFIRMAÇÕES
        # =====================================================
        elif "titular" in ultima:
            print("👤 Confirmando titular")
            await self.enviar_mensagem("Sim")
            return "OK"

        elif (
            "está correto" in ultima
            or "esta correto" in ultima
            or "só pra confirmar" in ultima
            or "so pra confirmar" in ultima
            or "você quer a conta" in ultima
            or "voce quer a conta" in ultima
        ):
            print("✅ Confirmando dados")
            await self.enviar_mensagem("Sim")
            return "OK"

        # =====================================================
        # 🔥 MENU
        # =====================================================
        elif (
            ("como posso te ajudar" in ultima or "principais assuntos" in ultima)
            and "deseja atendimento" not in ultima
        ):
            await self.enviar_mensagem("Segunda Via")
            return "OK"

        elif (
            "digite em poucas palavras" in ultima
            and "deseja atendimento" not in ultima
        ):
            await self.enviar_mensagem("2 via fatura")
            return "OK"

        # =====================================================
        # 🔥 ERROS
        # =====================================================
        elif "não foi possível" in ultima:
            return "SEM_CONTA"
        
        elif "números" in ultima and "cpf" in ultima:
            print("📄 Fallback CPF")
            await self.enviar_mensagem(cpf)
            return "OK"
        
        elif "não entendi" in ultima:
            print("🔄 Reenviando CPF")
            await self.enviar_mensagem(cpf)
            return "OK"

        # =====================================================
        return "IGNORAR"
    
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
    async def buscar_conta(self, cpf, instalacao, mes_ano):
        await self.abrir_conversa_cemig()
        await self.limpar_conversa()

        await self.enviar_mensagem("Oi")
        await self.esperar_nova_resposta()

        mensagens = self.page.locator("div.message-in")
        self.mensagem_inicial_count = await mensagens.count()

        await self.enviar_mensagem("2 via fatura")
        await self.esperar_nova_resposta()

        for _ in range(20):

            if await self.tem_pdf():
                return await self.baixar_pdf()

            resultado = await self.responder_fluxo(cpf, instalacao, mes_ano)

            if resultado == "SEM_CONTA":
                return "❌ Conta não encontrada"

            if resultado == "FINALIZADO":
                return {"tipo": "confirmacao"}

            if resultado != "IGNORAR":
                await self.esperar_nova_resposta()

            if await self.tem_pdf():
                return await self.baixar_pdf()

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
            
    