import time

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
            ('setup', '[<argon>] [<hgcd>] [<krypton>] [<neon>] [<xenon>] [<halogen>]', self.setup),
            ('go', '', self.go),
            ('status', '', self.status),
            ('pi', '@raw', self.raw),
        ]

        # Define typed command arguments for the above commands.
        self.keys = keys.KeysDictionary("lamps_lamps", (1, 1),
                                        keys.Key("argon", types.Int(), help="Ar lamp time"),
                                        keys.Key("hgcd", types.Int(), help="HgCd lamp time"),
                                        keys.Key("krypton", types.Int(), help="Kr lamp time"),
                                        keys.Key("neon", types.Int(), help="Ne lamp time"),
                                        keys.Key("xenon", types.Int(), help="Xe lamp time"),
                                        keys.Key("halogen", types.Int(), help="Quartz lamp time"),
                                        )

        self.lampNames = ('argon', 'krypton', 'neon', 'xenon', 'hgcd', 'halogen')

    @property
    def pi(self):
        return self.actor.controllers['lamps_pi']

    def raw(self, cmd):
        """ Send a raw command to the controller. """

        cmd_txt = cmd.cmd.keywords['raw'].values[0]

        ret = self.pi.lampsCmd(f'raw {cmd_txt}', cmd=cmd)
        cmd.finish('text=%s' % (qstr('returned: %s' % (ret))))

    def setup(self, cmd):
        """Configure the calibration system lamps for the given exposure times. """

        cmdkeys = cmd.cmd.keywords
        if 'hgcd' in cmdkeys and 'halogen' in cmdkeys:
            cmd.fail('text="halogen and hgcd cannot both be specified"')
            return

        lamps = []
        for name in self.lampNames:
            if name in cmdkeys:
                val = cmdkeys[name].values[0]
                val = int(val)
                if name == 'halogen':
                    name = 'cont'
                lamps.append(f'{name}={val}')

        if len(lamps) == 0:
            cmd.fail('text="at least one lamp must be specified"')
            return

        setupCmd = f'setup {" ".join(lamps)}'
        ret = self.pi.lampsCmd(setupCmd)
        cmd.finish(f'text="{ret}"')

    def _getStatus(self, cmd):
        """Get current lamp status."""

        ret = self.pi.lampsCmd('status')
        ok, running, ready = ret.split()
        if ok != 'OK':
            raise RuntimeError(f'status is bad: {ret}')
        running = bool(running)
        ready = bool(ready)

        return running, ready

    def go(self, cmd):
        """Given the already configured lamps, run the sequence """

        while True:
            running, ready = self._getStatus(cmd)
            if not running:
                cmd.fail('text="lamps are not configured"')
                return
            if ready:
                break
            time.sleep(0.2)

        ret = self.pi.lampsCmd('go')
        cmd.finish(f'text="{ret}"')

    def stop(self, cmd):
        """Given a running or merely configured sequence, stop it."""

        ret = self.pi.lampsCmd('stop')
        cmd.finish(f'text="{ret}"')

    def status(self, cmd):
        """Get current lamp status."""

        ret = self.pi.lampsCmd('status')
        cmd.finish(f'text="{ret}"')
