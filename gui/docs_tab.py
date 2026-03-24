"""
DocsTab - Built-in documentation viewer for CapiHeater.
"""

import tkinter as tk
from tkinter import ttk


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
            "executadas por dia, escalando progressivamente ao longo de varios dias."
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
            "  - Registrar (link): cria uma nova conta (requer confirmacao por e-mail)\n\n"
            "NOTAS:\n"
            "  - Se 'Lembrar de mim' estiver ativo, o login e feito automaticamente\n"
            "  - Apos o login, a licenca e verificada. Se inativa, o acesso e bloqueado\n"
            "  - O botao 'Sair da Conta' na barra inferior faz logout e limpa credenciais salvas"
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
            "LISTA DE CONTAS:\n"
            "  Exibe todas as contas com colunas: Conta, Status, Dia\n"
            "  Indicadores coloridos de status:\n"
            "    - Verde: rodando\n"
            "    - Amarelo: pausada\n"
            "    - Vermelho: erro\n"
            "    - Cinza: parada (idle)\n"
            "    - Azul: concluida\n\n"
            "BOTOES GLOBAIS:\n"
            "  - Iniciar Todos: inicia o aquecimento de todas as contas\n"
            "  - Parar Todos: para todas as contas em execucao\n"
            "  - Atualizar: recarrega os dados da tela\n\n"
            "BOTOES INDIVIDUAIS (abaixo da lista):\n"
            "  - Iniciar Selecionada: inicia apenas a conta selecionada\n"
            "  - Pausar Selecionada: pausa a conta selecionada\n"
            "  - Parar Selecionada: para a conta selecionada\n\n"
            "MENU DE CONTEXTO (clique direito na conta):\n"
            "  - Iniciar / Pausar / Parar"
        ),
    },
    {
        "title": "3. Contas",
        "content": (
            "Aba de gerenciamento de contas Twitter/X que serao aquecidas.\n\n"
            "TABELA:\n"
            "  Colunas: Usuario, Status, Cronograma, Categoria, Dia, Proxy, Data Inicio\n\n"
            "BOTOES:\n"
            "  - Adicionar Conta: abre formulario para nova conta\n"
            "  - Editar: edita a conta selecionada\n"
            "  - Excluir: remove a conta selecionada (com confirmacao)\n"
            "  - Importar Cookies: importa cookies de arquivo para conta selecionada\n"
            "  - Importar em Massa: importa varias contas de uma vez\n"
            "  - Categorias: gerencia categorias (criar/excluir)\n\n"
            "FORMULARIO DE CONTA:\n"
            "  - Usuario (sem @): nome de usuario do Twitter/X\n"
            "  - Arquivo de Cookies: selecionar arquivo .json ou .txt (Netscape)\n"
            "  - Proxy (opcional): formato socks5:// ou http://\n"
            "  - Cronograma: selecionar qual cronograma usar\n"
            "  - Categorias: selecao multipla (Ctrl+clique)\n"
            "  - Notas: campo livre para anotacoes\n\n"
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
            "TABELA:\n"
            "  Colunas: Usuario, URL, Prioridade, Categoria, Ativo\n\n"
            "BOTOES:\n"
            "  - Adicionar Alvo: formulario para adicionar um alvo\n"
            "  - Adicionar em Massa: adiciona varios alvos de uma vez\n"
            "  - Editar: edita alvo selecionado\n"
            "  - Excluir: exclui alvo(s) selecionado(s)\n"
            "  - Alternar Ativo: ativa/desativa alvo sem excluir\n"
            "  - Abrir Perfil: abre o perfil no navegador padrao\n"
            "  - Categorias: gerencia categorias\n\n"
            "FORMULARIO DE ALVO:\n"
            "  - Usuario alvo (sem @)\n"
            "  - URL do perfil: preenchida automaticamente como https://x.com/{usuario}\n"
            "  - Prioridade: Baixa, Media ou Alta\n"
            "  - Categorias: selecao multipla (Ctrl+clique)\n\n"
            "ADICIONAR EM MASSA:\n"
            "  Cole links ou usernames, um por linha. Formatos aceitos:\n"
            "    - https://x.com/usuario\n"
            "    - https://twitter.com/usuario\n"
            "    - @usuario\n"
            "    - usuario\n"
            "  Selecione prioridade e categoria para todos os importados\n\n"
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
            "CRONOGRAMAS PRE-DEFINIDOS:\n"
            "  - Padrao (14 dias): crescimento moderado e seguro\n"
            "  - Conservador (21 dias): crescimento lento, mais browsing, menor risco\n"
            "  - Agressivo (7 dias): crescimento rapido, maior risco\n\n"
            "SELETOR: dropdown no topo para escolher qual cronograma visualizar\n\n"
            "TABELA:\n"
            "  Colunas: Dia, Likes, Follows, Retweets, Unfollows, Feed Antes (seg),\n"
            "           Feed Entre (seg), Abrir Posts\n\n"
            "BOTOES:\n"
            "  - Novo Cronograma: cria um cronograma vazio com nome e descricao\n"
            "  - Duplicar: copia o cronograma atual com novo nome\n"
            "  - Editar Dia: edita as configuracoes do dia selecionado\n"
            "  - Adicionar Dia: adiciona novo dia ao final do cronograma\n"
            "  - Remover Dia: remove o dia selecionado (renumera automaticamente)\n"
            "  - Excluir Cronograma: exclui o cronograma inteiro\n"
            "    (nao permite excluir se contas estiverem usando)\n\n"
            "EDITAR DIA - campos disponiveis:\n"
            "  Acoes:\n"
            "    - Likes: quantidade de curtidas no dia\n"
            "    - Follows: quantidade de follows no dia\n"
            "    - Retweets: quantidade de retweets no dia\n"
            "    - Unfollows: quantidade de unfollows no dia\n\n"
            "  Navegar pelo Feed (segundos):\n"
            "    - Antes das acoes: tempo min/max de navegacao antes de executar acoes\n"
            "    - Entre as acoes: tempo min/max de navegacao entre blocos de acoes\n"
            "    Ex: Antes 120-300 seg = navega entre 2 a 5 minutos antes de comecar\n\n"
            "  Comportamento:\n"
            "    - Abrir postagens: quantidade de posts para abrir e ler durante navegacao\n"
            "    - Ver comentarios (%): chance percentual de abrir comentarios dos posts\n"
            "    - Curtir no feed: se ativo, curtidas sao feitas durante a navegacao do feed\n"
            "    - Follows iniciais: follows extras feitos no inicio (para contas muito novas)\n\n"
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
            "  - Conta: filtra por conta especifica ou 'Todas'\n"
            "  - Acao: like, follow, retweet, unfollow, login, browse, sistema\n"
            "  - Status: success, failed, skipped\n\n"
            "BOTOES:\n"
            "  - Atualizar: recarrega os logs com filtros aplicados\n"
            "  - Limpar Logs: apaga TODOS os logs (irreversivel, pede confirmacao)\n\n"
            "OPCAO:\n"
            "  - Atualizar automaticamente: checkbox que recarrega logs a cada 5 segundos\n\n"
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
            "    DEBUG: maximo de detalhes (para diagnóstico)\n"
            "    INFO: nivel padrao recomendado\n"
            "    WARNING: apenas avisos e erros\n"
            "    ERROR: apenas erros criticos\n\n"
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
            "  Defina prioridades (Alta para alvos principais).\n\n"
            "PASSO 3 - CRIAR/ESCOLHER CRONOGRAMA\n"
            "  Na aba 'Cronogramas', revise os cronogramas disponiveis.\n"
            "  Recomendacao para iniciantes: use o 'Padrao' ou 'Conservador'.\n"
            "  Personalize os dias conforme necessario.\n\n"
            "PASSO 4 - ADICIONAR CONTAS\n"
            "  Na aba 'Contas', clique em 'Adicionar Conta'.\n"
            "  Voce precisara do arquivo de cookies da conta Twitter/X.\n"
            "  Como obter cookies:\n"
            "    1. Faca login no Twitter/X no navegador\n"
            "    2. Use uma extensao como 'Cookie Editor' ou 'EditThisCookie'\n"
            "    3. Exporte os cookies como JSON\n"
            "    4. Salve o arquivo .json\n"
            "  Selecione o arquivo, escolha o cronograma, e opcionalmente\n"
            "  configure proxy e categorias.\n\n"
            "PASSO 5 - CONFIGURACOES\n"
            "  Na aba 'Configuracoes', ajuste:\n"
            "  - Workers: comece com 1-2 para testar\n"
            "  - Headless: desative no inicio para visualizar o processo\n"
            "  - Proxy: configure se necessario\n"
            "  Clique em 'Salvar Configuracoes'.\n\n"
            "PASSO 6 - INICIAR\n"
            "  Volte ao 'Dashboard' e clique em 'Iniciar Todos'\n"
            "  ou inicie contas individualmente.\n"
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
            "   - Navega ate x.com e verifica se o login foi bem-sucedido\n\n"
            "2. CICLO DIARIO (conforme cronograma)\n"
            "   Para cada dia do cronograma, o worker executa na ordem:\n\n"
            "   a) Navegar pelo Feed (antes das acoes)\n"
            "      - Rola o feed por tempo aleatorio dentro do intervalo configurado\n"
            "      - Abre postagens aleatoriamente\n"
            "      - Pode visualizar comentarios (conforme % configurada)\n\n"
            "   b) Curtidas\n"
            "      - Curte a quantidade de posts definida para o dia\n"
            "      - Evita curtir posts ja curtidos\n\n"
            "   c) Follows\n"
            "      - Segue usuarios-alvo conforme quantidade do dia\n"
            "      - Navega ate o perfil e clica em seguir\n"
            "      - Verifica se ja esta seguindo\n\n"
            "   d) Retweets\n"
            "      - Retweeta posts conforme quantidade do dia\n"
            "      - Evita duplicatas\n\n"
            "   e) Unfollows\n"
            "      - Deixa de seguir usuarios conforme quantidade do dia\n\n"
            "   f) Navegar pelo Feed (entre acoes)\n"
            "      - Navegacao adicional entre blocos de acoes\n\n"
            "3. HUMANIZACAO\n"
            "   - Delays aleatorios entre acoes (distribuicao Gaussiana)\n"
            "   - Media de 4 segundos, variando entre 2 e 8 segundos\n"
            "   - Velocidade de scroll variavel\n"
            "   - Pulos aleatorios de acoes\n"
            "   - Pausas naturais entre interacoes\n\n"
            "4. LOGGING\n"
            "   - Todas as acoes sao registradas no banco de dados\n"
            "   - Visiveis na aba Logs com filtros"
        ),
    },
    {
        "title": "Categorias",
        "content": (
            "Categorias permitem organizar contas e alvos em grupos.\n\n"
            "COMO USAR:\n"
            "  - Crie categorias pelo botao 'Categorias' nas abas Contas ou Alvos\n"
            "  - Atribua categorias ao criar ou editar contas/alvos\n"
            "  - Use Ctrl+clique para selecionar multiplas categorias\n\n"
            "EXEMPLOS DE USO:\n"
            "  - Agrupar contas por nicho: 'Tech', 'Marketing', 'Esportes'\n"
            "  - Separar alvos por tipo: 'Influencers', 'Marcas', 'Concorrentes'\n"
            "  - Organizar por cliente (se gerencia varias contas)"
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
            "  - Evite proxies de datacenter (maior chance de deteccao)"
        ),
    },
    {
        "title": "Atualizacao Automatica",
        "content": (
            "O CapiHeater verifica atualizacoes automaticamente 3 segundos apos iniciar.\n\n"
            "FLUXO:\n"
            "  1. O app consulta o servidor de atualizacoes\n"
            "  2. Se houver versao nova, mostra um dialogo com as novidades\n"
            "  3. Clique 'Sim' para baixar e aplicar automaticamente\n"
            "  4. Uma barra de progresso mostra o download\n"
            "  5. A atualizacao e aplicada e o app solicita reinicializacao\n\n"
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
            "   Cookies expiram e precisam ser renovados periodicamente.\n\n"
            "5. NAO EXAGERE NOS WORKERS\n"
            "   Comece com 1-2 workers e aumente conforme necessidade.\n"
            "   Muitos workers = mais uso de CPU e memoria.\n\n"
            "6. USE CATEGORIAS\n"
            "   Organize suas contas e alvos em categorias para facilitar o gerenciamento.\n\n"
            "7. REVISE CRONOGRAMAS\n"
            "   Personalize os cronogramas para o seu caso de uso especifico.\n"
            "   A quantidade ideal de acoes depende da idade e atividade previa da conta."
        ),
    },
]


