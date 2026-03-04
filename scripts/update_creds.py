import subprocess

cmds = [
    'sed -i "s/^HELIUM10_EMAIL=.*/HELIUM10_EMAIL=gonthierandco@gmail.com/" /root/marcus/infra/.env',
    'sed -i "s/^HELIUM10_PASSWORD=.*/HELIUM10_PASSWORD=9zL5GR3Dq3bzi4@/" /root/marcus/infra/.env',
    'grep -E "^(HELIUM10|KEEPA)" /root/marcus/infra/.env',
]
for cmd in cmds:
    print(f"$ {cmd}")
