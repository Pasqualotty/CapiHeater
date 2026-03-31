# CapiHeater - Manual do Usuario

## O que e o CapiHeater?

O CapiHeater e um software de aquecimento de contas do Twitter/X. Ele automatiza acoes como curtir, seguir, retweetar e navegar pelo feed de forma natural, simulando o comportamento de um usuario real. O objetivo e aquecer contas novas ou inativas gradualmente, evitando suspensoes.

---

## Instalacao

1. Baixe o arquivo **CapiHeater.exe**
2. Salve em qualquer pasta do seu computador
3. Clique duas vezes para executar
4. Se o Windows bloquear, clique com o botao direito no arquivo > **Propriedades** > marque **Desbloquear** > **OK**

> **Nao precisa instalar nada alem do .exe.** Nao precisa de Python, bibliotecas ou qualquer outro programa.

---

## Primeiro Acesso

### Passo 1 — Criar Conta

1. Abra o CapiHeater
2. Na tela de login, preencha seu **e-mail** e uma **senha**
3. Clique em **"Ainda nao tem conta? Registrar"**
4. Uma mensagem de sucesso vai aparecer
5. **Aguarde** — um administrador precisa liberar seu acesso

### Passo 2 — Aguardar Liberacao

- Apos o registro, sua conta fica **inativa**
- Um administrador vai liberar seu acesso pelo painel Admin
- Quando liberado, voce consegue fazer login normalmente

### Passo 3 — Fazer Login

1. Digite seu **e-mail** e **senha**
2. Marque **"Lembrar de mim"** se quiser entrar automaticamente nas proximas vezes
3. Clique em **Entrar**

---

## Visao Geral das Abas

O CapiHeater tem 7 abas principais:

| Aba | O que faz |
|-----|-----------|
| **Dashboard** | Visao geral das contas e controles de iniciar/parar |
| **Contas** | Gerenciar contas do Twitter (adicionar, editar, excluir) |
| **Alvos** | Gerenciar perfis alvo que o bot vai interagir |
| **Cronogramas** | Configurar o plano diario de acoes |
| **Logs** | Ver historico de todas as acoes realizadas |
| **Configuracoes** | Ajustes gerais do programa |
| **Admin** | Gerenciar usuarios do sistema (so para administradores) |

---

## Fluxo de Uso — Passo a Passo

Siga esta ordem para configurar tudo corretamente:

### 1. Adicionar Alvos (aba Alvos)

Os alvos sao os perfis do Twitter que o bot vai visitar para curtir e seguir.

1. Va na aba **Alvos**
2. Clique em **Adicionar Alvo**
3. Digite o **nome de usuario** do perfil (sem @)
4. A URL sera preenchida automaticamente
5. Escolha a **prioridade**: Baixa, Media ou Alta
6. Clique em **Salvar**

**Repita para cada perfil alvo.** Recomendamos adicionar pelo menos 5 a 10 alvos.

**Funcoes da aba Alvos:**
- **Adicionar Alvo** — cadastra um novo perfil alvo
- **Editar** — altera os dados de um alvo selecionado
- **Excluir** — remove alvos selecionados (aceita selecao multipla com Ctrl+Clique)
- **Alternar Ativo** — ativa/desativa alvos selecionados sem excluir
- **Abrir Perfil** — abre o perfil no navegador (duplo clique tambem funciona)
- **Ctrl+A** — seleciona todos os alvos
- **Clique direito** — menu de contexto com todas as opcoes

---

### 2. Escolher ou Criar Cronograma (aba Cronogramas)

O cronograma define quantas acoes o bot faz por dia e como ele se comporta.

**Templates disponiveis:**

| Template | Duracao | Risco | Descricao |
|----------|---------|-------|-----------|
| **Padrao** | 14 dias | Medio | Crescimento equilibrado |
| **Conservador** | 21 dias | Baixo | Crescimento lento, mais seguro |
| **Agressivo** | 7 dias | Alto | Crescimento rapido, mais arriscado |

**Para editar um dia do cronograma:**

1. Selecione o cronograma no dropdown
2. De um **duplo clique** no dia que quer editar
3. Configure os campos:

**Secao Acoes:**
- **Likes** — quantas curtidas por dia
- **Likes coment.** — quantas curtidas em comentarios de posts alvo por dia
- **Follows** — quantos perfis seguir por dia
- **Retweets** — quantos retweets por dia
- **Unfollows** — quantos perfis deixar de seguir por dia

**Secao Navegar pelo Feed (segundos):**
- **Antes das acoes (Min/Max)** — tempo em segundos que o bot navega pelo feed ANTES de comecar as acoes. Exemplo: Min 120, Max 300 = navega entre 2 e 5 minutos
- **Entre as acoes (Min/Max)** — tempo em segundos que o bot navega pelo feed ENTRE cada bloco de acoes (entre likes e follows, entre follows e retweets, etc.)

