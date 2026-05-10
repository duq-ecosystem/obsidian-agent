# Obsidian Agent

DUQ specialist agent for Obsidian vault operations.

## Features

- Full CRUD operations on Obsidian notes
- Wikilink resolution
- Tag management
- Search across vault

## Ports

- 9001: A2A JSON-RPC endpoint

## Tools

- `obsidian_read` - Read note content
- `obsidian_create` - Create new note
- `obsidian_update` - Update existing note
- `obsidian_delete` - Delete note
- `obsidian_search` - Search vault
- `obsidian_list_files` - List files in vault

## Environment Variables

- `OBSIDIAN_VAULT_PATH` - Path to Obsidian vault
- `REDIS_URL` - Redis connection URL
- `AGENT_NAME` - Agent identifier
- `AGENT_PORT` - A2A server port
