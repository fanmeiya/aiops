import asyncio
import posixpath
import uuid
from dataclasses import dataclass, field
from typing import Any
import asyncssh
from app.security import decrypt


@dataclass
class Terminal:
    session_id: str; connection_id: str; process: Any
    output: list[str] = field(default_factory=list); agent_output: list[str] = field(default_factory=list)
    capture: bool = False; reader: asyncio.Task | None = None; command_lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    def append_output(self, text: str) -> None:
        self.output.append(text)
        # Preserve drain-buffer behavior while bounding a stalled client.
        if sum(map(len, self.output)) > 2 * 1024 * 1024:
            self.output[:] = ["".join(self.output)[-1024 * 1024:]]
        if self.capture:
            self.agent_output.append(text)
            if sum(map(len, self.agent_output)) > 2 * 1024 * 1024:
                self.agent_output[:] = ["".join(self.agent_output)[-1024 * 1024:]]


class SSHManager:
    def __init__(self):
        self.connections: dict[str, asyncssh.SSHClientConnection] = {}
        self.sftp_clients: dict[str, Any] = {}
        self.terminals: dict[str, Terminal] = {}

    async def connect(self, record, config) -> None:
        options = dict(host=record.host, port=record.port, username=record.username,
                       connect_timeout=(config.connect_timeout or 10), keepalive_interval=(config.keepalive_interval or 60))
        if not config.strict_host_key_check: options["known_hosts"] = None
        elif config.known_hosts: options["known_hosts"] = config.known_hosts
        if record.auth_type == 2: options["client_keys"] = [asyncssh.import_private_key(decrypt(record.private_key, record.encrypted))]
        else: options["password"] = decrypt(record.password, record.encrypted)
        self.connections[record.connection_id] = await asyncssh.connect(**options)

    async def disconnect(self, connection_id: str):
        for sid in [k for k, v in self.terminals.items() if v.connection_id == connection_id]: await self.close(sid)
        conn = self.connections.pop(connection_id, None)
        client = self.sftp_clients.pop(connection_id, None)
        if client: client.exit()
        if conn: conn.close(); await conn.wait_closed()

    async def open(self, connection_id: str, cols=120, rows=24, startup_command=None) -> Terminal:
        conn = self.connections.get(connection_id)
        if not conn or conn.is_closed(): raise ValueError("SSH连接未建立，请先连接")
        proc = await conn.create_process(term_type="xterm", term_size=(cols, rows), encoding="utf-8")
        sid = str(uuid.uuid4()); term = Terminal(sid, connection_id, proc); self.terminals[sid] = term
        term.reader = asyncio.create_task(self._reader(term))
        if startup_command: proc.stdin.write(startup_command + "\n")
        await asyncio.sleep(.25)
        return term

    async def _reader(self, term):
        try:
            async for text in term.process.stdout:
                term.append_output(text)
        except (asyncssh.Error, OSError): pass

    def require(self, sid):
        term = self.terminals.get(sid)
        if not term: raise ValueError(f"终端会话不存在或已关闭 sessionId={sid}")
        return term

    async def write(self, sid, text): self.require(sid).process.stdin.write(text)
    def read(self, sid):
        term = self.require(sid); result = "".join(term.output); term.output.clear(); return result
    async def resize(self, sid, cols, rows): self.require(sid).process.change_terminal_size(cols, rows)
    async def close(self, sid):
        term = self.terminals.pop(sid, None)
        if term:
            term.process.stdin.write_eof(); term.process.terminate()
            if term.reader: term.reader.cancel()

    async def execute(self, sid, command, timeout=60):
        term = self.require(sid)
        async with term.command_lock:
            marker = f"__WALISSH_DONE_{uuid.uuid4().hex}__"
            term.agent_output.clear(); term.capture = True
            term.process.stdin.write(f"{command}\nprintf '\\n{marker}:%s\\n' $?\n")
            end = asyncio.get_running_loop().time() + timeout
            while asyncio.get_running_loop().time() < end:
                text = "".join(term.agent_output)
                match = __import__('re').search(r"(?:\r?\n)" + marker + r":(-?\d+)(?:\r?\n)", text)
                if match:
                    term.capture = False
                    before = text[:match.start()]
                    # The interactive terminal echoes submitted input. Remove only
                    # the exact command/marker prelude and preserve remote output.
                    lines = before.splitlines(keepends=True)
                    echoed = command.splitlines()
                    while lines and echoed and lines[0].rstrip("\r\n") == echoed[0]:
                        lines.pop(0); echoed.pop(0)
                    lines = [line for line in lines if marker not in line]
                    return "".join(lines)
                await asyncio.sleep(.1)
            term.capture = False; raise TimeoutError("命令执行超时")

    def sftp_connection(self, cid):
        conn = self.connections.get(cid)
        if not conn or conn.is_closed(): raise ValueError("SSH连接未建立，请先连接")
        return conn

    async def sftp(self, cid):
        self.sftp_connection(cid)
        client = self.sftp_clients.get(cid)
        if client is None:
            client = await self.connections[cid].start_sftp_client()
            self.sftp_clients[cid] = client
        return client


ssh_manager = SSHManager()
