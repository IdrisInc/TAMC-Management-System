from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
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
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, related_name='approved_requests', null=True, blank=True)
    approved_by_production = models.BooleanField(default=False)
    approved_by_technical_manager = models.BooleanField(default=False)
    approved_by_finance = models.BooleanField(default=False)
    approved_by_treasurer = models.BooleanField(default=False)
    approved_by_cashier = models.BooleanField(default=False)
    wef = models.DateField(blank=True, null=True)
    account_to_charge = models.CharField(max_length=100, blank=True, null=True)
    account_code = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    
    def update_status(self):
        if self.approved_by_cashier:
            self.status = 'Approved'
        elif self.approved_by_treasurer or self.approved_by_finance or self.approved_by_technical_manager or self.approved_by_production:
            self.status = 'Under Review'
        else:
            self.status = 'Pending'

    def calculate_total_request(self):
        self.total_request = sum(item.total_request for item in self.items.all())

    def save(self, *args, **kwargs):
        self.update_status()
        super().save(*args, **kwargs)

    class Meta:
        ordering = ['-created_at'] 


@receiver(post_save, sender=FinancialRequest)
def create_or_update_items(sender, instance, created, **kwargs):
    if not created:
        instance.calculate_total_request()
        FinancialRequest.objects.filter(pk=instance.pk).update(total_request=instance.total_request)


class Item(models.Model):
    financial_request = models.ForeignKey(FinancialRequest, on_delete=models.CASCADE, related_name='items')
    item_name = models.CharField(max_length=255, default='My Item')  # Ensure item_name is not empty
    quantity = models.IntegerField(blank=False)  # Ensure quantity is not empty
    price = models.DecimalField(max_digits=15, decimal_places=2, blank=False)  # Ensure price is not empty
    total_request = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)

    def save(self, *args, **kwargs):
        self.total_request = self.quantity * self.price
        super().save(*args, **kwargs)

    def __str__(self):
        return self.item_name



