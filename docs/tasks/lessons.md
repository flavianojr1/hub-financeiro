# Aprendizados (Lessons Learned)

- **Condicionais em Templates Django**: Nunca use blocos lógicos (`{% if ... %}`) como atributos inline dentro de tags HTML (ex: `<button {% if condicao %}disabled{% endif %}>`). Formatadores de código podem deletar ou adicionar espaços indevidos ao redor dos operadores e quebrar o parser do Django, resultando em erros fatais (500) do tipo `TemplateSyntaxError`. A solução correta é **isolar o bloco condicional** copiando o elemento HTML por inteiro dentro do IF e do ELSE (ex: `{% if condicao %} <button disabled> {% else %} <button> {% endif %}`).
