import logging

from django.conf import settings
from django.utils.dateparse import parse_datetime

from django_filters.rest_framework import DjangoFilterBackend
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from eth_account.account import Account
from rest_framework import filters, status
from rest_framework.authentication import TokenAuthentication
from rest_framework.generics import CreateAPIView, ListAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView, exception_handler
from web3 import Web3

from gnosis.eth.constants import NULL_ADDRESS
from gnosis.safe.exceptions import SafeServiceException
from gnosis.safe.serializers import SafeMultisigEstimateTxSerializer

from safe_relay_service.version import __version__

from .filters import DefaultPagination, SafeMultisigTxFilter
from .models import EthereumEvent, SafeContract, SafeFunding, SafeMultisigTx
from .serializers import (
    ERC20Serializer, ERC721Serializer, InfuraTxResponseSerializer,
    InfuraTxSerializer, SafeBalanceResponseSerializer, SafeContractSerializer,
    SafeCreationResponseSerializer, SafeCreationSerializer,
    SafeFundingResponseSerializer, SafeMultisigEstimateTxResponseSerializer,
    SafeMultisigTxResponseSerializer, SafeRelayMultisigTxSerializer,
    SafeResponseSerializer,
    TransactionEstimationWithNonceAndGasTokensResponseSerializer)
from .services import StatsServiceProvider
from .services.funding_service import FundingServiceException
from .services.infura_relay_service import (InfuraRelayServiceException,
                                            InfuraRelayServiceProvider)
from .services.safe_creation_service import (SafeCreationServiceException,
                                             SafeCreationServiceProvider)
from .services.transaction_service import (TransactionServiceException,
                                           TransactionServiceProvider)
from .tasks import fund_deployer_task

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    # Call REST framework's default exception handler first,
    # to get the standard error response.
    response = exception_handler(exc, context)

    # Now add the HTTP status code to the response.
    if not response:
        if isinstance(exc, (SafeServiceException, SafeCreationServiceException, TransactionServiceException,
                            FundingServiceException, InfuraRelayServiceException)):
            response = Response(status=status.HTTP_422_UNPROCESSABLE_ENTITY)
        else:
            response = Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        if str(exc):
            exception_str = '{}: {}'.format(exc.__class__.__name__, exc)
        else:
            exception_str = exc.__class__.__name__
        response.data = {'exception': exception_str}

        logger.warning('%s - Exception: %s - Data received %s',
                       context['request'].build_absolute_uri(),
                       exception_str,
                       context['request'].data)

    return response


