# Plano: Adicionar Animação aos Itens do Menu Lateral

## Contexto
A página `/dashboard` utiliza a animação `fadeInUp` nos elementos `.stat-card` e `.chart-card`. O objetivo é aplicar a mesma animação aos itens do menu lateral (sidebar) ao carregar a página.

## Animação Atual no Dashboard

```css
/* style.css linha 672-680 */
@keyframes fadeInUp {
    from {
        opacity: 0;
        transform: translateY(20px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

/* Aplicada aos stat-cards com delays escalonados */
.stat-card {
    animation: fadeInUp 0.5s ease forwards;
    opacity: 0;
}
.stat-card:nth-child(1) { animation-delay: 0.1s; }
.stat-card:nth-child(2) { animation-delay: 0.2s; }
.stat-card:nth-child(3) { animation-delay: 0.3s; }
.stat-card:nth-child(4) { animation-delay: 0.4s; }
```

## Estrutura do Menu Lateral

Localizada em `invoices/templates/invoices/base.html` (linhas 38-88):

- Dashboard (linha 39-44)
- Nova Fatura (linha 45-50)
- Faturas (linha 51-56)
- Categorias (linha 57-62)
- Cartões (linha 63-68)
- Meu Perfil (linha 75-80) - dentro de `.sidebar-profile-section`

## Plano de Implementação

### 1. Modificar o CSS (`invoices/static/css/style.css`)

Adicionar animação aos links da sidebar com delays escalonados:

```css
/* Adicionar após a definição dos .stat-card */
.sidebar-link {
    animation: fadeInUp 0.4s ease forwards;
    opacity: 0;
}

/* Delays escalonados para cada item do menu */
.sidebar-nav .sidebar-link:nth-child(1) { animation-delay: 0.05s; }  /* Dashboard */
.sidebar-nav .sidebar-link:nth-child(2) { animation-delay: 0.1s; }   /* Nova Fatura */
.sidebar-nav .sidebar-link:nth-child(3) { animation-delay: 0.15s; }  /* Faturas */
.sidebar-nav .sidebar-link:nth-child(4) { animation-delay: 0.2s; }   /* Categorias */
.sidebar-nav .sidebar-link:nth-child(5) { animation-delay: 0.25s; }  /* Cartões */

/* Meu Perfil tem delay maior pois está em seção separada */
.sidebar-profile-section .sidebar-link {
    animation-delay: 0.3s;
}
```

### 2. Considerações

- **Performance**: Usar `transform` e `opacity` é eficiente (GPU-accelerated)
- **Acessibilidade**: A animação não bloqueia interação com os links
- **Timing**: Delays menores (0.05s a 0.3s) para não parecer lento
- **Mobile**: A animação deve funcionar em todos os tamanhos de tela

### 3. Arquivos a Modificar

| Arquivo | Linha(s) | Ação |
|---------|----------|------|
| `invoices/static/css/style.css` | Após linha 670 | Adicionar regras de animação para `.sidebar-link` |

### 4. Efeito Visual Esperado

Ao carregar qualquer página com o menu lateral:
1. Os itens do menu surgem de baixo para cima (`translateY(20px)` → `translateY(0)`)
2. Fade in simultâneo (`opacity: 0` → `opacity: 1`)
3. Efeito cascata: cada item aparece 0.05s após o anterior
4. Total da animação: ~0.35s para todos os itens

## Diagrama do Efeito

```
Tempo →
0ms    [Dashboard] aparece
50ms   [Nova Fatura] aparece
100ms  [Faturas] aparece
150ms  [Categorias] aparece
200ms  [Cartões] aparece
250ms  [Meu Perfil] aparece
```
