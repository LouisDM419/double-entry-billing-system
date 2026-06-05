from django.contrib import admin
from billing.models import Account, LedgerTransaction, Entry, IdempotencyKey

@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'account_type', 'created_at')
    list_filter = ('account_type',)
    search_fields = ('name',)

@admin.register(LedgerTransaction)
class LedgerTransactionAdmin(admin.ModelAdmin):
    list_display = ('id', 'description', 'idempotency_key', 'created_at')
    search_fields = ('description', 'idempotency_key')

@admin.register(Entry)
class EntryAdmin(admin.ModelAdmin):
    list_display = ('id', 'transaction', 'account', 'amount', 'direction', 'created_at')
    list_filter = ('direction',)
    search_fields = ('account__name', 'transaction__description')

@admin.register(IdempotencyKey)
class IdempotencyKeyAdmin(admin.ModelAdmin):
    list_display = ('key', 'status', 'created_at')
    list_filter = ('status',)
    search_fields = ('key',)
