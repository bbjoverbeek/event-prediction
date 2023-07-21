def convert(line):
    """
    >>> convert('12-34|Hallo , wereld !')
    ((12, 34), 'Hallo , wereld !')
    """
    label, sent = line.rstrip().split('|', 1)
    sentno, parno = label.split('-')
    return ((int(sentno), int(parno)), sent)


class Index:
    """Map various indices to other types of indices.

    :ivar parsenttok2charidx: maps (parno, sentno, tokenno)
        to (startcharidx, endcharidx).
        (parno, sentno) is a paragraph number and sentence number within
        that paragraph.
    :ivar gsenttok2charidx: maps (gsentno, tokenno)
        to (startcharidx, endcharidx).
        gsentno is a global sentence number.
    :ivar gtok2charidx: map global token index to (startcharidx, endcharidx).
    :ivar parsent2gsent: maps (parno, sentno) to global sentence number
    :ivar gsent2sentpar: maps global sentence number to (parno, sentno)
    """
    def __init__(self, fname):
        with open(fname, 'r', encoding='utf8') as inp:
            sents = [convert(line) for line in inp.read().splitlines()]
        self.gsenttok2charidx = {}
        self.parsenttok2charidx = {}
        self.gtok2charidx = {}
        self.parsent2gsent = {}
        self.gsent2sentpar = {}
        charidx = 0
        gtokidx = 0
        for gsentno, ((parno, sentno), sent) in enumerate(sents):
            tokidx = 0
            self.parsent2gsent[parno, sentno] = gsentno
            self.gsent2sentpar[gsentno] = parno, sentno
            for n, token in enumerate(sent.split(' ')):
                cur = (charidx, charidx + len(token))
                self.gsenttok2charidx[gsentno, tokidx] = cur
                self.parsenttok2charidx[parno, sentno, tokidx] = cur
                self.gtok2charidx[gtokidx] = cur
                tokidx += 1
                gtokidx += 1
                charidx += len(token) + 1  # token + space/newline
