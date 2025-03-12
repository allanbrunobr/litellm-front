# LiteLLM Key Manager

A graphical user interface for managing API keys for the LiteLLM proxy. This tool allows you to create, list, and revoke API keys for various LLM providers through a simple desktop application.

## Features

- Create API keys with specific permissions and budgets
- List existing keys with their details
- Revoke keys when they are no longer needed
- Set model access restrictions for keys
- Configure budget limits and expiration dates

## Prerequisites

- Docker and Docker Compose
- Python 3.8 or higher
- Tkinter (usually comes with Python)
- API keys for the LLM providers you want to use

## Setup Instructions

1. **Clone the repository**

```bash
git clone https://github.com/yourusername/litellm-key-manager.git
cd litellm-key-manager
```

2. **Set up environment variables**

```bash
cp .env.example .env
```

Edit the `.env` file and add your API keys for the LLM providers you want to use:

- OpenAI
- Anthropic
- Grok
- Gemini
- Deepseek

Also set your preferred master key for the LiteLLM proxy.

3. **Start the LiteLLM proxy and PostgreSQL database**

```bash
docker-compose up -d
```

This will start two containers:

- LiteLLM proxy on port 8080
- PostgreSQL database on port 5432

4. **Run the Key Manager application**

```bash
python key_manager.py
```

## Usage

### Connection Tab

1. The default server URL is `http://localhost:8080`
2. Enter the master key you set in the `.env` file
3. Click "Test Connection" to verify that you can connect to the LiteLLM proxy

### Manage Keys Tab

1. Enter a name for the key
2. Optionally set a team ID
3. Set a maximum budget
4. Set an expiration period (e.g., "30d" for 30 days)
5. Select which models the key can access
6. Click "Create Key" to generate a new API key

### List Keys Tab

1. Click "Update Key List" to see all existing keys
2. Select a key and click "Revoke Selected Key" to delete it

## Configuration

You can modify the `config.yaml` file to change the LiteLLM proxy configuration:

- Add or remove models
- Change routing strategies
- Adjust timeout settings
- Set global spend limits

## Troubleshooting

- If you can't connect to the LiteLLM proxy, make sure the containers are running:

  ```bash
  docker-compose ps
  ```

- If you need to see the logs from the LiteLLM proxy:

  ```bash
  docker-compose logs litellm
  ```

- If you need to reset the database:
  ```bash
  docker-compose down
  rm -rf data/postgres
  docker-compose up -d
  ```

## License

[MIT License](LICENSE)
