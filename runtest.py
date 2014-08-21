#!/usr/bin/env python3

import smof
import unittest
import argparse
import sys
from tempfile import TemporaryFile
from collections import Counter

class TestFSeq(unittest.TestCase):
    def test_subseq(self):
        header = 'seq1'
        seq = 'AcGGNttt'
        seqobj = smof.FSeq(header, seq)
        sq = seqobj.subseq(1, 5)
        self.assertEqual(sq.seq, 'cGGN')
        self.assertEqual(sq.header, 'seq1|SUBSEQ(2..5)')

    def test_getrevcomp_fromStringInput(self):
        seq = 'ACGTT'
        self.assertEqual(smof.FSeq.getrevcomp(seq), 'AACGT')

    def test_getrevcomp_fromFSeqInput(self):
        header = 'seq1'
        seq = 'ACGTT'
        seqobj = smof.FSeq(header,seq)
        rc = smof.FSeq.getrevcomp(seqobj)
        self.assertEqual(rc.seq, 'AACGT')
        self.assertEqual(rc.header, 'seq1|REVCOM')

    def test_ungap(self):
        header = 'seq1'
        seq = 'A.C-G_T'
        seqobj = smof.FSeq(header,seq)
        seqobj.ungap()
        self.assertEqual(seqobj.seq, 'ACGT')
        self.assertEqual(seqobj.header, 'seq1|UNGAPPED')

    def test_reverse(self):
        header = 'seq1'
        seq = 'ACGTT'
        seqobj = smof.FSeq(header,seq)
        seqobj.reverse()
        self.assertEqual(seqobj.seq, 'TTGCA')
        self.assertEqual(seqobj.header, 'seq1|REVERSE')

class TestStatFun(unittest.TestCase):
    def test_N50(self):
        self.assertEqual(smof.StatFun.N50([1,2,3.1]), 3.1)

    def test_mean(self):
        self.assertEqual(smof.StatFun.mean([1,2,3]), 2)

    def test_median(self):
        self.assertEqual(smof.StatFun.median([1,2,3]), 2)

    def test_sd(self):
        self.assertEqual(smof.StatFun.sd([1,2,3]), 1)

    def test_quantile(self):
        self.assertEqual(smof.StatFun.quantile([1,2,3], 0.5), 2)

    def test_summary_values(self):
        x = list(range(-5, 11))
        o = smof.StatFun.summary(x)
        self.assertEqual(o['min'], -5)
        self.assertEqual(o['1st_qu'], -1.25)
        self.assertEqual(o['median'], 2.5)
        self.assertEqual(o['3rd_qu'], 6.25)
        self.assertEqual(o['max'], 10)

