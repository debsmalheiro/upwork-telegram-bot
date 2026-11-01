# Upwork → Telegram bot

Avisa no Telegram sobre cada vaga nova do Upwork que combine com seus filtros. Roda grátis no **GitHub Actions** a cada 10 minutos, usando a **API GraphQL oficial** do Upwork.

```
GitHub Actions (cron) → renova token Upwork → busca vagas por perfil (config.yaml)
  → filtra (orçamento, cliente, categoria) → ignora já enviadas (state/seen.json)
  → envia no Telegram → commita seen.json
```

## Configuração

### 1. Chave da API do Upwork (faça primeiro: a aprovação leva alguns dias)
1. Acesse https://www.upwork.com/developer/keys/apply
2. Em **Callback URL**, use `https://localhost/callback`.
3. Peça acesso de leitura a job postings / marketplace.
4. Quando aprovarem, anote o **Client ID** e o **Client Secret**.

### 2. Bot do Telegram
1. No Telegram, fale com o **@BotFather**, envie `/newbot` e copie o token.
2. Mande qualquer mensagem para o seu bot.
3. Abra `https://api.telegram.org/bot<TOKEN>/getUpdates` e copie o `chat.id`.

### 3. Rodar localmente
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env              # preencha os valores
python scripts/get_upwork_token.py  # gera o UPWORK_REFRESH_TOKEN e cole no .env
python -m bot.main --dry-run      # mostra as vagas no terminal, sem enviar
pytest -q
```

### 4. Publicar no GitHub
1. Crie um repositório **público** (no público, os minutos do Actions são ilimitados; num privado, mude o cron para `*/30`).
2. Em **Settings → Secrets and variables → Actions**, cadastre estes secrets:
   - `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`
   - `UPWORK_CLIENT_ID`, `UPWORK_CLIENT_SECRET`, `UPWORK_REFRESH_TOKEN`
   - `GH_PAT`: um *fine-grained token* restrito a este repositório, com permissão **Secrets: Read and write**. É usado para gravar o novo refresh token, que o Upwork troca a cada renovação.
3. Na aba **Actions**, rode **Poll Upwork jobs** manualmente (Run workflow).
   - A 1ª execução só registra as vagas que já existem e envia "🤖 Bot ativo!".
   - Nas próximas, chegam apenas as vagas novas.

## Filtros (`config.yaml`)
Cada perfil é um tipo de vaga e vira uma tag na mensagem (`#PythonDados`). Os campos disponíveis são `keywords`, `exclude_keywords`, `categories`, `job_type`, `min_fixed_budget`, `min_hourly_rate` e `client.{payment_verified, min_total_spent, countries_exclude}`. Se uma vaga casar com vários perfis, ela chega uma vez só, com todas as tags.

## Problemas comuns
- **🚨 Erro no bot / token expirado:** rode `scripts/get_upwork_token.py` de novo e atualize o secret `UPWORK_REFRESH_TOKEN`.
- **Erro GraphQL (campo inexistente):** o Upwork mudou o schema. Ajuste `SEARCH_QUERY` e `parse_job()` em `bot/upwork.py`.
- **O cron parou:** o GitHub desativa workflows agendados de repositórios sem atividade por 60 dias. Os commits do `seen.json` evitam isso enquanto chegarem vagas novas.

## Roadmap
1. Comandos no Telegram (`/filtros`, `/pausar`, `/add`), via Cloudflare Workers com webhook
2. Pontuação das vagas com IA (Claude): nota de aderência, resumo e sinais de risco
3. Botão "Gerar proposta" com rascunho de cover letter
4. Um tópico do grupo do Telegram para cada perfil
5. Botões inline: ⭐ salvar, 🚫 ignorar cliente, 🔕 silenciar keyword
6. Resumo diário ou semanal (volume, orçamento médio, skills em alta)
7. Horário de silêncio, com resumo pela manhã
8. Dashboard estático no GitHub Pages com o histórico de vagas
9. Lista negra de clientes e detecção de vagas repostadas
10. Prioridade: notificação com som só para as melhores vagas
