from dataclasses import dataclass
from functools import cached_property
from typing import List, Optional

import requests
from eth_abi import encode_abi
from eth_account import Account
from eth_account.datastructures import SignedMessage
from eth_account.messages import encode_defunct
from eth_typing import ChecksumAddress, HexStr
from web3 import Web3

from gnosis.eth import EthereumClient
from gnosis.eth.ethereum_client import EthereumNetwork


class ItxException(Exception):
    pass


class ItxInsufficientFunds(ItxException):
    """
    {'jsonrpc': '2.0', 'id': '1', 'error': {'code': -32007, 'message': 'Insufficient funds.'}}
    """
    pass


class ItxTransactionAlreadySent(ItxException):
    """
    {'jsonrpc': '2.0', 'id': '1', 'error': {'code': -32008, 'message': 'Transaction already sent'}}
    """
    pass


@dataclass
class InfuraTxSent:
    infura_tx_hash: str
    tx_hash: str


class ItxRelayTx:
    """
    Infura Relay Tx
    """
    def __init__(self, to: ChecksumAddress, data: bytes, gas: int, chain_id: int = 4):
        self.to = to
        self.data = data
        self.gas = gas
        self.chain_id = chain_id

    def tx_hash(self):
        encoded = encode_abi(['address', 'bytes', 'uint', 'uint'],
                             [self.to, self.data, self.gas, self.chain_id])
        return Web3.sha3(encoded)

    def sign(self, account: Account) -> SignedMessage:
        return account.sign_message(encode_defunct(self.tx_hash()))


class ItxClient:
    """
    Infura Relay Txs client
    """
    def __init__(self, infura_node_url: str):
        self.base_url = infura_node_url
        self.http_session = requests.session()

    def get_balance(self, address: ChecksumAddress):
        if not Web3.isChecksumAddress(address):
            raise ValueError(f'{address} is not a valid checksummed address')
        return int(requests.post(self.base_url, json={
            "id": "1",
            "jsonrpc": "2.0",
            "method": "relay_getBalance",
            "params": [
                address
            ]
        }).json()['result']) / 1e18

    def get_transaction_status(self, relay_tx_hash: str):
        """
        :param relay_tx_hash:
        :return: Dictionary  {'broadcastTime': '2021-02-15T16:28:47.978Z',
                              'ethTxHash': '0x5aaf963acc5ec3ec64c6c954f617e6539663bacf42a73fce74bb0c8829088a8e',
                              'gasPrice': '7290000028'}
        """
        return requests.post(self.base_url, json={
            "id": "1",
            "jsonrpc": "2.0",
            "method": "relay_getTransactionStatus",
            "params": [
                relay_tx_hash
            ]
        }).json()['result'][0]

    def send_transaction(self, relay_tx: ItxRelayTx, account: Account) -> HexStr:
        """
        :param relay_tx:
        :param account:
        :return: Infura tx identifier as str
        """
        signature = relay_tx.sign(account).signature.hex()
        response = requests.post(self.base_url, json={
            "id": "1",
            "jsonrpc": "2.0",
            "method": "relay_sendTransaction",
            "params": [
                {
                    'to': relay_tx.to,
                    'data': relay_tx.data.hex(),
                    'gas': str(relay_tx.gas),
                },
                signature,
            ]
        })
        response_json = response.json()
        if 'error' in response_json:
            error_message = response_json['error']['message']
            if error_message == 'Insufficient funds.':
                raise ItxInsufficientFunds
            elif error_message == 'Transaction already sent':
                raise ItxTransactionAlreadySent
            else:
                raise ItxException(error_message)
        return response_json['result']


class InfuraRelayServiceException(Exception):
    pass


class InfuraRelayServiceProvider:
    def __new__(cls):
        if not hasattr(cls, 'instance'):
            from django.conf import settings
            from django.core.exceptions import ImproperlyConfigured
            if not settings.INFURA_NODE_URL:
                raise ImproperlyConfigured('INFURA_NODE_URL is missing')
            cls.instance = InfuraRelayService(settings.INFURA_NODE_URL, settings.INFURA_RELAY_SENDER_PRIVATE_KEY)
        return cls.instance

    @classmethod
    def del_singleton(cls):
        if hasattr(cls, 'instance'):
            del cls.instance


class InfuraRelayService:
    ALLOWED_ADDRESSES = {
        EthereumNetwork.RINKEBY: [ChecksumAddress('0x2d8cE02dd1644A9238e08430CaeA15a609503140')],
    }
    EXECUTE_METHOD_ID = bytes.fromhex('1cff79cd')

    def __init__(self, infura_node_url: str, infura_relay_sender_private_key: str):
        self.infura_node_url = infura_node_url
        self.infura_relay_sender_account = Account.from_key(infura_relay_sender_private_key)
        self.ethereum_client = EthereumClient(infura_node_url)
        self.itx_client = ItxClient(infura_node_url)

    def allowed_addresses(self) -> Optional[List[ChecksumAddress]]:
        return self.ALLOWED_ADDRESSES.get(self.ethereum_network, [])

    @cached_property
    def ethereum_network(self) -> EthereumNetwork:
        return self.ethereum_client.get_network()

    def estimate_gas(self, to: ChecksumAddress, data: bytes):
        """
        :param to:
        :param data:
        :return: gas estimation
        :raises:
        """
        try:
            return self.ethereum_client.w3.eth.estimateGas({'to': to,
                                                            'from': self.infura_relay_sender_account.address,
                                                            'data': data,
                                                            'value': 0})
        except ValueError:
            # ValueError: {'code': -32016, 'message': 'The execution failed due to an exception.',
            #              'data': 'Reverted'}
            raise InfuraRelayServiceException(f'Cannot estimate gas price for tx to={to} data={data.hex()}')

    def check_transaction(self, itx_relay_tx: ItxRelayTx) -> bool:
        if itx_relay_tx.to not in self.allowed_addresses():
            return False
        if itx_relay_tx.data[:4] != self.EXECUTE_METHOD_ID:
            return False
        return True

    def send_transaction(self, to: ChecksumAddress, data: bytes) -> InfuraTxSent:
        gas = self.estimate_gas(to, data)
        itx_relay_tx = ItxRelayTx(to, data, gas * 2)
        if self.check_transaction(itx_relay_tx):
            infura_tx_hash = self.itx_client.send_transaction(itx_relay_tx, self.infura_relay_sender_account)
            transaction_status = self.itx_client.get_transaction_status(infura_tx_hash)
            return InfuraTxSent(infura_tx_hash, transaction_status['ethTxHash'])
        else:
            raise InfuraRelayServiceException('Not valid tx to send using Infura relay')
