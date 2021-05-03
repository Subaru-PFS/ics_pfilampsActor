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
            ('prepare', '[halogen] [argon] [hgcd] [krypton] [neon] [xenon]', self.prepare),
            ('go', '', self.go),
            ('status', '', self.status),
            ('pi', '@raw', self.raw),
        ]

        # Define typed command arguments for the above commands.
        self.keys = keys.KeysDictionary("lamps_lamps", (1, 1),
                                        keys.Key("argon", types.Float(), help="Ar lamp time"),
                                        keys.Key("hgcd", types.Float(), help="HgCd lamp time"),
                                        keys.Key("krypton", types.Float(), help="Kr lamp time"),
                                        keys.Key("neon", types.Float(), help="Ne lamp time"),
                                        keys.Key("xenon", types.Float(), help="Xe lamp time"),
                                        keys.Key("halogen", types.Float(), help="Quartz lamp time"),
                                        )

    @property
    def pi(self):
        return self.actor.controllers['lamps_pi']

    def raw(self, cmd):
        """ Send a raw command to the controller. """

        cmd_txt = cmd.cmd.keywords['raw'].values[0]

        ret = self.pi.lampsCmd(cmd_txt, cmd=cmd)
        cmd.finish('text=%s' % (qstr('returned: %s' % (ret))))

    def prepare(self, cmd):
        """Configure the calibration system lamps for the given exposure times. """

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
