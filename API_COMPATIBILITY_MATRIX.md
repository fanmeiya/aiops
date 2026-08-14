# API Compatibility Matrix

The Python implementation exposes every route from the source controllers. “Implemented” means code exists; “unit” identifies locally automated contract coverage, while SSH/MySQL/DeepSeek integration still requires configured external services.

| Compatible route | Method | Python implementation | Automated coverage |
|---|---|---|---|
| `/api/v1/query_ai_agent_config_list` | GET | Implemented | unit |
| `/api/v1/create_session` | GET, POST | Implemented | unit |
| `/api/v1/chat` | POST JSON | Implemented | contract fixture |
| `/api/v1/chat_stream` | POST JSON/NDJSON | Implemented | contract fixture |
| `/api/v1/knowledge/documents` | POST JSON, GET query | Implemented | unit/core |
| `/api/v1/knowledge/documents/{document_id}` | DELETE query | Implemented | unit/core |
| `/api/v1/knowledge/search` | POST JSON | Implemented | unit/core |
| `/api/v1/ssh/agent/bind_terminal` | POST JSON | Implemented | unit |
| `/api/v1/ssh/agent/unbind_terminal` | POST query | Implemented | unit |
| `/api/v1/ssh/agent/query_binding` | GET query | Implemented | unit |
| `/api/v1/ssh/create_connection` | POST JSON | Implemented | schema fixture |
| `/api/v1/ssh/update_connection` | POST JSON | Implemented | schema fixture |
| `/api/v1/ssh/delete_connection` | POST query | Implemented | schema fixture |
| `/api/v1/ssh/get_connection` | GET query | Implemented | schema fixture |
| `/api/v1/ssh/connection_list` | GET query, `userId=default` | Implemented | schema fixture |
| `/api/v1/ssh/connect` | POST query | Implemented | external SSH required |
| `/api/v1/ssh/disconnect` | POST query | Implemented | external SSH required |
| `/api/v1/ssh/terminal/open` | POST JSON, 120x24 defaults | Implemented | external SSH required |
| `/api/v1/ssh/terminal/exec` | POST JSON | Implemented | external SSH required |
| `/api/v1/ssh/terminal/write` | POST JSON | Implemented | external SSH required |
| `/api/v1/ssh/terminal/read` | GET query | Implemented | external SSH required |
| `/api/v1/ssh/terminal/resize` | POST JSON | Implemented | external SSH required |
| `/api/v1/ssh/terminal/close` | POST query | Implemented | external SSH required |
| `/api/v1/ssh/file/tree` | GET query | Implemented | external SFTP required |
| `/api/v1/ssh/file/content` | GET query | Implemented | external SFTP required |
| `/api/v1/ssh/file/content-chunk` | GET query | Implemented | external SFTP required |
| `/api/v1/ssh/file/create-file` | POST query | Implemented | external SFTP required |
| `/api/v1/ssh/file/create-directory` | POST query | Implemented | external SFTP required |
| `/api/v1/ssh/file/rename` | POST query | Implemented | external SFTP required |
| `/api/v1/ssh/file/delete` | POST query | Implemented | external SFTP required |
| `/api/v1/ssh/file/save-content` | POST query + JSON | Implemented | external SFTP required |
| `/api/v1/ssh/file/upload` | POST multipart | Implemented | external SFTP required |
| `/api/v1/ssh/file/download` | GET binary | Implemented | external SFTP required |
