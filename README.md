<div align="center">

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/assets/logo-dark.svg">
  <img src="docs/assets/logo.svg" alt="X28 OpenWrt" width="120">
</picture>

# X28 OpenWrt

**OpenWrt 23.05.5 for the ZLT X28 and X28 PRO 5G routers.**

[![Release](https://img.shields.io/github/v/release/mralinp/zlt-x28-openwrt?include_prereleases&label=release)](https://github.com/mralinp/zlt-x28-openwrt/releases)
[![CI](https://github.com/mralinp/zlt-x28-openwrt/actions/workflows/ci.yml/badge.svg)](https://github.com/mralinp/zlt-x28-openwrt/actions/workflows/ci.yml)
[![License: GPL v3](https://img.shields.io/badge/license-GPLv3-blue.svg)](LICENSE)

[Get started](#get-started) · [Documentation](docs/README.md) · [Contributing](#contributing) · [Releases](https://github.com/mralinp/zlt-x28-openwrt/releases)

</div>

## What works

Tested on **X28 and X28 PRO**. The firmware provides standard OpenWrt with LuCI, 5G data, dual-band Wi-Fi, LAN, DHCP/DNS, firewall and NAT. WireGuard, OpenVPN and Passwall2 are included. **Signed firmware upgrades and package updates work**, with a kernel-compatible `opkg` feed.

This is community firmware using the vendor 4.19.205 kernel, not an official OpenWrt device image. Most feature testing was on the X28; not every feature has been verified on both models. SMS and voice are not supported yet. See [status and limitations](docs/STATUS.md) and [test evidence](docs/TESTING.md).

## Get started

Use **[x28-flasher](https://github.com/mralinp/x28-flasher)** for installation, backup and recovery—the only supported installation path.

1. Get the flasher and follow its setup instructions. If it is not public yet, wait for its release; do not flash manually.
2. Connect your router with a **USB-A to USB-C** cable (USB-C to USB-C does not work).
3. Follow the flasher's guided steps: connect, make a verified full backup, enable root access, prepare the image, flash OpenWrt and select the boot slot. Keep a second copy of your backup offline.
4. After boot, open **https://192.168.70.1/cgi-bin/luci**, accept the self-signed certificate and set a root password. SSH is available on port 22 from the LAN.

> [!WARNING]
> Flashing can brick your router. Use the flasher's safety checks; never write partitions or change the boot order by hand. Read the [recovery guide](docs/RECOVERY.md) first. Firmware upgrades write the inactive slot, so the first upgrade can replace the stock firmware fallback. Back up your settings before upgrading.

> [!NOTE]
> **Carrier unlocking:** we will provide step-by-step instructions later.

## Contributing

Bug reports, test results and pull requests are welcome.

1. [Open an issue](https://github.com/mralinp/zlt-x28-openwrt/issues) before starting work. Include your model, firmware version and relevant logs; remove credentials and device identifiers.
2. Branch from `develop` as `feature|fix|docs|chore|research/<issue>-slug`.
3. Submit a PR into `develop` with a Conventional Commit title and a reference to the issue. Include test results, anything not verified, and a safety/rollback note for changes that affect the device.

See the [contribution workflow](docs/WORKFLOW.md) for labels, milestones and review requirements.

## Documentation

The **[documentation index](docs/README.md)** covers installation, recovery, firmware upgrades, packages, hardware and development. See the [changelog](CHANGELOG.md) for release history.

## Credits and license

Built on OpenWrt and LuCI, with work from [EngineerMazeed](https://github.com/EngineerMazeed/ZLT-X28), [mt6890-cpe-recovery](https://github.com/mt6890-cpe-recovery/mt6890-cpe-recovery), [mtkclient](https://github.com/bkerler/mtkclient) and [gaglians](https://github.com/gaglians/zlt-x28-openwrt2305).

Copyright (C) 2026 Ali Naderi Parizi. Repository code is [GPL-3.0-or-later](LICENSE); third-party components retain their own licenses. Not affiliated with ZLT, Tozed, MediaTek or Quectel.
