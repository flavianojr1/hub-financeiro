<div align="center">

<img src="apps/invoices/static/img/hub-financeiro-wide-v2.png" alt="Hub Financeiro" width="500" />

# Hub Financeiro

**Uma solução moderna e modular para gestão financeira pessoal com Django.**

[![Python](https://img.shields.io/badge/Python-3.x-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![Django](https://img.shields.io/badge/Django-5.0.1-092E20?style=flat-square&logo=django&logoColor=white)](https://djangoproject.com)
[![SQLite](https://img.shields.io/badge/SQLite-Local-003B57?style=flat-square&logo=sqlite&logoColor=white)](https://sqlite.org)
[![Status](https://img.shields.io/badge/Status-Development-orange?style=flat-square)](https://github.com/flavianojr1/hub-financeiro)
[![Architecture](https://img.shields.io/badge/Architecture-Core--Apps-blueviolet?style=flat-square)](https://github.com/flavianojr1/hub-financeiro)

---

[Sobre](#-sobre) • [Funcionalidades](#-funcionalidades) • [Tecnologias](#-tecnologias) • [Estrutura](#-estrutura) • [Começando](#-começando) • [Comandos](#-comandos)

</div>

## 📖 Sobre

O **Hub Financeiro** nasceu da necessidade de simplificar o controle de gastos complexos, como faturas de cartão de crédito com múltiplas parcelas. Diferente de uma planilha estática, ele oferece uma plataforma dinâmica que processa extratos CSV, projeta gastos futuros e categoriza suas despesas automaticamente, permitindo que você foque no que realmente importa: **sua saúde financeira.**

---

## ✨ Funcionalidades

- 💳 **Gestão de Cartões**: Cadastro e acompanhamento individual de múltiplos cartões.
- 📂 **Parser de CSV**: Importação simplificada de extratos (NuBank e outros).
- 🗓️ **Projeção de Parcelas**: Visualize hoje o impacto das compras parceladas nos próximos meses.
- 🏷️ **Categorização Inteligente**: Regras baseadas em palavras-chave para classificação automática.
- 📊 **Dashboard de Insights**: Visão geral de gastos por categoria e evolução mensal.
- 🔒 **Privacidade**: Execução 100% local com SQLite para total controle dos seus dados.

---

## 🛠️ Tecnologias

O projeto foi construído utilizando as melhores práticas do ecossistema Python:

- **Linguagem:** [Python 3.x](https://python.org)
- **Framework Web:** [Django 5.0.1](https://djangoproject.com)
- **Banco de Dados:** [SQLite](https://sqlite.org) (Local)
- **Gráficos:** [Chart.js](https://www.chartjs.org/)
- **Estilização:** CSS Vanilla & [Font Awesome](https://fontawesome.com/)

---

## 🏗️ Estrutura do Projeto

O Hub Financeiro utiliza uma arquitetura modular **Core/Apps**, separando preocupações de infraestrutura da lógica de negócio:

```bash
hub-financeiro/
├── core/             # Configurações globais, URLs e WSGI/ASGI
├── apps/             # Módulos de negócio (apps Django)
│   ├── invoices/     # Lógica de faturas, upload e dashboard
│   └── pages/        # Gestão de usuários e páginas institucionais
├── templates/        # Arquivos HTML globais e componentes
└── main.py           # Ponto único de entrada do sistema
```

---

## 🚀 Começando

Siga os passos abaixo para rodar o projeto em sua máquina local:

### 1. Clonar o Repositório
```bash
git clone https://github.com/flavianojr1/hub-financeiro.git
cd hub-financeiro
```

### 2. Configurar Ambiente
```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/Mac
source .venv/bin/activate

pip install -r requirements.txt
```

### 3. Variáveis de Ambiente
Crie um arquivo `.env` na raiz:
```env
DEBUG=True
SECRET_KEY=sua_chave_secreta_aqui
```

### 4. Inicializar e Rodar
```bash
python main.py migrate
python main.py
```
Acesse: [http://127.0.0.1:8000](http://127.0.0.1:8000)

---

## ⌨️ Comandos Rápidos

O `main.py` substitui o tradicional `manage.py`, centralizando a administração:

| Objetivo | Comando |
| :--- | :--- |
| **Rodar Servidor** | `python main.py` |
| **Aplicar Migrações** | `python main.py migrate` |
| **Criar Superusuário** | `python main.py createsuperuser` |
| **Gerar Migrações** | `python main.py makemigrations` |
| **Console Django** | `python main.py shell` |

---

<div align="center">

**[Hub Financeiro](https://github.com/flavianojr1/hub-financeiro)** • Organização e Clareza para o seu bolso.

</div>
