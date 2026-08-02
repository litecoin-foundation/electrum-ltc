from hashlib import sha256
from decimal import Decimal
from binascii import unhexlify, hexlify
import pprint
import unittest

import electrum_ecc as ecc

from electrum.bolt11 import (shorten_amount, unshorten_amount, BOLT11Addr, encode_bolt11_invoice,
                             decode_bolt11_invoice, parse_fallback_addr, int_to_data5, tagged5, tagged8,
                             BOLT11DecodeException, BOLT11InvoiceException, TIMESTAMP_SANE_MAX)
from electrum.segwit_addr import bech32_encode, bech32_decode, convertbits, CHARSET_INVERSE
from electrum import segwit_addr
from electrum.lnutil import UnknownEvenFeatureBits, LnFeatures, IncompatibleLightningFeatures
from electrum import constants
from electrum.util import bfh, ShortID

from . import ElectrumTestCase


RHASH=unhexlify('0001020304050607080900010203040506070809000102030405060708090102')
PAYMENT_SECRET=unhexlify('1111111111111111111111111111111111111111111111111111111111111111')
CONVERSION_RATE=1200
PRIVKEY=unhexlify('e126f68f7eafcc8b74f54d269fe206be715000f94dac067d1c04a8ca3b2db734')
PUBKEY=unhexlify('03e7156ae33b0a208d0744199163177e909e80176e55d97a2f221ede0f934dd9ad')


