"""Testes de concorrencia para state-lock.sh.

Garante:
- acquire/release basico
- 2 acquires concorrentes: um espera, sem corrupcao
- timeout retorna 1
- stale lock e auto-removido
- N=10 processos concorrentes nao corrompem state.json
- Lock e re-entrante apenas via re-acquire (release explicito)
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(os.environ["HARNESS_PLUGIN_ROOT"])
LOCK_SH = ROOT / "scripts" / "state-lock.sh"

BASH = "bash"
if sys.platform == "win32":
    for candidate in (
        r"C:\Program Files\Git\bin\bash.exe",
        r"C:\Program Files\Git\usr\bin\bash.exe",
        "bash",
    ):
        if Path(candidate).exists() or candidate == "bash":
            BASH = candidate
            break


@pytest.fixture
def harness_dir(tmp_path):
    """Use tmp dir como HARNESS_DIR para isolar de instancia real."""
    d = tmp_path / "harness"
    d.mkdir()
    return d


def _env(harness_dir: Path, **extra: str) -> dict[str, str]:
    env = os.environ.copy()
    env["HARNESS_DIR"] = str(harness_dir)
    env.update(extra)
    return env


def _run_lock(args: list[str], harness_dir: Path, **extra) -> subprocess.CompletedProcess:
    return subprocess.run(
        [BASH, str(LOCK_SH), *args],
        env=_env(harness_dir, **extra),
        capture_output=True,
        text=True,
        timeout=15,
    )


class TestBasicLifecycle:
    def test_acquire_then_release(self, harness_dir):
        # Acquire em sub-shell so locks dentro daquele processo. Para testar
        # de fora, precisamos checar via filesystem.
        # Usamos um script inline que adquire, segura, e libera.
        script = f"""
            source "{LOCK_SH}"
            acquire_state_lock || exit 99
            test -d "$STATE_LOCK_DIR" || exit 98
            release_state_lock
            test ! -d "$STATE_LOCK_DIR" || exit 97
            exit 0
        """
        result = subprocess.run(
            [BASH, "-c", script],
            env=_env(harness_dir),
            capture_output=True, text=True, timeout=10,
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"

    def test_age_secs_when_no_lock(self, harness_dir):
        result = _run_lock(["age-secs"], harness_dir)
        assert result.returncode == 0
        assert result.stdout.strip() == "-1"

    def test_is_locked_false_initially(self, harness_dir):
        result = _run_lock(["is-locked"], harness_dir)
        assert result.returncode == 1


class TestConcurrency:
    def test_two_concurrent_acquires_serialize(self, harness_dir):
        """Dois processos concorrentes: ambos acquire, mas serializados."""
        # Processo A segura o lock por 1s
        script_a = f"""
            source "{LOCK_SH}"
            acquire_state_lock || exit 1
            sleep 1
            release_state_lock
        """
        # Processo B tenta acquire com timeout 5s — deve esperar A liberar
        script_b = f"""
            source "{LOCK_SH}"
            START=$(date +%s)
            acquire_state_lock || exit 1
            END=$(date +%s)
            ELAPSED=$((END - START))
            release_state_lock
            echo "$ELAPSED"
        """
        env = _env(harness_dir, STATE_LOCK_TIMEOUT_SECS="5")

        proc_a = subprocess.Popen(
            [BASH, "-c", script_a],
            env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        # Espera A pegar o lock
        time.sleep(0.2)
        proc_b = subprocess.Popen(
            [BASH, "-c", script_b],
            env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )
        proc_a.wait(timeout=10)
        out_b, _ = proc_b.communicate(timeout=10)
        assert proc_a.returncode == 0
        assert proc_b.returncode == 0
        elapsed = int(out_b.strip())
        # B esperou pelo menos 0s (ja que A liberou). Range realista: 0-2s.
        assert 0 <= elapsed <= 3, f"elapsed inesperado: {elapsed}"

    def test_timeout_returns_failure(self, harness_dir):
        """Lock segurado por outro processo + timeout curto = falha."""
        # Hold script segura por 3s
        hold_script = f"""
            source "{LOCK_SH}"
            acquire_state_lock || exit 1
            sleep 3
            release_state_lock
        """
        proc_hold = subprocess.Popen(
            [BASH, "-c", hold_script],
            env=_env(harness_dir), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        time.sleep(0.3)
        # Tenta com timeout 1s — deve falhar
        result = _run_lock(
            ["acquire"], harness_dir,
            STATE_LOCK_TIMEOUT_SECS="1",
        )
        assert result.returncode == 1
        assert "timeout" in result.stderr.lower()
        proc_hold.wait(timeout=10)


class TestStaleHandling:
    def test_stale_lock_auto_removed(self, harness_dir):
        """Lockdir antigo (mtime > stale threshold) e removido na proxima aquisicao."""
        lockdir = harness_dir / "state.json.lockdir"
        lockdir.mkdir()
        # Backdate mtime 60s para o passado
        old = time.time() - 60
        os.utime(lockdir, (old, old))

        # Stale threshold = 10s, lockdir tem 60s -> deve ser removido
        result = _run_lock(
            ["acquire"], harness_dir,
            STATE_LOCK_STALE_SECS="10",
            STATE_LOCK_TIMEOUT_SECS="2",
        )
        assert result.returncode == 0
        assert lockdir.exists()  # foi recriado pelo acquire
        # Cleanup
        _run_lock(["release"], harness_dir)

    def test_fresh_lock_not_removed(self, harness_dir):
        """Lockdir novo (mtime recente) nao e removido por stale-detection."""
        lockdir = harness_dir / "state.json.lockdir"
        lockdir.mkdir()
        result = _run_lock(
            ["acquire"], harness_dir,
            STATE_LOCK_STALE_SECS="100",
            STATE_LOCK_TIMEOUT_SECS="1",
        )
        assert result.returncode == 1


class TestWriteRaceProtection:
    """Cenario realistico: N processos escrevem state.json sob lock.
    Sem lock, alguns escreveriam JSON corrompido. Com lock, todos preservam.
    """

    @pytest.mark.parametrize("n_workers", [5, 10])
    def test_concurrent_writes_no_corruption(self, harness_dir, n_workers):
        state_file = harness_dir / "state.json"
        state_file.write_text('{"counter": 0, "writers": []}', encoding="utf-8")

        # Cada worker: acquire lock, le state, incrementa counter, append id, escreve, release.
        worker_template = f"""
            source "{LOCK_SH}"
            acquire_state_lock || exit 1
            python -c "
