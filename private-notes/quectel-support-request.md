# Support request draft: RG500L-EU, IMS registered, VoLTE call active but no voice media

To: Quectel technical support (RG500L-EU), cc MediaTek channel if available.
Contains no SIM identifiers, phone numbers or credentials. Add them only if support asks.

## Summary
RG500L-EU in an embedded-Linux CPE (MT6890 application processor, modem on the same SoC, no USB/PCIe link; AT access through the vendor `mipc_wan_cli --at_cmd`).
IMS registers on MCI (Iran, MCC/MNC 432/11) and calls go to the active state, but the modem never sets up a voice media bearer,
no speech path is started, and the network clears every call about 20 seconds after answer. The same SIM does VoLTE in a smartphone.

## Firmware
- Modem: `RG500LEUAPR04A01M1G_OCPU_BETA20231220`, baseband `MOLY.NR15.R3.MD700.MP.V53.5.P98`.
- Application side: OpenWrt 23.05.5 userspace on the vendor 4.19.205 kernel; stock voice daemons (`speech_daemon`,
  `libmodem-afe-ctrl-server-bin`, `audio-ctrl-service`) staged and running and connected to the modem (`/dev/ccci_aud`, `ccci_raw_audio`).

## Configuration (all verified by read-back)
- `AT+CGDCONT`: CID0 `mcinet` (internet), CID1 `ims` = `1,"IPV4V6","ims","",0,0,0,2,1,1,0,1,0`.
- `AT+QCFG="ims"` = `0,1`; `AT+CIREG?` = `2,1,5`; `mipc_wan_cli --ims_get_status` = Registered; `--ims_get_config` = On(3).
- `AT+ECFGGET`: `operator_code` 16386 (set to get IMS to register; before that IMS stayed unregistered), `voice_support` 0, `mncmcc_whitelist` empty, `mncmcc_pass_flag` 0, `sms_over_ip` 1.
- `AT+CEVDP?` = 3, `AT+CEUS?` = 1, `AT+CREG?` = `0,6` (SMS only, no CS fallback), `AT+COPS?` = `0,2,"43211",13`.

## Observed during a call (incoming and outgoing behave the same)
- `AT+CLCC` -> `1,<dir>,0,20,0,"<number>",145` (active, mode 20).
- `AT+CGEQOSRDP` empty; `AT+CGCONTRDP` lists only the internet bearer and the default `ims` bearer: **no dedicated QCI-1 voice bearer**.
- No ALSA stream opens; `speech_daemon` logs no speech-on message from the modem.
- `ccmni2` (ims) packet counters do not move: IMS signalling is internal to the modem.
- Call ends about 20 s after answer, `AT+CEER` = `16,CM_NORMAL_CALL_CLR`.

## Tried without effect (each with a real call, then rolled back)
`voice_support` 0/1; `operator_code` 16386/0; whitelist `112113432` with `voice_support` 1 (public MTK guide for MCI);
4G-only (`--nw_set_rat 3`) versus 4G/5G NSA; `AT+CEUS` 0/1; incoming versus outgoing (`ATD`).

## Questions
1. Which settings or configuration (MBN/MCF carrier profile, `AT+QCFG`, `AT+ECFGSET` keys) does this build need so the modem requests the QCI-1 bearer and starts the speech path for IMS calls on MCI?
2. What does `<mode>` 20 in `AT+CLCC` mean on this build, and is the call really carried over IMS?
3. Is there an AT command or log (modem log, IMS log) to see the SIP INVITE/response and bearer setup, and how do we enable it on an embedded-Linux host?
4. Is the carrier profile for MCI (432 11) present in this firmware? `AT+EMCFC=4,0/1/2` returns empty paths.
5. Does this firmware support the call audio route over the SoC speech interface (hostless speech, ETDM) without an Android audio HAL?
