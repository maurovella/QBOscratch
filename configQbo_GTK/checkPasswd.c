// gcc -lcrypt checkPasswd.c -o checkPasswd
// hay que hacer un cat de /etc/shadow para pillar el salt, 
// entonces pasarlo a crypt junto con el password a checkear.
// e resultado de crypt() compararlo con el del cat.
 
#define _XOPEN_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <unistd.h>
#include <crypt.h>

int main (void)
{
    char *passwd;
    passwd = crypt("raspberry", "$6$xNAkaz9i");
    printf("passwd: %s\n", passwd);

    system("sudo cat /etc/shadow | grep pi");
}