class TestFileDescription(unittest.TestCase):
    def setUp(self):
        self.seqs = {
            'p-normal':'SMIF',
            'p-selenocysteine':'SMUF',
            'p-unknown':'SMXF',
            'p-ambiguous':'SMBF',
            'p-illegal':'SMOF',
            'p-terminal-stop':'SMIF*',
            'p-internal-stop':'SM*F',
            'p-initial-Met':'MSMIF',
            'p-lowercase':'smif',
            'p-mixedcase':'sMiF',
            '0000':'GGTtaagGCCGGT',
            '0001':'GGTgGCCGGT',
            '0010':'GGTtaaGCCGGT',
            '0011':'GGTGCCGGT',
            '0100':'GGTtaagGCCTAA',
            '0101':'GGTgGCCTAA',
            '0110':'GGTtaaGCCTAA',
            '0111':'GGTGCCTAA',
            '1000':'ATGtaagGCCGGT',
            '1001':'ATGgGCCGGT',
            '1010':'ATGtaaGCCGGT',
            '1011':'ATGGCCGGT',
            '1100':'ATGtaagGCCTAA',
            '1101':'ATGgGCCTAA',
            '1110':'ATGtaaGCCTAA',
            '1111':'ATGGCCTAA',
            'n-gapped':'-GATACA_CAT.TAG.',
            'p-gapped':'.YELL-AT_FAT-PHIL.',
            'illegal':'CHOCOLATE'
        }

    def _prep_fd(self, keys):
        fd = smof.FileDescription()
        for key in keys:
            seq = smof.FSeq(header=key, seq=self.seqs[key])
            fd.add_seq(seq)
        return(fd)

    def _equal_counts(self, test, true):
        return(
            test.ntype == true.ntype and
            test.ncase == true.ncase and
            test.pfeat == true.pfeat and
            test.nfeat == true.nfeat and
            test.ufeat == true.ufeat
        )

    def test_prot_normal(self):
        fd_test = self._prep_fd(['p-normal'])

        fd_true = smof.FileDescription()
        fd_true.ntype['prot'] += 1
        fd_true.ncase['uppercase'] += 1

        self.assertTrue(self._equal_counts(fd_true, fd_test))

    def test_prot_selenocysteine(self):
        fd_test = self._prep_fd(['p-selenocysteine'])

        fd_true = smof.FileDescription()
        fd_true.ntype['prot'] += 1
        fd_true.ncase['uppercase'] += 1
        fd_true.pfeat['selenocysteine'] += 1

        self.assertTrue(self._equal_counts(fd_true, fd_test))

    def test_prot_unknown(self):
        fd_test = self._prep_fd(['p-unknown'])

        fd_true = smof.FileDescription()
        fd_true.ntype['prot'] += 1
        fd_true.ncase['uppercase'] += 1
        fd_true.ufeat['unknown'] += 1

        self.assertTrue(self._equal_counts(fd_true, fd_test))

    def test_prot_ambiguous(self):
        fd_test = self._prep_fd(['p-ambiguous'])

        fd_true = smof.FileDescription()
        fd_true.ntype['prot'] += 1
        fd_true.ncase['uppercase'] += 1
        fd_true.ufeat['ambiguous'] += 1

        self.assertTrue(self._equal_counts(fd_true, fd_test))

    def test_prot_illegal(self):
        fd_test = self._prep_fd(['p-illegal'])

        fd_true = smof.FileDescription()
        fd_true.ntype['illegal'] += 1
        fd_true.ncase['uppercase'] += 1

        self.assertTrue(self._equal_counts(fd_true, fd_test))

    def test_prot_terminal_stop(self):
        fd_test = self._prep_fd(['p-terminal-stop'])

        fd_true = smof.FileDescription()
        fd_true.ntype['prot'] += 1
        fd_true.ncase['uppercase'] += 1
        fd_true.pfeat['terminal-stop'] += 1

        self.assertTrue(self._equal_counts(fd_true, fd_test))

    def test_prot_internal_stop(self):
        fd_test = self._prep_fd(['p-internal-stop'])

        fd_true = smof.FileDescription()
        fd_true.ntype['prot'] += 1
        fd_true.ncase['uppercase'] += 1
        fd_true.pfeat['internal-stop'] += 1

        self.assertTrue(self._equal_counts(fd_true, fd_test))

    def test_prot_initial_met(self):
        fd_test = self._prep_fd(['p-initial-Met'])

        fd_true = smof.FileDescription()
        fd_true.ntype['prot'] += 1
        fd_true.ncase['uppercase'] += 1
        fd_true.pfeat['initial-Met'] += 1

        self.assertTrue(self._equal_counts(fd_true, fd_test))

    def test_prot_lowercase(self):
        fd_test = self._prep_fd(['p-lowercase'])

        fd_true = smof.FileDescription()
        fd_true.ntype['prot'] += 1
        fd_true.ncase['lowercase'] += 1

        self.assertTrue(self._equal_counts(fd_true, fd_test))

    def test_prot_mixedcase(self):
        fd_test = self._prep_fd(['p-mixedcase'])

        fd_true = smof.FileDescription()
        fd_true.ntype['prot'] += 1
        fd_true.ncase['mixedcase'] += 1

        self.assertTrue(self._equal_counts(fd_true, fd_test))

    def test_prot_gapped(self):
        fd_test = self._prep_fd(['p-gapped'])

        fd_true = smof.FileDescription()
        fd_true.ntype['prot'] += 1
        fd_true.ncase['uppercase'] += 1
        fd_true.ufeat['gapped'] += 1

        self.assertTrue(self._equal_counts(fd_true, fd_test))

    def test_nucl_gapped(self):
        fd_test = self._prep_fd(['n-gapped'])

        fd_true = smof.FileDescription()
        fd_true.ntype['dna'] += 1
        fd_true.ncase['uppercase'] += 1
        fd_true.ufeat['gapped'] += 1
        fd_true.nfeat['0111'] += 1

        self.assertTrue(self._equal_counts(fd_true, fd_test))

    def test_illegal(self):
        fd_test = self._prep_fd(['illegal'])

        fd_true = smof.FileDescription()
        fd_true.ntype['illegal'] += 1
        fd_true.ncase['uppercase'] += 1

        self.assertTrue(self._equal_counts(fd_true, fd_test))

    def test_has_start(self):
        start = lambda s: smof.FileDescription._has_start(s)
        self.assertTrue(start('ATGGGT'))
        self.assertFalse(start('GGTATG'))
        self.assertFalse(start('GATGG'))
        self.assertFalse(start('GGGGG'))

    def test_has_stop(self):
        stop = lambda s: smof.FileDescription._has_stop(s)
        for codon in ('TAA', 'TAG', 'TGA'):
            self.assertTrue(stop('GGG%s' % codon))
            self.assertTrue(stop('GG%s' % codon))
            self.assertFalse(stop('%sGG' % codon))
            self.assertFalse(stop('G%sGG' % codon))
        self.assertTrue(stop('TAATGA'))
        self.assertTrue(stop('TAAgTGA'))

    def test_is_sense(self):
        sense = lambda s: smof.FileDescription._is_sense(s)
        self.assertTrue(sense('ATGGGGCCCTAA'))
        self.assertTrue(sense('CCCGGGCCCAAA'))
        self.assertTrue(sense('CCCGGGCCCTAA'))
        self.assertTrue(sense('CCCGTAAAAAAGG'))
        self.assertFalse(sense('CCCTAACCCAAA'))
        self.assertFalse(sense('ATGTAACCCAAA'))
        self.assertFalse(sense('ATGCCCTAATAA'))

    def test_is_triple(self):
        triple = lambda s: smof.FileDescription._is_triple(s)
        self.assertTrue(triple('ATG'))
        self.assertTrue(triple('ATGGGG'))
        self.assertFalse(triple('ATGGGGg'))
        self.assertFalse(triple('ATGGGGgg'))

    def test_nfeat(self):
        from itertools import product as product
        def test_profile(prof):
            fd = self._prep_fd([prof])
            return(bool(fd.nfeat[prof]))
        for prof in [''.join(c) for c in product('01', repeat=4)]:
            self.assertTrue(test_profile(prof), 'nfeat profile: %s, failed' % prof)

