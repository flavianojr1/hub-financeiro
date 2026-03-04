# Plano de Correção - Layout de Categorias

## Problema Atual
Os inputs e dados do formulário de Categorias estão empilhados verticalmente ao invés de ficarem lado a lado (inline).

## Análise
O CSS atual (style.css linhas 1396-1406) força `.form-row` a ter `flex-direction: column`, making elements stack vertically. Além disso, os elementos não têm dimensões quadradas apropriadas.

## Correções Necessárias

### 1. Adicionar Descrição Informativa (HTML)
Após o título "📁 Categorias" no card, adicionar um `div.rule-help` similar ao das Regras:

```html
<div class="rule-help">
    <p>Quando uma transação contém a <strong>palavra-chave</strong>, ela é automaticamente classificada
        na categoria correspondente.</p>
</div>
```

**Nota:** Esta descrição será reutilizada das regras, pois o conceito é o mesmo.

### 2. Corrigir CSS do Form-Row (style.css)
Remover ou condicionar o CSS que força column:
- Linhas 1396-1406: `.form-row { flex-direction: column; }` deve ser removido ou condicionada a telas muito pequenas

### 3. Ajustar Dimensões dos Elementos (category_manage.html)
Modificar o template para ter elementos quadrados:

| Elemento | Largura | Altura |
|----------|---------|--------|
| Seletor Ícone | 50px | 50px (quadrado) |
| Input Descrição | flex: 1 (wide) | 50px |
| Seletor Cor | 50px | 50px (quadrado) |
| Botão + | 50px | 50px (quadrado) |

### 4. Estilos CSS Adicionais (style.css)
Adicionar estilos específicos para os inputs do form de categoria:

```css
/* Inputs de categoria com dimensões quadradas */
.category-form-square {
    width: 50px;
    height: 50px;
    padding: 8px;
    text-align: center;
    flex-shrink: 0;
}

.category-form-wide {
    flex: 1;
    min-width: 200px;
}
```

## Arquivos a Modificar
1. `invoices/templates/invoices/category_manage.html` - HTML
2. `invoices/static/css/style.css` - CSS

## ordem de Implementação
- [ ] 1. Adicionar descrição rule-help após título Categorias
- [ ] 2. Corrigir CSS .form-row (remover column forçado)
- [ ] 3. Adicionar classes CSS para elementos quadrados
- [ ] 4. Aplicar classes CSS no template
- [ ] 5. Validar visualmente

## Resultado Esperado
- Título "📁 Categorias" com descrição informativa abaixo
- Seletor de ícone: quadrado (50x50)
- Input descrição: wide (ocupa espaço restante)
- Seletor cor: quadrado (50x50) 
- Botão +: quadrado (50x50)
- Tudo alinhado na mesma linha (inline)
