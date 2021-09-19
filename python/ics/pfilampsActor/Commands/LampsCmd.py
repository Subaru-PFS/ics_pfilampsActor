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
            ('prepare', '[<argon>] [<hgcd>] [<krypton>] [<neon>] [<xenon>] [<halogen>]', self.prepare),
            ('go', '[<delay>] [@noWait]', self.go),
            ('stop', '', self.stop),
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

        self.lampNames = ('neon', 'argon', 'krypton', 'xenon', 'hgcd', 'halogen')
        self.piLampNames = ('neon', 'argon', 'krypton', 'xenon', 'hgcd', 'cont')

        self.request = {}

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
        request = {}
        maxtime = 0
        for name in self.lampNames:
            if name in cmdkeys:
                val = cmdkeys[name].values[0]
                val = int(val)
                if name == 'halogen':
                    name = 'cont'
                lamps.append(f'{name}={val}')
                request[name] = val
                maxtime = max(maxtime, val)
        self.requestTime = maxtime
        self.request = {}
        self.genVisitKeys(cmd)

        self.request = request

        if len(lamps) == 0:
            cmd.fail('text="at least one lamp must be specified"')
            return

        setupCmd = f'setup {" ".join(lamps)}'
        ret = self.pi.lampsCmd(setupCmd)

        self.genStatusKey(cmd, *self._getStatus(cmd))
        cmd.finish()

    def genStatusKey(self, cmd, running, ready, cooling):
        cmd.inform(f'calibState={running},{ready},{cooling}')

    def _getStatus(self, cmd):
        """Get current lamp status."""

        ret = self.pi.lampsCmd('status')
        ok, running, ready, cooling = ret.split()
        if ok != 'OK':
            raise RuntimeError(f'status is bad: {ret}')
        running = int(running)
        ready = int(ready)
        cooling = int(cooling)

        return running, ready, cooling

    def waitForReadySignal(self, cmd, doFinish=True):
        maxtime = 2
        if 'hgcd' in self.request:
            maxtime = 130

        lastRunning = lastReady = lastCooling = None
        startTime = time.time()
        while True:
            running, ready, cooling = self._getStatus(cmd)
            if running != lastRunning or ready != lastReady or cooling != lastCooling:
                self.genStatusKey(cmd, running, ready, cooling)
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
                self.pi.lampsCmd('stop')
                self.genVisitKeys(cmd)
                return

            time.sleep(0.2)

        if doFinish:
            cmd.finish()

    def stop(self, cmd):
        """Stop any lamp command, and turn off lamps. """

        ret = self.pi.lampsCmd('stop')
        self.request = {}
        self.genStatusKey(cmd, *self._getStatus(cmd))
        self.genVisitKeys(cmd)
        self.allstat(cmd, doFinish=False)
        cmd.finish()

    def go(self, cmd):
        """Given the already configured lamps, run the sequence """

        if len(self.request) == 0:
            cmd.fail('text="No lamps requested"')
            return

        cmdKeys = cmd.cmd.keywords
        noWait = 'noWait' in cmdKeys

        self.waitForReadySignal(cmd, doFinish=False)

        ret = self.pi.lampsCmd('go')
        self.genVisitKeys(cmd)

        waitTime = self.requestTime + 5
        if noWait:
            cmd.inform(f'text="lamps should be on; please wait {waitTime} to be safe."')
        else:
            cmd.inform(f'text="waiting {waitTime} for lamps to go out."')
            time.sleep(waitTime)

        # self.allstat(cmd, doFinish=False)
        cmd.finish()

    def genVisitKeys(self, cmd):
        """Generate MHS keys based on confguration and status.

        Slightly tricky.

        For the headers, the keys at the end of the exposure will be
        latched. So we generate keys just before the prepare based on
        status: these should all indicate OFF. Then we generate keys
        mostly based on allstat taken imediately after the go command:
        these should match the request, and be valid if we ask fast
        enough.

        We also want to be able to query the current lamp status at any time.
        """
        def lampStateName(val):
            return 'on' if val else 'off'

        mask = [lampStateName(name in self.request) for name in self.piLampNames]
        times = [str(self.request.get(name, 0)) for name in self.piLampNames]

        cmd.inform(f'lampRequestMask={",".join(mask)}')
        cmd.inform(f'lampRequestTimes={",".join(times)}')

    def status(self, cmd):
        """Get current lamp status."""

        self.genStatusKey(cmd, *self._getStatus(cmd))
        cmd.finish()

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
        ret = ret.split('\n')
        statusLines = []
        statusDict = dict()

        for l in ret:
            l = l.strip()
            if not l:
                continue
            statusLines.append(l)
            cmd.inform(f'text="allstat:{l}"')

        try:
            fansLine = statusLines[0]
            udt, _, fans = fansLine.split()
            statusDict['fans'] = fans
        except Exception as e:
            cmd.fail(f'text="did not get allstat output"')
            return

        for l in statusLines[1:]:
            name, status, rawReading, reading = l.split()
            _, rawReading = rawReading.split('=')
            rawReading = float(rawReading)

            readingName, reading = reading.split('=')
            reading = float(reading)

            statusDict[f'{name}_state'] = status
            statusDict[f'{name}_raw'] = rawReading

            if name == 'Cont':
                if readingName == 'fs':
                    statusDict['Cont_fanspeed'] = reading
                    statusDict['Cont'] = -9999
                else:
                    statusDict['Cont_fanspeed'] = -9999
                    statusDict['Cont'] = reading
            else:
                statusDict[name] = reading

        return statusDict

    def allstat(self, cmd, doFinish=True):
        statDict = self._allstat(cmd)

        statNames = ('Ne','Ar','Kr','Xe','Hg','Cd','Cont')
        for lamp in statNames:
            cmd.inform(f'{lamp}State={statDict[lamp+"_state"]},{statDict[lamp]}')
        if doFinish:
            cmd.finish()
