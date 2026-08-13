# Java Feature Inventory

This inventory was produced from the implementation (not README) before the rewrite.

## HTTP controllers

| Controller | Routes | Observable behavior |
|---|---|---|
| `AgentServiceController` | agent list, POST/GET create session, chat, chat_stream | `Response<T>` for non-streaming calls; stream is newline-delimited JSON objects. |
| `SshAgentController` | bind, unbind, query binding | process-local `chatSessionId -> terminalSessionId` map. |
| `SshConnectionController` | connection CRUD, list, connect, disconnect | logical persistence, live status synchronization, second precision date strings. |
| `SshTerminalController` | open, exec, write, read, resize, close | persistent PTY; open drains MOTD; reads drain a shared output buffer. |
| `SshFileController` | tree/content/chunk/create/rename/delete/save/upload/download | SFTP, 500 entries, 256 KiB chunks, UTF-8/binary detection, octet-stream downloads. |

## DTO and errors

All JSON properties are camelCase. The envelope is `{code, info, data}` (including null data). Codes are `0000`, `0001`, `0002`, `0003`, `E0001`, and `E0002`. ReAct events are `text`, `tool_call`, `tool_result`, `round_end`, `done`, and `error`; result state includes content, counters, termination flags/reason, calls, results, and error.

## SSH, agent, and state

`SshSessionPort` owns live JSch connections. `TerminalSessionPort` owns a persistent interactive `ChannelShell`, a drain-on-read UI buffer, and a separately gated agent buffer so both consumers observe the same PTY. `SshExecuteAdkTool`/MCP service execute `executeCommand` against the bound terminal—not the application host. The ReAct chain limits work to 50 steps, 200 calls, and 10 calls per round.

The configured SSH agent (`ssh-agent.yml`) defines the full SRE role, proactive command execution and sudo rules, package/Docker/network/performance/log/security workflows, recovery, confirmation boundary, and reporting format. The Python artifact retains this resource verbatim.

## Memory, context, intent

`ChatHistoryRepository` persists application history independently of the model runtime. `ChatContextService` assembles terminal/task/milestone/tool-result providers and applies sliding-window, priority, or hybrid reduction. `PromptService`, `DynamicPromptBuilder`, and `MilestoneTracker` add task progress. Intent flows through `IntentService`, context tracking, rules first, then the LLM classifier. These are application concepts and not Claude session substitutes.

## Persistence and configuration

The schema contains `chat_message`, `chat_milestone`, `chat_session`, `ssh_connection`, `ssh_connection_config`, and `ssh_session_log`. Existing names, nullable columns, indices, defaults, and timestamp meanings are authoritative. Spring YAML contains database/model credentials and placeholders; no values were copied. Python reads secrets from environment variables.
