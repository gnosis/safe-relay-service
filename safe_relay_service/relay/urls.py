from django.urls import path

from rest_framework.authtoken import views as rest_views

from safe_relay_service.gas_station.views import (GasStationHistoryView,
                                                  GasStationView)
from safe_relay_service.tokens.views import TokensView, TokenView

from . import views

app_name = "safe"

timestamp_regex = '\\d{4}[-]?\\d{1,2}[-]?\\d{1,2} \\d{1,2}:\\d{1,2}:\\d{1,2}'

urlpatterns = [
    path('about/', views.AboutView.as_view(), name='about'),
    path('gas-station/', GasStationView.as_view(), name='gas-station'),
    path('gas-station/history/', GasStationHistoryView.as_view(), name='gas-station-history'),
    path('tokens/', TokensView.as_view(), name='tokens'),
    path('tokens/<str:address>/', TokenView.as_view(), name='token'),
    path('safes/<str:address>/', views.SafeView.as_view(), name='safe'),
    path('safes/<str:address>/balances/', views.SafeBalanceView.as_view(), name='safe-balances'),
    path('safes/<str:address>/funded/', views.SafeSignalView.as_view(), name='safe-signal'),
    path('safes/<str:address>/transactions/', views.SafeMultisigTxView.as_view(), name='safe-multisig-txs'),
    path('safes/<str:address>/erc20-transactions/', views.ERC20View.as_view(), name='erc20-txs'),
    path('safes/<str:address>/erc721-transactions/', views.ERC721View.as_view(), name='erc721-txs'),
    path('safes/<str:address>/transactions/estimate/', views.SafeMultisigTxEstimateView.as_view(),
         name='safe-multisig-tx-estimate'),
    path('safes/<str:address>/transactions/estimates/', views.SafeMultisigTxEstimatesView.as_view(),
         name='safe-multisig-tx-estimates'),
    path('stats/', views.StatsView.as_view(), name='stats'),
    path('stats/history/', views.StatsHistoryView.as_view(), name='stats-history'),
    path('private/api-token-auth/', rest_views.obtain_auth_token, name='api-token-auth'),
    path('private/safes/', views.PrivateSafesView.as_view(), name='private-safes'),
    path('infura/transactions/', views.InfuraRelayView.as_view(), name='infura-txs'),
    path('infura/transactions/<str:infura_tx_hash>/', views.InfuraRelayView.as_view(), name='infura-tx'),

]
