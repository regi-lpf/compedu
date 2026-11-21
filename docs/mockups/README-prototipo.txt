CompEdu — protótipo de acompanhamento pedagógico

Para testar, abra index.html no navegador. Não é necessário instalar dependências.

Fluxos demonstrativos:
- Mural: tela inicial com comunicados internos e opção de publicar mensagens com público definido e múltiplos anexos.
- Administração: cadastre professores e seus vínculos com turmas, turmas, alunos e membros da equipe pedagógica.
- Painel: visão geral, registros recentes, alunos para acompanhar e data do conselho.
- Turmas: abra uma turma e depois um aluno para consultar o histórico.
- Registros: filtre os registros por turma, tipo e aluno.
- Novo registro: selecione aluno, tipo e público de compartilhamento.

Os dados são fictícios e ficam apenas na memória da página; recarregar o protótipo os restaura. Anexos são mantidos temporariamente no navegador e não são enviados a um servidor. As opções de público servem para discutir o produto e não aplicam controle de acesso. Não use informações reais de estudantes.

Decisões para a próxima etapa:
- Definir perfis (por exemplo, professor, coordenação, secretaria, psicopedagogia e administração) e quais ações cada perfil pode executar.
- Definir se a visibilidade varia por papel, vínculo com a turma, conselho ou combinação desses fatores. Para registros de alunos, prefira regras explícitas de menor privilégio a uma hierarquia genérica de níveis.
- Aplicar autorização no servidor em toda leitura e gravação, incluindo consultas por aluno e relatórios; ocultar opções na interface não protege os dados.
- Modelar vínculos de profissionais com turmas, matrículas, registros, comunicados, públicos-alvo e trilha de auditoria antes de escolher Flask ou FastAPI.
- Validar privacidade e retenção de dados de menores segundo a LGPD.

Os SVGs de mockup podem ser importados no Canva.
