#! /usr/bin/python3

import csv
import random
import math
import re
import sys
import string
from collections import defaultdict
from hashlib import md5
from collections import Counter

__version__ = "1.2.1"

# ================
# Argument Parsing
# ================

class Parser:
    def __init__(self):
        self.parser = self._build_base_parser()
        self.subparsers = self._build_subparsers()
        self.usage = '<fastafile> | smof {} <options>'

    def _build_base_parser(self):
        import argparse
        parser = argparse.ArgumentParser(
            prog='smof',
            usage='<fastafile> | smof <subcommand> <options>',
            description='Tools for studying and manipulating fasta files')

        parser.add_argument(
            '-v', '--version',
            action='version',
            version='%(prog)s {}'.format(__version__))
        return(parser)

    def _build_subparsers(self):
        subparsers = self.parser.add_subparsers(
            metavar='[ for help on each: smof <subcommand> -h ]',
            title='subcommands')
        return(subparsers)

def parse(argv=None):

    parser = Parser()

    Chksum(parser)

    Complexity(parser)
    Fstat(parser)
    Unmask(parser)
    Hstat(parser)
    Idsearch(parser)
    Tounk(parser)
    Prettyprint(parser)
    Qstat(parser)
    Retrieve(parser)
    Sample(parser)
    Sort(parser)
    Search(parser)
    Split(parser)
    Subseq(parser)
    Sniff(parser)
    Fsubseq(parser)
    Fasta2csv(parser)
    Perm(parser)
    Simplifyheader(parser)
    Reverse(parser)
    Grep(parser)
    Uniq(parser)
    Wc(parser)

    if(len(sys.argv) == 1):
        parser.parser.print_help()
        raise SystemExit

    args = parser.parser.parse_args(argv)

    return(args)


# =================
# CLASS DEFINITIONS
# =================

class Alphabet:
    # Including U, for selenocysteine, and * for STOP
    PROT     = set('ACDEFGHIKLMNPQRSTUVWYX*')
    PROT_UNK = set('X')
    PROT_AMB = set('BZJ')
    PROT_EXC = set('EFILQPXJZ*') # unique to protein sequences
    DNA      = set('ACGTN')
    DNA_UNK  = set('N')
    DNA_AMB  = set('RYSWKMDBHV')
    RNA      = set('ACGUN')
    RNA_UNK  = set('N')
    RNA_AMB  = set('RYSWKMDBHV')
    GAP      = set('.-_')
    STOP     = {'TAG', 'TAA', 'TGA', 'UAG', 'UAA', 'UGA'}
    START    = {'ATG', 'AUG'}

class FSeqGenerator:
    def __init__(self, fh=sys.stdin):
        self.fh = fh

    def next(self):
        seq_list = []
        header = ''
        nseqs = 0
        for line in self.fh:
            line = line.strip()
            if ">" == line[0]:
                if(seq_list):
                    nseqs += 1
                    yield FSeq(header, ''.join(seq_list))
                seq_list = []
                header = line.split('>')[1]
            elif header:
                seq_list.append(line)
            else:
                print("First line must begin with '>'", file=sys.stderr)
                raise SystemExit
        if header:
            nseqs += 1
            yield FSeq(header, ''.join(seq_list))
        if not nseqs:
            print("smof could not retrieve any sequence from this file, exiting", file=sys.stderr)
            raise SystemExit

class FSeq:
    # The translator for taking reverse complements
    revcomp_translator = str.maketrans('acgtACGT', 'tgcaTGCA')
    def __init__(self, header, seq):
        self.seq = seq
        self.header = header
        self.headerfields = {}
        self.colseq = ColorString()
        self.colheader = ColorString()

    def parse_header(self):
        '''
        Parses headers of the format:
           '>field_1|value_1|field_2|value_2|...|field_k|value_k| description (optional)
        For example:
            >locus|AT3G01015|taxon|3702|gi|186509637|gb|NP_186749.2| TPX2 targeting protein
        '''
        fields = self.header.split('|')
        # If there is no delimitation with '|', set whatever there is to field
        # 'header'
        if(len(fields) == 1):
            self.headerfields['header'] = fields[0]
        else:
            if(len(fields) % 2  == 1 and fields[-1]):
                self.headerfields['desc'] = fields.pop().strip()
            for i in range(0, len(fields), 2):
                self.headerfields[fields[i].strip()] = fields[i+1].strip()

    def has_field(self, field):
        if(not self.headerfields):
            self.parse_header()
        if field in self.headerfields:
            return True
        else:
            return False

    def field_is(self, field, value):
        value = str(value)
        if(not self.headerfields):
            self.parse_header()
        try:
            if(self.headerfields[field] == value):
                return True
            else:
                return False
        except:
            print("Header lacks field {}".format(field), file=sys.stderr)
            print(self.header, file=sys.stderr)

    def getvalue(self, field, quiet=False, missing=''):
        if not self.headerfields:
            self.parse_header()
        try:
            return(self.headerfields[field])
        except:
            if missing:
                return missing
            if not quiet:
                print("Header lacks field '{}'".format(field), file=sys.stderr)
                print(self.header, file=sys.stderr)
            raise SystemExit

    def countmasked(self):
        '''
        Masked sequences are lowercase, unmasked are uppercase. This function
        simply counts the number of lowercase characters.
        '''
        # ASCII values: (97-122 for a-z), (65-90 for A-Z)
        nmasked = sum(c > 90 for c in self.seq.encode('ascii'))
        return(nmasked)

    def subseq(self, a, b):
        try:
            return(self.seq[a:b])
        except IndexError as e:
            print("Cannot extract subsequence ({}, {}) from".format(a,b))
            print('>' + self.header)
        except:
            print("Unknown error in extraction of subsequence ({}, {}) from".format(a,b))
            print('>' + self.header)

    def ungap(self):
        self.seq = re.sub('[._-]', '', self.seq)

    def print(self, column_width=80):
        if self.colheader.seq:
            self.colheader.print(column_width)
        else:
            print('>' + self.header)
        for i in range(0, len(self.seq), column_width):
            if self.colseq.seq:
                self.colseq.print(column_width)
                break
            else:
                print(self.seq[i:i + column_width])

    def get_pretty_string(self, column_width=80):
        out = ['>' + self.header]
        for i in range(0, len(self.seq), column_width):
            out.append(self.seq[i:i + column_width])
        outstr = '\n'.join(out)
        return(outstr)

    def seq_upper(self):
        self.seq = self.seq.upper()

    def header_upper(self):
        self.header = self.header.upper()

    @classmethod
    def getrevcomp(cls, seq):
        return(seq[::-1].translate(FSeq.revcomp_translator))