class TestBolt11(ElectrumTestCase):
    def test_shorten_amount(self):
        tests = {
            Decimal(10)/10**12: '10p',
            Decimal(1000)/10**12: '1n',
            Decimal(1200)/10**12: '1200p',
            Decimal(123)/10**6: '123u',
            Decimal(123)/1000: '123m',
            Decimal(3): '3',
            Decimal(1000): '1000',
        }

        for i, o in tests.items():
            self.assertEqual(shorten_amount(i), o)
            assert unshorten_amount(shorten_amount(i)) == i

    @staticmethod
    def compare(a, b):

        if len([t[1] for t in a.tags if t[0] == 'h']) == 1:
            h1 = sha256([t[1] for t in a.tags if t[0] == 'h'][0].encode('utf-8')).digest()
            h2 = [t[1] for t in b.tags if t[0] == 'h'][0]
            assert h1 == h2

        # Need to filter out these, since they are being modified during
        # encoding, i.e., hashed
        a.tags = [t for t in a.tags if t[0] != 'h' and t[0] != 'n']
        b.tags = [t for t in b.tags if t[0] != 'h' and t[0] != 'n']

        assert b.pubkey.serialize() == PUBKEY, (hexlify(b.pubkey.serialize()), hexlify(PUBKEY))
        assert b.signature is not None

        # Unset these, they are generated during encoding/decoding
        b.pubkey = None
        b.signature = None

        assert a.__dict__ == b.__dict__, (pprint.pformat([a.__dict__, b.__dict__]))

    def test_roundtrip(self):
        longdescription = ('One piece of chocolate cake, one icecream cone, one'
                          ' pickle, one slice of swiss cheese, one slice of salami,'
                          ' one lollypop, one piece of cherry pie, one sausage, one'
                          ' cupcake, and one slice of watermelon')

        timestamp = 1615922274
        tests = [
            (BOLT11Addr(date=timestamp, paymenthash=RHASH, payment_secret=PAYMENT_SECRET, tags=[('d', ''), ('9', 33282)]),
             "lnltc1ps9zprzpp5qqqsyqcyq5rqwzqfqqqsyqcyq5rqwzqfqqqsyqcyq5rqwzqfqypqsp5zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zygsdqq9qypqszqzgtd6vmekfly93cnrul3772cx24w0l0cqka4cpywy9km3dxwq330e2k648zeknmxztfk84j4esx00nx79374q0wa444zydl402rh5cqgf65sq"),
            (BOLT11Addr(date=timestamp, paymenthash=RHASH, payment_secret=PAYMENT_SECRET, amount=Decimal('0.001'), tags=[('d', '1 cup coffee'), ('x', 60), ('9', 0x28200)]),
             "lnltc1m1ps9zprzpp5qqqsyqcyq5rqwzqfqqqsyqcyq5rqwzqfqqqsyqcyq5rqwzqfqypqsp5zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zygsdq5xysxxatsyp3k7enxv4jsxqzpu9qy9qsqrk5p227neujjnf8pna3law67zuqtq7w37ja37tkwytmzum80dnk8gc3ewlv7xpmjhsw5av7t0sfwqpvl0wes95cwqlsx7c43vadkwfgpe7axap"),
            (BOLT11Addr(date=timestamp, paymenthash=RHASH, payment_secret=PAYMENT_SECRET, amount=Decimal('1'), tags=[('h', longdescription), ('9', 0x28200)]),
             "lnltc11ps9zprzpp5qqqsyqcyq5rqwzqfqqqsyqcyq5rqwzqfqqqsyqcyq5rqwzqfqypqsp5zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zygshp58yjmdan79s6qqdhdzgynm4zwqd5d7xmw5fk98klysy043l2ahrqs9qy9qsqfydt5gh5fw6rc0utv0rmtkphx7tldh2zdasseqyv3vjtsnt7zrx4qt4l7gn9s2vjstt3v28ernw42gpfmrtk843j0rnvaxy70zdv6tspwtatxk"),
            (BOLT11Addr(date=timestamp, paymenthash=RHASH, payment_secret=PAYMENT_SECRET, net=constants.BitcoinTestnet, tags=[('f', 'mk2QpYatsKicvFVuTAQLBryyccRXMUaGHP'), ('h', longdescription), ('9', 0x28200)]),
             "lntltc1ps9zprzpp5qqqsyqcyq5rqwzqfqqqsyqcyq5rqwzqfqqqsyqcyq5rqwzqfqypqsp5zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zygsfpp3x9et2e20v6pu37c5d9vax37wxq72un98hp58yjmdan79s6qqdhdzgynm4zwqd5d7xmw5fk98klysy043l2ahrqs9qy9qsqwzq273x6gc0xfy3p50r7uy5ppk5tvf34ndssdqpmhcv4q56x2zq564wyga03dmvmnjr4vka3vr33al8ftrn0zhg5083tzrsp2juvgwqqk6qk2w"),
            (BOLT11Addr(date=timestamp, paymenthash=RHASH, payment_secret=PAYMENT_SECRET, amount=24, tags=[
                ('r', [(unhexlify('029e03a901b85534ff1e92c43c74431f7ce72046060fcf7a95c37e148f78c77255'), unhexlify('0102030405060708'), 1, 20, 3),
                       (unhexlify('039e03a901b85534ff1e92c43c74431f7ce72046060fcf7a95c37e148f78c77255'), unhexlify('030405060708090a'), 2, 30, 4)]),
                ('f', 'LKes97HFbh3dxrvhiMohYXyzYJPTK37n7u'),
                ('h', longdescription),
                ('9', 0x28200)]),
             "lnltc241ps9zprzpp5qqqsyqcyq5rqwzqfqqqsyqcyq5rqwzqfqqqsyqcyq5rqwzqfqypqsp5zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zygsr9yq20q82gphp2nflc7jtzrcazrra7wwgzxqc8u7754cdlpfrmccae92qgzqvzq2ps8pqqqqqqpqqqqq9qqqvpeuqafqxu92d8lr6fvg0r5gv0heeeqgcrqlnm6jhphu9y00rrhy4grqszsvpcgpy9qqqqqqgqqqqq7qqzqfpp3qjmp7lwpagxun9pygexvgpjdc4jdj85fhp58yjmdan79s6qqdhdzgynm4zwqd5d7xmw5fk98klysy043l2ahrqs9qy9qsqr8k87557npyvh09gymtdx6p6s0f6aw5djakjvtzhcxu6akhg0nus8336gtm37fpt0462e5jckxzrwgfstm2ffmevrdfjta9j8h4y54gp5d5x9w"),
            (BOLT11Addr(date=timestamp, paymenthash=RHASH, payment_secret=PAYMENT_SECRET, amount=24, tags=[('f', 'MLy36ApB4YZb2cBtTc1uYJhYsP2JkYokaf'), ('h', longdescription), ('9', 0x28200)]),
             "lnltc241ps9zprzpp5qqqsyqcyq5rqwzqfqqqsyqcyq5rqwzqfqqqsyqcyq5rqwzqfqypqsp5zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zygsfppj3a24vwu6r8ejrss3axul8rxldph2q7z9hp58yjmdan79s6qqdhdzgynm4zwqd5d7xmw5fk98klysy043l2ahrqs9qy9qsq0my3shwh9l5rad2mvtupgdgk0dx3sw92wemlxfkwey84jg4szkpn49s7spa24q8uue83h4xv99v6q8rvk8zmhwx6vn6nwpe2kntgetgp2gxp4f"),
            (BOLT11Addr(date=timestamp, paymenthash=RHASH, payment_secret=PAYMENT_SECRET, amount=24, tags=[('f', 'ltc1qw508d6qejxtdg4y5r3zarvary0c5xw7kgmn4n9'), ('h', longdescription), ('9', 0x28200)]),
             "lnltc241ps9zprzpp5qqqsyqcyq5rqwzqfqqqsyqcyq5rqwzqfqqqsyqcyq5rqwzqfqypqsp5zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zygsfppqw508d6qejxtdg4y5r3zarvary0c5xw7khp58yjmdan79s6qqdhdzgynm4zwqd5d7xmw5fk98klysy043l2ahrqs9qy9qsqff8reqynw3sfw4wshnda55706cztd6lpj7aalxpu3zvwyk2uvlzyrxw3l8hc3rawnwgzjasch08scayt7xy5lg0ndm3g2pdzgya993cp3hld9a"),
            (BOLT11Addr(date=timestamp, paymenthash=RHASH, payment_secret=PAYMENT_SECRET, amount=24, tags=[('f', 'ltc1qrp33g0q5c5txsp9arysrx4k6zdkfs4nce4xj0gdcccefvpysxf3qmu8tk5'), ('h', longdescription), ('9', 0x28200)]),
             "lnltc241ps9zprzpp5qqqsyqcyq5rqwzqfqqqsyqcyq5rqwzqfqqqsyqcyq5rqwzqfqypqsp5zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zygsfp4qrp33g0q5c5txsp9arysrx4k6zdkfs4nce4xj0gdcccefvpysxf3qhp58yjmdan79s6qqdhdzgynm4zwqd5d7xmw5fk98klysy043l2ahrqs9qy9qsqvtrtqgp5mpu2llc53wxzxxyqvqggykx8s98kjm0lvnpk4ll2xn9rudasmlzhmntgg7h8kqnwscc8esk8rtqke3wqezzk0k8kwewzvzqp40vma6"),
            (BOLT11Addr(date=timestamp, paymenthash=RHASH, payment_secret=PAYMENT_SECRET, amount=24, tags=[('n', PUBKEY), ('h', longdescription), ('9', 0x28200)]),
             "lnltc241ps9zprzpp5qqqsyqcyq5rqwzqfqqqsyqcyq5rqwzqfqqqsyqcyq5rqwzqfqypqsp5zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zygsnp4q0n326hr8v9zprg8gsvezcch06gfaqqhde2aj730yg0durunfhv66hp58yjmdan79s6qqdhdzgynm4zwqd5d7xmw5fk98klysy043l2ahrqs9qy9qsqg60uez77a5p0p9m4eezrxkxvng986xjrqujxkqd7ntmtxrwlvm75hglnqsh3z9fwr82rfs8pk7qsdx526l73hjhem2g5np6rgcfqa6qpty228q"),
            (BOLT11Addr(date=timestamp, paymenthash=RHASH, payment_secret=PAYMENT_SECRET, amount=24, tags=[('h', longdescription), ('9', 2 + (1 << 9) + (1 << 15))]),
             "lnltc241ps9zprzpp5qqqsyqcyq5rqwzqfqqqsyqcyq5rqwzqfqqqsyqcyq5rqwzqfqypqsp5zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zygshp58yjmdan79s6qqdhdzgynm4zwqd5d7xmw5fk98klysy043l2ahrqs9qypqszxkdza3c2a8mx7htenxyj28tl9uhs6zd8pz8nec3n2s7k0zzas4cn6jcgnk4j49zu552kwlg6nz4lcl847d8g26nf6lxn4c0y7jmkkjsqt2wsey"),
            (BOLT11Addr(date=timestamp, paymenthash=RHASH, payment_secret=PAYMENT_SECRET, amount=24, tags=[('h', longdescription), ('9', 10 + (1 << 8) + (1 << 15))]),
             "lnltc241ps9zprzpp5qqqsyqcyq5rqwzqfqqqsyqcyq5rqwzqfqqqsyqcyq5rqwzqfqypqsp5zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zygshp58yjmdan79s6qqdhdzgynm4zwqd5d7xmw5fk98klysy043l2ahrqs9qypqg2gl3auylqzqmk9fjgg5medm9xcduc4pwhpgah3wv46m86tp2my6jnh4fqgq23n0dfhuy8zy7ml506e0lzugrw0trslluw9y76g2x778sqzgmqk5"),
            (BOLT11Addr(date=timestamp, paymenthash=RHASH, payment_secret=PAYMENT_SECRET, amount=24, tags=[('h', longdescription), ('9', 10 + (1 << 9) + (1 << 15))]),
             "lnltc241ps9zprzpp5qqqsyqcyq5rqwzqfqqqsyqcyq5rqwzqfqqqsyqcyq5rqwzqfqypqsp5zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zygshp58yjmdan79s6qqdhdzgynm4zwqd5d7xmw5fk98klysy043l2ahrqs9qypqs2g6vwg4g7u9etssefv0rkd90ttkwqs3j3klwq7xzftyw9zx4nl9aj74p42p58fphv0qyu4g5hu8p840efazhxhve300wpzgqgf6ntmpsp88c9xn"),
            (BOLT11Addr(date=timestamp, paymenthash=RHASH, payment_secret=PAYMENT_SECRET, amount=24, tags=[('h', longdescription), ('9', 10 + (1 << 9) + (1 << 14))]),
             "lnltc241ps9zprzpp5qqqsyqcyq5rqwzqfqqqsyqcyq5rqwzqfqqqsyqcyq5rqwzqfqypqsp5zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zygshp58yjmdan79s6qqdhdzgynm4zwqd5d7xmw5fk98klysy043l2ahrqs9qrss2q90trpgcmhjq7lyv9dgu5dtc5uu3jk6a052fpx4ma4awff4u57sp2947rxwhn00sqqxlnnnhkqpfnm3ep73ur0rrhsemcys9v77q0fsqchjpv2"),
        ]

        # Roundtrip
        for lnaddr1, invoice_str1 in tests:
            invoice_str2 = encode_bolt11_invoice(lnaddr1, PRIVKEY)
            self.assertEqual(invoice_str1, invoice_str2)
            lnaddr2 = decode_bolt11_invoice(invoice_str2, net=lnaddr1.net)
            self.assertEqual(invoice_str1, encode_bolt11_invoice(lnaddr2, PRIVKEY))
            self.compare(lnaddr1, lnaddr2)

    def test_int_to_data5_padding(self):
        # if bit_len is given, the result is left-padded with zeroes to exactly bit_len//5 values
        self.assertEqual([0, 0, 0, 0, 0, 1, 8], list(int_to_data5(40, bit_len=35)))
        self.assertEqual([1, 16, 5, 2, 1, 3, 2], list(int_to_data5(1615922274, bit_len=35)))
        # ... so the fixed-width timestamp field stays 7 values wide and a small date roundtrips
        lnaddr = BOLT11Addr(date=1000, paymenthash=RHASH, payment_secret=PAYMENT_SECRET, tags=[('d', '')])
        self.assertEqual(1000, decode_bolt11_invoice(encode_bolt11_invoice(lnaddr, PRIVKEY)).date)

    def test_n_decoding(self):
        # We flip the signature recovery bit, which would normally give a different
        # pubkey.
        _, hrp, data = bech32_decode(
            encode_bolt11_invoice(BOLT11Addr(paymenthash=RHASH, payment_secret=PAYMENT_SECRET, amount=24, tags=[('d', ''), ('9', 33282)]), PRIVKEY),
            ignore_long_length=True)
        data[-1] ^= 1
        lnaddr = decode_bolt11_invoice(bech32_encode(segwit_addr.Encoding.BECH32, hrp, data), verbose=True)
        self.assertNotEqual(lnaddr.pubkey.serialize(), PUBKEY)

        # But not if we supply expliciy `n` specifier!
        _, hrp, data = bech32_decode(
            encode_bolt11_invoice(BOLT11Addr(paymenthash=RHASH, payment_secret=PAYMENT_SECRET, amount=24, tags=[('d', ''), ('n', PUBKEY), ('9', 33282)]), PRIVKEY),
            ignore_long_length=True)
        data[-1] ^= 1
        lnaddr = decode_bolt11_invoice(bech32_encode(segwit_addr.Encoding.BECH32, hrp, data), verbose=True)
        self.assertEqual(lnaddr.pubkey.serialize(), PUBKEY)

        # the 'n' field is kept as a tag, so that re-encoding does not silently drop it
        invoice = encode_bolt11_invoice(
            BOLT11Addr(date=1615922274, paymenthash=RHASH, payment_secret=PAYMENT_SECRET, amount=24,
                       tags=[('d', ''), ('n', PUBKEY), ('9', 33282)]), PRIVKEY)
        lnaddr = decode_bolt11_invoice(invoice)
        self.assertEqual(PUBKEY, lnaddr.get_tag('n'))
        self.assertEqual(invoice, encode_bolt11_invoice(lnaddr, PRIVKEY))

    @staticmethod
    def _encode_invoice_with_raw_tags(tags5, *, net=None, date=1615922274, amountstr='') -> str:
        """Builds a correctly signed invoice containing exactly the given (tag, data5) fields."""
        net = net or constants.BitcoinMainnet
        hrp = 'ln' + net.BOLT11_HRP + amountstr
        data5 = list(int_to_data5(date, bit_len=35))
        for tag, tagdata5 in tags5:
            data5 += list(tagged5(tag, list(tagdata5)))
        msg32 = sha256(hrp.encode('ascii') + bytes(convertbits(data5, 5, 8))).digest()
        sig = ecc.ECPrivkey(PRIVKEY).ecdsa_sign_recoverable(msg32, is_compressed=False)
        sig = bytes(sig[1:]) + bytes([sig[0] - 27])
        return bech32_encode(segwit_addr.Encoding.BECH32, hrp, data5 + list(convertbits(sig, 8, 5, False)))

    @staticmethod
    def _encode_invoice_with_raw_tag(tag, tagdata5, *, net=None, date=1615922274, expiry=None) -> str:
        """Builds a correctly signed invoice with one arbitrary (possibly malformed) tagged field."""
        tags5 = []
        if tag != 'p':
            tags5.append(('p', convertbits(RHASH, 8, 5)))
        if tag != 's':
            tags5.append(('s', convertbits(PAYMENT_SECRET, 8, 5)))
        if tag not in ('d', 'h'):  # exactly one of 'd'/'h' must be present
            tags5.append(('d', convertbits(b'test', 8, 5)))
        if expiry is not None:
            tags5.append(('x', int_to_data5(expiry)))
        tags5.append((tag, tagdata5))
        return TestBolt11._encode_invoice_with_raw_tags(tags5, net=net, date=date)

    @staticmethod
    def _encode_invoice_with_raw_sig(sig65, *, net=None) -> str:
        """Builds an invoice with an arbitrary (possibly invalid) 65-byte signature.
        Note: no 'n' field, so decoding goes through pubkey recovery."""
        net = net or constants.BitcoinMainnet
        hrp = 'ln' + net.BOLT11_HRP
        data5 = list(int_to_data5(1615922274, bit_len=35))
        data5 += list(tagged8('p', RHASH))
        data5 += list(tagged8('s', PAYMENT_SECRET))
        data5 += list(tagged8('d', b'test'))
        return bech32_encode(segwit_addr.Encoding.BECH32, hrp, data5 + list(convertbits(sig65, 8, 5, False)))

    def test_parse_fallback_addr(self):
        net = constants.BitcoinMainnet

        def parse(wver, data8):
            return parse_fallback_addr([wver] + list(convertbits(data8, 8, 5)), net)

        # p2pkh/p2sh: the payload must be a hash160
        self.assertEqual('LKDxGDJq5fF4FohAB8zJH24mDDNHDNtqsE', parse(17, bytes(20)))
        self.assertEqual('M7uAERuQW2AotfyLDyewFGcLUDtAYu9v5V', parse(18, bytes(20)))
        for nbytes in (0, 1, 19, 21, 32, 40):
            self.assertIsNone(parse(17, bytes(nbytes)))
            self.assertIsNone(parse(18, bytes(nbytes)))
        # segwit v0: the witness program must be 20 or 32 bytes
        self.assertEqual('ltc1qqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqp9ysmq', parse(0, bytes(20)))
        self.assertEqual('ltc1qqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqgnwq3z', parse(0, bytes(32)))
        for nbytes in (0, 1, 19, 21, 40, 41):
            self.assertIsNone(parse(0, bytes(nbytes)))
        # segwit v1-v16: the witness program must be 2-40 bytes
        for wver in (1, 16):
            self.assertIsNotNone(parse(wver, bytes(2)))
            self.assertIsNotNone(parse(wver, bytes(40)))
            for nbytes in (0, 1, 41):
                self.assertIsNone(parse(wver, bytes(nbytes)))
        # unknown witness versions
        self.assertIsNone(parse(19, bytes(20)))
        self.assertIsNone(parse(31, bytes(20)))
        # truncated/malformed frames
        self.assertIsNone(parse_fallback_addr([], net))
        self.assertIsNone(parse_fallback_addr(bytearray(), net))
        self.assertIsNone(parse_fallback_addr([16, 1], net))  # non-zero padding bits
        self.assertIsNone(parse_fallback_addr([17, 1], net))

    def test_malformed_fallback_addr_is_skipped(self):
        # BOLT #11: "A reader MUST skip over [...] an `f` field with unknown `version`".
        # A malformed 'f' field must not abort decoding of the whole invoice.
        for tagdata5 in ([],                # empty payload
                         [16, 1],           # non-zero padding bits
                         [17] + [0] * 4,    # p2pkh with a too-short hash160
                         [0] + [0] * 4,     # p2wpkh with a too-short witness program
                         [19, 0, 0]):       # unknown witness version
            lnaddr = decode_bolt11_invoice(self._encode_invoice_with_raw_tag('f', tagdata5))
            self.assertIsNone(lnaddr.get_tag('f'))
            self.assertEqual('', lnaddr.get_fallback_address())
            self.assertEqual(['f'], [tag for tag, _ in lnaddr.unknown_tags])
        # sanity: a well-formed 'f' field is still parsed
        lnaddr = decode_bolt11_invoice(
            self._encode_invoice_with_raw_tag('f', [17] + list(convertbits(bytes(20), 8, 5))))
        self.assertEqual('LKDxGDJq5fF4FohAB8zJH24mDDNHDNtqsE', lnaddr.get_fallback_address())
        self.assertEqual([], lnaddr.unknown_tags)

    def test_tag_padding_errors(self):
        # A tag whose 5->8 bit conversion has non-zero padding bits (or a length that cannot
        # be converted at all) is malformed: it must be rejected, not crash the parser.
        for tag, tagdata5 in (('d', [1]),               # 5 bits left over: no valid conversion
                              ('d', [0, 1]),            # non-zero padding bits
                              ('h', [0] * 51 + [1]),    # data_length 52, non-zero padding bits
                              ('p', [0] * 51 + [1]),
                              ('s', [0] * 51 + [1]),
                              ('n', [0] * 52 + [1]),    # data_length 53, non-zero padding bit
                              ('r', [1]),
                              ('r', [0, 1])):
            with self.subTest(tag=tag, tagdata5=tagdata5):
                with self.assertRaises(BOLT11DecodeException):
                    decode_bolt11_invoice(self._encode_invoice_with_raw_tag(tag, tagdata5))

        # control: the same lengths with zero padding bits decode fine
        for tag, tagdata5 in (('d', [0, 0]),
                              ('h', [0] * 51 + [16]),
                              ('p', [0] * 51 + [16]),
                              ('s', [0] * 51 + [16]),
                              ('n', list(convertbits(PUBKEY, 8, 5))),
                              ('r', [0] * 8)):
            with self.subTest(tag=tag):
                decode_bolt11_invoice(self._encode_invoice_with_raw_tag(tag, tagdata5))

        # 'h', 'p', 's' and 'n' have a fixed data_length: a wrong length rejects the invoice
        for tag, data_length in (('h', 52), ('p', 52), ('s', 52), ('n', 53)):
            for wrong_length in (data_length - 1, data_length + 1):
                with self.subTest(tag=tag, data_length=wrong_length):
                    with self.assertRaises(BOLT11DecodeException):
                        decode_bolt11_invoice(
                            self._encode_invoice_with_raw_tag(tag, [0] * wrong_length))

        # 'r': an empty payload converts to b'' instead of failing, so it is skipped
        lnaddr = decode_bolt11_invoice(self._encode_invoice_with_raw_tag('r', []))
        self.assertIsNone(lnaddr.get_tag('r'))
        self.assertEqual([], lnaddr.unknown_tags)

        # control: a well-formed hop is parsed
        r_hop = bytes(33) + bytes(8) + (1).to_bytes(4, 'big') + (2).to_bytes(4, 'big') + (3).to_bytes(2, 'big')
        invoice = self._encode_invoice_with_raw_tag('r', list(convertbits(r_hop, 8, 5)))
        self.assertEqual(1, len(decode_bolt11_invoice(invoice).get_routing_info()))

    def test_invalid_signature(self):
        # The trailing 65 bytes of an invoice are attacker-controlled: every way the ecc lib
        # can reject them must surface as BOLT11DecodeException, not leak out of the parser.
        r_ok = (1).to_bytes(32, 'big')
        s_ok = (1).to_bytes(32, 'big')

        # the recovery id (the last byte) must be 0-3
        for recid in (4, 27, 255):
            with self.subTest(recid=recid):
                with self.assertRaisesRegex(BOLT11DecodeException, r"^Invalid signature:"):
                    decode_bolt11_invoice(self._encode_invoice_with_raw_sig(r_ok + s_ok + bytes([recid])))

        # r and s must be below the curve order
        for label, sig64 in (('r == n', ecc.CURVE_ORDER.to_bytes(32, 'big') + s_ok),
                             ('r == n+1', (ecc.CURVE_ORDER + 1).to_bytes(32, 'big') + s_ok),
                             ('r == 2**256-1', b'\xff' * 32 + s_ok),
                             ('s == n', r_ok + ecc.CURVE_ORDER.to_bytes(32, 'big')),
                             ('s == n+1', r_ok + (ecc.CURVE_ORDER + 1).to_bytes(32, 'big')),
                             ('s == 2**256-1', r_ok + b'\xff' * 32)):
            with self.subTest(sig=label):
                with self.assertRaisesRegex(BOLT11DecodeException, r"^Invalid signature:"):
                    decode_bolt11_invoice(self._encode_invoice_with_raw_sig(sig64 + b'\x00'))

        # in-range but unrecoverable signature
        with self.assertRaisesRegex(BOLT11DecodeException, r"^Invalid signature:"):
            decode_bolt11_invoice(self._encode_invoice_with_raw_sig(r_ok + s_ok + b'\x03'))

        # an 'n' field that is not a valid curve point (this path uses ecdsa_verify, not recovery)
        with self.assertRaisesRegex(BOLT11DecodeException, r"^Invalid signature:"):
            decode_bolt11_invoice(self._encode_invoice_with_raw_tag('n', list(convertbits(bytes(33), 8, 5))))

    def test_mandatory_tags(self):
        # BOLT #11: a reader MUST fail the payment if a 'p' or 's' field is missing, and MUST
        # fail if neither a 'd' nor an 'h' field is present, or if both are present.
        p5 = convertbits(RHASH, 8, 5)
        s5 = convertbits(PAYMENT_SECRET, 8, 5)
        d5 = convertbits(b'test', 8, 5)
        h5 = convertbits(sha256(b'test').digest(), 8, 5)
        # control: 'd' and 'h' are each enough on their own
        lnaddr = decode_bolt11_invoice(self._encode_invoice_with_raw_tags([('p', p5), ('s', s5), ('d', d5)]))
        self.assertEqual('test', lnaddr.get_description())
        self.assertEqual(RHASH, lnaddr.paymenthash)
        self.assertEqual(PAYMENT_SECRET, lnaddr.payment_secret)
        decode_bolt11_invoice(self._encode_invoice_with_raw_tags([('p', p5), ('s', s5), ('h', h5)]))

        for label, tags5 in (("no 'p' field", [('s', s5), ('d', d5)]),
                             ("no 's' field", [('p', p5), ('d', d5)]),
                             ("neither 'd' nor 'h'", [('p', p5), ('s', s5)]),
                             ("both 'd' and 'h'", [('p', p5), ('s', s5), ('d', d5), ('h', h5)]),
                             ("no tagged fields at all", [])):
            with self.subTest(label):
                with self.assertRaises(BOLT11DecodeException):
                    decode_bolt11_invoice(self._encode_invoice_with_raw_tags(tags5))

    def test_duplicate_tags(self):
        p5 = convertbits(RHASH, 8, 5)
        s5 = convertbits(PAYMENT_SECRET, 8, 5)
        d5 = convertbits(b'test', 8, 5)
        h5 = convertbits(sha256(b'test').digest(), 8, 5)
        n5 = convertbits(PUBKEY, 8, 5)
        # a second copy of a field we only keep one value for is rejected
        for tag, tags5 in (('p', [('p', p5), ('p', p5), ('s', s5), ('d', d5)]),
                           ('s', [('p', p5), ('s', s5), ('s', s5), ('d', d5)]),
                           ('d', [('p', p5), ('s', s5), ('d', d5), ('d', d5)]),
                           ('h', [('p', p5), ('s', s5), ('h', h5), ('h', h5)]),
                           ('n', [('p', p5), ('s', s5), ('d', d5), ('n', n5), ('n', n5)])):
            with self.subTest(tag=tag):
                with self.assertRaisesRegex(BOLT11DecodeException, f"^Unexpected (multiple )?'{tag}' tags?$"):
                    decode_bolt11_invoice(self._encode_invoice_with_raw_tags(tags5))

    def test_invalid_utf8_description(self):
        # the 'd' field is UTF-8: an invalid encoding must be rejected, not crash the parser
        with self.assertRaises(BOLT11DecodeException):
            decode_bolt11_invoice(self._encode_invoice_with_raw_tag('d', convertbits(b'\xff\xfe', 8, 5)))
        # control: non-ASCII UTF-8 decodes fine
        description = 'ナンセンス 1杯'
        lnaddr = decode_bolt11_invoice(
            self._encode_invoice_with_raw_tag('d', convertbits(description.encode('utf-8'), 8, 5)))
        self.assertEqual(description, lnaddr.get_description())

    def test_non_minimal_data_length(self):
        # BOLT #11: a 'c', 'x' or '9' field "MUST use the minimum `data_length` possible, i.e.
        # no leading 0 field-elements"; a reader SHOULD treat a non-minimal one as invalid.
        for tag in ('x', 'c', '9'):
            for tagdata5 in ([0],               # zero, which is minimally encoded as an empty field
                             [0, 1, 28],        # 60, left-padded with one 0 element
                             [0] * 50 + [1]):   # 1, left-padded all the way
                with self.subTest(tag=tag, tagdata5=tagdata5):
                    with self.assertRaises(BOLT11DecodeException):
                        decode_bolt11_invoice(self._encode_invoice_with_raw_tag(tag, tagdata5))
            # control: minimally encoded values, zero (i.e. an empty field) included
            for tagdata5, value in (([], 0), ([31], 31), ([1, 28], 60)):
                with self.subTest(tag=tag, tagdata5=tagdata5):
                    lnaddr = decode_bolt11_invoice(self._encode_invoice_with_raw_tag(tag, tagdata5))
                    self.assertEqual(value, lnaddr.get_tag(tag))

        # the accessors see the decoded values
        self.assertEqual(60, decode_bolt11_invoice(
            self._encode_invoice_with_raw_tag('x', [1, 28])).get_expiry())
        self.assertEqual(31, decode_bolt11_invoice(
            self._encode_invoice_with_raw_tag('c', [31])).get_min_final_cltv_delta())

        # ... and whatever our own encoder emits is minimal, so it still roundtrips
        for tag in ('x', 'c', '9'):
            for value in (1, 31, 32, 60, 3600, 2 ** 40):
                with self.subTest(tag=tag, value=value):
                    addr = BOLT11Addr(date=1615922274, paymenthash=RHASH, payment_secret=PAYMENT_SECRET,
                                      tags=[('d', ''), (tag, value)])
                    lnaddr = decode_bolt11_invoice(encode_bolt11_invoice(addr, PRIVKEY))
                    self.assertEqual(value, lnaddr.get_tag(tag))
        # zero: 'x' and 'c' are written as an empty (still minimal) field, '9' is omitted entirely
        for tag, expected in (('x', 0), ('c', 0), ('9', None)):
            with self.subTest(tag=tag, value=0):
                addr = BOLT11Addr(date=1615922274, paymenthash=RHASH, payment_secret=PAYMENT_SECRET,
                                  tags=[('d', ''), (tag, 0)])
                lnaddr = decode_bolt11_invoice(encode_bolt11_invoice(addr, PRIVKEY))
                self.assertEqual(expected, lnaddr.get_tag(tag))

    def test_corrupt_tag_data(self):
        # A tagged field whose data_length runs past the end of the data part must be rejected.
        # Note the signature is split off the end first, so what is left for the tag loop is
        # attacker-controlled in length as well as content.
        hrp = 'ln' + constants.BitcoinMainnet.BOLT11_HRP
        body = list(int_to_data5(1615922274, bit_len=35))
        body += list(tagged8('p', RHASH)) + list(tagged8('s', PAYMENT_SECRET)) + list(tagged8('d', b'test'))
        sig5 = [0] * (65 * 8 // 5)

        def encode(data5):
            return bech32_encode(segwit_addr.Encoding.BECH32, hrp, data5)

        for label, trailer in (("data_length past end of data", [CHARSET_INVERSE['x'], 0, 20]),
                               ("1 stray data element", [CHARSET_INVERSE['x']]),
                               ("2 stray data elements", [CHARSET_INVERSE['x'], 0])):
            with self.subTest(label):
                with self.assertRaises(BOLT11DecodeException):
                    decode_bolt11_invoice(encode(body + trailer + sig5))
        # an invoice that is all tags and no signature: the last 65 bytes are taken to be the
        # signature regardless, which leaves a truncated tag behind
        with self.assertRaises(BOLT11DecodeException):
            decode_bolt11_invoice(encode(body))
        # ... and one shorter than a signature is rejected outright
        with self.assertRaises(BOLT11DecodeException):
            decode_bolt11_invoice(encode(list(int_to_data5(1615922274, bit_len=35))))
        # control: the same body followed by a signature-sized (if bogus) trailer gets all the
        # way past the tag loop, and fails on the signature instead
        with self.assertRaisesRegex(BOLT11DecodeException, 'signature'):
            decode_bolt11_invoice(encode(body + sig5))

    def test_bech32_errors(self):
        invoice = self._encode_invoice_with_raw_tag('x', int_to_data5(60))
        self.assertEqual(60, decode_bolt11_invoice(invoice).get_expiry())  # control

        for label, bad_invoice in (("corrupt checksum", invoice[:-1] + ('q' if invoice[-1] != 'q' else 'p')),
                                   ("mixed case", invoice[:8].upper() + invoice[8:]),
                                   ("empty string", ''),
                                   ("no separator", 'lnltc'),
                                   ("not an invoice", 'not an invoice')):
            with self.subTest(label):
                with self.assertRaises(BOLT11DecodeException):
                    decode_bolt11_invoice(bad_invoice)

        decoded = bech32_decode(invoice, ignore_long_length=True)
        # bolt11 uses vanilla bech32; the same data encoded as bech32m must be rejected
        with self.assertRaises(BOLT11DecodeException):
            decode_bolt11_invoice(bech32_encode(segwit_addr.Encoding.BECH32M, decoded.hrp, decoded.data))
        # hrp of another network, and one that is not a lightning invoice at all
        with self.assertRaises(BOLT11DecodeException):
            decode_bolt11_invoice(invoice, net=constants.BitcoinTestnet)
        with self.assertRaises(BOLT11DecodeException):
            decode_bolt11_invoice(bech32_encode(segwit_addr.Encoding.BECH32, 'bc', decoded.data))

    def test_invalid_amount(self):
        # the amount is part of the hrp; amounts the BOLT11Addr.amount setter rejects must
        # surface as BOLT11DecodeException, not as a bare BOLT11InvoiceException
        tags5 = [('p', convertbits(RHASH, 8, 5)),
                 ('s', convertbits(PAYMENT_SECRET, 8, 5)),
                 ('d', convertbits(b'test', 8, 5))]
        self.assertEqual(  # control
            Decimal('0.0025'),
            decode_bolt11_invoice(self._encode_invoice_with_raw_tags(tags5, amountstr='2500u')).amount)
        self.assertEqual(  # control: 'p' is allowed as long as the amount is a whole msat
            Decimal('0.00000000001'),
            decode_bolt11_invoice(self._encode_invoice_with_raw_tags(tags5, amountstr='10p')).amount)
        for amountstr in ('84000001',  # more than the total coin supply
                          '1p',        # sub-millisatoshi precision
                          '25y',       # invalid multiplier
                          '0',         # must be positive; an absent amount means "any amount"
                          '0u',
                          '025u',      # no leading zeroes
                          '-1',
                          'nan',
                          '1e3'):
            with self.subTest(amountstr=amountstr):
                with self.assertRaises(BOLT11DecodeException):
                    decode_bolt11_invoice(self._encode_invoice_with_raw_tags(tags5, amountstr=amountstr))

    def test_amount_validation(self):
        addr = BOLT11Addr(paymenthash=RHASH, payment_secret=PAYMENT_SECRET, tags=[('d', '')])
        for label, value in (("str", '1'),
                             ("float", 1.5),
                             ("bytes", b'1'),
                             ("NaN", Decimal('nan')),
                             ("negative", Decimal(-1)),
                             ("zero", Decimal(0)),
                             ("more than the coin supply", Decimal(84_000_001)),
                             ("sub-millisatoshi", Decimal('0.0000000000001'))):
            with self.subTest(label):
                with self.assertRaises(BOLT11InvoiceException):
                    addr.amount = value
        addr.amount = 1  # an int is accepted and converted
        self.assertEqual(Decimal(1), addr.amount)
        addr.amount = Decimal('0.00000000001')  # 1 msat, the smallest encodable amount
        self.assertEqual(Decimal('0.00000000001'), addr.amount)
        addr.amount = None
        self.assertIsNone(addr.amount)

    def test_date_validation(self):
        addr = BOLT11Addr(paymenthash=RHASH, payment_secret=PAYMENT_SECRET, tags=[('d', '')])
        for label, value in (("str", '123'),
                             ("bytes", b'123'),
                             ("None", None),
                             ("above TIMESTAMP_SANE_MAX", TIMESTAMP_SANE_MAX + 1)):
            with self.subTest(label):
                with self.assertRaises(BOLT11InvoiceException):
                    addr.date = value
        with self.assertRaises(BOLT11InvoiceException):
            BOLT11Addr(date=TIMESTAMP_SANE_MAX + 1)
        # a float (e.g. straight from time.time()) is truncated to an int
        addr.date = 1615922274.9
        self.assertEqual(1615922274, addr.date)
        # the largest timestamp the 35-bit bolt11 field can hold is still accepted
        addr.date = 2 ** 35 - 1
        self.assertEqual(2 ** 35 - 1, addr.date)
        self.assertLessEqual(2 ** 35 - 1, TIMESTAMP_SANE_MAX)

    def test_min_final_cltv_expiry_decoding(self):
        lnaddr = decode_bolt11_invoice("lnsb500u1pdsgyf3pp5nmrqejdsdgs4n9ukgxcp2kcq265yhrxd4k5dyue58rxtp5y83s3qsp5qyqszqgpqyqszqgpqyqszqgpqyqszqgpqyqszqgpqyqszqgpqyqsdqqcqzys9qypqsqp2h6a5xeytuc3fad2ed4gxvhd593lwjdna3dxsyeem0qkzjx6guk44jend0xq4zzvp6f3fy07wnmxezazzsxgmvqee8shxjuqu2eu0qpnvc95x",
                                       net=constants.BitcoinSimnet)
        self.assertEqual(144, lnaddr.get_min_final_cltv_delta())

        lnaddr = decode_bolt11_invoice("lntltc15u1p0m6lzupp5zqjthgvaad9mewmdjuehwddyze9d8zyxcc43zhaddeegt37sndgsdq4xysyymr0vd4kzcmrd9hx7cqp7xqrrss9qy9qsqsp5vlhcs24hwm747w8f3uau2tlrdkvjaglffnsstwyamj84cxuhrn2sd9wnsselxlsqyz5ktk0dafjj77ag862qqeqmldxd6nzx7z2q2ttsu073xujdvjjzwcullaxh5mfz3qmd558cf7l8m0e4rkq227cnsvcp2lx59z",
                                       net=constants.BitcoinTestnet)
        self.assertEqual(30, lnaddr.get_min_final_cltv_delta())

    def test_min_final_cltv_expiry_roundtrip(self):
        for cltv in (1, 15, 16, 31, 32, 33, 150, 511, 512, 513, 1023, 1024, 1025):
            lnaddr = BOLT11Addr(
                paymenthash=RHASH, payment_secret=b"\x01"*32, amount=Decimal('0.001'), tags=[('d', '1 cup coffee'), ('x', 60), ('c', cltv), ('9', 33282)])
            self.assertEqual(cltv, lnaddr.get_min_final_cltv_delta())
            invoice = encode_bolt11_invoice(lnaddr, PRIVKEY)
            self.assertEqual(cltv, decode_bolt11_invoice(invoice).get_min_final_cltv_delta())

    def test_features(self):
        lnaddr = decode_bolt11_invoice("lnltc25m1pvjluezpp5qqqsyqcyq5rqwzqfqqqsyqcyq5rqwzqfqqqsyqcyq5rqwzqfqypqsp5zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zygsdq5vdhkven9v5sxyetpdees9qypqsz9xh7sh9jme6a8sccdc2wp7gg38yzljq5z035uzkattc40vcv66lj7uhn4nnswfa2s00rjrdjhw9uncw7jn43kj5n45ur3v4r77f25pcpmamsgf")
        self.assertEqual(33282, lnaddr.get_tag('9'))
        self.assertEqual(LnFeatures(33282), lnaddr.get_features())

    def test_payment_secret(self):
        lnaddr = decode_bolt11_invoice("lnltc25m1pvjluezpp5qqqsyqcyq5rqwzqfqqqsyqcyq5rqwzqfqqqsyqcyq5rqwzqfqypqsp5zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zygsdq5vdhkven9v5sxyetpdees9q5sqqqqqqqqqqqqqqqpqsq8da9nsp6wq9ugrglqwvgzqn6tj6wr0u0fzwg57trnjd070ef6f6ykh6kykgtdg9umljul8ah85sy80jgz7f3jr5y2uu756s4a8pq80qpxe4kez")
        self.assertEqual((1 << 9) + (1 << 15) + (1 << 99), lnaddr.get_tag('9'))
        self.assertEqual(b"\x11" * 32, lnaddr.payment_secret)

    def test_validate_and_compare_features(self):
        lnaddr = decode_bolt11_invoice("lnltc25m1pvjluezpp5qqqsyqcyq5rqwzqfqqqsyqcyq5rqwzqfqqqsyqcyq5rqwzqfqypqsp5zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zygsdq5vdhkven9v5sxyetpdees9q5sqqqqqqqqqqqqqqqpqsq8da9nsp6wq9ugrglqwvgzqn6tj6wr0u0fzwg57trnjd070ef6f6ykh6kykgtdg9umljul8ah85sy80jgz7f3jr5y2uu756s4a8pq80qpxe4kez")
        lnaddr.validate_and_compare_features(LnFeatures((1 << 8) + (1 << 14) + (1 << 15)))
        with self.assertRaises(IncompatibleLightningFeatures):
            lnaddr.validate_and_compare_features(LnFeatures((1 << 8) + (1 << 14) + (1 << 16)))

    def test_format_bolt11_routing_info_as_human_readable(self):
        r_tags_expl = [
            ['r', [(bfh('029e03a901b85534ff1e92c43c74431f7ce72046060fcf7a95c37e148f78c77255'), bfh('0102030405060708'), 1, 20, 3),
                   (bfh('039e03a901b85534ff1e92c43c74431f7ce72046060fcf7a95c37e148f78c77255'), bfh('030405060708090a'), 2, 30, 4)]],
            ['r', [(bfh('038863cf8ab91046230f561cd5b386cbff8309fa02e3f0c3ed161a3aeb64a643b9'), bfh('f4240000000002cd'), 0, 1, 40)]],
        ]
        self.assertEqual(
            [
                ('r', [('029e03a901b85534ff1e92c43c74431f7ce72046060fcf7a95c37e148f78c77255',
                        '66051x263430x1800', 1, 20, 3),
                       ('039e03a901b85534ff1e92c43c74431f7ce72046060fcf7a95c37e148f78c77255',
                        '197637x395016x2314', 2, 30, 4)]
                 ),
                ('r', [('038863cf8ab91046230f561cd5b386cbff8309fa02e3f0c3ed161a3aeb64a643b9',
                        '16000000x0x717', 0, 1, 40),]
                 ),
            ],
            BOLT11Addr.format_bolt11_routing_info_as_human_readable(r_tags_expl, has_explicit_r_tagtype=True))

        r_tags_impl = [
            [(bfh('029e03a901b85534ff1e92c43c74431f7ce72046060fcf7a95c37e148f78c77255'), bfh('0102030405060708'), 1, 20, 3),
                   (bfh('039e03a901b85534ff1e92c43c74431f7ce72046060fcf7a95c37e148f78c77255'), bfh('030405060708090a'), 2, 30, 4)],
            [(bfh('038863cf8ab91046230f561cd5b386cbff8309fa02e3f0c3ed161a3aeb64a643b9'), bfh('f4240000000002cd'), 0, 1, 40)],
        ]
        self.assertEqual(
            [
                [('029e03a901b85534ff1e92c43c74431f7ce72046060fcf7a95c37e148f78c77255',
                  '66051x263430x1800', 1, 20, 3),
                 ('039e03a901b85534ff1e92c43c74431f7ce72046060fcf7a95c37e148f78c77255',
                  '197637x395016x2314', 2, 30, 4)],
                [('038863cf8ab91046230f561cd5b386cbff8309fa02e3f0c3ed161a3aeb64a643b9',
                  '16000000x0x717', 0, 1, 40),],
            ],
            BOLT11Addr.format_bolt11_routing_info_as_human_readable(r_tags_impl, has_explicit_r_tagtype=False))

        for has_explicit_r_tagtype in (False, True):
            self.assertEqual(
                [],
                BOLT11Addr.format_bolt11_routing_info_as_human_readable([], has_explicit_r_tagtype=has_explicit_r_tagtype))
