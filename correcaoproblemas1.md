# Correcao de Problemas #1 — Humanizacao do Worker

**Data:** 2026-03-29
**Branch:** feature/pyside6-migration

---

## Problemas Reportados

1. **Scroll robótico** — `window.scrollBy` instantâneo + snap-to-center após CADA scroll cria padrão detectável
2. **Likes em perfis sem abrir post** — clica like direto na timeline, fluxo deveria ser: perfil → scroll → abrir post → ler → curtir → voltar
3. **Comentários bugados** — pausa 0.5s (muito rápido), lê até 8 comentários, não volta pro post original
4. **Post errado aberto** — abre post que não está centralizado/visível na tela
5. **Sem scroll pra cima** — sempre desce, nunca sobe (comportamento não-humano)

---

## Solucoes Planejadas

### 1. Smooth Scroll (`utils/humanizer.py`)
- Nova funcao `smooth_scroll(driver, total_px, direction)`: scroll incremental via JS setInterval
  - Steps de 20-60px com intervalo de 30-80ms (simula mouse wheel)
  - Cap de 1500px; acima disso, pulo rapido + smooth nos ultimos 500px
- Nova funcao `smooth_scroll_to_element(driver, element)`: centraliza elemento no viewport

### 2. Feed Browsing (`workers/actions/browse_feed.py`)
- Trocar `window.scrollBy` por `smooth_scroll` em todos os behaviors
- Snap-to-nearest-tweet: reduzir de 100% para ~30% das vezes
- Novo behavior "scroll_up" com ~5% de chance
- Post centering: `smooth_scroll_to_element` + pausa 0.5-1.5s ANTES de clicar
- Comentarios:
  - Pausa entre comentarios: 0.5s → 1.5-3.0s
  - Max comentarios: 3-8 → 2-5
  - Comment read time: 2-6s → 3-8s
  - Scroll back to top ao sair dos comentarios
  - Remover snap dentro do loop de comentarios

### 3. Profile Likes (`workers/twitter_worker.py`)
- `_execute_likes_on_profiles()` REESCRITO:
  - Encontrar tweet → smooth_scroll_to_element → pausa 1-3s
  - Clicar pra abrir post → esperar load → ler 3-8s
  - Dar like DENTRO do post aberto → voltar ao perfil
- `_scroll_naturally()` e `_scroll_profile()`: usar smooth_scroll + 10% scroll up
- `_execute_likes()`: trocar scrollIntoView por smooth_scroll_to_element

### 4. Config Defaults (`utils/config.py`)
- `comment_read_time_min`: 2.0 → 3.0
- `comment_read_time_max`: 6.0 → 8.0

---

## Arquivos Modificados
1. `utils/humanizer.py` — smooth_scroll + smooth_scroll_to_element
2. `utils/config.py` — comment read time defaults
3. `workers/actions/browse_feed.py` — scroll, snap, centering, comentarios
4. `workers/twitter_worker.py` — profile likes, scroll methods

---

## Verificacao
- [ ] Scroll suave (nao instantaneo)
- [ ] Snap so ~30% das vezes
- [ ] Scroll up ocasional
- [ ] Likes em perfil abrem o post primeiro
- [ ] Comentarios: max 2-5, pausas reais, volta pro post
- [ ] Post correto centralizado antes de abrir