**Secao Comportamento:**
- **Abrir postagens** — quantos posts o bot vai clicar para abrir e "ler" durante a navegacao
- **Ver comentarios (%)** — chance de rolar ate os comentarios quando abrir um post (0-100%)
- **Curtir no feed** — se marcado, curte posts no feed inicial. Se desmarcado, curte diretamente nos perfis alvo
- **Likes/alvo (coment.)** — maximo de comentarios a curtir por perfil alvo visitado (default: 3)
- **Pular coment. (%)** — chance de pular um comentario sem curtir, para humanizacao (default: 25%)
- **Follows iniciais** — quantidade extra de follows feitos desde o dia 1, ideal para contas novas que precisam seguir gente para montar um feed

**Outros botoes:**
- **Novo Cronograma** — cria um cronograma do zero
- **Duplicar** — copia um cronograma existente para customizar
- **Adicionar Dia** — adiciona um novo dia ao final do cronograma
- **Remover Dia** — remove o dia selecionado
- **Excluir Cronograma** — exclui o cronograma inteiro (nao pode excluir se alguma conta estiver usando)

---

### 3. Adicionar Conta do Twitter (aba Contas)

Para adicionar uma conta do Twitter ao programa, voce precisa dos **cookies** da conta.

**Como exportar cookies:**

1. Faca login na conta do Twitter no navegador
2. Use uma extensao de cookies (como "Cookie Editor" ou "EditThisCookie")
3. Exporte os cookies em formato **JSON**
4. Salve o arquivo `.json` no seu computador

**Como adicionar a conta:**

1. Va na aba **Contas**
2. Clique em **Adicionar Conta**
3. Digite o **nome de usuario** (sem @)
4. Clique em **Importar Cookies** e selecione o arquivo `.json`
5. (Opcional) Configure um **proxy** se necessario
6. Escolha o **cronograma** que essa conta vai usar
7. Clique em **Salvar**

**Funcoes da aba Contas:**
- **Adicionar Conta** — cadastra uma nova conta do Twitter
- **Editar** — altera configuracoes de uma conta
- **Excluir** — remove a conta do programa
- **Importar Cookies** — importa cookies de um arquivo JSON ou TXT (formato Netscape)

> **Importante:** Os cookies expiram com o tempo. Se o bot parar de funcionar em uma conta, exporte novos cookies e atualize.

---

### 4. Iniciar o Aquecimento (aba Dashboard)

Depois de configurar alvos, cronograma e contas, e hora de iniciar.

1. Va na aba **Dashboard**
2. Voce vera suas contas listadas com status "Parado"
3. Selecione uma conta e clique em **Iniciar Selecionada**, ou clique em **Iniciar Todos**
4. O status muda para **Rodando** (verde)
5. O bot vai abrir o navegador e comecar as acoes

**Status possiveis:**
- **Parado** (cinza) — conta nao esta rodando
- **Rodando** (verde) — bot esta executando acoes
- **Pausado** (amarelo) — bot esta pausado temporariamente
- **Erro** (vermelho) — algo deu errado (verifique os logs)
- **Concluido** (azul) — acoes do dia foram completadas

**Botoes de controle:**
- **Iniciar Todos** — inicia todas as contas de uma vez
- **Parar Todos** — para todas as contas
- **Atualizar** — atualiza as informacoes na tela
- **Iniciar Selecionada** — inicia apenas a conta selecionada
- **Pausar Selecionada** — pausa a conta selecionada
- **Parar Selecionada** — para a conta selecionada

---

### 5. Acompanhar os Resultados (aba Logs)

A aba Logs mostra tudo que o bot fez.

**Colunas:**
- **Data/Hora** — quando a acao aconteceu
- **Conta** — qual conta executou a acao
- **Acao** — tipo de acao (like, like_comment, follow, retweet, unfollow)
- **Alvo** — perfil alvo da acao
- **Status** — se deu certo (success), falhou (failed) ou foi pulado (skipped)
- **Erro** — mensagem de erro (se houver)

**Filtros:**
- **Conta** — filtrar por conta especifica
- **Acao** — filtrar por tipo de acao (like, follow, etc.)
- **Status** — filtrar por resultado (success, failed, etc.)
- **Atualizar automaticamente** — atualiza os logs a cada 5 segundos
- **Limpar Logs** — apaga todos os logs (com confirmacao)

---

## Configuracoes (aba Configuracoes)

