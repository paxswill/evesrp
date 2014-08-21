from evesrp.killmail import ZKillmail


class TestZKillboard(ZKillmail):
    def __init__(self, *args, **kwargs):
        super(TestZKillboard, self).__init__(*args, **kwargs)
        if self.domain not in ('zkb.pleaseignore.com', 'kb.pleaseignore.com'):
            raise ValueError(u"This killmail is from the wrong killboard")

    @property
    def value(self):
        return 0
