<div align="center">

<img src="apps/invoices/static/img/hub-financeiro-wide-texto-branco-v2-removebg-preview.png" alt="Hub Financeiro" width="600" />

# 💰 Hub Financeiro

**Gestão financeira moderna, inteligente e 100% sob seu controle.**

[![Python](https://img.shields.io/badge/Python-3.x-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Django](https://img.shields.io/badge/Django-5.0.1-092E20?style=for-the-badge&logo=django&logoColor=white)](https://djangoproject.com)
[![SQLite](https://img.shields.io/badge/SQLite-Local-003B57?style=for-the-badge&logo=sqlite&logoColor=white)](https://sqlite.org)
[![Licença](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](LICENSE)

---

[Sobre](#-sobre) • [Funcionalidades](#-funcionalidades) • [Interface](#-interface) • [Começando](#-começando) • [Diferenciais](#-diferenciais)

</div>

<br />

## 📖 Sobre

O **Hub Financeiro** é uma plataforma modular desenvolvida em Django para centralizar e automatizar sua vida financeira. Ele vai além das planilhas tradicionais ao processar faturas bancárias reais, projetar compras parceladas nos meses futuros e oferecer insights visuais dinâmicos sobre seus hábitos de consumo.

Ideal para quem busca **privacidade total** (dados 100% locais) e **automação inteligente**.

---

## ✨ Funcionalidades Principais

### 📂 Importação Inteligente
- **Nubank (CSV)**: Importação nativa direta do extrato do app.
- **Banco Inter (PDF)**: Leitura automática de faturas em PDF com extração de tabelas e datas de vencimento.
- **Confirmação de Período**: Modal inteligente que detecta o mês/ano no nome do arquivo e solicita sua confirmação manual.

### 🔮 Projeção de Futuro
- **Detecção de Parcelas**: O sistema identifica padrões como `Parcela 01/10` e gera automaticamente previsões para os próximos meses.
- **Deduplicação Ativa**: Algoritmo inteligente que substitui previsões por gastos reais confirmados, evitando dados duplicados em múltiplos uploads.

### 🏷️ Categorização Automática
- **Motor de Regras**: Crie regras baseadas em palavras-chave (ex: `iFood` ➔ `Alimentação`).
- **Kit de Boas-Vindas**: Novos usuários já começam com categorias e regras padrão (Uber, Netflix, etc.) pré-configuradas.

### 📊 Dashboard Dinâmico
- **KPIs em Tempo Real**: Total gasto, média de transações e contagem mensal.
- **Gráficos Interativos**: Evolução temporal e distribuição por categoria via Chart.js.
- **Filtros Ágeis**: Slicers de mês e cartão com atualização via AJAX (sem recarregar a página).

---

## 🎨 Interface Vision

A UI foi construída sob a estética **Vision**, focada em uma experiência premium e fluida:

- 🌓 **Temas Dinâmicos**: Suporte nativo a temas **Claro (Padrão)** e **Escuro**, com persistência local.
- 📱 **Responsividade Total**: Interface adaptada para qualquer tamanho de tela.
- 🌪️ **Coreografia Visual**: Animações de slide-up majestosas, efeitos de Glassmorphism e gráficos 3D flutuantes no Hero.
- ⚡ **Micro-interações**: Feedback tátil em botões, transições de perspectiva no hover e ícones animados.

---

## 🚀 Começando

### Pré-requisitos
- Python 3.10+
- Ambiente virtual (venv)

### Instalação Rápida

1. **Clone e acesse a pasta:**
   ```bash
   git clone https://github.com/flavianojr1/hub-financeiro.git
   cd hub-financeiro
   ```

2. **Configure o ambiente:**
   ```bash
   python -m venv .venv
   # Windows: .venv\Scripts\activate | Mac/Linux: source .venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Inicie o banco de dados e o servidor:**
   ```bash
   python main.py migrate
   python main.py
   ```
   Acesse: [http://127.0.0.1:8000](http://127.0.0.1:8000)

---

## 💎 Diferenciais Técnicos

- **Arquitetura Core/Apps**: Separação clara entre infraestrutura e lógica de negócio.
- **Ponto de Entrada Único**: O arquivo `main.py` centraliza todos os comandos administrativos.
- **Deduplicação de Transações**: Integridade de dados garantida por cruzamento de chaves únicas.
- **Extratividade Robusta**: Motor baseado em Regex e `pdfplumber` para layouts complexos.

---

<div align="center">

Desenvolvido com muito carinho ❤️ por **[Flaviano Junior](https://www.linkedin.com/in/flaviano-junior)**

</div>
