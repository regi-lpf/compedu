# Decisões e princípios de produto — CompEdu

Este documento registra as conclusões das conversas de 19/10/2026. Ele orienta o refinamento do protótipo e a implementação inicial; os pontos marcados como **a validar** não devem ser tratados como política escolar definitiva.

## Objetivo e escopo

- Manter o CompEdu simples e focado em dois recursos: mural interno de comunicados e registros pedagógicos.
- Construir a experiência a partir das tarefas da equipe escolar. Não expor complexidade de banco de dados, vínculos anuais ou permissões como etapas desnecessárias para o usuário.
- Refinar primeiro os fluxos essenciais do protótipo e iniciar a API em fatias pequenas, mantendo protótipo, contrato da API e implementação alinhados. Não é necessário polir todas as telas antes de começar a API.

## Níveis de acesso

- O acesso às publicações é numérico, de **1 a 5**; **1 é o nível mais alto**.
- Uma conta de nível `U` pode visualizar uma publicação de nível `P` quando `P >= U`. Exemplo: nível 2 visualiza publicações dos níveis 2, 3, 4 e 5.
- O nível controla a faixa de leitura; o tipo de usuário controla as ações que pode executar.
- Uma pessoa não deve poder criar uma publicação em um nível mais alto de acesso do que o seu próprio.
- O nível da conta deve ser visível para o próprio usuário.

## Registros pedagógicos e escopo

- Registros não são necessariamente exclusivos de professores. Professores e profissionais pedagógicos autorizados podem precisar consultá-los.
- Para professores, o acesso deve considerar **o vínculo com a turma e o nível da conta**. Ter um nível amplo, por si só, não deve conceder acesso a todas as turmas.
- Secretaria não recebe acesso pedagógico por padrão; qualquer exceção deve corresponder a uma necessidade de trabalho definida pela escola.
- **A validar com a escola:** quais perfis podem ler, criar ou corrigir registros; quais áreas da equipe pedagógica precisam de acesso; e se os registros têm exceções de escopo por aluno, turma ou equipe.

## Alunos, turmas e ano letivo

- Um aluno tem cadastro próprio e identificador estável; o nome não é uma chave única. Alunos diferentes podem ter o mesmo nome.
- O vínculo do aluno a uma turma pertence a um ano letivo. Trocar de turma atualiza o vínculo vigente e preserva os vínculos e registros históricos.
- O cadastro deve ser simples: ao adicionar alguém a uma turma, a interface permite criar um aluno novo ou vincular um cadastro existente. O sistema cria o cadastro e o vínculo juntos quando for um aluno novo.
- Na preparação de um novo ano, criam-se as turmas daquele ano e vinculam-se alunos e profissionais já cadastrados, evitando recadastrar pessoas.
- Professores devem ver as próprias turmas vinculadas no perfil. A equipe pedagógica só precisa de uma área/grupo específico no perfil se essa informação afetar tarefas ou permissões.
- **A validar:** identificador escolar disponível para distinguir homônimos e o fluxo concreto de preparação/transferência entre anos.

## Conta e login

- Não criar uma tela de conta separada neste estágio. Usar um componente no rodapé da sidebar com nome, tipo de usuário e nível; ao abrir, mostrar turmas do professor ou área de atuação relevante e a ação **Sair**.
- O perfil CompEdu (papel, nível e vínculos escolares) deve ser separado da identidade usada para entrar.
- A preferência inicial é login com **gov.br**; **Gmail** é alternativa a avaliar. A escolha e a integração ficam para uma etapa posterior e dependem da viabilidade para a escola.

## Próxima fatia de implementação

1. Refinar no protótipo o perfil na sidebar, cadastro do nível do profissional e fluxos de adicionar/vincular aluno e trocar de turma.
2. Confirmar com a escola as regras de leitura e escrita dos registros e os perfis da equipe pedagógica.
3. Ajustar o modelo para ano letivo, matrícula/vínculo do aluno e vínculo anual de profissionais com turmas.
4. Implementar uma fatia vertical: autenticação escolhida, perfil, cadastros essenciais e registros com autorização por papel, vínculo e nível.

## Estado técnico registrado

- O protótipo permanece demonstrativo e seus dados são mantidos em memória no navegador; ainda não está conectado à API.
- A API inicial e o banco local de demonstração existem. A API já aplica o filtro numérico nos registros e comunicados, mas o escopo de turma precisa ser aplicado nas consultas de registros antes de usar dados reais.
- O modelo atual de aluno ligado diretamente a uma turma e o vínculo de professor sem ano letivo precisam evoluir antes de consolidar dados de produção.
- Nenhum dado real de estudantes deve ser usado no protótipo ou banco demo.
