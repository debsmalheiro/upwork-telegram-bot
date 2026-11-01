# Próximos passos para ativar o bot

Status em 01/11/2026.

## ✅ Já feito
- [x] Repositório criado no GitHub. Os testes passam no Actions.
- [x] Chave da API do Upwork aprovada, com `UPWORK_CLIENT_ID` e `UPWORK_CLIENT_SECRET` no `.env`.
- [x] Bot do Telegram criado (@upworkSearchJobBot) e mensagem de teste recebida. `TELEGRAM_BOT_TOKEN` e `TELEGRAM_CHAT_ID` estão no `.env`.
- [x] Secrets cadastrados no GitHub: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `UPWORK_CLIENT_ID`, `UPWORK_CLIENT_SECRET`.
- [x] Workflow **Poll Upwork jobs** desativado até terminar a configuração.

## ⏳ Pendente

### 1. Autorizar o app no Upwork e gerar o refresh token
```bash
cd ~/projetos/upwork-telegram-bot
.venv/bin/python scripts/get_upwork_token.py          # mostra a URL de autorização
```
1. Abra a URL exibida e clique em autorizar.
2. Copie a URL para onde o navegador foi redirecionado (`https://localhost/callback?code=...`). A página de erro é esperada.
3. Logo em seguida (o code expira em poucos minutos), rode:
   ```bash
   .venv/bin/python scripts/get_upwork_token.py "URL_DO_CALLBACK"
   ```
   O token é gravado em `UPWORK_REFRESH_TOKEN` no `.env`, sem aparecer na tela.

> Se aparecer erro de `redirect_uri`, adicione `UPWORK_REDIRECT_URI=<Callback URL cadastrado na chave>` ao `.env` e repita o passo 1.

### 2. Validar a consulta ao Upwork localmente
```bash
.venv/bin/python -m bot.main --dry-run
```
O comando deve listar as vagas no terminal. Se aparecer um erro GraphQL de campo inexistente, ajuste `SEARCH_QUERY` e `parse_job()` em `bot/upwork.py` (o Upwork Developer Portal tem um explorador do schema).

### 3. Ajustar os filtros
Edite `config.yaml` com seus perfis (palavras-chave, orçamento, cliente) e repita o `--dry-run` até o resultado ficar bom.

### 4. Enviar o refresh token para o GitHub
```bash
grep '^UPWORK_REFRESH_TOKEN=' .env | cut -d= -f2- | tr -d '\n' | gh secret set UPWORK_REFRESH_TOKEN
```
> Rode o `--dry-run` **antes** deste passo. Cada execução renova o token, e o Upwork invalida o anterior. Se o bot rodar localmente depois de enviar o token, o secret do GitHub fica desatualizado e é preciso enviar de novo.

### 5. Criar o `GH_PAT`
Ele permite que o workflow atualize o `UPWORK_REFRESH_TOKEN` sozinho a cada execução.
1. Crie o token em https://github.com/settings/personal-access-tokens/new
   - **Repository access:** apenas `upwork-telegram-bot`
   - **Permissions → Secrets:** Read and write
2. Cadastre sem colar no chat:
   ```bash
   gh secret set GH_PAT
   ```

### 6. Ativar o bot
```bash
gh workflow enable "Poll Upwork jobs"
gh workflow run "Poll Upwork jobs"
gh run watch
```
Se der certo, você recebe **"🤖 Bot ativo!"** no Telegram. Daí em diante chegam só as vagas novas, a cada ~10 minutos.

### 7. (Opcional) Trocar o token do Telegram
O token atual do bot apareceu numa conversa. Para mais segurança, gere outro no @BotFather (`/revoke`) e atualize:
```bash
gh secret set TELEGRAM_BOT_TOKEN   # e também no .env
```

## Checklist final de secrets no GitHub
| Secret | Status |
|---|---|
| `TELEGRAM_BOT_TOKEN` | ✅ |
| `TELEGRAM_CHAT_ID` | ✅ |
| `UPWORK_CLIENT_ID` | ✅ |
| `UPWORK_CLIENT_SECRET` | ✅ |
| `UPWORK_REFRESH_TOKEN` | ⏳ passo 4 |
| `GH_PAT` | ⏳ passo 5 |

Confira com: `gh secret list`