import json, os, sys
p = os.path.join(os.environ['HARNESS_DIR'], 'state.json')
with open(p, 'r', encoding='utf-8') as f:
    s = json.load(f)
s['counter'] += 1
s['writers'].append(int(sys.argv[1]))
with open(p, 'w', encoding='utf-8') as f:
    json.dump(s, f, indent=2)
" $WORKER_ID
            release_state_lock
        """

        env = _env(harness_dir, STATE_LOCK_TIMEOUT_SECS="20")

        procs = []
        for i in range(n_workers):
            worker_env = env.copy()
            worker_env["WORKER_ID"] = str(i)
            p = subprocess.Popen(
                [BASH, "-c", worker_template],
                env=worker_env,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            )
            procs.append(p)

        for p in procs:
            p.wait(timeout=30)

        failures = [p.returncode for p in procs if p.returncode != 0]
        assert not failures, f"workers falharam: {failures}"

        # State final: JSON valido, counter == n_workers, writers tem n_workers ids unicos
        final = json.loads(state_file.read_text(encoding="utf-8"))
        assert final["counter"] == n_workers, (
            f"counter perdeu writes: esperado {n_workers}, achou {final['counter']}"
        )
        assert sorted(final["writers"]) == list(range(n_workers)), (
            f"writers ids inconsistentes: {final['writers']}"
        )


class TestReentrancySemantics:
    def test_release_only_removes_own_lock(self, harness_dir):
        """release_state_lock so remove se owner_pid bate com $$."""
        # Cria lockdir manualmente com owner = PID falso
        lockdir = harness_dir / "state.json.lockdir"
        lockdir.mkdir()
        (lockdir / "owner").write_text("999999 12345\n", encoding="utf-8")

        # release_state_lock deve recusar (owner != $$)
        script = f"""
            source "{LOCK_SH}"
            release_state_lock
            test -d "$STATE_LOCK_DIR" && exit 0 || exit 1
        """
        result = subprocess.run(
            [BASH, "-c", script],
            env=_env(harness_dir),
            capture_output=True, text=True, timeout=10,
        )
        assert result.returncode == 0, "lockdir foi removido indevidamente"
