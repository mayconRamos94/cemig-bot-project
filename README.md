# 🤖 Bot Telegram + WhatsApp (Cemig)

Este projeto automatiza a solicitação de segunda via de contas da Cemig através do WhatsApp Web, integrado com um bot no Telegram.

---

## 🚀 Funcionalidades

* Solicitação automática de segunda via
* Integração Telegram → WhatsApp
* Download automático do PDF da fatura
* Tratamento de erros e fluxo completo da Cemig

---

## 🛠️ Tecnologias

* Python 3.11+
* Playwright
* python-telegram-bot
* AsyncIO

---

## 📦 Instalação

### 1. Clonar o projeto

```bash
git clone <seu-repositorio>
cd cemig_bot_project
```

---

### 2. Criar ambiente virtual (recomendado)

```bash
python -m venv venv
venv\Scripts\activate
```

---

### 3. Instalar dependências

```bash
pip install -r requirements.txt
```

---

### 4. Instalar Playwright

```bash
playwright install
```

---

## ▶️ Como rodar o projeto

```bash
python main.py
```

---

## 📱 Primeiro acesso (IMPORTANTE)

Na primeira execução:

* O WhatsApp Web será aberto automaticamente
* Você deverá escanear o QR Code
* Após isso, a sessão será salva (não precisa escanear novamente)

---

## 🤖 Como usar o bot

1. Abra o bot no Telegram

2. Envie:

   * CPF
   * Número da instalação
   * Mês/Ano (ex: 05/2025)

3. O bot irá:

   * acessar a Cemig
   * solicitar a fatura
   * retornar o PDF automaticamente

---

## ⚠️ Observações importantes

* O WhatsApp Web deve permanecer aberto
* Não fechar o navegador enquanto o bot estiver rodando
* Internet estável é necessária

---

## 📁 Estrutura

```
main.py
whatsapp_client.py
requirements.txt
```

---

## ✅ Status

Projeto funcional e pronto para uso.

---

## 📞 Suporte

Caso tenha dúvidas, estou à disposição para ajudar.
