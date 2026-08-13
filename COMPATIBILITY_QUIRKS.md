# Compatibility Quirks

1. `chat_stream` is newline-delimited JSON, because the former emitter serialized an event and appended `\n`; it is intentionally not `data: ...\n\n` SSE framing.
2. Binding state was process-local. Python retains the same externally visible behavior and also keeps an explicit typed mapping. Multi-worker deployments need sticky routing.
3. Terminal reads drain the browser buffer. Agent capture duplicates output from that same PTY into a separate drain buffer; one-shot SSH commands are not substituted.
4. File `content` uses the effective 256 KiB implementation default even though an obsolete source comment mentioned 512 KiB.
5. Handled failures use HTTP 200 business envelopes. FastAPI request-binding failures remain framework errors, as Spring binding errors previously remained framework errors.
6. The previous SFTP layer automatically retried permission failures with password-fed sudo. Python never exposes a stored password to a shell. Explicit `sudo=true` uses remote `sudo -n`, so the account must be root or have passwordless sudo; this is intentionally stricter for credential safety.
7. The old deployment files contained plaintext credentials. They were removed, environment placeholders were introduced, and exposed credentials must be rotated.
