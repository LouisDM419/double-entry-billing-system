from decimal import Decimal
from django.db import transaction, IntegrityError
from django.db.models import Sum
from billing.models import Account, LedgerTransaction, Entry, AccountType

class LedgerService:
    @staticmethod
    def create_account(name: str, account_type: str) -> Account:
        return Account.objects.create(name=name, account_type=account_type)

    @staticmethod
    def record_transaction(
        description: str, 
        legs: list[dict], 
        idempotency_key: str = None
    ) -> LedgerTransaction:
        """
        Record a double-entry transaction.
        legs input format:
        [
            {"account_id": 1, "amount": Decimal("100.00"), "direction": "DEBIT"},
            {"account_id": 2, "amount": Decimal("100.00"), "direction": "CREDIT"}
        ]
        """
        # 1. Enforce Double-Entry Constraint
        total_debits = sum(Decimal(str(leg["amount"])) for leg in legs if leg["direction"] == "DEBIT")
        total_credits = sum(Decimal(str(leg["amount"])) for leg in legs if leg["direction"] == "CREDIT")

        if total_debits != total_credits:
            raise ValueError(
                f"Double-entry mismatch! Debits ({total_debits}) must equal Credits ({total_credits})"
            )

        with transaction.atomic():
            # 2. Prevent Duplicate Runs using Idempotency Key
            if idempotency_key:
                # If transaction with the key already exists, raise ValueError
                if LedgerTransaction.objects.filter(idempotency_key=idempotency_key).exists():
                    raise ValueError("Duplicate transaction request blocked by Idempotency Key.")

            # 3. Create Transaction Header
            tx = LedgerTransaction.objects.create(
                description=description, 
                idempotency_key=idempotency_key
            )

            # 4. Insert Ledger Legs
            for leg in legs:
                Entry.objects.create(
                    transaction=tx,
                    account_id=leg["account_id"],
                    amount=Decimal(str(leg["amount"])),
                    direction=leg["direction"]
                )
            
            return tx

    @staticmethod
    def get_account_balance(account_id: int) -> Decimal:
        """
        Calculates balance based on account type:
        - Assets / Expenses: Debits - Credits
        - Liabilities / Revenue: Credits - Debits
        """
        try:
            account = Account.objects.get(id=account_id)
        except Account.DoesNotExist:
            return Decimal("0.00")

        # Sum Debits
        debits = Entry.objects.filter(
            account_id=account_id, 
            direction="DEBIT"
        ).aggregate(total=Sum('amount'))['total'] or Decimal("0.00")

        # Sum Credits
        credits = Entry.objects.filter(
            account_id=account_id, 
            direction="CREDIT"
        ).aggregate(total=Sum('amount'))['total'] or Decimal("0.00")

        if account.account_type in (AccountType.ASSET, AccountType.EXPENSE):
            return debits - credits
        else:
            return credits - debits