class Colors:
    HIGHLIGHT = chr(27) + '[32m'
    BACKGROUND = chr(27) + '[0m'

class ColorString:
    def __init__(self,
                 bgcolor=Colors.BACKGROUND,
                 default=Colors.HIGHLIGHT):
        self.bgcolor = bgcolor
        self.default = default
        self.seq = []

    def setseq(self, seq):
        if not self.seq:
            self.seq = [[self.bgcolor, s] for s in seq]

    def colorpos(self, pos, col=None):
        col = self.default if not col else col
        for i in pos:
            self.seq[i][0] = col

    def print(self, colwidth=None):
        lastcol = self.seq[0][0]
        for i in range(1, len(self.seq)):
            if(self.seq[i][0] == lastcol):
                self.seq[i][0] = ''
            else:
                lastcol = self.seq[i][0]
        for i in range(len(self.seq)):
            print(''.join(self.seq[i]), end='')
            if(colwidth and i % colwidth == 0 and i != 0):
                print()
        print()

    def colormatch(self, pattern, col=None):
        col = self.default if not col else col
        s = ''.join([x[1] for x in self.seq])
        for m in re.compile(pattern).finditer(s):
            a = m.start()
            b = m.start() + len(m.group())
            self.colorpos(list(range(a,b)), col)

class SeqSummary:
    def __init__(self):
        self.seqs = set()
        self.headers = set()
        self.ntype = {
            'prot':0,
            'dna':0,
            'rna':0,
            'illegal':0,
            'ambiguous':0}
        self.ncase = {
            'uppercase':0,
            'lowercase':0,
            'mixedcase':0}
        self.pfeat = {
            'selenocysteine':0,
            'initial-Met':0,
            'internal-stop':0,
            'terminal-stop':0}
        self.nfeat = {
            'start|coding|stop':0,
            'start|coding':0,
            'start|nonsense|stop':0,
            'start|nonsense':0,
            'coding|stop':0,
            'nonsense|stop':0,
            'start|n|stop':0,
            'start':0,
            'stop':0,
            'not-CDS':0}
        self.ufeat = {
            'gapped':0,
            'unknown':0,
            'ambiguous':0}

    def add_seq(self, seq):
        '''
        Calculates properties for one sequence
        @type seq: FSeq object
        '''

        # Add md5 hashes of sequences and headers to respective sets
        self.seqs.update([md5(bytes(seq.seq, 'ascii')).digest()])
        self.headers.update([md5(bytes(seq.header, 'ascii')).digest()])

        counts = Counter(seq.seq)

        # Ungapped the sequence is required for downstream analysis
        is_gapped = self._handle_gaps(seq, counts)
        if is_gapped:
            seq.ungap()
            counts = Counter(seq.seq)

        scase = self._handle_case(counts)
        # Sum upper and lowercase
        if scase not in 'upper':
            counts = counter_caser(counts)

        # ('prot'|'dna'|'rna'|'amb'|'bad')
        stype = self._handle_type(counts)

        if stype == 'prot':
            self.ufeat['unknown'] += 'X' in counts
            self.ufeat['ambiguous'] += bool(Alphabet.PROT_AMB & set(counts))
            self.pfeat['selenocysteine'] += 'U' in counts
            self.pfeat['initial-Met'] += 'M' == seq.seq[0].upper()
            tstop = '*' == seq.seq[-1]
            self.pfeat['terminal-stop'] += tstop
            self.pfeat['internal-stop'] += (counts['*'] - tstop) > 0
        elif stype in ('dna', 'rna'):
            self.ufeat['unknown'] += 'N' in counts
            self.ufeat['ambiguous'] += bool(Alphabet.DNA_AMB & set(counts))
            triple = len(seq.seq) % 3 == 0
            # Is last three bases STOP?
            tstop = seq.seq[-3:].upper() in Alphabet.STOP

            codons_1 = [seq.seq[i:i+3].upper() for i in range(0, len(seq.seq) - 3, 3)]
            start_1 = 'ATG' == codons_1[0]
            stop_1 = codons_1[-1] in Alphabet.STOP
            internal_stop_1 = bool(set(codons_1[:-1]) & Alphabet.STOP)

            # Triplet and START-STOP
            if start_1 and triple and stop_1 and not internal_stop_1:
                self.nfeat['start|coding|stop'] += 1
            elif start_1 and triple and stop_1 and internal_stop_1:
                self.nfeat['start|nonsense|stop'] += 1
            # Triplet and START
            elif start_1 and triple and not stop_1 and not internal_stop_1:
                self.nfeat['start|coding'] += 1
            elif start_1 and triple and not stop_1 and internal_stop_1:
                self.nfeat['start|nonsense'] += 1
            # Triplet and STOP
            elif not start_1 and tstop and triple and not internal_stop_1:
                self.nfeat['coding|stop'] += 1

            # START and terminal-STOP
            elif start_1 and tstop and not triple:
                self.nfeat['start|n|stop'] += 1
            elif start_1 and not tstop:
                self.nfeat['start'] += 1
            elif not start_1 and not tstop:
                self.nfeat['stop'] += 1
            else:
                self.nfeat['not-CDS'] += 1

    def _handle_gaps(self, seq, counts):
        # Handle gaps
        if Alphabet.GAP & set(counts):
            self.ufeat['ngapped'] += 1
            return(True)
        return(False)

    def _handle_case(self, counts):
        has_lower = set(string.ascii_lowercase) & set(counts)
        has_upper = set(string.ascii_uppercase) & set(counts)
        if has_lower and has_upper:
            case = 'mixedcase'
        elif has_lower:
            case = 'lowercase'
        else:
            case = 'uppercase'
        self.ncase[case] += 1
        return(case)

    def _handle_type(self, counts):
        # If all chars are in ACGT
        if set(counts) <= Alphabet.DNA:
            stype = 'dna'
        # If all chars in ACGU
        elif set(counts) <= Alphabet.RNA:
            stype = 'rna'
        # If has any chars unique to proteins (EFILQPXJZ*)
        elif set(counts) & Alphabet.PROT_EXC:
            if set(counts) <= Alphabet.PROT | Alphabet.PROT_AMB:
                stype = 'prot'
            else:
                stype = 'illegal'
        # If all the residues could be aa, DNA, or RNA
        elif set(counts) <= (Alphabet.PROT | Alphabet.PROT_AMB):
            # If more than 80% look like nucleic acids, set 'amb_nucl'
            if (sum([counts[x] for x in 'ACGTUN' if x in counts]) / sum(counts.values())) > 0.8:
                stype = 'rna' if 'U' in counts else 'dna'
            # Otherwise set as ambibuous
            else:
                stype = 'ambiguous'
        # If none of these match, something is horribly wrong with your
        # sequence
        else:
            stype = 'illegal'
        self.ntype[stype] += 1
        return(stype)


