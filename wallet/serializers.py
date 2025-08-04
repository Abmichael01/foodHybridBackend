from rest_framework import serializers
from .models import Transaction, Beneficiary

class TransactionSerializer(serializers.ModelSerializer):
    from_user = serializers.SerializerMethodField()
    to = serializers.SerializerMethodField()
    partner_name = serializers.SerializerMethodField()
    # last_name = serializers.SerializerMethodField()


    class Meta:
        model = Transaction
        fields = ['id', 'amount', 'from_user', 'to', 'transaction_type', 'status', 'created_at', 'order_id', 'available_balance_at_time', 'payment_method', 'bank_name', 'account_number','account_name', 'reference', 'user', 'partner_name']

    def get_from_user(self, obj):
        if obj.transaction_type in ['fund']:
            return "External Source"
        return obj.from_user or obj.user.username

    def get_to(self, obj):
        if obj.transaction_type in ['fund', 'roi']:
            return obj.user.username  # Money enters user
        if obj.transaction_type in ['investment', 'investmentUpdate']:
            return obj.to  # should be set to shop/product name
        return obj.to
    def to_representation(self, instance):
        data = super().to_representation(instance)

        if instance.transaction_type in ['fund', 'withdraw']:
            data.pop('order_id', None)

        # Hide bank details if not a withdrawal
        if instance.transaction_type != 'withdraw':
            data.pop('bank_name', None)
            data.pop('account_number', None)
            data.pop('account_name', None)

        return data
    
    def get_partner_name(self, obj):
          full_name = getattr(obj.user, 'first_name', None) + " " + getattr(obj.user, 'last_name', None) 
          return full_name or obj.user.username


class BeneficiarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Beneficiary
        fields = ['id', 'name', 'bank_name', 'account_number', 'account_type', 'sort_code']