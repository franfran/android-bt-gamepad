/* RetroBox M3: non-invasive Bluetooth Classic socket capability probe.
 * This program DOES NOT bind, listen, connect, send HCI commands, or pair.
 * It only tries creating and closing sockets.
 * SPDX-License-Identifier: MIT
 */
#include <errno.h>
#include <stdio.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>

#ifndef AF_BLUETOOTH
#define AF_BLUETOOTH 31
#endif
#ifndef BTPROTO_L2CAP
#define BTPROTO_L2CAP 0
#endif
#ifndef BTPROTO_HCI
#define BTPROTO_HCI 1
#endif

static void probe(const char *name, int type, int protocol) {
    errno = 0;
    int fd = socket(AF_BLUETOOTH, type, protocol);
    if (fd < 0) {
        printf("%-24s UNAVAILABLE errno=%d (%s)\n", name, errno, strerror(errno));
        return;
    }
    printf("%-24s AVAILABLE fd=%d (creation only)\n", name, fd);
    close(fd);
}

int main(void) {
    puts("RetroBox M3 Bluetooth socket probe v0.1 (read-only)");
    probe("L2CAP SEQPACKET", SOCK_SEQPACKET, BTPROTO_L2CAP);
    probe("L2CAP RAW", SOCK_RAW, BTPROTO_L2CAP);
    probe("HCI RAW", SOCK_RAW, BTPROTO_HCI);
    puts("Note: AVAILABLE does not establish that binding, incoming DS3 HID, or coexistence with Android Bluetooth works.");
    return 0;
}
