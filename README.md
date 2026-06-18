# Painel de Demandas OSP

Cockpit web para gestão da esteira de demandas, checkpoint de configuração Locator e indicadores executivos.

## Visões disponíveis

1. **Esteira de Demandas**
   - Cadastro, edição e exclusão de demandas.
   - Cards por status.
   - Filtros por cliente/carteira/analista, status e responsável.
   - Campo Wrike para link do projeto.
   - Cálculo automático de Dias POC.

2. **Checkpoint Locator**
   - Cada ID de demanda possui um checklist próprio.
   - Vínculo: `demandas.id -> checkpoints.demanda_id`.
   - Campos preenchidos ficam como configurados.
   - Campos vazios ficam pendentes com alerta visual.

3. **Indicadores Executivos**
   - Cards consolidados.
   - Distribuição por status.
   - Farol de prazo.
   - Demandas por analista.
   - Ranking de pendências do checkpoint.
   - Farol por cliente/carteira.

## Paleta visual

- Laranja: `#FB5C28`
- Azul escuro: `#000049`
- Azul claro: `#345F99`
- Branco: `#FFFFFF`
- Cinza: `#848484`

O fundo possui gradiente fluido animado e interação com o movimento do mouse.

---

## Rodar localmente

Entre na pasta onde está o `app.py`:

```powershell
cd "C:\Users\gersou\OneDrive - Olos\04 - Locator\Locator\Github\painel_demandas\painel_demandas"
```

Instale as dependências:

```powershell
python -m pip install -r requirements.txt
```

Rode o app:

```powershell
python app.py
```

Acesse:

```txt
http://127.0.0.1:5000
```

### Python usado localmente

Se estiver usando o Python específico da máquina:

```powershell
C:\Users\gersou\AppData\Local\Python\pythoncore-3.14-64\python.exe -m pip install -r requirements.txt
C:\Users\gersou\AppData\Local\Python\pythoncore-3.14-64\python.exe app.py
```

Para produção, o projeto está preparado com `python-3.11.9` no `runtime.txt`.

---

## Banco local

Sem `DATABASE_URL`, o sistema usa SQLite local:

```txt
sqlite:///demandas.db
```

O arquivo `.db` não deve ir para o GitHub, e já está no `.gitignore`.

---

## Configuração no Render

### Build Command

```bash
pip install -r requirements.txt
```

### Start Command

```bash
gunicorn app:app
```

### Health Check Path

```txt
/health
```

### Environment Variables

Configure no Render:

```txt
DATABASE_URL=<Internal Database URL do PostgreSQL Render>
SECRET_KEY=<chave gerada pelo Render ou uma chave segura>
FLASK_DEBUG=0
```

Use sempre a **Internal Database URL** do banco Render no serviço web.

Nunca cole a URL real do banco dentro do código, README ou GitHub.

---

## Validar banco

Depois de rodar localmente ou no Render, acesse:

```txt
/db-status
```

Resposta esperada:

```json
{
  "database": "postgresql+pg8000://host/database",
  "status": "conectado",
  "total_demandas": 30
}
```

No local com SQLite, o retorno deve indicar `sqlite`.

---

## Endpoints principais

```txt
GET    /
GET    /health
GET    /db-status
GET    /api/demandas
POST   /api/demandas
PUT    /api/demandas/<id>
DELETE /api/demandas/<id>
GET    /api/demandas/<id>/checkpoint
PUT    /api/demandas/<id>/checkpoint
POST   /api/demandas/<id>/checkpoint/reset
GET    /api/indicadores
```

---

## Subir para GitHub

Na pasta do projeto:

```powershell
git init
git add .
git commit -m "Painel de Demandas OSP"
git branch -M main
git remote add origin URL_DO_REPOSITORIO
git push -u origin main
```

Troque `URL_DO_REPOSITORIO` pela URL HTTPS do repositório.

Antes do push, confirme que não existe arquivo `.env` com senha no commit:

```powershell
git status
```

---

## Observação sobre PostgreSQL

O projeto usa `pg8000` em vez de `psycopg2-binary`, evitando erro de `pg_config` no Windows e simplificando o deploy no Render.