class AboutView(APIView):
    renderer_classes = (JSONRenderer,)

    def get(self, request, format=None):
        safe_funder_public_key = Account.from_key(settings.SAFE_FUNDER_PRIVATE_KEY).address \
            if settings.SAFE_FUNDER_PRIVATE_KEY else None
        safe_sender_public_key = Account.from_key(settings.SAFE_TX_SENDER_PRIVATE_KEY).address \
            if settings.SAFE_TX_SENDER_PRIVATE_KEY else None
        content = {
            'name': 'Safe Relay Service',
            'version': __version__,
            'api_version': self.request.version,
            'https_detected': self.request.is_secure(),
            'settings': {
                'ETHEREUM_NODE_URL': settings.ETHEREUM_NODE_URL,
                'ETH_HASH_PREFIX ': settings.ETH_HASH_PREFIX,
                'FIXED_GAS_PRICE': settings.FIXED_GAS_PRICE,
                'GAS_STATION_NUMBER_BLOCKS': settings.GAS_STATION_NUMBER_BLOCKS,
                'NOTIFICATION_SERVICE_PASS': bool(settings.NOTIFICATION_SERVICE_PASS),
                'NOTIFICATION_SERVICE_URI': settings.NOTIFICATION_SERVICE_URI,
                'SAFE_ACCOUNTS_BALANCE_WARNING': settings.SAFE_ACCOUNTS_BALANCE_WARNING,
                'SAFE_CHECK_DEPLOYER_FUNDED_DELAY': settings.SAFE_CHECK_DEPLOYER_FUNDED_DELAY,
                'SAFE_CHECK_DEPLOYER_FUNDED_RETRIES': settings.SAFE_CHECK_DEPLOYER_FUNDED_RETRIES,
                'SAFE_CONTRACT_ADDRESS': settings.SAFE_CONTRACT_ADDRESS,
                'SAFE_DEFAULT_CALLBACK_HANDLER': settings.SAFE_DEFAULT_CALLBACK_HANDLER,
                'SAFE_FIXED_CREATION_COST': settings.SAFE_FIXED_CREATION_COST,
                'SAFE_FUNDER_MAX_ETH': settings.SAFE_FUNDER_MAX_ETH,
                'SAFE_FUNDER_PUBLIC_KEY': safe_funder_public_key,
                'SAFE_FUNDING_CONFIRMATIONS': settings.SAFE_FUNDING_CONFIRMATIONS,
                'SAFE_PROXY_FACTORY_ADDRESS': settings.SAFE_PROXY_FACTORY_ADDRESS,
                'SAFE_PROXY_FACTORY_V1_0_0_ADDRESS': settings.SAFE_PROXY_FACTORY_V1_0_0_ADDRESS,
                'SAFE_TX_NOT_MINED_ALERT_MINUTES': settings.SAFE_TX_NOT_MINED_ALERT_MINUTES,
                'SAFE_TX_SENDER_PUBLIC_KEY': safe_sender_public_key,
                'SAFE_V0_0_1_CONTRACT_ADDRESS': settings.SAFE_V0_0_1_CONTRACT_ADDRESS,
                'SAFE_V1_0_0_CONTRACT_ADDRESS': settings.SAFE_V1_0_0_CONTRACT_ADDRESS,
                'SAFE_VALID_CONTRACT_ADDRESSES': settings.SAFE_VALID_CONTRACT_ADDRESSES,
            }
        }
        return Response(content)


class SafeCreationView(CreateAPIView):
    permission_classes = (AllowAny,)
    serializer_class = SafeCreationSerializer

    @swagger_auto_schema(responses={201: SafeCreationResponseSerializer(),
                                    400: 'Invalid data',
                                    422: 'Cannot process data'})
    def post(self, request, *args, **kwargs):
        """
        Begins creation of a Safe
        """
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            s, owners, threshold, payment_token = (serializer.data['s'], serializer.data['owners'],
                                                   serializer.data['threshold'], serializer.data['payment_token'])

            safe_creation = SafeCreationServiceProvider().create_safe_tx(s, owners, threshold, payment_token)
            safe_creation_response_data = SafeCreationResponseSerializer(data={
                'signature': {
                    'v': safe_creation.v,
                    'r': safe_creation.r,
                    's': safe_creation.s,
                },
                'tx': {
                    'from': safe_creation.deployer,
                    'value': safe_creation.value,
                    'data': safe_creation.data.hex(),
                    'gas': safe_creation.gas,
                    'gas_price': safe_creation.gas_price,
                    'nonce': 0,
                },
                'tx_hash': safe_creation.tx_hash,
                'payment': safe_creation.payment,
                'payment_token': safe_creation.payment_token or NULL_ADDRESS,
                'safe': safe_creation.safe.address,
                'deployer': safe_creation.deployer,
                'funder': safe_creation.funder,
            })
            safe_creation_response_data.is_valid(raise_exception=True)
            return Response(status=status.HTTP_201_CREATED, data=safe_creation_response_data.data)
        else:
            http_status = status.HTTP_422_UNPROCESSABLE_ENTITY \
                if 's' in serializer.errors else status.HTTP_400_BAD_REQUEST
            return Response(status=http_status, data=serializer.errors)


