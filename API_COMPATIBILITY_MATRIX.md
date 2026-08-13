# API Compatibility Matrix

All routes have compatibility tests via FastAPI/OpenAPI plus unit coverage for envelopes and binding semantics. Live SSH parity requires an integration host.

| Route group | Methods / inputs | Output and errors | Python status |
|---|---|---|---|
| `/api/v1/query_ai_agent_config_list` | GET | envelope/list | Implemented |
| `/api/v1/create_session` | GET query; POST JSON | session envelope; E0001 | Implemented/tested |
| `/api/v1/chat`, `/chat_stream` | POST camelCase JSON | envelope; NDJSON event objects | Implemented |
| `/api/v1/ssh/agent/*` | POST JSON/query; GET query | binding DTO/null semantics | Implemented/tested |
| `/api/v1/ssh/{create,update}_connection` | POST JSON | connection DTO | Implemented |
| `/api/v1/ssh/delete_connection` | POST query | empty-data envelope | Implemented |
| `/api/v1/ssh/{get_connection,connection_list}` | GET query | connection/list DTO | Implemented |
| `/api/v1/ssh/{connect,disconnect}` | POST query | localized info envelope | Implemented |
| `/api/v1/ssh/terminal/open` | POST JSON; default 120x24 | session/MOTD | Implemented |
| `/api/v1/ssh/terminal/{exec,write,resize}` | POST JSON | output/empty envelope | Implemented |
| `/api/v1/ssh/terminal/{read,close}` | GET/POST query | drain output/empty envelope | Implemented |
| `/api/v1/ssh/file/{tree,content,content-chunk}` | GET query | tree/content DTO | Implemented |
| `/api/v1/ssh/file/{create-file,create-directory,rename,delete}` | POST query, sudo=false | localized envelope | Implemented |
| `/api/v1/ssh/file/save-content` | POST query + JSON | localized envelope | Implemented |
| `/api/v1/ssh/file/upload` | multipart `file` | localized envelope | Implemented |
| `/api/v1/ssh/file/download` | GET query | octet stream/attachment | Implemented |
