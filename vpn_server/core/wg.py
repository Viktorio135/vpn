import subprocess
from pathlib import Path


def generate_keys() -> tuple[str, str]:
    private_key = subprocess.run(
        ["wg", "genkey"],
        capture_output=True,
        text=True
    ).stdout.strip()
    public_key = subprocess.run(
        ["wg", "pubkey"],
        input=private_key,
        capture_output=True,
        text=True
    ).stdout.strip()
    return private_key, public_key


def add_client_to_server_config(client_public_key: str, client_ip: str):
    peer_config = (
        f"\n[Peer]\n"
        f"PublicKey = {client_public_key}\n"
        f"AllowedIPs = {client_ip}/32\n"
    )
    with open("/etc/wireguard/wg0.conf", "a") as f:
        f.write(peer_config)
    command = "sudo bash -c 'wg syncconf wg0 <(wg-quick strip wg0)'"
    result = subprocess.run(
        command,
        shell=True,
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        raise subprocess.CalledProcessError(result.returncode, result.args)


def delete_client_from_server_config(client_public_key: str):
    """Полное удаление пира из конфига и runtime"""
    config_path = Path("/etc/wireguard/wg0.conf")

    # Шаг 1: Удаление из runtime-конфигурации
    try:
        subprocess.run(
            ["sudo", "wg", "set", "wg0", "peer", client_public_key, "remove"],
            check=True,
            capture_output=True,
            text=True
        )
    except subprocess.CalledProcessError as e:
        if "No such peer" not in e.stderr:
            raise RuntimeError(f"Ошибка удаления из runtime: {e.stderr}")

    # Шаг 2: Удаление из конфиг-файла
    config_content = config_path.read_text().splitlines()
    new_content = []
    peer_block = []
    in_target_peer = False

    for line in config_content:
        if line.strip() == "[Peer]":
            if peer_block:
                if not in_target_peer:
                    new_content.extend(peer_block)
                peer_block = []
            in_target_peer = False
            peer_block.append(line)
        elif peer_block:
            peer_block.append(line)
            if line.strip().startswith("PublicKey ="):
                current_key = line.split("=", 1)[1].strip()
                if current_key == client_public_key:
                    in_target_peer = True
        else:
            new_content.append(line)

    # Добавляем последний блок, если не целевой
    if peer_block and not in_target_peer:
        new_content.extend(peer_block)

    # Запись нового конфига
    config_path.write_text("\n".join(new_content) + "\n")

    # Шаг 3: Принудительная синхронизация
    command = "sudo bash -c 'wg syncconf wg0 <(wg-quick strip wg0)'"
    result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True
        )

    if result.returncode != 0:
        raise subprocess.CalledProcessError(result.returncode, result.args)
