from dataclasses import dataclass
from functools import cached_property
from typing import Optional, TypedDict

import humps
import requests
from eth_abi import encode_abi
from eth_account import Account
from eth_account.datastructures import SignedMessage
from eth_account.messages import encode_defunct
from eth_typing import ChecksumAddress, HexStr
from hexbytes import HexBytes
from web3 import Web3
from web3.contract import Contract

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
    tx_hash: Optional[str]


class ItxTxStatus(TypedDict):
    broadcastTime: str  # '2021-02-15T16:28:47.978Z'
    ethTxHash: str  # '0x5aaf963acc5ec3ec64c6c954f617e6539663bacf42a73fce74bb0c8829088a8e'
    gasPrice: str  # '7290000028'


# TODO Move this to EthereumClient on gnosis-py
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
        self.http_session = requests.Session()

    def get_balance(self, address: ChecksumAddress):
        if not Web3.isChecksumAddress(address):
            raise ValueError(f'{address} is not a valid checksummed address')
        return int(self.http_session.post(self.base_url, json={
            "id": "1",
            "jsonrpc": "2.0",
            "method": "relay_getBalance",
            "params": [
                address
            ]
        }).json()['result']) / 1e18

    def get_transaction_status(self, relay_tx_hash: str) -> Optional[ItxTxStatus]:
        """
        :param relay_tx_hash:
        :return: Dictionary  {'broadcast_time': '2021-02-14T16:28:47.978Z',
                              'eth_tx_hash': '0x1aaf963acc5ec3e164c6c954f617e6532663b2cf42a73fce74bb0c8829021a2f',
                              'gas_price': '7290000028'}
        """
        response = self.http_session.post(self.base_url, json={
            "id": "1",
            "jsonrpc": "2.0",
            "method": "relay_getTransactionStatus",
            "params": [
                relay_tx_hash
            ]
        })
        if result := response.json()['result']:
            return humps.decamelize(result[0])

    def send_transaction(self, relay_tx: ItxRelayTx, account: Account) -> HexStr:
        """
        :param relay_tx:
        :param account:
        :return: Infura tx identifier as str
        """
        signature = relay_tx.sign(account).signature.hex()
        response = self.http_session.post(self.base_url, json={
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


refunder_abi = [{'inputs': [{'internalType': 'contract Token',
                             'name': '_token',
                             'type': 'address'},
                            {'internalType': 'address', 'name': '_owner', 'type': 'address'},
                            {'internalType': 'uint256', 'name': '_fee', 'type': 'uint256'},
                            {'internalType': 'bytes4', 'name': '_method', 'type': 'bytes4'}],
                 'stateMutability': 'nonpayable',
                 'type': 'constructor'},
                {'inputs': [{'internalType': 'address',
                             'name': 'newOwner',
                             'type': 'address'}],
                 'name': 'changeOwner',
                 'outputs': [],
                 'stateMutability': 'nonpayable',
                 'type': 'function'},
                {'inputs': [{'internalType': 'address', 'name': 'target', 'type': 'address'},
                            {'internalType': 'bytes', 'name': 'functionData', 'type': 'bytes'}],
                 'name': 'execute',
                 'outputs': [],
                 'stateMutability': 'nonpayable',
                 'type': 'function'},
                {'inputs': [{'internalType': 'address', 'name': 'target', 'type': 'address'},
                            {'internalType': 'bytes', 'name': 'functionData', 'type': 'bytes'}],
                 'name': 'executeTrusted',
                 'outputs': [],
                 'stateMutability': 'nonpayable',
                 'type': 'function'},
                {'inputs': [],
                 'name': 'fee',
                 'outputs': [{'internalType': 'uint256', 'name': '', 'type': 'uint256'}],
                 'stateMutability': 'view',
                 'type': 'function'},
                {'inputs': [],
                 'name': 'method',
                 'outputs': [{'internalType': 'bytes4', 'name': '', 'type': 'bytes4'}],
                 'stateMutability': 'view',
                 'type': 'function'},
                {'inputs': [],
                 'name': 'owner',
                 'outputs': [{'internalType': 'address', 'name': '', 'type': 'address'}],
                 'stateMutability': 'view',
                 'type': 'function'},
                {'inputs': [],
                 'name': 'token',
                 'outputs': [{'internalType': 'contract Token',
                              'name': '',
                              'type': 'address'}],
                 'stateMutability': 'view',
                 'type': 'function'},
                {'inputs': [{'internalType': 'contract Token',
                             'name': 'withdrawToken',
                             'type': 'address'},
                            {'internalType': 'address', 'name': 'target', 'type': 'address'}],
                 'name': 'withdrawTokensTo',
                 'outputs': [],
                 'stateMutability': 'nonpayable',
                 'type': 'function'}]


class InfuraRelayService:
    REFUNDER_ADDRESSES = {
        EthereumNetwork.RINKEBY: ChecksumAddress('0x0971BF033F429B6077b81911505c406Ffb8cde2c'),
    }

    def __init__(self, infura_node_url: str, infura_relay_sender_private_key: str):
        self.infura_node_url = infura_node_url
        self.infura_relay_sender_account = Account.from_key(infura_relay_sender_private_key)
        self.ethereum_client = EthereumClient(infura_node_url)
        self.itx_client = ItxClient(infura_node_url)

    @cached_property
    def ethereum_network(self) -> EthereumNetwork:
        return self.ethereum_client.get_network()

    @cached_property
    def refunder_contract(self) -> Contract:
        refunder_address = self.REFUNDER_ADDRESSES.get(self.ethereum_network)
        return self.ethereum_client.w3.eth.contract(refunder_address, abi=refunder_abi)

    def build_refunder_transaction_data(self, to: ChecksumAddress, data: bytes) -> HexBytes:
        return HexBytes(self.refunder_contract.functions.executeTrusted(to, data).buildTransaction(
            {'gas': 0, 'gasPrice': 0}
        )['data'])

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
        except ValueError as exc:
            # ValueError: {'code': -32016, 'message': 'The execution failed due to an exception.',
            #              'data': 'Reverted'}
            raise InfuraRelayServiceException(f'Cannot estimate gas price for tx to={to} data={data.hex()}') from exc

    def get_transaction_status(self, infura_tx_hash: str):
        return self.itx_client.get_transaction_status(infura_tx_hash)

    def send_transaction(self, to: ChecksumAddress, data: bytes) -> InfuraTxSent:
        refunder_transaction_data = self.build_refunder_transaction_data(to, data)
        gas = self.estimate_gas(self.refunder_contract.address, refunder_transaction_data)
        itx_relay_tx = ItxRelayTx(self.refunder_contract.address, refunder_transaction_data, gas * 2)
        infura_tx_hash = self.itx_client.send_transaction(itx_relay_tx, self.infura_relay_sender_account)
        transaction_status = self.itx_client.get_transaction_status(infura_tx_hash)
        if transaction_status:
            return InfuraTxSent(infura_tx_hash, transaction_status['eth_tx_hash'])
        else:
            return InfuraTxSent(infura_tx_hash, None)
