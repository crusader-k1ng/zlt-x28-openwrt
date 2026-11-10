#!/bin/sh
# LED polling against netifd/interface fixtures; no modem or LED device writes.
set -eu
leds=$(dirname "$0")/../package/x28-leds/files/x28-leds
eval "$(sed '/^case "\$1" in/,$d' "$leds")"
at() { case "$1" in 'AT+COPS?') echo '0,0,"test",7';; 'AT+CESQ') echo '0,0,0,0,0,58,0,255';; esac; }
ubus() { case "$2" in network.interface.wan) echo wan;; network.wireless) echo wireless;; esac; }
jsonfilter() {
	read -r input
	case "$input:$2" in
		wan:@.up) echo true;;
		'wireless:@[@.up=true && @.disabled=false].interfaces[*].ifname') printf '%s\n' "$active";;
		*) return 1;;
	esac
}
ip() {
	[ "$*" = 'link show up' ] && { echo '36: ra0: <UP,LOWER_UP>'; return; }
	[ "$5" != missing ] || return 1
	case " $links " in *" $5 "*) echo "36: $5: <UP,LOWER_UP>";; *) echo "36: $5: <NO-CARRIER,UP>";; esac
}
check() {
	active=$1 links=$2
	got=$(poll | sed -n 's/^6 //p')
	[ "$got" = "$3 0" ] || { echo "Wi-Fi LED: expected $3, got $got (active=$active links=$links)"; exit 1; }
}
check '' ra0 0             # Disabled/down radios must ignore a stale helper interface.
check ra0 ra0 1
check rai0 'ra0 rai0' 1    # One enabled band is enough.
check rai0 ra0 0           # Enabled radio but its actual interface is down.
check missing ra0 0       # Missing interface is not working Wi-Fi.
check 'ra0
rai0' rai0 1               # A failed band must not hide a healthy band.
echo 'PASS: Wi-Fi LED follows active wireless interfaces, not helper interfaces'