# =================
# UTILITY FUNCTIONS
# =================

def csvrowGenerator(filename):
    try:
        f = open(filename, 'r')
        dialect = csv.Sniffer().sniff(f.read(1024))
        f.seek(0)
        reader = csv.reader(f, dialect)
    except IOError as e:
        print(e)
        sys.exit(0)
    for row in reader:
        yield row

def counter_caser(counter, lower=False):
    '''
    Sums cases in Collections.Counter object
    '''
    if lower:
        counts_obj = Counter({k:v for k,v in counter.items() if k.islower()}) + \
                     Counter({k.lower():v for k,v in counter.items() if k.isupper()})
    else:
        counts_obj = Counter({k:v for k,v in counter.items() if k.isupper()}) + \
                     Counter({k.upper():v for k,v in counter.items() if k.islower()})
    return(counts_obj)

# ====================
# ONE-BY-ONE FUNCTIONS
# ====================

class Subcommand:
    def __init__(self, parser_obj, write=True):
        self.func = self.write if write else self.generator
        self.usage = parser_obj.usage
        self.subparsers = parser_obj.subparsers
        self._parse()

    def _parse(self):
        raise NotImplemented

    def generator(self, args, gen):
        raise NotImplemented

    def write(self, args, gen):
        for out in self.generator(args, gen):
            if(isinstance(out, FSeq)):
                out.print()
            else:
                print(out)

class Chksum(Subcommand):
    def _parse(self):
        cmd_name = 'chksum'
        parser = self.subparsers.add_parser(
            cmd_name,
            usage=self.usage.format(cmd_name),
            help="Calculate an md5 checksum for the input sequences"
        )
        parser.add_argument(
            '-i', '--ignore-case',
            help='Convert all to uppercase, before hashing',
            action='store_true',
            default=False
        )
        method = parser.add_mutually_exclusive_group(required=False)
        method.add_argument(
            '-w', '--whole-file',
            help='Calculate single md5sum for all headers and sequences (default action)',
            action='store_true',
            default=False
        )
        method.add_argument(
            '-q', '--each-sequence',
            help='Calculate md5sum for each sequence, write as TAB delimited list',
            action='store_true',
            default=False
        )
        method.add_argument(
            '-s', '--all-sequences',
            help='Calculate single md5sum for all sequences',
            action='store_true',
            default=False
        )
        method.add_argument(
            '-d', '--all-headers',
            help='Calculate single md5sum for all headers',
            action='store_true',
            default=False
        )
        parser.set_defaults(func=self.func)

    def generator(self, args, gen):
        from hashlib import md5
        md5hash = md5()
        # Hash the sequences only (in input order)
        if(args.all_sequences):
            fun = lambda s,h: md5hash.update(s)
        # Hash the headers only (in input order)
        elif(args.all_headers):
            fun = lambda s,h: md5hash.update(h)
        # DEFAULT: Hash each header-sequence pair
        else:
            fun = lambda s,h: md5hash.update(h + b'\n' + s)

        for seq in gen.next():
            if args.ignore_case:
                if args.all_headers or args.whole_file :
                    seq.header_upper()
                if not args.all_headers:
                    seq.seq_upper()
            s = seq.seq.encode('ascii')
            h = seq.header.encode('ascii')
            # Write <header>\t<sequence hash> for each sequence
            if(args.each_sequence):
                yield h.decode() + '\t' + md5(s).hexdigest()
            else:
                fun(s,h)

        # Print output hash for cumulative options
        if not args.each_sequence:
            yield md5hash.hexdigest()

