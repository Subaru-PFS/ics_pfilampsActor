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
            ('prepare', 'lamps [<argon>] [<hgcd>] [<krypton>] [<neon>] [<xenon>] [<halogen>]', self.prepare),
            ('go', '[<delay>]', self.go),
            ('status', '', self.status),
            ('allstat', '', self.allstat),
            ('waitForReadySignal', '', self.waitForReadySignal),
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
                                        keys.Key("delay", types.Float(), help="time to delay start for")
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

    def prepare(self, cmd):
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

    def waitForReadySignal(self. cmd, doFinish=True):
        maxtime = 2
        if 'hgcd' in self.request:
            maxtime = 130

        lastRunning, lastReady, lastCooling = None
        startTime = time.time()
        while True:
            running, ready, cooling = self._getStatus(cmd)
            if running != lastRunning or ready != lastReady or cooling != lastCooling:
                self.genStatusKey(running, ready, cooling)
                lastRunning = running
                lastReady = ready
                lastCooling = cooling
            if not running:
                cmd.fail('text="lamps are not configured"')
                return
            if ready:
                break

            now = time.time()
            if now - startTime > maxtime:
                cmd.fail(f'text="lamps did not turn on in {maxtime} seconds.... stopping lamps command"')
                self.request = {}
                self.requestVisit = None
                self.pi.lampsCmd('stop')
                self.genKeys(cmd)
                return

            time.sleep(0.2)

        if doFinish:
            cmd.finish()

    def go(self, cmd, doWait=False):
        """Given the already configured lamps, run the sequence """

        if len(self.request) == 0:
            cmd.fail('text="No lamps requested"')
            return

        self.waitForReadySignal(cmd, doFinish=False)

        ret = self.pi.lampsCmd('go')
        self.genKeys(cmd)
        time.sleep(0.5)
        self.allstat(cmd, doFinish=False)
        cmd.finish()


    def stop(self, cmd):
        """Given a running or merely configured sequence, stop it."""

        ret = self.pi.lampsCmd('stop')
        cmd.finish(f'text="{ret}"')

    def status(self, cmd):
        """Get current lamp status."""

        ret = self.pi.lampsCmd('status')
        cmd.finish(f'text="{ret}"')
    def _allstat(self, cmd):
        """Fetch and parse fan speed and lamp output

        200318:182439 Fans 0
        Ne   off v=0.0283  vc=0.00
        Ar   off v=0.0286  vc=0.00
        Kr   off v=0.0286  vc=0.00
        Xe   off v=0.0283  vc=0.00
        Hg   off v=0.0287  vc=0.00
        Cd   off v=0.0286  vc=0.00
        Cont off v=0.0297  fs=0

        """

        ret = self.pi.lampsCmd('allstat')
        statusLines = []
        statusDict = dict()

        for l in ret:
            l = l.strip()
            if not l:
                continue
            statusLines.append(l)

        fansLine = statusLines[0]
        udt, _, fans = fansLine.split()
        statusDict['fans'] = fans

        for l in statusLines:
            name, status, rawReading, reading = ret[chan_i+1].split()
            _, rawReading = rawReading.split('=')
            rawReading = float(rawReading)

            readingName, reading = reading.split('=')
            reading = float(reading)

            statusDict[f'{name}_state'] = status
            statusDict[f'{name}_raw'] = rawReading

            if name == 'Cont':
                if readingName == 'fs':
                    statusDict['cont_fanspeed'] = reading
                    statusDict['cont'] = -9999
                else:
                    statusDict['cont_fanspeed'] = -9999
                    statusDict['cont'] = reading
            else:
                statusDict[name] = reading

        return statusDict

    def allstat(self, cmd):
        statDict = self._allstat(cmd)
        for k, v in statDict.items():
            cmd.inform(f'{k}={v}')
        cmd.finish(f'')
