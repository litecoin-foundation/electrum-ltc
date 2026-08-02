import os
import asyncio
from unittest.mock import patch

from electrum import SimpleConfig
from electrum.invoices import Invoice
from electrum.payment_identifier import (
    maybe_extract_bech32_lightning_payment_identifier, PaymentIdentifier, PaymentIdentifierType,
    PaymentIdentifierState, invoice_from_payment_identifier, remove_uri_prefix, outputs_to_multiline_csv,
)
from electrum.lnurl import LNURL6Data, LNURL3Data, LNURLError
from electrum.transaction import PartialTxOutput

from . import ElectrumTestCase
from . import restore_wallet_from_text__for_unittest


class WalletMock:
    def __init__(self, electrum_path):
        self.config = SimpleConfig({
            'electrum_path': electrum_path,
            'decimal_point': 5
        })
        self.contacts = None


class TestPaymentIdentifier(ElectrumTestCase):
    def setUp(self):
        super().setUp()
        self.wallet = WalletMock(self.electrum_path)

        self.config = SimpleConfig({
            'electrum_path': self.electrum_path,
            'decimal_point': 5
        })
        self.wallet2_path = os.path.join(self.electrum_path, "somewallet2")

    def test_maybe_extract_bech32_lightning_payment_identifier(self):
        bolt11 = "lnltc1ps9zprzpp5qqqsyqcyq5rqwzqfqqqsyqcyq5rqwzqfqqqsyqcyq5rqwzqfqypqsp5zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zygsdqq9qypqszqzgtd6vmekfly93cnrul3772cx24w0l0cqka4cpywy9km3dxwq330e2k648zeknmxztfk84j4esx00nx79374q0wa444zydl402rh5cqgf65sq"
        lnurl = "lnurl1dp68gurn8ghj7um9wfmxjcm99e5k7telwy7nxenrxvmrgdtzxsenjcm98pjnwxq96s9"
        self.assertEqual(bolt11, maybe_extract_bech32_lightning_payment_identifier(f"{bolt11}".upper()))
        self.assertEqual(bolt11, maybe_extract_bech32_lightning_payment_identifier(f"lightningltc:{bolt11}"))
        self.assertEqual(bolt11, maybe_extract_bech32_lightning_payment_identifier(f"  lightningltc:{bolt11}   ".upper()))
        self.assertEqual(lnurl, maybe_extract_bech32_lightning_payment_identifier(lnurl))
        self.assertEqual(lnurl, maybe_extract_bech32_lightning_payment_identifier(f"  lightningltc:{lnurl}   ".upper()))

        self.assertEqual(None, maybe_extract_bech32_lightning_payment_identifier(f"litecoin:{bolt11}"))
        self.assertEqual(None, maybe_extract_bech32_lightning_payment_identifier(f":{bolt11}"))
        self.assertEqual(None, maybe_extract_bech32_lightning_payment_identifier(f"garbage text"))

    def test_remove_uri_prefix(self):
        lightning, bitcoin = 'lightningltc', 'litecoin'
        tests = (
            (lightning, '', ''),
            (lightning, 'lightningltc:test', 'test'),
            (lightning, 'litecoin:test', 'litecoin:test'),
            (lightning, 'lightningtest', 'lightningtest'),
            (lightning, 'lightning test', 'lightning test'),
            (bitcoin, 'lightningltc:test', 'lightningltc:test'),
            (bitcoin, 'litecoin:test', 'test'),
            (bitcoin, 'litecoin', 'litecoin'),
            (bitcoin, 'litecoin:', ''),
        )
        for prefix, input_str, expected_output_str in tests:
            output_str = remove_uri_prefix(input_str, prefix=prefix)
            self.assertEqual(expected_output_str, output_str, msg=output_str)
        with self.assertRaises(AssertionError):
            remove_uri_prefix(data=1234, prefix="test")

    def test_bolt11(self):
        # no amount, no fallback address
        bolt11 = 'lnltc1ps9zprzpp5qqqsyqcyq5rqwzqfqqqsyqcyq5rqwzqfqqqsyqcyq5rqwzqfqypqsp5zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zygsr9yq20q82gphp2nflc7jtzrcazrra7wwgzxqc8u7754cdlpfrmccae92qgzqvzq2ps8pqqqqqqpqqqqq9qqqvpeuqafqxu92d8lr6fvg0r5gv0heeeqgcrqlnm6jhphu9y00rrhy4grqszsvpcgpy9qqqqqqgqqqqq7qqzqhp58yjmdan79s6qqdhdzgynm4zwqd5d7xmw5fk98klysy043l2ahrqs9qy9qsqdpq5eygqqx5m47qqdj6dq02echphtxhe98un5q2r9uzhg66pue3rj6f3d8mmwtttycnak60y35626rkhvca9kaejsv3czra7cscw99sqxa7cuk'
        for pi_str in [
            f'{bolt11}',
            f'  {bolt11}',
            f'{bolt11}  ',
            f'lightningltc:{bolt11}',
            f'  lightningltc:{bolt11}',
            f'lightningltc:{bolt11}  ',
            f'lightningltc:{bolt11.upper()}',
            f'lightningltc:{bolt11}'.upper(),
        ]:
            pi = PaymentIdentifier(None, pi_str)
            self.assertTrue(pi.is_valid())
            self.assertEqual(PaymentIdentifierType.BOLT11, pi.type)
            self.assertFalse(pi.is_amount_locked())
            self.assertFalse(pi.is_error())
            self.assertIsNotNone(pi.bolt11)

        for pi_str in [
            f'lightningltc:  {bolt11}',
            f'litecoin:{bolt11}'
        ]:
            pi = PaymentIdentifier(None, pi_str)
            self.assertFalse(pi.is_valid())

        # amount, fallback address
        bolt_11_w_fallback = 'lnltc241ps9zprzpp5qqqsyqcyq5rqwzqfqqqsyqcyq5rqwzqfqqqsyqcyq5rqwzqfqypqsp5zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zygsr9yq20q82gphp2nflc7jtzrcazrra7wwgzxqc8u7754cdlpfrmccae92qgzqvzq2ps8pqqqqqqpqqqqq9qqqvpeuqafqxu92d8lr6fvg0r5gv0heeeqgcrqlnm6jhphu9y00rrhy4grqszsvpcgpy9qqqqqqgqqqqq7qqzqfpp3qjmp7lwpagxun9pygexvgpjdc4jdj85fhp58yjmdan79s6qqdhdzgynm4zwqd5d7xmw5fk98klysy043l2ahrqs9qy9qsqr8k87557npyvh09gymtdx6p6s0f6aw5djakjvtzhcxu6akhg0nus8336gtm37fpt0462e5jckxzrwgfstm2ffmevrdfjta9j8h4y54gp5d5x9w'

        pi = PaymentIdentifier(None, bolt_11_w_fallback)
        self.assertTrue(pi.is_valid())
        self.assertEqual(PaymentIdentifierType.BOLT11, pi.type)
        self.assertIsNotNone(pi.bolt11)
        self.assertTrue(pi.is_lightning())
        self.assertTrue(pi.is_onchain())
        self.assertTrue(pi.is_amount_locked())

        self.assertFalse(pi.is_error())
        self.assertFalse(pi.need_resolve())
        self.assertFalse(pi.need_finalize())
        self.assertFalse(pi.is_multiline())

    def test_bip21(self):
        bip21 = 'litecoin:ltc1qj3zx2zc4rpv3npzmznxhdxzn0wm7pzqpraswap?message=unit_test'
        for pi_str in [
            f'{bip21}',
            f'  {bip21}',
            f'{bip21}  ',
            f'{bip21}'.upper(),
        ]:
            pi = PaymentIdentifier(None, pi_str)
            self.assertTrue(pi.is_available())
            self.assertFalse(pi.is_lightning())
            self.assertTrue(pi.is_onchain())
            self.assertIsNotNone(pi.bip21)

        # amount, expired, message
        bip21 = 'litecoin:ltc1qy7ps80x5csdqpfcekn97qfljxtg2lryarms74q?amount=0.001&message=unit_test&time=1707382023&exp=3600'

        pi = PaymentIdentifier(None, bip21)
        self.assertTrue(pi.is_available())
        self.assertFalse(pi.is_lightning())
        self.assertTrue(pi.is_onchain())
        self.assertIsNotNone(pi.bip21)

        self.assertTrue(pi.has_expired())
        self.assertEqual('unit_test', pi.bip21.get('message'))

        # amount, expired, message, lightning w matching amount
        bip21 = 'litecoin:LKes97HFbh3dxrvhiMohYXyzYJPTK37n7u?amount=0.001&message=unit_test&time=1707382023&exp=3600&lightningltc=lnltc1m1ps9zprzpp5qqqsyqcyq5rqwzqfqqqsyqcyq5rqwzqfqqqsyqcyq5rqwzqfqypqsp5zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zygsdq5xysxxatsyp3k7enxv4jsxqzpu9qy9qsqrk5p227neujjnf8pna3law67zuqtq7w37ja37tkwytmzum80dnk8gc3ewlv7xpmjhsw5av7t0sfwqpvl0wes95cwqlsx7c43vadkwfgpe7axap'

        pi = PaymentIdentifier(None, bip21)
        self.assertTrue(pi.is_available())
        self.assertTrue(pi.is_lightning())
        self.assertTrue(pi.is_onchain())
        self.assertIsNotNone(pi.bip21)
        self.assertIsNotNone(pi.bolt11)

        self.assertTrue(pi.has_expired())
        self.assertEqual('unit_test', pi.bip21.get('message'))

        # amount, expired, message, lightning w non-matching amount
        bip21 = 'litecoin:LKes97HFbh3dxrvhiMohYXyzYJPTK37n7u?amount=0.01&message=unit_test&time=1707382023&exp=3600&lightningltc=lnltc20m1pvjluezpp5qqqsyqcyq5rqwzqfqqqsyqcyq5rqwzqfqqqsyqcyq5rqwzqfqypqhp58yjmdan79s6qqdhdzgynm4zwqd5d7xmw5fk98klysy043l2ahrqsfpp3qjmp7lwpagxun9pygexvgpjdc4jdj85fr9yq20q82gphp2nflc7jtzrcazrra7wwgzxqc8u7754cdlpfrmccae92qgzqvzq2ps8pqqqqqqpqqqqq9qqqvpeuqafqxu92d8lr6fvg0r5gv0heeeqgcrqlnm6jhphu9y00rrhy4grqszsvpcgpy9qqqqqqgqqqqq7qqzqdawnkw3dr9zrh4v0u6ad97nx3hqsw7als037v3h9m3hzzw77c9unq8uhqel5dvtrqexu08200f2alk6ul0skh3q3jag0gvr9z46xxlcpcjry0w'

        pi = PaymentIdentifier(None, bip21)
        self.assertFalse(pi.is_valid())

        # amount bounds
        bip21 = 'litecoin:LKes97HFbh3dxrvhiMohYXyzYJPTK37n7u?amount=-1'
        pi = PaymentIdentifier(None, bip21)
        self.assertFalse(pi.is_valid())

        bip21 = 'litecoin:LKes97HFbh3dxrvhiMohYXyzYJPTK37n7u?amount=84000001'
        pi = PaymentIdentifier(None, bip21)
        self.assertFalse(pi.is_valid())

        bip21 = 'litecoin:LKes97HFbh3dxrvhiMohYXyzYJPTK37n7u?amount=0'
        pi = PaymentIdentifier(None, bip21)
        self.assertFalse(pi.is_valid())

    def test_lnurl_basic(self):
        """Test basic LNURL parsing without resolve"""
        valid_lnurl = 'lnurl1dp68gurn8ghj7um9wfmxjcm99e5k7telwy7nxenrxvmrgdtzxsenjcm98pjnwxq96s9'
        pi = PaymentIdentifier(None, valid_lnurl)
        self.assertTrue(pi.is_valid())
        self.assertEqual(PaymentIdentifierType.LNURL, pi.type)
        self.assertFalse(pi.is_available())
        self.assertTrue(pi.need_resolve())
        self.assertEqual(PaymentIdentifierState.NEED_RESOLVE, pi.state)

        # Test with lightningltc: prefix
        lightning_lnurl = f'lightningltc:{valid_lnurl}'
        pi = PaymentIdentifier(None, lightning_lnurl)
        self.assertTrue(pi.is_valid())
        self.assertEqual(PaymentIdentifierType.LNURL, pi.type)
        self.assertTrue(pi.need_resolve())

        # test with lud17 prefix
        unsupported_lud_17_lnurl_c = f"lnurlc://service.io/?q=3fc3645b439ce8e7"
        pi = PaymentIdentifier(None, unsupported_lud_17_lnurl_c)
        self.assertFalse(pi.is_valid())

        valid_lud_17_lnurl_w = f"lnurlw://service.io/?q=3fc3645b439ce8e7"
        pi = PaymentIdentifier(None, valid_lud_17_lnurl_w)
        self.assertTrue(pi.is_valid())
        self.assertEqual(PaymentIdentifierType.LNURL, pi.type)
        self.assertTrue(pi.need_resolve())

    @patch('electrum.payment_identifier.request_lnurl')
    def test_lnurl_pay_resolve(self, mock_request_lnurl):
        """Test LNURL-pay (LNURL6) with mocked resolve"""
        valid_lnurl = 'LNURL1DP68GURN8GHJ7MRWVF5HGUEWD3HXZERYWFJHXUEWVDHK6TMVDE6HYMRS9ANRV46DXETQPJQCS4'

        # Mock lnurl-p response
        mock_lnurl6_data = LNURL6Data(
            callback_url='https://example.com/lnurl-pay',
            max_sendable_sat=1_000_000,
            min_sendable_sat=1_000,
            metadata_plaintext='Test payment',
            comment_allowed=100,
        )
        mock_request_lnurl.return_value = mock_lnurl6_data

        pi = PaymentIdentifier(None, valid_lnurl)
        self.assertTrue(pi.need_resolve())
        self.assertEqual(PaymentIdentifierType.LNURL, pi.type)

        async def run_resolve():
            await pi._do_resolve()

        asyncio.run(run_resolve())

        self.assertEqual(PaymentIdentifierType.LNURLP, pi.type)
        self.assertEqual(PaymentIdentifierState.LNURLP_FINALIZE, pi.state)
        self.assertTrue(pi.need_finalize())
        self.assertIsNotNone(pi.lnurl_data)
        self.assertTrue(isinstance(pi.lnurl_data, LNURL6Data))
        self.assertEqual(1_000, pi.lnurl_data.min_sendable_sat)
        self.assertEqual(1_000_000, pi.lnurl_data.max_sendable_sat)
        self.assertEqual('Test payment', pi.lnurl_data.metadata_plaintext)
        self.assertEqual(100, pi.lnurl_data.comment_allowed)

    @patch('electrum.payment_identifier.request_lnurl')
    def test_lnurl_withdraw_resolve(self, mock_request_lnurl):
        """Test LNURL-withdraw (LNURL3) with mocked resolve"""
        valid_lnurl = 'LNURL1DP68GURN8GHJ7MRWVF5HGUEWD3HXZERYWFJHXUEWVDHK6TM4WPNHYCTYV4EJ7DFCVGENSDPH8QCRZETXVGCXGCMPVFJR' \
                        'WENP8P3NJEP3XE3NQWRPXFJR2VRRVSCX2V33V5UNVC3SXP3RXCFSVFSKVWPCV3SKZWTP8YUZ7AMFW35XGUNPWUHKZURF9AMRZT' \
                        'MVDE6HYMP0FETHVUNZDAMHQ7JSF4RX73TZ2VU9Z3J3GVMSLCJ57F'

        # Mock lnurl-w response
        mock_lnurl3_data = LNURL3Data(
            callback_url='https://example.com/lnurl-withdraw',
            k1='test-k1-value',
            default_description='Test withdrawal',
            min_withdrawable_sat=1_000,
            max_withdrawable_sat=500_000,
        )
        mock_request_lnurl.return_value = mock_lnurl3_data

        pi = PaymentIdentifier(None, valid_lnurl)
        self.assertTrue(pi.need_resolve())
        self.assertEqual(PaymentIdentifierType.LNURL, pi.type)

        async def run_resolve():
            await pi._do_resolve()

        asyncio.run(run_resolve())

        self.assertEqual(PaymentIdentifierType.LNURLW, pi.type)
        self.assertEqual(PaymentIdentifierState.LNURLW_FINALIZE, pi.state)
        self.assertIsNotNone(pi.lnurl_data)
        self.assertEqual('test-k1-value', pi.lnurl_data.k1)
        self.assertEqual('Test withdrawal', pi.lnurl_data.default_description)
        self.assertEqual(1000, pi.lnurl_data.min_withdrawable_sat)
        self.assertEqual(500000, pi.lnurl_data.max_withdrawable_sat)

    @patch('electrum.payment_identifier.request_lnurl')
    def test_lnurl_resolve_error(self, mock_request_lnurl):
        """Test LNURL resolve error handling"""
        lnurl = 'LNURL1DP68GURN8GHJ7MRWVF5HGUEWD3HXZERYWFJHXUEWVDHK6TM4WPNHYCTYV4EJ7DFCVGENSDPH8QCRZETXVGCXGCMPVFJR' \
                  'WENP8P3NJEP3XE3NQWRPXFJR2VRRVSCX2V33V5UNVC3SXP3RXCFSVFSKVWPCV3SKZWTP8YUZ7AMFW35XGUNPWUHKZURF9AMRZT' \
                  'MVDE6HYMP0FETHVUNZDAMHQ7JSF4RX73TZ2VU9Z3J3GVMSLCJ57F'

        # Mock LNURL error
        mock_request_lnurl.side_effect = LNURLError("Server error")

        pi = PaymentIdentifier(None, lnurl)
        self.assertTrue(pi.need_resolve())

        async def run_resolve():
            await pi._do_resolve()

        asyncio.run(run_resolve())

        self.assertEqual(PaymentIdentifierState.ERROR, pi.state)
        self.assertTrue(pi.is_error())
        self.assertIn("Server error", pi.get_error())

    def test_multiline(self):
        pi_str = '\n'.join([
            'ltc1qj3zx2zc4rpv3npzmznxhdxzn0wm7pzqpraswap,0.01',
            'ltc1q66ex4c3vek4cdmrfjxtssmtguvs3r30pdfskez,0.01',
        ])
        pi = PaymentIdentifier(self.wallet, pi_str)
        self.assertTrue(pi.is_valid())
        self.assertTrue(pi.is_multiline())
        self.assertFalse(pi.is_multiline_max())
        self.assertIsNotNone(pi.multiline_outputs)
        self.assertEqual(2, len(pi.multiline_outputs))
        self.assertTrue(all(lambda x: isinstance(x, PartialTxOutput) for x in pi.multiline_outputs))
        self.assertEqual(1000, pi.multiline_outputs[0].value)
        self.assertEqual(1000, pi.multiline_outputs[1].value)
        self.assertEqual(pi_str, outputs_to_multiline_csv(pi.multiline_outputs, self.config))

        pi_str = '\n'.join([
            'ltc1qj3zx2zc4rpv3npzmznxhdxzn0wm7pzqpraswap,0.01',
            'ltc1q66ex4c3vek4cdmrfjxtssmtguvs3r30pdfskez,0.01',
            'ltc1qy7ps80x5csdqpfcekn97qfljxtg2lryarms74q,!',
        ])
        pi = PaymentIdentifier(self.wallet, pi_str)
        self.assertTrue(pi.is_valid())
        self.assertTrue(pi.is_multiline())
        self.assertTrue(pi.is_multiline_max())
        self.assertIsNotNone(pi.multiline_outputs)
        self.assertEqual(3, len(pi.multiline_outputs))
        self.assertTrue(all(lambda x: isinstance(x, PartialTxOutput) for x in pi.multiline_outputs))
        self.assertEqual(1000, pi.multiline_outputs[0].value)
        self.assertEqual(1000, pi.multiline_outputs[1].value)
        self.assertEqual('!', pi.multiline_outputs[2].value)
        self.assertEqual(pi_str, outputs_to_multiline_csv(pi.multiline_outputs, self.config))

        pi_str = '\n'.join([
            'ltc1qj3zx2zc4rpv3npzmznxhdxzn0wm7pzqpraswap,0.01',
            'ltc1q66ex4c3vek4cdmrfjxtssmtguvs3r30pdfskez,2!',
            'ltc1qy7ps80x5csdqpfcekn97qfljxtg2lryarms74q,3!',
        ])
        pi = PaymentIdentifier(self.wallet, pi_str)
        self.assertTrue(pi.is_valid())
        self.assertTrue(pi.is_multiline())
        self.assertTrue(pi.is_multiline_max())
        self.assertIsNotNone(pi.multiline_outputs)
        self.assertEqual(3, len(pi.multiline_outputs))
        self.assertTrue(all(lambda x: isinstance(x, PartialTxOutput) for x in pi.multiline_outputs))
        self.assertEqual(1000, pi.multiline_outputs[0].value)
        self.assertEqual('2!', pi.multiline_outputs[1].value)
        self.assertEqual('3!', pi.multiline_outputs[2].value)

        pi_str = '\n'.join([
            'ltc1qj3zx2zc4rpv3npzmznxhdxzn0wm7pzqpraswap,0.01',
            'script(OP_RETURN baddc0ffee),0',
            'script(OP_0 OP_1NEGATE OP_16 ' + 'aa' * 80 + ' ' + 'bb' * 300 + '),0',  # every push encoding
        ])
        pi = PaymentIdentifier(self.wallet, pi_str)
        self.assertTrue(pi.is_valid())
        self.assertTrue(pi.is_multiline())
        self.assertIsNotNone(pi.multiline_outputs)
        self.assertEqual(3, len(pi.multiline_outputs))
        self.assertTrue(all(lambda x: isinstance(x, PartialTxOutput) for x in pi.multiline_outputs))
        self.assertEqual(1000, pi.multiline_outputs[0].value)
        self.assertEqual(0, pi.multiline_outputs[1].value)
        self.assertEqual(0, pi.multiline_outputs[2].value)
        self.assertEqual(pi_str, outputs_to_multiline_csv(pi.multiline_outputs, self.config))

        # disallow negative output values
        pi_str = '\n'.join([
            'ltc1qj3zx2zc4rpv3npzmznxhdxzn0wm7pzqpraswap,-0.01',
        ])
        pi = PaymentIdentifier(self.wallet, pi_str)
        self.assertFalse(pi.is_valid())
        self.assertTrue(pi.is_multiline())
        self.assertIsNotNone(pi.error)

    def test_spk(self):
        address = 'ltc1qj3zx2zc4rpv3npzmznxhdxzn0wm7pzqpraswap'
        for pi_str in [
            f'{address}',
            f'  {address}',
            f'{address}  ',
            f'{address}'.upper(),
        ]:
            pi = PaymentIdentifier(None, pi_str)
            self.assertTrue(pi.is_valid())
            self.assertTrue(pi.is_available())

        spk = 'script(OP_RETURN baddc0ffee)'
        for pi_str in [
            f'{spk}',
            f'  {spk}',
            f'{spk}  ',
        ]:
            pi = PaymentIdentifier(None, pi_str)
            self.assertTrue(pi.is_valid())
            self.assertTrue(pi.is_available())

    def test_email_and_domain(self):
        # TODO resolve mock
        domain_pi_strings = (
            'some.domain',
            'some.weird.but.valid.domain',
            'lnbcsome.weird.but.valid.domain',
            'bc1qsome.weird.but.valid.domain',
            'lnurlsome.weird.but.valid.domain',
        )
        for pi_str in domain_pi_strings:
            pi = PaymentIdentifier(None, pi_str)
            self.assertTrue(pi.is_valid())
            self.assertEqual(PaymentIdentifierType.DOMAINLIKE, pi.type)
            self.assertFalse(pi.is_available())
            self.assertTrue(pi.need_resolve())

        email_pi_strings = (
            'user@some.domain',
            'user@some.weird.but.valid.domain',
            'lnbcuser@some.domain',
            'lnurluser@some.domain',
            'bc1quser@some.domain',
            'lightningltc:user@some.domain',
            'lightningltc:user@some.weird.but.valid.domain',
            'lightningltc:lnbcuser@some.domain',
            'lightningltc:lnurluser@some.domain',
            'lightningltc:bc1quser@some.domain',
        )
        for pi_str in email_pi_strings:
            pi = PaymentIdentifier(None, pi_str)
            self.assertTrue(pi.is_valid())
            self.assertEqual(PaymentIdentifierType.EMAILLIKE, pi.type)
            self.assertFalse(pi.is_available())
            self.assertTrue(pi.need_resolve())

    async def test_invoice_from_payment_identifier(self):
        # amount, expired, message, lightning w matching amount
        bip21 = 'litecoin:LKes97HFbh3dxrvhiMohYXyzYJPTK37n7u?amount=0.001&message=unit_test&time=1707382023&exp=3600&lightningltc=lnltc1m1ps9zprzpp5qqqsyqcyq5rqwzqfqqqsyqcyq5rqwzqfqqqsyqcyq5rqwzqfqypqsp5zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zygsdq5xysxxatsyp3k7enxv4jsxqzpu9qy9qsqrk5p227neujjnf8pna3law67zuqtq7w37ja37tkwytmzum80dnk8gc3ewlv7xpmjhsw5av7t0sfwqpvl0wes95cwqlsx7c43vadkwfgpe7axap'

        pi = PaymentIdentifier(None, bip21)
        invoice = invoice_from_payment_identifier(pi, None, None)
        self.assertTrue(isinstance(invoice, Invoice))
        self.assertTrue(invoice.is_lightning())
        self.assertEqual(100_000_000, invoice.amount_msat)

        text = 'bitter grass shiver impose acquire brush forget axis eager alone wine silver'
        d = restore_wallet_from_text__for_unittest(text, path=self.wallet2_path, config=self.config)
        wallet2 = d['wallet']  # type: Standard_Wallet

        # no amount bip21+lightning, MAX amount passed
        bip21 = 'litecoin:LKes97HFbh3dxrvhiMohYXyzYJPTK37n7u?message=unit_test&time=1707382023&exp=3600&lightningltc=lnltc1ps9zprzpp5qqqsyqcyq5rqwzqfqqqsyqcyq5rqwzqfqqqsyqcyq5rqwzqfqypqsp5zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zygsdqq9qypqszqzgtd6vmekfly93cnrul3772cx24w0l0cqka4cpywy9km3dxwq330e2k648zeknmxztfk84j4esx00nx79374q0wa444zydl402rh5cqgf65sq'
        pi = PaymentIdentifier(None, bip21)
        invoice = invoice_from_payment_identifier(pi, wallet2, '!')
        self.assertTrue(isinstance(invoice, Invoice))
        self.assertFalse(invoice.is_lightning())

        # no amount lightning, MAX amount passed -> expect raise
        bolt11 = 'lightningltc:lnltc1ps9zprzpp5qqqsyqcyq5rqwzqfqqqsyqcyq5rqwzqfqqqsyqcyq5rqwzqfqypqsp5zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zygsdqq9qypqszqzgtd6vmekfly93cnrul3772cx24w0l0cqka4cpywy9km3dxwq330e2k648zeknmxztfk84j4esx00nx79374q0wa444zydl402rh5cqgf65sq'
        pi = PaymentIdentifier(None, bolt11)
        with self.assertRaises(AssertionError):
            invoice_from_payment_identifier(pi, wallet2, '!')
        invoice = invoice_from_payment_identifier(pi, wallet2, 1)
        self.assertEqual(1000, invoice.amount_msat)