class TestUtilities(unittest.TestCase):
    def setUp(self):
        self.seq = smof.FSeq('seq', 'ACDEFSTVWY')

    def test_counter_caser(self):
        self.assertEqual(smof.counter_caser(Counter('Aaa')), {'A':3})
        self.assertEqual(smof.counter_caser(Counter('Aaa'), True), {'a':3})

    def test_sum_lower(self):
        self.assertEqual(smof.sum_lower(Counter('AaaFf')), 3)
        self.assertEqual(smof.sum_lower(Counter('AAAFF')), 0)
        self.assertEqual(smof.sum_lower(Counter('AaaF.{')), 2)

    def test_guess_type_input(self):
        # String input
        self.assertEqual(smof.guess_type('FFFF'), 'prot')
        # Counter object input
        self.assertEqual(smof.guess_type(Counter('FFFF')), 'prot')
        # FSeq object input
        self.assertEqual(smof.guess_type(smof.FSeq('s1', 'FFFF')), 'prot')
        # Gaps should be ignored
        self.assertEqual(smof.guess_type(smof.FSeq('s1', 'F-F_F.F')), 'prot')
        # Case should be ignored
        self.assertEqual(smof.guess_type(smof.FSeq('s1', 'ffff')), 'prot')

    def test_guess_type_dna(self):
        self.assertEqual(smof.guess_type('GATACA'), 'dna')
        self.assertEqual(smof.guess_type('GATACANNN'), 'dna')
        self.assertEqual(smof.guess_type('NNNNNN'), 'dna')

    def test_guess_type_rna(self):
        self.assertEqual(smof.guess_type('GAUACA'), 'rna')

    def test_guess_type_prot(self):
        self.assertEqual(smof.guess_type('FAMNX'), 'prot')
        self.assertEqual(smof.guess_type('XXXXX'), 'prot')

    def test_guess_type_illegal(self):
        self.assertEqual(smof.guess_type('DAMO'), 'illegal')
        self.assertEqual(smof.guess_type('DAM!'), 'illegal')
        # A nucleotide sequence can't have both U and T
        self.assertEqual(smof.guess_type('GATU'), 'illegal')
        # Space is illegal
        self.assertEqual(smof.guess_type('DAM '), 'illegal')
        # Gaps should NOT be counted as illegal
        self.assertNotEqual(smof.guess_type('D.A-M_'), 'illegal')
        # * should not be illegal (indicates STOP in protein sequence)
        self.assertNotEqual(smof.guess_type('DA*M*'), 'illegal')

    def test_guess_type_ambiguous(self):
        self.assertEqual(smof.guess_type('A'), 'ambiguous')
        self.assertEqual(smof.guess_type('AT'), 'ambiguous')
        self.assertNotEqual(smof.guess_type('ATG'), 'ambiguous')
        self.assertNotEqual(smof.guess_type('AUG'), 'ambiguous')
        # Greater than 80% nucleotide characters with ambiguous is dna
        self.assertEqual(smof.guess_type('ATGGR'), 'ambiguous')
        self.assertEqual(smof.guess_type('ATGGGR'), 'dna')
        # Sequences containing only ambiguous nucleotides (could be dna or
        # protein) are counted as ambiguous regardless of lenght
        self.assertEqual(smof.guess_type('WYS'), 'ambiguous')
        self.assertEqual(smof.guess_type('RYSWKMDBHV'), 'ambiguous')
        # But if one unambiguous aa is added ('F')
        self.assertEqual(smof.guess_type('FRYSWKMDBHV'), 'prot')

    def test_counting_number(self):
        import argparse
        self.assertRaises(argparse.ArgumentTypeError, smof.counting_number, 0)
        self.assertRaises(argparse.ArgumentTypeError, smof.counting_number, -1)

    def test_positive_int(self):
        import argparse
        self.assertRaises(argparse.ArgumentTypeError, smof.positive_int, -1)
        try:
            smof.positive_int(0)
            zero_calls_exception = False
        except argparse.ArgumentTypeError:
            zero_calls_exception = True
        self.assertFalse(zero_calls_exception)

    def test_headtailtrunk_first(self):
        # Note: argparse will only allow positive integers
        self.assertEqual(smof.headtailtrunk(seq=self.seq, first=1, last=0).seq, 'A')
        self.assertEqual(smof.headtailtrunk(seq=self.seq, first=5, last=0).seq, 'ACDEF')
        self.assertEqual(smof.headtailtrunk(seq=self.seq, first=20, last=0).seq, 'ACDEFSTVWY')

    def test_headtailtrunk_last(self):
        self.assertEqual(smof.headtailtrunk(seq=self.seq, first=0, last=1).seq, 'Y')
        self.assertEqual(smof.headtailtrunk(seq=self.seq, first=0, last=5).seq, 'STVWY')
        self.assertEqual(smof.headtailtrunk(seq=self.seq, first=0, last=20).seq, 'ACDEFSTVWY')

    def test_headtailtrunk_firstandlast(self):
        self.assertEqual(smof.headtailtrunk(seq=self.seq, first=1, last=1).seq, 'A...Y')
        self.assertEqual(smof.headtailtrunk(seq=self.seq, first=2, last=3).seq, 'AC...VWY')
        self.assertEqual(smof.headtailtrunk(seq=self.seq, first=5, last=5).seq, 'ACDEFSTVWY')
        self.assertEqual(smof.headtailtrunk(seq=self.seq, first=6, last=6).seq, 'ACDEFSTVWY')

    def test_headtailtrunk_doublezero(self):
        self.assertRaises(SystemExit, smof.headtailtrunk, seq=self.seq, first=0, last=0)

