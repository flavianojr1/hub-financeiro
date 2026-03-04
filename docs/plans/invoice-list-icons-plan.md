# Plano: Profissionalizar Ícones na Lista de Faturas

## Contexto
Na página `/dashboard/faturas/`, há emojis sendo usados como ícones:
- 📅 (calendar) - ícone da fatura
- 🔄 (refresh) - botão de atualizar
- 🗑️ (trashbin) - botão de deletar

## Objetivo
Substituir os emojis por ícones Flaticon profissionais (fi fi-br-*).

## Ícones Sugeridos

| Emoji | Uso | Ícone Flaticon | Classe |
|-------|-----|----------------|--------|
| 📅 | Ícone da fatura | Calendário | `fi fi-br-calendar` |
| 🔄 | Atualizar fatura | Refresh/Rotação | `fi fi-br-rotate-right` |
| 🗑️ | Deletar fatura | Lixeira | `fi fi-br-trash` |

## Implementação

### Arquivo: `invoices/templates/invoices/invoice_list.html`

**Linha 81 - Ícone da fatura:**
```html
<!-- Antes -->
<div class="inv-icon-box">📅</div>

<!-- Depois -->
<div class="inv-icon-box"><i class="fi fi-br-calendar"></i></div>
```

**Linha 118 - Botão atualizar:**
```html
<!-- Antes -->
🔄

<!-- Depois -->
<i class="fi fi-br-rotate-right"></i>
```

**Linha 125 - Botão deletar:**
```html
<!-- Antes -->
🗑️

<!-- Depois -->
<i class="fi fi-br-trash"></i>
```

## CSS Adicional (se necessário)

Ajustar tamanho e alinhamento dos ícones nos botões de ação:
```css
.inv-row .btn i {
    font-size: 1rem;
    display: flex;
    align-items: center;
    justify-content: center;
}
```

## Arquivos

| Arquivo | Ação |
|---------|------|
| `invoices/templates/invoices/invoice_list.html` | Substituir 3 emojis por ícones Flaticon |
