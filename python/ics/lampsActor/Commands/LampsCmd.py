import opscore.protocols.keys as keys
import opscore.protocols.types as types
from opscore.utility.qstr import qstr

class LampsCmd(object):

    def __init__(self, actor):
        # This lets us access the rest of the actor.
        self.actor = actor

        # Declare the commands we implement. When the actor is started
        # these are registered with the parser, which will call the
        # associated methods when matched. The callbacks will be
        # passed a single argument, the parsed and typed command.
        #
        self.vocab = [
            ('setupArcs', '[<ar>] [<hgcd>] [<kr>] [<ne>] [<xe>] [<qth>]', self.setupArcs),
            ('setupContinuum', '[<qth>]', self.setupContinuum),
            ('go', '', self.go),
            ('stop', '', self.cancel),
            ('status', '', self.status),
        ]

        # Define typed command arguments for the above commands.
        self.keys = keys.KeysDictionary("lamps_lamps", (1, 1),
                                        keys.Key("ar", types.Float(), help="Ar lamp time"),
                                        keys.Key("hgcd", types.Float(), help="HgCd lamp time"),
                                        keys.Key("kr", types.Float(), help="Kr lamp time"),
                                        keys.Key("ne", types.Float(), help="Ne lamp time"),
                                        keys.Key("Xe", types.Float(), help="Xe lamp time"),
                                        keys.Key("qtz", types.Float(), help="Quartz lamp time"),
                                        )

    def setupArcs(self, cmd):
        """Configure the calibration system arc lamps for the given exposure times. """

        cmd.finish("text='Present and (probably) well'")

    def setupQuartz(self, cmd):
        """Configure the calibration system continuum lamp for the given exposure time. """

        cmd.finish("text='Present and (probably) well'")

    def go(self, cmd):
        """Given the already configured lamps, run the sequence """

        cmd.finish()

    def stop(self, cmd):
        """Given a running or merely configured sequence, stop it."""

        cmd.finish()

    def status(self, cmd):
        """Get current lamp status."""

        cmd.finish()
