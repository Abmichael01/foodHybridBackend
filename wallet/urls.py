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
    path("admin/remittance/<str:remittance_>/confirm/", AdminConfirmRemittanceView.as_view(), name="admin-confirm-remittance"),
    path("remittance/", VendorRemitView.as_view(), name="create-remittance"),
]
