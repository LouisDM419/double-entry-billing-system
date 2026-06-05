from django.db import models
from django.db.models import CheckConstraint, Q

class AccountType(models.TextChoices):
    ASSET = 'ASSET', 'Asset'
    LIABILITY = 'LIABILITY', 'Liability'
    REVENUE = 'REVENUE', 'Revenue'
    EXPENSE = 'EXPENSE', 'Expense'

class Account(models.Model):
    name = models.CharField(max_length=100)
    account_type = models.CharField(max_length=20, choices=AccountType.choices)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.account_type})"

class LedgerTransaction(models.Model):
    description = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    idempotency_key = models.CharField(max_length=100, unique=True, null=True, blank=True)

    def __str__(self):
        return f"Tx {self.id}: {self.description}"

class Entry(models.Model):
    DIRECTION_CHOICES = [
        ('DEBIT', 'DEBIT'),
        ('CREDIT', 'CREDIT'),
    ]
    transaction = models.ForeignKey(
        LedgerTransaction, 
        on_delete=models.CASCADE, 
        related_name='entries'
    )
    account = models.ForeignKey(
        Account, 
        on_delete=models.CASCADE, 
        related_name='entries'
    )
    amount = models.DecimalField(max_digits=18, decimal_places=4)
    direction = models.CharField(max_length=10, choices=DIRECTION_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            CheckConstraint(
                condition=Q(direction__in=['DEBIT', 'CREDIT']),
                name='check_direction'
            ),
            CheckConstraint(
                condition=Q(amount__gt=0),
                name='check_positive_amount'
            )
        ]

    def __str__(self):
        return f"Entry {self.id} ({self.direction}): {self.amount} to {self.account.name}"

class IdempotencyKey(models.Model):
    key = models.CharField(max_length=100, primary_key=True)
    status = models.CharField(max_length=20) # PENDING, COMPLETED, FAILED
    response_body = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"IdempotencyKey {self.key} ({self.status})"
