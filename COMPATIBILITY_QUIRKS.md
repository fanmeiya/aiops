# Compatibility Quirks

1. `chat_stream` is not SSE framing: Java emits a serialized JSON object followed by `\n`. The Python route deliberately preserves that wire format.
2. Binding state is process-local in Java and is likewise non-durable. Multi-worker deployment therefore needs sticky routing or a future shared-state migration.
3. Terminal `read` drains the browser buffer while agent capture duplicates shell output into a second buffer. It is not replaceable with one-shot SSH execution.
4. Java file `content` delegates to the same 256 KiB default used by chunk reading despite an obsolete 512 KiB comment.
5. Java returns HTTP 200 business error envelopes for handled failures. Framework binding failures remain framework-level errors.
6. Java may automatically fall back to sudo for permission-denied file operations. The Python rewrite does not silently send stored passwords to sudo; explicit sudo file fallbacks require a separately reviewed credential policy.
7. Existing YAML included credential locations/placeholders. No live secret was copied; operators must rotate any credential that was historically committed.
