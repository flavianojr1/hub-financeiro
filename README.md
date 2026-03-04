# Hub Financeiro

Aplicacao web em Django para organizar gastos de cartao de credito a partir de CSV.

## O que o projeto faz

- Importacao de faturas CSV
- Deteccao de compras parceladas e projecao de parcelas futuras
- Categorizacao automatica por regras de palavra-chave
- Dashboard com filtros por mes e por cartao
- Graficos por categoria e evolucao temporal (Chart.js)
- Gestao de cartoes, faturas, categorias e regras
- Area de autenticacao e perfil de usuario

## Stack

- Python 3.13
- Django 5.0.1
- SQLite (local) / Postgres (producao)
- WhiteNoise para static files
- Gunicorn para WSGI

## Estrutura principal

- `nubank_project/` configuracoes do Django
- `invoices/` regras de negocio (upload, parser, dashboard)
- `pages/` home, autenticacao e perfil
- `templates/` templates globais
- `api/index.py` entrada serverless para Vercel
- `vercel.json` roteamento/build para Vercel

## Executar localmente

1. Criar e ativar virtualenv

```bash
python -m venv .venv
.venv\Scripts\activate
```

2. Instalar dependencias

```bash
pip install -r requirements.txt
```

3. Configurar ambiente local (`.env`)

Use o `.env.example` como base.

4. Migrar banco

```bash
python manage.py migrate
```

5. Rodar servidor

```bash
python manage.py runserver
```

Acesse: `http://127.0.0.1:8000/`

## Variaveis de ambiente

Minimo recomendado:

- `SECRET_KEY`
- `DEBUG`
- `ALLOWED_HOSTS`
- `CSRF_TRUSTED_ORIGINS`
- `DATABASE_URL` (em producao)

## Deploy na Vercel

No projeto da Vercel:

1. Framework Preset: `Other`
2. Build Command: usa o `vercel.json` do repo
3. Configurar env vars de producao:
   - `SECRET_KEY`
   - `DEBUG=False`
   - `ALLOWED_HOSTS=<seu-projeto>.vercel.app`
   - `CSRF_TRUSTED_ORIGINS=https://<seu-projeto>.vercel.app`
   - `DATABASE_URL=<postgres-url>`

Depois do primeiro deploy, rode migracoes no banco de producao.

## Seguranca de repositorio

- `.env`, banco local e arquivos locais de IDE/agentes estao ignorados no Git
- Hook versionado em `.githooks/pre-commit` bloqueia commits de arquivos sensiveis

## Licenca

Projeto de uso pessoal/estudo.
