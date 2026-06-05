from decimal import Decimal
from django.test import TransactionTestCase
from concurrent.futures import ThreadPoolExecutor
from billing.models import Account, LedgerTransaction, Entry, AccountType
from billing.services.ledger_service import LedgerService

class BillingLedgerTestCase(TransactionTestCase):
    def test_double_entry_balance(self):
        # 1. Create debit/credit accounts
        rev_acc = LedgerService.create_account("Revenue", AccountType.REVENUE)
        cust_acc = LedgerService.create_account("Customer", AccountType.LIABILITY)
        
        # 2. Add credit balance
        legs = [
            {"account_id": rev_acc.id, "amount": Decimal("50.00"), "direction": "DEBIT"},
            {"account_id": cust_acc.id, "amount": Decimal("50.00"), "direction": "CREDIT"}
        ]
        LedgerService.record_transaction("User Top Up", legs)
        
        # 3. Assert exact balance values
        rev_bal = LedgerService.get_account_balance(rev_acc.id)
        cust_bal = LedgerService.get_account_balance(cust_acc.id)
        
        self.assertEqual(rev_bal, Decimal("-50.00"))
        self.assertEqual(cust_bal, Decimal("50.00"))

    def test_idempotency_keys(self):
        rev_acc = LedgerService.create_account("Revenue", AccountType.REVENUE)
        cust_acc = LedgerService.create_account("Customer", AccountType.LIABILITY)
        
        legs = [
            {"account_id": rev_acc.id, "amount": Decimal("20.00"), "direction": "DEBIT"},
            {"account_id": cust_acc.id, "amount": Decimal("20.00"), "direction": "CREDIT"}
        ]
        
        # Send transaction with key
        key = "webhook_evt_abc123"
        LedgerService.record_transaction("Billing Run", legs, idempotency_key=key)
        
        # Resend identical payload -> Assert error raised
        with self.assertRaises(ValueError) as exc:
            LedgerService.record_transaction("Billing Run", legs, idempotency_key=key)
        
        self.assertIn("Duplicate transaction request", str(exc.exception))

    def test_unbalanced_transaction_rejected(self):
        rev_acc = LedgerService.create_account("Revenue", AccountType.REVENUE)
        cust_acc = LedgerService.create_account("Customer", AccountType.LIABILITY)
        
        legs = [
            {"account_id": rev_acc.id, "amount": Decimal("20.00"), "direction": "DEBIT"},
            {"account_id": cust_acc.id, "amount": Decimal("10.00"), "direction": "CREDIT"}
        ]
        
        with self.assertRaises(ValueError) as exc:
            LedgerService.record_transaction("Unbalanced Tx", legs)
            
        self.assertIn("Double-entry mismatch", str(exc.exception))

    def test_concurrent_transactions(self):
        rev_acc = LedgerService.create_account("Revenue", AccountType.REVENUE)
        cust_acc = LedgerService.create_account("Customer", AccountType.LIABILITY)
        
        def run_tx(i):
            legs = [
                {"account_id": rev_acc.id, "amount": Decimal("1.00"), "direction": "DEBIT"},
                {"account_id": cust_acc.id, "amount": Decimal("1.00"), "direction": "CREDIT"}
            ]
            # Unique idempotency key for each thread to avoid duplicates
            LedgerService.record_transaction(f"Concurrent Tx {i}", legs, idempotency_key=f"concurrent_key_{i}")

        num_threads = 10
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            list(executor.map(run_tx, range(num_threads)))

        rev_bal = LedgerService.get_account_balance(rev_acc.id)
        cust_bal = LedgerService.get_account_balance(cust_acc.id)
        
        self.assertEqual(rev_bal, Decimal("-10.00"))
        self.assertEqual(cust_bal, Decimal("10.00"))
