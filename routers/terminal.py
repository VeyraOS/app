import asyncio
import os
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from services.supabase_client import supabase

router = APIRouter()

E2B_API_KEY = os.getenv("E2B_API_KEY", "")

# ANSI helpers
RST  = '\033[0m'
BOLD = '\033[1m'
DIM  = '\033[2m'
CORAL  = '\033[38;2;212;113;74m'
GREEN  = '\033[38;2;61;184;138m'
BLUE   = '\033[38;2;74;144;217m'
RED    = '\033[31m'
WHITE  = '\033[38;2;255;223;196m'

PROMPT = f'\r\n{CORAL}{BOLD}veyra{RST}{DIM}>{RST} '


def _validate_token(token: str):
    try:
        result = supabase.auth.get_user(token)
        return result.user
    except Exception:
        return None


# ── VEYRA CLI TERMINAL ───────────────────────────────────
@router.websocket("/veyra")
async def veyra_cli(websocket: WebSocket, token: str = Query(...), template: str = Query(""), agent_id: str = Query("")):
    user = _validate_token(token)
    if not user:
        await websocket.close(code=4001)
        return

    await websocket.accept()

    async def send(text: str):
        await websocket.send_text(text)

    await send(
        f'\r\n{BOLD}{CORAL}  VEYRA Agent Terminal{RST}  {DIM}v1.0{RST}\r\n'
        f'{DIM}  Autonomous · Web Search · Code Execution · File System{RST}\r\n'
        f'{DIM}  ────────────────────────────────────────────────────{RST}\r\n'
        f'{DIM}  Type a task and press Enter.  Ctrl+C to cancel.{RST}\r\n'
    )
    await send(PROMPT)

    input_buf   = ''
    agent_task  = None
    cancel_flag = asyncio.Event()

    async def run_cmd(cmd: str):
        cancel_flag.clear()
        from services.agent_sandbox import run_agent
        try:
            async for evt in run_agent(cmd, template=template, terminal=True, agent_id=agent_id, user_id=user.id):
                if cancel_flag.is_set():
                    await send(f'\r\n{DIM}  [cancelled]{RST}\r\n')
                    break
                t = evt.get('type', '')
                if t == 'spinning_up':
                    await send(f'{DIM}  ◌  {evt["message"]}{RST}\r\n')
                elif t == 'ready':
                    await send(f'{GREEN}  ✓  Sandbox online{RST}\r\n\r\n')
                elif t == 'searching':
                    await send(f'{BLUE}  ⟳  Searching — {DIM}{evt["query"]}{RST}\r\n')
                elif t == 'found':
                    await send(f'{GREEN}  ✓  Results found{RST}\r\n')
                elif t == 'coding':
                    await send(f'\r\n{CORAL}  ⌨  {evt["description"]}{RST}\r\n')
                    lines = evt.get('code', '').split('\n')
                    for line in lines[:12]:
                        await send(f'{DIM}     {line}{RST}\r\n')
                    if len(lines) > 12:
                        await send(f'{DIM}     … ({len(lines)-12} more lines){RST}\r\n')
                elif t == 'code_result':
                    out = (evt.get('output') or '').strip()
                    if out and out != '(no output)':
                        await send(f'{DIM}  ▶  Output:{RST}\r\n')
                        for line in out.split('\n')[:20]:
                            await send(f'{DIM}     {line}{RST}\r\n')
                elif t == 'writing_file':
                    await send(f'{CORAL}  ✎  Writing — {DIM}{evt["path"]}{RST}\r\n')
                elif t == 'reading_file':
                    await send(f'{DIM}  📂  Reading — {evt["path"]}{RST}\r\n')
                elif t == 'finishing':
                    await send(f'\r\n{CORAL}  ◎  {evt["message"]}{RST}\r\n\r\n')
                elif t == 'chunk':
                    await send(evt['content'])
                elif t == 'done':
                    await send(f'\r\n\r\n{DIM}  ─── {evt["tokens_used"]:,} tokens · task complete ───{RST}\r\n')
                elif t == 'error':
                    await send(f'{RED}  ✕  {evt["message"]}{RST}\r\n')
        except Exception as e:
            await send(f'{RED}  ✕  {e}{RST}\r\n')
        finally:
            await send(PROMPT)

    try:
        while True:
            data = await websocket.receive_text()
            for ch in data:
                code = ord(ch)
                if ch in ('\r', '\n'):
                    await send('\r\n')
                    cmd = input_buf.strip()
                    input_buf = ''
                    if cmd:
                        agent_task = asyncio.create_task(run_cmd(cmd))
                        await agent_task
                        agent_task = None
                    else:
                        await send(PROMPT)
                elif ch in ('\x7f', '\x08'):
                    if input_buf:
                        input_buf = input_buf[:-1]
                        await send('\b \b')
                elif ch == '\x03':
                    cancel_flag.set()
                    if agent_task:
                        agent_task.cancel()
                    await send(f'{DIM}^C{RST}')
                    input_buf = ''
                elif code >= 32:
                    input_buf += ch
                    await send(ch)
    except (WebSocketDisconnect, Exception):
        if agent_task:
            agent_task.cancel()


# ── RAW BASH TERMINAL ────────────────────────────────────
@router.websocket("/ws")
async def terminal_ws(websocket: WebSocket, token: str = Query(...)):
    user = _validate_token(token)
    if not user:
        await websocket.close(code=4001)
        return

    await websocket.accept()

    sandbox = None
    terminal = None
    loop = asyncio.get_event_loop()
    output_q = asyncio.Queue()
    stop = asyncio.Event()

    try:
        await websocket.send_text(
            "\r\n\033[1;32m VEYRA Agent Terminal\033[0m\r\n"
            "\033[2m Spinning up cloud sandbox...\033[0m\r\n\r\n"
        )

        from e2b_code_interpreter import AsyncSandbox

        sandbox = await AsyncSandbox.create(api_key=E2B_API_KEY)

        await websocket.send_text("\033[1;32m✓ Sandbox online\033[0m\r\n\r\n")

        def on_data(data: str):
            loop.call_soon_threadsafe(output_q.put_nowait, data)

        terminal = await sandbox.terminal.start(
            on_data=on_data,
            cols=220,
            rows=50,
        )

        async def send_loop():
            while not stop.is_set():
                try:
                    data = await asyncio.wait_for(output_q.get(), timeout=0.05)
                    await websocket.send_text(data)
                except asyncio.TimeoutError:
                    continue
                except Exception:
                    stop.set()
                    break

        async def recv_loop():
            while not stop.is_set():
                try:
                    msg = await websocket.receive_text()
                    await terminal.send_data(msg)
                except WebSocketDisconnect:
                    stop.set()
                    break
                except Exception:
                    stop.set()
                    break

        await asyncio.gather(send_loop(), recv_loop(), return_exceptions=True)

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_text(f"\r\n\033[1;31mError: {e}\033[0m\r\n")
        except Exception:
            pass
    finally:
        stop.set()
        if terminal:
            try:
                await terminal.kill()
            except Exception:
                pass
        if sandbox:
            try:
                await sandbox.kill()
            except Exception:
                pass