class SafeView(APIView):
    permission_classes = (AllowAny,)
    serializer_class = SafeResponseSerializer

    @swagger_auto_schema(responses={200: SafeResponseSerializer(),
                                    404: 'Safe not found',
                                    422: 'Safe address checksum not valid'})
    def get(self, request, address, format=None):
        """
        Get status of the safe
        """
        if not Web3.isChecksumAddress(address):
            return Response(status=status.HTTP_422_UNPROCESSABLE_ENTITY)

        safe_info = SafeCreationServiceProvider().retrieve_safe_info(address)
        serializer = self.serializer_class(safe_info)
        return Response(status=status.HTTP_200_OK, data=serializer.data)


class SafeBalanceView(APIView):
    permission_classes = (AllowAny,)
    serializer_class = SafeBalanceResponseSerializer

    @swagger_auto_schema(responses={200: SafeBalanceResponseSerializer(many=True),
                                    404: 'Safe not found',
                                    422: 'Safe address checksum not valid'})
    def get(self, request, address, format=None):
        """
        Get status of the safe
        """
        if not Web3.isChecksumAddress(address):
            return Response(status=status.HTTP_422_UNPROCESSABLE_ENTITY)
        else:
            try:
                SafeContract.objects.get(address=address)
            except SafeContract.DoesNotExist:
                return Response(status=status.HTTP_404_NOT_FOUND)

            safe_balances = StatsServiceProvider().get_balances(address)
            serializer = self.serializer_class(data=safe_balances, many=True)
            # assert serializer.is_valid(), 'Safe Balance result not valid'
            serializer.is_valid()
            return Response(status=status.HTTP_200_OK, data=serializer.data)


class SafeSignalView(APIView):
    permission_classes = (AllowAny,)

    @swagger_auto_schema(responses={200: SafeFundingResponseSerializer(),
                                    404: 'Safe not found',
                                    422: 'Safe address checksum not valid'})
    def get(self, request, address, format=None):
        """
        Get status of the safe creation
        """
        if not Web3.isChecksumAddress(address):
            return Response(status=status.HTTP_422_UNPROCESSABLE_ENTITY)
        else:
            try:
                safe_funding = SafeFunding.objects.get(safe=address)
                serializer = SafeFundingResponseSerializer(safe_funding)
                return Response(status=status.HTTP_200_OK, data=serializer.data)
            except SafeFunding.DoesNotExist:
                return Response(status=status.HTTP_404_NOT_FOUND)

    @swagger_auto_schema(responses={202: 'Task was queued',
                                    404: 'Safe not found',
                                    422: 'Safe address checksum not valid'})
    def put(self, request, address, format=None):
        """
        Force check of a safe balance to start the safe creation
        """
        if not Web3.isChecksumAddress(address):
            return Response(status=status.HTTP_422_UNPROCESSABLE_ENTITY)
        else:
            try:
                SafeContract.objects.get(address=address)
            except SafeContract.DoesNotExist:
                return Response(status=status.HTTP_404_NOT_FOUND)

            fund_deployer_task.delay(address)
            return Response(status=status.HTTP_202_ACCEPTED)


class SafeMultisigTxEstimateView(CreateAPIView):
    permission_classes = (AllowAny,)
    serializer_class = SafeMultisigEstimateTxSerializer

    @swagger_auto_schema(responses={200: SafeMultisigEstimateTxResponseSerializer(),
                                    400: 'Data not valid',
                                    404: 'Safe not found',
                                    422: 'Safe address checksum not valid/Tx not valid'})
    def post(self, request, address):
        """
        Estimates a Safe Multisig Transaction. `operational_gas` and `data_gas` are deprecated, use `base_gas` instead
        """
        if not Web3.isChecksumAddress(address):
            return Response(status=status.HTTP_422_UNPROCESSABLE_ENTITY)

        request.data['safe'] = address
        serializer = self.get_serializer_class()(data=request.data)

        if serializer.is_valid():
            data = serializer.validated_data

            transaction_estimation = TransactionServiceProvider().estimate_tx(address, data['to'], data['value'],
                                                                              data['data'], data['operation'],
                                                                              data['gas_token'])
            response_serializer = SafeMultisigEstimateTxResponseSerializer(transaction_estimation)
            return Response(status=status.HTTP_200_OK, data=response_serializer.data)
        else:
            return Response(status=status.HTTP_400_BAD_REQUEST, data=serializer.errors)


