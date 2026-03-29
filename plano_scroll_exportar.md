# Plano: Novos Modos de Scroll + Exportar/Importar Cronogramas

**Data:** 2026-03-29
**Branch:** feature/pyside6-migration

---

## Feature 1: Novos Presets de Scroll

### Presets atuais: Lento, Normal, Rapido
### Novos: Super Rapido (+50% velocidade), Ultra Rapido (2x velocidade)

**Arquivo:** `utils/config.py` — 2 novos dicts no SCROLL_PRESETS

**"Super Rapido"** (1.5x do Rapido):
- Scroll: small 450-825px, medium 900-1500px, large 1650-2700px
- Pausa: small 0.5-1.2s, medium 0.4-0.9s, large 0.3-0.8s
- Leitura: post 2.0-6.7s, comment 1.0-2.7s
- Pesos: small 18%, medium 30%, large 24%, pause_read 18%, distracted 5%, scroll_up 5%
- Distracted: 2.0-5.0s, Hover: 5%

**"Ultra Rapido"** (2x do Rapido):
- Scroll: small 600-1100px, medium 1200-2000px, large 2200-3600px
- Pausa: small 0.4-0.9s, medium 0.3-0.6s, large 0.2-0.5s
- Leitura: post 1.5-5.0s, comment 0.8-2.0s
- Pesos: small 10%, medium 28%, large 30%, pause_read 18%, distracted 4%, scroll_up 10%
- Distracted: 1.5-4.0s, Hover: 3%

**GUI (automatico):** `gui/settings_tab.py` lê de SCROLL_PRESETS.keys() — sem mudança no código.

**GUI (hardcoded):** `gui/accounts_tab.py` — adicionar "Super Rapido" e "Ultra Rapido" nos 2 comboboxes:
- `_open_account_form()` linha ~385: scroll_preset_names
- `_open_bulk_edit_form()` linha ~560: scroll_options

---

## Feature 2: Exportar/Importar Cronogramas

### Formato JSON:
```json
{
  "capiheater_schedule": true,
  "version": 1,
  "name": "Nome do Cronograma",
  "description": "Descricao",
  "days": [ { "day": 1, "likes": 3, ... }, ... ]
}
```

### Exportar (`gui/schedule_tab.py`)
- Novo botao "Exportar" na toolbar
- `QFileDialog.getSaveFileName(filter="JSON (*.json)")`
- Monta JSON com envelope + days do cronograma selecionado
- Salva no arquivo

### Importar (`gui/schedule_tab.py`)
- Novo botao "Importar" na toolbar
- `QFileDialog.getOpenFileName(filter="JSON (*.json)")`
- Lê e valida: aceita envelope OU array puro de dias
- `QInputDialog.getText` pra nome (sugere nome do arquivo ou do envelope)
- INSERT no banco, refresh lista

### Validacao:
- Cada dia precisa de: `day`, `likes`, `follows`, `retweets`, `unfollows`
- Campos faltando preenchidos com defaults (0 ou False)

---

## Arquivos Modificados
1. `utils/config.py` — 2 novos presets
2. `gui/accounts_tab.py` — nomes nos comboboxes (2 locais)
3. `gui/schedule_tab.py` — botoes Exportar/Importar + metodos

## Checklist
- [ ] Super Rapido e Ultra Rapido aparecem em Configuracoes
- [ ] Super Rapido e Ultra Rapido aparecem no form de conta e bulk edit
- [ ] Exportar gera JSON valido
- [ ] Importar com envelope funciona
- [ ] Importar array puro de dias funciona
- [ ] Cronograma importado aparece na lista
