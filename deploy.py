import deploycert, logging, os


def main():
    try:
        domainlist = os.environ["RENEWED_DOMAINS"].split(" ")
        path = os.environ["RENEWED_LINEAGE"]

        apache = deploycert.SystemdService("apache2")
        dovecot = deploycert.SystemdService("dovecot")
        postfix = deploycert.SystemdService("postfix")
        quassel = deploycert.SystemdService("quassel")

        domain2service = {
            "*.mydomain.local": (dovecot.reload, postfix.reload, deploycert.update_quassel(quassel, path)),
            "www.mydomain.local": apache.reload,
            "wiki.myotherdomain.local": apache.reload
        }

        deploycert.logger.info("Renewed domains: %s, Path: %s", domainlist, path)
        errorlist = deploycert.executor(domainlist, domain2service)

        # Output all failed services with their error messages
        if errorlist:
            for error in errorlist:
                print("{0} failed: {1}".format(error[0], error[1]))
            exit(1)
        else:
            deploycert.logger.info("Success")
            print("Success")
            exit(0)
    except KeyError as k:
        print("Environment variable {0} not set!".format(k))
        exit(1)


if __name__ == '__main__':
    deploycert.logger = logging.getLogger("deploycert")
    logging.basicConfig(level=logging.CRITICAL)
    main()
