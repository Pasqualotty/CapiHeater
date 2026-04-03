"""
DocsTab - Built-in documentation viewer for CapiHeater.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QLabel,
    QListWidget,
    QSplitter,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from gui.base import BaseTab
from gui.theme import BG_INPUT, BG_SECONDARY, FG_TITLE


# ======================================================================
# Documentation content (PT-BR)
# ======================================================================

DOCS = [
    {
        "title": "Visao Geral",
        "content": (
            "O CapiHeater e uma ferramenta de aquecimento automatizado de contas Twitter/X. "
            "Ele simula comportamento humano (curtidas, follows, retweets, unfollow e navegacao "
            "pelo feed) de forma gradual para aumentar a atividade das contas sem levantar "
            "suspeitas.\n\n"
            "O programa opera com cronogramas personalizaveis que definem quantas acoes serao "
            "executadas por dia, escalando progressivamente ao longo de varios dias.\n\n"
            "RECURSOS PRINCIPAIS:\n"
            "  - Aquecimento automatizado com cronogramas progressivos\n"
            "  - Likes, follows, retweets e unfollows no feed ou em perfis alvos\n"
            "  - Curtir comentarios em posts de contas alvo (v1.4)\n"
            "  - Navegacao natural pelo feed com abertura de posts e comentarios\n"
            "  - Sistema de categorias para organizar contas e alvos\n"
            "  - Pesquisa rapida por nome em contas, alvos e cronogramas\n"
            "  - Selecao multipla com acoes em massa\n"
            "  - Perfil de rolagem configuravel por conta\n"
            "  - Proxy por conta ou global\n"
            "  - Atualizacao automatica integrada\n"
            "  - Painel admin para gerenciar licencas\n"
            "  - Teste de proxy integrado (HTTP e SOCKS5)\n"
            "  - Verificacao visual de IP do proxy ao iniciar conta\n"
            "  - Exportar e importar cronogramas e alvos via JSON\n"
            "  - 5 perfis de rolagem: Lento, Normal, Rapido, Super Rapido, Ultra Rapido\n"
            "  - Scroll humanizado que simula comportamento real de mouse\n"
            "  - Curtidas em perfis abrem o post antes de curtir\n"
            "  - Horario local nos logs (DD/MM/YYYY)\n"
            "  - SFS (Shoutout For Shoutout): sessoes de interacao mútua entre contas\n"
            "  - Delays SFS configuráveis: Slow (20-35s), Normal (10-20s), Fast (5-10s)\n"
            "  - Links de alvos aceitam qualquer formato (sem https://, twitter.com, @usuario)\n"
            "  - Tabelas ordenáveis: clique no cabeçalho de qualquer coluna para ordenar\n"
            "  - Dropdowns de contas pesquisáveis (digitar para filtrar)\n"
            "  - Edição em massa de categorias para múltiplos alvos"
        ),
    },
    {
        "title": "1. Login e Autenticacao",
        "content": (
            "Ao abrir o CapiHeater, a tela de login e exibida.\n\n"
            "CAMPOS:\n"
            "  - E-mail: seu e-mail de cadastro\n"
            "  - Senha: sua senha\n"
            "  - Lembrar de mim: salva as credenciais localmente (criptografadas)\n\n"
            "BOTOES:\n"
            "  - Entrar: autentica com as credenciais informadas\n"
            "  - Registrar (link): cria uma nova conta\n\n"
            "NOTAS:\n"
            "  - Se 'Lembrar de mim' estiver ativo, o login e feito automaticamente\n"
            "  - Apos o login, a licenca e verificada. Se inativa, o acesso e bloqueado\n"
            "  - O botao 'Sair da Conta' na barra inferior faz logout e limpa credenciais salvas\n"
            "  - Contas que estavam rodando sao automaticamente resetadas para 'Parado'\n"
            "    ao reabrir o app (evita contas travadas)"
        ),
    },
    {
        "title": "2. Dashboard",
        "content": (
            "A aba principal que mostra o panorama geral de todas as contas.\n\n"
            "CARDS DE RESUMO (topo):\n"
            "  - Total de Contas: numero total de contas cadastradas\n"
            "  - Rodando: contas atualmente em execucao\n"
            "  - Pausadas: contas pausadas pelo usuario\n"
            "  - Erros: contas que encontraram erro\n\n"
            "FILTROS DE STATUS:\n"
            "  - Todas: mostra todas as contas\n"
            "  - A aquecer: contas aguardando inicio (idle)\n"
            "  - Em Aquecimento: contas em processo de aquecimento\n"
            "  - Erro: contas que deram problema\n"
            "  - Concluido: contas que terminaram o ciclo\n\n"
            "LISTA DE CONTAS:\n"
            "  Exibe todas as contas com colunas: Conta, Status, Dia, Ultimo Aquecimento\n"
            "  Indicadores coloridos de status:\n"
            "    - Verde: rodando\n"
            "    - Amarelo: pausada\n"
            "    - Vermelho: erro\n"
            "    - Cinza: a aquecer (idle)\n"
            "    - Azul: concluida\n\n"
            "BOTOES GLOBAIS:\n"
            "  - Iniciar Todos: inicia o aquecimento de todas as contas\n"
            "  - Parar Todos: para todas as contas em execucao\n"
            "  - Atualizar: recarrega os dados da tela\n\n"
            "SELECAO MULTIPLA (abaixo da lista):\n"
            "  - Iniciar Selecionadas: inicia as contas selecionadas\n"
            "  - Pausar Selecionadas: pausa as contas selecionadas\n"
            "  - Parar Selecionadas: para as contas selecionadas\n"
            "  - Ctrl+A: seleciona todas as contas\n"
            "  - Ctrl+clique / Shift+clique: selecao multipla\n\n"
            "MENU DE CONTEXTO (clique direito):\n"
            "  - Iniciar / Pausar / Parar\n"
            "  - Editar Dia: altera em qual dia do cronograma a conta esta"
        ),
    },
    {
        "title": "3. Contas",
        "content": (
            "Aba de gerenciamento de contas Twitter/X que serao aquecidas.\n\n"
            "PESQUISA:\n"
            "  Barra de pesquisa no topo filtra contas por @username em tempo real.\n"
            "  Botao 'Limpar' reseta o filtro.\n\n"
            "TABELA:\n"
            "  Colunas: Usuario, Status, Cronograma, Categoria, Dia, Proxy, Data Inicio\n"
            "  Clique no cabecalho de qualquer coluna para ordenar (asc/desc).\n"
            "  Ordenacao inteligente: numeros, datas e texto sao ordenados corretamente.\n"
            "  O cursor muda para mao nos cabecalhos clicaveis.\n\n"
            "SELECAO MULTIPLA:\n"
            "  - Ctrl+clique: seleciona varias contas individualmente\n"
            "  - Shift+clique: seleciona intervalo\n"
            "  - Ctrl+A: seleciona todas\n"
            "  - Acoes em massa: Excluir, Reiniciar Cronograma, Importar Cookies\n"
            "    operam em todas as contas selecionadas de uma vez\n\n"
            "MENU DE CONTEXTO (clique direito):\n"
            "  - Abrir Perfil: abre o perfil no navegador (multi-select)\n"
            "  - Editar: abre formulario de edicao\n"
            "  - Importar Cookies: importa cookies para as contas selecionadas\n"
            "  - Alternar Ativo: pausa/ativa as contas selecionadas\n"
            "  - Reiniciar Cronograma: volta pro dia 1\n"
            "  - Excluir Selecionados: remove as contas\n"
            "  - Selecionar Todos\n"
            "  - Duplo clique: abre perfil no navegador\n\n"
            "BOTOES DA TOOLBAR:\n"
            "  - Adicionar Conta: abre formulario para nova conta\n"
            "  - Editar: edita a conta selecionada\n"
            "  - Excluir: remove contas selecionadas\n"
            "  - Importar Cookies: importa cookies de arquivo\n"
            "  - Importar em Massa: importa varias contas de uma vez\n"
            "  - Reiniciar Cronograma: reseta o dia e limpa historico\n"
            "  - Categorias: gerencia categorias (criar/excluir)\n\n"
            "FORMULARIO DE CONTA (organizado em abas):\n"
            "  Aba Conta: usuario (sem @) e notas\n"
            "  Aba Conexao: arquivo de cookies (.json/.txt) e proxy (socks5/http)\n"
            "  Aba Cronograma: cronograma a usar e perfil de rolagem\n"
            "  Aba Categorias: selecao multipla de categorias (Ctrl+clique)\n"
            "  Aba Extras: reservada para configuracoes futuras\n"
            "  - Testar Proxy: botao que testa a conexao do proxy configurado\n"
            "    Mostra o IP do proxy em verde (sucesso) ou erro em vermelho\n\n"
            "IMPORTACAO EM MASSA:\n"
            "  - Selecione multiplos arquivos .json de cookies\n"
            "  - O nome do arquivo vira o username da conta\n"
            "  - Ex: arquivo 'minhaconta.json' cria conta @minhaconta\n"
            "  - Contas duplicadas sao ignoradas automaticamente\n\n"
            "FORMATOS DE COOKIES ACEITOS:\n"
            "  - JSON: array de objetos com campos domain, name, value, etc.\n"
            "  - Netscape TXT: formato padrao de cookies de navegador (tab-separated)"
        ),
    },
    {
        "title": "4. Alvos",
        "content": (
            "Aba para gerenciar perfis-alvo com os quais suas contas interagirao.\n\n"
            "PESQUISA:\n"
            "  Barra de pesquisa filtra alvos por @username em tempo real.\n"
            "  Mostra 'X/Y alvos encontrados' quando filtro esta ativo.\n\n"
            "TABELA:\n"
            "  Colunas: Usuario, URL, Prioridade, Categoria, Ativo\n"
            "  Clique no cabecalho de qualquer coluna para ordenar (asc/desc).\n\n"
            "BOTOES:\n"
            "  - Adicionar Alvo: formulario para adicionar um alvo\n"
            "  - Adicionar em Massa: adiciona varios alvos de uma vez\n"
            "  - Editar: edita alvo selecionado\n"
            "  - Excluir: exclui alvo(s) selecionado(s)\n"
            "  - Alternar Ativo: ativa/desativa alvo sem excluir\n"
            "  - Abrir Perfil: abre o perfil no navegador padrao\n"
            "  - Categorias: gerencia categorias\n"
            "  - Exportar: salva todos os alvos como arquivo JSON\n"
            "    Inclui username, URL, prioridade, status ativo e categorias\n"
            "  - Importar: carrega alvos de um arquivo JSON\n"
            "    Aceita formato exportado pelo CapiHeater ou array de alvos\n"
            "    Duplicados sao ignorados automaticamente\n"
            "    Categorias inexistentes sao criadas automaticamente\n\n"
            "FORMULARIO DE ALVO:\n"
            "  - Usuario alvo (sem @)\n"
            "  - URL do perfil: preenchida automaticamente como https://x.com/{usuario}\n"
            "  - Prioridade: Baixa, Media ou Alta\n"
            "  - Categorias: selecao multipla (Ctrl+clique)\n\n"
            "ADICIONAR EM MASSA:\n"
            "  Cole links ou usernames, um por linha. Formatos aceitos:\n"
            "    - https://x.com/usuario\n"
            "    - https://twitter.com/usuario\n"
            "    - x.com/usuario (sem https://)\n"
            "    - twitter.com/usuario\n"
            "    - @usuario\n"
            "    - usuario\n"
            "  Links com letras maiusculas e qualquer variacao sao normalizados automaticamente.\n"
            "  Selecione prioridade e multiplas categorias para todos os importados.\n\n"
            "EDICAO EM MASSA DE CATEGORIAS (v1.9.4):\n"
            "  - Selecione multiplos alvos (Ctrl+clique ou Ctrl+A)\n"
            "  - Clique em 'Editar'\n"
            "  - Escolha as categorias para aplicar a todos os selecionados de uma vez\n\n"
            "ATALHOS:\n"
            "  - Duplo clique: abre perfil no navegador\n"
            "  - Ctrl+A: seleciona todos\n"
            "  - Clique direito: menu de contexto (Abrir, Editar, Excluir, etc.)\n"
            "  - Selecao multipla: Ctrl+clique ou Shift+clique"
        ),
    },
    {
        "title": "5. Cronogramas",
        "content": (
            "Aba para configurar os planos de aquecimento dia a dia.\n\n"
            "PESQUISA:\n"
            "  Barra de pesquisa filtra cronogramas por nome no dropdown.\n\n"
            "CRONOGRAMAS PRE-DEFINIDOS:\n"
            "  - Padrao (14 dias): crescimento moderado e seguro\n"
            "  - Conservador (21 dias): crescimento lento, mais browsing, menor risco\n"
            "  - Agressivo (7 dias): crescimento rapido, maior risco\n\n"
            "TABELA:\n"
            "  Colunas: Dia, Likes, Likes Coment., Follows, Retweets, Unfollows,\n"
            "           Feed Antes (seg), Feed Entre (seg), Abrir Posts\n\n"
            "BOTOES:\n"
            "  - Novo Cronograma: cria um cronograma vazio com nome e descricao\n"
            "  - Duplicar: copia o cronograma atual com novo nome\n"
            "  - Editar Dia: edita as configuracoes do dia selecionado\n"
            "  - Adicionar Dia: adiciona novo dia ao final do cronograma\n"
            "  - Duplicar Dia: duplica o dia selecionado (insere logo apos)\n"
            "  - Remover Dia: remove o dia selecionado (renumera automaticamente)\n"
            "  - Excluir Cronograma: exclui o cronograma inteiro\n"
            "    (nao permite excluir se contas estiverem usando)\n"
            "  - Exportar: salva o cronograma selecionado como arquivo JSON\n"
            "    O arquivo contem nome, descricao e todos os dias do cronograma\n"
            "    Util para backup ou compartilhar com outros usuarios\n"
            "  - Importar: carrega um cronograma de um arquivo JSON\n"
            "    Aceita o formato exportado pelo CapiHeater ou array puro de dias\n"
            "    Pede um nome para o cronograma importado\n\n"
            "EDITAR DIA (organizado em abas):\n"
            "  Aba Acoes:\n"
            "    - Likes: quantidade de curtidas no dia\n"
            "    - Likes coment.: quantidade de curtidas em comentarios de posts alvos\n"
            "    - Follows: quantidade de follows no dia\n"
            "    - Retweets: quantidade de retweets no dia\n"
            "    - Unfollows: quantidade de unfollows no dia\n"
            "    (todos variam automaticamente em +/-20%% para simular comportamento humano)\n\n"
            "  Aba Feed:\n"
            "    - Antes das acoes: tempo min/max de navegacao antes de executar acoes\n"
            "    - Entre as acoes: tempo min/max de navegacao entre blocos de acoes\n"
            "    Ex: Antes 120-300 seg = navega entre 2 a 5 minutos antes de comecar\n\n"
            "  Aba Comportamento:\n"
            "    - Abrir postagens: quantidade de posts para abrir e ler durante navegacao\n"
            "    - Ver comentarios (%%): chance percentual de abrir comentarios dos posts\n"
            "    - Curtir no feed: se ativo, curtidas no feed. Se desativado, curtidas nos perfis alvos\n"
            "    - RT no feed: se ativo, retweets no feed. Se desativado, retweets nos perfis alvos\n"
            "    - Likes/alvo (coment.): max de comentarios a curtir por perfil alvo visitado\n"
            "    - Pular coment. (%%): chance de pular um comentario sem curtir (humanizacao)\n"
            "    - Follows iniciais: follows feitos logo apos login, antes de navegar\n\n"
            "DICA: clique duplo em um dia para editar rapidamente"
        ),
    },
    {
        "title": "6. Logs",
        "content": (
            "Aba para visualizar o historico de todas as acoes executadas.\n\n"
            "TABELA:\n"
            "  Colunas: Data/Hora, Conta, Acao, Alvo, Status, Erro\n"
            "  Cores de status:\n"
            "    - Verde: sucesso\n"
            "    - Vermelho: falha\n"
            "    - Amarelo: ignorado/pulado\n\n"
            "FILTROS:\n"
            "  - Conta: dropdown pesquisavel — digite para filtrar por nome (v1.9.4)\n"
            "    Contas em ordem alfabetica. Selecione 'Todas' para ver todas.\n"
            "  - Acao: like, like_comment, follow, retweet, unfollow, login, browse, sistema\n"
            "  - Status: success, failed, skipped\n\n"
            "BOTOES:\n"
            "  - Atualizar: recarrega os logs com filtros aplicados\n"
            "  - Limpar Logs: apaga TODOS os logs (irreversivel, pede confirmacao)\n\n"
            "OPCAO:\n"
            "  - Atualizar automaticamente: JA VEM LIGADO por padrao\n"
            "    Recarrega logs a cada 5 segundos\n\n"
            "FORMATO:\n"
            "  - Horario local (fuso horario do seu computador)\n"
            "  - Formato: DD/MM/YYYY HH:MM:SS\n\n"
            "CONTAGEM PROGRESSIVA:\n"
            "  Acoes individuais mostram progresso na coluna Erro:\n"
            "  Ex: 'Like 3/11', 'Follow 2/5', 'Retweet 1/3',\n"
            "      'Unfollow 1/4', 'Like comentario 5/8'\n\n"
            "NOTA: exibe no maximo 1000 registros por vez (mais recentes primeiro)"
        ),
    },
    {
        "title": "7. Configuracoes",
        "content": (
            "Aba de configuracoes gerais do aplicativo.\n\n"
            "CAMPOS:\n"
            "  - Workers simultaneos (max): de 1 a 10\n"
            "    Quantas contas podem rodar ao mesmo tempo\n"
            "    Padrao: 3. Mais workers = mais uso de recursos\n\n"
            "  - Modo headless: checkbox\n"
            "    Quando ativo, o navegador roda de forma invisivel\n"
            "    Util para economizar recursos, mas dificulta debug\n\n"
            "  - Proxy padrao: campo de texto\n"
            "    Proxy usado por contas que nao tem proxy proprio\n"
            "    Formatos: socks5://ip:porta ou http://ip:porta\n\n"
            "  - Nivel de log: DEBUG, INFO, WARNING, ERROR\n"
            "    DEBUG: maximo de detalhes (para diagnostico)\n"
            "    INFO: nivel padrao recomendado\n"
            "    WARNING: apenas avisos e erros\n"
            "    ERROR: apenas erros criticos\n\n"
            "  - Perfil de rolagem global: Lento, Normal, Rapido, Super Rapido ou Ultra Rapido\n"
            "    Define a velocidade padrao de navegacao para todas as contas\n"
            "    Pode ser sobrescrito individualmente por conta\n"
            "    Super Rapido: 50%% mais veloz que Rapido, para contas maduras\n"
            "    Ultra Rapido: o dobro da velocidade, maximo desempenho\n\n"
            "  - Testar Proxy: botao ao lado do campo de proxy padrao\n"
            "    Testa a conexao do proxy e mostra o IP retornado\n"
            "    Suporta HTTP e SOCKS5 (com ou sem autenticacao)\n\n"
            "BOTAO:\n"
            "  - Salvar Configuracoes: salva e aplica imediatamente\n"
            "    O numero de workers e aplicado sem reiniciar o app"
        ),
    },
    {
        "title": "8. Admin (Moderadores/Admins)",
        "content": (
            "Aba visivel apenas para usuarios com papel 'moderator' ou 'admin'.\n\n"
            "TABELA:\n"
            "  Colunas: E-mail, Papel, Status, Ativado em, Liberado por, Motivo\n\n"
            "FILTROS:\n"
            "  - Todos / Ativos / Inativos / Liberados Manualmente\n\n"
            "BOTOES:\n"
            "  - Liberar Acesso: ativa a licenca de um usuario selecionado\n"
            "  - Revogar Acesso: desativa a licenca de um usuario\n"
            "  - Atualizar: recarrega a lista de usuarios"
        ),
    },
    {
        "title": "Fluxo de Configuracao Inicial",
        "content": (
            "Siga estes passos para configurar o CapiHeater pela primeira vez:\n\n"
            "PASSO 1 - LOGIN\n"
            "  Abra o programa, registre-se ou faca login com suas credenciais.\n"
            "  Marque 'Lembrar de mim' para logins automaticos futuros.\n\n"
            "PASSO 2 - ADICIONAR ALVOS\n"
            "  Va para a aba 'Alvos' e adicione os perfis com os quais suas contas\n"
            "  devem interagir. Use 'Adicionar em Massa' para importar varios de uma vez.\n"
            "  Defina prioridades (Alta para alvos principais) e categorias.\n\n"
            "PASSO 3 - CRIAR/ESCOLHER CRONOGRAMA\n"
            "  Na aba 'Cronogramas', revise os cronogramas disponiveis.\n"
            "  Recomendacao para iniciantes: use o 'Padrao' ou 'Conservador'.\n"
            "  Personalize os dias conforme necessario (duplo clique para editar).\n\n"
            "PASSO 4 - ADICIONAR CONTAS\n"
            "  Na aba 'Contas', clique em 'Adicionar Conta'.\n"
            "  Voce precisara do arquivo de cookies da conta Twitter/X.\n"
            "  Como obter cookies:\n"
            "    1. Faca login no Twitter/X no navegador\n"
            "    2. Use uma extensao como 'Cookie Editor' ou 'EditThisCookie'\n"
            "    3. Exporte os cookies como JSON\n"
            "    4. Salve o arquivo .json\n"
            "  Selecione o arquivo, escolha o cronograma, perfil de rolagem,\n"
            "  e opcionalmente configure proxy e categorias.\n\n"
            "PASSO 5 - CONFIGURACOES\n"
            "  Na aba 'Configuracoes', ajuste:\n"
            "  - Workers: comece com 1-2 para testar\n"
            "  - Headless: desative no inicio para visualizar o processo\n"
            "  - Proxy: configure se necessario\n"
            "  Clique em 'Salvar Configuracoes'.\n\n"
            "PASSO 6 - INICIAR\n"
            "  Volte ao 'Dashboard' e clique em 'Iniciar Todos'\n"
            "  ou selecione contas especificas e clique em 'Iniciar Selecionadas'.\n"
            "  Acompanhe o progresso na aba 'Logs'.\n\n"
            "DICA: ative 'Atualizar automaticamente' nos Logs para monitorar em tempo real."
        ),
    },
    {
        "title": "Como Funciona o Aquecimento",
        "content": (
            "O CapiHeater executa o seguinte fluxo para cada conta:\n\n"
            "1. INICIALIZACAO\n"
            "   - Abre o navegador (visivel ou headless)\n"
            "   - Carrega os cookies da conta\n"
            "   - Navega ate x.com e verifica se o login foi bem-sucedido\n"
            "   - Detecta e trata paginas de conteudo sensivel automaticamente\n\n"
            "2. FOLLOWS INICIAIS (se configurado)\n"
            "   - Executa follows imediatamente apos o login\n"
            "   - Quantidade definida no campo 'Follows iniciais' do cronograma\n\n"
            "3. CICLO DIARIO (conforme cronograma)\n"
            "   Para cada dia, o worker executa na ordem:\n\n"
            "   a) Navegar pelo Feed (antes das acoes)\n"
            "      - Rola o feed por tempo aleatorio dentro do intervalo configurado\n"
            "      - Abre postagens aleatoriamente\n"
            "      - Pode visualizar comentarios (conforme %% configurada)\n"
            "      - Velocidade de scroll conforme perfil: Lento, Normal, Rapido, Super Rapido ou Ultra Rapido\n\n"
            "   b) Curtidas\n"
            "      - 'Curtir no feed' ativado: curte posts durante navegacao do feed\n"
            "      - 'Curtir no feed' desativado: visita perfis alvos e curte la\n\n"
            "   b2) Curtir Comentarios (se configurado)\n"
            "      - Visita perfis de alvos ja seguidos\n"
            "      - Abre um post e rola ate os comentarios\n"
            "      - Curte comentarios com delays humanizados (4-12s)\n"
            "      - Pula comentarios aleatoriamente (chance configuravel)\n"
            "      - Limite de seguranca: max 50 likes em comentarios/dia\n\n"
            "   c) Follows\n"
            "      - Visita perfis-alvo e clica em seguir\n"
            "      - Pula alvos ja seguidos e tenta o proximo\n"
            "      - Nunca re-segue o mesmo alvo em qualquer dia\n"
            "      - Avisa quando nao ha alvos suficientes disponiveis\n\n"
            "   d) Retweets\n"
            "      - 'RT no feed' ativado: retweeta posts do feed\n"
            "      - 'RT no feed' desativado: visita perfis alvos e retweeta la\n\n"
            "   e) Unfollows\n"
            "      - Acessa a lista de 'seguindo' da conta\n"
            "      - Deixa de seguir a quantidade definida\n\n"
            "   f) Navegacao entre acoes\n"
            "      - Browsing adicional entre cada bloco de acoes\n\n"
            "4. HUMANIZACAO\n"
            "   - Scroll suave incremental que simula rolagem de mouse real\n"
            "     (nao pula de post em post — rola gradualmente)\n"
            "   - Centraliza o post na tela antes de abrir\n"
            "   - Pausas de leitura reais antes de interagir\n"
            "   - Scroll para cima ocasional (como uma pessoa faria)\n"
            "   - Delays aleatorios entre acoes (8-25 segundos)\n"
            "   - Variacao de +/-20%% nas quantidades de acoes\n"
            "   - Hover aleatorio em elementos da pagina\n"
            "   - Curtidas em perfis: abre o post, le por alguns segundos,\n"
            "     depois curte de dentro do post aberto (mais natural)\n"
            "   - Comentarios: le 2-5 comentarios com pausas reais,\n"
            "     depois volta para o post antes de sair\n\n"
            "5. TRATAMENTO DE PERFIS\n"
            "   - Perfis com aviso de conteudo sensivel: clica 'Sim, ver perfil'\n"
            "   - Perfis inexistentes (404): remove automaticamente dos alvos\n"
            "   - Perfis suspensos: remove automaticamente dos alvos\n\n"
            "6. FINALIZACAO\n"
            "   - Registra todas as acoes no banco de dados\n"
            "   - Avanca o dia do cronograma automaticamente\n"
            "   - Fecha o navegador\n"
            "   - Status atualizado para 'Concluido' ou 'Parado'"
        ),
    },
    {
        "title": "Categorias",
        "content": (
            "Categorias permitem organizar contas e alvos em grupos.\n\n"
            "COMO FUNCIONA:\n"
            "  - Conta SEM categorias: interage com TODOS os alvos ativos\n"
            "  - Conta COM categorias: interage apenas com alvos que compartilham\n"
            "    pelo menos uma categoria em comum\n\n"
            "COMO USAR:\n"
            "  - Crie categorias pelo botao 'Categorias' nas abas Contas ou Alvos\n"
            "  - Atribua categorias ao criar ou editar contas/alvos\n"
            "  - Use Ctrl+clique para selecionar multiplas categorias\n"
            "  - Na importacao em massa de alvos, selecione multiplas categorias\n\n"
            "EXEMPLOS DE USO:\n"
            "  - Agrupar contas por nicho: 'Tech', 'Marketing', 'Esportes'\n"
            "  - Separar alvos por tipo: 'Influencers', 'Marcas', 'Concorrentes'\n"
            "  - Organizar por cliente (se gerencia varias contas)\n\n"
            "DICA: excluir uma categoria remove automaticamente todas as associacoes\n"
            "com contas e alvos (as contas e alvos nao sao excluidos)."
        ),
    },
    {
        "title": "Proxies",
        "content": (
            "O CapiHeater suporta proxies para rotacionar IPs.\n\n"
            "FORMATOS ACEITOS:\n"
            "  - socks5://ip:porta\n"
            "  - http://ip:porta\n"
            "  - socks5://usuario:senha@ip:porta\n"
            "  - http://usuario:senha@ip:porta\n\n"
            "CONFIGURACAO:\n"
            "  - Proxy por conta: definido no formulario de cada conta\n"
            "  - Proxy padrao: definido em Configuracoes (usado quando a conta nao tem proxy)\n\n"
            "RECOMENDACAO:\n"
            "  - Use proxies residenciais para menor risco\n"
            "  - Um proxy diferente por conta e o ideal\n"
            "  - Evite proxies de datacenter (maior chance de deteccao)\n\n"
            "TESTAR PROXY:\n"
            "  Disponivel em tres locais:\n"
            "  - Configuracoes: ao lado do proxy padrao\n"
            "  - Formulario de conta: ao lado do proxy da conta\n"
            "  - Edicao em massa: ao lado do proxy\n\n"
            "  Clique 'Testar Proxy' e o sistema:\n"
            "  1. Valida o formato do proxy\n"
            "  2. Tenta conectar pelo proxy\n"
            "  3. Mostra o IP publico obtido (sucesso) ou a mensagem de erro\n\n"
            "  Suporta HTTP, HTTPS e SOCKS5 (com ou sem usuario/senha)\n\n"
            "VERIFICACAO VISUAL AO INICIAR:\n"
            "  Quando uma conta com proxy e iniciada:\n"
            "  1. O navegador abre whatismyipaddress.com por 5 segundos\n"
            "  2. Voce ve o IP do proxy na tela do navegador\n"
            "  3. O sistema confirma nos logs: \"Proxy verificado — IP: x.x.x.x\"\n"
            "  4. Depois segue normalmente para o Twitter/X\n\n"
            "  Se o proxy nao estiver funcionando, uma mensagem amigavel aparece:\n"
            "  \"Falha na conexao com o proxy. Verifique se o proxy esta ativo.\""
        ),
    },
    {
        "title": "Atualizacao Automatica",
        "content": (
            "O CapiHeater verifica atualizacoes automaticamente 3 segundos apos iniciar.\n\n"
            "FLUXO:\n"
            "  1. O app consulta as releases do GitHub\n"
            "  2. Se houver versao nova, mostra um dialogo com as novidades\n"
            "  3. Clique 'Sim' para baixar e aplicar automaticamente\n"
            "  4. Uma barra de progresso mostra o download\n"
            "  5. O download e verificado (tamanho e integridade)\n"
            "  6. Os novos arquivos sao copiados sobre os antigos\n"
            "  7. O app reinicia automaticamente com a versao nova\n\n"
            "VERIFICACOES DE SEGURANCA:\n"
            "  - Tamanho do arquivo verificado contra a API do GitHub\n"
            "  - Downloads truncados ou corrompidos sao rejeitados\n"
            "  - Se a atualizacao falhar, o app antigo continua funcionando\n\n"
            "NOTA: a atualizacao e opcional, voce pode clicar 'Nao' para ignorar."
        ),
    },
    {
        "title": "Barra de Status",
        "content": (
            "A barra inferior do aplicativo mostra:\n\n"
            "  - Lado esquerdo: mensagens de status (acoes realizadas, erros, etc.)\n"
            "  - Lado direito: botao 'Sair da Conta'\n\n"
            "O botao 'Sair da Conta':\n"
            "  - Para todos os workers em execucao\n"
            "  - Limpa credenciais salvas (Lembrar de mim)\n"
            "  - Fecha o aplicativo\n"
            "  - Na proxima abertura, a tela de login sera exibida"
        ),
    },
    {
        "title": "Dicas e Boas Praticas",
        "content": (
            "1. COMECE DEVAGAR\n"
            "   Use o cronograma 'Conservador' para contas novas ou recem-adquiridas.\n"
            "   Evite o 'Agressivo' em contas que nao tem historico.\n\n"
            "2. MONITORE OS LOGS\n"
            "   Verifique regularmente a aba Logs para identificar erros ou bloqueios.\n"
            "   Ative o auto-refresh para monitoramento em tempo real.\n\n"
            "3. USE PROXIES\n"
            "   Para varias contas, use proxies diferentes para cada uma.\n"
            "   Proxies residenciais sao mais seguros que datacenter.\n\n"
            "4. MANTENHA COOKIES ATUALIZADOS\n"
            "   Se uma conta apresentar erro de login, reimporte os cookies.\n"
            "   Cookies expiram e precisam ser renovados periodicamente.\n"
            "   Use o menu de contexto para importar cookies em multiplas contas.\n\n"
            "5. NAO EXAGERE NOS WORKERS\n"
            "   Comece com 1-2 workers e aumente conforme necessidade.\n"
            "   Muitos workers = mais uso de CPU e memoria.\n\n"
            "6. USE CATEGORIAS\n"
            "   Organize suas contas e alvos em categorias para direcionar\n"
            "   as interacoes para os alvos certos.\n\n"
            "7. REVISE CRONOGRAMAS\n"
            "   Personalize os cronogramas para o seu caso de uso.\n"
            "   A quantidade ideal de acoes depende da idade da conta.\n"
            "   Use 'Duplicar Dia' para criar variacoes rapidamente.\n\n"
            "8. LIKES E RT NOS PERFIS\n"
            "   Para aquecimento mais direcionado, desative 'Curtir no feed'\n"
            "   e 'RT no feed' no cronograma. As acoes serao feitas diretamente\n"
            "   nos perfis alvos, gerando interacao mais relevante.\n\n"
            "9. USE A PESQUISA\n"
            "   Com muitas contas ou alvos, use a barra de pesquisa para\n"
            "   encontrar rapidamente o que precisa.\n\n"
            "10. TESTE SEUS PROXIES\n"
            "   Antes de iniciar, use o botao 'Testar Proxy' para confirmar\n"
            "   que o proxy esta funcionando. Ao iniciar, o app mostra o IP\n"
            "   do proxy no navegador por 5 segundos.\n\n"
            "11. EXPORTE SEUS CRONOGRAMAS\n"
            "   Crie cronogramas personalizados e exporte como JSON para backup.\n"
            "   Compartilhe com outros usuarios ou importe em outras maquinas.\n\n"
            "12. ESCOLHA A VELOCIDADE CERTA\n"
            "   Use 'Lento' ou 'Normal' para contas novas (mais seguro).\n"
            "   Use 'Super Rapido' ou 'Ultra Rapido' apenas para contas\n"
            "   ja maduras que precisam de agilidade."
        ),
    },
    {
        "title": "Novidades da v1.0+",
        "content": (
            "INTERFACE MODERNA (v1.0)\n"
            "  A interface foi completamente redesenhada usando PySide6 (Qt6)\n"
            "  com o tema 'Obsidian Pulse' — visual dark premium com detalhes\n"
            "  em teal e violet.\n\n"
            "TESTE DE PROXY (v1.0)\n"
            "  Botao 'Testar Proxy' disponivel nas Configuracoes e no formulario\n"
            "  de conta. Testa HTTP e SOCKS5 e mostra o IP do proxy.\n\n"
            "VERIFICACAO VISUAL DE IP (v1.0)\n"
            "  Ao iniciar uma conta com proxy, o navegador abre\n"
            "  whatismyipaddress.com por 5 segundos para voce confirmar\n"
            "  que o proxy esta ativo antes de ir ao Twitter.\n\n"
            "SCROLL HUMANIZADO (v1.0)\n"
            "  O scroll agora simula movimento real de mouse, nao pula\n"
            "  entre posts. Curtidas em perfis agora abrem o post primeiro.\n\n"
            "NOVOS MODOS DE VELOCIDADE (v1.0)\n"
            "  Alem de Lento, Normal e Rapido, agora tem:\n"
            "  - Super Rapido: 50%% mais veloz que Rapido\n"
            "  - Ultra Rapido: o dobro da velocidade\n\n"
            "EXPORTAR/IMPORTAR CRONOGRAMAS (v1.0)\n"
            "  Exporte cronogramas como JSON e importe em outras instalacoes.\n"
            "  Facilita backup e compartilhamento entre usuarios.\n\n"
            "HORARIO LOCAL NOS LOGS (v1.0)\n"
            "  Logs agora mostram horario local (DD/MM/YYYY HH:MM:SS)\n"
            "  e o auto-refresh vem ligado por padrao.\n\n"
            "ERROS AMIGAVEIS (v1.0)\n"
            "  Fechar o navegador manualmente ou proxy offline\n"
            "  mostra mensagem clara ao inves de erro tecnico.\n\n"
            "CURTIR COMENTARIOS (v1.4)\n"
            "  Nova acao que visita perfis de alvos ja seguidos, abre um post\n"
            "  e curte comentarios/replies com humanizacao completa.\n"
            "  Configuravel por dia: total de likes, max por alvo e chance de pular.\n"
            "  Delays gaussianos (4-12s), leitura do comentario antes de curtir,\n"
            "  scroll suave e cap de seguranca de 50 likes/dia.\n"
            "  Progressao nos cronogramas: Padrao (dia 5), Conservador (dia 8),\n"
            "  Agressivo (dia 2)."
        ),
    },
    {
        "title": "Novidades v1.9.x",
        "content": (
            "SFS MAIS RAPIDO (v1.9.1)\n"
            "  Os delays entre perfis no modo SFS foram drasticamente reduzidos:\n"
            "    - Slow:   20-35 segundos entre perfis\n"
            "    - Normal: 10-20 segundos entre perfis\n"
            "    - Fast:    5-10 segundos entre perfis\n\n"
            "LINKS FUNCIONAM EM TODOS OS FORMATOS (v1.9.2)\n"
            "  Ao adicionar alvos, o sistema normaliza automaticamente qualquer formato:\n"
            "    - Com ou sem https:// (ex: x.com/usuario funciona diretamente)\n"
            "    - Links com letras maiusculas sao aceitos normalmente\n"
            "    - Links do twitter.com sao convertidos para x.com\n"
            "    - @usuario em qualquer variacao e reconhecido\n\n"
            "TABELAS ORDENAVEIS (v1.9.3)\n"
            "  Todas as tabelas do app agora suportam ordenacao por coluna:\n"
            "    - Clique no cabecalho de qualquer coluna para ordenar crescente\n"
            "    - Clique novamente para inverter (decrescente)\n"
            "    - Ordenacao inteligente: numeros, datas e texto reconhecidos\n"
            "    - Funciona em: Contas, Alvos, SFS, Logs, Dashboard, Cronogramas, Admin\n"
            "    - O cursor muda para mao nos cabecalhos clicaveis\n\n"
            "DROPDOWNS PESQUISAVEIS + EDICAO EM MASSA (v1.9.4)\n"
            "  Dropdowns de contas:\n"
            "    - Digite para filtrar contas nos dropdowns do SFS e Logs\n"
            "    - Contas listadas em ordem alfabetica\n"
            "  SFS — nova sessao:\n"
            "    - Ao criar uma nova sessao SFS, Curtir, RT, Like ultimo post\n"
            "      e RT ultimo post ja vem ativados por padrao\n"
            "  Edicao em massa de categorias em Alvos:\n"
            "    - Selecione multiplos alvos (Ctrl+clique ou Ctrl+A)\n"
            "    - Clique em 'Editar'\n"
            "    - As categorias escolhidas sao aplicadas a todos os selecionados"
        ),
    },
]


class DocsTab(BaseTab):
    """Built-in documentation tab with sidebar navigation and rich text display.

    Parameters
    ----------
    app : CapiHeaterApp
        Reference to the main application instance.
    """

    def __init__(self, app, parent=None):
        super().__init__(app, parent)
        self._section_anchors: list[str] = []
        self._build_ui()

    # ==================================================================
    # UI
    # ==================================================================

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter)

        # --- Left sidebar (index) ---
        sidebar = QWidget()
        sidebar.setFixedWidth(220)
        sidebar.setStyleSheet(f"background-color: {BG_SECONDARY};")
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(8, 12, 8, 8)
        sidebar_layout.setSpacing(8)

        index_title = QLabel("Indice")
        index_title.setStyleSheet(f"font-size: 12pt; font-weight: bold; color: {FG_TITLE};")
        sidebar_layout.addWidget(index_title)

        self._index_list = QListWidget()
        for doc in DOCS:
            self._index_list.addItem(doc["title"])
        self._index_list.currentRowChanged.connect(self._on_index_select)
        sidebar_layout.addWidget(self._index_list)

        splitter.addWidget(sidebar)

        # --- Right content area ---
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(12, 12, 12, 12)
        content_layout.setSpacing(6)

        header_lbl = QLabel("Documentacao do CapiHeater")
        header_lbl.setStyleSheet("font-size: 13pt; font-weight: bold;")
        content_layout.addWidget(header_lbl)

        self._browser = QTextBrowser()
        self._browser.setOpenExternalLinks(False)
        self._browser.setStyleSheet(
            f"background-color: {BG_INPUT}; padding: 12px;"
        )
        content_layout.addWidget(self._browser)

        splitter.addWidget(content)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

        # Load content
        self._load_all_content()

        # Select first item
        if DOCS:
            self._index_list.setCurrentRow(0)

    def _load_all_content(self) -> None:
        """Build HTML content from the DOCS list."""
        html_parts = []
        for i, doc in enumerate(DOCS):
            anchor = f"section_{i}"
            self._section_anchors.append(anchor)

            title_html = f'<a name="{anchor}"></a><h2 style="color:#5588cc; margin-top:16px;">{doc["title"]}</h2>'
            # Convert newlines to <br> and preserve indentation with &nbsp;
            content_escaped = (
                doc["content"]
                .replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace("\n", "<br>")
                .replace("  ", "&nbsp;&nbsp;")
            )
            body_html = f'<p style="color:#e0e0e0; font-size:10pt; line-height:1.5;">{content_escaped}</p>'

            html_parts.append(title_html + body_html)

            if i < len(DOCS) - 1:
                html_parts.append('<hr style="border-color:#333355;">')

        full_html = f"""
        <html>
        <body style="background-color:{BG_INPUT}; color:#e0e0e0; font-family:'Segoe UI'; font-size:10pt;">
        {"".join(html_parts)}
        </body>
        </html>
        """
        self._browser.setHtml(full_html)

    def _on_index_select(self, row: int) -> None:
        """Scroll to the selected section."""
        if 0 <= row < len(self._section_anchors):
            self._browser.scrollToAnchor(self._section_anchors[row])
