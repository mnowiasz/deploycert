""" Restarts the services using the given certificates """

import collections
import logging
import shutil
import subprocess
import tempfile

# logger used in this module
logger = logging.getLogger()


class InitService(object):
    """ A classic init.d system - /etc/init.d/<service> (start|stop|restart)"""
    _service_string = "/etc/init.d/{0} {1}"

    def __init__(self, service_name: str, timeout: int = 10):
        """
        :param service_name: the service name, i.e. apache, bind...
        :type service_name: stre
        :param timeout: Timeout for executing the job
        :type timeout: int
        """
        self._service_name = service_name
        self._timeout = timeout

        # Avoid unneccessary restarts/reloads of the service. For example, there might be dependencies: service A
        # should stop service B and C, after restarting A service B C are started again. But since service B and C
        # are also using the certificate, this would result in restarting B and C again - which is unneccessary,
        # may take some time (consider restarting a very large DBM) and causes downtime which can be avoided.

        self._started = True
        self._restarted = False
        self._reloaded = False

    def __str__(self):
        return self._service_name

    def _execute(self, command: str):

        logger.info("Executing %s", command)
        subprocess.call(command.split(" "), timeout=self._timeout)

    def start(self):
        """ Starts the service if previously stopped  """
        if self._started is False:
            self._execute(self._service_string.format(self._service_name, "start"))
            self._started = True

            # Stopping and starting a service is tantamount to restarting it.
            self._restarted = True

    def stop(self):
        """ If running stop the service """
        if self._started is True:
            self._execute(self._service_string.format(self._service_name, "stop"))
            self._started = False

    def restart(self):
        """ Restart the service"""

        # If the service should have been stopped (for what ever reason) as restart  will start it

        if self._restarted is False or self._started is False:
            self._execute(self._service_string.format(self._service_name, "restart"))
            self._started = True
            self._restarted = True

    def reload(self):
        """ Reload the service """

        if self._reloaded is False:
            self._execute(self._service_string.format(self._service_name, "reload"))
            self._reloaded = True


class SystemdService(InitService):
    """ systemd: systemctl (start|stop|restart) <service>"""
    _service_string = "systemctl {1} {0}"

    def __init__(self, service_name: str):
        """
        :param service_name: The name of the service (apache2, ..) Note: .service will be automatically appended.
        :type service_name: str
        """
        super().__init__(service_name + ".service")


def executor(domainlist: list, domain2service: dict, finaljob: object = None) -> list:
    """
    :param domainlist: domains in the certificate
    :type domainlist: list
    :param domain2service: Mapping domain to services
    :type domain2service: dict
    :param finaljob: An optional job to execute after all the others has been done (usually apache)
    :type finaljob: object
    :return A list containing tuples of failed services (service, exception message)
    :rtype list

    Stop/Start or restart all involved services
    """
    joblist = []
    errorlist = []

    # Build the joblist
    for domain in domainlist:
        service = domain2service.get(domain)
        if service is not None:
            # service might be a tuple or a list - when multiple services are using the same domain
            if isinstance(service, collections.Iterable):
                joblist.extend(service)
            else:
                joblist.append(service)

    if finaljob is not None:
        joblist.append(finaljob)

    # Do it

    for job in joblist:
        # Catch all exception, because a failed restart of a service shouldn't affect other services
        try:
            job()
        except Exception as e:
            logger.error(e)
            # Since "job" can be a method or a plain function, __self__ might not be defined
            if hasattr(job, "__self__"):
                errorlist.append((job.__self__, str(e)))
            else:
                errorlist.append((str(job), str(e)))
    return errorlist


# Make a backup of the file in question
def safe_copy(source: str, destination: str):
    """

    :param source: Source filename
    :type source: str
    :param destination: Destination filename
    :type destination: str

    Makes a copy of the destination file, (destination.old) before coping the source to the destination
    """

    try:
        shutil.copyfile(destination, destination + ".old")
    except OSError:
        # There might be legitimate reasons why the original file isn't there.
        logger.warning("%s does not exist", destination)

    shutil.copyfile(source, destination)


# quassel requires it's certificate to be under /var/lib/quassel. symlinking doesn't work. Furthermore,
# quassel requires the certificate and the key to be in the same PEM
def update_quassel(service: object, path: str, destination: str = "/var/lib/quassel/quasselCert.pem") -> object:
    """
    :param service: The quassel object
    :type service: Object
    :param path: Source path of the certificate in question
    :type path: str
    :param destination: Destination of the certificate (/var/lib/quassel/quasselCert.pem)
    :type destination: str
    :return: Closure
    :rtype: object
    """

    def doit():
        filenames = ("privkey.pem", "fullchain.pem")

        logger.info("Merging %s into %s", filenames, destination)

        # To make sure that the (still valid) certificate won't be empty due to IO errors, create a temporary
        # file and than copy it to the final destination (after backing up the old file)

        with tempfile.NamedTemporaryFile() as tmpfile:
            for file in filenames:
                with open(path + "/" + file, 'rb') as infile:
                    shutil.copyfileobj(infile, tmpfile)
            tmpfile.file.flush()
            safe_copy(tmpfile.name, destination)

        service.restart()

    return doit


# Just copy the files, no need to restart the service
def update_synapse(path: str, destination: str) -> object:
    """

    :param path: Source path of the certificate in questing
    :type path: str
    :param destination: Synapse's installation (/home.../.synapse/)
    :type destination: str
    :return: Closure
    :rtype: object
    """

    def doit():
        filenames = ("privkey.pem", "fullchain.pem")

        logger.info("Copying %s to %s", filenames, destination)

        for file in filenames:
            safe_copy(path + "/" + file, destination + "/" + file)

    return doit
