# Dashboard de Encerrados

Dashboard de visualização de dossiês encerrados, alimentado por dados do Odoo.

## Como funciona

- `buscar_dados_encerrados.py` conecta no Odoo via XML-RPC e gera o `dados_encerrados.json`.
- `dashboard_encerrados.html` lê esse JSON e renderiza os gráficos no navegador.
- O GitHub Actions roda o Python 1x por dia (06:00 BRT) e faz commit do JSON atualizado.
- O GitHub Pages publica o resultado em uma URL pública.

## URL do dashboard

https://SEU-USUARIO.github.io/dashboard-encerrados/dashboard_encerrados.html

## Atualizar manualmente

1. Aba **Actions** do repositório
2. Workflow **Atualizar dashboard de encerrados**
3. Botão **Run workflow** → **Run workflow**

A próxima atualização automática é diária às 06:00 BRT.