class Complexity(Subcommand):
    def _parse(self):
        cmd_name = 'complexity'
        parser = self.subparsers.add_parser(
            cmd_name,
            usage=self.usage.format(cmd_name),
            help='Calculates the complexity of the given sequences'
        )
        parser.add_argument(
            '-k', '--alphabet-size',
            help='Number of letters in the alphabet (4 for DNA, 20 for proteins)',
            default=4
        )
        parser.add_argument(
            '-w', '--window-length',
            help='Window length (if provided, output will average of window complexities)',
            default=100
        )
        parser.add_argument(
            '-m', '--word-length',
            help='Length of each word',
            default=1
        )
        parser.add_argument(
            '-j', '--jump',
            help='Distance between adjacent windows',
            default=1
        )
        parser.add_argument(
            '-o', '--offset',
            help='Index of start point',
            default=0
        )
        parser.add_argument(
            '-d', '--drop',
            help="Drop sequence if contains this character (e.g. 'X' or 'N')",
            default=None
        )
        parser.set_defaults(func=self.func)

    def generator(self, args, gen):
        try:
            w = int(args.window_length)
            m = int(args.word_length)
            k = pow(int(args.alphabet_size), m)
            p = int(args.jump)
            offset = int(args.offset)
        except ValueError:
            print('All values must be integers', file=sys.stderr)
            raise SystemExit

        # Calculates the variable component of a single window's score
        def varscore_generator(seq, words):
            for i in range(offset, len(seq) - w + 1, p):
                counts = defaultdict(int)
                for j in range(i, i+w):
                    try:
                        counts[words[j]] += 1
                    except IndexError:
                        break
                yield sum([math.log(math.factorial(x), k) for x in counts.values()])

        w_fact = math.log(math.factorial(w), k)

        seq_id = 0
        for seq in gen.next():
            seq_id += 1
            mean = 'NA'
            var = 'NA'
            if(len(seq.seq) < w + offset): pass
            elif(args.drop and args.drop in seq.seq): pass
            else:
                words = tuple(seq.seq[i:i+m] for i in range(offset, len(seq.seq) - m + 1))
                varscores = tuple(score for score in varscore_generator(seq.seq, words))
                winscores = tuple((1 / w) * (w_fact - v) for v in varscores)
                mean = sum(winscores) / len(winscores)
                try:
                    var = sum([pow(mean - x, 2) for x in winscores]) / (len(varscores) - 1)
                except ZeroDivisionError:
                    var = 'NA'
                try:
                    col1 = seq.getvalue('gb', quiet=True)
                except:
                    col1 = seq_id
                yield "{},{},{}".format(col1, mean, var)

class Fstat(Subcommand):
    def _parse(self):
        cmd_name = 'fstat'
        parser = self.subparsers.add_parser(
            cmd_name,
            usage=self.usage.format(cmd_name),
            help="Provides total counts for file sequence characters"
        )
        parser.add_argument(
            '-i', '--ignorecase',
            help="Ignores case when counting characters",
            action='store_true',
            default=False)
        parser.set_defaults(func=self.func)

    def generator(self, args, gen):
        counts = Counter()
        nseqs = 0
        for seq in gen.next():
            nseqs += 1
            counts.update(seq.seq)

        if args.ignorecase:
            counts = counter_caser(counts)

        nchars = sum(counts.values())
        for k, v in sorted(counts.items(), key=lambda x: x[1], reverse=True):
            yield "{}: {} {}".format(k, v, round(v/nchars, 4))
        yield "nseqs: {}".format(nseqs)
        yield "nchars: {}".format(nchars)
        yield "mean length: {}".format(round(nchars/nseqs, 4))

class Hstat(Subcommand):
    def _parse(self):
        cmd_name = 'hstat'
        parser = self.subparsers.add_parser(
            cmd_name,
            usage=self.usage.format(cmd_name),
            help="Extract info from headers (also seq length)")
        parser.add_argument(
            'fields',
            help="Header fields to write to csv",
            nargs='+')
        parser.add_argument(
            '--length',
            help="Report length of each sequence",
            action='store_true',
            default=False)
        parser.set_defaults(func=self.func)

    def generator(self, args, gen):
        ''' Writes chosen header and seq length data to csv '''
        fieldnames = self._get_fieldnames(args)
        for seq in gen.next():
            row = {}
            for field in args.fields:
                row[field] = seq.getvalue(field)
            if(args.length):
                row['length'] = len(seq.seq)
            yield row

    def _get_fieldnames(self, args):
        fieldnames = list(args.fields)
        if(args.length):
            fieldnames.append('length')
        return(fieldnames)

    def write(self, args, gen):
        fieldnames = self._get_fieldnames(args)
        w = csv.DictWriter(sys.stdout, fieldnames=fieldnames)
        w.writeheader()
        for row in self.generator(args, gen):
            w.writerow(row)

class Unmask(Subcommand):
    def _parse(self):
        cmd_name = 'unmask'
        parser = self.subparsers.add_parser(
            cmd_name,
            usage=self.usage.format(cmd_name),
            help="Converts all letters to uppercase")
        parser.add_argument(
            '-x', '--to-x',
            help="Convert lower case letters to X",
            action='store_true',
            default=False)
        parser.set_defaults(func=self.func)

    def generator(self, args, gen):
        ''' Converts to upcase '''
        for seq in gen.next():
            if(args.to_x):
                unmasked_seq = FSeq(seq.header, re.sub('[a-z]', 'X', seq.seq))
            else:
                unmasked_seq = FSeq(seq.header, seq.seq.upper())
            yield unmasked_seq

class Idsearch(Subcommand):
    def _parse(self):
        cmd_name = 'idsearch'
        parser = self.subparsers.add_parser(
            cmd_name,
            usage=self.usage.format(cmd_name),
            help='Find sequences by field/value pair')
        parser.add_argument(
            'field',
            help="Header field (e.g. 'gi' or 'locus')")
        parser.add_argument(
            'value',
            help="Header field value (e.g. '15237703' or 'AT5G64430')")
        parser.set_defaults(func=self.func)

    def generator(self, args, gen):
        ''' Print entries whose headers contain a field with a given value '''
        for seq in gen.next():
            if(seq.field_is(args.field, args.value)):
                yield seq