- **Workers simultaneos** — quantas contas podem rodar ao mesmo tempo (padrao: 3)
- **Modo headless** — rodar o navegador sem janela visivel
- **Proxy padrao** — proxy a ser usado por padrao em novas contas
- **Nivel de log** — quantidade de detalhes nos logs (DEBUG, INFO, WARNING, ERROR)

---

## Painel Admin (aba Admin)

> Visivel apenas para administradores e moderadores.

**O que faz:**
- Lista todos os usuarios registrados no sistema
- Mostra email, papel (role), status (ativo/inativo), data de ativacao

**Acoes:**
- **Liberar Acesso** — digita o email de um usuario registrado e ativa sua licenca
- **Revogar Acesso** — seleciona um usuario e desativa sua licenca
- **Atualizar** — recarrega a lista de usuarios

**Filtros:**
- **Todos** — mostra todos os usuarios
- **Ativos** — mostra apenas usuarios com acesso ativo
- **Inativos** — mostra apenas usuarios sem acesso
- **Liberados Manualmente** — mostra usuarios que foram liberados por um admin/moderador

---

## Funcoes Extras

### Sair da Conta
- Clique em **"Sair da Conta"** no canto inferior direito
- Remove as credenciais salvas (lembrar de mim)
- Fecha o programa
- Na proxima abertura, pede login novamente

### Atualizacao Automatica
- O programa verifica automaticamente se ha uma versao nova
- Se houver, uma mensagem aparece perguntando se deseja atualizar
- Se aceitar, o programa baixa e instala a nova versao automaticamente

---

## O que o Bot faz em cada Dia

Quando voce inicia uma conta, o bot executa nesta ordem:

1. **Abre o navegador** e faz login com os cookies
2. **Navega pelo feed** pelo tempo configurado (antes das acoes)
   - Rola o feed naturalmente
   - Para com posts centralizados
   - Abre e le postagens (se configurado)
   - Ve comentarios em alguns posts (se configurado)
3. **Executa as curtidas** (no feed ou nos perfis alvo, conforme configurado)
4. **Curte comentarios** em posts de alvos ja seguidos (se configurado)
5. **Navega pelo feed** novamente (entre as acoes)
6. **Segue os perfis alvo** configurados
7. **Navega pelo feed** novamente (entre as acoes)
8. **Faz retweets** no feed
9. **Navega pelo feed** novamente (entre as acoes)
10. **Faz unfollows** se configurado
11. **Fecha o navegador** e marca como concluido

O dia seguinte, o programa automaticamente avanca para o proximo dia do cronograma com mais acoes.

---

## Tratamento de Problemas

O bot detecta e trata automaticamente:

| Situacao | O que acontece |
|----------|----------------|
| **Perfil com conteudo sensivel** | Clica em "Sim, ver perfil" automaticamente |
| **Perfil nao encontrado (404)** | Pula o alvo e registra nos logs |
| **Conta suspensa** | Pula o alvo e registra nos logs |
| **Cookies expirados** | Mostra erro — exporte novos cookies |

---

## Dicas de Uso

1. **Comece pelo cronograma Conservador** se for uma conta muito nova — e mais seguro
2. **Adicione pelo menos 5-10 alvos** para ter variedade
3. **Use "Follows iniciais" = 2-3** em contas novas para construir o feed
4. **Configure navegacao pelo feed antes das acoes** (120-300 segundos) para parecer natural
5. **Nao rode mais de 3 contas ao mesmo tempo** no mesmo computador
6. **Verifique os logs regularmente** para identificar problemas
7. **Atualize os cookies** se o bot parar de conseguir fazer login
8. **Nao mexa no navegador** enquanto o bot estiver rodando — deixe ele trabalhar

---

## Problemas Comuns

| Problema | Solucao |
|----------|---------|
| "Licenca nao ativa" | Aguarde um admin liberar seu acesso |
| Bot nao abre o navegador | Verifique se o Google Chrome esta instalado |
| Bot nao faz login | Cookies expiraram — exporte novos |
| Windows bloqueou o .exe | Botao direito > Propriedades > Desbloquear |
| Conta nao aparece no Dashboard | Clique em "Atualizar" ou troque de aba e volte |
| Follows nao funcionam | Verifique se os alvos estao ativos na aba Alvos |
| Erro ao iniciar | Verifique os logs na aba Logs para mais detalhes |

---

## Resumo do Fluxo

```
1. Baixar o CapiHeater.exe
2. Abrir e criar conta (Registrar)
3. Aguardar admin liberar acesso
4. Fazer login
5. Adicionar alvos (aba Alvos)
6. Configurar cronograma (aba Cronogramas)
7. Adicionar conta do Twitter com cookies (aba Contas)
8. Iniciar aquecimento (aba Dashboard)
9. Acompanhar resultados (aba Logs)
```
