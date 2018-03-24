# deploycert
Automatic deployment of let's encrypt certificates via certbot's deploy-hook

This is basically a toy project of me to get to know python - it's quite over-engineered,
using classes to model init services and so on. A equivalent bash script might be
smaller, although it might lack the error handling/logging functionality.

Despite being a test project of mine, it *is* useful - you can map certificate's 
domains to services. For example, "myhost.mydomain.tld" might be used for postfix, dovecot 
and apache2, "www.mydomain.tld" only by apache2 (a typical vhost). If your 
certificate contains both myhost.mydomain.tld, the program will make sure 
that apache2 will be reloaded only once (instead of two times, one for myhost 
and the second one for www)

I've included an example script (deploy.py)

