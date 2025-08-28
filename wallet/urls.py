from django.urls import path
from .views import *

urlpatterns = [
    # path('invest/', PartnerInvestmentView.as_view(), name='partner-invest'),
    path('invest/<str:investment_id>/delete/', PartnerInvestmentDeleteView.as_view(), name='investment_delete'),
    path('fund/', FundWalletView.as_view(), name='fund-wallet'),
    path('withdraw/', WithdrawWalletView.as_view(), name='withdraw-wallet'),
    path('invest/<str:investment_id>/approve/', ApproveInvestmentView.as_view(), name='approve-investment'),
    path('beneficiaries/', BeneficiaryListCreateView.as_view(), name='list-add-beneficiaries'),
    path('beneficiaries/<int:pk>/', BeneficiaryDetailView.as_view(), name='update-delete-beneficiary'), 
    path("remittance/confirm/", ConfirmRemittanceView.as_view(), name="admin-confirm-remittance"),
    path("remittance/", VendorRemitView.as_view(), name="create-remittance"),
    path("remittance/<str:remittance_id>/approve/", AdminApproveRemittanceView.as_view(), name="remittance-approval"),
    path("vendor/beneficiaries/", VendorBeneficiaryView.as_view(), name="beneficiary-list-create"),
    path("vendor/beneficiaries/<int:pk>/", BeneficiaryDeleteView.as_view(), name="beneficiary-delete"),
    path("stripe/webhook/", stripe_webhook, name="stripe-webhook"),
]
