import strawberry
from typing import List
from decimal import Decimal
from billing.models import Account, LedgerTransaction, Entry
from billing.services.ledger_service import LedgerService

@strawberry.django.type(Account)
class AccountType:
    id: strawberry.ID
    name: str
    account_type: str
    created_at: strawberry.auto

@strawberry.django.type(Entry)
class EntryType:
    id: strawberry.ID
    amount: Decimal
    direction: str
    created_at: strawberry.auto

@strawberry.django.type(LedgerTransaction)
class LedgerTransactionType:
    id: strawberry.ID
    description: str
    created_at: strawberry.auto
    entries: List[EntryType]

@strawberry.type
class Query:
    @strawberry.field
    def accounts(self) -> List[AccountType]:
        return Account.objects.all()

    @strawberry.field
    def transactions(self) -> List[LedgerTransactionType]:
        return LedgerTransaction.objects.prefetch_related('entries').all()

    @strawberry.field
    def account_balance(self, account_id: int) -> float:
        balance = LedgerService.get_account_balance(account_id)
        return float(balance)

@strawberry.type
class Mutation:
    @strawberry.mutation
    def create_account(self, name: str, account_type: str) -> AccountType:
        account = LedgerService.create_account(name=name, account_type=account_type.upper())
        return account

    @strawberry.mutation
    def grant_credits(self, account_id: int, amount: float, description: str) -> LedgerTransactionType:
        # Systems revenue offset account is assumed to be ID 1
        revenue_source_id = 1
        legs = [
            {"account_id": revenue_source_id, "amount": Decimal(str(amount)), "direction": "DEBIT"},
            {"account_id": account_id, "amount": Decimal(str(amount)), "direction": "CREDIT"}
        ]
        tx = LedgerService.record_transaction(description, legs)
        return tx

schema = strawberry.Schema(query=Query, mutation=Mutation)
