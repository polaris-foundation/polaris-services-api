from subprocess import PIPE, STDOUT, Popen
from typing import IO, Optional


def run_on_dhos_services(cmd: str) -> str:
    ssh_cmd = (
        """sshpass -p app ssh -o StrictHostKeyChecking=no -l app dhos-services-api"""
    )
    proc = Popen(
        ssh_cmd, shell=True, bufsize=40960, stdin=PIPE, stdout=PIPE, stderr=STDOUT
    )
    stdin: Optional[IO[bytes]] = proc.stdin
    stdout: Optional[IO[bytes]] = proc.stdout
    assert stdin is not None and stdout is not None

    stdin.write(
        (
            "&&".join(
                [
                    "cd /app",
                    "set -o allexport",
                    ". ./local.env",
                    cmd,
                ]
            )
            + "; exit"
        ).encode("utf-8")
    )
    stdin.close()
    proc.wait()
    output = stdout.read().decode("utf-8")
    return output
