# ODROID-HC1 flash-to-SSH bootstrap

Status: **incremental physical bring-up path**

This path exists to get the current JETOS Python userspace onto the physical ODROID-HC1 quickly enough to test it over the network. It is intentionally transitional: the image starts from a **known-bootable HC1 Linux base image** so that bootloader/kernel/device-tree bring-up can proceed independently from JETOS userspace and remote-administration testing.

It does **not** claim that the final JETOS-owned HC1 boot chain is complete.

## What the bootstrap produces

`tools/hc1_flash.py` prepares a raw microSD image that:

- retains the supplied HC1 bootloader, kernel, device tree, and ARMv7 userspace as temporary imported substrate;
- copies the current `src/jetos/` tree into `/opt/jetos/src/jetos`;
- records the machine as `armv7` / `odroid-hc1` in `/etc/jetos/target.json`;
- configures wired DHCP through `systemd-networkd`;
- enables OpenSSH for **public-key-only root login**;
- installs `jetos-console`, which opens the JETOS Python control console;
- records SHA-256 provenance for the supplied base image and prepared output image;
- never mounts, formats, probes destructively, or otherwise modifies the HC1 SATA disk.

## Base-image requirements

The supplied base image must already be known to boot on the ODROID-HC1 and must contain an ARMv7 Linux userspace with:

- Python 3;
- OpenSSH `sshd`;
- `ssh-keygen`;
- systemd and `systemd-networkd`;
- a writable root filesystem partition (partition 2 by default).

JETOS does not download a base image automatically. The operator chooses and verifies the imported boot substrate explicitly.

## 1. Review the plan

```text
python tools/hc1_flash.py plan \
  --base-image /path/to/hc1-base.img.xz \
  --authorized-keys ~/.ssh/id_ed25519.pub \
  --device /dev/sdX
```

`plan` is non-destructive.

## 2. Prepare the JETOS image

Image preparation currently requires a Linux host with root privileges because it uses Linux loop devices and mounts the root partition while injecting the JETOS payload.

```text
sudo python tools/hc1_flash.py prepare \
  --base-image /path/to/hc1-base.img.xz \
  --authorized-keys ~/.ssh/id_ed25519.pub
```

Default output:

```text
.build/jetos-hc1-ssh.img
.build/jetos-hc1-ssh.img.json
```

The input may be raw, `.gz`, or `.xz`; decompression uses the Python standard library.

If the base image uses a different root partition, pass for example:

```text
--root-partition 1
```

## 3. Flash a dedicated microSD card

**This step erases the selected block device.** Identify the microSD device independently before running it. Do not use the HC1 SATA disk as the target.

The tool refuses non-block devices, mounted targets, targets smaller than the image, and any flash request whose confirmation string does not exactly match the resolved device path.

```text
sudo python tools/hc1_flash.py flash \
  --image .build/jetos-hc1-ssh.img \
  --device /dev/sdX \
  --confirm-device /dev/sdX
```

## 4. Boot the HC1

1. Power the HC1 off.
2. Insert the dedicated JETOS bootstrap microSD card.
3. Connect wired Ethernet.
4. Power the HC1 on.
5. Find the DHCP lease/address assigned to hostname `jetos-hc1`.

Then connect with the private key corresponding to the public key injected during `prepare`:

```text
ssh root@<hc1-ip-address>
```

Password authentication is intentionally disabled.

## 5. Enter the JETOS Python console

After SSH login:

```text
jetos-console
```

The machine should also expose its bootstrap identity:

```text
cat /etc/jetos/target.json
```

Expected target fields include:

```text
"board": "odroid-hc1"
"cpu_arch": "armv7"
"mode": "incremental-linux-bootstrap"
"sata_policy": "untouched"
```

## Qualification for this milestone

This bootstrap milestone is successful when the physical HC1 repeatedly:

1. boots from the dedicated microSD image;
2. obtains a wired DHCP address;
3. accepts key-only SSH login;
4. launches `jetos-console`;
5. reports `armv7` / `odroid-hc1` correctly;
6. leaves attached SATA data untouched.

After that is stable, JETOS can replace the temporary base-image pieces incrementally: first target-native CPython/rootfs qualification, then the JETOS-selected kernel/device tree, then the board bootloader/image path. The Python-facing behavior should remain stable while those lower layers are replaced.
