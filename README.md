# LiteLLM Key Manager

A graphical user interface for managing API keys for the LiteLLM proxy. This tool allows you to create, list, and revoke API keys for various LLM providers through a simple desktop application.

## Features

- Create API keys with specific permissions and budgets
- List existing keys with their details
- Revoke keys when they are no longer needed
- Set model access restrictions for keys
- Configure budget limits and expiration dates

## Prerequisites

- Python 3.8 or higher
- API keys for the LLM providers you want to use

## Arquitetura

Este projeto utiliza uma arquitetura cliente-servidor:

- **Servidor (LiteLLM Proxy)**:

  - Hospedado em: `https://litellm-server-458225897211.us-central1.run.app`
  - Gerencia todas as chaves API e solicitações de LLM
  - Utiliza SQLite como banco de dados para armazenar as chaves e registros de uso
  - Requer a master key "metatron123" para autenticação

- **Cliente (Web Manager)**:
  - Interface web que roda localmente na porta 5001
  - Comunica-se com o servidor via API REST
  - Não requer banco de dados local (todos os dados são armazenados no servidor)

## Setup Instructions

1. **Clone the repository**

```bash
git clone https://github.com/yourusername/litellm-key-manager.git
cd litellm-key-manager
```

2. **Set up environment variables (optional)**

```bash
cp .env.example .env
```

Edit the `.env` file and add your preferred master key for accessing the LiteLLM proxy.

3. **Run the Web Manager application**

```bash
./run.sh
```

This will:

- Create a virtual environment
- Install required dependencies
- Start the web interface on http://localhost:5001

## Usage

### Web Interface

Access the web interface at http://localhost:5001 in your browser.

### Connection

1. The server URL is already configured to connect to `https://litellm-server-458225897211.us-central1.run.app`
2. Enter the master key provided by your administrator
3. Click "Test Connection" to verify that you can connect to the LiteLLM proxy

### Manage Keys

1. Enter a name for the key
2. Optionally set a team ID
3. Set a maximum budget
4. Set an expiration period (e.g., "30d" for 30 days)
5. Select which models the key can access
6. Click "Create Key" to generate a new API key

### List Keys

1. Click "Update Key List" to see all existing keys
2. Select a key and click "Revoke Selected Key" to delete it

## Available Models

The following models are configured on the server:

- **OpenAI**

  - gpt-4
  - gpt-3.5-turbo

- **Anthropic**

  - claude-3-opus
  - claude-3-sonnet

- **Google**

  - gemini-pro

- **Grok (xAI)**

  - grok

- **Deepseek**
  - deepseek-chat

For more details about the model configurations, see the `models_config.yaml` file.

## Troubleshooting

- If you can't connect to the LiteLLM proxy, make sure you have the correct master key and that the server is online.

- If you need to use a different LiteLLM server, you can modify the `LITELLM_HOST` variable in the `.env` file or in the `run.sh` script.

## License

[MIT License](LICENSE)
