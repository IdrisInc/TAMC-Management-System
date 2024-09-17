from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils import timezone

class FinancialRequest(models.Model):
    STATUS_CHOICES = (
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),
        ('Under Review', 'Under Review'),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True)
    amount_numeric = models.DecimalField(max_digits=10, decimal_places=2)
    amount_words = models.CharField(max_length=255)
    purpose = models.CharField(max_length=255)
    description = models.CharField(max_length=255, default='No description provided')
    total_request = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    wef = models.DateField(blank=True, null=True)
    account_to_charge = models.CharField(max_length=100, blank=True, null=True)
    account_code = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')

    # Approval fields
    approved_by_production = models.ManyToManyField(User, related_name='approved_by_production', blank=True)
    approved_by_technical_manager = models.ManyToManyField(User, related_name='approved_by_technical_manager', blank=True)
    approved_by_finance = models.ManyToManyField(User, related_name='approved_by_finance', blank=True)
    approved_by_treasurer = models.ManyToManyField(User, related_name='approved_by_treasurer', blank=True)
    approved_by_cashier = models.ManyToManyField(User, related_name='approved_by_cashier', blank=True)
    
    def update_status(self):
        if (self.approved_by_production.exists() and 
            self.approved_by_technical_manager.exists() and 
            self.approved_by_finance.exists() and 
            self.approved_by_treasurer.exists() and 
            self.approved_by_cashier.exists()):
            self.status = 'Approved'
        elif (self.approved_by_production.exists() or 
            self.approved_by_technical_manager.exists() or 
            self.approved_by_finance.exists() or 
            self.approved_by_treasurer.exists() or 
            self.approved_by_cashier.exists()):
            self.status = 'Under Review'
        else:
            self.status = 'Pending'
        self.save(update_fields=['status'])

    def calculate_total_request(self):
        self.total_request = sum(item.total_request for item in self.items.all())

    def save(self, *args, **kwargs):
        initial_save = not self.pk
        if initial_save:
            super().save(*args, **kwargs)  # Save initially to get a primary key
        if not kwargs.pop('skip_total_request', False):
            self.calculate_total_request()
        if not initial_save:
            super().save(*args, **kwargs)  # Save again to update total_request

    class Meta:
        ordering = ['-created_at']

class Item(models.Model):
    financial_request = models.ForeignKey(FinancialRequest, on_delete=models.CASCADE, related_name='items')
    item_name = models.CharField(max_length=255, default='My Item')
    quantity = models.IntegerField(blank=False)
    price = models.DecimalField(max_digits=15, decimal_places=2, blank=False)
    total_request = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)

    def save(self, *args, **kwargs):
        self.total_request = self.quantity * self.price
        super().save(*args, **kwargs)

    def __str__(self):
        return self.item_name

@receiver(post_save, sender=Item)
@receiver(post_delete, sender=Item)
def update_financial_request_total(sender, instance, **kwargs):
    instance.financial_request.calculate_total_request()
    instance.financial_request.save(skip_total_request=True)
