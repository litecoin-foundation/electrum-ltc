#!/usr/bin/env bash
export HOME=~
set -eux pipefail
mkdir -p ~/.litecoin
cat > ~/.litecoin/litecoin.conf <<EOF
regtest=1
txindex=1
txospenderindex=1
printtoconsole=1
rpcuser=doggman
rpcpassword=donkey
rpcallowip=127.0.0.1
zmqpubrawblock=tcp://127.0.0.1:29332
zmqpubrawtx=tcp://127.0.0.1:29333
fallbackfee=0.0002
[regtest]
rpcbind=0.0.0.0
rpcport=19554
EOF
rm -rf ~/.litecoin/regtest
litecoind -regtest &
litecoin_cli=(litecoin-cli -regtest -rpcuser=doggman -rpcpassword=donkey -rpcport=19554)
"${litecoin_cli[@]}" -rpcwait createwallet test_wallet
addr=$("${litecoin_cli[@]}" -rpcwallet=test_wallet getnewaddress)
# Initialize MWEB with a peg-in at activation (Litecoin Core issue #807).
"${litecoin_cli[@]}" generatetoaddress 431 "$addr"
mweb_addr=$("${litecoin_cli[@]}" getnewaddress mweb mweb)
"${litecoin_cli[@]}" sendtoaddress "$mweb_addr" 1
"${litecoin_cli[@]}" generatetoaddress 10 "$addr"
tail -f ~/.litecoin/regtest/debug.log