class DocsTab(ttk.Frame):
    """Built-in documentation tab with scrollable content.

    Parameters
    ----------
    parent : tk.Widget
        Parent frame (notebook tab container).
    app : CapiHeaterApp
        Reference to the main application instance.
    """

    def __init__(self, parent, app, **kwargs):
        super().__init__(parent, style="Tab.TFrame", **kwargs)
        self.app = app
        self._build_ui()

    # ==================================================================
    # UI
    # ==================================================================

    def _build_ui(self) -> None:
        # Main layout: sidebar + content
        main = ttk.Frame(self, style="Dark.TFrame")
        main.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)

        # --- Left sidebar (index) ---
        sidebar = tk.Frame(main, bg="#16213e", width=220)
        sidebar.pack(side=tk.LEFT, fill=tk.Y)
        sidebar.pack_propagate(False)

        tk.Label(
            sidebar, text="Indice", font=("Segoe UI", 12, "bold"),
            bg="#16213e", fg="#ffffff",
        ).pack(padx=12, pady=(12, 8), anchor="w")

        self._index_listbox = tk.Listbox(
            sidebar,
            bg="#0d1b2a", fg="#e0e0e0",
            selectbackground="#1a73e8", selectforeground="#ffffff",
            relief="flat", highlightthickness=0,
            font=("Segoe UI", 9),
            activestyle="none",
        )
        self._index_listbox.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))

        for doc in DOCS:
            self._index_listbox.insert(tk.END, doc["title"])

        self._index_listbox.bind("<<ListboxSelect>>", self._on_index_select)

        # --- Right content area ---
        content_frame = ttk.Frame(main, style="Dark.TFrame")
        content_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Header
        header = ttk.Frame(content_frame, style="Dark.TFrame")
        header.pack(fill=tk.X, padx=12, pady=(12, 6))
        ttk.Label(header, text="Documentacao do CapiHeater", style="Heading.TLabel").pack(side=tk.LEFT)

        # Scrollable text area
        text_frame = tk.Frame(content_frame, bg="#1a1a2e")
        text_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 12))

        self._text = tk.Text(
            text_frame,
            bg="#0d1b2a", fg="#e0e0e0",
            font=("Segoe UI", 10),
            relief="flat",
            highlightthickness=1,
            highlightcolor="#0f3460",
            wrap="word",
            padx=16, pady=12,
            cursor="arrow",
            state="disabled",
        )
        scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=self._text.yview)
        self._text.configure(yscrollcommand=scrollbar.set)
        self._text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Configure text tags
        self._text.tag_configure("title", font=("Segoe UI", 14, "bold"), foreground="#ffffff",
                                  spacing3=8)
        self._text.tag_configure("section", font=("Segoe UI", 12, "bold"), foreground="#5588cc",
                                  spacing1=16, spacing3=6)
        self._text.tag_configure("body", font=("Segoe UI", 10), foreground="#e0e0e0",
                                  spacing1=2, lmargin1=8, lmargin2=8)
        self._text.tag_configure("separator", font=("Segoe UI", 4), foreground="#333355")

        # Load all content
        self._load_all_content()

        # Select first item
        if DOCS:
            self._index_listbox.selection_set(0)

    def _load_all_content(self) -> None:
        """Load all documentation sections into the text widget."""
        self._text.configure(state="normal")
        self._text.delete("1.0", tk.END)

        # Store marks for scrolling to sections
        self._section_marks: list[str] = []

        for i, doc in enumerate(DOCS):
            mark = f"section_{i}"
            self._text.mark_set(mark, tk.END)
            self._text.mark_gravity(mark, "left")
            self._section_marks.append(mark)

            self._text.insert(tk.END, doc["title"] + "\n", "section")
            self._text.insert(tk.END, doc["content"] + "\n", "body")

            if i < len(DOCS) - 1:
                self._text.insert(tk.END, "\n" + "─" * 70 + "\n\n", "separator")

        self._text.configure(state="disabled")

    def _on_index_select(self, _event=None) -> None:
        """Scroll to the selected section."""
        sel = self._index_listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        if idx < len(self._section_marks):
            mark = self._section_marks[idx]
            self._text.see(mark)

    def refresh(self) -> None:
        """No-op refresh for tab-change compatibility."""
        pass
