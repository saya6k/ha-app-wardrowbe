"""Run inside the built image: prove the old limit fails and the managed one works."""

import ast
import asyncio
from pathlib import Path
import re
import subprocess
import tempfile

import asyncpg


def pool_capacity(path):
    tree = ast.parse(Path(path).read_text())
    calls = [
        node for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "create_async_engine"
    ]
    assert len(calls) == 1, f"Review database pool budget for {path}"
    options = {arg.arg: ast.literal_eval(arg.value) for arg in calls[0].keywords
               if arg.arg in {"pool_size", "max_overflow"}}
    assert options["pool_size"] > 0 and options["max_overflow"] >= 0
    return options["pool_size"] + options["max_overflow"]


async def check_connections(capacity, expect_exhaustion):
    admin = await asyncpg.connect(host="127.0.0.1", user="postgres", database="postgres")
    connections = []
    exhausted = False
    try:
        await admin.execute("CREATE ROLE wardrowbe_test LOGIN NOSUPERUSER")
        # Hold every slot allowed by the three upstream pools, plus a backup
        # connection. The admin connection represents a health/maintenance check.
        for _ in range(capacity + 1):
            try:
                connections.append(await asyncpg.connect(
                    host="127.0.0.1", user="wardrowbe_test", database="postgres",
                ))
            except asyncpg.TooManyConnectionsError:
                exhausted = True
                break
        assert exhausted == expect_exhaustion, (
            f"Connection exhaustion={exhausted}, expected={expect_exhaustion}; "
            f"opened {len(connections)} app connections"
        )
        assert await admin.fetchval("SELECT 1") == 1
        if not expect_exhaustion:
            assert all(result == 1 for result in await asyncio.gather(
                *(connection.fetchval("SELECT 1") for connection in connections)
            ))
        print(f"PASS: {'legacy limit reproduces exhaustion' if exhausted else 'all pools and backup fit'}")
    finally:
        for connection in connections:
            await connection.close()
        await admin.close()


def run_cluster(config, capacity, expect_exhaustion):
    # CI runs this isolated database as the real postgres OS user. The HA
    # production root shim is unnecessary for this connection-capacity test.
    with tempfile.TemporaryDirectory(prefix="wardrowbe-pg-test-") as directory:
        root = Path(directory)
        data = root / "data"
        subprocess.run([
            "initdb", "-D", str(data), "-U", "postgres", "--auth=trust",
            "--encoding=UTF-8", "--locale=C",
        ], check=True, stdout=subprocess.DEVNULL)
        (data / "wardrowbe.conf").write_text(config)
        with (data / "postgresql.conf").open("a") as file:
            file.write("\ninclude = 'wardrowbe.conf'\n")
        subprocess.run([
            "pg_ctl", "-D", str(data), "-l", str(root / "postgres.log"),
            "-o", f"-h 127.0.0.1 -k {directory}", "-w", "start",
        ], check=True)
        try:
            asyncio.run(check_connections(capacity, expect_exhaustion))
        finally:
            subprocess.run([
                "pg_ctl", "-D", str(data), "-m", "immediate", "-w", "stop",
            ], check=True)


if __name__ == "__main__":
    init = Path("/etc/cont-init.d/00-init.sh").read_text()
    config = re.search(r"<<'PGCONF'\n(.*?)\nPGCONF", init, re.S).group(1)
    capacity = pool_capacity("/app/backend/app/database.py")
    capacity += 2 * pool_capacity("/app/backend/app/workers/db.py")
    legacy = re.sub(r"^max_connections\s*=.*$", "max_connections = 10", config, flags=re.M)
    run_cluster(legacy, capacity, expect_exhaustion=True)
    run_cluster(config, capacity, expect_exhaustion=False)
