# UPV Inter-Slice Connectivity Demonstration

Project: Imagine (https://www.notion.so/Imagine-7086dc437a4f44f4b49336b275434f51?pvs=21)
Author: Rafael Direito
NoteType: Wiki
Creation Time: June 27, 2025 12:23 PM
Last Edited Time: June 27, 2025 6:06 PM
❤️: No
Status: Inbox
Archived: No

# IMAGINE-B5G ITAv-UPV Inter-Domain Network Slice Orchestration

For achieving an inter-domain network slice between ITAv and UPV, we rely on a VPN link between the two facilities. The orchestration of this VPN link relies on 3 core modules/components:

- openvpn (service)
- A REST API that allows for starting the VPN link, shutting it down, and check its status
- A cronjob that continuously checks if a VM in UPV’s domain is reachable

## 1. OpenVPN Service

[upv_vpn_aveiro.zip](UPV%20Inter-Slice%20Connectivity%20Demonstration%2021f11fa2ed8d80168a1be6b713a38101/upv_vpn_aveiro.zip)

[UPV testbed access - Guidelines.pdf](UPV%20Inter-Slice%20Connectivity%20Demonstration%2021f11fa2ed8d80168a1be6b713a38101/UPV_testbed_access_-_Guidelines.pdf)

The configuration of OpenVPN requires installing openvpn and placing the configuration files under `/etc/openvpn/`. If the config file is named `upv_vpn_aveiro.conf`, the VPN link can be started with: `systemctl start openvpn@upv_vpn_aveiro` .

This service will start automatically when the VM boots. To prevent this, it is needed to update `vim /etc/default/openvpn` and set `AUTOSTART="none"` . This prevents starting the VPN connection when the VM boot.

## 2.  UPV VPN Control REST API

To start and stop the VPN connection, a minimal REST API was implemented with FastAPI. This API invokes `systemctl` commands to start and stop the VPN connection. Therefore, given this is just a PoC, this API must be executed by the root user (This is insecure, and the correct user permissions should be configure. But again, this is just a simplistic PoC). The REST API is available on this repository, inside the `api` directory. 

The REST API has 3 endpoints:

- /vpn/start → protected with HTTP Basic Auth and used to start the VPN connection
- /vpn/stop → protected with HTTP Basic Auth and used to stop the VPN connection
- /vpn/status → unprotected endpoint that allows checking the VPN connection status

The API credentials are the following:

- username: admin
- password: secret

Regarding the process for checking if the VPN link is allowing  ITAv’s VMs to communicate with the ones on UPV, a cronjob was created. This cronjob will be addressed in the next section, but it is important to state that it produces a file (`/tmp/upv_vpn_aveiro_status`) with the content `OK` or  `NOT_OK` . When the /vpn/status endpoint is invoked, the API will check the previous file and return a response according to its content.

This REST API is already pre-loaded in the VM Image through which the VPN link between ITAv and UPV will be realized. 

The first step to achieve this was installing the API’s requirements. Since the API will be run by the root user, this should be taken into consideration when installing the python requirements. The API main file (`vpn_status_api.py`) was placed in  `/usr/local/bin/`.

Afterwards, a service was created to run the API when the VM boots, thus ensuring the API is offered out of the box. The service was created in `/etc/systemd/system/vpn-api.service` .

Contents of `/etc/systemd/system/vpn-api.service` :

```bash
[Unit]
Description=FastAPI VPN Control API
After=network.target

[Service]
Type=simple
WorkingDirectory=/usr/local/bin
ExecStart=/usr/bin/python3 -m uvicorn vpn_status_api:app --host 0.0.0.0 --port 8000 --app-dir /usr/local/bin
Environment=API_USERNAME=admin
Environment=API_PASSWORD=secret
Restart=always
User=root

[Install]
WantedBy=multi-user.target
```

As you can see, the API will be available on port 8000.

Then, we enabled this service, so it starts on boot:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now vpn-api.service
```

## 3.  Connectivity Status Cronjob

As previously sated, the REST API relies on the content of a file to inform its clients if the VPN link is working or not. The content of that file is set through a Cronjob that continuously evaluates if UPV VMs are reachable from within ITAv. For this effect the *ping* tool is used.

The cron job runs every 10 seconds, and runs a ping command that sends 5 ICMP packets. If more than 50% of these packets reach UPV, then the VPN link is considered as active. Else, as not active. Based on this, the cronjob will update the content of `/tmp/upv_vpn_aveiro_status`.

For the cronjob to know which IP to ping, an additional file is required. This file should be placed in `/home/ubuntu/vpn_check_ip` and should only contain one line with the IP to ping on UPV’s domain. By relying on a file, we can update the IP to ping though cloudinit, when we deploy the UPV VPN cloud Image.

In a similar way to the REST API, the cronjob is already pre-loaded in the VM Image through which the VPN link between ITAv and UPV will be realized. To this end, we have developed a python script and placed it in `/usr/local/bin/vpn_status_check.py` . 

Afterwards, we proceeded with the implementation of a systemd service to run our script.

Contents of `/etc/systemd/system/vpn-status-check.service`:

```bash
[Unit]
Description=Check VPN status and update status file

[Service]
Type=oneshot
ExecStart=/usr/local/bin/vpn_status_check.py
```

Then we proceed with the creation of a systemd timer, to invoke the just created service every 10 seconds.

Contents of `/etc/systemd/system/vpn-status-check.timer`:

```bash
[Unit]
Description=Run VPN status check every 10 seconds

[Timer]
OnBootSec=10
OnUnitActiveSec=10
AccuracySec=1s
Unit=vpn-status-check.service

[Install]
WantedBy=timers.target
```

Finally, we enabled the timer:

```bash
sudo systemctl daemon-reexec
sudo systemctl daemon-reload
sudo systemctl enable --now vpn-status-check.timer
```

# VPN Link Orchestration Cloud Image

To facilitate the orchestration of the VPN tunnel between ITAv and UPV a qcow2 cloud image was created. This image already comprises all the previously addressed components, and therefore will make them available when booted.

The image is available on ATNoG’s Openstack (Jarvis) and is named `upv-vpn-cloud-image`. Additionally, to ensure that the VPN link is always available through the same IP, we also created a network port named `upv-vpn-link-port` and assigned it the IP `10.255.40.250`. This network port needs to have **port security DISABLED**, otherwise it will drop all packets coming from UPV.

When deploying this cloud image, the network port should be attached to the VM, as specific routes will be configured in ATNoG’s network and they consider that the VPN link is available through the previous IP.

To provision the VM you should:

- use the `upv-vpn-cloud-image` qcow2 image
- use the `2cpu2ram32disk` flavor
- do not use a volume
- use an appropriate security group that enables traffic to be steered through this VM
- attach the `upv-vpn-link-port` network port
- configure the VM credentials through cloud-init or use an SSH key

To set the VM credentials to ubuntu:password and update the IP that is queried by the cronjob, on UPV’s facility, you may use the following cloud-init:

```yaml
#cloud-config
password: password
chpasswd: { expire: False }
ssh_pwauth: True

write_files:
  - content: |
      1.1.1.1
    path: /home/ubuntu/vpn_check_ip
    permissions: '0644'
    owner: ubuntu:ubuntu

runcmd:
  - chown ubuntu:ubuntu /home/ubuntu/vpn_check_ip
```