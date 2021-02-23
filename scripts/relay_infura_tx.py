import argparse

import requests
from eth_account import Account
from hexbytes import HexBytes

from gnosis.eth import EthereumClient
from gnosis.safe import SafeTx

TRANSACTION_SERVICE_URL = 'https://safe-transaction.rinkeby.staging.gnosisdev.com/api/v1/multisig-transactions/'
RELAY_URL = 'https://safe-relay.dev.gnosisdev.com/api/v1/infura/transactions/'

parser = argparse.ArgumentParser(description='Send transaction using Infura relay')
parser.add_argument('safe_tx_hash', type=str, help='Safe tx hash to get from tx service')
args = parser.parse_args()

safe_tx_hash = args.safe_tx_hash
response = requests.get(TRANSACTION_SERVICE_URL + safe_tx_hash)
if response.ok:
    data = response.json()
    signatures = HexBytes(b''.join([HexBytes(confirmation['signature']) for confirmation in
                                    sorted(data['confirmations'], key=lambda x: x['owner'].lower())]))

    ethereum_client = EthereumClient('https://staging-openethereum.rinkeby.gnosisdev.com/')
    safe_tx = SafeTx(ethereum_client, data['safe'], data['to'], int(data['value']),
                     data['data'], data['operation'], data['safeTxGas'],
                     data['baseGas'], int(data['gasPrice']), data['gasToken'], data['refundReceiver'],
                     signatures, safe_nonce=data['nonce'])
    tx_data = safe_tx.w3_tx.buildTransaction({'gas': 0, 'from': Account.create().address})['data']
    payload = {
        'data': HexBytes(tx_data)[4:].hex(),
        'to': data['safe'],
    }
    response = requests.post(RELAY_URL, json=payload)
    print(response.ok, response.json())