class SafeMultisigTxEstimatesView(CreateAPIView):
    permission_classes = (AllowAny,)
    serializer_class = SafeMultisigEstimateTxSerializer

    @swagger_auto_schema(responses={200: TransactionEstimationWithNonceAndGasTokensResponseSerializer(),
                                    400: 'Data not valid',
                                    404: 'Safe not found',
                                    422: 'Safe address checksum not valid/Tx not valid'})
    def post(self, request, address):
        """
        Estimates a Safe Multisig Transaction. `operational_gas` and `data_gas` are deprecated, use `base_gas` instead
        """
        if not Web3.isChecksumAddress(address):
            return Response(status=status.HTTP_422_UNPROCESSABLE_ENTITY)

        request.data['safe'] = address
        serializer = self.get_serializer_class()(data=request.data)

        if serializer.is_valid():
            data = serializer.validated_data

            transaction_estimations = TransactionServiceProvider().estimate_tx_for_all_tokens(address, data['to'],
                                                                                              data['value'],
                                                                                              data['data'],
                                                                                              data['operation'])
            response_serializer = TransactionEstimationWithNonceAndGasTokensResponseSerializer(transaction_estimations)
            return Response(status=status.HTTP_200_OK, data=response_serializer.data)
        else:
            return Response(status=status.HTTP_400_BAD_REQUEST, data=serializer.errors)


# Abstract class
class SafeListApiView(ListAPIView):
    filter_backends = (DjangoFilterBackend, filters.OrderingFilter)
    ordering_fields = '__all__'
    pagination_class = DefaultPagination
    permission_classes = (AllowAny,)

    @swagger_auto_schema(responses={400: 'Data not valid',
                                    404: 'Safe not found/No data for that Safe',
                                    422: 'Safe address checksum not valid'})
    def get(self, request, address):
        if not Web3.isChecksumAddress(address):
            return Response(status=status.HTTP_422_UNPROCESSABLE_ENTITY)
        else:
            try:
                SafeContract.objects.get(address=address)
            except SafeContract.DoesNotExist:
                return Response(status=status.HTTP_404_NOT_FOUND)

        response = super().get(request, address)
        if response.data['count'] == 0:
            response.status_code = status.HTTP_404_NOT_FOUND
        return response


class SafeMultisigTxView(SafeListApiView):
    filterset_class = SafeMultisigTxFilter
    ordering = ('-created',)

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return SafeMultisigTxResponseSerializer
        elif self.request.method == 'POST':
            return SafeRelayMultisigTxSerializer

    def get_queryset(self):
        return SafeMultisigTx.objects.filter(safe=self.kwargs['address'])

    @swagger_auto_schema(responses={201: SafeMultisigTxResponseSerializer(),
                                    400: 'Data not valid',
                                    404: 'Safe not found',
                                    422: 'Safe address checksum not valid/Tx not valid'})
    def post(self, request, address, format=None):
        """
        Send a Safe Multisig Transaction
        """
        if not Web3.isChecksumAddress(address):
            return Response(status=status.HTTP_422_UNPROCESSABLE_ENTITY)

        request.data['safe'] = address
        serializer = self.get_serializer_class()(data=request.data)

        if not serializer.is_valid():
            return Response(status=status.HTTP_400_BAD_REQUEST, data=serializer.errors)
        else:
            data = serializer.validated_data
            safe_multisig_tx = TransactionServiceProvider().create_multisig_tx(
                safe_address=data['safe'],
                to=data['to'],
                value=data['value'],
                data=data['data'],
                operation=data['operation'],
                safe_tx_gas=data['safe_tx_gas'],
                base_gas=data['data_gas'],
                gas_price=data['gas_price'],
                gas_token=data['gas_token'],
                refund_receiver=data['refund_receiver'],
                safe_nonce=data['nonce'],
                signatures=data['signatures']
            )
            response_serializer = SafeMultisigTxResponseSerializer(safe_multisig_tx)
            return Response(status=status.HTTP_201_CREATED, data=response_serializer.data)