class Tounk(Subcommand):
    def _parse(self):
        cmd_name = 'tounk'
        parser = self.subparsers.add_parser(
            cmd_name,
            usage=self.usage.format(cmd_name),
            help='Convert irregular characters to unknown character'
        )
        parser.add_argument(
            '-t', '--type',
            help='Sequence type [n, p]'
        )
        parser.add_argument(
            '-l', '--lc',
            help='Convert lower-case to unknown',
            action='store_true',
            default=False
        )
        parser.add_argument(
            '--nir',
            help='Nucleotide irregulars [default=(not ACGT)]',
            default=''.join(set(string.ascii_letters) - set('ACGTNacgtn'))
        )
        parser.add_argument(
            '--pir',
            help='Protein irregulars [default=BJOUZbjouz]',
            default='BJOUXZbjouxz'
        )
        parser.add_argument(
            '--nunk',
            help='Nucleotide unknown character (default=N)',
            default='N'
        )
        parser.add_argument(
            '--punk',
            help='Protein unknown character (default=X)',
            default='X'
        )
        parser.set_defaults(func=self.func)

    def generator(self, args, gen):
        if(args.type.lower()[0] in ['a', 'p']):
            irr = args.pir
            unk = args.punk
        elif(args.type.lower()[0] in ['n', 'd']):
            irr = args.nir
            unk = args.nunk
        if(args.lc):
            irr = ''.join(set(irr) | set(string.ascii_lowercase))
        trans = str.maketrans(irr, unk * len(irr))
        for seq in gen.next():
            seq.seq = seq.seq.translate(trans)
            yield seq

class Prettyprint(Subcommand):
    def _parse(self):
        cmd_name = 'prettyprint'
        parser = self.subparsers.add_parser(
            cmd_name,
            usage=self.usage.format(cmd_name),
            help='Prints fasta file in neat columns')
        parser.add_argument(
            'cwidth',
            help='Output column width',
            type=int,
            default=60)
        parser.set_defaults(func=self.func)

    def generator(self, args, gen):
        ''' Print each sequence with even columns of length cwidth '''
        for seq in gen.next():
            yield seq

    def write(self, args, gen):
        for seq in self.generator(args, gen):
            seq.print(args.cwidth)

class Qstat(Subcommand):
    def _parse(self):
        cmd_name = 'qstat'
        parser = self.subparsers.add_parser(
            cmd_name,
            usage=self.usage.format(cmd_name),
            help="Gathers statistics on each sequence")
        parser.add_argument(
            '-f', '--fields',
            help="Header fields by which each sequence is identified in output csv file",
            nargs='+',
            default=[])
        parser.add_argument(
            '-m', '--masked',
            help="Count the number of masked (lowercase) characters",
            action='store_true',
            default=False)
        parser.add_argument(
            '-i', '--ignorecase',
            help="Ignores case when counting characters",
            action='store_true',
            default=False)
        parser.add_argument(
            '-s', '--start-offset',
            help='Number of letters to ignore at beginning (default=0)',
            type=int,
            default=0
        )
        parser.add_argument(
            '-e', '--end-offset',
            help='Number of letters to ignore at end (default=0)',
            type=int,
            default=0
        )
        parser.set_defaults(func=self.func)

    def generator(self, args, gen):
        for seq in gen.next():
            if args.fields:
                fields = tuple(seq.getvalue(x, missing='NA') for x in args.fields)
            else:
                fields = []

            # Trim the beginning and end of the sequence, as specified
            count = Counter(seq.seq[args.start_offset:len(seq.seq) - args.end_offset])

            if args.masked:
                nmasked = sum([v for c,v in count.items() if c in string.ascii_lower])
            else:
                nmasked = None

            if args.ignorecase:
                count = counter_caser(count)

            yield (fields, count, nmasked)

    def write(self, args, gen):
        results = list(self.generator(args, gen))
        # Set of all unique characters seen in the fasta file
        chars = set()
        for f,c,m in results:
            chars.update(c.keys())
        if args.ignorecase:
            chars = sorted(set(''.join(chars).upper()))
        else:
            chars = sorted(chars)

        headerfields = args.fields if args.fields else []
        fieldnames = ['length'] + headerfields
        fieldnames += ['masked'] if args.masked else []
        fieldnames += chars

        w = csv.DictWriter(sys.stdout, fieldnames=fieldnames)
        w.writeheader()
        for fields,counts,masked in results:
            row = {'length':sum(counts.values())}
            if headerfields:
                for i in range(len(fields)):
                    row[headerfields[i]] = str(fields[i])
            for k,v in counts.items():
                row[k] = str(v)
            w.writerow(row)

class Retrieve(Subcommand):
    def _parse(self):
        cmd_name = 'retrieve'
        parser = self.subparsers.add_parser(
            cmd_name,
            usage=self.usage.format(cmd_name),
            help="Retrieve sequences with matches pattern"
        )
        parser.add_argument(
            '-p', '--pattern',
            help="Perl regular expressions",
            nargs='+'
        )
        parser.add_argument(
            '-P', '--patternfile',
            help="Perl regular expressions"
        )
        parser.add_argument(
            '-g', '--groups',
            help="The acceptable values for parenthesized groups",
            nargs='*'
        )
        parser.add_argument(
            '-G', '--groupfile',
            help="Read values from file"
        )
        parser.add_argument(
            '-v', '--invert',
            help="Write sequences that don't match"
        )
        parser.add_argument(
            '-q', '--match-sequence',
            help='Match sequence rather than header',
            action='store_true',
            default=False
        )
        parser.add_argument(
            '-c', '--color',
            help='Color match',
            action='store_true',
            default=False
        )
        parser.set_defaults(func=self.func)

    def generator(self, args, gen):
        '''
        Extracts sequences matching a certain pattern
        '''
        def getset(values, filename):
            s = set()
            if filename:
                with open(filename, 'r') as f:
                    s.update([line.rstrip('\n') for line in f.readlines()])
            if values:
                s.update(values)
            return(s)

        groups = getset(args.groups, args.groupfile)
        pat = set((re.compile(p) for p in getset(args.pattern, args.patternfile)))

        if(len(pat) > 1 and groups):
            print('Cannot process multiple patterns with groups', file=sys.stderr)
            raise SystemExit
        if not pat:
            print('Please provide a pattern (-p <regex>)', file=sys.stderr)

        for seq in gen.next():
            if(args.match_sequence):
                text = seq.seq
            else:
                text = seq.header
            for p in pat:
                m = re.search(p, text)
                if not m and not args.invert:
                    continue
                elif groups:
                    try:
                        # If at least one group defined
                        match = m.group(1)
                    except:
                        # If no groups defined
                        match = m.group(0)
                    if (match in groups and args.invert) or \
                    (match not in groups and not args.invert):
                        continue
                if not args.color or args.invert:
                    yield seq
                    break
                # KLUDGE, TODO: Make seq and header classes
                else:
                    if(args.match_sequence):
                        seq.colseq.setseq(text)
                        seq.colseq.colormatch(p)
                    else:
                        seq.colheader.setseq(text)
                        seq.colheader.colormatch(p)
            if(seq.colseq.seq or seq.colheader.seq):
                yield seq

