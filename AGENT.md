# AI Agent Log: Erros e Obstáculos do VidFetch
*(Documento exigido para memória futura e prevenção de loops)*

Ao longo do desenvolvimento e refatoração do *VidFetch* (migração de Python/Flask para Node.js/Vercel Serverless), ocorreram diversos bloqueios que consumiram tempo. Abaixo estão listados os maiores erros e como não se deve repeti-los:

## 1. O Falso Amigo: `@distube/ytdl-core` e `play-dl`
- **O Erro:** Logo após refatorar o backend em servidor Python para TypeScript, tentamos utilizar as bibliotecas JS populares `@distube/ytdl-core` e, posteriormente, `play-dl` para buscar URLs criptografadas do YouTube.
- **O Bloqueio:** O YouTube ativou rotinas pesadas de bloqueio antibot baseadas em "Proof of Work" (`poToken`), fazendo as bibliotecas quebrarem internamente. Elas não conseguiam descriptografar Ciphers (gerando `Failed to find any playable formats` ou URLs `undefined`/nulas das *streams*).
- **Tentativas falhas:** Passamos quase 15 chamadas no prompt tentando reinjetar JSON de cookies manuais exportados do browser, tentar extrair `poToken` ativamente com bibliotecas de terceiros (`youtube-po-token-generator`), e testar clones no GitHub como `khlevon/ytdl-core` usando chamadas experimentais.
- **A Solução Definitiva:** Desistir de soluções *puramente JavaScript* baseadas nas proteções antigas. Foi feita a transição para a raiz do problema instalando o **`youtube-dl-exec`** (um wrapper direto para o aclamado binário **yt-dlp** em Python encapsulado), que burla as travas com excelência e suporta a arquitetura Vercel serverless.

## 2. Serverless Timeouts vs Pipes
- **O Erro:** Utilizar métodos baseados no core Vercel que tentavam parsear dados grandes localmente no processo do Node, gerando o infame "A Server Error has ocured: `FUNCTION_INVOCATION_FAILED`" e estourando memória antes da conclusão. Além disso, as rotinas originais do projeto demandavam Merge via `FFmpeg` na nuvem para juntar as faixas DASH maiores que 720p.
- **A Solução Definitiva:** O `download.ts` deve apenas invocar requisições HTTP (`https.get(directUrl)`) redirecionadas diretamente da URL entregue pelo `yt-dlp` dos servidores do Google, acoplando a saída dela como um cano nativo (`.pipe(res)`) e anexando um header `Content-Disposition`. Downloads massivos ocorrem anonimamente entre a nuvem do Google e o usuário final sem estourar as funções de 10 segundos da Vercel. Evitar FFmpeg local em Vercel Functions.

## 3. O Inferno do Vercel CLI e `npm start`
- **O Erro:** O `package.json` original de migração mantinha comandos redundantes (ex: `"dev": "vercel dev"` recursivo que travava a Vercel CLI com erro crasso) e o `vercel.json` mantinha menções a bibliotecas `@vercel/python@latest`.
- **A Solução:** Padronizou-se que o `"start": "vercel dev"` será usado. O CLI deve ser respeitado rodando apenas Serverless APIs puras na pasta `/api` e o front como estático na raiz ou `/public`.

## Resumo da Lei do VidFetch:
Na arquitetura Vercel: **NUNCA tente puxar streams brutas via array JS para fundir em disco** e **NUNCA confie em forks instáveis de `ytdl-core`**. Use somente `yt-dlp` como fonte da verdade, gere o link direto anonimamente, crie um proxy stream (Pipe) do link Google no header de resposta e descarte a requisição HTTP local.
