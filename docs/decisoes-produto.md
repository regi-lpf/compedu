# Decisões e princípios de produto — CompEdu

Este documento registra as decisões de produto e o estado atual de implementação, alinhado com a arquitetura consolidada em [docs/arq-decisoes-final.md](arq-decisoes-final.md).

## Objetivo e escopo

- Manter o CompEdu simples e focado em dois recursos: **mural interno de comunicados** e **registros pedagógicos**.
- Construir a experiência a partir das tarefas da equipe escolar, sem expor complexidade de banco de dados, vínculos anuais ou permissões como etapas desnecessárias para o usuário.

## Níveis de acesso e Mural (implementado)

- O acesso às publicações é numérico, de **1 a 5**; **1 é o nível mais alto**.
- Uma conta de nível `U` pode visualizar uma publicação de nível `P` quando `P >= U`. Exemplo: nível 2 visualiza publicações dos níveis 2, 3, 4 e 5.
- **No mural de comunicados, qualquer usuário autenticado pode publicar**, sendo restrito exclusivamente pelo seu nível de acesso (`P >= U`): ninguém pode criar ou editar uma publicação para um nível mais alto (`P < U`) do que o seu próprio.
- Nos registros pedagógicos e cadastros administrativos, além do nível, o papel (`role`) e os vínculos de turma controlam as ações e o escopo horizontal.
- O papel, nível da conta e turmas vinculadas no ano ativo ficam visíveis para o próprio usuário no componente de perfil no rodapé da sidebar.

## Registros pedagógicos e escopo (implementado)

- **Professores (`teacher`):** acesso restrito aos alunos com matrícula vigente nas **próprias turmas vinculadas no ano letivo ativo** (e aos registros de própria autoria), respeitando o nível `P >= U`.
- **Coordenação (`coordination`):** não recebe acesso aos registros de rotina dos professores; visualiza apenas registros de encaminhamento/acompanhamento (`follow_up`) ou marcados com nível `<= 2`, além dos relatórios consolidados (contagens agregadas) de todas as turmas.
- **Secretaria (`secretary`) e Suporte (`support`):** não possuem acesso de leitura nem de escrita aos registros pedagógicos.
- **Edição e remoção:** somente o próprio autor pode editar o conteúdo de um registro; a remoção (exclusão lógica com `deleted_at`) é permitida ao autor ou à administração, com registro em trilha de auditoria (`AuditLog`).

## Alunos, turmas e ano letivo (implementado)

- Todas as entidades usam identificadores **UUID**.
- Um aluno (`Student`) possui cadastro próprio e identificador escolar único (`school_identifier`); o nome completo (`full_name`) não é chave única, permitindo homônimos.
- O vínculo do aluno a uma turma (`Enrollment`) pertence a um ano letivo (`AcademicYear`). Trocar o aluno de turma encerra o vínculo anterior (`ended_at`) e cria um novo vínculo vigente, preservando todo o histórico de matrículas e os registros pedagógicos no contexto da turma em que foram criados.
- Na aba **Cadastros → Alunos e matrículas** (acessível à administração e à secretaria), o formulário único permite escolher entre **criar um aluno novo já matriculado na turma** ou **vincular/transferir um aluno existente**.
- A mesma aba permite importar listas CSV, XLS e XLSX para uma turma existente do ano ativo, com prévia e limite de 60 linhas. A importação usa nomes, ignora colunas de notas/presenças/observações, normaliza caixa e acentuação para detectar duplicatas e gera identificadores para novos alunos. Correspondências existentes e transferências exigem confirmação explícita; nomes ambíguos e linhas inválidas são ignorados e contabilizados.
- Os vínculos de professores com turmas (`TeachingAssignment`) são associados às turmas de cada ano letivo, permitindo preparar um novo ano letivo sem recadastrar profissionais ou estudantes.

## Conta e login (implementado)

- Não há tela de conta separada: o rodapé da sidebar exibe nome, papel e nível, e ao clicar abre o popover com e-mail, turmas vinculadas no ano ativo e o botão **Sair da conta**.
- O perfil CompEdu (papel, nível e vínculos escolares) é gerenciado pela administração e separado da identidade de autenticação.
- A autenticação principal usa **Google OAuth2** (`POST /api/auth/google`), validando o token do Google Identity Services e exigindo que o e-mail pertença a uma conta cadastrada e ativa no CompEdu (com restrição opcional de domínio institucional `ALLOWED_DOMAIN`).
- O primeiro administrador é criado uma única vez por `python -m app.create_admin`, executado manualmente contra o banco de produção. Depois disso, administradores criam e desativam contas pela interface.
- Para desenvolvimento local e testes automatizados, o login por e-mail/senha permanece disponível enquanto `AUTH_DEV_LOGIN=true`.

## Evoluções futuras (fora do escopo atual)

- **Anexos no mural de comunicados:** exigir armazenamento externo de objetos compatível com ambiente serverless (ex.: Vercel Blob ou S3) com controle de acesso autenticado.
