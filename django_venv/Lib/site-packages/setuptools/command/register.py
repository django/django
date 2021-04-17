from distutils import log
import distutils.command.register as orig


class register(orig.register):
    __doc__ = orig.register.__doc__

    def run(self):
        try:
            # Make sure that we are using valid current name/version info
            self.run_command('egg_info')
            orig.register.run(self)
        finally:
            self.announce(
                "WARNING: Registering is deprecated, use twine to "
                "upload instead (https://pypi.org/p/twine/)",
                log.WARN
            )