class TestFSeqGenerator(unittest.TestCase):
    def setUp(self):
        self.seq1 = smof.FSeq(header='seq1', seq='ACGTA')
        self.seq2 = smof.FSeq(header='seq2', seq='GGTT')
        self.seq1_spaced = smof.FSeq(header='seq1', seq='AC GTA')
        self.seq2_spaced = smof.FSeq(header='seq2', seq='GGTT')
        self.seq1_weird = smof.FSeq(header="seq1 >weirdness", seq='ACGTA')

        self.good = [
            ">seq1", "ACGT", "A",
            ">seq2", "GGT", "T"
        ]
        self.good_empty_lines = [
            ">seq1", "ACGT", "A", "\n",
            ">seq2", "GGT", "T", "\n"
        ]
        self.weird_empty_lines = [
            "\n", ">seq1", "ACGT", "\n", "A", "\n",
            ">seq2", "GGT", "T", "\n"
        ]
        self.spaced = [
            " >seq1", "AC GT", "A",
            " >seq2 ", " GGT", "T "
        ]
        self.well_commented = [
            "# this is a comment",
            "# so is this",
            ">seq1", "ACGT", "A",
            ">seq2", "GGT", "T"
        ]
        self.interspersed_comments = [
            "# this is a comment",
            ">seq1", "ACGT", "A",
            "# so is this",
            ">seq2", "GGT", "T"
        ]
        self.bad_first = [
            "A",
            ">seq1", "ACGT", "A",
            ">seq2", "GGT", "T"
        ]
        self.empty_seq = [
            ">seq1",
            ">seq2", "GGT", "T"
        ]
        self.empty_last_seq = [
            ">seq1", "ACGT", "A",
            ">seq2"
        ]
        self.internal_gt = [
            ">seq1 >weirdness", "ACGT", "A",
        ]
        self.no_sequence = []

    def cmp_seqs(self, fh, exp_seqs):
        g = smof.FSeqGenerator(fh)
        obs_seqs = [s for s in g.next()]
        for obs, exp in zip(obs_seqs, exp_seqs):
            if (obs.header != exp.header) or (obs.seq != exp.seq):
                print([obs.header, exp.header])
                return(False)
        return(True)

    def is_valid(self, fh):
        try:
            g = smof.FSeqGenerator(fh)
            out = [s for s in g.next()]
            return(True)
        except BaseException:
            return(False)

    def test_good(self):
        self.assertTrue(self.cmp_seqs(self.good, (self.seq1, self.seq2)))

    def test_good_empty_lines(self):
        self.assertTrue(self.cmp_seqs(self.good_empty_lines, (self.seq1, self.seq2)))

    def test_weird_empty_lines(self):
        self.assertTrue(self.cmp_seqs(self.weird_empty_lines, (self.seq1, self.seq2)))

    def test_spaced(self):
        self.assertTrue(self.cmp_seqs(self.spaced, (self.seq1_spaced, self.seq2_spaced)))

    def test_well_commented(self):
        self.assertTrue(self.cmp_seqs(self.well_commented, (self.seq1, self.seq2)))

    def test_interspersed_comments(self):
        self.assertTrue(self.cmp_seqs(self.interspersed_comments, (self.seq1, self.seq2)))

    def test_internal_gt(self):
        self.assertTrue(self.cmp_seqs(self.internal_gt, [self.seq1_weird]))

    def test_bad_first(self):
        self.assertFalse(self.is_valid(self.bad_first))

    def test_empty_seq(self):
        self.assertFalse(self.is_valid(self.empty_seq))

    def test_empty_last_seq(self):
        self.assertFalse(self.is_valid(self.empty_last_seq))

    def test_no_sequence(self):
        self.assertFalse(self.is_valid(self.no_sequence))


if __name__ == '__main__':
    unittest.main()