class Search(Subcommand):
    def _parse(self):
        cmd_name = 'search'
        parser = self.subparsers.add_parser(
            cmd_name,
            usage=self.usage.format(cmd_name),
            help='Search for pattern')
        parser.add_argument(
            'pattern',
            help='Perl regular expression search pattern')
        parser.add_argument(
            '-i', '--invert',
            help="Drop all not matching the pattern",
            action='store_true',
            default=False
        )
        parser.add_argument(
            '-q', '--seq',
            help='Search for pattern in the sequence',
            action='store_true',
            default=False
        )
        parser.add_argument(
            '-c', '--color',
            help='Highlight the matched sequence',
            action='store_true',
            default=False
        )
        parser.set_defaults(func=self.func)

    def generator(self, args, gen):
        '''
        Print entries whose headers contain a given pattern. Similar to `retrieve` but lighterweight.
        '''
        prog = re.compile(args.pattern)
        for seq in gen.next():
            text = seq.seq if args.seq else seq.header
            m = prog.search(text)
            if (not m and not args.invert) or (m and args.invert):
                continue
            if(args.color and not args.invert):
                if(args.seq):
                    seq.colseq.setseq(text)
                    seq.colseq.colormatch(prog)
                else:
                    seq.colheader.setseq(text)
                    seq.colheader.colormatch(prog)
            yield seq

class Subseq(Subcommand):
    def _parse(self):
        cmd_name = 'subseq'
        parser = self.subparsers.add_parser(
            cmd_name,
            usage=self.usage.format(cmd_name),
            help="Extract subsequence from each entry")
        parser.add_argument(
            'bounds',
            help="from and to values (indexed from 1)",
            nargs=2,
            type=int)
        parser.add_argument(
            '-r', '--revcomp',
            help='Take the reverse complement if bounds[0] > bounds[1]',
            action='store_true',
            default=False)
        parser.set_defaults(func=self.func)

    def generator(self, args, gen):
        ''' Index starting from 1 (not 0) '''
        for seq in gen.next():
            a = args.bounds[0]
            b = args.bounds[1]
            # If a > b, take reverse complement if that option is enabled,
            # if not die
            if(a > b):
                if(args.revcomp):
                    newseq = FSeq.getrevcomp(seq.seq[b-1:a])
                else:
                    print('Lower bound cannot be greater than upper bound ' + \
                        '(do you want reverse complement? See options)', file=sys.stderr)
                    sys.exit()
            # If b >= a, this is a normal forward sequence
            else:
                newseq = seq.seq[a-1:b]
            yield FSeq(seq.header, newseq)

class Fsubseq(Subcommand):
    def _parse(self):
        cmd_name = 'fsubseq'
        parser = self.subparsers.add_parser(
            cmd_name,
            usage=self.usage.format(cmd_name),
            help="Mass extraction of subsequences from first fasta entry")
        parser.add_argument(
            'file',
            help="File containing bounds for subsequence extraction")
        parser.add_argument(
            '-r', '--revcomp',
            help='Take the reverse complement if bounds[0] > bounds[1]',
            action='store_true',
            default=False)
        parser.add_argument(
            '-p', '--pattern-index',
            help='Index of regex pattern in each row',
            type=int,
            default=-1)
        parser.set_defaults(func=self.func)

    def generator(self, args, gen):
        '''
        Extracts many subsequences. Positional argument file
        '''
        bounds = defaultdict(list)
        for row in csvrowGenerator(args.file):
            if(args.pattern_index >= 0):
                try:
                    pat = row[args.pattern_index]
                    del row[args.pattern_index]
                except IndexError:
                    print("Given pattern index doesn't exist, fuck you!",
                          file=sys.stderr)
                    raise SystemExit
            else:
                pat = '.*'
            try:
                a,b = [int(x) for x in row]
            except TypeError:
                print("Bounds must be pair of integers", file=sys.stderr)
                raise SystemExit
            bounds[pat].append((a,b))

        for seq in gen.next():
            for pat in bounds.keys():
                if(not re.search(pat, seq.header)):
                    continue
                for a,b in bounds[pat]:
                    # If a > b, take reverse complement if that option is enabled,
                    # if not die
                    if(a > b):
                        if(args.revcomp):
                            newseq = FSeq.getrevcomp(seq.seq[(b-1):a])
                        else:
                            print('Lower bound cannot be greater than upper bound '
                                  '(do you want reverse complement? See options)',
                                  file=sys.stderr)
                            raise SystemExit
                    # If b >= a, this is a normal forward sequence
                    else:
                        newseq = seq.seq[(a-1):b]
                    yield FSeq(seq.header, newseq)

