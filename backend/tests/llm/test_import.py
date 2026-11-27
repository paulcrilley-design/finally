"""Importing the LLM client must not load .env or open a network connection."""

import os
import subprocess
import sys
from pathlib import Path

# Spies replace dotenv's loader, so no .env file is ever read, in either mode.
PROBE = """
import socket, dotenv, dotenv.main
calls, network = [], []
def spy(*args, **kwargs):
    calls.append(1)
    return False
def blocked(*args, **kwargs):
    network.append(args)
    raise OSError("network blocked by test")
dotenv.load_dotenv = dotenv.main.load_dotenv = spy
socket.getaddrinfo = socket.create_connection = blocked
socket.socket.connect = socket.socket.connect_ex = blocked
import app.llm.client
print(len(calls), len(network))
"""


def run_probe(**extra) -> tuple[int, int]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("LITELLM_")}
    result = subprocess.run(
        [sys.executable, "-c", PROBE],
        cwd=Path(__file__).resolve().parents[2],
        env={**env, **extra},
        capture_output=True,
        text=True,
        timeout=120,
        check=True,
    )
    loads, connections = result.stdout.split()[-2:]
    return int(loads), int(connections)


def test_import_loads_no_dotenv_and_uses_no_network():
    assert run_probe() == (0, 0)


def test_probe_detects_a_dotenv_load():
    assert run_probe(LITELLM_MODE="DEV")[0] > 0