class ERC20View(SafeListApiView):
    ordering = ('-ethereum_tx__block__number',)
    serializer_class = ERC20Serializer

    def get_queryset(self):
        address = self.kwargs['address']
        return EthereumEvent.objects.erc20_events(address=address).select_related('ethereum_tx', 'ethereum_tx__block')


class ERC721View(SafeListApiView):
    ordering = ('-ethereum_tx__block__number',)
    serializer_class = ERC721Serializer

    def get_queryset(self):
        address = self.kwargs['address']
        return EthereumEvent.objects.erc721_events(address=address).select_related('ethereum_tx', 'ethereum_tx__block')


class StatsView(APIView):
    permission_classes = (AllowAny,)
    # serializer_class = StatsResponseSerializer

    @swagger_auto_schema(manual_parameters=[
        openapi.Parameter('fromDate', openapi.IN_QUERY, type=openapi.TYPE_STRING, format='date-time',
                          description="ISO 8601 date to filter stats from. If not set, 2018-11-01"),
        openapi.Parameter('toDate', openapi.IN_QUERY, type=openapi.TYPE_STRING, format='date-time',
                          description="ISO 8601 date to filter stats to. If not set, now"),
    ])
    def get(self, request, format=None):
        """
        Get stats of the Safe Relay Service
        """
        from_date = self.request.query_params.get('fromDate')
        to_date = self.request.query_params.get('toDate')
        from_date = parse_datetime(from_date) if from_date else from_date
        to_date = parse_datetime(to_date) if to_date else to_date
        return Response(status=status.HTTP_200_OK, data=StatsServiceProvider().get_relay_stats(from_date, to_date))


class StatsHistoryView(APIView):
    permission_classes = (AllowAny,)
    # serializer_class = StatsResponseSerializer

    @swagger_auto_schema(manual_parameters=[
        openapi.Parameter('fromDate', openapi.IN_QUERY, type=openapi.TYPE_STRING, format='date-time',
                          description="ISO 8601 date to filter stats from. If not set, 2018-11-01"),
        openapi.Parameter('toDate', openapi.IN_QUERY, type=openapi.TYPE_STRING, format='date-time',
                          description="ISO 8601 date to filter stats to. If not set, now"),
    ])
    def get(self, request, format=None):
        """
        Get historic stats of the Safe Relay Service
        """
        from_date = self.request.query_params.get('fromDate')
        to_date = self.request.query_params.get('toDate')
        from_date = parse_datetime(from_date) if from_date else from_date
        to_date = parse_datetime(to_date) if to_date else to_date
        return Response(status=status.HTTP_200_OK,
                        data=StatsServiceProvider().get_relay_history_stats(from_date, to_date))


class PrivateSafesView(ListAPIView):
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)
    queryset = SafeContract.objects.deployed().order_by('created')
    serializer_class = SafeContractSerializer


class InfuraRelayView(APIView):
    def get_serializer_class(self):
        return InfuraTxSerializer

    @swagger_auto_schema(responses={201: InfuraTxResponseSerializer(),
                                    400: 'Data not valid',
                                    404: 'Safe not found',
                                    422: 'Safe address checksum not valid/Tx not valid'})
    def post(self, request, format=None):
        serializer = self.get_serializer_class()(data=request.data)

        if not serializer.is_valid():
            return Response(status=status.HTTP_400_BAD_REQUEST, data=serializer.errors)
        else:
            data = serializer.validated_data
            infura_tx_sent = InfuraRelayServiceProvider().send_transaction(
                data['to'], data['data']
            )
            response_serializer = InfuraTxResponseSerializer(infura_tx_sent)
            return Response(status=status.HTTP_201_CREATED, data=response_serializer.data)
