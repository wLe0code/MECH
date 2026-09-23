"""pi/iniciar-mech.sh: el auto-reinicio del server.

Se ejecuta el script REAL con un `python3` falso que devuelve el código que
queramos (1 = crash, 130 = Ctrl+C, o un número fijo de arranques antes de
salir bien). Verifica:
  * un crash se reinicia solo (hasta 5 veces) y después deja la ventana
    abierta con el motivo;
  * Ctrl+C (130) NO se reinicia (apagado a propósito);
  * salida limpia tampoco.
"""
from __future__ import annotations

import os
import shutil
import stat
import subprocess

import pytest

FIX_PI = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "fix", "pi")

FAKE_PYTHON = """#!/bin/bash
set -u
COUNT_FILE="$MECH_COUNT_FILE"
n=0
if [ -f "$COUNT_FILE" ]; then n=$(cat "$COUNT_FILE"); fi
n=$((n + 1))
echo "$n" > "$COUNT_FILE"
if [ -n "${MECH_EXIT_AT:-}" ] && [ "$n" -ge "$MECH_EXIT_AT" ]; then
    exit 0
fi
exit "${MECH_EXIT_CODE:-1}"
"""


def _montar_sandbox(tmp_path, exit_code, exit_at=None):
    repo = tmp_path / "repo"
    (repo / "pi").mkdir(parents=True)
    shutil.copy(os.path.join(FIX_PI, "iniciar-mech.sh"), repo / "pi" / "iniciar-mech.sh")
    (repo / "pi" / "volumen-max.sh").write_text("#!/bin/bash\nexit 0\n")
    (repo / "pi" / "volumen-max.sh").chmod(0o755)

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    (bin_dir / "python3").write_text(FAKE_PYTHON)
    (bin_dir / "python3").chmod(0o755)
    (bin_dir / "sleep").write_text("#!/bin/bash\nexit 0\n")
    (bin_dir / "sleep").chmod(0o755)

    count = tmp_path / "count.txt"
    env = {
        **os.environ,
        "PATH": f"{bin_dir}:{os.environ['PATH']}",
        "MECH_COUNT_FILE": str(count),
        "MECH_EXIT_CODE": str(exit_code),
    }
    if exit_at is not None:
        env["MECH_EXIT_AT"] = str(exit_at)
    return repo, count, env


def _correr(repo, env):
    return subprocess.run(
        ["bash", str(repo / "pi" / "iniciar-mech.sh"), "--sin-actualizar", "--sin-panel"],
        cwd=str(repo),
        env=env,
        input="\n",  # el "Pulsa Enter" final del script recibe un Enter de verdad
        capture_output=True,
        text=True,
        timeout=60,
    )


def test_crash_se_reinicia_solo_y_luego_avisa(tmp_path):
    repo, count, env = _montar_sandbox(tmp_path, exit_code=1)
    res = _correr(repo, env)

    assert int(count.read_text()) == 6, "5 reinicios + el arranque original"
    assert "reinicio solo en 4 s" in res.stdout
    assert "dejo de" in res.stdout  # el mensaje final parte en dos líneas
    assert res.returncode == 0  # el script termina prolijo


def test_ctrl_c_no_se_reinicia(tmp_path):
    repo, count, env = _montar_sandbox(tmp_path, exit_code=130)
    res = _correr(repo, env)

    assert int(count.read_text()) == 1, "Ctrl+C debe respetarse: un solo arranque"
    assert "reinicio solo" not in res.stdout


def test_salida_limpia_no_se_reinicia(tmp_path):
    repo, count, env = _montar_sandbox(tmp_path, exit_code=0)
    res = _correr(repo, env)

    assert int(count.read_text()) == 1
    assert "reinicio solo" not in res.stdout


def test_se_recupera_si_el_crash_era_transitorio(tmp_path):
    # El server crashea en el 1er arranque y en el 2º sale bien:
    # el bucle debe terminar sin llegar a los 5 reinicios.
    repo, count, env = _montar_sandbox(tmp_path, exit_code=1, exit_at=2)
    res = _correr(repo, env)

    assert int(count.read_text()) == 2
    assert "reinicio solo en 4 s" in res.stdout
    assert "dejo de reintentar" not in res.stdout