class Fasta2csv(Subcommand):
    def _parse(self):
        cmd_name = 'fasta2csv'
        parser = self.subparsers.add_parser(
            cmd_name,
            usage=self.usage.format(cmd_name),
            help="Converts a fasta file to 2-column csv")
        parser.add_argument(
            '-d', '--delimiter',
            help="Set delimiter (',' by default)",
            default=',')
        parser.add_argument(
            '-r', '--header',
            help='Write header (default=False)',
            action='store_true',
            default=False)
        parser.add_argument(
            '-f', '--fields',
            help='Extract given fields from the header',
            nargs='+')
        parser.set_defaults(func=self.func)

    def generator(self, args, gen):
        if(args.header):
            if(args.fields):
                yield args.fields + ['seq']
            else:
                yield ['header', 'seq']
        for seq in gen.next():
            if(args.fields):
                row = [seq.getvalue(field) for field in args.fields]
            else:
                row = [seq.header]
            yield tuple(row + [seq.seq])

    def write(self, args, gen):
        w = csv.writer(sys.stdout, delimiter=args.delimiter)
        for row in self.generator(args, gen):
            w.writerow(row)

class Perm(Subcommand):
    def _parse(self):
        cmd_name = 'perm'
        parser = self.subparsers.add_parser(
            cmd_name,
            usage=self.usage.format(cmd_name),
            help="Randomly order sequence by words of length w"
        )
        parser.add_argument(
            '-w', '--word-size',
            help='Size of each word (default=1)',
            type=int,
            default=1
        )
        parser.add_argument(
            '-s', '--start-offset',
            help='Number of letters to ignore at beginning (default=0)',
            type=int,
            default=0
        )
        parser.add_argument(
            '-e', '--end-offset',
            help='Number of letters to ignore at end (default=0)',
            type=int,
            default=0
        )
        parser.add_argument(
            '-f', '--field',
            help="Header field (e.g. 'gi' or 'locus')"
        )
        parser.set_defaults(func=self.func)

    def generator(self, args, gen):
        w = args.word_size
        start = args.start_offset
        end = args.end_offset
        for seq in gen.next():
            s = seq.seq
            L = len(s)
            prefix = s[0:start]
            suffix = s[L-end:L]
            rseq = s[start:L-end]
            M = len(rseq)
            words = list(rseq[i:i+w] for i in range(0, M - w + 1, w))
            words.append(rseq[(M - M % w):M])
            random.shuffle(words)
            out = ''.join(prefix + ''.join(words) + suffix)
            if(args.field):
                header='|'.join((args.field, seq.getvalue(args.field), 'start', str(start), 'end', str(end), 'word_size', str(w)))
            else:
                header=seq.header
            yield FSeq(header, out)

class Simplifyheader(Subcommand):
    def _parse(self):
        cmd_name = 'rmfields'
        parser = self.subparsers.add_parser(
            cmd_name,
            usage=self.usage.format(cmd_name),
            help="Reduce header to given fields"
        )
        parser.add_argument(
            'fields',
            help="Fields to retain",
            nargs='+'
        )
        parser.set_defaults(func=self.func)

    def generator(self, args, gen):
        if(hasattr(args.fields, '__upper__')):
            args.fields = (args.fields, )
        for seq in gen.next():
            values = [seq.getvalue(field) for field in args.fields]
            pairs = ['|'.join((args.fields[i], values[i])) for i in range(len(values))]
            header = '|'.join(pairs)
            yield FSeq(header, seq.seq)

class Sniff(Subcommand):
    def _parse(self):
        cmd_name = 'sniff'
        parser = self.subparsers.add_parser(
            cmd_name,
            usage=self.usage.format(cmd_name),
            help="Extract info about the sequence"
        )
        parser.set_defaults(func=self.func)

    def generator(self, args, gen):
        seqsum = SeqSummary()
        for seq in gen.next():
            seqsum.add_seq(seq)
        yield seqsum

    def write(self, args, gen):
        seqsum = next(self.generator(args, gen))
        nseqs = sum(seqsum.ncase.values())

        has_degen_headers = nseqs != len(seqsum.headers)
        has_degen_seqs = nseqs != len(seqsum.seqs)
        has_bad = seqsum.ntype['illegal'] != 0

        if has_degen_seqs:
            print("{} uniq sequences ({} total)".format(len(seqsum.seqs), nseqs))
        else:
            print("Total sequences: {}".format(nseqs))

        if has_degen_headers:
            print("WARNING: headers are not unique ({}/{})".format(len(seqsum.headers), nseqs))
        if has_bad:
            print("WARNING: illegal characters found")

        def write_dict(d, name, N):
            uniq = [[k,v] for  k,v in d.items() if v != 0]
            if len(uniq) == 1:
                print("All {}".format(uniq[0][0]))
            else:
                print("{}:".format(name))
                for k,v in sorted(uniq, key=lambda x: -x[1]):
                    print("  {:<20} {:<10} {:>7.4f}%".format(k + ':', v, 100*v/N))

        write_dict(seqsum.ntype, 'Sequence types', nseqs)
        write_dict(seqsum.ncase, 'Sequences cases', nseqs)

        nnucl = sum([v for k,v in seqsum.ntype.items() if k in {'dna', 'rna'}])
        nprot = sum([v for k,v in seqsum.ntype.items() if k == 'prot'])

        def write_feat(d, text, N):
            if not N:
                return(0)
            print(text)
            for k,v in sorted(list(d.items()), key=lambda x: -x[1]):
                print("  {:<20} {:<10} {:>7.4f}%".format(k + ':', v, 100*v/N))

        write_feat(seqsum.nfeat, "Nucleotide Features:", nnucl)
        write_feat(seqsum.pfeat, "Protein Features:", nprot)
        write_feat(seqsum.ufeat, "Universal Features:", nseqs)

class Reverse(Subcommand):
    def _parse(self):
        cmd_name = 'reverse'
        parser = self.subparsers.add_parser(
            cmd_name,
            usage=self.usage.format(cmd_name),
            help="Reverse each sequence")
        parser.set_defaults(func=self.func)

    def generator(self, args, gen):
        ''' Reverse each sequence '''
        for seq in gen.next():
            yield FSeq(seq.header, seq.seq[::-1])


# ==============
# FULL FUNCTIONS
# ==============

class Sample(Subcommand):
    def _parse(self):
        cmd_name = 'sample'
        parser = self.subparsers.add_parser(
            cmd_name,
            usage=self.usage.format(cmd_name),
            help="Randomly select entries from fasta file")
        parser.add_argument(
            'n',
            help="Sample size",
            type=int,
            default=1)
        parser.set_defaults(func=self.func)

    def generator(self, args, gen):
        ''' Randomly sample n entries from input file '''
        seqs = [s for s in gen.next()]
        sample_indices = random.sample(range(len(seqs)), min(len(seqs), args.n))
        for i in sample_indices:
            yield seqs[i]

class Split(Subcommand):
    def _parse(self):
        cmd_name = 'split'
        parser = self.subparsers.add_parser(
            cmd_name,
            usage=self.usage.format(cmd_name),
            help='Split a multifasta file into k smaller filers'
        )
        parser.add_argument(
            '-n', '--nfiles',
            help='Number of output files'
        )
        parser.add_argument(
            '-p', '--prefix',
            help='Prefix for output files',
            default='xxx'
        )
        parser.set_defaults(func=self.func)

    def generator(self, args, gen):
        for s in gen.next():
            yield s

    def write(self, args, gen):
        k = int(args.nfiles)
        p = args.prefix
        seqs = list(self.generator(args, gen))
        for i in range(0, k):
            begin = i * (len(seqs) // k + 1)
            end = min(len(seqs), (i+1) * (len(seqs) // k + 1))
            outfile = p + str(i) + '.fasta'
            with open(outfile, 'w+') as fo:
                for seq in (seqs[x] for x in range(begin, end)):
                    fo.write(seq.get_pretty_string() + '\n')

class Sort(Subcommand):
    def _parse(self):
        cmd_name = 'sort'
        parser = self.subparsers.add_parser(
            cmd_name,
            usage=self.usage.format(cmd_name),
            help="Sort sequences by given fields")
        parser.add_argument(
            'fields',
            help="Header fields by which to sort sequences",
            nargs='+')
        parser.set_defaults(func=self.func)

    def generator(self, args, gen):
        seqs = [s for s in gen.next()]
        seqs.sort(key=lambda x: list(x.getvalue(y) for y in args.fields))
        for s in seqs:
            yield s


# ==============
# UNIX EMULATORS
# ==============

class Grep(Subcommand):
    def _parse(self):
        cmd_name = 'grep'
        parser = self.subparsers.add_parser(
            cmd_name,
            usage=self.usage.format(cmd_name),
            help="Roughly emulates the UNIX grep command"
        )
        parser.add_argument(
            '-f', '--file',
            help='Obtain patterns from given file, one per line'
        )
        parser.add_argument(
            '-w', '--pattern-wrapper',
            help='A pattern that matches its capture against strings in FILE'
        )
        parser.add_argument(
            '-i', '--ignore-case',
            help='Ignore case distinctions',
            action='store_true',
            default=False
        )
        parser.add_argument(
            '-v', '--invert-match',
            help='Print non-matching entries',
            action='store_true',
            default=False
        )
        parser.add_argument(
            '-c', '--count',
            help='Print number of matching entries',
            action='store_true',
            default=False
        )
        parser.add_argument(
            '-o', '--only',
            help='Print only matching parts of header of sequence',
            action='store_true',
            default=False
        )
        parser.add_argument(
            '-A', '--after-context',
            help='Print INT characters after the match'
            action='store_true',
            default=False
        )
        parser.add_argument(
            '-B', '--before-context',
            help='Print INT characters before the match'
            action='store_true',
            default=False
        )
        parser.add_argument(
            '-C', '--context',
            help='Print INT characters after the match'
            action='store_true',
            default=False
        )
        parser.add_argument(
            '--color',
            help='Print in color',
            action='store_true',
            default=False
        )

    def generator(self, args, gen):
        raise NotImplemented

class Uniq(Subcommand):
    def _parse(self):
        cmd_name = 'uniq'
        parser = self.subparsers.add_parser(
            cmd_name,
            usage=self.usage.format(cmd_name),
            help="Emulates the UNIX uniq command (doesn't require prior sorting)"
        )
        parser.add_argument(
            '-c', '--count',
            help='Writes (count|header|sequence) in tab-delimited format',
            action='store_true',
            default=False
        )
        parser.add_argument(
            '-d', '--repeated',
            help='Print only repeated entries',
            action='store_true',
            default=False
        )
        parser.add_argument(
            '-i', '--ignore-case',
            help='Ignore differences in case when comparing',
            action='store_true',
            default=False
        )
        parser.add_argument(
            '-u', '--uniq',
            help='Print only unique entries'
            action='store_true',
            default=False
        )

    def generator(self, args, gen):
        raise NotImplemented

class Wc(Subcommand):
    def _parse(self):
        cmd_name = 'wc'
        parser = self.subparsers.add_parser(
            cmd_name,
            usage=self.usage.format(cmd_name),
            help="Roughly emulates the UNIX wc command"
        )
        parser.add_argument(
            '-m', '--chars',
            help='Writes the summed length of all sequences',
            action='store_true',
            default=False
        )
        parser.add_argument(
            '-l', '--lines',
            help='Writes the total number of sequences',
            action='store_true',
            default=False
        )

    def generator(self, args, gen):
        raise NotImplemented


# =======
# EXECUTE
# =======

if __name__ == '__main__':
    gen = FSeqGenerator()
    args = parse()
    args.func(args, gen)
